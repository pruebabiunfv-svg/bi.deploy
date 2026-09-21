import datetime as dt
import hashlib
import math
import os
import statistics
import time
from urllib.parse import quote

import requests

from database.db import get_connection
from database.audit import finish_analysis_run, save_raw_payload, start_analysis_run
from database.init_db import init_database
from ml.hf_client import analyze_sentiment
from ml.validation import classification_metrics, walk_forward_splits

TICKERS = [
    x.strip().upper()
    for x in os.getenv("TICKERS", "AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ").split(",")
    if x.strip()
]
MARKET_PERIOD = os.getenv("MARKET_PERIOD", "10y")
HORIZON = int(os.getenv("PREDICTION_HORIZON_DAYS", "126"))
FRED_KEY = os.getenv("FRED_API_KEY", "")
SEC_UA = os.getenv("SEC_USER_AGENT", "BusinessAnalytics/1.0 contact@example.com")
NEWS_PER_TICKER = int(os.getenv("NEWS_PER_TICKER", "25"))
WALK_FORWARD_FOLDS = int(os.getenv("WALK_FORWARD_FOLDS", "4"))
GDELT_DELAY_SECONDS = float(os.getenv("GDELT_DELAY_SECONDS", "3"))
CURRENT_RUN_ID = None

CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
}


COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
}

COMPANY_QUERY = {
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet Google",
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
}


def _safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def load_yahoo(ticker):
    endpoint = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": MARKET_PERIOD, "interval": "1d", "events": "history"}
    response = requests.get(
        endpoint,
        params=params,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    full_payload = response.json()
    save_raw_payload(CURRENT_RUN_ID, "Yahoo Finance", ticker, endpoint, params, full_payload, response.status_code)

    payload = full_payload["chart"]["result"][0]
    timestamps = payload.get("timestamp", [])
    quote_data = payload.get("indicators", {}).get("quote", [{}])[0]
    adj_data = payload.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    meta = payload.get("meta", {})
    currency = meta.get("currency")
    exchange_name = meta.get("exchangeName") or meta.get("fullExchangeName")
    rows = []

    for i, stamp in enumerate(timestamps):
        close_values = quote_data.get("close", [])
        close = _safe_float(close_values[i]) if i < len(close_values) else None
        if close is None:
            continue
        def item(name, default=None):
            values = quote_data.get(name, [])
            return values[i] if i < len(values) else default
        adj_close = _safe_float(adj_data[i]) if i < len(adj_data) else close
        rows.append(
            (
                ticker,
                dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).date(),
                _safe_float(item("open")),
                _safe_float(item("high")),
                _safe_float(item("low")),
                close,
                adj_close,
                int(item("volume", 0) or 0),
                currency,
                exchange_name,
                "Yahoo Finance",
            )
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO market_data "
                "(ticker,price_date,open_price,high_price,low_price,close_price,adj_close,volume,currency,exchange_name,source) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE "
                "open_price=VALUES(open_price),high_price=VALUES(high_price),"
                "low_price=VALUES(low_price),close_price=VALUES(close_price),"
                "adj_close=VALUES(adj_close),volume=VALUES(volume),currency=VALUES(currency),"
                "exchange_name=VALUES(exchange_name),source=VALUES(source)",
                rows,
            )
    print(f"Yahoo {ticker}: {len(rows)} filas")


