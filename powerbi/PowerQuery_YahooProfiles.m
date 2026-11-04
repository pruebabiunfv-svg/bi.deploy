let
    BaseUrl = "https://bideploy-production.up.railway.app",
    Source = Json.Document(Web.Contents(BaseUrl, [RelativePath="api/dashboard/yahoo-profiles"])),
    Columns = {"run_id", "ticker", "sector", "industry", "country", "website", "currency",
        "market_cap", "trailing_pe", "forward_pe", "beta", "dividend_yield",
        "fifty_two_week_high", "fifty_two_week_low", "average_volume", "captured_at"},
    Raw = if List.IsEmpty(Source) then #table(Columns, {}) else Table.FromRecords(Source),
    DateFields = Table.TransformColumns(Raw, {
        {"captured_at", each if _ = null then null else
            DateTime.FromText(Text.Replace(Text.Start(Text.From(_), 19), "T", " "),
                [Format="yyyy-MM-dd HH:mm:ss", Culture="en-US"]), type datetime}
    }, null, MissingField.Ignore),
    Typed = Table.TransformColumnTypes(DateFields, {
        {"run_id", Int64.Type}, {"ticker", type text}, {"sector", type text},
        {"industry", type text}, {"country", type text}, {"website", type text},
        {"currency", type text}, {"market_cap", Int64.Type}, {"trailing_pe", type number},
        {"forward_pe", type number}, {"beta", type number}, {"dividend_yield", type number},
        {"fifty_two_week_high", type number}, {"fifty_two_week_low", type number},
        {"average_volume", Int64.Type}
    }, "en-US")
in
    Typed
