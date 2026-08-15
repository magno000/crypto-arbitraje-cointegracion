"""Página de cribado de pares cointegrados."""

from __future__ import annotations

import itertools
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Screener | Arbitraje estadístico", page_icon="🔎", layout="wide")

from modules.cointegration import CointegrationAnalyzer
from utils.helpers import format_date, initialize_session_state, render_binance_sidebar, show_error_message
from utils.visualization import Visualizer


def align_pair(first: pd.DataFrame, second: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Alinea dos datasets descargados individualmente por sus velas comunes."""
    common = pd.Index(first["timestamp"]).intersection(pd.Index(second["timestamp"]))
    left = first[first["timestamp"].isin(common)].sort_values("timestamp").reset_index(drop=True)
    right = second[second["timestamp"].isin(common)].sort_values("timestamp").reset_index(drop=True)
    if len(left) < 30:
        raise ValueError("Menos de 30 velas comunes.")
    return left, right


def card_color(status: str) -> str:
    return {"success": "#e8f5e9", "warning": "#fff8e1", "danger": "#ffebee"}[status]


initialize_session_state()
use_synthetic = render_binance_sidebar()
st.title("Screener de pares cointegrados")
st.write("Analiza combinaciones de activos contra USDT, priorizando una cointegración estadísticamente significativa y una correlación elevada. Para limitar llamadas de red, cada activo se descarga una sola vez por ejecución.")

symbols = st.session_state.available_symbols
settings_1, settings_2, settings_3, settings_4 = st.columns(4)
with settings_1:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)
with settings_2:
    period_days = st.selectbox("Ventana histórica", [30, 60, 90], index=1, format_func=lambda value: f"{value} días")
with settings_3:
    min_correlation = st.slider("Correlación mínima", min_value=0.0, max_value=1.0, value=0.70, step=0.05)
with settings_4:
    max_pvalue = st.slider("P-value máximo", min_value=0.01, max_value=0.20, value=0.05, step=0.01)

selected_symbols = st.multiselect(
    "Activos a combinar",
    symbols,
    default=symbols[: min(6, len(symbols))],
    help="Se recomienda comenzar con cinco o seis activos líquidos; el número de pares crece de forma cuadrática.",
)
possible_pairs = len(selected_symbols) * (len(selected_symbols) - 1) // 2
st.caption(f"Se evaluarán **{possible_pairs}** combinaciones. Fuente seleccionada: **{'sintética de pruebas' if use_synthetic else 'Binance (datos reales)'}**.")
run = st.button("Ejecutar screener", type="primary")

if run:
    if len(selected_symbols) < 2:
        st.warning("Selecciona al menos dos activos.")
        st.stop()
    if len(selected_symbols) > 10:
        st.warning("Selecciona como máximo 10 activos por ejecución para respetar los límites de la API y mantener una respuesta ágil.")
        st.stop()

    end_date = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    start_date = end_date - timedelta(days=int(period_days))
    analyzer = CointegrationAnalyzer()
    visualizer = Visualizer()
    results = []
    failures = []
    progress = st.progress(0, text="Preparando descarga de velas…")

    try:
        if use_synthetic:
            pair_data = {}
        else:
            pair_data = {}
            fetcher = st.session_state.data_fetcher
            for index, symbol in enumerate(selected_symbols):
                progress.progress((index + 1) / (len(selected_symbols) + possible_pairs), text=f"Descargando {symbol}…")
                try:
                    pair_data[symbol] = fetcher.get_symbol_data(symbol, format_date(start_date), format_date(end_date), timeframe)
                except Exception as exc:
                    failures.append(f"{symbol}: {exc}")

        pairs = list(itertools.combinations(selected_symbols, 2))
        for offset, (symbol_1, symbol_2) in enumerate(pairs):
            progress.progress(
                (len(selected_symbols) + offset + 1) / (len(selected_symbols) + possible_pairs),
                text=f"Evaluando {symbol_1} / {symbol_2}…",
            )
            try:
                if use_synthetic:
                    data_1, data_2 = st.session_state.data_fetcher.get_synthetic_data(
                        format_date(start_date), format_date(end_date), timeframe
                    )
                else:
                    if symbol_1 not in pair_data or symbol_2 not in pair_data:
                        continue
                    data_1, data_2 = align_pair(pair_data[symbol_1], pair_data[symbol_2])

                stats = analyzer.analyze(data_1, data_2)
                if stats["is_cointegrated"] and stats["correlation"] >= min_correlation:
                    color = "success"
                elif stats["is_cointegrated"]:
                    color = "warning"
                else:
                    color = "danger"
                card = visualizer.create_screener_card({
                    "pair": f"{symbol_1} / {symbol_2}",
                    "pair_names": [symbol_1, symbol_2],
                    "is_cointegrated": stats["is_cointegrated"],
                    "correlation": stats["correlation"],
                    "pvalue": stats["pvalue"],
                    "hedge_ratio": stats["hedge_ratio"],
                    "color": color,
                })
                results.append({**card, "score": stats["score"]})
            except Exception as exc:
                failures.append(f"{symbol_1}/{symbol_2}: {exc}")
    finally:
        progress.empty()

    if not results:
        show_error_message("No se pudieron calcular resultados para los activos seleccionados.")
        if failures:
            with st.expander("Detalles técnicos"):
                st.code("\n".join(failures))
        st.stop()

    all_results = pd.DataFrame(results).sort_values(["pvalue", "correlation"], ascending=[True, False])
    filtered = all_results[(all_results["pvalue"].astype(float) <= max_pvalue) & (all_results["correlation"].astype(float) >= min_correlation)]
    st.success(f"Se evaluaron {len(all_results)} pares; **{len(filtered)}** cumplen los filtros de p-value ≤ {max_pvalue:.2f} y correlación ≥ {min_correlation:.2f}.")

    if filtered.empty:
        st.info("No hay pares que cumplan ambos filtros. Puedes ajustar los umbrales o ampliar la ventana histórica.")
    else:
        st.subheader("Pares candidatos")
        for row_start in range(0, len(filtered), 3):
            columns = st.columns(3)
            for column, (_, row) in zip(columns, filtered.iloc[row_start : row_start + 3].iterrows()):
                with column:
                    with st.container(border=True):
                        st.markdown(
                            f"<div style='background:{card_color(row['color'])}; padding:0.45rem 0.6rem; border-radius:0.35rem; font-weight:600'>{row['status']}</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"### {row['pair']}")
                        metric_a, metric_b = st.columns(2)
                        metric_a.metric("Correlación", row["correlation"])
                        metric_b.metric("P-value", row["pvalue"])
                        st.caption(f"Hedge ratio: **{row['hedge_ratio']}** · Score: **{row['score']:.3f}**")
                        if st.button("Abrir en analizador", key=f"open_{row['pair']}"):
                            st.session_state.selected_pair = row["pair_names"]
                            st.switch_page("pages/1_analyzer.py")

    with st.expander("Tabla completa de resultados"):
        display = all_results.rename(columns={
            "pair": "Par", "status": "Estado", "correlation": "Correlación", "pvalue": "P-value",
            "hedge_ratio": "Hedge ratio", "score": "Score",
        })[["Par", "Estado", "Correlación", "P-value", "Hedge ratio", "Score"]]
        st.dataframe(display, width="stretch", hide_index=True)
        st.download_button("Descargar resultados (CSV)", display.to_csv(index=False).encode("utf-8"), "screener_cointegracion.csv", "text/csv")

    if failures:
        st.warning(f"{len(failures)} descarga(s) o análisis no pudieron completarse.")
        with st.expander("Ver incidencias técnicas"):
            st.code("\n".join(failures))
else:
    st.info("Configura los filtros y pulsa **Ejecutar screener** para buscar candidatos.")
