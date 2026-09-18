let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/ai-comment"])),
    Tabla = Table.FromRecords(Source),
    Fecha = Table.TransformColumns(Tabla,{
        {"created_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(Fecha,{
        {"id", Int64.Type},
        {"ticker", type text},
        {"decision_id", Int64.Type},
        {"decision_label", type text},
        {"final_score", type number},
        {"summary", type text},
        {"main_reason", type text},
        {"positive_factors", type text},
        {"risk_factors", type text},
        {"model_comment", type text},
        {"model_name", type text}
    })
in
    Tipos
