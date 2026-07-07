"""종목별 롱/숏 투표 + 세션 마감(08:00)/정산(20:00).

vote_settlement.py 내용을 이 파일에 통합 — Streamlit Cloud 배포 시
별도 vote_settlement.py 없이 동작합니다.
"""

from __future__ import annotations

import hashlib
import html
from datetime import date, datetime, time, timedelta
from typing import Any

import streamlit as st

# ── 세션 마감 · 정산 ─────────────────────────────────────────────

VOTE_LEDGER_KEY = "member_vote_ledger"
MARKET_OPEN_LOCK = time(8, 0)
MARKET_CLOSE_SETTLE = time(20, 0)


def _now() -> datetime:
    return datetime.now()


def session_date_str(d: date) -> str:
    return d.isoformat()


def get_vote_title_date(now: datetime | None = None) -> date:
    now = now or _now()
    today = now.date()
    if now.time() < MARKET_OPEN_LOCK:
        return today
    return today + timedelta(days=1)


def is_session_locked(session_date: date, now: datetime | None = None) -> bool:
    now = now or _now()
    lock_at = datetime.combine(session_date, MARKET_OPEN_LOCK)
    return now >= lock_at


def get_open_vote_date(now: datetime | None = None) -> date | None:
    now = now or _now()
    target = get_vote_title_date(now)
    if is_session_locked(target, now):
        return None
    return target


def get_locked_display_date(now: datetime | None = None) -> date:
    now = now or _now()
    open_date = get_open_vote_date(now)
    if open_date is not None:
        return open_date
    return get_vote_title_date(now)


def is_session_settle_ready(session_date: date, now: datetime | None = None) -> bool:
    now = now or _now()
    settle_at = datetime.combine(session_date, MARKET_CLOSE_SETTLE)
    return now >= settle_at


def format_korean_date_label(d: date) -> str:
    return f"{d.month}월 {d.day}일"


def format_vote_panel_title(stock_name: str, now: datetime | None = None) -> str:
    target = get_vote_title_date(now)
    name = str(stock_name or "").strip() or "종목"
    return f"{format_korean_date_label(target)} {name} 나의 포지션은?"


def format_target_date_label(d: date | None = None) -> str:
    target = d if d is not None else get_locked_display_date()
    return f"{target.month}/{target.day}"


def get_vote_target_date(now: datetime | None = None) -> date:
    return get_locked_display_date(now)


def format_vote_window_hint(now: datetime | None = None) -> str:
    now = now or _now()
    open_date = get_open_vote_date(now)
    if open_date is None:
        target = get_vote_title_date(now)
        return (
            f"⏰ {target.month}/{target.day} 08:00 마감 · "
            "다음 회차 투표가 곧 열립니다."
        )
    lock_label = f"{open_date.month}/{open_date.day} 08:00"
    return f"🗳️ {lock_label}까지 투표·변경 가능"


def init_vote_ledger() -> dict[str, Any]:
    if VOTE_LEDGER_KEY not in st.session_state:
        st.session_state[VOTE_LEDGER_KEY] = {
            "pending": {},
            "history": [],
            "settled_dates": [],
        }
    ledger = st.session_state[VOTE_LEDGER_KEY]
    ledger.setdefault("pending", {})
    ledger.setdefault("history", [])
    ledger.setdefault("settled_dates", [])
    return ledger


def _pending_key(session_date: str, stock_code: str) -> str:
    return f"{session_date}:{stock_code}"


def get_member_pending_vote(
    *,
    user: dict[str, Any] | None,
    session_date: str,
    stock_code: str,
) -> str | None:
    if not user:
        return None
    email = str(user.get("email", "")).strip()
    if not email:
        return None
    ledger = init_vote_ledger()
    entry = ledger["pending"].get(_pending_key(session_date, stock_code))
    if not isinstance(entry, dict):
        return None
    if str(entry.get("email", "")) != email:
        return None
    side = str(entry.get("vote", "")).strip().lower()
    return side if side in ("long", "short") else None


