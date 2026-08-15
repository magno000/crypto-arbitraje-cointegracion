import numpy as np
import pandas as pd
import logging

class SignalGenerator:
    """
    Clase para generar señales de trading basadas en la cointegración de pares.
    Calcula el spread y el z-score para identificar oportunidades de trading.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_signals(self, data1, data2, hedge_ratio, window=20, zscore_entry=2.0, zscore_exit=0.0):
        """
        Genera señales de trading basadas en el z-score del spread.
        
        Args:
            data1 (DataFrame): DataFrame con datos de la primera criptomoneda
            data2 (DataFrame): DataFrame con datos de la segunda criptomoneda
            hedge_ratio (float): Ratio de cobertura entre los dos activos
            window (int): Ventana para el cálculo de la media móvil y desviación estándar
            zscore_entry (float): Umbral de z-score para entrar en posición
            zscore_exit (float): Umbral de z-score para salir de posición
            
        Returns:
            DataFrame: DataFrame con señales de trading
        """
        try:
            # Extraer precios de cierre
            prices1 = data1['close'].values
            prices2 = data2['close'].values
            dates = data1['timestamp'].values
            
            # Calcular spread
            spread = prices2 - hedge_ratio * prices1
            
            # Calcular z-score
            spread_mean = pd.Series(spread).rolling(window=window).mean().values
            spread_std = pd.Series(spread).rolling(window=window).std().values
            zscore = np.zeros_like(spread)
            
            # Evitar división por cero
            mask = spread_std > 0
            zscore[mask] = (spread[mask] - spread_mean[mask]) / spread_std[mask]
            
            # Generar señales
            signals = np.zeros_like(zscore)
            position = 0
            
            for i in range(window, len(zscore)):
                # Si no hay posición y z-score cruza umbral inferior, comprar spread
                if position == 0 and zscore[i] < -zscore_entry:
                    signals[i] = 1
                    position = 1
                # Si no hay posición y z-score cruza umbral superior, vender spread
                elif position == 0 and zscore[i] > zscore_entry:
                    signals[i] = -1
                    position = -1
                # Si posición larga y z-score cruza umbral de salida, cerrar posición
                elif position == 1 and zscore[i] > -zscore_exit:
                    signals[i] = -1
                    position = 0
                # Si posición corta y z-score cruza umbral de salida, cerrar posición
                elif position == -1 and zscore[i] < zscore_exit:
                    signals[i] = 1
                    position = 0
            
            # Crear DataFrame de resultados
            results = pd.DataFrame({
                'timestamp': dates,
                'price1': prices1,
                'price2': prices2,
                'spread': spread,
                'zscore': zscore,
                'signal': signals
            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error generando señales: {str(e)}")
            raise
