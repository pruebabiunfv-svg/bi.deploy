let
    // Cambie el dominio si el despliegue de Railway tiene otra URL.
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/market-history"])),
    Tabla = if List.IsEmpty(Source) then
        #table({"ticker", "price_date", "close_price", "volume", "source"}, {})
    else
        Table.FromRecords(Source),
    Seleccion = Table.SelectColumns(
        Tabla,
        {"ticker", "price_date", "close_price", "volume", "source"},
        MissingField.UseNull
    ),
    Fechas = Table.TransformColumns(Seleccion, {
        {"price_date", each if _ = null then null else
            Date.FromText(Text.Start(Text.From(_), 10),
                [Format="yyyy-MM-dd", Culture="en-US"]), type date}
    }),
    Tipos = Table.TransformColumnTypes(Fechas, {
        {"ticker", type text},
        {"close_price", type number},
        {"volume", Int64.Type},
        {"source", type text}
    }, "en-US")
in
    Tipos
