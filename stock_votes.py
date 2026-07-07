"""종목별 실시간 투표 — session_state 딕셔너리 백엔드."""

from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

STOCK_VOTES_KEY = "stock_votes"
VOTE_LOCK_BY_STOCK_KEY = "vote_lock_by_stock"


def _default_bucket(stock_code: str) -> dict[str, Any]:
    """종목 코드 시드 — 데모용 초기 투표 분포 (종목마다 다름)."""
    seed = int(hashlib.sha256(stock_code.encode()).hexdigest()[:8], 16)
    fear = (seed % 41) + 8
    greed = (seed % 37) + 12
    return {"fear": fear, "greed": greed, "user_voted": False}


def init_stock_votes(stock_code: str) -> dict[str, Any]:
    code = str(stock_code).strip()
    if STOCK_VOTES_KEY not in st.session_state:
        st.session_state[STOCK_VOTES_KEY] = {}
    store: dict[str, dict[str, Any]] = st.session_state[STOCK_VOTES_KEY]
    if code not in store:
        store[code] = _default_bucket(code)
    return store[code]


def get_stock_vote_counts(stock_code: str) -> tuple[int, int]:
    bucket = init_stock_votes(stock_code)
    return int(bucket["fear"]), int(bucket["greed"])


def add_stock_vote(stock_code: str, vote_type: str) -> None:
    bucket = init_stock_votes(stock_code)
    if vote_type == "fear":
        bucket["fear"] = int(bucket["fear"]) + 1
    else:
        bucket["greed"] = int(bucket["greed"]) + 1
    bucket["user_voted"] = True


def is_vote_locked_for_stock(stock_code: str) -> bool:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    return bool(locks.get(str(stock_code).strip(), False))


def set_vote_locked_for_stock(stock_code: str) -> None:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    locks[str(stock_code).strip()] = True


def clear_vote_lock_for_stock(stock_code: str) -> None:
    locks: dict[str, bool] = st.session_state.setdefault(VOTE_LOCK_BY_STOCK_KEY, {})
    locks.pop(str(stock_code).strip(), None)
