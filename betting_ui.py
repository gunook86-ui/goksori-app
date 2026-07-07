"""금일 롱/숏 배팅 현황판 · 히스토리 결과 조회 UI."""

from __future__ import annotations

import html
from datetime import date, timedelta
from typing import Any

import streamlit as st

from stock_votes import current_vote_session_date, get_stock_vote_counts, init_stock_votes
from stock_votes import (
    format_vote_window_hint,
    get_locked_display_date,
    init_vote_ledger,
    session_date_str,
)


def render_toss_style_bar(
    long_pct: float,
    *,
    short_pct: float | None = None,
    label_left: str = "",
    label_right: str = "",
    compact: bool = False,
) -> str:
    short_pct = short_pct if short_pct is not None else (100.0 - long_pct)
    height = "14px" if compact else "20px"
    return f"""
    <div class="toss-bet-bar-wrap" style="height:{height};">
        <div class="toss-bet-bar-long" style="width:{long_pct:.1f}%;"></div>
        <div class="toss-bet-bar-short" style="width:{short_pct:.1f}%;"></div>
    </div>
    <div class="toss-bet-bar-labels">
        <span>{html.escape(label_left or f"📈 롱 {long_pct:.0f}%")}</span>
        <span class="toss-bet-sep">|</span>
        <span>{html.escape(label_right or f"📉 숏 {short_pct:.0f}%")}</span>
    </div>
    """


def _vote_pcts(stock_code: str) -> tuple[int, int, float, float]:
    short_v, long_v = get_stock_vote_counts(stock_code)
    total = short_v + long_v
    if total <= 0:
        return short_v, long_v, 50.0, 50.0
    long_pct = long_v / total * 100
    return short_v, long_v, long_pct, 100.0 - long_pct