def load_fred():
    if not FRED_KEY:
        print("FRED omitido: FRED_API_KEY no configurado")
        return

    series = {
        "FEDFUNDS": "Federal Funds Rate",
        "CPIAUCSL": "CPI",
        "UNRATE": "Unemployment Rate",
        "GDP": "GDP",
    }
    observations_endpoint = "https://api.stlouisfed.org/fred/series/observations"
    metadata_endpoint = "https://api.stlouisfed.org/fred/series"
    with get_connection() as conn:
        with conn.cursor() as cur:
            for series_id, name in series.items():
                meta_params = {"series_id": series_id, "api_key": FRED_KEY, "file_type": "json"}
                meta_response = requests.get(metadata_endpoint, params=meta_params, timeout=30)
                meta_response.raise_for_status()
                meta_payload = meta_response.json()
                save_raw_payload(CURRENT_RUN_ID, "FRED", None, metadata_endpoint, {"series_id": series_id}, meta_payload, meta_response.status_code)
                metadata = (meta_payload.get("seriess") or [{}])[0]
                units = metadata.get("units")
                frequency = metadata.get("frequency")

                params = {"series_id": series_id, "api_key": FRED_KEY, "file_type": "json"}
                response = requests.get(observations_endpoint, params=params, timeout=30)
                response.raise_for_status()
                payload = response.json()
                save_raw_payload(CURRENT_RUN_ID, "FRED", None, observations_endpoint, {"series_id": series_id}, payload, response.status_code)
                rows = []
                for observation in payload.get("observations", []):
                    value = _safe_float(observation.get("value"))
                    if value is not None:
                        rows.append((
                            series_id, name, observation["date"], value,
                            observation.get("realtime_start"), observation.get("realtime_end"),
                            units, frequency,
                        ))
                cur.executemany(
                    "INSERT INTO economic_indicators "
                    "(series_id,indicator_name,period_date,value,realtime_start,realtime_end,units,frequency) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE value=VALUES(value),indicator_name=VALUES(indicator_name),"
                    "realtime_start=VALUES(realtime_start),realtime_end=VALUES(realtime_end),"
                    "units=VALUES(units),frequency=VALUES(frequency)",
                    rows,
                )
                print(f"FRED {series_id}: {len(rows)} filas")


def _latest_fact(companyfacts, tag):
    facts = companyfacts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    entries = facts.get("USD") or facts.get("USD/shares") or []
    entries = [x for x in entries if x.get("end") and x.get("val") is not None]
    if not entries:
        return None, None
    entries.sort(key=lambda x: (x.get("end", ""), x.get("filed", "")))
    latest = entries[-1]
    return latest.get("end"), _safe_float(latest.get("val"))


def _store_sec_company_facts(ticker, data):
    rows = []
    for taxonomy, concepts in (data.get("facts") or {}).items():
        if not isinstance(concepts, dict):
            continue
        for concept, fact in concepts.items():
            label = (fact or {}).get("label")
            for unit, entries in ((fact or {}).get("units") or {}).items():
                for entry in entries or []:
                    value = _safe_float(entry.get("val"))
                    if value is None:
                        continue
                    identity = "|".join(str(x or "") for x in [ticker,taxonomy,concept,unit,entry.get("start"),entry.get("end"),entry.get("filed"),entry.get("accn"),entry.get("frame"),value])
                    source_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
                    rows.append((
                        source_key,ticker,taxonomy,concept,(label or "")[:500],unit,
                        entry.get("start"),entry.get("end"),value,entry.get("fy"),entry.get("fp"),
                        entry.get("form"),entry.get("filed"),entry.get("accn"),entry.get("frame"),
                    ))
    if not rows:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT IGNORE INTO sec_company_facts
                (source_key,ticker,taxonomy,concept,label,unit,start_date,end_date,value,
                 fiscal_year,fiscal_period,form_type,filed_date,accession_number,frame)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )
            return cur.rowcount


def load_sec(ticker):
    cik = CIK.get(ticker)
    if not cik:
        return

    endpoint = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(
        endpoint,
        headers={"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"},
        timeout=40,
    )
    response.raise_for_status()
    data = response.json()
    save_raw_payload(CURRENT_RUN_ID, "SEC EDGAR", ticker, endpoint, {}, data, response.status_code)
    inserted_facts = _store_sec_company_facts(ticker, data)

    fields = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "net_income": ["NetIncomeLoss"],
        "total_assets": ["Assets"],
        "total_liabilities": ["Liabilities"],
        "equity": ["StockholdersEquity"],
        "eps": ["EarningsPerShareDiluted"],
    }

    values = {}
    dates = []
    for key, tags in fields.items():
        fact_date = fact_value = None
        for tag in tags:
            fact_date, fact_value = _latest_fact(data, tag)
            if fact_value is not None:
                break
        values[key] = fact_value
        if fact_date:
            dates.append(fact_date)

    if not dates:
        return

    report_date = max(dates)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fundamentals "
                "(ticker,report_date,revenue,net_income,total_assets,total_liabilities,equity,eps,source) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'SEC EDGAR') "
                "ON DUPLICATE KEY UPDATE revenue=VALUES(revenue),net_income=VALUES(net_income),"
                "total_assets=VALUES(total_assets),total_liabilities=VALUES(total_liabilities),"
                "equity=VALUES(equity),eps=VALUES(eps)",
                (
                    ticker,report_date,values["revenue"],values["net_income"],values["total_assets"],
                    values["total_liabilities"],values["equity"],values["eps"],
                ),
            )
    print(f"SEC {ticker}: actualizado; facts nuevos={inserted_facts}")


