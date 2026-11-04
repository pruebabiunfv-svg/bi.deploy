let
    // Misma API que DashboardAssets: solo opiniones del último run completado.
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/company-opinions"])),
    Tabla = if List.IsEmpty(Source) then
        #table({"run_id", "ticker", "summary", "strengths", "risks",
                "model_comment", "model_name", "created_at"}, {})
    else
        Table.FromRecords(Source),
    Fechas = Table.TransformColumns(Tabla, {
        {"created_at", each if _ = null then null else
            DateTime.FromText(Text.Replace(Text.Start(Text.From(_), 19), "T", " "),
                [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }, null, MissingField.Ignore),
    Tipos = Table.TransformColumnTypes(Fechas, {
        {"run_id", Int64.Type}, {"ticker", type text},
        {"summary", type text}, {"strengths", type text},
        {"risks", type text}, {"model_comment", type text},
        {"model_name", type text}
    }, "en-US")
in
    Tipos
