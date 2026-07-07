"""앱 전역 회원 세션 · 소셜 로그인(카카오/네이버) Mock OAuth + 가입 게이트."""

from __future__ import annotations

import time
from typing import Any

import streamlit as st

from stock_votes import VOTE_LOCK_BY_STOCK_KEY

MEMBER_LOGGED_IN_KEY = "member_logged_in"
MEMBER_USER_KEY = "member_user"
MEMBER_VOTE_LOCK_KEY = "member_vote_lock"
MEMBER_CPR_TOUCH_KEY = "member_cpr_touch"
MEMBER_COMMUNITY_TOUCH_KEY = "member_community_touch"
VOTE_ACCURACY_KEY = "vote_accuracy_30d"

# CPR 모듈 호환
CPR_LOGGED_IN_KEY = MEMBER_LOGGED_IN_KEY
CPR_USER_KEY = MEMBER_USER_KEY
CPR_TOUCHED_KEY = MEMBER_CPR_TOUCH_KEY

MEMBER_NICKNAME_DRAFT_KEY = "member_nickname_draft"

MOCK_OAUTH_PROFILES: dict[str, dict[str, str]] = {
    "kakao": {
        "email": "goksori_trader@kakao.com",
    },
    "naver": {
        "email": "human_index@naver.com",
    },
}

SOCIAL_LOGIN_CSS = """
<style>
.social-login-banner {
    margin: 0 0 14px 0; padding: 16px 16px 14px 16px;
    border-radius: 18px; background: #ffffff;
    border: 1px solid #eef0f4;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.04);
}
.social-login-title {
    margin: 0 0 4px 0; font-size: 0.9375rem; font-weight: 800;
    color: #191f28; letter-spacing: -0.03em; text-align: center;
}
.social-login-sub {
    margin: 0 0 14px 0; font-size: 0.75rem; font-weight: 600;
    color: #8b95a1; letter-spacing: -0.02em; text-align: center;
    line-height: 1.45;
}
.social-login-stack {
    display: flex; flex-direction: column; gap: 10px;
    width: 100%;
}
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
    line-height: 1.6; margin: 0 0 14px 0; letter-spacing: -0.02em;
}
.social-btn-kakao-wrap [data-testid="stButton"] > button,
#member-kakao-gate [data-testid="stButton"] > button,
#member-kakao-compact [data-testid="stButton"] > button[kind="primary"],
#social-oauth-kakao-top_banner [data-testid="stButton"] > button {
    background: #FEE500 !important;
    color: #191919 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
    font-size: 0.9375rem !important;
    min-height: 48px !important;
    letter-spacing: -0.02em !important;
    box-shadow: 0 4px 14px rgba(254, 229, 0, 0.28) !important;
}
.social-btn-kakao-wrap [data-testid="stButton"] > button:hover,
#member-kakao-gate [data-testid="stButton"] > button:hover {
    opacity: 0.92 !important;
}
.social-btn-naver-wrap [data-testid="stButton"] > button,
#social-oauth-naver-top_banner [data-testid="stButton"] > button {
    background: #03C75A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 800 !important;
    font-size: 0.9375rem !important;
    min-height: 48px !important;
    letter-spacing: -0.02em !important;
    box-shadow: 0 4px 14px rgba(3, 199, 90, 0.28) !important;
}
.social-btn-naver-wrap [data-testid="stButton"] > button:hover {
    opacity: 0.94 !important;
}
.member-kakao-slide {
    animation: member-slide-up 0.25s ease-out both;
}
.nickname-setup-card {
    margin: 0 0 14px 0; padding: 18px 16px;
    border-radius: 18px; background: #ffffff;
    border: 1px solid #eef0f4;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.04);
}
.nickname-setup-title {
    margin: 0 0 6px 0; font-size: 1rem; font-weight: 800;
    color: #191f28; letter-spacing: -0.03em; text-align: center;
}
.nickname-setup-sub {
    margin: 0 0 14px 0; font-size: 0.75rem; font-weight: 600;
    color: #8b95a1; line-height: 1.5; text-align: center;
}
@keyframes member-slide-up {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
"""

MEMBER_GATE_CSS = SOCIAL_LOGIN_CSS