def _parse_gdelt_date(raw_value):
    if not raw_value:
        return None
    value = str(raw_value).strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return dt.datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def _request_with_retry(url, timeout=45, attempts=4):
    delay = max(1.0, GDELT_DELAY_SECONDS)
    last = None
    for attempt in range(1, attempts + 1):
        response = requests.get(url, timeout=timeout)
        last = response
        if response.status_code != 429:
            response.raise_for_status()
            return response
        if attempt < attempts:
            wait = delay * (2 ** (attempt - 1))
            print(f"GDELT 429: reintento {attempt}/{attempts} en {wait:.1f}s")
            time.sleep(wait)
    last.raise_for_status()
    return last


def load_gdelt_and_sentiment(ticker):
    query_text = f'"{COMPANY_QUERY.get(ticker, ticker)}" finance'
    query = quote(query_text)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={query}&mode=ArtList&maxrecords={NEWS_PER_TICKER}"
        "&format=json&sort=HybridRel"
    )
    response = _request_with_retry(url, timeout=45)
    payload = response.json()
    save_raw_payload(CURRENT_RUN_ID, "GDELT", ticker, url, {"query": query_text, "maxrecords": NEWS_PER_TICKER}, payload, response.status_code)
    articles = payload.get("articles", [])[:NEWS_PER_TICKER]
    inserted_news = 0
    inserted_sentiment = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for article in articles:
                title = (article.get("title") or "").strip()
                article_url = (article.get("url") or "").strip()[:1500]
                if not title:
                    continue

                existing = None
                if article_url:
                    cur.execute("SELECT id FROM financial_news WHERE url=%s LIMIT 1", (article_url,))
                    existing = cur.fetchone()
                if not existing:
                    cur.execute(
                        "SELECT id FROM financial_news WHERE ticker=%s AND title=%s LIMIT 1",
                        (ticker, title[:1000]),
                    )
                    existing = cur.fetchone()

                seen_at = _parse_gdelt_date(article.get("seendate"))
                if existing:
                    news_id = existing["id"]
                    cur.execute(
                        """
                        UPDATE financial_news SET domain=%s,language=%s,source_country=%s,
                               social_image=%s,seen_at=%s
                        WHERE id=%s
                        """,
                        (
                            article.get("domain"), article.get("language"), article.get("sourcecountry"),
                            (article.get("socialimage") or "")[:1500], seen_at, news_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO financial_news
                        (ticker,title,url,published_at,source,domain,language,source_country,social_image,seen_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            ticker,title[:1000],article_url,seen_at,article.get("domain") or "GDELT",
                            article.get("domain"),article.get("language"),article.get("sourcecountry"),
                            (article.get("socialimage") or "")[:1500],seen_at,
                        ),
                    )
                    news_id = cur.lastrowid
                    inserted_news += 1

                cur.execute("SELECT id FROM sentiment WHERE news_id=%s LIMIT 1", (news_id,))
                if cur.fetchone():
                    continue
                try:
                    sentiment = analyze_sentiment(title)
                    cur.execute(
                        "INSERT INTO sentiment "
                        "(news_id,ticker,positive_score,neutral_score,negative_score,sentiment_label,sentiment_score) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (
                            news_id,ticker,sentiment["positive"],sentiment["neutral"],sentiment["negative"],
                            sentiment["label"],sentiment["score"],
                        ),
                    )
                    inserted_sentiment += 1
                except Exception as exc:
                    print(f"FinBERT {ticker}: {exc}")

    print(f"GDELT {ticker}: {inserted_news} noticias nuevas, {inserted_sentiment} sentimientos nuevos")


def _returns(closes, n):
    return (
        closes[-1] / closes[-1 - n] - 1.0
        if len(closes) > n and closes[-1 - n]
        else 0.0
    )


def _feature_rows(closes, horizon):
    features = []
    labels = []
    for i in range(21, len(closes) - horizon):
        window = closes[: i + 1]
        daily = [
            window[j] / window[j - 1] - 1.0
            for j in range(max(1, len(window) - 20), len(window))
            if window[j - 1]
        ]
        features.append(
            [
                _returns(window, 1),
                _returns(window, 5),
                _returns(window, 20),
                statistics.pstdev(daily) if len(daily) > 1 else 0.0,
            ]
        )
        labels.append(1 if closes[i + horizon] > closes[i] else 0)
    return features, labels


