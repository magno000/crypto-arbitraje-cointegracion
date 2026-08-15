"""Adaptador Backtrader para la estrategia de pares cointegrados.

Se mantiene separado del motor vectorial para permitir comparar ambos enfoques.
"""

from __future__ import annotations

from typing import Dict, List

import backtrader as bt
import numpy as np
import pandas as pd


class _PairsCointegrationStrategy(bt.Strategy):
    params = (
        ("hedge_ratio", 1.0),
        ("zscore_entry", 2.0),
        ("zscore_exit", 0.5),
        ("window", 30),
        ("leverage", 1.0),
        ("stop_loss", 4.0),
        ("commission", 0.001),
    )

    def __init__(self) -> None:
        self.spread = self.datas[1].close - self.p.hedge_ratio * self.datas[0].close
        self.mean = bt.indicators.SimpleMovingAverage(self.spread, period=self.p.window)
        self.std = bt.indicators.StandardDeviation(self.spread, period=self.p.window)
        self.zscore = (self.spread - self.mean) / self.std
        self.direction = 0
        self.quantity_1 = 0.0
        self.quantity_2 = 0.0
        self.entry_price_1 = 0.0
        self.entry_price_2 = 0.0
        self.entry_date = None
        self.entry_zscore = np.nan
        self.gross_notional = 0.0
        self.trades: List[Dict] = []
        self.equity_dates: List[pd.Timestamp] = []
        self.equity_values: List[float] = []

    def _record_equity(self) -> None:
        timestamp = pd.Timestamp(self.datas[0].datetime.datetime(0)).tz_localize(None)
        self.equity_dates.append(timestamp)
        self.equity_values.append(float(self.broker.getvalue()))

    def _open_spread(self, direction: int) -> None:
        price_1 = float(self.datas[0].close[0])
        price_2 = float(self.datas[1].close[0])
        self.gross_notional = max(float(self.broker.getvalue()), 0.0) * self.p.leverage
        leg_notional = self.gross_notional / 2
        self.quantity_2 = direction * leg_notional / price_2
        self.quantity_1 = -direction * self.p.hedge_ratio * leg_notional / price_2
        self.entry_price_1, self.entry_price_2 = price_1, price_2
        self.entry_date = pd.Timestamp(self.datas[0].datetime.datetime(0)).tz_localize(None)
        self.entry_zscore = float(self.zscore[0])
        self.direction = direction
        # Spread = P2 - beta * P1: long spread compra P2 y vende beta*P1.
        self.order_target_size(data=self.datas[0], target=self.quantity_1)
        self.order_target_size(data=self.datas[1], target=self.quantity_2)

    def _close_spread(self, reason: str) -> None:
        if self.direction == 0:
            return
        price_1 = float(self.datas[0].close[0])
        price_2 = float(self.datas[1].close[0])
        gross_pnl = self.quantity_1 * (price_1 - self.entry_price_1) + self.quantity_2 * (price_2 - self.entry_price_2)
        estimated_commission = self.gross_notional * self.p.commission * 2
        exit_timestamp = pd.Timestamp(self.datas[0].datetime.datetime(0)).tz_localize(None)
        self.trades.append({
            "type": "long spread" if self.direction == 1 else "short spread",
            "entry_date": self.entry_date,
            "exit_date": exit_timestamp,
            "entry_zscore": float(self.entry_zscore),
            "exit_zscore": float(self.zscore[0]),
            "entry_price_1": self.entry_price_1,
            "entry_price_2": self.entry_price_2,
            "exit_price_1": price_1,
            "exit_price_2": price_2,
            "gross_notional": self.gross_notional,
            "gross_pnl": gross_pnl,
            "commission_paid": estimated_commission,
            "pnl": gross_pnl - estimated_commission,
            "exit_reason": reason,
        })
        self.order_target_size(data=self.datas[0], target=0)
        self.order_target_size(data=self.datas[1], target=0)
        self.direction = 0
        self.quantity_1 = self.quantity_2 = self.gross_notional = 0.0

    def next(self) -> None:
        z_value = float(self.zscore[0])
        if np.isfinite(z_value):
            if self.direction != 0 and self.p.stop_loss > 0 and abs(z_value) >= self.p.stop_loss:
                self._close_spread("stop-loss")
            elif self.direction == 1 and z_value >= -self.p.zscore_exit:
                self._close_spread("reversión a la media")
            elif self.direction == -1 and z_value <= self.p.zscore_exit:
                self._close_spread("reversión a la media")

            if self.direction == 0:
                if z_value <= -self.p.zscore_entry:
                    self._open_spread(1)
                elif z_value >= self.p.zscore_entry:
                    self._open_spread(-1)

        # El modo COC permite que esta orden de cierre sea ejecutable en la última vela.
        if len(self.datas[0]) == self.datas[0].buflen() and self.direction != 0:
            self._close_spread("fin de muestra")
        self._record_equity()


