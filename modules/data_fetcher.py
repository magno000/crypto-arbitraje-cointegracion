"""Obtención de velas históricas desde Binance mediante CCXT.

Los datos sintéticos sólo se generan cuando se solicitan explícitamente para pruebas;
nunca se usan silenciosamente como sustituto de una descarga real fallida.
"""

from __future__ import annotations

import logging
import time
from typing import Iterable, List, Optional, Tuple

import ccxt
import numpy as np
import pandas as pd


DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "DOT/USDT",
    "LTC/USDT", "ATOM/USDT", "UNI/USDT", "FIL/USDT", "NEAR/USDT",
]


class DataFetcher:
    """Cliente de mercado *spot* de Binance con paginación, reintentos y alineación temporal."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.connection_error: Optional[str] = None
        self.exchange: Optional[ccxt.Exchange] = None

        config = {
            "enableRateLimit": True,
            "timeout": 30_000,
            "options": {"defaultType": "spot"},
        }
        if api_key and api_secret:
            config.update({"apiKey": api_key.strip(), "secret": api_secret.strip()})

        try:
            self.exchange = ccxt.binance(config)
            self.exchange.load_markets()
            self.logger.info("Mercados de Binance cargados correctamente.")
        except Exception as exc:
            self.connection_error = f"No fue posible conectar con Binance: {exc}"
            self.logger.warning(self.connection_error)

    @property
    def is_connected(self) -> bool:
        """Indica si el cliente pudo cargar los mercados de Binance."""
        return self.exchange is not None and self.connection_error is None

    def test_connection(self) -> bool:
        """Comprueba la conectividad pública con Binance."""
        if self.exchange is None:
            return False
        try:
            self.exchange.fetch_time()
            self.connection_error = None
            return True
        except Exception as exc:
            self.connection_error = f"No fue posible comprobar Binance: {exc}"
            self.logger.warning(self.connection_error)
            return False

    def get_available_symbols(self, limit: int = 30) -> List[str]:
        """Devuelve mercados *spot* activos contra USDT; usa lista estática sólo para la interfaz."""
        if self.exchange is None:
            return DEFAULT_SYMBOLS.copy()

        try:
            markets = self.exchange.load_markets()
            symbols = [
                symbol
                for symbol, market in markets.items()
                if market.get("spot") and market.get("active", True)
                and market.get("quote") == "USDT"
            ]
            if not symbols:
                raise RuntimeError("Binance no devolvió mercados spot contra USDT.")

            preferred = [symbol for symbol in DEFAULT_SYMBOLS if symbol in symbols]
            remaining = sorted(symbol for symbol in symbols if symbol not in preferred)
            return (preferred + remaining)[:limit]
        except Exception as exc:
            self.connection_error = f"No fue posible listar los mercados de Binance: {exc}"
            self.logger.warning(self.connection_error)
            return DEFAULT_SYMBOLS.copy()

    def get_historical_data(
        self,
        symbol1: str,
        symbol2: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1h",
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Descarga y alinea velas OHLCV reales para un par de símbolos.

        Lanza una excepción si no hay datos reales suficientes. De este modo, el usuario
        puede decidir expresamente si desea emplear el modo sintético de pruebas.
        """
        if symbol1 == symbol2:
            raise ValueError("Selecciona dos activos distintos.")
        if self.exchange is None:
            raise ConnectionError(self.connection_error or "Binance no está disponible.")

        start_ts, end_ts = self._date_range_to_milliseconds(start_date, end_date)
        if end_ts <= start_ts:
            raise ValueError("La fecha final debe ser posterior a la fecha inicial.")

        try:
            candles_1 = self._fetch_ohlcv_paginated(symbol1, timeframe, start_ts, end_ts)
            candles_2 = self._fetch_ohlcv_paginated(symbol2, timeframe, start_ts, end_ts)
            frame_1 = self._ohlcv_to_dataframe(candles_1, symbol1)
            frame_2 = self._ohlcv_to_dataframe(candles_2, symbol2)
            frame_1, frame_2 = self._align_dataframes(frame_1, frame_2)

            if len(frame_1) < 30:
                raise ValueError(
                    "El período seleccionado contiene menos de 30 velas comunes; "
                    "amplía el rango temporal o utiliza un timeframe más corto."
                )
            return frame_1, frame_2
        except Exception as exc:
            self.connection_error = f"Error al descargar datos reales: {exc}"
            self.logger.exception(self.connection_error)
            raise RuntimeError(self.connection_error) from exc

    def get_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = "1h",
    ) -> pd.DataFrame:
        """Descarga las velas reales de un único activo para reutilizarlas en un screener."""
        if self.exchange is None:
            raise ConnectionError(self.connection_error or "Binance no está disponible.")
        start_ts, end_ts = self._date_range_to_milliseconds(start_date, end_date)
        try:
            candles = self._fetch_ohlcv_paginated(symbol, timeframe, start_ts, end_ts)
            frame = self._ohlcv_to_dataframe(candles, symbol)
            if len(frame) < 30:
                raise ValueError(f"{symbol} contiene menos de 30 velas en el período solicitado.")
            return frame
        except Exception as exc:
            self.connection_error = f"Error al descargar {symbol}: {exc}"
            self.logger.exception(self.connection_error)
            raise RuntimeError(self.connection_error) from exc

    def _fetch_ohlcv_paginated(
        self,
        symbol: str,
        timeframe: str,
        since: int,
        until: int,
        max_retries: int = 3,
    ) -> List[List[float]]:
        """Obtiene el histórico por bloques de hasta mil velas, respetando el límite de Binance."""
        if self.exchange is None:
            raise ConnectionError("Cliente de Binance no inicializado.")
        if timeframe not in self.exchange.timeframes:
            raise ValueError(f"Timeframe no soportado por Binance: {timeframe}")
        if symbol not in self.exchange.markets:
            raise ValueError(f"Símbolo no disponible en Binance: {symbol}")

        timeframe_ms = self.exchange.parse_timeframe(timeframe) * 1000
        cursor = since
        collected: List[List[float]] = []

        while cursor < until:
            last_error: Optional[Exception] = None
            batch: List[List[float]] = []
            for attempt in range(max_retries):
                try:
                    batch = self.exchange.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
                    break
                except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
                    last_error = exc
                    wait_seconds = max(1, (self.exchange.rateLimit / 1000) * (attempt + 1))
                    self.logger.warning(
                        "Error descargando %s (%s/%s): %s", symbol, attempt + 1, max_retries, exc
                    )
                    time.sleep(wait_seconds)
            else:
                raise RuntimeError(f"No se pudieron obtener velas de {symbol}: {last_error}")

            if not batch:
                break

            collected.extend(batch)
            next_cursor = int(batch[-1][0]) + timeframe_ms
            if next_cursor <= cursor:
                break
            cursor = next_cursor

            if len(batch) < 1000:
                break
            time.sleep(self.exchange.rateLimit / 1000)

        filtered = [candle for candle in collected if since <= int(candle[0]) < until]
        deduplicated = {int(candle[0]): candle for candle in filtered}
        return [deduplicated[key] for key in sorted(deduplicated)]

    @staticmethod
    def _date_range_to_milliseconds(start_date: str, end_date: str) -> Tuple[int, int]:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        if start.tzinfo is not None:
            start = start.tz_convert("UTC").tz_localize(None)
        if end.tzinfo is not None:
            end = end.tz_convert("UTC").tz_localize(None)
        # Las entradas de fecha de la interfaz no incluyen hora: se interpreta la fecha final como inclusiva.
        if end == end.normalize():
            end += pd.Timedelta("1D")
        return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    @staticmethod
    def _ohlcv_to_dataframe(candles: Iterable[Iterable[float]], symbol: str) -> pd.DataFrame:
        frame = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        if frame.empty:
            raise ValueError(f"Binance no devolvió velas para {symbol} en el período solicitado.")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True).dt.tz_localize(None)
        frame = frame.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
        return frame

    @staticmethod
    def _align_dataframes(frame_1: pd.DataFrame, frame_2: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        common = pd.Index(frame_1["timestamp"]).intersection(pd.Index(frame_2["timestamp"]))
        first = frame_1[frame_1["timestamp"].isin(common)].sort_values("timestamp").reset_index(drop=True)
        second = frame_2[frame_2["timestamp"].isin(common)].sort_values("timestamp").reset_index(drop=True)
        if first.empty or second.empty:
            raise ValueError("Los activos no tienen velas con marcas temporales comunes.")
        return first, second

    @staticmethod
    def get_synthetic_data(start_date: str, end_date: str, timeframe: str = "1h") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Genera un par cointegrado reproducible exclusivamente para pruebas de la interfaz."""
        frequency = {
            "1m": "min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "h", "4h": "4h", "1d": "D",
        }.get(timeframe)
        if frequency is None:
            raise ValueError(f"Timeframe no reconocido: {timeframe}")

        dates = pd.date_range(pd.Timestamp(start_date), pd.Timestamp(end_date), freq=frequency)
        if len(dates) < 30:
            raise ValueError("El rango de prueba debe generar al menos 30 velas.")
        rng = np.random.default_rng(42)
        price_1 = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, len(dates))))
        residual = np.zeros(len(dates))
        for index in range(1, len(dates)):
            residual[index] = 0.82 * residual[index - 1] + rng.normal(0, 0.85)
        price_2 = 0.72 * price_1 + residual + 15

        def build_frame(close: np.ndarray) -> pd.DataFrame:
            high = close * (1 + rng.uniform(0.0005, 0.008, len(close)))
            low = close * (1 - rng.uniform(0.0005, 0.008, len(close)))
            return pd.DataFrame({
                "timestamp": dates,
                "open": close * (1 + rng.normal(0, 0.0015, len(close))),
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.uniform(1_000, 10_000, len(close)),
            })

        return build_frame(price_1), build_frame(price_2)
