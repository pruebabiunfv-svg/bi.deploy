let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/runs"])),
    Tabla = if List.Count(Source)=0 then #table({}, {}) else Table.FromRecords(Source)
in
    Tabla
