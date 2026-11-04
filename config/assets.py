"""Universo de empresas y referencias de mercado para InversIA.

TICKERS contiene exclusivamente empresas; BENCHMARK_TICKER se procesa aparte.
"""

import os


DEFAULT_TICKERS = (
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "NFLX", "AMD", "ORCL",
)

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "TSLA": "Tesla, Inc.",
    "NFLX": "Netflix, Inc.",
    "AMD": "Advanced Micro Devices, Inc.",
    "ORCL": "Oracle Corporation",
}

SEC_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "TSLA": "0001318605",
    "NFLX": "0001065280",
    "AMD": "0000002488",
    "ORCL": "0001341439",
}

COMPANY_QUERY = {
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet Google",
    "META": "Meta Platforms",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "AMD": "Advanced Micro Devices",
    "ORCL": "Oracle",
}


def configured_tickers():
    raw = os.getenv("TICKERS", ",".join(DEFAULT_TICKERS))
    tickers = [value.strip().upper() for value in raw.split(",") if value.strip()]
    if not tickers or len(tickers) != len(set(tickers)):
        raise ValueError("TICKERS debe contener símbolos únicos y no estar vacío")
    if len(tickers) != 10:
        raise ValueError("La vista de 10 empresas requiere exactamente 10 símbolos en TICKERS")
    if {"SPY", "QQQ"}.intersection(tickers):
        raise ValueError("SPY y QQQ son ETFs: use diez empresas y deje SPY como BENCHMARK_TICKER")
    return tickers
