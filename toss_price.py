"""토스증권 일별 최종 체결가(넥스트·시간외 포함 20시 마감) — wts-cert-api c-chart."""

from __future__ import annotations

from typing import Any

from http_client import get_http_session
from stock_config import STOCK_CATALOG, normalize_stock_code

API_BASE = "https://wts-cert-api.tossinvest.com"
C_CHART_PATH = "/api/v1/c-chart/kr-s/{product_code}/day:1"
REQUEST_TIMEOUT = (2, 6)


def _toss_product_code(stock_code: str) -> str:
    code = normalize_stock_code(stock_code)
    meta = STOCK_CATALOG.get(code, {})
    return str(meta.get("toss_product") or f"A{code}")


def _fetch_candles(
    product_code: str,
    count: int,
    *,
    session: str = "all",
    invest_mode: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"count": count, "session": session}
    if invest_mode:
        params["investMode"] = invest_mode

    response = get_http_session().get(
        f"{API_BASE}{C_CHART_PATH.format(product_code=product_code)}",
        params=params,
        headers={
            "Accept": "application/json",
            "Referer": f"https://www.tossinvest.com/stocks/{product_code}",
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    candles = (result or {}).get("candles") if isinstance(result, dict) else None
    if not isinstance(candles, list) or not candles:
        raise ValueError("토스 일봉 데이터가 비어 있습니다.")
    return candles


def _candles_to_bars(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """API는 최신→과거 순 — 오래된 날짜부터 정렬하고 change_pct 계산."""
    rows: list[dict[str, Any]] = []
    for item in reversed(candles):
        dt = str(item.get("dt", "")).strip()
        close = item.get("close")
        if not dt or close is None:
            continue
        rows.append(
            {
                "date": dt[:10],
                "close": int(close),
            }
        )

    if not rows:
        raise ValueError("유효한 토스 종가를 찾지 못했습니다.")

    prev_close: int | None = None
    for row in rows:
        close = int(row["close"])
        if prev_close:
            row["change_pct"] = round((close - prev_close) / prev_close * 100, 2)
        else:
            row["change_pct"] = 0.0
        prev_close = close
    return rows


def fetch_toss_daily_final_bars(stock_code: str, count: int = 30) -> list[dict[str, Any]]:
    """session=all — 정규장+넥스트·시간외 반영 일별 최종 종가(20시 마감 기준)."""
    product_code = _toss_product_code(stock_code)
    candles = _fetch_candles(product_code, count, session="all")
    return _candles_to_bars(candles)[-count:]


def fetch_toss_krx_daily_bars(stock_code: str, count: int = 30) -> list[dict[str, Any]]:
    """정규장 종가만 — 네이버 보정용."""
    product_code = _toss_product_code(stock_code)
    candles = _fetch_candles(
        product_code,
        count,
        session="all",
        invest_mode="krx",
    )
    return _candles_to_bars(candles)[-count:]


def fetch_extended_change_pct_by_date(
    stock_code: str,
    count: int = 30,
) -> dict[str, float]:
    """날짜별 (최종종가−정규장종가)/정규장종가 % — 네이버 보정용."""
    final_bars = fetch_toss_daily_final_bars(stock_code, count)
    krx_bars = fetch_toss_krx_daily_bars(stock_code, count)
    krx_by_date = {bar["date"]: int(bar["close"]) for bar in krx_bars}
    rates: dict[str, float] = {}
    for bar in final_bars:
        date = str(bar["date"])
        krx_close = krx_by_date.get(date)
        if not krx_close:
            continue
        final_close = int(bar["close"])
        rates[date] = round((final_close - krx_close) / krx_close * 100, 4)
    return rates
