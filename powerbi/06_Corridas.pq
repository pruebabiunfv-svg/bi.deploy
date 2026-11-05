let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/dashboard/runs",
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 2, 0)
            ]
        )
    ),
    Tabla = Table.FromRecords(Respuesta),
    Tipos = Table.TransformColumnTypes(
        Tabla,
        {
            {"id", Int64.Type},
            {"started_at", type datetime},
            {"completed_at", type datetime},
            {"horizon_days", Int64.Type},
            {"market_period", type text},
            {"model_version", type text},
            {"status", type text},
            {"total_assets", Int64.Type},
            {"notes", type text}
        },
        "en-US"
    )
in
    Tipos
