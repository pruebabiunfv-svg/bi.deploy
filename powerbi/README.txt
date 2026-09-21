POWER BI - MODELO V2 CONSISTENTE POR EMPRESA

1) Importe PowerQuery_DashboardAssets.m como consulta "DashboardAssets".
2) Importe PowerQuery_AIRecommendation.m como "AIRecommendation".
3) Importe PowerQuery_MarketHistory.m como "MarketHistory".
4) Opcional: PowerQuery_AnalysisRuns.m para auditoría de ejecuciones.
5) Cree DimActivo con el DAX de Measures.dax.
6) Relaciones:
   DimActivo[Ticker] 1 -> * DashboardAssets[ticker]
   DimActivo[Ticker] 1 -> * MarketHistory[ticker]
7) Use DimActivo[Empresa] como slicer.

IMPORTANTE:
- NO use las consultas Predictions/Sentiment/Backtesting/ModelMetrics para las tarjetas actuales.
  Se conservan para auditoría e históricos, pero los KPI del dashboard salen de DashboardAssets.
- Ranking y Mejor Activo usan el MISMO DashboardAssets[final_score].
- Gemini no elige otro activo: explica el registro DashboardAssets[is_best]=1 del mismo run.

Visuales:
- Tarjetas por empresa: Probabilidad Favorable, Score Sentimiento, Rentabilidad Backtesting,
  Maximum Drawdown, Nivel Confianza Modelo, F1 Modelo, Score Final, Posicion Ranking.
- Barras ranking: ticker + final_score, ordenar DESC.
- Línea histórica: price_date + close_price.
- Panel global: Mejor Activo IA + Score Mejor Activo + Comentario IA Mejor Activo.
