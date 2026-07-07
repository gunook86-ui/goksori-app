"""일별 시세 — 토스 20시 최종 종가 우선, 실패 시 네이버 정규장+시간외 보정."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from http_client import get_http_session
from stock_config import USER_AGENT, normalize_stock_code

NAVER_MOBILE_PRICE_API = "https://m.stock.naver.com/api/stock/{code}/price"
NAVER_MOBILE_BASIC_API = "https://m.stock.naver.com/api/stock/{code}/basic"
NAVER_SISE_JSON_API = "https://api.finance.naver.com/siseJson.naver"
REQUEST_TIMEOUT = (2, 6)


def _parse_price(value: Any) -> int:
    return int(str(value).replace(",", "").strip())


def _parse_change_pct(value: Any) -> float:
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return 0.0
    return float(text)


def _attach_change_pct(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev_close: int | None = None
    for row in rows:
        close = int(row["close"])
        if prev_close:
            row["change_pct"] = round((close - prev_close) / prev_close * 100, 2)
        else:
            row["change_pct"] = 0.0
        prev_close = close
    return rows


def _apply_extended_rate(krx_close: int, extended_pct: float) -> int:
    return int(round(krx_close * (1 + extended_pct / 100)))


def _fetch_from_mobile_api(stock_code: str, count: int) -> list[dict[str, Any]]:
    response = get_http_session().get(
        NAVER_MOBILE_PRICE_API.format(code=stock_code),
        params={"page": 1, "pageSize": count},
        headers={
            "Accept": "application/json",
            "Referer": f"https://m.stock.naver.com/domestic/stock/{stock_code}/price",
            "User-Agent": USER_AGENT,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise ValueError("일별 시세 데이터가 비어 있습니다.")

    rows: list[dict[str, Any]] = []
    for item in reversed(payload):
        traded_at = str(item.get("localTradedAt", "")).strip()
        close_price = item.get("closePrice")
        if not traded_at or close_price is None:
            continue
        rows.append(
            {
                "date": traded_at[:10],
                "close": _parse_price(close_price),
                "change_pct": _parse_change_pct(item.get("fluctuationsRatio", 0)),
            }
        )

    if not rows:
        raise ValueError("유효한 종가 데이터를 찾지 못했습니다.")
    return rows[-count:]


def _fetch_from_sise_json(stock_code: str, count: int) -> list[dict[str, Any]]:
    end = datetime.now()
    start = end - timedelta(days=max(count * 2, 45))
    response = get_http_session().get(
        NAVER_SISE_JSON_API,
        params={
            "symbol": stock_code,
            "requestType": "1",
            "startTime": start.strftime("%Y%m%d"),
            "endTime": end.strftime("%Y%m%d"),
            "timeframe": "day",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    pattern = re.compile(
        r'\["(\d{8})",\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),'
    )
    rows: list[dict[str, Any]] = []
    prev_close: int | None = None
    for match in pattern.finditer(response.text):
        ymd, _open, _high, _low, close = match.groups()
        close_int = int(close)
        change_pct = 0.0
        if prev_close:
            change_pct = (close_int - prev_close) / prev_close * 100
        rows.append(
            {
                "date": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}",
                "close": close_int,
                "change_pct": round(change_pct, 2),
            }
        )
        prev_close = close_int

    if not rows:
        raise ValueError("siseJson 응답에서 종가를 파싱하지 못했습니다.")
    return rows[-count:]


def _fetch_naver_krx_bars(stock_code: str, count: int) -> list[dict[str, Any]]:
    code = normalize_stock_code(stock_code)
    try:
        return _fetch_from_mobile_api(code, count)
    except Exception:
        return _fetch_from_sise_json(code, count)


def _fetch_today_over_market_extended_pct(stock_code: str) -> float | None:
    """당일 넥스트·시간외 최종 등락률(정규장 종가 대비 %)."""
    code = normalize_stock_code(stock_code)
    try:
        response = get_http_session().get(
            NAVER_MOBILE_BASIC_API.format(code=code),
            headers={
                "Accept": "application/json",
                "Referer": f"https://m.stock.naver.com/domestic/stock/{code}",
                "User-Agent": USER_AGENT,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        basic = response.json()
    except Exception:
        return None

    krx_close = _parse_price(basic.get("closePrice"))
    over_market = basic.get("overMarketPriceInfo") or {}
    over_price = over_market.get("overPrice")
    if not krx_close or over_price is None:
        return None
    return round((_parse_price(over_price) - krx_close) / krx_close * 100, 4)


def _synthesize_final_bars_from_naver(stock_code: str, count: int) -> list[dict[str, Any]]:
    """
    토스 일별 최종 종가가 부족할 때:
    네이버 정규장 종가 × (1 + 당일 시간외·넥스트 최종 등락률)로 20시 종가 추정.
    """
    krx_rows = _fetch_naver_krx_bars(stock_code, count)
    extended_by_date: dict[str, float] = {}
    final_by_date: dict[str, int] = {}

    try:
        from toss_price import fetch_extended_change_pct_by_date, fetch_toss_daily_final_bars

        toss_final = fetch_toss_daily_final_bars(stock_code, count)
        final_by_date = {str(bar["date"]): int(bar["close"]) for bar in toss_final}
        extended_by_date = fetch_extended_change_pct_by_date(stock_code, count)
    except Exception:
        pass

    today_ext = _fetch_today_over_market_extended_pct(stock_code)
    if today_ext is not None and krx_rows:
        extended_by_date.setdefault(str(krx_rows[-1]["date"]), today_ext)

    rows: list[dict[str, Any]] = []
    for row in krx_rows:
        date = str(row["date"])
        if date in final_by_date:
            close = final_by_date[date]
        else:
            ext_pct = extended_by_date.get(date, 0.0)
            close = _apply_extended_rate(int(row["close"]), ext_pct)
        rows.append({"date": date, "close": close})

    return _attach_change_pct(rows)


def fetch_daily_bars(stock_code: str, count: int = 30) -> list[dict[str, Any]]:
    """최근 count거래일 20시 최종 종가 — 토스 c-chart 우선, 실패 시 네이버 보정."""
    try:
        from toss_price import fetch_toss_daily_final_bars

        bars = fetch_toss_daily_final_bars(stock_code, count)
        if len(bars) >= min(count, 2):
            return bars[-count:]
    except Exception:
        pass
    return _synthesize_final_bars_from_naver(stock_code, count)


def fetch_daily_closes(stock_code: str, count: int = 30) -> list[tuple[str, int]]:
    """하위 호환용 (날짜, 20시 최종 종가) 목록."""
    return [(bar["date"], int(bar["close"])) for bar in fetch_daily_bars(stock_code, count)]
