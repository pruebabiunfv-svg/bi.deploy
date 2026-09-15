let
    BaseUrl = "https://TU-API.up.railway.app/api/predictions",
    Source = Json.Document(Web.Contents(BaseUrl,[ApiKeyName="api_key"])),
    ToTable = Table.FromRecords(Source),
    Types = Table.TransformColumnTypes(ToTable,{
        {"ticker", type text},
        {"prediction_date", type date},
        {"horizon_days", Int64.Type},
        {"probability_favorable", type number},
        {"predicted_class", Int64.Type},
        {"model", type text}
    })
in
    Types
