"""종목별 실시간 롱/숏 투표 — 세션(금일) 단위 집계."""

from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

from vote_settlement import (
    get_locked_display_date,
    get_open_vote_date,
    session_date_str,
)

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
    """현재 세션에서 유저가 고른 롱/숏 (없으면 None)."""
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
    """세션·종목당 1표. 마감 전 변경 시 이전 표 차감."""
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
