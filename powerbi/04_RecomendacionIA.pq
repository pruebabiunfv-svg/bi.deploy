let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Respuesta = Json.Document(
        Web.Contents(
            BaseUrl,
            [
                RelativePath = "api/dashboard/recommendation",
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
            {"comparison_comment", type text},
            {"main_reason", type text},
            {"positive_factors", type text},
            {"risk_factors", type text},
            {"model_comment", type text},
            {"summary", type text},
            {"decision_label", type text},
            {"final_score", type number},
            {"created_at", type datetime}
        },
        "en-US"
    )
in
    Tipos
