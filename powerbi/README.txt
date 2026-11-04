POWER BI - DASHBOARD DE INVERSIÓN V3 (EMPRESA + OPINIONES IA)

1) API / Railway
   Asegúrese de que el pipeline esté COMPLETED o COMPLETED_WITH_WARNINGS.
   La API debe devolver JSON en estos 4 endpoints:
   /api/dashboard/assets
   /api/dashboard/recommendation
   /api/dashboard/company-opinions
   /api/market-history

2) POWER QUERY (Inicio > Transformar datos > Consulta en blanco > Editor avanzado)
   Importe PowerQuery_DashboardAssets.m       -> DashboardAssets
   Importe PowerQuery_AIRecommendation.m      -> AIRecommendation
   Importe PowerQuery_CompanyOpinions.m       -> CompanyOpinions
   Importe PowerQuery_MarketHistory.m         -> MarketHistory
   Todos usan BaseUrl = https://bideploy-production.up.railway.app
   Cambie BaseUrl en TODOS los archivos si el dominio real es distinto.
   NO mezcle consultas legacy Predictions/Sentiment/Backtesting/ModelMetrics
   con las tarjetas de la vista V3: los KPI salen de un mismo snapshot.

3) MODELO Y MEDIDAS
   En Measures.dax hay DOS tablas calculadas:
     SelectorEmpresa (slicer empresa; selección única)
     Periodos        (slicer período; selección única; ordenar Periodo por Orden)
   NO crear relaciones desde esas tablas hacia otros hechos.
   No usar el slicer DimActivo del modelo V2; quítelo de la página.
   Cree cada expresión de Measures.dax como Nueva tabla o Nueva medida
   POR SEPARADO. No pegar el archivo completo en una sola medida.
   Si ya existe una medida del mismo nombre, sustituya su fórmula.

4) DISTRIBUCIÓN SIMILAR A LA REFERENCIA
   Panel superior: SelectorEmpresa[Empresa] | Periodos[Periodo]
   Tarjetas:
     [Mejor Activo IA]             -> ganador global, constante
     [Probabilidad Favorable]      -> empresa seleccionada (formato %)
     [Sentimiento FinBERT]         -> score entre -1 y +1
     [Rentabilidad Backtesting]    -> empresa seleccionada (formato %)
     [Drawdown Maximo]             -> empresa seleccionada (formato %)
   Ranking barras:
     Eje DashboardAssets[ticker]
     Valor [Puntuacion Ranking] (0-100), ordenar descendente
     Color condicional con [Color Ranking]; muestra TODOS los tickers.
   Histórico líneas:
     Eje MarketHistory[price_date]
     Valores [Indice Precio Normalizado], opcional [Indice SP500]
     Eje X continuo; desactivar Mostrar elementos sin datos.
   [Indice SP500] exige que existan precios de SPY en market_data.
   BENCHMARK_TICKER=SPY permite cargarlos incluso si SPY no está en TICKERS.
   Panel inferior derecho:
     [Empresa Seleccionada], [Opinion IA Empresa] o [Opinion IA Empresa Breve]
   Panel inferior izquierdo:
     [Mejor Empresa IA], [Score Mejor Activo], [Explicacion IA Completa]

5) ESCALAS/FORMATOS
   Valores probabilidad/backtesting/drawdown/hit rate = decimales [0,1]:
   aplicar formato porcentual; NO multiplicar esas medidas por 100.
   [Score Empresa], [Score Mejor Activo], [Puntuacion Ranking] sí van de 0 a 100.
   [Rentabilidad Precio Periodo] es retorno de mercado del período seleccionado;
   NO confundirla con [Rentabilidad Backtesting] del modelo.

6) PRUEBAS
   Seleccione AMZN -> deben cambiar tarjetas, curva y opinión IA individual.
   Seleccione MSFT -> deberían reflejar MSFT sin afectar el ranking global.
   La opinión comparativa debe seguir explicando is_best=1 del mismo run_id.
   Cambiar 3 meses/1 año solo recorta la curva histórica: no reentrena XGBoost
   ni cambia el horizonte de predicción. Ejecutar pipeline + Refresh Power BI
   para traer datos y textos nuevos.

   Apariencia: Vista > Temas > Examinar temas e importe
   Theme_Inversion_IA.json. Use tarjetas blancas de esquinas redondeadas,
   fondo azul muy claro y paneles inferiores de texto con ajuste de línea.

7) CAVEATS
   La vista se construye en Power BI Desktop; no se entrega un .pbix binario.
   Cambiar de empresa NO hace una solicitud de IA en tiempo real: muestra el
   comentario ya almacenado por el pipeline en ai_asset_opinion.
   Una ejecución con cuota agotada de Gemini podrá tener KPI sin opinión IA.
   No presentar los scores como garantía de rentabilidad futura.
