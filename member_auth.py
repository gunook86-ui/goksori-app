"""앱 전역 회원 세션 · 밀당식 가입 유도 게이트."""

from __future__ import annotations

import time

import streamlit as st

from stock_votes import VOTE_LOCK_BY_STOCK_KEY

MEMBER_LOGGED_IN_KEY = "member_logged_in"
MEMBER_USER_KEY = "member_user"
MEMBER_VOTE_LOCK_KEY = "member_vote_lock"
MEMBER_CPR_TOUCH_KEY = "member_cpr_touch"
MEMBER_COMMUNITY_TOUCH_KEY = "member_community_touch"

# CPR 모듈 호환
CPR_LOGGED_IN_KEY = MEMBER_LOGGED_IN_KEY
CPR_USER_KEY = MEMBER_USER_KEY
CPR_TOUCHED_KEY = MEMBER_CPR_TOUCH_KEY

MEMBER_GATE_CSS = """
<style>
.member-gate-card {
    margin: 14px 0 6px 0; padding: 20px;
    border-radius: 20px; background: #ffffff;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
    text-align: center;
}
.member-gate-label {
    display: inline-block; font-size: 0.6875rem; font-weight: 700;
    color: #3182f6; background: #e8f3ff; padding: 4px 10px;
    border-radius: 999px; margin-bottom: 10px;
}
.member-gate-msg {
    font-size: 0.9375rem; font-weight: 600; color: #333d4b;
    line-height: 1.6; margin: 0; letter-spacing: -0.02em;
}
#member-kakao-gate [data-testid="stButton"] > button {
    background: #fee500 !important;
    color: #191f28 !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 14px rgba(254, 229, 0, 0.35) !important;
}
#member-kakao-compact [data-testid="stButton"] > button {
    background: #fee500 !important;
    color: #191f28 !important;
    font-weight: 800 !important;
    font-size: 0.875rem !important;
    min-height: 44px !important;
    box-shadow: 0 4px 14px rgba(254, 229, 0, 0.35) !important;
    margin-top: 4px !important;
}
.member-kakao-slide {
    animation: member-slide-up 0.25s ease-out both;
}
@keyframes member-slide-up {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""

DEFAULT_GATE_MSG = (
    "🔒 투표와 글쓰기는 회원전용 기능입니다.<br>"
    "카카오톡 3초 가입 후 개미들의 실시간 심리 배틀에 동참해 보세요!"
)


def init_member_session() -> None:
    if MEMBER_LOGGED_IN_KEY not in st.session_state:
        legacy = st.session_state.pop("cpr_logged_in", None)
        st.session_state[MEMBER_LOGGED_IN_KEY] = bool(legacy)
    if MEMBER_USER_KEY not in st.session_state:
        st.session_state[MEMBER_USER_KEY] = st.session_state.pop("cpr_user", None)
    if MEMBER_VOTE_LOCK_KEY not in st.session_state:
        st.session_state[MEMBER_VOTE_LOCK_KEY] = False
    if MEMBER_CPR_TOUCH_KEY not in st.session_state:
        legacy_touch = st.session_state.pop("cpr_compose_touched", False)
        st.session_state[MEMBER_CPR_TOUCH_KEY] = bool(legacy_touch)
    if MEMBER_COMMUNITY_TOUCH_KEY not in st.session_state:
        st.session_state[MEMBER_COMMUNITY_TOUCH_KEY] = False


def is_member() -> bool:
    init_member_session()
    return bool(st.session_state.get(MEMBER_LOGGED_IN_KEY))


def simulate_kakao_login() -> None:
    with st.spinner("카카오 로그인 연동 중..."):
        time.sleep(1.0)
    st.session_state[MEMBER_LOGGED_IN_KEY] = True
    st.session_state[MEMBER_USER_KEY] = {
        "name": "응급실새내기",
        "provider": "kakao",
    }
    st.session_state[MEMBER_VOTE_LOCK_KEY] = False
    st.session_state[MEMBER_CPR_TOUCH_KEY] = False
    st.session_state[MEMBER_COMMUNITY_TOUCH_KEY] = False
    st.session_state.pop(VOTE_LOCK_BY_STOCK_KEY, None)


def render_member_gate(
    *,
    message_html: str | None = None,
    button_key: str = "member_kakao_signup",
) -> None:
    """회원 전용 잠금 — 카카오 가입 CTA."""
    st.markdown(MEMBER_GATE_CSS, unsafe_allow_html=True)
    msg = message_html or DEFAULT_GATE_MSG
    st.markdown(
        f'<div class="member-gate-card">'
        f'<span class="member-gate-label">회원 전용</span>'
        f'<p class="member-gate-msg">{msg}</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div id="member-kakao-gate">', unsafe_allow_html=True)
    if st.button(
        "💛 카카오 3초 가입하기",
        key=button_key,
        use_container_width=True,
        type="primary",
    ):
        simulate_kakao_login()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def require_member_for_vote() -> bool:
    """투표 시도 시 True = 잠금 표시 필요."""
    if is_member():
        return False
    st.session_state[MEMBER_VOTE_LOCK_KEY] = True
    return True


def render_compact_kakao_cta(*, button_key: str = "member_kakao_compact") -> None:
    """가입 CTA 버튼만 — 카드 박스 없이 하단 슬림 노출."""
    st.markdown(
        '<div id="member-kakao-compact" class="member-kakao-slide">',
        unsafe_allow_html=True,
    )
    if st.button(
        "💛 카카오 3초 가입하기",
        key=button_key,
        use_container_width=True,
        type="primary",
    ):
        simulate_kakao_login()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def show_vote_gate_if_needed(*, compact: bool = False) -> None:
    if st.session_state.get(MEMBER_VOTE_LOCK_KEY) and not is_member():
        if compact:
            render_compact_kakao_cta(button_key="member_kakao_from_vote")
        else:
            render_member_gate(button_key="member_kakao_from_vote")
