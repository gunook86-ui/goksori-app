"""종목 메타데이터 — 코스피/코스닥 시총 상위 10 (requests/API 전용)"""

from __future__ import annotations

MARKET_KOSPI = "코스피"
MARKET_KOSDAQ = "코스닥"

# (종목코드, 종목명) — 시총 상위 10 순서
KOSPI_TOP10: list[tuple[str, str]] = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("373220", "LG에너지솔루션"),
    ("207940", "삼성바이오로직스"),
    ("005380", "현대차"),
    ("000270", "기아"),
    ("068270", "셀트리온"),
    ("105560", "KB금융"),
    ("005490", "POSCO홀딩스"),
    ("055550", "신한지주"),
]

KOSDAQ_TOP10: list[tuple[str, str]] = [
    ("247540", "에코프로비엠"),
    ("086520", "에코프로"),
    ("196170", "알테오젠"),
    ("028300", "HLB"),
    ("068760", "셀트리온제약"),
    ("348370", "엔켐"),
    ("058470", "리노공업"),
    ("277810", "레인보우로보틱스"),
    ("214150", "클래시스"),
    ("403870", "HPSP"),
]

# 토스 GUID는 stock-infos API 조회로만 사용 (하드코딩 캐시 사용 안 함)

STOCK_CATALOG: dict[str, dict[str, str]] = {}

for _code, _name in KOSPI_TOP10:
    STOCK_CATALOG[_code] = {
        "name": _name,
        "market": MARKET_KOSPI,
        "toss_product": f"A{_code}",
    }

for _code, _name in KOSDAQ_TOP10:
    STOCK_CATALOG[_code] = {
        "name": _name,
        "market": MARKET_KOSDAQ,
        "toss_product": f"A{_code}",
    }

DEFAULT_STOCK_CODE = "005930"
DEFAULT_MARKET = MARKET_KOSPI

# 예전 버전에서 잘못 저장된 코드 → 정식 코드
STOCK_CODE_ALIASES: dict[str, str] = {
    "191150": "196170",  # 알테오젠 (구 오타 코드)
}


def normalize_stock_code(stock_code: str) -> str:
    return STOCK_CODE_ALIASES.get(stock_code, stock_code)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def get_market_codes(market: str) -> list[str]:
    if market == MARKET_KOSDAQ:
        return [code for code, _ in KOSDAQ_TOP10]
    return [code for code, _ in KOSPI_TOP10]


def format_stock_label(stock_code: str) -> str:
    meta = STOCK_CATALOG[stock_code]
    return f"{meta['name']} ({stock_code})"


def get_stock_name(stock_code: str) -> str:
    return STOCK_CATALOG[stock_code]["name"]


def get_all_top20_stocks() -> list[tuple[str, str]]:
    """코스피·코스닥 시총 상위 10 종목 전체 (코드, 종목명)."""
    return list(KOSPI_TOP10 + KOSDAQ_TOP10)