class BacktraderPairsRunner:
    """Ejecuta la estrategia de pares usando ``backtrader.Cerebro``."""

    @staticmethod
    def run(
        data_1: pd.DataFrame,
        data_2: pd.DataFrame,
        hedge_ratio: float,
        zscore_entry: float = 2.0,
        zscore_exit: float = 0.5,
        window: int = 30,
        initial_capital: float = 10_000,
        commission: float = 0.001,
        leverage: float = 1.0,
        stop_loss: float = 4.0,
        periods_per_year: int = 8_760,
    ) -> Dict:
        if len(data_1) != len(data_2) or len(data_1) <= window:
            raise ValueError("Las series deben estar alineadas y superar la ventana de cálculo.")
        if hedge_ratio <= 0 or initial_capital <= 0 or leverage <= 0:
            raise ValueError("Hedge ratio, capital y apalancamiento deben ser positivos.")

        def feed_frame(frame: pd.DataFrame) -> pd.DataFrame:
            prepared = frame.copy()
            prepared["timestamp"] = pd.to_datetime(prepared["timestamp"])
            prepared = prepared.set_index("timestamp")
            return prepared[["open", "high", "low", "close", "volume"]]

        cerebro = bt.Cerebro(stdstats=False)
        cerebro.broker.setcash(initial_capital)
        cerebro.broker.setcommission(commission=commission)
        cerebro.broker.set_coc(True)
        cerebro.adddata(bt.feeds.PandasData(dataname=feed_frame(data_1)), name="asset_1")
        cerebro.adddata(bt.feeds.PandasData(dataname=feed_frame(data_2)), name="asset_2")
        cerebro.addstrategy(
            _PairsCointegrationStrategy,
            hedge_ratio=float(hedge_ratio),
            zscore_entry=float(zscore_entry),
            zscore_exit=float(zscore_exit),
            window=int(window),
            leverage=float(leverage),
            stop_loss=float(stop_loss),
            commission=float(commission),
        )
        strategy = cerebro.run()[0]

        dates = pd.to_datetime(data_1["timestamp"]).reset_index(drop=True)
        ledger = pd.Series(strategy.equity_values, index=pd.DatetimeIndex(strategy.equity_dates))
        equity = ledger.reindex(pd.DatetimeIndex(dates), method="ffill").fillna(initial_capital)
        if len(equity):
            equity.iloc[-1] = float(cerebro.broker.getvalue())
        drawdown = (equity / equity.cummax() - 1).fillna(0.0)
        returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        sharpe = 0.0
        if len(returns) > 1 and returns.std(ddof=0) > 1e-12:
            sharpe = float(returns.mean() / returns.std(ddof=0) * np.sqrt(periods_per_year))

        trade_pnls = [trade["pnl"] for trade in strategy.trades]
        return {
            "initial_cash": float(initial_capital),
            "final_value": float(equity.iloc[-1]),
            "total_return": float(equity.iloc[-1] / initial_capital - 1),
            "sharpe_ratio": sharpe,
            "max_drawdown": float(abs(drawdown.min())),
            "num_trades": len(strategy.trades),
            "winning_pct": float(np.mean([pnl > 0 for pnl in trade_pnls])) if trade_pnls else 0.0,
            "equity_curve": equity.tolist(),
            "drawdown_curve": drawdown.abs().tolist(),
            "trades": strategy.trades,
            "dates": [pd.Timestamp(value).isoformat() for value in dates],
            "engine": "backtrader",
        }
