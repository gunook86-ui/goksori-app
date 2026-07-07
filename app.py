"""
공포·탐욕 인간지표 대시보드 (Streamlit)
- 네이버: requests + HTML 파싱
- 토스: wts-cert-api requests
- Selenium / webdriver 사용 없음
"""

from __future__ import annotations

import html
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.modules.pop("member_auth", None)
from member_auth import (
    MEMBER_GATE_CSS,
    MEMBER_VOTE_LOCK_KEY,
    init_member_session,
    is_member,
    render_compact_kakao_cta,
    render_member_gate,
    show_vote_gate_if_needed,
)
from stock_votes import (
    add_stock_vote,
    get_stock_vote_counts,
    is_vote_locked_for_stock,
    set_vote_locked_for_stock,
)
from accuracy_badge import (
    get_member_badge,
    inject_accuracy_badge_css,
    init_vote_accuracy_session,
    record_member_vote,
)
from stock_config import (
    DEFAULT_STOCK_CODE,
    MARKET_KOSDAQ,
    MARKET_KOSPI,
    format_stock_label,
    get_market_codes,
    get_stock_name,
)


APP_VERSION = "20260708o"
BACKTEST_LOOKBACK_DAYS = 30
BACKTEST_SIM_INVESTMENT = 10_000_000
TARGET_POST_COUNT = 100
MAX_SCAN_PAGES = 20
RANKING_POST_LIMIT = 40
LEGEND_DRIP_COUNT = 3
HANRIVER_FEAR_KEY = "hanriver_fear_votes"  # legacy — stock_votes.py 사용
HANRIVER_GREED_KEY = "hanriver_greed_votes"
LOCAL_MODULES = (
    "http_client",
    "stock_config",
    "sentiment_core",
    "naver_scraper",
    "toss_scraper",
    "naver_price",
    "backtest_core",
)


def _load_fresh_analyzers():
    """Streamlit이 예전 scraper 모듈을 붙잡는 문제 방지."""
    import sys as _sys

    for module_name in LOCAL_MODULES:
        _sys.modules.pop(module_name, None)
    from naver_scraper import analyze_naver_board
    from toss_scraper import analyze_toss_community

    return analyze_naver_board, analyze_toss_community


def _load_fresh_backtest():
    """Streamlit이 예전 naver_price/backtest_core 모듈을 붙잡는 문제 방지."""
    import sys as _sys

    for module_name in ("toss_price", "naver_price", "backtest_core"):
        _sys.modules.pop(module_name, None)
    from backtest_core import build_contrarian_backtest

    return build_contrarian_backtest

# 구 버전 세션/캐시 호환 (알테오젠 오타 코드)
LEGACY_STOCK_CODES = {"191150": "196170"}


def normalize_stock_code(stock_code: str) -> str:
    return LEGACY_STOCK_CODES.get(stock_code, stock_code)

