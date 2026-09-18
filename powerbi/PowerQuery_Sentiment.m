let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/sentiment"])),
    Tabla = Table.FromRecords(Source),
    Tipos = Table.TransformColumnTypes(Tabla,{
        {"ticker", type text},
        {"sentiment_score", type number},
        {"positive_score", type number},
        {"neutral_score", type number},
        {"negative_score", type number},
        {"news_count", Int64.Type}
    })
in
    Tipos
