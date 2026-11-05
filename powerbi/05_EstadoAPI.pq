let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/dashboard/status",
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 2, 0)
            ]
        )
    ),
    Tabla = Table.FromRecords({Respuesta}),
    Tipos = Table.TransformColumnTypes(
        Tabla,
        {
            {"dashboard_ready", type logical},
            {"latest_run_id", Int64.Type},
            {"latest_run_status", type text},
            {"published_run_id", Int64.Type},
            {"published_is_older", type logical},
            {"configured_companies", Int64.Type},
            {"latest_snapshots", Int64.Type},
            {"latest_company_opinions", Int64.Type},
            {"message", type text}
        },
        "en-US"
    )
in
    Tipos
