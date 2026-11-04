let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/status"])),
    Tabla = Table.FromRecords({Source}),
    Tipos = Table.TransformColumnTypes(Tabla, {
        {"latest_run_id", Int64.Type}, {"latest_expected_assets", Int64.Type},
        {"latest_snapshots", Int64.Type}, {"latest_company_opinions", Int64.Type},
        {"latest_general_recommendations", Int64.Type}, {"published_run_id", Int64.Type},
        {"configured_companies", Int64.Type}, {"dashboard_ready", type logical},
        {"published_is_older", type logical}, {"latest_run_status", type text},
        {"message", type text}
    }, "en-US")
in
    Tipos