def render_daily_betting_board(
    selected_code: str,
    selected_name: str,
    *,
    extra_stocks: list[dict[str, Any]] | None = None,
) -> None:
    """실시간 심리 탭 상단 — 금일 종목별 롱/숏 배팅 현황판."""
    session = current_vote_session_date()
    session_label = session[5:].replace("-", "/")
    st.markdown(
        f"""
        <div class="betting-board-head">
            <p class="betting-board-title">금일 종목별 롱/숏 배팅 현황판</p>
            <p class="betting-board-sub">{session_label} 회차 · {html.escape(format_vote_window_hint())}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows: list[tuple[str, str, bool]] = [
        (str(selected_code), str(selected_name), True),
    ]
    seen = {str(selected_code)}
    for item in extra_stocks or []:
        code = str(item.get("code", "")).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append((code, str(item.get("name", code)), False))

    cards: list[str] = []
    for code, name, highlight in rows:
        init_stock_votes(code)
        short_v, long_v, long_pct, short_pct = _vote_pcts(code)
        hl = " betting-row-highlight" if highlight else ""
        cards.append(
            f'<div class="betting-row{hl}">'
            f'<p class="betting-row-name">{html.escape(name)} '
            f'<span class="betting-row-code">{html.escape(code)}</span></p>'
            f'{render_toss_style_bar(long_pct, short_pct=short_pct, compact=True)}'
            f'<p class="betting-row-meta">{long_v}롱 · {short_v}숏 · {long_v + short_v}표</p>'
            f"</div>"
        )
    st.markdown(
        f'<div class="betting-board-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _aggregate_session_votes(session_date: str) -> dict[str, dict[str, int]]:
    """해당 날짜 pending + settled 집계."""
    ledger = init_vote_ledger()
    tallies: dict[str, dict[str, int]] = {}

    def _add(code: str, side: str) -> None:
        bucket = tallies.setdefault(code, {"long": 0, "short": 0})
        if side == "long":
            bucket["long"] += 1
        else:
            bucket["short"] += 1

    for entry in ledger.get("pending", {}).values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("session_date", "")) != session_date:
            continue
        _add(str(entry.get("stock_code", "")), str(entry.get("vote", "")).lower())

    for entry in ledger.get("history", []):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("date", "")) != session_date:
            continue
        _add(str(entry.get("stock_code", "")), str(entry.get("vote", "")).lower())

    store = st.session_state.get("stock_votes") or {}
    for code, bucket in store.items():
        if isinstance(bucket, dict) and str(bucket.get("session_date", "")) == session_date:
            tallies.setdefault(str(code), {"long": 0, "short": 0})
            tallies[str(code)]["long"] = max(
                tallies[str(code)]["long"], int(bucket.get("long", 0))
            )
            tallies[str(code)]["short"] = max(
                tallies[str(code)]["short"], int(bucket.get("short", 0))
            )
    return tallies


def _market_result_label(change_pct: float | None) -> str:
    if change_pct is None:
        return "정산 대기"
    if change_pct > 0:
        return f"📈 상승 {change_pct:+.2f}%"
    if change_pct < 0:
        return f"📉 하락 {change_pct:+.2f}%"
    return "➖ 보합 0.00%"


def render_betting_history_panel(selected_code: str, selected_name: str) -> None:
    """과거 날짜별 배팅 현황 + 종가 결과(적중/미적중)."""
    ledger = init_vote_ledger()
    settled: list[str] = list(ledger.get("settled_dates") or [])
    today = session_date_str(date.today())
    candidates = sorted(set(settled + [today, current_vote_session_date()]), reverse=True)

    st.markdown(
        '<p class="betting-history-title">📅 배팅 결과 히스토리</p>',
        unsafe_allow_html=True,
    )

    pick = st.selectbox(
        "조회 날짜",
        options=candidates[:30] if candidates else [today],
        format_func=lambda d: d.replace("-", "/"),
        key="betting_history_date",
        label_visibility="collapsed",
    )

    if not pick:
        st.info("조회할 날짜가 없습니다.")
        return

    tallies = _aggregate_session_votes(pick)
    from stock_votes import fetch_session_change_pct

    try:
        session_d = date.fromisoformat(pick)
    except ValueError:
        session_d = date.today()

    user = st.session_state.get("member_user")
    user_email = str((user or {}).get("email", "")) if isinstance(user, dict) else ""
    my_records = [
        h
        for h in ledger.get("history", [])
        if isinstance(h, dict)
        and str(h.get("date", "")) == pick
        and (not user_email or str(h.get("email", "")) == user_email)
    ]

    change_main = fetch_session_change_pct(selected_code, session_d)
    st.markdown(
        f'<p class="betting-history-market">{html.escape(selected_name)} '
        f"({html.escape(selected_code)}) · "
        f"{_market_result_label(change_main)}</p>",
        unsafe_allow_html=True,
    )

    if my_records:
        streak = "".join("⭕" if r.get("hit") else "❌" for r in my_records[:5])
        st.markdown(
            f'<p class="betting-history-my">내 결과 · {html.escape(streak)}</p>',
            unsafe_allow_html=True,
        )

    if not tallies:
        st.caption("해당 날짜 배팅 데이터가 없습니다.")
        return

    from stock_config import get_stock_name

    cards: list[str] = []
    for code, counts in sorted(tallies.items(), key=lambda x: -(x[1]["long"] + x[1]["short"])):
        total = counts["long"] + counts["short"]
        if total <= 0:
            continue
        long_pct = counts["long"] / total * 100
        chg = fetch_session_change_pct(code, session_d)
        result = _market_result_label(chg)
        name = get_stock_name(code) or code
        cards.append(
            f'<div class="betting-history-card">'
            f'<p class="betting-row-name">{html.escape(name)} '
            f'<span class="betting-row-code">{html.escape(code)}</span></p>'
            f'{render_toss_style_bar(long_pct, compact=True)}'
            f'<p class="betting-row-meta">{result} · {total}표</p>'
            f"</div>"
        )
    st.markdown(
        f'<div class="betting-history-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
