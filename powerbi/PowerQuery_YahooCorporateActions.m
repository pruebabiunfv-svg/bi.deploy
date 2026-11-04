let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/corporate-actions"])),
    Columns = {"ticker", "event_date", "event_type", "event_value", "source", "fetched_at"},
    Raw = if List.IsEmpty(Source) then #table(Columns, {}) else Table.FromRecords(Source),
    DateFields = Table.TransformColumns(Raw, {
        {"event_date", each if _ = null then null else Date.FromText(
            Text.Start(Text.From(_), 10), [Format="yyyy-MM-dd", Culture="en-US"]), type date},
        {"fetched_at", each if _ = null then null else DateTime.FromText(
            Text.Replace(Text.Start(Text.From(_), 19), "T", " "),
            [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }, null, MissingField.Ignore),
    Typed = Table.TransformColumnTypes(DateFields, {
        {"ticker", type text}, {"event_type", type text},
        {"event_value", type number}, {"source", type text}
    }, "en-US")
in
    Typed
