# Arbitraje estadístico con cointegración para criptomonedas

Aplicación de investigación cuantitativa construida con **Python** y **Streamlit** para estudiar estrategias de *pairs trading* sobre activos *spot* contra USDT. La fuente predeterminada son velas OHLCV reales de Binance obtenidas con CCXT. El modo de datos sintéticos existe exclusivamente para probar la interfaz cuando el acceso a mercado no está disponible.

> **Aviso importante:** el proyecto es educativo y de investigación. No constituye asesoramiento financiero, no ejecuta órdenes y un resultado histórico no garantiza resultados futuros.

## Capacidades

| Área | Funcionalidad |
|---|---|
| Datos | Descarga paginada de velas reales de Binance, reintentos, control de límite de llamadas y alineación temporal de series. |
| Analizador | Prueba Engle–Granger, p-value, score, correlación, hedge ratio, vida media, precios, spread y z-score. |
| Screener | Descarga cada activo una vez, evalúa sus combinaciones y muestra tarjetas de color según el estado estadístico. |
| Backtesting | Simulación de cartera long/short, entradas/salidas por z-score, stop-loss, comisión, apalancamiento, curva de equity, drawdown y detalle de operaciones. |
| Interfaz | Navegación multipágina, exportación CSV, credenciales opcionales y documentación integrada. |

## Estructura del proyecto

```text
streamlit_app/
├── app.py                         # Portada, navegación y estado inicial
├── requirements.txt               # Dependencias para instalación/despliegue
├── .streamlit/
│   └── config.toml                # Tema y configuración de Streamlit
├── modules/
│   ├── data_fetcher.py            # CCXT/Binance y generación sintética explícita
│   ├── cointegration.py           # Prueba Engle–Granger y hedge ratio
│   ├── signals.py                 # Spread, z-score y señales
│   ├── backtest.py              # Motor vectorial de simulación long/short
│   ├── backtrader_engine.py     # Motor alternativo implementado con Backtrader
│   └── performance.py             # Utilidades de rendimiento extensibles
├── pages/
│   ├── 1_analyzer.py              # Analizador de pares
│   ├── 2_screener.py              # Screener de combinaciones
│   ├── 3_backtest.py              # Backtesting y métricas
│   └── 4_documentation.py         # Guía metodológica
└── utils/
    ├── helpers.py                 # Sesión, sidebar Binance y cálculos auxiliares
    └── visualization.py           # Gráficas interactivas Plotly
```

Los directorios `modules`, `pages` y `utils` contienen archivos `__init__.py` para que los importes sean consistentes tanto en local como en Streamlit Cloud.

## Ejecución local

Crea un entorno virtual y ejecuta estos comandos desde la carpeta que contiene `app.py`:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit abrirá la aplicación en `http://localhost:8501`. Los selectores siempre muestran una lista de mercados de reserva; al ejecutar un análisis real, la aplicación descarga los datos actuales desde Binance. Si el intercambio no es accesible desde tu red, el error se muestra de forma explícita y puedes habilitar manualmente el modo de pruebas sintéticas desde la barra lateral.

## Uso de Binance

Las credenciales de Binance son **opcionales** para consultar datos de mercado. Si deseas usar una API Key, crea una clave de solo lectura y aplica restricciones de IP cuando sea posible. Introduce la clave y el secreto en la barra lateral y pulsa **Conectar / actualizar**.

La aplicación no guarda las claves en el repositorio ni las escribe en archivos. Se mantienen únicamente en el estado de la sesión activa de Streamlit. No habilites permisos de retirada o trading para una aplicación de análisis de datos.

## Despliegue en Streamlit Cloud

1. Crea un repositorio en GitHub y sube el contenido de `streamlit_app/` a la raíz del repositorio. Alternativamente, conserva la carpeta y utiliza `streamlit_app/app.py` como archivo principal.
2. En [Streamlit Community Cloud](https://share.streamlit.io/), selecciona **Create app** y autoriza el repositorio.
3. Escoge la rama de despliegue y configura el archivo principal como `app.py` —o `streamlit_app/app.py` si mantuviste la carpeta contenedora—.
4. Confirma el despliegue. La plataforma instalará las bibliotecas declaradas en `requirements.txt`.
5. Abre la URL generada y utiliza la barra lateral para comprobar la disponibilidad de Binance antes de iniciar el análisis.

## Consideraciones metodológicas

El screener es una herramienta de descubrimiento, no una validación definitiva. Se recomienda comprobar los candidatos con una muestra fuera de la ventana de selección y examinar su liquidez. El motor de backtesting modela entradas, salidas y comisiones, pero no representa exhaustivamente slippage, *funding*, costes de préstamo, límites de tamaño, latencia, liquidaciones o impuestos.

La página de Backtesting permite elegir entre **Backtrader**, integrado mediante `Cerebro`, y el motor vectorial propio. Ambos modelan una cartera long/short con hedge ratio; el motor vectorial es útil para comparar hipótesis de forma rápida, mientras Backtrader aporta una ruta directa de extensión con *feeds*, *brokers* y *analyzers* de su ecosistema.

## Diagnóstico rápido

| Síntoma | Causa probable | Acción recomendada |
|---|---|---|
| Selectores con lista limitada | Binance no es accesible al iniciar la sesión. | La lista estática permite navegar; prueba la conexión desde la barra lateral antes de ejecutar análisis real. |
| Error al descargar velas | Restricción de red, símbolo no disponible o rango sin suficientes velas. | Reduce el período, cambia el timeframe, vuelve a conectar o usa modo sintético sólo para pruebas. |
| Screener lento | Hay muchas combinaciones o velas que descargar. | Selecciona cinco o seis activos líquidos y un timeframe más amplio. |
| Backtest sin operaciones | Los umbrales no se activaron o no hay reversión suficiente. | Ajusta ventana, entrada/salida y revisa el gráfico de z-score. |

## Referencias

La página **Documentación** incluye enlaces a la prueba de cointegración de `statsmodels`, CCXT, Binance y literatura base de *pairs trading*, incluido el artículo de Engle y Granger.[1]

[1]: https://doi.org/10.2307/1913236 "Engle, R. F. & Granger, C. W. J. (1987). Co-integration and error correction"
