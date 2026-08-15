"""Utilidades compartidas de la interfaz Streamlit."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from modules.data_fetcher import DEFAULT_SYMBOLS, DataFetcher

logger = logging.getLogger(__name__)


def format_date(value: Any) -> str:
    """Convierte una fecha de interfaz en el formato ``YYYY-MM-DD``."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def parse_timeframe(timeframe: str) -> int:
    """Devuelve la duración de un timeframe de Binance en minutos."""
    units = {"m": 1, "h": 60, "d": 1_440, "w": 10_080}
    try:
        return int(timeframe[:-1]) * units[timeframe[-1]]
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError(f"Timeframe no reconocido: {timeframe}") from exc


def calculate_zscore(spread: pd.Series, window: int = 20) -> pd.Series:
    """Calcula el z-score móvil del spread sin dividir por desviaciones nulas."""
    mean = spread.rolling(window=window, min_periods=window).mean()
    std = spread.rolling(window=window, min_periods=window).std(ddof=0)
    return (spread - mean).div(std.where(std > 1e-12))


def calculate_half_life(spread: pd.Series) -> float:
    """Estima la vida media de reversión del spread mediante una regresión AR(1)."""
    series = pd.Series(spread).dropna()
    if len(series) < 3:
        return float("nan")
    lagged = series.shift(1).dropna()
    delta = series.diff().dropna()
    coefficient = np.polyfit(lagged.to_numpy(), delta.to_numpy(), 1)[0]
    return float(-np.log(2) / coefficient) if coefficient < 0 else float("nan")


def format_number(value: Any, decimals: int = 2) -> str:
    """Formatea valores numéricos y conserva los valores ausentes de forma legible."""
    try:
        number = float(value)
        return "—" if not np.isfinite(number) else f"{number:,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def get_session_state(key: str, default: Any = None) -> Any:
    """Lee el estado de sesión sin crear acoplamiento con páginas concretas."""
    return st.session_state.get(key, default)


def show_error_message(message: str) -> None:
    """Presenta y registra un error de ejecución."""
    logger.error(message)
    st.error(message)


def initialize_session_state() -> None:
    """Inicializa un único cliente de datos y valores de interfaz compartidos."""
    defaults: Dict[str, Any] = {
        "api_key": "",
        "api_secret": "",
        "connection_status": False,
        "connection_error": None,
        "available_symbols": DEFAULT_SYMBOLS.copy(),
        "selected_pair": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "data_fetcher" not in st.session_state or st.session_state.data_fetcher is None:
        fetcher = DataFetcher(st.session_state.api_key, st.session_state.api_secret)
        st.session_state.data_fetcher = fetcher
        st.session_state.connection_status = fetcher.is_connected
        st.session_state.connection_error = fetcher.connection_error
        st.session_state.available_symbols = fetcher.get_available_symbols()

    if "use_synthetic_data" not in st.session_state:
        # La opción no se activa de manera automática: los datos reales son la fuente por defecto.
        st.session_state.use_synthetic_data = False


def connect_binance(api_key: str = "", api_secret: str = "") -> bool:
    """Crea un cliente de Binance y actualiza el estado de sesión compartido."""
    api_key, api_secret = api_key.strip(), api_secret.strip()
    if bool(api_key) != bool(api_secret):
        st.session_state.connection_status = False
        st.session_state.connection_error = "Introduce tanto la API Key como el API Secret, o deja ambos vacíos para usar la API pública."
        return False

    fetcher = DataFetcher(api_key or None, api_secret or None)
    st.session_state.api_key = api_key
    st.session_state.api_secret = api_secret
    st.session_state.data_fetcher = fetcher
    st.session_state.connection_status = fetcher.test_connection()
    st.session_state.connection_error = fetcher.connection_error
    st.session_state.available_symbols = fetcher.get_available_symbols()
    return st.session_state.connection_status


def render_binance_sidebar() -> bool:
    """Renderiza la configuración común y devuelve si se eligió el modo sintético explícito."""
    initialize_session_state()
    with st.sidebar:
        st.header("Fuente de datos")
        st.caption("Las velas históricas proceden de Binance a través de su API pública. Las credenciales son opcionales y sólo viven en esta sesión.")
        with st.form("binance_connection_form", clear_on_submit=False):
            api_key = st.text_input("API Key (opcional)", value=st.session_state.api_key, type="password")
            api_secret = st.text_input("API Secret (opcional)", value=st.session_state.api_secret, type="password")
            connect_clicked = st.form_submit_button("Conectar / actualizar")
        if connect_clicked:
            with st.spinner("Comprobando la conexión con Binance..."):
                if connect_binance(api_key, api_secret):
                    st.success("Conexión con Binance disponible.")
                else:
                    st.warning(st.session_state.connection_error or "No se pudo conectar con Binance.")

        if st.session_state.connection_status:
            st.success("Estado: datos reales de Binance disponibles")
        else:
            st.warning("Estado: Binance no disponible en este entorno")
            if st.session_state.connection_error:
                st.caption(st.session_state.connection_error)

        st.checkbox(
            "Usar datos sintéticos para pruebas",
            key="use_synthetic_data",
            help="Sólo activa datos simulados si deseas probar la interfaz sin consultar Binance.",
        )
        st.divider()
        st.caption("Esta herramienta es de investigación educativa. No constituye una recomendación de inversión.")
    return bool(st.session_state.use_synthetic_data)


def default_pair(symbols: list[str]) -> Tuple[int, int]:
    """Devuelve índices seguros para el par almacenado por el screener o el par inicial."""
    if len(symbols) < 2:
        raise ValueError("Se requieren al menos dos símbolos disponibles.")
    selected = st.session_state.get("selected_pair")
    if selected and len(selected) == 2 and selected[0] in symbols and selected[1] in symbols:
        return symbols.index(selected[0]), symbols.index(selected[1])
    return 0, 1


def get_color_by_value(value: float, thresholds: Dict[float, str]) -> str:
    """Devuelve el color asociado al primer umbral alcanzado."""
    for threshold in sorted(thresholds):
        if value <= threshold:
            return thresholds[threshold]
    return thresholds[max(thresholds)]
