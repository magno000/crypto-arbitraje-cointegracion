"""Página de documentación funcional y metodológica."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Documentación | Arbitraje estadístico", page_icon="📚", layout="wide")

from utils.helpers import initialize_session_state, render_binance_sidebar

initialize_session_state()
render_binance_sidebar()

st.title("Documentación")
st.write("Guía de uso y fundamentos del análisis de pares para investigación cuantitativa en criptoactivos.")

intro, methodology, workflow, data, limitations, references = st.tabs([
    "Introducción", "Metodología", "Flujo de trabajo", "Datos Binance", "Riesgos y límites", "Referencias",
])

with intro:
    st.header("Arbitraje estadístico de pares")
    st.markdown("""
    El arbitraje estadístico busca explotar desviaciones transitorias de una relación histórica entre activos. En un enfoque de *pairs trading*, no se intenta adivinar la dirección general del mercado. En su lugar, se construye un spread long/short y se observa si se aleja de una relación de equilibrio estimada.

    > La cointegración no es sinónimo de correlación. Dos precios pueden moverse de forma parecida en el corto plazo y, aun así, no presentar un spread estacionario y revertible a largo plazo.

    La aplicación está orientada a **investigación y formación**. Sus resultados no constituyen una recomendación de inversión, una señal ejecutable ni una garantía de rentabilidad futura.
    """)

with methodology:
    st.header("Prueba de cointegración y spread")
    st.markdown("""
    Para cada par, se estima una regresión lineal de los precios de cierre y se obtiene un **hedge ratio**. Con ese coeficiente se construye el spread:
    """)
    st.latex(r"Spread_t = P_{2,t} - \beta P_{1,t}")
    st.markdown("""
    Posteriormente se aplica la prueba de Engle–Granger a los precios. Un p-value inferior a 0,05 se etiqueta como evidencia estadística de cointegración al 5 %. El z-score móvil mide cuántas desviaciones estándar separan al spread de su media local:
    """)
    st.latex(r"Z_t = \frac{Spread_t - \mu_{t,w}}{\sigma_{t,w}}")
    st.markdown("""
    En la interfaz, un z-score negativo suficientemente extremo puede abrir una posición **long spread**; uno positivo puede abrir una **short spread**. El motor cierra la posición cuando el z-score se aproxima al umbral de salida o alcanza el stop-loss configurado.
    """)

    table = {
        "Métrica": ["P-value", "Score Engle–Granger", "Correlación", "Hedge ratio", "Vida media", "Z-score"],
        "Uso en la aplicación": [
            "Criterio principal de evidencia de cointegración.",
            "Estadístico de la prueba; se compara implícitamente mediante su p-value.",
            "Cofinancia la selección de pares, pero no demuestra cointegración por sí sola.",
            "Proporción estimada para neutralizar las patas del spread.",
            "Estimación de la velocidad media de reversión del spread.",
            "Disparador relativo de entradas, salidas y stop-loss.",
        ],
    }
    import pandas as pd
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")

with workflow:
    st.header("Uso recomendado")
    st.markdown("""
    Comienza en el **Screener** con cinco o seis activos líquidos y un timeframe coherente con tu horizonte. Ajusta el mínimo de correlación y el máximo p-value para obtener una lista manejable de candidatos. Abre los mejores pares en el **Analizador** y revisa el precio, spread, z-score y vida media. Finalmente, prueba hipótesis de entrada, salida, ventana, comisión y apalancamiento en **Backtesting**.

    Conviene separar temporalmente la fase de selección de pares y la fase de evaluación. Por ejemplo, estima el hedge ratio en una muestra de formación y evalúa las reglas en una muestra posterior. Repetir una búsqueda hasta encontrar el mejor resultado sobre la misma muestra puede producir sobreajuste.
    """)

with data:
    st.header("Datos reales de Binance")
    st.markdown("""
    La fuente predeterminada son velas OHLCV *spot* contra USDT obtenidas mediante CCXT. La API pública de Binance suele ser suficiente para consultar datos de mercado; las credenciales son opcionales. Si se proporcionan, la aplicación sólo las conserva en el estado de la sesión actual y no las escribe en archivos ni en la base de código.

    El modo de datos sintéticos está disponible únicamente para comprobar componentes visuales o flujos de trabajo cuando la red no permite consultar Binance. La interfaz muestra de manera explícita la fuente utilizada para evitar confundir una prueba simulada con un resultado de mercado.
    """)
    st.info("Para desplegar en Streamlit Cloud, almacena cualquier secreto exclusivamente en el gestor de secretos de la plataforma; nunca lo añadas al repositorio GitHub.")

with limitations:
    st.header("Riesgos y limitaciones")
    st.markdown("""
    Un p-value bajo no elimina el riesgo de ruptura de régimen. Los criptoactivos pueden cambiar rápidamente de dinámica debido a noticias, cambios de liquidez, *listings*, deslistados o eventos de mercado. El resultado también depende de la calidad de las velas, el período, el timeframe y la estabilidad del hedge ratio.

    El backtest aplica comisiones configurables y una cartera long/short con apalancamiento bruto. No modela de forma exhaustiva slippage, *funding*, costes de préstamo para posiciones cortas, límites de tamaño, latencia, liquidaciones, impuestos ni la ejecución real de órdenes. Debe considerarse una primera capa de investigación, no una simulación de producción.
    """)

with references:
    st.header("Referencias técnicas")
    st.markdown("""
    | Recurso | Utilidad |
    |---|---|
    | [Engle y Granger (1987)](https://doi.org/10.2307/1913236) | Artículo fundacional sobre cointegración y corrección del error. |
    | [Documentación de `statsmodels.coint`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html) | Implementación de la prueba de cointegración utilizada por la aplicación. |
    | [CCXT Manual](https://docs.ccxt.com/) | Referencia del conector de mercados y de las velas OHLCV. |
    | [Documentación oficial de Binance Spot API](https://developers.binance.com/docs/binance-spot-api-docs) | Límites, formato y comportamiento de los datos de Binance. |
    | [Pairs Trading, Vidyamurthy](https://onlinelibrary.wiley.com/doi/book/10.1002/9781119203362) | Referencia práctica sobre el análisis cuantitativo de pares. |
    """)

st.divider()
st.caption("Aplicación de investigación cuantitativa · Datos de mercado y resultados sujetos a disponibilidad de Binance.")
