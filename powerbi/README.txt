POWER BI — InversIA V4 / 10 EMPRESAS / YAHOO FINANCE / GEMINI

1. Desplegar API y ejecutar pipeline según docs/RAILWAY.md.
   Revisar primero /api/dashboard/status:
   - published_run_id: ejecución de la que salen TODOS los paneles.
   - latest_run_id: última ejecución, que puede ser parcial.
   - latest_company_opinions: opiniones realmente almacenadas para la última ejecución.
   - published_is_older=true: se conserva el último conjunto íntegro.

2. En Power BI Desktop: Obtener datos > Consulta en blanco > Editor avanzado.
   Crear estas consultas con el nombre de la izquierda y contenido del archivo:

   DashboardAssets      -> PowerQuery_DashboardAssets.m
   AIRecommendation     -> PowerQuery_AIRecommendation.m
   CompanyOpinions      -> PowerQuery_CompanyOpinions.m
   MarketHistory        -> PowerQuery_MarketHistory.m
   YahooProfiles        -> PowerQuery_YahooProfiles.m
   YahooCorporateActions -> PowerQuery_YahooCorporateActions.m
   DashboardStatus      -> PowerQuery_DashboardStatus.m

   La URL base de ejemplo es https://bideploy-production.up.railway.app.
   Cambiar en los siete archivos si el dominio real es diferente.
   Con PUBLIC_ANALYTICS=true, autenticación Anónima en Power BI.

3. Power BI > Modelado > Nueva tabla: cree POR SEPARADO las tablas calculadas
   SelectorEmpresa y Periodos de Measures.dax. No cree relaciones entre ellas.
   Crear cada medida restante por separado en Modelado > Nueva medida.
   Utilizar SelectorEmpresa[Empresa] como slicer de SELECCIÓN ÚNICA.
   Al cargar un run nuevo completo de 10 empresas aparecen automáticamente:
   Apple, Microsoft, NVIDIA, Amazon, Google, Meta, Tesla, Netflix, AMD y Oracle.
   SPY solo es benchmark y no es seleccionable.

4. Distribución similar a la imagen:
   - Fila 1: Empresa, Periodo, Estado Publicacion.
   - Fila 2 tarjetas: Mejor Activo IA, Probabilidad Favorable, Sentimiento
     FinBERT, Rentabilidad Backtesting, Drawdown Maximo.
   - Centro izquierdo: ranking (DashboardAssets[ticker] por Puntuacion Ranking).
   - Centro derecho: curva (MarketHistory[price_date] por Indice Precio
     Normalizado y opcional Indice SP500).
   - Abajo izquierda: Explicacion IA Completa / Comentario IA Mejor Activo.
   - Abajo derecha: Opinion IA Empresa / Opinion IA Empresa Breve.
   - Nueva fila Yahoo opcional: Capitalizacion Yahoo, PER Historico Yahoo,
     Beta Yahoo, Rendimiento Dividendo Yahoo, Sector Yahoo.
   - Eventos: YahooCorporateActions (fecha, ticker, tipo, importe/razón split).

5. Formatos: probabilidad, drawdown, backtesting y dividend_yield en porcentaje
   (fracción 0..1, no multiplicar por 100 en DAX). Scores en escala 0..100.
   Capitalización = moneda USD y unidades miles de millones opcionales;
   PER y Beta = decimal. Por cada ticker, las nuevas cifras Yahoo pueden
   estar vacías si la fuente denegó solicitudes (no presentar como cero).

6. Prueba obligatoria:
   - Seleccionar AMZN -> varían sus KPI, curva, perfil y opinión Gemini.
   - Seleccionar MSFT -> cambian los elementos anteriores, no el ganador global.
   - El ranking global contiene 10 tickers del MISMO run_id.
   - AIRecommendation, CompanyOpinions y DashboardAssets mantienen run_id idéntico.
   - Periodo 3 meses / 1 año / 5 años / 10 años afecta SOLO el gráfico
     histórico; no reentrena el modelo ni modifica la opinión publicada.

7. La creación de .pbix requiere Power BI Desktop. Estos archivos entregan
   Power Query, DAX y configuración para construir la vista; el ZIP no incluye
   un .pbix binario. Los resultados no garantizan rentabilidad futura.
