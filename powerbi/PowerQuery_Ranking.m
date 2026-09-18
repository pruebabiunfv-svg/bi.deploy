let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/ranking"])),
    Tabla = Table.FromRecords(Source),
    Fecha = Table.TransformColumns(Tabla,{
        {"calculated_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(Fecha,{
        {"ticker", type text},
        {"probability_score", type number},
        {"sentiment_score", type number},
        {"final_score", type number},
        {"ranking_position", Int64.Type}
    })
in
    Tipos
