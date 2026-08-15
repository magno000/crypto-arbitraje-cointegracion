"""Portada de la aplicación de arbitraje estadístico con cointegración."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="Arbitraje estadístico | Cripto",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.helpers import initialize_session_state, render_binance_sidebar

initialize_session_state()
use_synthetic = render_binance_sidebar()

st.markdown(
    """
    <style>
    .hero {padding: 1.35rem 1.5rem; border: 1px solid rgba(49, 51, 63, .18); border-radius: .75rem;
           background: linear-gradient(110deg, rgba(16, 185, 129, .13), rgba(59, 130, 246, .10));}
    .hero h1 {margin: 0 0 .5rem 0;}
    .hero p {font-size: 1.05rem; margin-bottom: 0;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero">
      <h1>Arbitraje estadístico con cointegración</h1>
      <p>Plataforma de investigación para encontrar, analizar y evaluar estrategias long/short sobre pares de criptomonedas.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

source_col, status_col, symbols_col = st.columns(3)
source_col.metric("Fuente activa", "Prueba sintética" if use_synthetic else "Binance spot")
status_col.metric("Conexión", "Disponible" if st.session_state.connection_status else "Pendiente / no disponible")
symbols_col.metric("Mercados cargados", len(st.session_state.available_symbols))

st.subheader("Flujo de investigación")
step_1, step_2, step_3 = st.columns(3)
with step_1:
    st.markdown("### 1. Screener")
    st.write("Examina combinaciones de activos y filtra por correlación y p-value.")
    if st.button("Abrir screener", use_container_width=True, type="primary"):
        st.switch_page("pages/2_screener.py")
with step_2:
    st.markdown("### 2. Analizador")
    st.write("Revisa precios, spread, z-score, hedge ratio y vida media del candidato.")
    if st.button("Abrir analizador", use_container_width=True):
        st.switch_page("pages/1_analyzer.py")
with step_3:
    st.markdown("### 3. Backtest")
    st.write("Simula reglas de entrada y salida, incluyendo comisión y apalancamiento.")
    if st.button("Abrir backtest", use_container_width=True):
        st.switch_page("pages/3_backtest.py")

st.divider()
left, right = st.columns([1.2, 1])
with left:
    st.subheader("Qué incorpora la aplicación")
    st.markdown("""
    La solución está organizada en módulos de datos, cointegración, señales, backtesting y visualización. La navegación multipágina separa el análisis individual, el screener, el backtest y la documentación, evitando un archivo monolítico y facilitando el mantenimiento en VS Code o GitHub.

    La fuente principal es Binance mediante CCXT. El modo sintético es una alternativa explícita para pruebas de interfaz, no un sustituto silencioso de una descarga fallida. Si Binance no está disponible en la red de despliegue, se conserva una lista de símbolos para que la interfaz siga siendo navegable, pero las acciones de análisis real mostrarán el error correspondiente.
    """)
with right:
    st.subheader("Antes de interpretar resultados")
    st.markdown("""
    La cointegración es una propiedad histórica y puede romperse. Contrasta los resultados fuera de muestra, incorpora costes operativos adicionales y valida la liquidez antes de considerar cualquier implementación real.

    > **Aviso:** Esta aplicación es educativa y de investigación. No es asesoramiento financiero ni ejecuta órdenes de trading.
    """)

st.info("También puedes usar el menú de páginas de Streamlit en la barra lateral para navegar por cada módulo.")
st.page_link("pages/4_documentation.py", label="Consultar documentación y referencias", icon="📚")
