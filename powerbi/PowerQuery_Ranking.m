let
    BaseUrl = "https://TU-API.up.railway.app/api/ranking",
    Source = Json.Document(
        Web.Contents(
            BaseUrl,
            [ApiKeyName="api_key"]
        )
    ),
    ToTable = Table.FromRecords(Source),
    Types = Table.TransformColumnTypes(ToTable,{
        {"ticker", type text},
        {"probability_score", type number},
        {"sentiment_score", type number},
        {"final_score", type number},
        {"ranking_position", Int64.Type},
        {"calculated_at", type datetime}
    })
in
    Types
