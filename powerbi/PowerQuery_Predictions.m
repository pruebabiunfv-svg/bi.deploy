let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/predictions"])),
    Tabla = Table.FromRecords(Source),
    FechaPrediccion = Table.TransformColumns(Tabla,{
        {"prediction_date", each if _ = null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date}
    }),
    FechaCreacion = Table.TransformColumns(FechaPrediccion,{
        {"created_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(FechaCreacion,{
        {"id", Int64.Type},
        {"ticker", type text},
        {"horizon_days", Int64.Type},
        {"probability_favorable", type number},
        {"predicted_class", Int64.Type},
        {"model", type text}
    })
in
    Tipos
