"""Motor de backtesting para *pairs trading* con cointegración.

El motor realiza una simulación de cartera long/short autocontenida. Es adecuado
para investigación; no sustituye un entorno de ejecución ni un modelo de slippage
completo de un exchange.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd


class BacktestRunner:
    """Simula entradas y salidas de un spread con hedge ratio fijo."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def run(
        self,
        data1: pd.DataFrame,
        data2: pd.DataFrame,
        hedge_ratio: float,
        zscore_entry: float = 2.0,
        zscore_exit: float = 0.5,
        window: int = 20,
        initial_capital: float = 10_000,
        commission: float = 0.001,
        leverage: float = 1.0,
        stop_loss: float = 4.0,
        periods_per_year: int = 8_760,
    ) -> Dict:
        """Ejecuta la estrategia long/short sobre dos series OHLCV alineadas.

        Un z-score negativo abre una posición **long spread**: compra el activo 2
        y vende en corto ``hedge_ratio`` unidades del activo 1. Un z-score positivo
        ejecuta el sentido opuesto. Las comisiones se aplican en apertura y cierre.
        """
        self._validate_inputs(data1, data2, hedge_ratio, window, initial_capital, commission, leverage)
        prices_1 = data1["close"].to_numpy(dtype=float)
        prices_2 = data2["close"].to_numpy(dtype=float)
        dates = pd.to_datetime(data1["timestamp"]).to_numpy()

        spread = prices_2 - hedge_ratio * prices_1
        rolling = pd.Series(spread).rolling(window=window, min_periods=window)
        mean = rolling.mean().to_numpy()
        std = rolling.std(ddof=0).to_numpy()
        zscore = np.divide(spread - mean, std, out=np.full(len(spread), np.nan), where=std > 1e-12)

        cash = float(initial_capital)
        position = 0  # 1 long spread; -1 short spread
        quantity_1 = quantity_2 = 0.0
        entry_price_1 = entry_price_2 = 0.0
        entry_date = None
        entry_zscore = np.nan
        gross_notional = 0.0
        trades: List[Dict] = []
        equity = np.full(len(spread), initial_capital, dtype=float)
        position_series = np.zeros(len(spread), dtype=int)

        def unrealized(index: int) -> float:
            if position == 0:
                return 0.0
            return quantity_1 * (prices_1[index] - entry_price_1) + quantity_2 * (prices_2[index] - entry_price_2)

        def open_position(index: int, direction: int) -> None:
            nonlocal position, quantity_1, quantity_2, entry_price_1, entry_price_2
            nonlocal entry_date, entry_zscore, gross_notional, cash
            gross_notional = max(cash, 0.0) * leverage
            # Dos patas aproximadamente equivalentes en nocional bruto.
            leg_notional = gross_notional / 2
            quantity_2 = direction * leg_notional / prices_2[index]
            quantity_1 = -direction * hedge_ratio * leg_notional / prices_2[index]
            entry_price_1, entry_price_2 = prices_1[index], prices_2[index]
            entry_date, entry_zscore = dates[index], zscore[index]
            position = direction
            cash -= gross_notional * commission

        def close_position(index: int, reason: str) -> None:
            nonlocal position, quantity_1, quantity_2, gross_notional, cash
            gross_pnl = unrealized(index)
            exit_cost = gross_notional * commission
            net_pnl = gross_pnl - exit_cost
            cash += gross_pnl - exit_cost
            trades.append({
                "type": "long spread" if position == 1 else "short spread",
                "entry_date": pd.Timestamp(entry_date),
                "exit_date": pd.Timestamp(dates[index]),
                "entry_zscore": float(entry_zscore),
                "exit_zscore": float(zscore[index]) if np.isfinite(zscore[index]) else np.nan,
                "entry_price_1": float(entry_price_1),
                "entry_price_2": float(entry_price_2),
                "exit_price_1": float(prices_1[index]),
                "exit_price_2": float(prices_2[index]),
                "gross_notional": float(gross_notional),
                "gross_pnl": float(gross_pnl),
                "commission_paid": float(gross_notional * commission + exit_cost),
                "pnl": float(net_pnl - gross_notional * commission),
                "exit_reason": reason,
            })
            position = 0
            quantity_1 = quantity_2 = gross_notional = 0.0

        for index in range(len(spread)):
            if index < window or not np.isfinite(zscore[index]):
                equity[index] = cash + unrealized(index)
                position_series[index] = position
                continue

            if position != 0 and stop_loss > 0 and abs(zscore[index]) >= stop_loss:
                close_position(index, "stop-loss")
            elif position == 1 and zscore[index] >= -zscore_exit:
                close_position(index, "reversión a la media")
            elif position == -1 and zscore[index] <= zscore_exit:
                close_position(index, "reversión a la media")

            if position == 0:
                if zscore[index] <= -zscore_entry:
                    open_position(index, 1)
                elif zscore[index] >= zscore_entry:
                    open_position(index, -1)

            equity[index] = cash + unrealized(index)
            position_series[index] = position

        if position != 0:
            close_position(len(spread) - 1, "fin de muestra")
            equity[-1] = cash
            position_series[-1] = 0

        equity_series = pd.Series(equity).replace([np.inf, -np.inf], np.nan).ffill().fillna(initial_capital)
        running_peak = equity_series.cummax()
        drawdown = (equity_series / running_peak - 1.0).fillna(0.0)
        returns = equity_series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        sharpe = 0.0
        if len(returns) > 1 and returns.std(ddof=0) > 1e-12:
            sharpe = float(returns.mean() / returns.std(ddof=0) * np.sqrt(periods_per_year))

        realized_pnl = [trade["pnl"] for trade in trades]
        return {
            "initial_cash": float(initial_capital),
            "final_value": float(equity_series.iloc[-1]),
            "total_return": float(equity_series.iloc[-1] / initial_capital - 1),
            "sharpe_ratio": sharpe,
            "max_drawdown": float(abs(drawdown.min())),
            "num_trades": len(trades),
            "winning_pct": float(np.mean([pnl > 0 for pnl in realized_pnl])) if realized_pnl else 0.0,
            "equity_curve": equity_series.tolist(),
            "drawdown_curve": drawdown.abs().tolist(),
            "trades": trades,
            "dates": [pd.Timestamp(value).isoformat() for value in dates],
            "spread": spread.tolist(),
            "zscore": zscore.tolist(),
            "position": position_series.tolist(),
        }

    @staticmethod
    def _validate_inputs(
        data1: pd.DataFrame,
        data2: pd.DataFrame,
        hedge_ratio: float,
        window: int,
        initial_capital: float,
        commission: float,
        leverage: float,
    ) -> None:
        required = {"timestamp", "close"}
        if not required.issubset(data1.columns) or not required.issubset(data2.columns):
            raise ValueError("Los datos deben contener las columnas timestamp y close.")
        if len(data1) != len(data2) or len(data1) <= window:
            raise ValueError("Las series deben estar alineadas y contener más velas que la ventana de cálculo.")
        if not np.isfinite(hedge_ratio) or hedge_ratio <= 0:
            raise ValueError("El hedge ratio debe ser un valor positivo y finito.")
        if initial_capital <= 0 or leverage <= 0:
            raise ValueError("El capital inicial y el apalancamiento deben ser positivos.")
        if not 0 <= commission < 1:
            raise ValueError("La comisión debe expresarse como un decimal entre 0 y 1.")