DEFAULT_GATE_MSG = (
    "🔒 투표와 글쓰기는 회원전용 기능입니다.<br>"
    "카카오 또는 네이버로 3초 만에 가입하고 실시간 포지션 배틀에 동참해 보세요!"
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


def _nickname_from_email(email: str) -> str:
    local = str(email).split("@", 1)[0].strip()
    return local or "투자자"


def has_nickname_setup(user: dict[str, Any] | None = None) -> bool:
    init_member_session()
    profile = user if user is not None else st.session_state.get(MEMBER_USER_KEY)
    if not isinstance(profile, dict):
        return False
    if profile.get("nickname_set"):
        return bool(str(profile.get("name", "")).strip())
    return False


def needs_nickname_setup(user: dict[str, Any] | None = None) -> bool:
    if not is_member():
        return False
    return not has_nickname_setup(user)


def is_member_ready() -> bool:
    """로그인 + 닉네임 설정 완료."""
    return is_member() and not needs_nickname_setup()


def save_member_nickname(nickname: str) -> tuple[bool, str]:
    nick = str(nickname or "").strip()
    if len(nick) < 2:
        return False, "닉네임은 2자 이상 입력해 주세요."
    if len(nick) > 12:
        return False, "닉네임은 12자 이하로 입력해 주세요."
    init_member_session()
    user = dict(st.session_state.get(MEMBER_USER_KEY) or {})
    user["name"] = nick
    user["nickname_set"] = True
    st.session_state[MEMBER_USER_KEY] = user
    st.session_state.pop(VOTE_ACCURACY_KEY, None)
    st.session_state.pop("_accuracy_badge_css_v8", None)
    st.session_state.pop("_accuracy_badge_css_v7", None)
    st.session_state.pop("_accuracy_badge_css_v4", None)
    st.session_state.pop("_accuracy_badge_css_v3", None)
    st.session_state.pop("_accuracy_badge_css_v2", None)
    st.session_state.pop("_accuracy_badge_css_injected", None)
    st.session_state.pop(MEMBER_NICKNAME_DRAFT_KEY, None)
    return True, ""


def _render_nickname_setup_body(*, key_suffix: str = "main") -> None:
    st.markdown(
        '<div class="nickname-setup-card">'
        '<p class="nickname-setup-title">닉네임을 설정해 주세요</p>'
        '<p class="nickname-setup-sub">곡소리·투표·계급 배지에 표시됩니다.<br>'
        "한 번 설정하면 다음 로그인부터는 자동으로 건너뜁니다.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    user = st.session_state.get(MEMBER_USER_KEY) or {}
    provider = str(user.get("provider", "kakao"))
    provider_label = "카카오" if provider == "kakao" else "네이버"
    st.caption(f"{provider_label} 계정으로 가입 중")
    draft_key = f"{MEMBER_NICKNAME_DRAFT_KEY}_{key_suffix}"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = ""
    nickname = st.text_input(
        "닉네임",
        key=draft_key,
        max_chars=12,
        placeholder="예: 개미왕, 역삼호랭이",
    )
    if st.button(
        "닉네임 저장하고 시작하기",
        key=f"save_nickname_{key_suffix}",
        use_container_width=True,
        type="primary",
    ):
        ok, err = save_member_nickname(nickname)
        if ok:
            st.rerun()
        else:
            st.warning(err)


if hasattr(st, "dialog"):

    @st.dialog("닉네임 설정")
    def nickname_setup_dialog() -> None:
        _render_nickname_setup_body(key_suffix="dialog")

else:

    def nickname_setup_dialog() -> None:
        _render_nickname_setup_body(key_suffix="inline")


def ensure_nickname_setup_flow() -> bool:
    """닉네임 미설정 시 설정 UI 표시. True = 설정 완료."""
    if not needs_nickname_setup():
        return True
    nickname_setup_dialog()
    return False


def simulate_oauth_login(provider: str) -> None:
    """Mock OAuth callback — 실제 Client ID 연동 전 테스트용."""
    profile = MOCK_OAUTH_PROFILES.get(provider)
    if not profile:
        return
    spinner_label = "카카오" if provider == "kakao" else "네이버"
    with st.spinner(f"{spinner_label} 로그인 연동 중..."):
        time.sleep(0.8)
    email = str(profile["email"])
    st.session_state[MEMBER_LOGGED_IN_KEY] = True
    st.session_state[MEMBER_USER_KEY] = {
        "email": email,
        "provider": provider,
        "name": "",
        "nickname_set": False,
    }
    st.session_state[MEMBER_VOTE_LOCK_KEY] = False
    st.session_state[MEMBER_CPR_TOUCH_KEY] = False
    st.session_state[MEMBER_COMMUNITY_TOUCH_KEY] = False
    st.session_state.pop(VOTE_LOCK_BY_STOCK_KEY, None)
    st.session_state.pop(VOTE_ACCURACY_KEY, None)
    st.session_state.pop("_accuracy_badge_css_v8", None)
    st.session_state.pop("_accuracy_badge_css_v7", None)
    st.session_state.pop("_accuracy_badge_css_v4", None)
    st.session_state.pop("_accuracy_badge_css_v3", None)
    st.session_state.pop("_accuracy_badge_css_v2", None)
    st.session_state.pop("_accuracy_badge_css_injected", None)


def simulate_kakao_login() -> None:
    """(호환) 카카오 Mock 로그인."""
    simulate_oauth_login("kakao")


def render_social_login_panel(*, key_suffix: str = "default") -> None:
    """카카오 · 네이버 소셜 로그인 버튼 (세로 스택)."""
    st.markdown(SOCIAL_LOGIN_CSS, unsafe_allow_html=True)
    st.markdown('<div class="social-login-stack">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="social-btn-kakao-wrap" id="social-oauth-kakao-{key_suffix}">',
        unsafe_allow_html=True,
    )
    if st.button(
        "💬 카카오톡으로 3초 만에 시작",
        key=f"oauth_kakao_{key_suffix}",
        use_container_width=True,
        type="primary",
    ):
        simulate_oauth_login("kakao")
        st.rerun()

    st.markdown(
        f'<div class="social-btn-naver-wrap" id="social-oauth-naver-{key_suffix}">',
        unsafe_allow_html=True,
    )
    if st.button(
        "N 네이버로 안전하게 시작",
        key=f"oauth_naver_{key_suffix}",
        use_container_width=True,
    ):
        simulate_oauth_login("naver")
        st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)


def render_social_login_banner() -> None:
    """비로그인 시 상단 — 소셜 로그인 배너."""
    st.markdown(
        '<div class="social-login-banner">'
        '<p class="social-login-title">3초 만에 시작하기</p>'
        '<p class="social-login-sub">카카오 · 네이버로 간편 가입하고<br>'
        "나만의 포지션 적중 계급을 받아보세요.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_social_login_panel(key_suffix="top_banner")


def _render_social_login_dialog_body() -> None:
    st.markdown(
        '<p class="social-login-sub" style="margin-bottom:16px;">'
        "소셜 계정으로 로그인하면 투표·글쓰기·계급 시스템을 이용할 수 있습니다."
        "</p>",
        unsafe_allow_html=True,
    )
    render_social_login_panel(key_suffix="dialog")


if hasattr(st, "dialog"):

    @st.dialog("로그인하고 시작하기")
    def social_login_dialog() -> None:
        _render_social_login_dialog_body()

else:

    def social_login_dialog() -> None:
        render_member_gate()


def render_member_gate(
    *,
    message_html: str | None = None,
    button_key: str = "member_social_signup",
) -> None:
    """회원 전용 잠금 — 소셜 로그인 CTA."""
    st.markdown(MEMBER_GATE_CSS, unsafe_allow_html=True)
    msg = message_html or DEFAULT_GATE_MSG
    st.markdown(
        f'<div class="member-gate-card">'
        f'<span class="member-gate-label">회원 전용</span>'
        f'<p class="member-gate-msg">{msg}</p></div>',
        unsafe_allow_html=True,
    )
    render_social_login_panel(key_suffix=button_key)


def require_member_for_vote() -> bool:
    if is_member():
        return False
    st.session_state[MEMBER_VOTE_LOCK_KEY] = True
    return True


def render_compact_kakao_cta(*, button_key: str = "member_social_compact") -> None:
    """(호환) 슬림 소셜 로그인 CTA."""
    st.markdown(
        f'<div class="member-kakao-slide" id="member-kakao-compact">',
        unsafe_allow_html=True,
    )
    render_social_login_panel(key_suffix=button_key)
    st.markdown("</div>", unsafe_allow_html=True)


def show_vote_gate_if_needed(*, compact: bool = False) -> None:
    if st.session_state.get(MEMBER_VOTE_LOCK_KEY) and not is_member():
        if compact:
            render_compact_kakao_cta(button_key="member_social_from_vote")
        else:
            social_login_dialog()


def get_member_display_name(user: dict[str, Any] | None = None) -> str:
    """설정 완료된 닉네임만 반환."""
    init_member_session()
    profile = user if user is not None else st.session_state.get(MEMBER_USER_KEY)
    if not isinstance(profile, dict) or not has_nickname_setup(profile):
        return ""
    return str(profile.get("name", "")).strip()
