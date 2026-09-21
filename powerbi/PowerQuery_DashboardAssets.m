let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/assets"])),
    Tabla = if List.Count(Source)=0 then #table({}, {}) else Table.FromRecords(Source),
    Fechas = if Table.IsEmpty(Tabla) then Tabla else Table.TransformColumns(
        Tabla,
        {
            {"market_date", each if _=null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date},
            {"created_at", each if _=null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19),"T"," "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
        },
        null,
        MissingField.Ignore
    ),
    Tipos = if Table.IsEmpty(Fechas) then Fechas else Table.TransformColumnTypes(
        Fechas,
        {
            {"id", Int64.Type}, {"run_id", Int64.Type}, {"ticker", type text}, {"company_name", type text},
            {"close_price", type number}, {"probability_favorable", type number}, {"predicted_class", Int64.Type},
            {"sentiment_score", type number}, {"sentiment_label", type text}, {"positive_score", type number},
            {"neutral_score", type number}, {"negative_score", type number}, {"news_count", Int64.Type},
            {"backtesting_return", type number}, {"benchmark_return", type number}, {"max_drawdown", type number},
            {"hit_rate", type number}, {"trades_count", Int64.Type}, {"accuracy", type number},
            {"precision_score", type number}, {"recall_score", type number}, {"f1_score", type number},
            {"roc_auc", type number}, {"ranking_score", type number}, {"final_score", type number},
            {"ranking_position", Int64.Type}, {"decision_label", type text}, {"is_best", Int64.Type}
        },
        "en-US"
    )
in
    Tipos