def _feature_rows_with_index(closes, horizon):
    features = []
    labels = []
    price_indexes = []

    for i in range(21, len(closes) - horizon):
        window = closes[: i + 1]
        daily = [
            window[j] / window[j - 1] - 1.0
            for j in range(max(1, len(window) - 20), len(window))
            if window[j - 1]
        ]
        features.append(
            [
                _returns(window, 1),
                _returns(window, 5),
                _returns(window, 20),
                statistics.pstdev(daily) if len(daily) > 1 else 0.0,
            ]
        )
        labels.append(1 if closes[i + horizon] > closes[i] else 0)
        price_indexes.append(i)

    return features, labels, price_indexes


def train_predict_xgb(ticker):
    import numpy as np
    import xgboost as xgb

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price_date, close_price FROM market_data "
                "WHERE ticker=%s ORDER BY price_date",
                (ticker,),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT AVG(sentiment_score) AS s FROM sentiment "
                "WHERE ticker=%s AND created_at >= NOW() - INTERVAL 30 DAY",
                (ticker,),
            )
            sentiment_row = cur.fetchone()

    closes = [float(row["close_price"]) for row in rows if row["close_price"] is not None]
    if len(closes) < max(180, HORIZON + 50):
        print(f"XGBoost {ticker}: datos insuficientes ({len(closes)})")
        return

    features, labels = _feature_rows(closes, HORIZON)
    if len(set(labels)) < 2 or len(labels) < 50:
        print(f"XGBoost {ticker}: muestra insuficiente")
        return

    split = max(1, int(len(features) * 0.8))
    train = xgb.DMatrix(
        np.asarray(features[:split], dtype=float),
        label=np.asarray(labels[:split], dtype=float),
    )
    test = xgb.DMatrix(
        np.asarray(features[split:], dtype=float),
        label=np.asarray(labels[split:], dtype=float),
    )
    booster = xgb.train(
        {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 3,
            "eta": 0.08,
            "subsample": 0.9,
            "seed": 42,
        },
        train,
        num_boost_round=120,
        evals=[(test, "test")],
        verbose_eval=False,
    )

    latest_daily = [
        closes[j] / closes[j - 1] - 1.0
        for j in range(max(1, len(closes) - 20), len(closes))
        if closes[j - 1]
    ]
    latest_features = [[
        _returns(closes, 1),
        _returns(closes, 5),
        _returns(closes, 20),
        statistics.pstdev(latest_daily) if len(latest_daily) > 1 else 0.0,
    ]]
    probability = float(
        booster.predict(xgb.DMatrix(np.asarray(latest_features, dtype=float)))[0]
    )
    sentiment_score = float((sentiment_row or {}).get("s") or 0.0)
    ranking_score = max(
        0.0,
        min(1.0, 0.8 * probability + 0.2 * ((sentiment_score + 1.0) / 2.0)),
    )
    today = dt.date.today()
    predicted_class = 1 if probability >= 0.5 else 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO predictions "
                "(ticker,prediction_date,horizon_days,probability_favorable,predicted_class,model) "
                "VALUES (%s,%s,%s,%s,%s,'XGBoost') "
                "ON DUPLICATE KEY UPDATE "
                "probability_favorable=VALUES(probability_favorable),"
                "predicted_class=VALUES(predicted_class),created_at=CURRENT_TIMESTAMP",
                (ticker, today, HORIZON, probability, predicted_class),
            )
            cur.execute(
                "INSERT INTO prediction_history "
                "(run_id,ticker,prediction_date,horizon_days,probability_favorable,predicted_class,model) "
                "VALUES (%s,%s,%s,%s,%s,%s,'XGBoost')",
                (CURRENT_RUN_ID, ticker, today, HORIZON, probability, predicted_class),
            )
            cur.execute(
                "INSERT INTO asset_ranking "
                "(run_id,ticker,probability_score,sentiment_score,final_score,ranking_position) "
                "VALUES (%s,%s,%s,%s,%s,0)",
                (CURRENT_RUN_ID, ticker, probability, sentiment_score, ranking_score),
            )

    print(f"XGBoost {ticker}: prob={probability:.4f}, score={ranking_score:.4f}")


