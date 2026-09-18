let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/market-history"])),
    Tabla = Table.FromRecords(Source),
    Fecha = Table.TransformColumns(Tabla,{
        {"price_date", each if _ = null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date}
    }),
    Tipos = Table.TransformColumnTypes(Fecha,{
        {"ticker", type text},
        {"open_price", type number},
        {"high_price", type number},
        {"low_price", type number},
        {"close_price", type number},
        {"volume", Int64.Type},
        {"source", type text}
    })
in
    Tipos