st.set_page_config(
    page_title="인간지표 대시보드",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

MOBILE_FRAME_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
/* ── 토스 감성 글로벌 베이스 ── */
[data-testid="stAppViewContainer"] {
    background-color: #F4F6F8 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}
[data-testid="stMain"] {
    margin-left: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    background: #F4F6F8 !important;
}
[data-testid="stMainBlockContainer"] {
    max-width: 450px !important;
    width: 100% !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 2.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-bottom: 2rem !important;
    overflow-x: hidden !important;
    background: transparent !important;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
[data-testid="stVerticalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    gap: 0.5rem !important;
}
[data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    gap: 0.5rem !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: none !important;
}
/* ── 탭: 가로 스크롤 세그먼트 ── */
[data-testid="stTabs"] {
    width: 100% !important;
    max-width: 100% !important;
    background: transparent !important;
}
[data-testid="stTabs"] .st-dr {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    width: 100% !important;
}
[data-testid="stTabs"] [role="tablist"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    gap: 0 !important;
    width: 100% !important;
    padding: 0 0 0 0 !important;
    margin-bottom: 4px !important;
    border-bottom: 1px solid #e5e8eb !important;
    scrollbar-width: none !important;
    -webkit-overflow-scrolling: touch !important;
}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
    display: none !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
    flex: 0 0 auto !important;
    min-width: max-content !important;
    max-width: none !important;
    width: auto !important;
    padding: 12px 16px !important;
    margin: 0 !important;
    font-size: 0.9375rem !important;
    font-weight: 600 !important;
    line-height: 1.3 !important;
    letter-spacing: -0.02em !important;
    white-space: nowrap !important;
    color: #8b95a1 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #191f28 !important;
    font-weight: 800 !important;
    border-bottom: 2px solid #3182F6 !important;
}
[data-testid="stTabs"] div[data-baseweb="tab-panel"],
[data-testid="stTabs"] .st-dr > .st-co {
    width: 100% !important;
    max-width: 100% !important;
    padding-top: 12px !important;
}
/* ── 버튼: 토스 블루 알약 ── */
[data-testid="stButton"] > button {
    font-family: 'Pretendard', -apple-system, sans-serif !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    font-size: 0.9375rem !important;
    letter-spacing: -0.02em !important;
    padding: 0.75rem 1.25rem !important;
    border: none !important;
    box-shadow: none !important;
    transition: opacity 0.15s ease !important;
}
[data-testid="stButton"] > button[kind="primary"] {
    background: #3182F6 !important;
    color: #ffffff !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1b64da !important;
    color: #ffffff !important;
    border: none !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background: #f2f4f6 !important;
    color: #333d4b !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #e5e8eb !important;
    color: #191f28 !important;
}
/* ── 입력 필드 ── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    border-radius: 16px !important;
    border: 1px solid #e5e8eb !important;
    background: #ffffff !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.9375rem !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stSelectbox"] > div > div {
    border-radius: 14px !important;
    border-color: #e5e8eb !important;
    background: #ffffff !important;
}
[data-testid="stRadio"] label {
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}
div[data-testid="stPlotlyChart"] {
    width: 100% !important;
    max-width: 100% !important;
    border-radius: 20px !important;
    overflow: hidden !important;
}
.gap-insight, .score-sub {
    word-break: keep-all !important;
    overflow-wrap: anywhere !important;
}
hr {
    border: none !important;
    border-top: 1px solid #e5e8eb !important;
    margin: 20px 0 !important;
}
</style>
"""
st.markdown(MOBILE_FRAME_CSS, unsafe_allow_html=True)

MOBILE_CSS = """
<style>
    .block-container { padding-bottom: 1.4rem; }
    section[data-testid="stSidebar"] .block-container {
        max-width: 100%; padding-top: 0.5rem; padding-left: 0.75rem; padding-right: 0.75rem;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
        width: 100%; min-width: 0; white-space: nowrap !important;
        border-radius: 10px; font-weight: 600; padding: 0.45rem 0.8rem;
    }
    div[data-testid="stTabs"] {
        margin-top: 0.5rem; width: 100%;
    }
    div[data-testid="stTabs"] div[data-baseweb="tab-panel"] {
        padding-top: 0.35rem !important;
    }
    .tab-section-gap { margin-top: 0.75rem; }
    .app-header { text-align: left; padding: 4px 0 16px 0; }
    .app-header h1 {
        font-size: 1.35rem; font-weight: 800; margin: 0; color: #191f28;
        letter-spacing: -0.03em; line-height: 1.3;
    }
    .app-header p {
        font-size: 0.8125rem; color: #8b95a1; margin: 6px 0 0 0;
        font-weight: 500; letter-spacing: -0.01em;
    }
    .score-display { text-align: center; margin: 4px 0 18px 0; }
    .score-status { font-size: 1.1rem; font-weight: 600; margin: 8px 0 0 0; }
    .score-sub {
        font-size: 0.875rem; color: #333d4b; margin-top: 12px; line-height: 1.6;
        padding: 16px 18px; background: #ffffff; border-radius: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); border: none;
        font-weight: 500; letter-spacing: -0.02em;
    }
    .gauge-box { max-width: 330px; margin: 0 auto 2px auto; overflow: visible; }
    .gauge-labels {
        display: flex; justify-content: space-between; max-width: 290px;
        margin: 2px auto 0 auto; font-size: 0.75rem; color: #8b9099; font-weight: 600; padding: 0 6px;
    }
    .post-list-title {
        font-size: 1rem; font-weight: 800; color: #191f28;
        margin: 20px 0 12px 0; letter-spacing: -0.02em;
    }
    .post-table-wrap {
        max-height: 360px; overflow-y: auto; overflow-x: hidden;
        border-radius: 20px; margin-bottom: 16px;
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .post-table {
        width: 100%; border-collapse: collapse; font-size: 0.82rem; table-layout: fixed;
    }
    .post-table thead th {
        position: sticky; top: 0; z-index: 1;
        background: #f8f9fb; color: #1a1a2e; font-weight: 700;
        padding: 8px 10px; border-bottom: 1px solid #eef0f4; text-align: left;
    }
    .post-table .post-no-h, .post-table .post-no {
        width: 44px; text-align: center; vertical-align: top;
    }
    .post-table td {
        padding: 7px 10px; border-bottom: 1px solid #f0f2f6;
        vertical-align: top; line-height: 1.45; word-break: break-all;
    }
    .post-table tbody tr:last-child td { border-bottom: none; }
    .post-table .post-title a {
        color: #1a73e8; text-decoration: none; font-weight: 500;
    }
    .post-table .post-title a:hover { text-decoration: underline; }
    .refresh-ad-gate-wrap {
        margin: 12px 0 16px 0; padding: 24px 20px;
        border-radius: 20px;
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        text-align: center;
    }
    .ad-gate-badge {
        display: inline-block; background: #e8f3ff; color: #3182f6;
        font-size: 0.6875rem; font-weight: 700; padding: 4px 10px;
        border-radius: 999px; letter-spacing: 0.02em;
    }
    .refresh-ad-msg {
        color: #191f28; font-size: 0.9375rem; font-weight: 700;
        margin: 12px 0 16px 0; line-height: 1.55; letter-spacing: -0.02em;
    }
    .refresh-ad-bar {
        height: 4px; background: #f2f4f6;
        border-radius: 999px; overflow: hidden; margin: 0 auto;
        max-width: 280px;
    }
    .refresh-ad-bar-fill {
        height: 100%; width: 8%;
        background: #3182F6;
        border-radius: 999px;
        animation: ad-bar-load 2s ease-in-out forwards;
    }
    @keyframes ad-bar-load {
        from { width: 8%; }
        to { width: 100%; }
    }
    .refresh-ad-hint {
        color: #8b95a1; font-size: 0.75rem; margin: 14px 0 0 0;
        line-height: 1.45; font-weight: 500;
    }
    .ad-membership-card {
        margin: 16px 0 8px 0; padding: 20px;
        border-radius: 20px;
        background: #ffffff;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        text-align: center; border: none;
    }
    .ad-membership-card .ad-badge {
        display: inline-block; background: #f2f4f6; color: #6b7684;
        font-size: 0.6875rem; font-weight: 700; padding: 3px 10px;
        border-radius: 999px; letter-spacing: 0.02em; margin-bottom: 10px;
    }
    .ad-membership-card p {
        margin: 0; font-size: 0.875rem; line-height: 1.6; color: #333d4b;
        font-weight: 500; letter-spacing: -0.02em;
    }
    .ad-membership-card strong { color: #191f28; font-weight: 800; }
    .ad-banner {
        margin-top: 24px; height: 60px;
        background: linear-gradient(135deg, #eceff3 0%, #dfe3ea 100%);
        border-radius: 12px; display: flex; align-items: center; justify-content: center;
        color: #7a8088; font-size: 0.82rem; font-weight: 600; border: 1px dashed #cfd5df;
    }
    div[data-testid="column"] div[data-testid="stButton"] > button,
    div[data-baseweb="tab-panel"] div[data-testid="stButton"] > button {
        width: 100%; min-width: 0; white-space: nowrap !important;
    }
    div[data-testid="stDataFrame"] div[data-testid="StyledFullScreenFrame"] {
        border-radius: 12px; overflow: hidden; border: 1px solid #eef0f4;
    }
    div[data-testid="stDataFrame"] th:first-child,
    div[data-testid="stDataFrame"] td:first-child,
    div[data-testid="stDataFrame"] div[role="columnheader"]:first-child,
    div[data-testid="stDataFrame"] div[role="gridcell"]:first-child {
        text-align: center !important;
    }
    div[data-testid="stDataFrame"] th:first-child > div,
    div[data-testid="stDataFrame"] td:first-child > div,
    div[data-testid="stDataFrame"] div[role="columnheader"]:first-child > div,
    div[data-testid="stDataFrame"] div[role="gridcell"]:first-child > div {
        justify-content: center !important;
        text-align: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    .killer-card {
        border-radius: 20px; padding: 20px; margin: 16px 0;
        border: none; background: #ffffff;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .killer-card h4 {
        font-size: 1rem; font-weight: 800; color: #191f28;
        margin: 0 0 8px 0; letter-spacing: -0.02em;
    }
    .killer-card p {
        font-size: 0.875rem; color: #333d4b; line-height: 1.6; margin: 0;
        font-weight: 500; letter-spacing: -0.02em;
    }
    .alert-card {
        background: #ffffff;
    }
    .gap-insight {
        font-size: 0.875rem; color: #333d4b; line-height: 1.6;
        padding: 16px 18px; background: #ffffff; border-radius: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); border: none;
        border-left: 4px solid #3182f6; margin-top: 12px;
        font-weight: 500; letter-spacing: -0.02em;
    }
    .proto-badge {
        display: inline-block; font-size: 0.68rem; font-weight: 700;
        color: #7c4dff; background: #ede7f6; padding: 2px 8px;
        border-radius: 999px; margin-left: 6px; vertical-align: middle;
    }
    .rank-board-title {
        font-size: 1rem; font-weight: 800; color: #191f28;
        margin: 0 0 12px 0; letter-spacing: -0.02em;
    }
    .rank-board-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
        width: 100%;
        max-width: 100%;
    }
    .rank-card {
        border-radius: 16px; padding: 14px 8px; text-align: center;
        border: none; background: #ffffff;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03); min-height: 92px;
    }
    .rank-card.rank-1 { background: #ffffff; }
    .rank-card.rank-2 { background: #ffffff; }
    .rank-card.rank-3 { background: #ffffff; }
    .rank-medal {
        font-size: 0.875rem; font-weight: 800; color: #3182f6;
        line-height: 1; background: #e8f3ff; width: 28px; height: 28px;
        border-radius: 999px; display: flex; align-items: center;
        justify-content: center; margin: 0 auto 6px auto;
    }
    .rank-name {
        font-size: 0.8125rem; font-weight: 800; color: #191f28;
        margin: 6px 0 4px 0; line-height: 1.25; word-break: keep-all;
        letter-spacing: -0.02em;
    }
    .rank-score {
        font-size: 0.8125rem; font-weight: 800; color: #3182f6; line-height: 1.3;
    }
    .rank-status { font-size: 0.75rem; color: #8b95a1; font-weight: 500; }
    .legend-card {
        border-radius: 20px; padding: 20px 20px 8px 20px; margin: 16px 0;
        background: #ffffff; border: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    .legend-header {
        font-size: 1rem; font-weight: 800; color: #191f28;
        margin: 0 0 14px 0; letter-spacing: -0.02em;
    }
    .legend-drip {
        padding: 14px 16px; border-radius: 16px; margin-bottom: 12px;
        font-size: 0.875rem; line-height: 1.55; font-weight: 600;
        background: #f9fafb; letter-spacing: -0.02em;
    }
    .legend-drip a {
        color: #333d4b; text-decoration: none; display: block;
    }
    .legend-drip-fear {
        background: #f9fafb; color: #333d4b; border-left: 4px solid #3182f6;
    }
    .legend-drip-greed {
        background: #f9fafb; color: #333d4b; border-left: 4px solid #8b95a1;
    }
    div[data-testid="stDataFrame"] div[role="gridcell"] {
        font-size: 0.82rem !important;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        min-height: 28px !important;
    }
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        font-size: 0.82rem !important;
        min-height: 32px !important;
    }
    .hanriver-card {
        border-radius: 14px; padding: 14px 16px; margin: 18px 0 8px 0;
        border: 1px solid #dbeafe; background: linear-gradient(135deg, #f0f9ff 0%, #fff 100%);
        box-shadow: 0 2px 8px rgba(26, 26, 46, 0.04);
    }
    .hanriver-card h4 {
        font-size: 0.95rem; font-weight: 800; color: #1a1a2e; margin: 0 0 10px 0;
        text-align: center;
    }
    .hanriver-bar-wrap {
        display: flex; height: 28px; border-radius: 999px; overflow: hidden;
        border: 1px solid #eef0f4; margin: 10px 0 8px 0;
    }
    .hanriver-bar-fear {
        background: linear-gradient(90deg, #ef5350, #e53935);
        transition: width 0.3s ease;
    }
    .hanriver-bar-greed {
        background: linear-gradient(90deg, #66bb6a, #43a047);
        transition: width 0.3s ease;
    }
    .hanriver-stats {
        display: flex; justify-content: space-between; font-size: 0.76rem;
        font-weight: 700; color: #555; margin-top: 4px;
    }
    .hanriver-caption {
        text-align: center; font-size: 0.78rem; color: #666;
        margin-top: 8px; line-height: 1.4;
    }
    .hanriver-compact-card {
        border-radius: 16px; padding: 14px 14px 10px 14px; margin: 0 0 14px 0;
        background: #ffffff;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.04);
        border: 1px solid #eef0f4;
    }
    .cpr-unified-card [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 10px 12px 8px 12px !important;
        margin-bottom: 8px !important;
        border-radius: 16px !important;
        border-color: #eef0f4 !important;
        background: #ffffff !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03) !important;
    }
    .cpr-vote-head {
        font-size: 0.9375rem; font-weight: 800; color: #191f28;
        margin: 0; letter-spacing: -0.03em; line-height: 1.3;
    }
    .cpr-vote-sub {
        font-size: 0.75rem; font-weight: 600; color: #8b95a1;
        margin: 2px 0 8px 0; letter-spacing: -0.01em;
    }
    .cpr-vote-lock {
        font-size: 0.6875rem; font-weight: 600; color: #adb5bd;
        margin: 0 0 6px 0; line-height: 1.4;
    }
    .cpr-vote-bar-wrap {
        display: flex; height: 20px; border-radius: 999px; overflow: hidden;
        border: 1px solid #eef0f4; margin: 6px 0 4px 0;
    }
    .cpr-vote-stats {
        display: flex; justify-content: space-between;
        font-size: 0.6875rem; font-weight: 700; color: #6b7684;
        margin: 0 0 6px 0;
    }
    .cpr-compose-divider {
        border-top: 1px solid #f2f4f6; margin: 6px 0 4px 0;
    }
    .cpr-external-lurk .post-list-title {
        margin: 10px 0 8px 0 !important;
        font-size: 0.9375rem;
    }
    .cpr-external-lurk .legend-card {
        margin-bottom: 10px;
    }
    .cpr-external-lurk .legend-drip {
        padding: 10px 12px; margin-bottom: 8px;
    }
    .cpr-external-lurk .post-table-wrap {
        max-height: 280px; margin-bottom: 10px;
    }
    #cpr-tab-compose [data-testid="stTextArea"] {
        margin-bottom: 4px !important;
    }
    #cpr-tab-compose [data-testid="stTextArea"] textarea {
        min-height: 64px !important; font-size: 0.875rem !important;
    }
    #cpr-tab-compose [data-testid="stButton"] > button {
        min-height: 40px !important; margin-top: 0 !important;
    }
    #cpr-onepass-tap [data-testid="stButton"] > button {
        min-height: 40px !important;
        padding: 10px 14px !important;
        font-size: 0.875rem !important;
        box-shadow: none !important;
        border: 1px dashed #d1d6db !important;
        border-radius: 12px !important;
        background: #fafbfc !important;
    }
    .hanriver-compact-head {
        font-size: 0.8125rem; font-weight: 800; color: #191f28;
        margin: 0 0 8px 0; letter-spacing: -0.02em;
    }
    .hanriver-compact-lock {
        font-size: 0.75rem; font-weight: 600; color: #8b95a1;
        margin: 0 0 10px 0; line-height: 1.45; letter-spacing: -0.01em;
    }
    .hanriver-bar-wrap.compact { height: 22px; margin: 8px 0 6px 0; }
    .hanriver-stats.compact {
        font-size: 0.6875rem; margin-top: 2px;
    }
    .backtest-tab-title {
        margin: 0 0 10px 0 !important;
    }
    .backtest-infographic {
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
        padding: 16px 14px 14px 14px;
        margin-bottom: 10px;
        letter-spacing: -0.02em;
    }
    .backtest-sim-question {
        font-size: 0.8125rem; font-weight: 600; color: #6b7684;
        margin: 0 0 10px 0; line-height: 1.5;
    }
    .backtest-sim-question b { color: #191f28; font-weight: 800; }
    .backtest-sim-value-row {
        display: flex; flex-wrap: wrap; align-items: baseline;
        justify-content: space-between; gap: 8px;
        margin-bottom: 6px;
    }
    .backtest-sim-label {
        font-size: 0.75rem; font-weight: 600; color: #8b95a1;
    }
    .backtest-sim-value {
        font-size: 1.375rem; font-weight: 900; color: #191f28;
        letter-spacing: -0.04em; line-height: 1.2;
    }
    .backtest-sim-profit {
        font-size: 0.9375rem; font-weight: 800; letter-spacing: -0.03em;
        margin: 0 0 14px 0;
    }
    .backtest-return-badge {
        display: inline-flex; align-items: center;
        padding: 5px 10px; border-radius: 999px;
        font-size: 0.8125rem; font-weight: 800;
        margin-bottom: 14px;
    }
    .backtest-return-badge.up {
        background: #fff0f0; color: #e53935;
    }
    .backtest-return-badge.down {
        background: #eef4ff; color: #3182f6;
    }
    .backtest-timeline-head {
        font-size: 0.6875rem; font-weight: 700; color: #adb5bd;
        margin: 0 0 8px 0; text-transform: uppercase; letter-spacing: 0.04em;
    }
    .backtest-timeline-track {
        position: relative; height: 10px;
        background: #f2f4f6; border-radius: 999px;
        margin: 28px 0 8px 0; overflow: visible;
    }
    .backtest-timeline-fill {
        position: absolute; top: 0; height: 100%;
        border-radius: 999px; min-width: 4px;
    }
    .backtest-timeline-fill.up {
        background: linear-gradient(90deg, #ffcdd2 0%, #e53935 100%);
    }
    .backtest-timeline-fill.down {
        background: linear-gradient(90deg, #bbdefb 0%, #3182f6 100%);
    }
    .backtest-timeline-node {
        position: absolute; top: 50%; transform: translate(-50%, -50%);
        width: 14px; height: 14px; border-radius: 50%;
        background: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        border: 3px solid #191f28; z-index: 2;
    }
    .backtest-timeline-node.current {
        border-color: #e53935; width: 16px; height: 16px;
    }
    .backtest-timeline-node.current.down-node {
        border-color: #3182f6;
    }
    .backtest-timeline-meta {
        display: flex; justify-content: space-between; gap: 8px;
        margin-bottom: 4px;
    }
    .backtest-timeline-point {
        flex: 1; min-width: 0;
    }
    .backtest-timeline-point.right { text-align: right; }
    .backtest-timeline-tag {
        font-size: 0.6875rem; font-weight: 700; color: #adb5bd;
        margin-bottom: 2px;
    }
    .backtest-timeline-price {
        font-size: 0.8125rem; font-weight: 800; color: #191f28;
        word-break: keep-all;
    }
    .backtest-timeline-date {
        font-size: 0.6875rem; font-weight: 600; color: #8b95a1;
        margin-top: 2px;
    }
    .backtest-top3-wrap {
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
        padding: 14px 12px 12px 12px;
    }
    .backtest-top3-title {
        font-size: 0.875rem; font-weight: 800; color: #191f28;
        margin: 0 0 10px 0; letter-spacing: -0.03em;
    }
    .backtest-top3-chip {
        display: block; padding: 10px 12px; margin-bottom: 8px;
        background: #f9fafb; border-radius: 14px;
        font-size: 0.75rem; line-height: 1.55; color: #4e5968;
        font-weight: 500; word-break: keep-all;
    }
    .backtest-top3-chip:last-child { margin-bottom: 0; }
    .backtest-top3-chip b { color: #191f28; font-weight: 800; }
    .backtest-top3-chip .chip-return.up { color: #e53935; font-weight: 800; }
    .backtest-top3-chip .chip-return.down { color: #3182f6; font-weight: 800; }
    .backtest-foot {
        margin: 10px 0 0 0; font-size: 0.75rem; color: #8b95a1;
        font-weight: 600; text-align: center;
    }
    div[data-testid="column"] .stButton > button[kind="secondary"] {
        font-size: 0.82rem !important;
    }
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def render_css_gauge(score: float) -> None:
    needle_angle = -90 + (score / 100) * 180
    tick_labels: list[str] = []
    label_radius = 92
    for value in range(0, 101, 10):
        rad = math.pi * (1 - value / 100)
        x = 110 + label_radius * math.cos(rad)
        y = 108 - label_radius * math.sin(rad)
        tick_labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="9.5" fill="#5f6672" '
            f'font-weight="600">{value}</text>'
        )
    ticks = "\n".join(tick_labels)
    st.markdown(
        f"""
        <div class="gauge-box">
          <svg viewBox="-8 -4 236 128" width="100%" height="190" overflow="visible">
            <defs>
              <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#ffcdd2"/>
                <stop offset="25%" stop-color="#ffccbc"/>
                <stop offset="50%" stop-color="#fff9c4"/>
                <stop offset="75%" stop-color="#dcedc8"/>
                <stop offset="100%" stop-color="#c8e6c9"/>
              </linearGradient>
            </defs>
            <path d="M 28 108 A 82 82 0 0 1 192 108"
                  fill="none" stroke="url(#gaugeGrad)" stroke-width="20" stroke-linecap="round"/>
            {ticks}
            <g transform="translate(110,108) rotate({needle_angle})">
              <polygon points="0,-70 -4.5,-8 4.5,-8" fill="#1a1a2e"/>
            </g>
            <circle cx="110" cy="108" r="8" fill="#1a1a2e"/>
          </svg>
        </div>
        <div class="gauge-labels"><span>공포</span><span>평온</span><span>탐욕</span></div>
        """,
        unsafe_allow_html=True,
    )


def format_score_summary(data: dict) -> str:
    if data["is_neutral"]:
        return "감지된 공포·탐욕 키워드가 없어 중립(평온) 상태입니다."

    fear_text = f"공포 {data['fear_count']}회"
    if data.get("fear_breakdown"):
        fear_text += f"({data['fear_breakdown']})"

    greed_text = f"탐욕 {data['greed_count']}회"
    if data.get("greed_breakdown"):
        greed_text += f"({data['greed_breakdown']})"

    return f"{fear_text} · {greed_text}"


def _score_or_default(data: dict | None) -> float:
    if data and data.get("post_count", 0) > 0:
        return float(data.get("score_raw", 50))
    return 50.0


def render_push_alert_card(stock_code: str, current_score: int) -> None:
    """🚨 실시간 곡소리 푸시 알림 시뮬레이터 (프로토타입)."""
    toggle_key = f"push_alert_{stock_code}"
    if toggle_key not in st.session_state:
        st.session_state[toggle_key] = True

    col_text, col_toggle = st.columns([5, 1])
    with col_text:
        st.markdown(
            """
            <div class="killer-card alert-card">
                <h4>🚨 실시간 곡소리 알림 설정</h4>
                <p>현재 선택된 종목의 공포 지수가 <b>20점 이하(극단적 공포)</b>로
                떨어지면 스마트폰 푸시 알림을 보냅니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_toggle:
        st.write("")
        st.write("")
        enabled = st.toggle("알림", key=toggle_key, label_visibility="collapsed")
        if enabled and current_score <= 20:
            st.caption("🔔 발송 대기")
        elif enabled:
            st.caption("✅ ON")
        else:
            st.caption("⏸ OFF")


def _shared_mood_label(naver_score: float, toss_score: float) -> str:
    avg_score = (naver_score + toss_score) / 2
    if avg_score <= 20:
        return "극단적 공포"
    if avg_score <= 40:
        return "공포"
    if avg_score <= 60:
        return "평온"
    if avg_score <= 80:
        return "탐욕"
    return "극단적 탐욕"


def _sync_mood_phrase(mood: str) -> str:
    phrases = {
        "극단적 공포": "양쪽 모두 한마음으로 <b>극단적 공포</b> 곡소리를 터뜨리는 중!",
        "공포": "양쪽 모두 한마음으로 <b>공포</b> 분위기를 공유하는 중!",
        "평온": "양쪽 모두 조용히 <b>평온</b> 모드를 유지하는 중!",
        "탐욕": "양쪽 모두 한마음으로 <b>탐욕</b> 불꽃을 키우는 중!",
        "극단적 탐욕": "양쪽 모두 한마음으로 <b>극단적 탐욕</b>을 외치는 중!",
    }
    return phrases[mood]


def _platform_gap_commentary(naver_score: float, toss_score: float) -> str:
    diff = toss_score - naver_score
    abs_diff = abs(diff)

    if abs_diff < 5:
        mood = _shared_mood_label(naver_score, toss_score)
        return (
            "💡 현재 네이버와 토스 개미들의 심리가 완벽하게 동기화되었습니다. "
            f"시장을 바라보는 눈높이도 비슷하고, {_sync_mood_phrase(mood)}"
        )
    if diff >= 5:
        return (
            f"💡 플랫폼 심리 격차 <b>{abs_diff:.0f}점</b> — "
            "네이버 형님들은 이미 한강 물 온도 체크 중인데, "
            "토스 젊은 개미들은 야수의 심장으로 아직 버티는 중입니다!"
        )
    return (
        f"💡 플랫폼 심리 격차 <b>{abs_diff:.0f}점</b> — "
        "토스방 개미들은 멘탈 터져서 패닉셀 중인데, "
        "짬에서 나오는 바이브일까요? 네이버 형님들은 오히려 침착하게 줍줍을 노리고 있습니다."
    )


def render_platform_gap_panel(
    naver_data: dict | None,
    toss_data: dict | None,
    stock_name: str,
) -> None:
    """🤼 네이버 vs 토스 심리 격차 분석 (프로토타입 + 실데이터 점수)."""
    naver_score = _score_or_default(naver_data)
    toss_score = _score_or_default(toss_data)

    st.markdown(
        '<p class="post-list-title">🤼 두 플랫폼간 심리 격차 분석'
        '<span class="proto-badge">PROTOTYPE</span></p>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["📗 네이버", "💙 토스"],
            y=[naver_score, toss_score],
            marker_color=["#43a047", "#5c6bc0"],
            text=[f"{naver_score:.0f}점", f"{toss_score:.0f}점"],
            textposition="outside",
            width=[0.45, 0.45],
        )
    )
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=24, b=10),
        yaxis=dict(range=[0, 105], title="", gridcolor="#f0f0f0"),
        xaxis=dict(title=""),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="sans-serif", size=12, color="#333"),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    commentary = _platform_gap_commentary(naver_score, toss_score)
    st.markdown(f'<div class="gap-insight">{commentary}</div>', unsafe_allow_html=True)


def _format_won(amount: int) -> str:
    """대형주(200만 원대+) 포함 — 정수 원화 고정 포맷."""
    return f"{max(int(amount), 0):,}원"


def _format_signed_won(amount: int) -> str:
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(int(amount)):,}원"


def _html_pct(value: float, *, signed: bool = True) -> str:
    """Streamlit markdown이 '%'를 포맷 문자로 오인하는 문제 방지."""
    if signed:
        sign = "+" if value >= 0 else ""
        return f"{sign}{value}&#37;"
    return f"{value}&#37;"


def _css_pct(value: float) -> str:
    return f"{value}&#37;"


def _timeline_layout(buy_price: int, current_price: int) -> dict[str, float]:
    """과거 vs 현재 타임라인 노드·채움 비율."""
    low = min(buy_price, current_price)
    high = max(buy_price, current_price)
    span = max(high - low, max(buy_price, current_price) // 50, 1)
    scale_min = low - span * 0.08
    scale_max = high + span * 0.08
    width = scale_max - scale_min
    buy_pos = (buy_price - scale_min) / width * 100
    current_pos = (current_price - scale_min) / width * 100
    fill_left = min(buy_pos, current_pos)
    fill_width = max(abs(current_pos - buy_pos), 2.5)
    return {
        "buy_pos": round(buy_pos, 2),
        "current_pos": round(current_pos, 2),
        "fill_left": round(fill_left, 2),
        "fill_width": round(fill_width, 2),
    }


def _render_top3_chips(episodes: list[dict]) -> str:
    if not episodes:
        return ""

    chips: list[str] = []
    for ep in episodes:
        rank = int(ep["rank"])
        buy_date = str(ep["buy_date"])[:10]
        fear = int(ep["buy_fear_score"])
        buy_price = int(ep["buy_price"])
        ret = float(ep["return_pct"])
        ret_class = "up" if ret >= 0 else "down"
        chips.append(
            f'<div class="backtest-top3-chip">'
            f"<b>{rank}위 타점</b>: {html.escape(buy_date)} "
            f"(공포 {fear}점) | 당시 {_format_won(buy_price)} "
            f'➡️ 현재 <span class="chip-return {ret_class}">'
            f"{_html_pct(ret)} 소생 중</span></div>"
        )

    return (
        '<div class="backtest-top3-wrap">'
        '<p class="backtest-top3-title">🏆 명예의 역발상 타점 TOP 3</p>'
        f"{''.join(chips)}"
        "</div>"
    )


def fetch_backtest_snapshot(stock_code: str) -> tuple[dict | None, str | None]:
    """최근 30거래일 실시간 종가 + 역발상 매수 타점 + TOP3 에피소드."""
    try:
        import sys as _sys

        for module_name in ("toss_price", "naver_price", "backtest_core"):
            _sys.modules.pop(module_name, None)
        from backtest_core import (
            build_contrarian_backtest_from_bars,
            estimate_daily_fear_scores,
            find_top_contrarian_episodes,
        )
        from naver_price import fetch_daily_bars

        bars = fetch_daily_bars(stock_code, count=BACKTEST_LOOKBACK_DAYS)
        bt = build_contrarian_backtest_from_bars(bars)
        buy_price = int(bt.buy_price)
        current_price = int(bt.current_price)
        if buy_price <= 0 or current_price <= 0:
            return None, "종가 데이터가 올바르지 않습니다."

        daily_scores = estimate_daily_fear_scores(bars)
        top_episodes = find_top_contrarian_episodes(
            bars, daily_scores, current_price, limit=3
        )
        return_pct = round((current_price - buy_price) / buy_price * 100, 1)
        invest = BACKTEST_SIM_INVESTMENT
        current_value = int(invest * current_price / buy_price)
        profit = current_value - invest

        return {
            "stock_code": str(stock_code),
            "buy_date": str(bt.buy_date),
            "buy_price": buy_price,
            "buy_fear_score": int(bt.buy_fear_score),
            "current_date": str(bt.current_date),
            "current_price": current_price,
            "return_pct": return_pct,
            "lookback_days": BACKTEST_LOOKBACK_DAYS,
            "sim_investment": invest,
            "sim_current_value": current_value,
            "sim_profit": profit,
            "top_episodes": top_episodes,
        }, None
    except Exception as exc:
        return None, str(exc)


def render_backtest_panel(
    stock_name: str,
    snapshot: dict | None,
    *,
    error: str | None = None,
) -> None:
    """토스형 자산 인포그래픽 — 역발상 백테스트 카드."""
    st.markdown(
        '<p class="post-list-title backtest-tab-title">📈 역발상 팩트체크</p>',
        unsafe_allow_html=True,
    )

    if error:
        st.warning(f"역발상 백테스트 데이터를 불러오지 못했습니다. ({error})")
        return
    if not snapshot:
        st.warning("최근 30일 주가 데이터가 비어 있습니다.")
        return

    try:
        buy_date_raw = str(snapshot["buy_date"])
        buy_price = int(snapshot["buy_price"])
        buy_fear_score = int(snapshot["buy_fear_score"])
        current_date_raw = str(snapshot["current_date"])
        current_price = int(snapshot["current_price"])
        lookback_days = int(snapshot.get("lookback_days", BACKTEST_LOOKBACK_DAYS))
        sim_investment = int(snapshot.get("sim_investment", BACKTEST_SIM_INVESTMENT))
        sim_current_value = int(snapshot.get("sim_current_value", 0))
        sim_profit = int(snapshot.get("sim_profit", 0))
        top_episodes = list(snapshot.get("top_episodes") or [])
    except (KeyError, TypeError, ValueError) as exc:
        st.warning(f"백테스트 데이터 형식 오류: {exc}")
        return

    if buy_price <= 0 or current_price <= 0:
        st.warning("주가 스케일 오류 — 데이터를 다시 불러와 주세요.")
        return

    if sim_current_value <= 0:
        sim_current_value = int(sim_investment * current_price / buy_price)
        sim_profit = sim_current_value - sim_investment

    return_pct = round((current_price - buy_price) / buy_price * 100, 1)
    buy_date_fmt = buy_date_raw[:10] if len(buy_date_raw) >= 10 else buy_date_raw
    current_date_fmt = (
        current_date_raw[:10] if len(current_date_raw) >= 10 else current_date_raw
    )
    is_up = return_pct >= 0
    trend_class = "up" if is_up else "down"
    profit_color = "#e53935" if is_up else "#3182f6"
    safe_name = html.escape(stock_name)
    invest_label = _format_won(sim_investment)
    timeline = _timeline_layout(buy_price, current_price)
    current_node_class = "current" if is_up else "current down-node"
    return_pct_html = _html_pct(return_pct)
    fill_left = _css_pct(timeline["fill_left"])
    fill_width = _css_pct(timeline["fill_width"])
    buy_pos = _css_pct(timeline["buy_pos"])
    current_pos = _css_pct(timeline["current_pos"])

    st.markdown(
        f"""
        <div class="backtest-infographic">
            <p class="backtest-sim-question">
                만약 전설적 곡소리 타점
                <b>(공포 {buy_fear_score}점 · {html.escape(buy_date_fmt)})</b>에<br>
                <b>{invest_label}</b>을 역발상 매수했다면?
            </p>
            <div class="backtest-sim-value-row">
                <span class="backtest-sim-label">현재 자산 가치</span>
                <span class="backtest-sim-value">{_format_won(sim_current_value)}</span>
            </div>
            <p class="backtest-sim-profit" style="color:{profit_color};">
                순수익 {_format_signed_won(sim_profit)}
            </p>
            <span class="backtest-return-badge {trend_class}">
                {safe_name} 역발상 수익률 {return_pct_html}
            </span>
            <p class="backtest-timeline-head">과거 vs 현재 주가 궤적</p>
            <div class="backtest-timeline-meta">
                <div class="backtest-timeline-point">
                    <div class="backtest-timeline-tag">매수 타점</div>
                    <div class="backtest-timeline-price">{_format_won(buy_price)}</div>
                    <div class="backtest-timeline-date">{html.escape(buy_date_fmt)}</div>
                </div>
                <div class="backtest-timeline-point right">
                    <div class="backtest-timeline-tag">현재가</div>
                    <div class="backtest-timeline-price">{_format_won(current_price)}</div>
                    <div class="backtest-timeline-date">{html.escape(current_date_fmt)}</div>
                </div>
            </div>
            <div class="backtest-timeline-track">
                <div class="backtest-timeline-fill {trend_class}"
                     style="left:{fill_left};width:{fill_width};"></div>
                <div class="backtest-timeline-node" style="left:{buy_pos};"></div>
                <div class="backtest-timeline-node {current_node_class}"
                     style="left:{current_pos};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top3_html = _render_top3_chips(top_episodes)
    if top3_html:
        st.markdown(top3_html, unsafe_allow_html=True)

    st.markdown(
        f'<p class="backtest-foot">최근 {lookback_days}일 실데이터 · 리얼 타임 종가 스케일 반영</p>',
        unsafe_allow_html=True,
    )


def _get_all_top20_stocks() -> list[tuple[str, str]]:
    """Streamlit 캐시된 예전 stock_config 대비 — TOP20 목록 fresh load."""
    import sys as _sys

    _sys.modules.pop("stock_config", None)
    from stock_config import KOSDAQ_TOP10, KOSPI_TOP10

    return list(KOSPI_TOP10 + KOSDAQ_TOP10)


def _combined_fear_score(naver_data: dict | None, toss_data: dict | None) -> float | None:
    scores: list[float] = []
    for data in (naver_data, toss_data):
        if data and data.get("post_count", 0) > 0:
            scores.append(float(data.get("score_raw", 50)))
    if not scores:
        return None
    return sum(scores) / len(scores)


def _build_combined_sentiment(
    naver_data: dict | None,
    toss_data: dict | None,
    stock_name: str,
    stock_code: str,
) -> dict | None:
    """네이버·토스 점수를 합친 실시간 심리 요약."""
    from sentiment_core import STATUS_COLORS, get_status_label

    parts: list[dict] = []
    for data in (naver_data, toss_data):
        if data and data.get("post_count", 0) > 0:
            parts.append(data)
    if not parts:
        return None

    score_raw = sum(float(item["score_raw"]) for item in parts) / len(parts)
    is_neutral = all(item.get("is_neutral") for item in parts)
    status = get_status_label(score_raw, is_neutral=is_neutral and len(parts) == 2)
    fear_count = sum(int(item.get("fear_count", 0)) for item in parts)
    greed_count = sum(int(item.get("greed_count", 0)) for item in parts)
    fear_breakdown = " · ".join(
        part for part in (item.get("fear_breakdown") for item in parts) if part
    )
    greed_breakdown = " · ".join(
        part for part in (item.get("greed_breakdown") for item in parts) if part
    )

    return {
        "stock_name": stock_name,
        "stock_code": stock_code,
        "post_count": sum(int(item.get("post_count", 0)) for item in parts),
        "fear_count": fear_count,
        "greed_count": greed_count,
        "fear_breakdown": fear_breakdown,
        "greed_breakdown": greed_breakdown,
        "score": round(score_raw),
        "score_raw": score_raw,
        "status": status,
        "status_color": STATUS_COLORS[status],
        "is_neutral": is_neutral and fear_count == 0 and greed_count == 0,
    }


def _merge_post_feed(
    naver_data: dict | None,
    toss_data: dict | None,
) -> tuple[list[str], list[str]]:
    titles: list[str] = []
    urls: list[str] = []
    for data, prefix in ((naver_data, "📗"), (toss_data, "💙")):
        if not data:
            continue
        for title, url in zip(
            data.get("titles") or [],
            data.get("post_urls") or [""] * len(data.get("titles") or []),
        ):
            titles.append(f"{prefix} {title}")
            urls.append(str(url or ""))
    return titles, urls


def render_combined_sentiment_panel(
    naver_data: dict | None,
    toss_data: dict | None,
    stock_name: str,
    stock_code: str,
) -> None:
    """실시간 심리 탭 — 통합 게이지 + 알림 카드."""
    combined = _build_combined_sentiment(naver_data, toss_data, stock_name, stock_code)
    if not combined:
        st.warning("네이버·토스 모두에서 키워드 글을 찾지 못했습니다.")
        return

    post_count = combined["post_count"]
    if post_count < TARGET_POST_COUNT:
        st.info(
            f"키워드 글 {post_count}개를 수집했습니다. "
            f"(목표 {TARGET_POST_COUNT}개 · {MAX_SCAN_PAGES}페이지 탐색)"
        )

    render_css_gauge(combined["score_raw"])
    score_summary = format_score_summary(combined)
    st.markdown(
        f"""
        <div class="score-display">
            <div style="display:inline-flex;align-items:baseline;justify-content:center;
                        color:{combined['status_color']};font-size:3.1rem;font-weight:800;
                        line-height:1;letter-spacing:-0.03em;margin:0;">
                <span>{combined['score']}</span>
                <span style="font-size:1.2rem;font-weight:700;margin-left:0.14em;
                              line-height:1;position:relative;top:0.18em;">점</span>
            </div>
            <p class="score-status" style="color: {combined['status_color']};">
                현재 상태: {combined['status']} <span style="font-size:0.78rem;color:#888;">
                (네이버·토스 통합)</span>
            </p>
            <div class="score-sub">{score_summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_push_alert_card(stock_code, int(combined.get("score", 50)))


def render_main_header(selected_name: str, selected_code: str, selected_market: str) -> None:
    """메인 화면 상단 종목 헤더."""
    st.markdown(
        f"""
        <div class="app-header">
            <h1>{selected_name} 인간지표</h1>
            <p>{selected_code} · {selected_market}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mobile_stock_controls() -> tuple[str, str, str]:
    """메인 화면 상단 — 종목 선택·새로고침 (모바일 450px)."""
    if "stock_code" not in st.session_state:
        st.session_state["stock_code"] = DEFAULT_STOCK_CODE
    st.session_state["stock_code"] = normalize_stock_code(st.session_state["stock_code"])

    selected_market = st.radio(
        "시장 선택",
        options=[MARKET_KOSPI, MARKET_KOSDAQ],
        horizontal=True,
        index=0 if st.session_state["stock_code"] in get_market_codes(MARKET_KOSPI) else 1,
        key="stock_market",
    )

    market_codes = get_market_codes(selected_market)
    market_labels = [format_stock_label(code) for code in market_codes]
    label_to_code = dict(zip(market_labels, market_codes))

    if st.session_state["stock_code"] not in market_codes:
        st.session_state["stock_code"] = market_codes[0]

    pick_index = market_codes.index(st.session_state["stock_code"])
    selected_label = st.selectbox(
        "종목 선택",
        market_labels,
        index=pick_index,
        key=f"stock_pick_{selected_market}",
    )
    refresh_clicked = st.button(
        "실시간 데이터 새로고침",
        key="global_refresh",
        use_container_width=True,
        type="primary",
    )

    selected_code = normalize_stock_code(label_to_code[selected_label])
    selected_name = get_stock_name(selected_code)

    if selected_code != st.session_state["stock_code"]:
        st.session_state["stock_code"] = selected_code
        reset_data_cache()
        clear_backtest_cache()

    if refresh_clicked:
        reset_data_cache()
        clear_backtest_cache()
        st.cache_data.clear()
        st.session_state["_force_fetch"] = True
        st.session_state["_ad_gate"] = True

    return selected_code, selected_name, selected_market


def render_sidebar_controls() -> tuple[str, str, str]:
    """(호환) → 모바일 메인 상단 컨트롤로 위임."""
    return render_mobile_stock_controls()


def render_stock_picker() -> tuple[str, str, str]:
    """(호환용) 사이드바 종목 선택 — 메인 헤더는 render_main_header 사용."""
    selected_code, selected_name, selected_market = render_sidebar_controls()
    render_main_header(selected_name, selected_code, selected_market)
    return selected_code, selected_name, selected_market


def _fetch_ranking_entry(
    stock_code: str,
    stock_name: str,
    analyze_naver_board,
    analyze_toss_community,
) -> dict | None:
    naver_data: dict | None = None
    toss_data: dict | None = None

    try:
        naver_data = analyze_naver_board(
            stock_code=stock_code,
            stock_name=stock_name,
            post_limit=RANKING_POST_LIMIT,
        )
    except Exception:
        naver_data = None

    try:
        toss_data = analyze_toss_community(
            stock_code=stock_code,
            stock_name=stock_name,
            post_limit=RANKING_POST_LIMIT,
        )
    except Exception:
        toss_data = None

    score = _combined_fear_score(naver_data, toss_data)
    if score is None:
        return None

    from sentiment_core import get_status_label

    return {
        "code": stock_code,
        "name": stock_name,
        "score": round(score),
        "status": get_status_label(score),
    }


def _build_top3_ranking(analyze_naver_board, analyze_toss_community) -> list[dict]:
    entries: list[dict] = []

    def _worker(stock: tuple[str, str]) -> dict | None:
        code, name = stock
        return _fetch_ranking_entry(code, name, analyze_naver_board, analyze_toss_community)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(_worker, _get_all_top20_stocks()):
            if result:
                entries.append(result)

    entries.sort(key=lambda item: item["score"])
    return entries[:3]


def _cached_top3_ranking(app_version: str) -> list[dict]:
    import sys as _sys

    for module_name in LOCAL_MODULES:
        _sys.modules.pop(module_name, None)
    from naver_scraper import analyze_naver_board
    from toss_scraper import analyze_toss_community

    return _build_top3_ranking(analyze_naver_board, analyze_toss_community)


def render_contrarian_ranking_board() -> None:
    """🏆 오늘의 역발상 랭킹 전광판 — 공포 점수 최저 TOP 3."""
    try:
        with st.spinner("역발상 랭킹 집계 중..."):
            top3 = _cached_top3_ranking(APP_VERSION)
    except Exception as exc:
        st.caption(f"역발상 랭킹을 불러오지 못했습니다. ({exc})")
        return

    if not top3:
        st.caption("역발상 랭킹 데이터가 아직 없습니다.")
        return

    st.markdown(
        '<p class="rank-board-title">역발상 매수 TOP 3</p>',
        unsafe_allow_html=True,
    )
    rank_labels = ("1", "2", "3")
    rank_classes = ("rank-1", "rank-2", "rank-3")
    cards_html: list[str] = []
    for item, rank_label, rank_cls in zip(top3, rank_labels, rank_classes):
        name = html.escape(str(item["name"]))
        status = html.escape(str(item["status"]))
        cards_html.append(
            f'<div class="rank-card {rank_cls}">'
            f'<div class="rank-medal">{rank_label}</div>'
            f'<div class="rank-name">{name}</div>'
            f'<div class="rank-score">{item["score"]}점</div>'
            f'<div class="rank-status">{status}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="rank-board-grid">{"".join(cards_html)}</div>',
        unsafe_allow_html=True,
    )


def _pick_legend_drips(
    titles: list[str],
    post_urls: list[str] | None = None,
    limit: int = LEGEND_DRIP_COUNT,
) -> list[dict[str, str | int]]:
    from sentiment_core import FEAR_WORDS, GREED_WORDS, count_word_breakdown

    urls = post_urls or [""] * len(titles)
    scored: list[tuple[float, str, int, int, str]] = []
    for index, title in enumerate(titles):
        url = urls[index] if index < len(urls) else ""
        fear_hits = count_word_breakdown(title, FEAR_WORDS)
        greed_hits = count_word_breakdown(title, GREED_WORDS)
        fear_count = sum(fear_hits.values())
        greed_count = sum(greed_hits.values())
        if fear_count == 0 and greed_count == 0:
            continue

        spice = fear_count * 2.5 + greed_count * 1.5
        if fear_count > 0 and greed_count > 0:
            spice += min(fear_count, greed_count) * 2
        spice += max(0, 40 - index) * 0.4
        scored.append((spice, title, fear_count, greed_count, url))

    scored.sort(key=lambda item: item[0], reverse=True)
    picks: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for _, title, fear_count, greed_count, url in scored:
        if title in seen:
            continue
        seen.add(title)
        picks.append(
            {
                "title": title,
                "url": url,
                "fear_count": fear_count,
                "greed_count": greed_count,
            }
        )
        if len(picks) >= limit:
            break
    return picks


def _truncate_drip(text: str, max_len: int = 72) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def render_legend_hall(titles: list[str], post_urls: list[str] | None = None) -> None:
    """🔥 실시간 인간지표 명예의 전당 — 레전드 드립 (원본 링크)."""
    picks = _pick_legend_drips(titles, post_urls)
    if not picks:
        return

    html_parts = [
        '<div class="legend-card">',
        '<p class="legend-header">레전드 주식방 드립</p>',
    ]
    for pick in picks:
        title = str(pick["title"])
        url = str(pick.get("url") or "").strip()
        fear_count = int(pick["fear_count"])
        greed_count = int(pick["greed_count"])
        drip = html.escape(_truncate_drip(title))
        css_class = "legend-drip-fear" if fear_count >= greed_count else "legend-drip-greed"

        if url:
            link_html = (
                f'<a href="{html.escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">💬 {drip}</a>'
            )
        else:
            link_html = f"💬 {drip}"

        html_parts.append(f'<div class="legend-drip {css_class}">{link_html}</div>')
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_hanriver_vote_panel(
    stock_code: str,
    stock_name: str,
    *,
    embed_cpr: bool = False,
) -> None:
    """종목별 실시간 투표 — embed_cpr 시 심폐소생실 통합 카드."""
    init_member_session()
    init_vote_accuracy_session()
    inject_accuracy_badge_css()
    code = str(stock_code).strip()

    guest = not is_member()
    vote_locked = is_vote_locked_for_stock(code)

    if embed_cpr:
        st.markdown(
            f'<p class="cpr-vote-head">📈 오늘의 개미방 포지션</p>'
            f'<p class="cpr-vote-sub">{html.escape(stock_name)} ({code})</p>',
            unsafe_allow_html=True,
        )
        if guest:
            st.markdown(
                '<p class="cpr-vote-lock">🔒 투표·글쓰기 회원전용 · 버튼 터치 시 가입</p>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f'<p class="cpr-vote-head">📊 실시간 시장 심리 전광판</p>'
            f'<p class="cpr-vote-sub">{html.escape(stock_name)} ({code})</p>',
            unsafe_allow_html=True,
        )

    vote_col1, vote_col2 = st.columns(2)
    with vote_col1:
        if st.button("😱 살려줘", use_container_width=True, key=f"vote_fear_{code}"):
            if not is_member():
                set_vote_locked_for_stock(code)
                st.rerun()
            add_stock_vote(code, "fear")
            record_member_vote(vote_type="fear")
            st.rerun()
    with vote_col2:
        if st.button("🚀 가즈아", use_container_width=True, key=f"vote_greed_{code}"):
            if not is_member():
                set_vote_locked_for_stock(code)
                st.rerun()
            add_stock_vote(code, "greed")
            record_member_vote(vote_type="greed")
            st.rerun()

    fear_votes, greed_votes = get_stock_vote_counts(code)
    total_votes = fear_votes + greed_votes
    if total_votes == 0:
        fear_pct = 50.0
        greed_pct = 50.0
    else:
        fear_pct = fear_votes / total_votes * 100
        greed_pct = 100 - fear_pct

    st.markdown(
        f"""
        <div class="cpr-vote-bar-wrap">
            <div class="hanriver-bar-fear" style="width:{fear_pct:.1f}%;"></div>
            <div class="hanriver-bar-greed" style="width:{greed_pct:.1f}%;"></div>
        </div>
        <div class="cpr-vote-stats">
            <span>😱 {fear_votes}표 ({fear_pct:.0f}%)</span>
            <span>🚀 {greed_votes}표 ({greed_pct:.0f}%)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if embed_cpr:
        if guest and vote_locked:
            render_compact_kakao_cta(button_key=f"member_kakao_vote_{code}")
        return

    show_vote_gate_if_needed(compact=False)

    if total_votes > 0:
        chart_fig = go.Figure(
            data=[
                go.Bar(
                    y=["실시간 투표"],
                    x=[fear_votes],
                    name="😱 살려줘",
                    orientation="h",
                    marker_color="#e53935",
                    text=[f"{fear_votes}표"],
                    textposition="inside",
                ),
                go.Bar(
                    y=["실시간 투표"],
                    x=[greed_votes],
                    name="🚀 가즈아",
                    orientation="h",
                    marker_color="#43a047",
                    text=[f"{greed_votes}표"],
                    textposition="inside",
                ),
            ]
        )
        chart_fig.update_layout(
            barmode="stack",
            height=72,
            margin=dict(l=10, r=10, t=8, b=8),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.15, x=0),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False),
        )
        st.plotly_chart(chart_fig, use_container_width=True)
    else:
        st.caption("아직 투표가 없습니다. 첫 번째 개미의 한 표를 던져 보세요!")


def simulate_refresh_ad_gate() -> None:
    """새로고침 직전 — 무료 유저용 2초 전면 광고 시뮬레이션."""
    gate_slot = st.empty()
    with gate_slot.container():
        st.markdown(
            """
            <div class="refresh-ad-gate-wrap">
                <span class="ad-gate-badge">AD · 전면 광고</span>
                <p class="refresh-ad-msg">잠시 후 실시간 데이터가 갱신됩니다...</p>
                <div class="refresh-ad-bar">
                    <div class="refresh-ad-bar-fill"></div>
                </div>
                <p class="refresh-ad-hint">프리미엄 멤버십 가입 시 광고 없이 즉시 갱신</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.spinner("광고 로딩 중..."):
            time.sleep(2)
    gate_slot.empty()


def render_membership_ad_footer() -> None:
    """탭 하단 — 멤버십 유도 배너 광고."""
    st.markdown("---")
    st.markdown(
        """
        <div class="ad-membership-card">
            <span class="ad-badge">AD</span>
            <p><strong>월 4,900원</strong>으로 모든 광고를 제거하고<br>
            실시간 <strong>찐바닥 곡소리 알림</strong>을 받아보세요!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ad_banner() -> None:
    """(호환) → 멤버십 배너로 위임."""
    render_membership_ad_footer()


def render_post_list(
    titles: list[str],
    list_label: str,
    post_count: int,
    post_urls: list[str] | None = None,
) -> None:
    st.markdown(
        f'<p class="post-list-title">{list_label} {post_count}개</p>',
        unsafe_allow_html=True,
    )
    if not titles:
        st.caption("표시할 글이 없습니다.")
        return

    clean_titles = [str(title).strip() for title in titles]
    urls = [str(url or "").strip() for url in (post_urls or [""] * len(clean_titles))]

    rows_html: list[str] = []
    for idx, (title, url) in enumerate(zip(clean_titles, urls), 1):
        safe_title = html.escape(title)
        if url:
            safe_url = html.escape(url)
            title_cell = (
                f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">'
                f"{safe_title}</a>"
            )
        else:
            title_cell = safe_title
        rows_html.append(
            f'<tr><td class="post-no">{idx}</td>'
            f'<td class="post-title">{title_cell}</td></tr>'
        )

    st.markdown(
        (
            '<div class="post-table-wrap">'
            '<table class="post-table">'
            '<thead><tr>'
            '<th class="post-no-h">번호</th>'
            '<th class="post-title-h">제목</th>'
            "</tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table></div>"
        ),
        unsafe_allow_html=True,
    )


def render_community_posts_panel(
    naver_data: dict | None,
    toss_data: dict | None,
    naver_error: str | None,
    toss_error: str | None,
    *,
    section_title: str | None = None,
    compact: bool = False,
) -> None:
    """외부 커뮤니티 글 목록 — 눈팅 전용 (글쓰기 폼 없음)."""
    if section_title:
        title_class = (
            "cpr-feed-label cpr-external-feed-head"
            if compact
            else "post-list-title"
        )
        st.markdown(
            f'<p class="{title_class}">{html.escape(section_title)}</p>',
            unsafe_allow_html=True,
        )
    if compact:
        st.markdown('<div class="cpr-external-lurk">', unsafe_allow_html=True)

    merged_titles, merged_urls = _merge_post_feed(naver_data, toss_data)
    if merged_titles:
        render_legend_hall(merged_titles, merged_urls)

    if naver_error:
        st.error(f"네이버 수집 실패: {naver_error}")
    elif naver_data and naver_data.get("titles"):
        render_post_list(
            naver_data["titles"],
            "네이버 키워드 글",
            naver_data.get("post_count", 0),
            naver_data.get("post_urls"),
        )
    elif naver_data:
        st.caption("네이버에서 키워드 글을 찾지 못했습니다.")

    if toss_error:
        st.error(f"토스 수집 실패: {toss_error}")
    elif toss_data and toss_data.get("titles"):
        render_post_list(
            toss_data["titles"],
            "토스 키워드 글",
            toss_data.get("post_count", 0),
            toss_data.get("post_urls"),
        )
    elif toss_data:
        st.caption("토스에서 키워드 글을 찾지 못했습니다.")

    if compact:
        st.markdown("</div>", unsafe_allow_html=True)


def fetch_both_parallel(stock_code: str, stock_name: str) -> tuple[dict | None, dict | None, str | None, str | None]:
    """네이버+토스 병렬 수집. 한쪽 실패해도 다른 쪽은 유지."""
    analyze_naver_board, analyze_toss_community = _load_fresh_analyzers()
    naver_data: dict | None = None
    toss_data: dict | None = None
    naver_error: str | None = None
    toss_error: str | None = None

    def _fetch_naver() -> dict:
        return analyze_naver_board(stock_code=stock_code, stock_name=stock_name)

    def _fetch_toss() -> dict:
        return analyze_toss_community(stock_code=stock_code, stock_name=stock_name)

    with ThreadPoolExecutor(max_workers=2) as pool:
        naver_future = pool.submit(_fetch_naver)
        toss_future = pool.submit(_fetch_toss)
        try:
            naver_data = naver_future.result()
        except Exception as error:
            naver_error = str(error)
        try:
            toss_data = toss_future.result()
        except Exception as error:
            toss_error = str(error)

    return naver_data, toss_data, naver_error, toss_error


def _cache_is_valid(cache_key: str, *, force: bool) -> bool:
    if force:
        return False
    if st.session_state.get("data_cache_key") != cache_key:
        return False
    naver = st.session_state.get("data_naver")
    toss = st.session_state.get("data_toss")
    if naver is None and toss is None:
        return False

    naver_count = (naver or {}).get("post_count", 0)
    toss_count = (toss or {}).get("post_count", 0)
    naver_error = st.session_state.get("data_naver_error")
    toss_error = st.session_state.get("data_toss_error")

    # 예전 버그로 저장된 '0건 캐시'는 무효 처리 → 다시 수집
    if naver_count == 0 and toss_count == 0 and not naver_error and not toss_error:
        return False
    return True


def ensure_data(stock_code: str, stock_name: str, *, force: bool = False) -> None:
    cache_key = f"{APP_VERSION}:{stock_code}"
    if _cache_is_valid(cache_key, force=force):
        return

    with st.spinner("최신 시장 데이터를 분석하는 중..."):
        naver_data, toss_data, naver_error, toss_error = fetch_both_parallel(
            stock_code, stock_name
        )

    st.session_state["data_naver"] = naver_data
    st.session_state["data_toss"] = toss_data
    st.session_state["data_naver_error"] = naver_error
    st.session_state["data_toss_error"] = toss_error
    st.session_state["data_cache_key"] = cache_key


def reset_data_cache() -> None:
    for key in (
        "data_cache_key",
        "data_naver",
        "data_toss",
        "data_naver_error",
        "data_toss_error",
    ):
        st.session_state.pop(key, None)


def clear_backtest_cache() -> None:
    """(호환) 세션 백테스트·구 300일 빌드업 캐시 키 제거."""
    st.session_state.pop("backtest_cache_key", None)
    for key in list(st.session_state.keys()):
        if str(key).startswith("history_buildup:"):
            st.session_state.pop(key, None)


def preload_shared_data(
    stock_code: str,
    stock_name: str,
    *,
    force: bool = False,
) -> dict:
    """탭 시작 전 — 커뮤니티·백테스트 데이터를 한 번에 준비 (로컬 변수로 반환)."""
    ensure_data(stock_code, stock_name, force=force)
    backtest_snapshot, backtest_error = fetch_backtest_snapshot(stock_code)

    return {
        "naver_data": st.session_state.get("data_naver"),
        "toss_data": st.session_state.get("data_toss"),
        "naver_error": st.session_state.get("data_naver_error"),
        "toss_error": st.session_state.get("data_toss_error"),
        "backtest_snapshot": backtest_snapshot,
        "backtest_error": backtest_error,
    }


def _load_cpr_room_renderer():
    """Streamlit이 cpr_room.py 수정본을 안 불러오는 문제 방지."""
    import sys as _sys

    _sys.modules.pop("cpr_room", None)
    import cpr_room

    return cpr_room


def run_app() -> None:
    """모바일 450px · 데이터 선로드 · 4단 탭."""
    init_member_session()
    if st.session_state.get("_app_version") != APP_VERSION:
        st.session_state["_app_version"] = APP_VERSION
        if st.session_state.get("stock_code") == "191150":
            st.session_state["stock_code"] = "196170"
        reset_data_cache()
        clear_backtest_cache()
        st.cache_data.clear()
        for key in (
            "cpr_logged_in",
            "cpr_user",
            "cpr_posts",
            "cpr_compose_touched",
            "cpr_draft",
            "_cpr_clear_draft",
            "member_logged_in",
            "member_user",
            "member_vote_lock",
            "member_cpr_touch",
            "member_community_touch",
            "vote_accuracy_30d",
            "_accuracy_badge_css_injected",
            "stock_votes",
            "vote_lock_by_stock",
            HANRIVER_FEAR_KEY,
            HANRIVER_GREED_KEY,
        ):
            st.session_state.pop(key, None)

    cpr_mod = _load_cpr_room_renderer()

    if "stock_code" not in st.session_state:
        st.session_state["stock_code"] = DEFAULT_STOCK_CODE
    st.session_state["stock_code"] = normalize_stock_code(st.session_state["stock_code"])

    selected_code, selected_name, selected_market = render_mobile_stock_controls()

    if st.session_state.pop("_ad_gate", False):
        simulate_refresh_ad_gate()

    force_fetch = st.session_state.pop("_force_fetch", False)
    with st.spinner("최신 시장 데이터를 분석하는 중..."):
        shared = preload_shared_data(selected_code, selected_name, force=force_fetch)

    naver_data = shared["naver_data"]
    toss_data = shared["toss_data"]
    naver_error = shared["naver_error"]
    toss_error = shared["toss_error"]
    backtest_snapshot = shared["backtest_snapshot"]
    backtest_error = shared["backtest_error"]

    tab_cpr, tab1, tab2, tab3 = st.tabs(
        [
            "심폐소생실",
            "실시간 심리",
            "백테스팅",
            "곡소리",
        ]
    )

    with tab_cpr:
        try:
            cpr_mod.init_cpr_session()
            st.markdown(MEMBER_GATE_CSS, unsafe_allow_html=True)
            cpr_mod.inject_accuracy_badge_css()
            st.markdown(cpr_mod.CPR_ROOM_CSS, unsafe_allow_html=True)
            with st.container(border=True):
                render_hanriver_vote_panel(
                    selected_code, selected_name, embed_cpr=True
                )
                st.markdown(
                    '<div class="cpr-compose-divider"></div>',
                    unsafe_allow_html=True,
                )
                cpr_mod.render_cpr_compose_zone()
            cpr_mod.render_cpr_post_feed()
            render_community_posts_panel(
                naver_data,
                toss_data,
                naver_error,
                toss_error,
                section_title="네이버·토스 등 외부 커뮤니티 곡소리",
                compact=True,
            )
        except Exception as exc:
            st.error(f"심폐소생실방 렌더링 오류: {exc}")

    with tab1:
        render_contrarian_ranking_board()
        render_main_header(selected_name, selected_code, selected_market)
        render_combined_sentiment_panel(
            naver_data, toss_data, selected_name, selected_code
        )
        render_platform_gap_panel(naver_data, toss_data, selected_name)

    with tab2:
        try:
            render_backtest_panel(
                selected_name,
                backtest_snapshot,
                error=backtest_error,
            )
        except Exception as exc:
            st.error(f"백테스트 렌더링 오류: {exc}")

    with tab3:
        try:
            render_community_posts_panel(
                naver_data,
                toss_data,
                naver_error,
                toss_error,
                section_title="네이버·토스 커뮤니티 실시간",
            )
        except Exception as exc:
            st.error(f"커뮤니티 글 목록 렌더링 오류: {exc}")
        render_membership_ad_footer()


run_app()
