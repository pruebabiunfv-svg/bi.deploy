let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/dashboard/assets",
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 2, 0)
            ]
        )
    ),
    Tabla = Table.FromRecords(Respuesta),
    Tipos = Table.TransformColumnTypes(
        Tabla,
        {
            {"ticker", type text},
            {"company_name", type text},
            {"ranking_position", Int64.Type},
            {"final_score", type number},
            {"probability_favorable", type number},
            {"hit_rate", type number},
            {"sentiment_score", type number},
            {"sentiment_label", type text},
            {"news_count", Int64.Type},
            {"backtesting_return", type number},
            {"benchmark_return", type number},
            {"max_drawdown", type number},
            {"accuracy", type number},
            {"f1_score", type number},
            {"roc_auc", type number},
            {"precision_score", type number},
            {"recall_score", type number},
            {"ranking_score", type number},
            {"decision_label", type text},
            {"close_price", type number},
            {"market_date", type date},
            {"created_at", type datetime},
            {"run_id", Int64.Type},
            {"trades_count", Int64.Type},
            {"is_best", Int64.Type}
        },
        "en-US"
    ),
    Ordenados = Table.Sort(Tipos, {{"ranking_position", Order.Ascending}})
in
    Ordenados
