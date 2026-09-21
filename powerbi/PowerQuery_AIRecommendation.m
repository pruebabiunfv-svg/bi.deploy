let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/recommendation"])),
    Tabla = if List.Count(Source)=0 then #table({}, {}) else Table.FromRecords(Source),
    Fecha = if Table.IsEmpty(Tabla) then Tabla else Table.TransformColumns(
        Tabla,
        {{"created_at", each if _=null then null else DateTime.FromText(Text.Replace(Text.Start(Text.From(_),19),"T"," "), [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}},
        null,
        MissingField.Ignore
    ),
    Tipos = if Table.IsEmpty(Fecha) then Fecha else Table.TransformColumnTypes(
        Fecha,
        {{"id", Int64.Type},{"run_id", Int64.Type},{"ticker", type text},{"final_score", type number},
         {"decision_label", type text},{"summary", type text},{"main_reason", type text},
         {"positive_factors", type text},{"risk_factors", type text},{"comparison_comment", type text},
         {"model_comment", type text},{"model_name", type text}},
        "en-US"
    )
in
    Tipos
