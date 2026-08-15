import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import logging

class Visualizer:
    """
    Clase para generar visualizaciones para el análisis de pares cointegrados en Streamlit.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_price_chart(self, data1, data2, symbol1, symbol2):
        """
        Crea un gráfico de precios normalizados para dos activos.
        
        Args:
            data1 (DataFrame): DataFrame con datos del primer activo
            data2 (DataFrame): DataFrame con datos del segundo activo
            symbol1 (str): Símbolo del primer activo
            symbol2 (str): Símbolo del segundo activo
            
        Returns:
            plotly.graph_objects.Figure: Figura de Plotly con el gráfico
        """
        try:
            # Normalizar precios para mejor visualización
            norm_price1 = data1['close'] / data1['close'].iloc[0]
            norm_price2 = data2['close'] / data2['close'].iloc[0]
            
            # Crear figura
            fig = go.Figure()
            
            # Añadir líneas de precios
            fig.add_trace(
                go.Scatter(
                    x=data1['timestamp'],
                    y=norm_price1,
                    mode='lines',
                    name=symbol1,
                    line=dict(color='blue')
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data2['timestamp'],
                    y=norm_price2,
                    mode='lines',
                    name=symbol2,
                    line=dict(color='orange')
                )
            )
            
            # Actualizar layout
            fig.update_layout(
                title=f'Precios Normalizados: {symbol1} vs {symbol2}',
                xaxis_title='Fecha',
                yaxis_title='Precio Normalizado',
                height=500,
                template='plotly_white'
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creando gráfico de precios: {str(e)}")
            raise
    
    def create_pair_analysis_chart(self, signals, symbol1, symbol2):
        """
        Crea un gráfico combinado para el análisis de pares.
        
        Args:
            signals (DataFrame): DataFrame con señales de trading
            symbol1 (str): Símbolo del primer activo
            symbol2 (str): Símbolo del segundo activo
            
        Returns:
            plotly.graph_objects.Figure: Figura de Plotly con el gráfico
        """
        try:
            # Crear subplots
            fig = make_subplots(
                rows=2, 
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=(
                    'Spread',
                    'Z-Score con Señales'
                ),
                row_heights=[0.5, 0.5]
            )
            
            # Gráfico 1: Spread
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=signals['spread'],
                    mode='lines',
                    name='Spread',
                    line=dict(color='green')
                ),
                row=1, col=1
            )
            
            # Añadir línea de media móvil del spread
            spread_mean = pd.Series(signals['spread']).rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=spread_mean,
                    mode='lines',
                    name='Media Móvil (20)',
                    line=dict(color='red', dash='dash')
                ),
                row=1, col=1
            )
            
            # Gráfico 2: Z-Score con señales
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=signals['zscore'],
                    mode='lines',
                    name='Z-Score',
                    line=dict(color='purple')
                ),
                row=2, col=1
            )
            
            # Añadir líneas de umbral para z-score
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=[2] * len(signals),
                    mode='lines',
                    name='Umbral Superior',
                    line=dict(color='red', dash='dash')
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=[-2] * len(signals),
                    mode='lines',
                    name='Umbral Inferior',
                    line=dict(color='red', dash='dash')
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=signals['timestamp'],
                    y=[0] * len(signals),
                    mode='lines',
                    name='Línea Cero',
                    line=dict(color='gray', dash='dash')
                ),
                row=2, col=1
            )
            
            # Añadir señales de compra y venta
            buy_signals = signals[signals['signal'] == 1]
            sell_signals = signals[signals['signal'] == -1]
            
            if not buy_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_signals['timestamp'],
                        y=buy_signals['zscore'],
                        mode='markers',
                        name='Compra',
                        marker=dict(
                            color='green',
                            size=10,
                            symbol='triangle-up'
                        )
                    ),
                    row=2, col=1
                )
            
            if not sell_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_signals['timestamp'],
                        y=sell_signals['zscore'],
                        mode='markers',
                        name='Venta',
                        marker=dict(
                            color='red',
                            size=10,
                            symbol='triangle-down'
                        )
                    ),
                    row=2, col=1
                )
            
            # Actualizar layout
            fig.update_layout(
                title=f'Análisis de Par: {symbol1} vs {symbol2}',
                height=800,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                template='plotly_white'
            )
            
            # Actualizar ejes
            fig.update_xaxes(title_text="Fecha", row=2, col=1)
            fig.update_yaxes(title_text="Spread", row=1, col=1)
            fig.update_yaxes(title_text="Z-Score", row=2, col=1)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creando gráfico de análisis de pares: {str(e)}")
            raise
    
    def create_backtest_charts(self, backtest_results, symbol1, symbol2):
        """
        Crea gráficos para visualizar los resultados del backtest.
        
        Args:
            backtest_results (dict): Resultados del backtest
            symbol1 (str): Símbolo del primer activo
            symbol2 (str): Símbolo del segundo activo
            
        Returns:
            tuple: (equity_fig, drawdown_fig, trade_dist_fig)
        """
        try:
            # Convertir fechas
            dates = [pd.to_datetime(d) if isinstance(d, str) else d for d in backtest_results['dates']]
            
            # Crear gráfico de equity curve
            equity_fig = go.Figure()
            
            equity_fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=backtest_results['equity_curve'],
                    mode='lines',
                    name='Equity',
                    line=dict(color='blue', width=2)
                )
            )
            
            # Añadir línea horizontal para el capital inicial
            equity_fig.add_hline(
                y=backtest_results['initial_cash'],
                line_dash="dash",
                line_color="red",
                annotation_text="Capital Inicial"
            )
            
            # Configurar gráfico
            equity_fig.update_layout(
                title=f'Curva de Equity: {symbol1} vs {symbol2}',
                xaxis_title='Fecha',
                yaxis_title='Valor de la Cartera ($)',
                height=500,
                template='plotly_white'
            )
            
            # Añadir anotación con métricas clave
            equity_fig.add_annotation(
                x=0.02,
                y=0.95,
                xref="paper",
                yref="paper",
                text=f"Retorno Total: {backtest_results['total_return']*100:.2f}%<br>"
                     f"Sharpe Ratio: {backtest_results['sharpe_ratio']:.2f}<br>"
                     f"Max Drawdown: {backtest_results['max_drawdown']*100:.2f}%",
                showarrow=False,
                font=dict(size=12),
                bgcolor="white",
                bordercolor="black",
                borderwidth=1,
                borderpad=4
            )
            
            # Crear gráfico de drawdown
            drawdown_fig = go.Figure()
            
            drawdown_fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=np.array(backtest_results['drawdown_curve'])*100,
                    mode='lines',
                    name='Drawdown',
                    fill='tozeroy',
                    line=dict(color='red')
                )
            )
            
            # Configurar gráfico
            drawdown_fig.update_layout(
                title=f'Drawdown: {symbol1} vs {symbol2}',
                xaxis_title='Fecha',
                yaxis_title='Drawdown (%)',
                height=400,
                template='plotly_white'
            )
            
            # Invertir eje Y para que el drawdown se muestre hacia abajo
            drawdown_fig.update_yaxes(autorange="reversed")
            
            # Añadir anotación con drawdown máximo
            drawdown_fig.add_annotation(
                x=0.02,
                y=0.05,
                xref="paper",
                yref="paper",
                text=f"Max Drawdown: {backtest_results['max_drawdown']*100:.2f}%",
                showarrow=False,
                font=dict(size=12),
                bgcolor="white",
                bordercolor="black",
                borderwidth=1,
                borderpad=4
            )
            
            # Crear gráfico de distribución de operaciones
            trade_dist_fig = go.Figure()
            
            # Extraer PnL de las operaciones
            trade_pnls = [trade['pnl'] for trade in backtest_results['trades']]
            
            if trade_pnls:
                # Crear histograma
                trade_dist_fig.add_trace(
                    go.Histogram(
                        x=trade_pnls,
                        nbinsx=20,
                        marker_color=['green' if x > 0 else 'red' for x in trade_pnls]
                    )
                )
                
                # Añadir línea vertical en cero
                trade_dist_fig.add_vline(
                    x=0,
                    line_dash="dash",
                    line_color="black"
                )
                
                # Calcular estadísticas de operaciones
                winning_trades = sum(1 for pnl in trade_pnls if pnl > 0)
                losing_trades = sum(1 for pnl in trade_pnls if pnl <= 0)
                avg_win = np.mean([pnl for pnl in trade_pnls if pnl > 0]) if winning_trades > 0 else 0
                avg_loss = np.mean([pnl for pnl in trade_pnls if pnl <= 0]) if losing_trades > 0 else 0
                
                # Añadir anotación con estadísticas
                trade_dist_fig.add_annotation(
                    x=0.02,
                    y=0.95,
                    xref="paper",
                    yref="paper",
                    text=f"Total Operaciones: {len(trade_pnls)}<br>"
                         f"Ganadoras: {winning_trades} ({winning_trades/len(trade_pnls)*100:.1f}%)<br>"
                         f"Perdedoras: {losing_trades} ({losing_trades/len(trade_pnls)*100:.1f}%)<br>"
                         f"Ganancia Media: ${avg_win:.2f}<br>"
                         f"Pérdida Media: ${avg_loss:.2f}",
                    showarrow=False,
                    font=dict(size=12),
                    bgcolor="white",
                    bordercolor="black",
                    borderwidth=1,
                    borderpad=4
                )
            else:
                # Si no hay operaciones, mostrar mensaje
                trade_dist_fig.add_annotation(
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    text="No hay operaciones para mostrar",
                    showarrow=False,
                    font=dict(size=16)
                )
            
            # Configurar gráfico
            trade_dist_fig.update_layout(
                title=f'Distribución de Operaciones: {symbol1} vs {symbol2}',
                xaxis_title='PnL ($)',
                yaxis_title='Frecuencia',
                height=400,
                template='plotly_white'
            )
            
            return equity_fig, drawdown_fig, trade_dist_fig
            
        except Exception as e:
            self.logger.error(f"Error creando gráficos de backtest: {str(e)}")
            raise
    
    def create_screener_card(self, pair_data):
        """
        Crea una tarjeta para el screener de pares.
        
        Args:
            pair_data (dict): Datos del par
            
        Returns:
            str: HTML para la tarjeta
        """
        try:
            # Determinar color según estado de cointegración
            if pair_data['color'] == 'success':
                color_class = 'success'
                status_text = 'Cointegrado'
            elif pair_data['color'] == 'warning':
                color_class = 'warning'
                status_text = 'Posible Cointegración'
            else:
                color_class = 'danger'
                status_text = 'No Cointegrado'
            
            # Formatear valores
            correlation = f"{pair_data['correlation']:.2f}"
            pvalue = f"{pair_data['pvalue']:.4f}"
            hedge_ratio = f"{pair_data['hedge_ratio']:.4f}"
            
            return {
                'pair': pair_data['pair'],
                'pair_names': pair_data['pair_names'],
                'is_cointegrated': pair_data['is_cointegrated'],
                'correlation': correlation,
                'pvalue': pvalue,
                'hedge_ratio': hedge_ratio,
                'color': color_class,
                'status': status_text
            }
            
        except Exception as e:
            self.logger.error(f"Error creando tarjeta para screener: {str(e)}")
            raise
