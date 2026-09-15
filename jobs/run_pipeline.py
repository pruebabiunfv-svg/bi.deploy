import datetime as dt
import json
import math
import os
import statistics
import time
from urllib.parse import quote

import requests

from database.init_db import init_database
from database.db import get_connection
from ml.hf_client import analyze_sentiment

TICKERS = [x.strip().upper() for x in os.getenv("TICKERS", "AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ").split(",") if x.strip()]
MARKET_PERIOD = os.getenv("MARKET_PERIOD", "5y")
HORIZON = int(os.getenv("PREDICTION_HORIZON_DAYS", "126"))
FRED_KEY = os.getenv("FRED_API_KEY", "")
SEC_UA = os.getenv("SEC_USER_AGENT", "BusinessAnalytics/1.0 contact@example.com")
NEWS_PER_TICKER = int(os.getenv("NEWS_PER_TICKER", "5"))

CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
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


def _safe_float(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def load_yahoo(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    r = requests.get(url, params={"range": MARKET_PERIOD, "interval": "1d", "events": "history"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    ts = result.get("timestamp", [])
    q = result["indicators"]["quote"][0]
    rows = []
    for i, stamp in enumerate(ts):
        close = _safe_float(q.get("close", [None] * len(ts))[i])
        if close is None:
            continue
        rows.append((
            ticker,
            dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).date(),
            _safe_float(q.get("open", [None] * len(ts))[i]),
            _safe_float(q.get("high", [None] * len(ts))[i]),
            _safe_float(q.get("low", [None] * len(ts))[i]),
            close,
            int(q.get("volume", [0] * len(ts))[i] or 0),
            "Yahoo Finance",
        ))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO market_data (ticker,price_date,open_price,high_price,low_price,close_price,volume,source) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE open_price=VALUES(open_price),high_price=VALUES(high_price),low_price=VALUES(low_price),close_price=VALUES(close_price),volume=VALUES(volume),source=VALUES(source)",
                rows,
            )
    print(f"Yahoo {ticker}: {len(rows)} filas")


def load_fred():
    if not FRED_KEY:
        print("FRED omitido: FRED_API_KEY no configurado")
        return
    series = {"FEDFUNDS": "Federal Funds Rate", "CPIAUCSL": "CPI", "UNRATE": "Unemployment Rate", "GDP": "GDP"}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for sid, name in series.items():
                r = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={"series_id": sid, "api_key": FRED_KEY, "file_type": "json"},
                    timeout=30,
                )
                r.raise_for_status()
                rows = []
                for o in r.json().get("observations", []):
                    value = _safe_float(o.get("value"))
                    if value is not None:
                        rows.append((sid, name, o["date"], value))
                cur.executemany(
                    "INSERT INTO economic_indicators (series_id,indicator_name,period_date,value) VALUES (%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE value=VALUES(value), indicator_name=VALUES(indicator_name)",
                    rows,
                )
                print(f"FRED {sid}: {len(rows)} filas")


def _latest_fact(companyfacts, tag):
    facts = companyfacts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    entries = facts.get("USD") or facts.get("USD/shares") or []
    entries = [x for x in entries if x.get("end") and x.get("val") is not None]
    if not entries:
        return None, None
    entries.sort(key=lambda x: (x.get("end", ""), x.get("filed", "")))
    x = entries[-1]
    return x.get("end"), _safe_float(x.get("val"))


def load_sec(ticker):
    cik = CIK.get(ticker)
    if not cik:
        return
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers={"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}, timeout=40)
    r.raise_for_status()
    data = r.json()
    fields = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "net_income": ["NetIncomeLoss"],
        "total_assets": ["Assets"],
        "total_liabilities": ["Liabilities"],
        "equity": ["StockholdersEquity"],
        "eps": ["EarningsPerShareDiluted"],
    }
    vals = {}
    dates = []
    for key, tags in fields.items():
        d = v = None
        for tag in tags:
            d, v = _latest_fact(data, tag)
            if v is not None:
                break
        vals[key] = v
        if d:
            dates.append(d)
    if not dates:
        return
    report_date = max(dates)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fundamentals (ticker,report_date,revenue,net_income,total_assets,total_liabilities,equity,eps,source) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'SEC EDGAR') "
                "ON DUPLICATE KEY UPDATE revenue=VALUES(revenue),net_income=VALUES(net_income),total_assets=VALUES(total_assets),total_liabilities=VALUES(total_liabilities),equity=VALUES(equity),eps=VALUES(eps)",
                (ticker, report_date, vals["revenue"], vals["net_income"], vals["total_assets"], vals["total_liabilities"], vals["equity"], vals["eps"]),
            )
    print(f"SEC {ticker}: actualizado")


def load_gdelt_and_sentiment(ticker):
    query = quote(f'"{COMPANY_QUERY.get(ticker, ticker)}" finance')
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&maxrecords={NEWS_PER_TICKER}&format=json&sort=HybridRel"
    r = requests.get(url, timeout=45)
    r.raise_for_status()
    articles = r.json().get("articles", [])[:NEWS_PER_TICKER]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for a in articles:
                title = (a.get("title") or "").strip()
                if not title:
                    continue
                cur.execute(
                    "INSERT INTO financial_news (ticker,title,url,published_at,source) VALUES (%s,%s,%s,%s,%s)",
                    (ticker, title[:1000], (a.get("url") or "")[:1500], None, a.get("domain") or "GDELT"),
                )
                news_id = cur.lastrowid
                try:
                    s = analyze_sentiment(title)
                    cur.execute(
                        "INSERT INTO sentiment (news_id,ticker,positive_score,neutral_score,negative_score,sentiment_label,sentiment_score) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        (news_id, ticker, s["positive"], s["neutral"], s["negative"], s["label"], s["score"]),
                    )
                except Exception as exc:
                    print(f"FinBERT {ticker}: {exc}")
    print(f"GDELT {ticker}: {len(articles)} noticias")


