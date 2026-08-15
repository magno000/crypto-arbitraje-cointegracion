import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint
import logging

class CointegrationAnalyzer:
    """
    Clase para analizar la cointegración entre pares de criptomonedas.
    Implementa la prueba de Engle-Granger para determinar si dos series temporales están cointegradas.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, data1, data2):
        """
        Analiza la cointegración entre dos series temporales.
        
        Args:
            data1 (DataFrame): DataFrame con datos de la primera criptomoneda
            data2 (DataFrame): DataFrame con datos de la segunda criptomoneda
            
        Returns:
            dict: Resultados del análisis de cointegración
        """
        try:
            # Extraer precios de cierre
            prices1 = data1['close'].values
            prices2 = data2['close'].values
            
            # Calcular correlación
            correlation = np.corrcoef(prices1, prices2)[0, 1]
            
            # Realizar prueba de cointegración
            score, pvalue, crit_value = coint(prices1, prices2)
            
            # Calcular hedge ratio (coeficiente de regresión)
            hedge_ratio = np.polyfit(prices1, prices2, 1)[0]
            
            # Determinar si están cointegradas (p-value < 0.05)
            is_cointegrated = pvalue < 0.05
            
            return {
                'is_cointegrated': is_cointegrated,
                'score': score,
                'pvalue': pvalue,
                'critical_value_1pct': crit_value[0],
                'critical_value_5pct': crit_value[1],
                'critical_value_10pct': crit_value[2],
                'hedge_ratio': hedge_ratio,
                'correlation': correlation
            }
            
        except Exception as e:
            self.logger.error(f"Error en análisis de cointegración: {str(e)}")
            raise
