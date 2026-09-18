let
    BaseUrl = "https://TU-API.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/backtesting"])),
    Tabla = Table.FromRecords(Source),
    Fechas = Table.TransformColumns(Tabla,{
        {"start_date", each if _ = null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date},
        {"end_date", each if _ = null then null else Date.FromText(Text.Start(Text.From(_),10), [Format="yyyy-MM-dd", Culture="en-US"]), type date},
        {"created_at", each if _ = null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19), "T", " "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }),
    Tipos = Table.TransformColumnTypes(Fechas,{
        {"id", Int64.Type},
        {"ticker", type text},
        {"total_return", type number},
        {"benchmark_return", type number},
        {"max_drawdown", type number},
        {"hit_rate", type number},
        {"trades_count", Int64.Type}
    })
in
    Tipos
