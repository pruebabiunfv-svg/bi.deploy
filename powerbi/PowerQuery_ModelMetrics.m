let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/model-metrics"])),
    Tabla = Table.FromRecords(Source),
    Fechas = Table.TransformColumns(Tabla,{
        {"metric_date", each if _ = null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date},
        {"created_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(Fechas,{
        {"id", Int64.Type},
        {"ticker", type text},
        {"accuracy", type number},
        {"precision_score", type number},
        {"recall_score", type number},
        {"f1_score", type number},
        {"roc_auc", type number},
        {"samples", Int64.Type},
        {"folds", Int64.Type},
        {"validation_method", type text}
    })
in
    Tipos