def evaluate_walk_forward(ticker):
    import numpy as np
    import xgboost as xgb

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price_date, close_price FROM market_data "
                "WHERE ticker=%s ORDER BY price_date",
                (ticker,),
            )
            rows = cur.fetchall()

    clean_rows = [row for row in rows if row["close_price"] is not None]
    dates = [row["price_date"] for row in clean_rows]
    closes = [float(row["close_price"]) for row in clean_rows]

    if len(closes) < max(250, HORIZON + 150):
        print(f"WalkForward {ticker}: datos insuficientes ({len(closes)})")
        return

    features, labels, price_indexes = _feature_rows_with_index(closes, HORIZON)
    if len(features) < 150:
        print(f"WalkForward {ticker}: muestra insuficiente")
        return

    min_train = max(120, int(len(features) * 0.55))
    splits = walk_forward_splits(
        len(features), min_train=min_train, folds=WALK_FORWARD_FOLDS
    )
    if not splits:
        print(f"WalkForward {ticker}: sin folds")
        return

    all_true = []
    all_probabilities = []
    all_price_indexes = []
    folds_used = 0

    for train_range, test_range in splits:
        train_idx = list(train_range)
        test_idx = list(test_range)
        if not train_idx or not test_idx:
            continue

        # Purga temporal: los labels de entrenamiento no pueden usar precios del periodo test.
        first_test_feature = test_idx[0]
        train_idx = [idx for idx in train_idx if idx + HORIZON < first_test_feature]
        if len(train_idx) < 80:
            continue

        y_train = [labels[idx] for idx in train_idx]
        if len(set(y_train)) < 2:
            continue

        x_train = np.asarray([features[idx] for idx in train_idx], dtype=float)
        x_test = np.asarray([features[idx] for idx in test_idx], dtype=float)
        train_matrix = xgb.DMatrix(
            x_train, label=np.asarray(y_train, dtype=float)
        )
        test_matrix = xgb.DMatrix(x_test)

        model = xgb.train(
            {
                "objective": "binary:logistic",
                "eval_metric": "logloss",
                "max_depth": 3,
                "eta": 0.08,
                "subsample": 0.9,
                "seed": 42,
            },
            train_matrix,
            num_boost_round=120,
            verbose_eval=False,
        )
        probabilities = model.predict(test_matrix)

        for local_pos, data_index in enumerate(test_idx):
            all_true.append(labels[data_index])
            all_probabilities.append(float(probabilities[local_pos]))
            all_price_indexes.append(price_indexes[data_index])
        folds_used += 1

    if not all_true:
        print(f"WalkForward {ticker}: sin resultados")
        return

    metrics = classification_metrics(all_true, all_probabilities)
    today = dt.date.today()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_metrics
                (run_id,ticker,metric_date,accuracy,precision_score,recall_score,f1_score,
                 roc_auc,samples,folds,validation_method)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Walk-Forward')
                """,
                (
                    CURRENT_RUN_ID,
                    ticker,
                    today,
                    metrics["accuracy"],
                    metrics["precision"],
                    metrics["recall"],
                    metrics["f1"],
                    metrics["roc_auc"],
                    metrics["samples"],
                    folds_used,
                ),
            )

    signals = sorted(zip(all_price_indexes, all_probabilities), key=lambda item: item[0])
    equity = 1.0
    equity_curve = [equity]
    trade_returns = []
    last_exit = -1

    for price_index, probability in signals:
        if probability < 0.5 or price_index <= last_exit:
            continue
        exit_index = price_index + HORIZON
        if exit_index >= len(closes):
            continue

        entry_price = closes[price_index]
        exit_price = closes[exit_index]
        if entry_price <= 0:
            continue

        base_equity = equity
        trade_return = exit_price / entry_price - 1.0
        for daily_index in range(price_index + 1, exit_index + 1):
            equity_curve.append(base_equity * (closes[daily_index] / entry_price))

        equity = base_equity * (1.0 + trade_return)
        trade_returns.append(trade_return)
        last_exit = exit_index

    total_return = equity - 1.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak)

    trades_count = len(trade_returns)
    hit_rate = (
        sum(1 for value in trade_returns if value > 0) / trades_count
        if trades_count
        else 0.0
    )

    benchmark_start = min(all_price_indexes)
    benchmark_end = min(len(closes) - 1, max(all_price_indexes) + HORIZON)
    benchmark_return = closes[benchmark_end] / closes[benchmark_start] - 1.0
    start_date = dates[benchmark_start]
    end_date = dates[benchmark_end]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backtesting
                (run_id,ticker,start_date,end_date,total_return,benchmark_return,
                 max_drawdown,hit_rate,trades_count)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    CURRENT_RUN_ID,
                    ticker,
                    start_date,
                    end_date,
                    total_return,
                    benchmark_return,
                    max_drawdown,
                    hit_rate,
                    trades_count,
                ),
            )

    print(
        f"WalkForward {ticker}: AUC={metrics['roc_auc']:.4f} "
        f"F1={metrics['f1']:.4f} samples={metrics['samples']} folds={folds_used}"
    )
    print(
        f"Backtesting {ticker}: return={total_return:.4f} "
        f"MDD={max_drawdown:.4f} hit={hit_rate:.4f} trades={trades_count}"
    )


def update_ranks(run_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,ticker,final_score FROM asset_ranking WHERE run_id=%s ORDER BY id DESC",
                (run_id,),
            )
            rows = cur.fetchall()
            latest = {}
            for row in rows:
                latest.setdefault(row["ticker"], row)
            ordered = sorted(latest.values(), key=lambda row: float(row["final_score"] or 0), reverse=True)
            for rank, row in enumerate(ordered, start=1):
                cur.execute("UPDATE asset_ranking SET ranking_position=%s WHERE id=%s", (rank, row["id"]))


def main():
    global CURRENT_RUN_ID
    init_database()
    CURRENT_RUN_ID = start_analysis_run(MARKET_PERIOD, HORIZON, "xgboost-finbert-v3", len(TICKERS))
    print(f"Analysis run iniciado: {CURRENT_RUN_ID}")
    notes = []

    try:
        for ticker in TICKERS:
            try:
                load_yahoo(ticker)
            except Exception as exc:
                notes.append(f"Yahoo {ticker}: {exc}")
                print(f"Yahoo {ticker} ERROR: {exc}")

        try:
            load_fred()
        except Exception as exc:
            notes.append(f"FRED: {exc}")
            print(f"FRED ERROR: {exc}")

        for ticker in TICKERS:
            try:
                load_sec(ticker)
            except Exception as exc:
                notes.append(f"SEC {ticker}: {exc}")
                print(f"SEC {ticker} ERROR: {exc}")

            try:
                load_gdelt_and_sentiment(ticker)
            except Exception as exc:
                notes.append(f"GDELT/FinBERT {ticker}: {exc}")
                print(f"GDELT/FinBERT {ticker} ERROR: {exc}")

            try:
                train_predict_xgb(ticker)
            except Exception as exc:
                notes.append(f"XGBoost {ticker}: {exc}")
                print(f"XGBoost {ticker} ERROR: {exc}")

            try:
                evaluate_walk_forward(ticker)
            except Exception as exc:
                notes.append(f"WalkForward {ticker}: {exc}")
                print(f"WalkForward/Backtesting {ticker} ERROR: {exc}")

            time.sleep(max(0.2, GDELT_DELAY_SECONDS))

        update_ranks(CURRENT_RUN_ID)

        from jobs.run_decision_engine import main as run_decision_engine
        run_decision_engine(CURRENT_RUN_ID)

        from jobs.build_kpi_snapshot import build_snapshot
        build_snapshot(CURRENT_RUN_ID)

        try:
            from jobs.run_best_asset_agent import main as run_best_asset_agent
            if not run_best_asset_agent(CURRENT_RUN_ID):
                notes.append("Gemini: sin recomendación generada")
        except Exception as exc:
            notes.append(f"Gemini: {exc}")
            print(f"Gemini Best Agent ERROR: {exc}")

        status = "COMPLETED" if not notes else "COMPLETED_WITH_WARNINGS"
        finish_analysis_run(CURRENT_RUN_ID, status, " | ".join(notes)[:8000] if notes else None)
        print(f"Pipeline finalizado run={CURRENT_RUN_ID} status={status}")

    except Exception as exc:
        finish_analysis_run(CURRENT_RUN_ID, "FAILED", str(exc)[:8000])
        raise


if __name__ == "__main__":
    main()