def queue_member_vote(
    *,
    user: dict[str, Any] | None,
    session_date: str,
    stock_code: str,
    vote_type: str,
) -> tuple[bool, str]:
    if not user:
        return False, "로그인이 필요합니다."
    email = str(user.get("email", "")).strip()
    if not email:
        return False, "회원 정보가 올바르지 않습니다."

    try:
        session_d = date.fromisoformat(session_date)
    except ValueError:
        return False, "투표 세션 날짜가 올바르지 않습니다."

    if is_session_locked(session_d):
        return False, "투표 마감 시간(08:00)이 지나 변경할 수 없습니다."

    side = vote_type
    if side in ("fear", "greed"):
        side = "short" if side == "fear" else "long"
    if side not in ("long", "short"):
        return False, "투표 유형이 올바르지 않습니다."

    ledger = init_vote_ledger()
    key = _pending_key(session_date, stock_code)
    prev = ledger["pending"].get(key)
    prev_side = None
    if isinstance(prev, dict) and str(prev.get("email", "")) == email:
        prev_side = str(prev.get("vote", "")).lower()

    ledger["pending"][key] = {
        "email": email,
        "vote": side,
        "stock_code": str(stock_code),
        "session_date": session_date,
        "queued_at": _now().isoformat(timespec="seconds"),
    }
    return True, prev_side or ""


def fetch_session_change_pct(stock_code: str, session_date: date) -> float | None:
    try:
        from naver_price import fetch_daily_bars

        bars = fetch_daily_bars(stock_code, count=10)
    except Exception:
        return None
    if len(bars) < 2:
        return None

    target = session_date_str(session_date)
    idx = next(
        (i for i, bar in enumerate(bars) if str(bar.get("date", ""))[:10] == target),
        None,
    )
    if idx is None or idx == 0:
        return None
    prev_close = float(bars[idx - 1].get("close", 0))
    close = float(bars[idx].get("close", 0))
    if prev_close <= 0:
        return None
    return round((close - prev_close) / prev_close * 100, 2)


_fetch_session_change_pct = fetch_session_change_pct


def _vote_hit(vote: str, change_pct: float) -> bool:
    if vote == "long":
        return change_pct > 0
    if vote == "short":
        return change_pct < 0
    return False


