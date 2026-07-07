"""유저 프로필 팝업 · 닉네임 클릭 · 투표 이력 조회."""

from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

from accuracy_badge import (
    badge_for_author,
    get_member_badge,
    render_trader_profile_ui,
)

PROFILE_OPEN_KEY = "_open_profile_author_key"


def author_key_for_seed(nickname: str) -> str:
    nick = str(nickname or "익명").strip()
    digest = hashlib.md5(nick.encode("utf-8")).hexdigest()[:12]
    return f"seed:{digest}"


def seed_email_for_author(nickname: str) -> str:
    return f"{author_key_for_seed(nickname).replace(':', '_')}@seed.local"


def author_key_for_user(user: dict[str, Any] | None) -> str:
    if not isinstance(user, dict):
        return ""
    email = str(user.get("email", "")).strip()
    return f"user:{email}" if email else ""


def resolve_post_author_key(post: dict[str, Any]) -> str:
    key = str(post.get("author_key", "")).strip()
    if key:
        return key
    author = str(post.get("author", "익명")).strip()
    return author_key_for_seed(author)


def _email_for_author_key(author_key: str, nickname: str = "") -> str:
    if author_key.startswith("user:"):
        return author_key[5:]
    if author_key.startswith("seed:"):
        return seed_email_for_author(nickname or author_key)
    return ""


def get_author_display_name(author_key: str, fallback: str = "익명") -> str:
    if author_key.startswith("user:"):
        user = st.session_state.get("member_user")
        if isinstance(user, dict) and author_key_for_user(user) == author_key:
            from member_auth import get_member_display_name

            name = get_member_display_name(user)
            if name:
                return name
    return fallback


def get_author_profile(
    author_key: str,
    *,
    nickname: str = "",
) -> dict[str, Any]:
    """누계 적중률 · 최근 투표 이력 · 등급."""
    from stock_votes import get_member_settled_history, init_vote_ledger

    init_vote_ledger()
    nick = nickname or get_author_display_name(author_key, "익명")
    email = _email_for_author_key(author_key, nick)

    if author_key.startswith("user:"):
        user = {"email": email, "name": nick}
        badge = get_member_badge(user)
        history = get_member_settled_history(user)
    else:
        badge = badge_for_author(nick)
        history = [
            h
            for h in (st.session_state.get("member_vote_ledger") or {}).get(
                "history", []
            )
            if isinstance(h, dict) and str(h.get("email", "")) == email
        ]

    history = sorted(
        [h for h in history if isinstance(h, dict)],
        key=lambda x: str(x.get("date", "")),
        reverse=True,
    )
    recent = history[:5]

    return {
        "author_key": author_key,
        "nickname": nick,
        "badge": badge,
        "history": history,
        "recent_items": recent,
    }


def render_profile_dialog_body(author_key: str, *, nickname: str = "") -> None:
    profile = get_author_profile(author_key, nickname=nickname)
    render_trader_profile_ui(
        profile["nickname"],
        profile["badge"],
        recent_items=profile["recent_items"],
    )


if hasattr(st, "dialog"):

    @st.dialog("투자자 프로필")
    def user_profile_dialog(author_key: str, nickname: str = "") -> None:
        render_profile_dialog_body(author_key, nickname=nickname)

else:

    def user_profile_dialog(author_key: str, nickname: str = "") -> None:
        with st.expander("투자자 프로필", expanded=True):
            render_profile_dialog_body(author_key, nickname=nickname)


def request_profile_open(author_key: str) -> None:
    st.session_state[PROFILE_OPEN_KEY] = author_key


def maybe_show_profile_dialog() -> None:
    key = st.session_state.pop(PROFILE_OPEN_KEY, None)
    if key:
        user_profile_dialog(str(key))
