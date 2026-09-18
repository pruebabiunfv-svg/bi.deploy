let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/decisions"])),
    Tabla = Table.FromRecords(Source),
    Fechas = Table.TransformColumns(Tabla,{
        {"decision_date", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime},
        {"created_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(Fechas,{
        {"id", Int64.Type},
        {"ticker", type text},
        {"ranking_position", Int64.Type},
        {"prediction_probability", type number},
        {"sentiment_score", type number},
        {"ranking_score", type number},
        {"backtesting_return", type number},
        {"backtesting_score", type number},
        {"model_confidence", type number},
        {"model_f1", type number},
        {"risk_score", type number},
        {"final_score", type number},
        {"decision_label", type text},
        {"explanation", type text},
        {"model_version", type text}
    })
in
    Tipos
