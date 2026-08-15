"""Página de análisis individual de pares cointegrados."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Analizador | Arbitraje estadístico", page_icon="📊", layout="wide")

from modules.cointegration import CointegrationAnalyzer
from modules.signals import SignalGenerator
from utils.helpers import (
    calculate_half_life,
    default_pair,
    format_date,
    format_number,
    initialize_session_state,
    render_binance_sidebar,
    show_error_message,
)
from utils.visualization import Visualizer

initialize_session_state()
use_synthetic = render_binance_sidebar()

st.title("Analizador de pares cointegrados")
st.write("Examina la relación de equilibrio entre dos criptoactivos *spot* contra USDT mediante la prueba de Engle–Granger. El análisis usa velas reales de Binance salvo que actives expresamente el modo de pruebas.")

symbols = st.session_state.available_symbols
if len(symbols) < 2:
    st.error("No hay suficientes símbolos disponibles para formar un par.")
    st.stop()

first_default, second_default = default_pair(symbols)
control_1, control_2, control_3, control_4 = st.columns([1.15, 1.15, 0.7, 0.9])
with control_1:
    symbol_1 = st.selectbox("Primer activo", symbols, index=first_default)
with control_2:
    symbol_2 = st.selectbox("Segundo activo", symbols, index=second_default)
with control_3:
    timeframe = st.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=2)
with control_4:
    z_window = st.number_input("Ventana z-score", min_value=10, max_value=200, value=30, step=5)

end_default = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
start_default = end_default - pd.DateOffset(days=60)
date_1, date_2, action = st.columns([1, 1, 0.8])
with date_1:
    start_date = st.date_input("Inicio", value=start_default.date(), max_value=end_default.date())
with date_2:
    end_date = st.date_input("Fin", value=end_default.date(), min_value=start_date, max_value=end_default.date())
with action:
    st.write("")
    st.write("")
    analyze = st.button("Analizar par", type="primary", width="stretch")

if analyze:
    if symbol_1 == symbol_2:
        st.warning("Selecciona dos activos diferentes.")
        st.stop()

    with st.spinner("Descargando y procesando velas…"):
        try:
            fetcher = st.session_state.data_fetcher
            if use_synthetic:
                data_1, data_2 = fetcher.get_synthetic_data(format_date(start_date), format_date(end_date), timeframe)
                source_label = "Datos sintéticos de prueba"
            else:
                data_1, data_2 = fetcher.get_historical_data(
                    symbol_1, symbol_2, format_date(start_date), format_date(end_date), timeframe
                )
                source_label = "Velas reales de Binance"

            analysis = CointegrationAnalyzer().analyze(data_1, data_2)
            signals = SignalGenerator().generate_signals(data_1, data_2, analysis["hedge_ratio"], window=int(z_window))
            latest_zscore = signals["zscore"].dropna().iloc[-1] if signals["zscore"].notna().any() else float("nan")
            half_life = calculate_half_life(signals["spread"])
            st.session_state.selected_pair = [symbol_1, symbol_2]
        except Exception as exc:
            show_error_message(f"No fue posible completar el análisis: {exc}")
            if not use_synthetic:
                st.info("Comprueba la conectividad con Binance desde la barra lateral o activa el modo sintético únicamente para comprobar la interfaz.")
            st.stop()

    st.success(f"{source_label}. Se analizaron {len(data_1):,} velas comunes entre {data_1['timestamp'].min():%Y-%m-%d %H:%M} y {data_1['timestamp'].max():%Y-%m-%d %H:%M} UTC.")

    metrics_1, metrics_2, metrics_3, metrics_4, metrics_5, metrics_6 = st.columns(6)
    metrics_1.metric("Cointegración", "Sí" if analysis["is_cointegrated"] else "No", help="Resultado con umbral p-value < 0,05.")
    metrics_2.metric("P-value", format_number(analysis["pvalue"], 4))
    metrics_3.metric("Score Engle–Granger", format_number(analysis["score"], 3))
    metrics_4.metric("Correlación", format_number(analysis["correlation"], 3))
    metrics_5.metric("Hedge ratio", format_number(analysis["hedge_ratio"], 4))
    metrics_6.metric("Z-score actual", format_number(latest_zscore, 2))

    details_1, details_2, details_3 = st.columns(3)
    details_1.caption(f"**Período:** {data_1['timestamp'].min():%d/%m/%Y} – {data_1['timestamp'].max():%d/%m/%Y}")
    details_2.caption(f"**Timeframe:** {timeframe} · **Ventana:** {int(z_window)} velas")
    details_3.caption(f"**Vida media estimada:** {format_number(half_life, 1)} velas")

    visualizer = Visualizer()
    st.subheader("Precios de los activos")
    st.plotly_chart(visualizer.create_price_chart(data_1, data_2, symbol_1, symbol_2), width="stretch")

    st.subheader("Spread y z-score")
    st.plotly_chart(visualizer.create_pair_analysis_chart(signals, symbol_1, symbol_2), width="stretch")

    with st.expander("Detalle estadístico y datos utilizados"):
        statistics = pd.DataFrame([{
            "Par": f"{symbol_1} / {symbol_2}",
            "Fuente": source_label,
            "Velas": len(data_1),
            "P-value": analysis["pvalue"],
            "Score": analysis["score"],
            "Crítico 1 %": analysis["critical_value_1pct"],
            "Crítico 5 %": analysis["critical_value_5pct"],
            "Crítico 10 %": analysis["critical_value_10pct"],
            "Correlación": analysis["correlation"],
            "Hedge ratio": analysis["hedge_ratio"],
            "Vida media (velas)": half_life,
        }])
        st.dataframe(statistics, width="stretch", hide_index=True)
        st.download_button(
            "Descargar serie del análisis (CSV)",
            signals.to_csv(index=False).encode("utf-8"),
            file_name=f"analisis_{symbol_1.replace('/', '-')}_{symbol_2.replace('/', '-')}.csv",
            mime="text/csv",
        )
else:
    st.info("Selecciona los activos, el rango temporal y el timeframe; después pulsa **Analizar par**.")