def process_vote_settlements(now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or _now()
    ledger = init_vote_ledger()
    settled_dates: set[str] = set(ledger.get("settled_dates") or [])
    history: list[dict[str, Any]] = list(ledger.get("history") or [])
    pending: dict[str, Any] = dict(ledger.get("pending") or {})
    results: list[dict[str, Any]] = []

    candidate_dates: set[str] = {session_date_str(now.date())}
    candidate_dates.update(
        str(item.get("session_date", ""))
        for item in pending.values()
        if isinstance(item, dict)
    )
    for d_str in sorted(candidate_dates):
        if not d_str or d_str in settled_dates:
            continue
        try:
            session_d = date.fromisoformat(d_str)
        except ValueError:
            continue
        if not is_session_settle_ready(session_d, now):
            continue

        session_pending = {
            k: v
            for k, v in pending.items()
            if isinstance(v, dict) and str(v.get("session_date", "")) == d_str
        }
        for key, entry in session_pending.items():
            stock_code = str(entry.get("stock_code", ""))
            vote = str(entry.get("vote", "")).lower()
            change_pct = fetch_session_change_pct(stock_code, session_d)
            if change_pct is None:
                continue
            hit = _vote_hit(vote, change_pct)
            record = {
                "date": d_str,
                "vote": vote,
                "stock_code": stock_code,
                "change_pct": change_pct,
                "hit": hit,
                "settled_at": now.isoformat(timespec="seconds"),
                "email": str(entry.get("email", "")),
            }
            history = [
                h
                for h in history
                if not (
                    str(h.get("date", "")) == d_str
                    and str(h.get("email", "")) == record["email"]
                    and str(h.get("stock_code", "")) == stock_code
                )
            ]
            history.append(record)
            pending.pop(key, None)
            results.append(record)

        settled_dates.add(d_str)

    ledger["history"] = history
    ledger["pending"] = pending
    ledger["settled_dates"] = sorted(settled_dates)
    st.session_state[VOTE_LEDGER_KEY] = ledger

    if results:
        from accuracy_badge import sync_accuracy_from_ledger

        sync_accuracy_from_ledger(ledger, user_email=_current_user_email())

    return results


def _current_user_email() -> str:
    user = st.session_state.get("member_user")
    if isinstance(user, dict):
        return str(user.get("email", "")).strip()
    return ""


def get_member_settled_history(
    user: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ledger = init_vote_ledger()
    email = str((user or {}).get("email", "")).strip()
    if not email:
        return []
    return [
        h
        for h in ledger.get("history", [])
        if isinstance(h, dict) and str(h.get("email", "")) == email
    ]


def get_last_settled_vote(
    user: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    history = get_member_settled_history(user)
    if not history:
        return None
    return max(history, key=lambda h: str(h.get("date", "")))


LAST_VOTE_DIALOG_KEY = "_open_last_vote_detail"


def request_last_vote_dialog() -> None:
    st.session_state[LAST_VOTE_DIALOG_KEY] = True


def maybe_show_last_vote_dialog(user: dict[str, Any] | None) -> None:
    if not st.session_state.pop(LAST_VOTE_DIALOG_KEY, False):
        return
    _show_last_vote_dialog(user)


def _render_last_vote_dialog_body(user: dict[str, Any] | None) -> None:
    from stock_config import get_stock_name

    record = get_last_settled_vote(user)
    if not record:
        st.info(
            "아직 정산된 투표 기록이 없습니다.\n\n"
            "롱/숏 투표 후 **당일 20:00** 정산이 끝나면 결과가 여기에 표시됩니다."
        )
        return

    try:
        session_d = date.fromisoformat(str(record.get("date", "")))
        date_label = format_korean_date_label(session_d)
    except ValueError:
        date_label = str(record.get("date", ""))

    code = str(record.get("stock_code", ""))
    stock_label = get_stock_name(code) or code
    vote = str(record.get("vote", "")).lower()
    vote_label = "📈 롱 (상승)" if vote == "long" else "📉 숏 (하락)"
    change_pct = float(record.get("change_pct", 0.0))
    hit = bool(record.get("hit"))
    result_label = "⭕ 적중" if hit else "❌ 미적중"
    result_color = "#2E7D32" if hit else "#C62828"
    direction = "상승" if change_pct > 0 else ("하락" if change_pct < 0 else "보합")

    st.markdown(
        f"""
        <div class="last-vote-result-card">
            <p class="last-vote-result-date">{html.escape(date_label)} · {html.escape(stock_label)}</p>
            <p class="last-vote-result-pick">내 투표: <b>{html.escape(vote_label)}</b></p>
            <p class="last-vote-result-market">
                당일 주가: <b>{change_pct:+.2f}%</b> ({direction})
            </p>
            <p class="last-vote-result-verdict" style="color:{result_color};">
                {html.escape(result_label)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("20:00 정산 기준 · 시간외·넥스트 반영 종가 대비 판정")


if hasattr(st, "dialog"):

    @st.dialog("전날 투표 결과")
    def _show_last_vote_dialog(user: dict[str, Any] | None) -> None:
        _render_last_vote_dialog_body(user)

else:

    def _show_last_vote_dialog(user: dict[str, Any] | None) -> None:
        with st.expander("전날 투표 결과", expanded=True):
            _render_last_vote_dialog_body(user)


def format_last_vote_result(record: dict[str, Any] | None) -> str:
    if not record:
        return "—"
    return "⭕ 적중" if record.get("hit") else "❌ 미적중"


# ── 종목별 실시간 집계 ───────────────────────────────────────────

STOCK_VOTES_KEY = "stock_votes"
VOTE_LOCK_BY_STOCK_KEY = "vote_lock_by_stock"
VOTE_SHORT = "short"
VOTE_LONG = "long"


def normalize_vote_type(vote_type: str) -> str:
    if vote_type in ("fear", VOTE_SHORT):
        return VOTE_SHORT
    if vote_type in ("greed", VOTE_LONG):
        return VOTE_LONG
    return vote_type


def _default_bucket(stock_code: str, session_date: str) -> dict[str, Any]:
    seed = int(hashlib.sha256(f"{stock_code}:{session_date}".encode()).hexdigest()[:8], 16)
    short_votes = (seed % 21) + 4
    long_votes = (seed % 19) + 6
    return {
        "session_date": session_date,
        "short": short_votes,
        "long": long_votes,
        "ballots": {},
    }


def _migrate_bucket(bucket: dict[str, Any], stock_code: str, session_date: str) -> dict[str, Any]:
    if "short" not in bucket and "fear" in bucket:
        bucket["short"] = int(bucket.pop("fear", 0))
    if "long" not in bucket and "greed" in bucket:
        bucket["long"] = int(bucket.pop("greed", 0))
    bucket.setdefault("short", 0)
    bucket.setdefault("long", 0)
    bucket.setdefault("ballots", {})
    if bucket.get("session_date") != session_date:
        return _default_bucket(stock_code, session_date)
    return bucket


def current_vote_session_date() -> str:
    open_date = get_open_vote_date()
    if open_date is not None:
        return session_date_str(open_date)
    return session_date_str(get_locked_display_date())


def get_user_stock_vote(stock_code: str, voter_key: str) -> str | None:
    if not voter_key:
        return None
    bucket = init_stock_votes(stock_code)
    side = bucket.get("ballots", {}).get(voter_key)
    if side in (VOTE_LONG, VOTE_SHORT):
        return str(side)
    return None


def init_stock_votes(stock_code: str) -> dict[str, Any]:
    code = str(stock_code).strip()
    session_date = current_vote_session_date()
    if STOCK_VOTES_KEY not in st.session_state:
        st.session_state[STOCK_VOTES_KEY] = {}
    store: dict[str, dict[str, Any]] = st.session_state[STOCK_VOTES_KEY]
    if code not in store:
        store[code] = _default_bucket(code, session_date)
    store[code] = _migrate_bucket(store[code], code, session_date)
    return store[code]


def get_stock_vote_counts(stock_code: str) -> tuple[int, int]:
    bucket = init_stock_votes(stock_code)
    return int(bucket["short"]), int(bucket["long"])


def add_stock_vote(
    stock_code: str,
    vote_type: str,
    *,
    voter_key: str | None = None,
) -> tuple[bool, str]:
    open_date = get_open_vote_date()
    if open_date is None:
        return False, "closed"
    if session_date_str(open_date) != current_vote_session_date():
        return False, "session_mismatch"

    bucket = init_stock_votes(stock_code)
    side = normalize_vote_type(vote_type)
    ballots: dict[str, str] = bucket.setdefault("ballots", {})

    if voter_key:
        prev = ballots.get(voter_key)
        if prev == side:
            return True, "same"
        if prev == VOTE_SHORT:
            bucket["short"] = max(0, int(bucket["short"]) - 1)
        elif prev == VOTE_LONG:
            bucket["long"] = max(0, int(bucket["long"]) - 1)
        ballots[voter_key] = side
    elif bucket.get("user_voted"):
        return False, "already_voted"

    if side == VOTE_SHORT:
        bucket["short"] = int(bucket["short"]) + 1
    else:
        bucket["long"] = int(bucket["long"]) + 1
    if not voter_key:
        bucket["user_voted"] = True
    return True, "ok"


def is_vote_locked_for_stock(stock_code: str) -> bool:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    return bool(locks.get(str(stock_code).strip(), False))


def set_vote_locked_for_stock(stock_code: str) -> None:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    locks[str(stock_code).strip()] = True


def clear_vote_lock_for_stock(stock_code: str) -> None:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    locks.pop(str(stock_code).strip(), None)


def is_trading_vote_open() -> bool:
    return get_open_vote_date() is not None
