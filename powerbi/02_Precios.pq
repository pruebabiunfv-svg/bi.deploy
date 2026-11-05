let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/market-history",
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 5, 0)
            ]
        )
    ),
    Tabla = Table.FromRecords(Respuesta),
    Tipos = Table.TransformColumnTypes(
        Tabla,
        {
            {"ticker", type text},
            {"price_date", type date},
            {"close_price", type number},
            {"open_price", type number},
            {"high_price", type number},
            {"low_price", type number},
            {"volume", Int64.Type},
            {"source", type text}
        },
        "en-US"
    ),
    Ordenados = Table.Sort(Tipos, {{"ticker", Order.Ascending}, {"price_date", Order.Ascending}})
in
    Ordenados
