"""Yahoo Finance: datos empresariales y eventos históricos adicionales.

El precio diario sigue siendo obtenido por el pipeline y guardado en market_data.
Este módulo añade métricas de valoración, dividendos y splits. Las APIs de Yahoo
son públicas/no oficiales y pueden imponer cuotas: los fallos son no críticos.
"""

import datetime as dt
import math

from database.db import get_connection


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _integer(value):
    number = _number(value)
    return int(number) if number is not None else None


def _text(value, max_length):
    return str(value)[:max_length] if value is not None else None


def _date(value):
    if hasattr(value, "date"):
        return value.date()
    return dt.date.fromisoformat(str(value)[:10])


def save_profile(run_id, ticker, info):
    """No almacena el JSON completo (riesgo de llenar el volumen de Railway)."""
    if not info:
        return False
    values = (
        run_id, ticker,
        _text(info.get("sector"), 150), _text(info.get("industry"), 150),
        _text(info.get("country"), 100), _text(info.get("website"), 400),
        _text(info.get("currency"), 10), _integer(info.get("marketCap")),
        _number(info.get("trailingPE")), _number(info.get("forwardPE")),
        _number(info.get("beta")), _number(info.get("dividendYield")),
        _number(info.get("fiftyTwoWeekHigh")), _number(info.get("fiftyTwoWeekLow")),
        _integer(info.get("averageVolume")),
    )
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO yahoo_company_profile
                    (run_id,ticker,sector,industry,country,website,currency,
                     market_cap,trailing_pe,forward_pe,beta,dividend_yield,
                     fifty_two_week_high,fifty_two_week_low,average_volume)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    sector=VALUES(sector), industry=VALUES(industry),
                    country=VALUES(country), website=VALUES(website),
                    currency=VALUES(currency), market_cap=VALUES(market_cap),
                    trailing_pe=VALUES(trailing_pe),forward_pe=VALUES(forward_pe),
                    beta=VALUES(beta), dividend_yield=VALUES(dividend_yield),
                    fifty_two_week_high=VALUES(fifty_two_week_high),
                    fifty_two_week_low=VALUES(fifty_two_week_low),
                    average_volume=VALUES(average_volume),captured_at=CURRENT_TIMESTAMP
                """,
                values,
            )
    return True


def corporate_actions_from_history(ticker, frame):
    """Extrae únicamente eventos reales (no registra ceros)."""
    rows = []
    if frame is None or frame.empty:
        return rows
    for timestamp, series in frame.iterrows():
        event_date = _date(timestamp)
        for field, event_type in (("Dividends", "DIVIDEND"), ("Stock Splits", "SPLIT")):
            value = _number(series.get(field))
            if value is not None and value > 0:
                rows.append((ticker, event_date, event_type, value))
    return rows


def save_actions(rows):
    if not rows:
        return 0
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO yahoo_corporate_actions (ticker,event_date,event_type,event_value)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE event_value=VALUES(event_value),
                                        fetched_at=CURRENT_TIMESTAMP
                """,
                rows,
            )
    return len(rows)


def load_yahoo_extra(run_id, ticker, period="10y", profile=True, actions=True):
    """Devuelve cifras de enriquecimiento; errores independientes por subfuente."""
    import yfinance as yf  # Dependencia solo del worker, no de Flask.

    source = yf.Ticker(ticker)
    result = {"ticker": ticker, "profile": False, "actions": 0, "warnings": []}
    if profile:
        try:
            result["profile"] = save_profile(run_id, ticker, source.get_info())
        except Exception as exc:
            result["warnings"].append(f"perfil: {type(exc).__name__}: {exc}")
    if actions:
        try:
            history = source.history(period=period, interval="1d", actions=True,
                                     auto_adjust=False, raise_errors=True)
            result["actions"] = save_actions(corporate_actions_from_history(ticker, history))
        except Exception as exc:
            result["warnings"].append(f"dividendos/splits: {type(exc).__name__}: {exc}")
    return result


def load_yahoo_price_fallback(ticker, period):
    """Fallback del endpoint chart: history() produce una serie OHLCV equivalente."""
    import yfinance as yf

    frame = yf.Ticker(ticker).history(period=period, interval="1d",
                                      auto_adjust=False, actions=False,
                                      raise_errors=True)
    if frame is None or frame.empty:
        raise RuntimeError(f"Yahoo Finance sin histórico para {ticker}")
    records = []
    for timestamp, row in frame.iterrows():
        close = _number(row.get("Close"))
        if close is None:
            continue
        records.append((ticker, _date(timestamp), _number(row.get("Open")),
                        _number(row.get("High")), _number(row.get("Low")), close,
                        _number(row.get("Adj Close")) or close,
                        _integer(row.get("Volume")) or 0, None, None, "Yahoo Finance"))
    if not records:
        raise RuntimeError(f"Yahoo Finance sin cierres válidos para {ticker}")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO market_data
                  (ticker,price_date,open_price,high_price,low_price,close_price,
                   adj_close,volume,currency,exchange_name,source)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE open_price=VALUES(open_price),
                    high_price=VALUES(high_price),low_price=VALUES(low_price),
                    close_price=VALUES(close_price),adj_close=VALUES(adj_close),
                    volume=VALUES(volume),source=VALUES(source)
                """, records,
            )
    return len(records)
