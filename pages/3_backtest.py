"""Página de backtesting para la estrategia de pares cointegrados."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="Backtest | Arbitraje estadístico", page_icon="📈", layout="wide")

from modules.backtest import BacktestRunner
from modules.backtrader_engine import BacktraderPairsRunner
from modules.cointegration import CointegrationAnalyzer
from modules.signals import SignalGenerator
from utils.helpers import (
    default_pair,
    format_date,
    initialize_session_state,
    parse_timeframe,
    render_binance_sidebar,
    show_error_message,
)
from utils.visualization import Visualizer

initialize_session_state()
use_synthetic = render_binance_sidebar()
st.title("Backtesting de la estrategia de cointegración")
st.write("Simula una cartera neutral al mercado: cuando el spread se desvía, abre posiciones long/short compensadas según el hedge ratio estimado y las cierra al revertir hacia su media.")
engine = st.radio(
    "Motor de simulación",
    ["Backtrader", "Vectorial propio"],
    horizontal=True,
    help="Backtrader ejecuta la estrategia sobre Cerebro; el motor vectorial permite una simulación rápida y transparente para comparar hipótesis.",
)

symbols = st.session_state.available_symbols
if len(symbols) < 2:
    st.error("No hay suficientes símbolos disponibles para ejecutar un backtest.")
    st.stop()

first_default, second_default = default_pair(symbols)
asset_1, asset_2, timeframe_control = st.columns(3)
with asset_1:
    symbol_1 = st.selectbox("Primer activo", symbols, index=first_default, key="backtest_symbol_1")
with asset_2:
    symbol_2 = st.selectbox("Segundo activo", symbols, index=second_default, key="backtest_symbol_2")
with timeframe_control:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1, key="backtest_timeframe")

end_default = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
start_default = end_default - pd.DateOffset(days=120)
date_1, date_2 = st.columns(2)
with date_1:
    start_date = st.date_input("Inicio del backtest", value=start_default.date(), max_value=end_default.date())
with date_2:
    end_date = st.date_input("Fin del backtest", value=end_default.date(), min_value=start_date, max_value=end_default.date())

st.subheader("Parámetros de la estrategia")
strategy_1, strategy_2, strategy_3, strategy_4 = st.columns(4)
with strategy_1:
    z_entry = st.slider("Entrada |z-score|", min_value=1.0, max_value=4.0, value=2.0, step=0.1)
with strategy_2:
    z_exit = st.slider("Salida |z-score|", min_value=0.0, max_value=1.5, value=0.5, step=0.1)
with strategy_3:
    window = st.number_input("Ventana z-score", min_value=10, max_value=200, value=30, step=5)
with strategy_4:
    stop_loss = st.slider("Stop-loss |z-score|", min_value=0.0, max_value=6.0, value=4.0, step=0.25, help="El valor 0 desactiva este umbral.")

st.subheader("Capital y costes")
capital_1, capital_2, capital_3 = st.columns(3)
with capital_1:
    initial_capital = st.number_input("Capital inicial (USDT)", min_value=1_000, max_value=1_000_000, value=10_000, step=1_000)
with capital_2:
    commission_pct = st.number_input("Comisión por lado (%)", min_value=0.0, max_value=1.0, value=0.10, step=0.01)
with capital_3:
    leverage = st.slider("Apalancamiento bruto", min_value=1.0, max_value=5.0, value=1.0, step=0.5)

run = st.button("Ejecutar backtest", type="primary")

if run:
    if symbol_1 == symbol_2:
        st.warning("Selecciona dos activos distintos.")
        st.stop()

    with st.spinner("Descargando velas y ejecutando la simulación…"):
        try:
            fetcher = st.session_state.data_fetcher
            if use_synthetic:
                data_1, data_2 = fetcher.get_synthetic_data(format_date(start_date), format_date(end_date), timeframe)
                source = "Datos sintéticos de prueba"
            else:
                data_1, data_2 = fetcher.get_historical_data(
                    symbol_1, symbol_2, format_date(start_date), format_date(end_date), timeframe
                )
                source = "Velas reales de Binance"

            cointegration = CointegrationAnalyzer().analyze(data_1, data_2)
            periods_per_year = int((365 * 24 * 60) / parse_timeframe(timeframe))
            runner = BacktraderPairsRunner() if engine == "Backtrader" else BacktestRunner()
            results = runner.run(
                data_1,
                data_2,
                hedge_ratio=cointegration["hedge_ratio"],
                zscore_entry=float(z_entry),
                zscore_exit=float(z_exit),
                window=int(window),
                initial_capital=float(initial_capital),
                commission=float(commission_pct) / 100,
                leverage=float(leverage),
                stop_loss=float(stop_loss),
                periods_per_year=periods_per_year,
            )
            signals = SignalGenerator().generate_signals(
                data_1, data_2, cointegration["hedge_ratio"], int(window), float(z_entry), float(z_exit)
            )
            st.session_state.selected_pair = [symbol_1, symbol_2]
        except Exception as exc:
            show_error_message(f"No fue posible ejecutar el backtest: {exc}")
            if not use_synthetic:
                st.info("La descarga real de Binance no se completó. Revisa la conexión de la barra lateral; el modo sintético queda disponible sólo para pruebas de interfaz.")
            st.stop()

    if not cointegration["is_cointegrated"]:
        st.warning(f"El test no confirma cointegración al 5 % (p-value {cointegration['pvalue']:.4f}). Interpreta este backtest con especial cautela.")
    else:
        st.success(f"{source}. El par supera el test de cointegración con p-value {cointegration['pvalue']:.4f}.")

    metric_1, metric_2, metric_3, metric_4, metric_5 = st.columns(5)
    metric_1.metric("Retorno total", f"{results['total_return'] * 100:.2f}%")
    metric_2.metric("Valor final", f"{results['final_value']:,.2f} USDT")
    metric_3.metric("Sharpe anualizado", f"{results['sharpe_ratio']:.2f}")
    metric_4.metric("Drawdown máximo", f"{results['max_drawdown'] * 100:.2f}%")
    metric_5.metric("Operaciones", str(results["num_trades"]), f"Acierto: {results['winning_pct'] * 100:.1f}%")

    st.caption(
        f"**Par:** {symbol_1} / {symbol_2} · **Timeframe:** {timeframe} · **Ventana:** {int(window)} velas · "
        f"**Hedge ratio:** {cointegration['hedge_ratio']:.4f} · **Comisión por lado:** {commission_pct:.2f}% · "
        f"**Motor:** {results.get('engine', 'vectorial propio')}"
    )

    visualizer = Visualizer()
    equity_figure, drawdown_figure, distribution_figure = visualizer.create_backtest_charts(results, symbol_1, symbol_2)
    st.subheader("Curva de equity")
    st.plotly_chart(equity_figure, width="stretch")
    drawdown_column, distribution_column = st.columns(2)
    with drawdown_column:
        st.plotly_chart(drawdown_figure, width="stretch")
    with distribution_column:
        st.plotly_chart(distribution_figure, width="stretch")

    st.subheader("Spread y señales generadas")
    st.plotly_chart(visualizer.create_pair_analysis_chart(signals, symbol_1, symbol_2), width="stretch")

    with st.expander("Operaciones y exportación"):
        trades = pd.DataFrame(results["trades"])
        if trades.empty:
            st.info("La estrategia no generó operaciones con estos parámetros.")
        else:
            st.dataframe(trades, width="stretch", hide_index=True)
            st.download_button(
                "Descargar operaciones (CSV)",
                trades.to_csv(index=False).encode("utf-8"),
                file_name=f"backtest_{symbol_1.replace('/', '-')}_{symbol_2.replace('/', '-')}.csv",
                mime="text/csv",
            )
else:
    st.info("Define el par y los parámetros de entrada/salida para ejecutar una simulación reproducible.")
