let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/dashboard/company-opinions",
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 2, 0)
            ]
        )
    ),
    Tabla = Table.FromRecords(Respuesta),
    Tipos = Table.TransformColumnTypes(
        Tabla,
        {
            {"ticker", type text},
            {"run_id", Int64.Type},
            {"model_name", type text},
            {"model_comment", type text},
            {"summary", type text},
            {"strengths", type text},
            {"risks", type text},
            {"created_at", type datetime}
        },
        "en-US"
    )
in
    Tipos