def _returns(closes, n):
    return (closes[-1] / closes[-1-n] - 1.0) if len(closes) > n and closes[-1-n] else 0.0


def _feature_rows(closes, horizon):
    X, y = [], []
    min_i = 21
    for i in range(min_i, len(closes) - horizon):
        window = closes[: i + 1]
        daily = [(window[j] / window[j-1] - 1.0) for j in range(max(1, len(window)-20), len(window)) if window[j-1]]
        feat = [
            _returns(window, 1),
            _returns(window, 5),
            _returns(window, 20),
            statistics.pstdev(daily) if len(daily) > 1 else 0.0,
        ]
        X.append(feat)
        y.append(1 if closes[i+horizon] > closes[i] else 0)
    return X, y


def train_predict_xgb(ticker):
    import numpy as np
    import xgboost as xgb

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT price_date, close_price FROM market_data WHERE ticker=%s ORDER BY price_date", (ticker,))
            rows = cur.fetchall()
            cur.execute("SELECT AVG(sentiment_score) AS s FROM sentiment WHERE ticker=%s AND created_at >= NOW() - INTERVAL 30 DAY", (ticker,))
            sentiment_row = cur.fetchone()
    closes = [float(r["close_price"]) for r in rows if r["close_price"] is not None]
    if len(closes) < max(180, HORIZON + 50):
        print(f"XGBoost {ticker}: datos insuficientes ({len(closes)})")
        return
    X, y = _feature_rows(closes, HORIZON)
    if len(set(y)) < 2 or len(y) < 50:
        print(f"XGBoost {ticker}: muestra insuficiente")
        return
    split = max(1, int(len(X) * 0.8))
    dtrain = xgb.DMatrix(np.asarray(X[:split], dtype=float), label=np.asarray(y[:split], dtype=float))
    dtest = xgb.DMatrix(np.asarray(X[split:], dtype=float), label=np.asarray(y[split:], dtype=float))
    booster = xgb.train(
        {"objective": "binary:logistic", "eval_metric": "logloss", "max_depth": 3, "eta": 0.08, "subsample": 0.9},
        dtrain,
        num_boost_round=120,
        evals=[(dtest, "test")],
        verbose_eval=False,
    )
    latest_daily = [(closes[j] / closes[j-1] - 1.0) for j in range(max(1, len(closes)-20), len(closes)) if closes[j-1]]
    latest = [[_returns(closes,1), _returns(closes,5), _returns(closes,20), statistics.pstdev(latest_daily) if len(latest_daily)>1 else 0.0]]
    prob = float(booster.predict(xgb.DMatrix(np.asarray(latest, dtype=float)))[0])
    sentiment = float((sentiment_row or {}).get("s") or 0.0)
    final_score = max(0.0, min(1.0, 0.8 * prob + 0.2 * ((sentiment + 1.0) / 2.0)))
    today = dt.date.today()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO predictions (ticker,prediction_date,horizon_days,probability_favorable,predicted_class,model) VALUES (%s,%s,%s,%s,%s,'XGBoost') "
                "ON DUPLICATE KEY UPDATE probability_favorable=VALUES(probability_favorable),predicted_class=VALUES(predicted_class),created_at=CURRENT_TIMESTAMP",
                (ticker, today, HORIZON, prob, 1 if prob >= 0.5 else 0),
            )
            cur.execute("INSERT INTO asset_ranking (ticker,probability_score,sentiment_score,final_score,ranking_position) VALUES (%s,%s,%s,%s,0)", (ticker, prob, sentiment, final_score))
    print(f"XGBoost {ticker}: prob={prob:.4f}, score={final_score:.4f}")


def update_ranks():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id,ticker,final_score FROM asset_ranking WHERE calculated_at >= NOW() - INTERVAL 1 DAY ORDER BY final_score DESC, id DESC")
            rows = cur.fetchall()
            seen = set(); rank = 1
            for row in rows:
                if row["ticker"] in seen:
                    continue
                seen.add(row["ticker"])
                cur.execute("UPDATE asset_ranking SET ranking_position=%s WHERE id=%s", (rank, row["id"]))
                rank += 1


def main():
    init_database()
    for ticker in TICKERS:
        try:
            load_yahoo(ticker)
        except Exception as exc:
            print(f"Yahoo {ticker} ERROR: {exc}")
    try:
        load_fred()
    except Exception as exc:
        print(f"FRED ERROR: {exc}")
    for ticker in TICKERS:
        try:
            load_sec(ticker)
        except Exception as exc:
            print(f"SEC {ticker} ERROR: {exc}")
        try:
            load_gdelt_and_sentiment(ticker)
        except Exception as exc:
            print(f"GDELT/FinBERT {ticker} ERROR: {exc}")
        try:
            train_predict_xgb(ticker)
        except Exception as exc:
            print(f"XGBoost {ticker} ERROR: {exc}")
        time.sleep(0.2)
    update_ranks()
    print("Pipeline finalizado")


if __name__ == "__main__":
    main()
