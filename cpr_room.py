"""
개미 심폐소생실 — 토스 피드형 원패스 계좌 심폐소생실 카드 UI
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import sys as _sys
_sys.modules.pop("member_auth", None)

from member_auth import (
    MEMBER_CPR_TOUCH_KEY,
    MEMBER_USER_KEY,
    init_member_session,
    is_member,
    render_compact_kakao_cta,
)
from accuracy_badge import (
    ensure_member_accuracy_profile,
    get_member_badge,
    inject_accuracy_badge_css,
    normalize_post_badge,
    render_accuracy_badge_html,
    render_profile_badge_row,
)

CPR_POSTS_KEY = "cpr_posts"
CPR_DRAFT_KEY = "cpr_draft"
CPR_CLEAR_DRAFT_KEY = "_cpr_clear_draft"
CPR_TOUCHED_KEY = MEMBER_CPR_TOUCH_KEY

CPR_UI_BUILD = "compact-v5"

SEED_POSTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "author": "목동매입왕",
        "badge": {"tier": "expert"},
        "body": "평단 31만인데 오늘 -7%에 심정지 왔습니다... 누가 제 계좌에 제세동기 좀...",
        "likes": 284,
        "comments": 47,
        "ago": "2분 전",
        "tag": "심정지",
    },
    {
        "id": 2,
        "author": "역삼동10억",
        "badge": {"tier": "master"},
        "body": "요즘 개미들 호흡 곤란 오는 거 다 보입니다. 저는 아직 산소포화도 98% 유지 중 ㅋㅋ",
        "likes": 512,
        "comments": 89,
        "ago": "5분 전",
        "tag": "VIP",
    },
    {
        "id": 3,
        "author": "텅장응급실",
        "badge": None,
        "body": "어제 풀매수했는데 오늘 아침에 눈 뜨자마자 응급실行... 인공호흡기 달아주실 분?",
        "likes": 193,
        "comments": 31,
        "ago": "8분 전",
        "tag": "긴급",
    },
    {
        "id": 4,
        "badge": {"tier": "challenger"},
        "body": "실적 발표 전날 매도 안 한 개미들 모여라... 우리 같이 CPR 배워서 살아남자",
        "likes": 367,
        "comments": 52,
        "ago": "12분 전",
        "tag": "모집",
    },
    {
        "id": 5,
        "author": "강남재테크언니",
        "badge": {"tier": "master"},
        "body": "공포지수 20 이하일 때 줍줍한 사람만 ICU에서 VIP 전실 갑니다. 데이터가 말해줘요.",
        "likes": 441,
        "comments": 64,
        "ago": "18분 전",
        "tag": "처방",
    },
    {
        "id": 6,
        "author": "마이너스손절왕",
        "badge": None,
        "body": "손절 버튼 누르는 손가락이 심장마비 온 것처럼 안 움직여요... -40%인데 어떡함",
        "likes": 628,
        "comments": 112,
        "ago": "24분 전",
        "tag": "심정지",
    },
    {
        "id": 7,
        "author": "판교개발자J",
        "badge": None,
        "body": "월급쟁이인데 매달 적립식으로 CPR 중입니다. 아직 심장 박동은 있습니다...",
        "likes": 156,
        "comments": 22,
        "ago": "31분 전",
        "tag": "회복중",
    },
    {
        "id": 8,
        "author": "수원왕초보",
        "badge": None,
        "body": "처음 주식해봤는데 첫날부터 응급실 왔네요 ㅠㅠ 선배 개미들 곡소리 보고 위로 받습니다",
        "likes": 98,
        "comments": 17,
        "ago": "45분 전",
        "tag": "신규",
    },
]

CPR_ROOM_CSS = """
<style>
.cpr-page-title {
    font-size: 1.375rem; font-weight: 800; color: #191f28;
    margin: 0 0 4px 0; letter-spacing: -0.035em; line-height: 1.25;
}
.cpr-ui-build {
    font-size: 0.6875rem; font-weight: 600; color: #b0b8c1;
    margin: 0 0 20px 0; letter-spacing: 0.02em;
}
.cpr-card {
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
    border: none;
    padding: 22px 20px;
    margin-bottom: 20px;
}
.cpr-onepass-headline {
    font-size: 1.0625rem; font-weight: 800; color: #191f28;
    margin: 0 0 6px 0; letter-spacing: -0.03em; line-height: 1.4;
    text-align: left;
}
.cpr-onepass-sub {
    font-size: 0.8125rem; color: #8b95a1; margin: 0;
    font-weight: 500; letter-spacing: -0.01em; line-height: 1.45;
}
.cpr-onepass-tap-hint {
    font-size: 0.75rem; color: #b0b8c1; margin-top: 14px;
    font-weight: 500; letter-spacing: -0.01em;
}
.cpr-kakao-reveal {
    animation: cpr-fade-up 0.28s ease-out both;
    margin-top: 4px;
}
@keyframes cpr-fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
#cpr-guest-unlock [data-testid="stButton"] > button {
    background: #fee500 !important;
    color: #191f28 !important;
    font-weight: 800 !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(254, 229, 0, 0.35) !important;
}
#cpr-guest-unlock [data-testid="stButton"] > button:hover {
    background: #f5dc00 !important;
    color: #191f28 !important;
}
#cpr-onepass-tap [data-testid="stButton"] > button {
    background: #ffffff !important;
    color: #191f28 !important;
    font-size: 1.0625rem !important;
    font-weight: 800 !important;
    text-align: left !important;
    padding: 22px 20px !important;
    min-height: 56px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04) !important;
    border-radius: 20px !important;
    border: none !important;
    letter-spacing: -0.03em !important;
    line-height: 1.45 !important;
    white-space: normal !important;
    justify-content: flex-start !important;
}
#cpr-onepass-tap [data-testid="stButton"] > button:hover {
    background: #fafbfc !important;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.06) !important;
}
#cpr-onepass-tap [data-testid="stButton"] > button p {
    margin: 0 !important;
}
#cpr-onepass-tap [data-testid="stButton"] > button small {
    display: block !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    color: #8b95a1 !important;
    margin-top: 6px !important;
    letter-spacing: -0.01em !important;
}
#cpr-member-compose .cpr-card {
    padding-bottom: 0;
    margin-bottom: 0;
    border-radius: 20px 20px 0 0;
    box-shadow: none;
}
#cpr-member-compose [data-testid="stTextArea"] {
    background: #ffffff;
    border-radius: 0 0 20px 20px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
    padding: 0 12px 4px 12px;
    margin-bottom: 12px;
}
#cpr-member-compose [data-testid="stTextArea"] textarea {
    border: none !important;
    box-shadow: none !important;
    padding-top: 0 !important;
}
.cpr-member-name {
    font-size: 0.8125rem; font-weight: 700; color: #3182f6;
    margin: 0 0 12px 0; letter-spacing: -0.02em;
}
.cpr-feed-label {
    font-size: 0.8125rem; font-weight: 700; color: #8b95a1;
    margin: 8px 0 10px 0; letter-spacing: -0.01em;
}
.cpr-external-feed-head {
    margin-top: 14px !important;
    margin-bottom: 8px !important;
}
.cpr-post-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
    border: none;
    padding: 16px;
    margin-bottom: 12px;
}
.cpr-post-meta {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 6px; margin-bottom: 14px;
}
.cpr-post-author {
    font-size: 0.9375rem; font-weight: 800; color: #191f28;
    letter-spacing: -0.025em;
}
.cpr-post-tag {
    font-size: 0.6875rem; font-weight: 600; color: #8b95a1;
    background: #f2f4f6; padding: 4px 9px; border-radius: 6px;
    margin-left: auto; letter-spacing: -0.01em;
}
.cpr-post-body {
    font-size: 1rem; color: #333d4b; line-height: 1.65;
    margin: 0 0 16px 0; word-break: keep-all; font-weight: 500;
    letter-spacing: -0.025em;
}
.cpr-post-footer {
    font-size: 0.8125rem; color: #adb5bd; font-weight: 600;
    display: flex; gap: 16px; letter-spacing: -0.01em;
}
</style>
"""


def init_cpr_session() -> None:
    init_member_session()
    if CPR_POSTS_KEY not in st.session_state:
        st.session_state[CPR_POSTS_KEY] = [dict(p) for p in SEED_POSTS]
    if CPR_DRAFT_KEY not in st.session_state:
        st.session_state[CPR_DRAFT_KEY] = ""


def _clear_draft_if_pending() -> None:
    if st.session_state.pop(CPR_CLEAR_DRAFT_KEY, False):
        st.session_state[CPR_DRAFT_KEY] = ""


def _add_post(author: str, body: str, *, user: dict[str, Any] | None = None) -> None:
    posts: list[dict[str, Any]] = st.session_state[CPR_POSTS_KEY]
    new_id = max((p.get("id", 0) for p in posts), default=0) + 1
    member_badge = get_member_badge(user)
    posts.insert(
        0,
        {
            "id": new_id,
            "author": author,
            "badge": member_badge,
            "body": body.strip(),
            "likes": 0,
            "comments": 0,
            "ago": "방금",
            "tag": "신규",
        },
    )
    st.session_state[CPR_POSTS_KEY] = posts
    st.session_state[CPR_CLEAR_DRAFT_KEY] = True


def _render_badge(post: dict[str, Any]) -> str:
    badge = normalize_post_badge(post)
    return render_accuracy_badge_html(badge)


def _render_post_card(post: dict[str, Any]) -> str:
    author = html.escape(str(post.get("author", "익명")))
    body = html.escape(str(post.get("body", "")))
    tag = html.escape(str(post.get("tag", "")))
    ago = html.escape(str(post.get("ago", "")))
    likes = int(post.get("likes", 0))
    comments = int(post.get("comments", 0))
    badge_html = _render_badge(post)

    return (
        f'<div class="cpr-post-card">'
        f'<div class="cpr-post-meta">'
        f'<span class="cpr-post-author">{author}</span>'
        f"{badge_html}"
        f'<span class="cpr-post-tag">{tag}</span>'
        f"</div>"
        f'<p class="cpr-post-body">{body}</p>'
        f'<div class="cpr-post-footer">'
        f"<span>공감 {likes}</span>"
        f"<span>댓글 {comments}</span>"
        f"<span>{ago}</span>"
        f"</div></div>"
    )


def _render_guest_onepass() -> None:
    touched = bool(st.session_state.get(CPR_TOUCHED_KEY))

    if not touched:
        st.markdown('<div id="cpr-onepass-tap">', unsafe_allow_html=True)
        if st.button(
            "✍️ 드립 쓰러 가기 (회원전용)",
            key="cpr_onepass_tap",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state[CPR_TOUCHED_KEY] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    render_compact_kakao_cta(button_key="member_kakao_from_cpr")


def render_cpr_compose_zone() -> None:
    """글쓰기 입력대 — 심폐소생실 통합 카드 하단."""
    _clear_draft_if_pending()
    st.markdown('<div id="cpr-tab-compose">', unsafe_allow_html=True)
    if is_member():
        _render_member_compose_inner()
    else:
        _render_guest_onepass()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_member_compose_inner() -> None:
    user = st.session_state.get(MEMBER_USER_KEY) or {}
    _ = user
    st.text_area(
        "곡소리",
        key=CPR_DRAFT_KEY,
        height=64,
        placeholder="오늘 나의 처절한 한탄이나 의견을 적어주세요",
        label_visibility="collapsed",
    )
    if st.button("등록", key="cpr_submit_post", use_container_width=True, type="primary"):
        body = str(st.session_state.get(CPR_DRAFT_KEY, "")).strip()
        if body:
            author = str(user.get("name", "응급실새내기"))
            _add_post(author, body, user=user)
            st.rerun()
        else:
            st.warning("내용을 입력해 주세요.")


def render_cpr_post_feed() -> None:
    """심폐소생실 피드 목록."""
    posts: list[dict[str, Any]] = st.session_state.get(CPR_POSTS_KEY, SEED_POSTS)
    st.markdown(
        f'<p class="cpr-feed-label">실시간 곡소리 · {len(posts)}</p>',
        unsafe_allow_html=True,
    )
    for post in posts:
        st.markdown(_render_post_card(post), unsafe_allow_html=True)


def render_cpr_room(stock_name: str, stock_code: str) -> None:
    """심폐소생실 피드 (투표·글쓰기는 tab_cpr에서 통합 카드로 렌더)."""
    _ = stock_name, stock_code
    init_cpr_session()
    inject_accuracy_badge_css()
    st.markdown(CPR_ROOM_CSS, unsafe_allow_html=True)
    render_cpr_post_feed()
