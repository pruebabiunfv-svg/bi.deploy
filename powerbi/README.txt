POWER BI

1. Abrir cada PowerQuery_*.m y reemplazar:
   https://TU-API.up.railway.app
   por el dominio real de bi.deploy.

2. Crear consultas con estos nombres:
   Ranking
   Predictions
   Sentiment
   Backtesting
   ModelMetrics
   MarketHistory
   Decisions
   AIComment

3. Si PUBLIC_ANALYTICS=true, elegir credencial Web: Anónimo.

4. Copiar las medidas de Measures.dax.

Visuales:
- Mejor Activo: tarjeta [Mejor Activo]
- Probabilidad: tarjeta [Probabilidad Favorable] formato %
- Sentimiento: tarjeta/gauge [Score Sentimiento]
- Backtesting: tarjeta [Rentabilidad Backtesting] formato %
- Riesgo: tarjeta [Maximum Drawdown] formato %
- Ranking: barras Decisions[ticker] vs Decisions[final_score]
- Histórico: línea MarketHistory[price_date] vs MarketHistory[close_price]
- Confianza: tarjeta [Nivel Confianza Modelo] formato %
- Gemini: tarjeta de texto [Comentario IA] o [Explicacion IA]
