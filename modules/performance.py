import numpy as np
import pandas as pd
import logging

class PerformanceAnalyzer:
    """
    Clase para analizar el rendimiento de estrategias de trading.
    Calcula métricas como retorno total, Sharpe ratio, drawdown, etc.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, equity_curve, risk_free_rate=0.0):
        """
        Analiza el rendimiento de una estrategia de trading.
        
        Args:
            equity_curve (array-like): Serie temporal del valor de la cartera
            risk_free_rate (float): Tasa libre de riesgo anualizada
            
        Returns:
            dict: Métricas de rendimiento
        """
        try:
            # Convertir a array de numpy si es necesario
            equity = np.array(equity_curve)
            
            # Calcular retornos diarios
            returns = np.diff(equity) / equity[:-1]
            
            # Calcular retorno total
            total_return = (equity[-1] / equity[0]) - 1
            
            # Calcular Sharpe ratio anualizado
            sharpe_ratio = 0
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe_ratio = (np.mean(returns) - risk_free_rate / 252) / np.std(returns) * np.sqrt(252)
            
            # Calcular drawdown
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / peak
            max_drawdown = np.max(drawdown)
            
            # Calcular volatilidad anualizada
            volatility = np.std(returns) * np.sqrt(252)
            
            return {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'equity_curve': equity,
                'drawdown_curve': drawdown
            }
            
        except Exception as e:
            self.logger.error(f"Error analizando rendimiento: {str(e)}")
            raise
