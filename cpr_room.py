"""
개미 심폐소생실 — Streamlit 네이티브 피드 UI
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import sys as _sys

_sys.modules.pop("member_auth", None)
_sys.modules.pop("accuracy_badge", None)
_sys.modules.pop("member_profile", None)
_sys.modules.pop("stock_votes", None)

from member_auth import (
    MEMBER_CPR_TOUCH_KEY,
    MEMBER_USER_KEY,
    get_member_display_name,
    init_member_session,
    is_member,
    is_member_ready,
    needs_nickname_setup,
    render_compact_kakao_cta,
)
from accuracy_badge import (
    feed_nameplate_html,
    get_member_badge,
    inject_accuracy_badge_css,
    normalize_post_badge,
)
from member_profile import (
    author_key_for_seed,
    author_key_for_user,
    maybe_show_profile_dialog,
    request_profile_open,
    resolve_post_author_key,
)

CPR_POSTS_KEY = "cpr_posts"
CPR_DRAFT_KEY = "cpr_draft"
CPR_CLEAR_DRAFT_KEY = "_cpr_clear_draft"
CPR_TOUCHED_KEY = MEMBER_CPR_TOUCH_KEY
CPR_LIKED_KEY = "cpr_liked_post_ids"
CPR_COMMENT_OPEN_KEY = "cpr_comment_open_post_id"

CPR_UI_BUILD = "native-v17"

CPR_ROOM_CSS = """
<style>
#cpr-onepass-tap [data-testid="stButton"] > button {
    background: #ffffff !important;
    font-weight: 800 !important;
    text-align: left !important;
    padding: 22px 20px !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card) {
    padding: 12px 14px 14px 14px !important;
    overflow: visible !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions) {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    gap: 6px !important;
    margin: 0 !important;
    align-items: stretch !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="column"] {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    width: 50% !important;
    max-width: 50% !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="column"] > div {
    width: 100% !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stElementContainer"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stButton"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stButton"] > button {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    min-height: 2.25rem !important;
    height: 2.25rem !important;
    max-height: 2.25rem !important;
    padding: 0 10px !important;
    border-radius: 10px !important;
    border: 1.5px solid #D1D6DB !important;
    background: #FFFFFF !important;
    color: #333D4B !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    box-shadow: none !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: nowrap !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stButton"] > button[kind="primary"] {
    border-color: #3182F6 !important;
    background: #E8F3FF !important;
    color: #1565C0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.cpr-feed-card)
  div[data-testid="stVerticalBlock"]:has(.cpr-feed-actions)
  [data-testid="stButton"] > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #333D4B !important;
}
</style>
"""

SEED_POSTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "author": "목동매입왕",
        "badge": {"tier": "expert"},
        "body": "평단 31만인데 오늘 -7%에 심정지 왔습니다... 누가 제 계좌에 제세동기 좀...",
        "likes": 284,
        "comments": 47,
        "comment_list": [],
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
        "comment_list": [],
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
        "comment_list": [],
        "ago": "8분 전",
        "tag": "긴급",
    },
    {
        "id": 4,
        "author": "익명챌린저",
        "badge": {"tier": "challenger"},
        "body": "실적 발표 전날 매도 안 한 개미들 모여라... 우리 같이 CPR 배워서 살아남자",
        "likes": 367,
        "comments": 52,
        "comment_list": [],
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
        "comment_list": [],
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
        "comment_list": [],
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
        "comment_list": [],
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
        "comment_list": [],
        "ago": "45분 전",
        "tag": "신규",
    },
]

def init_cpr_session() -> None:
    init_member_session()
    if CPR_POSTS_KEY not in st.session_state:
        st.session_state[CPR_POSTS_KEY] = [dict(p) for p in SEED_POSTS]
    if CPR_DRAFT_KEY not in st.session_state:
        st.session_state[CPR_DRAFT_KEY] = ""
    if CPR_LIKED_KEY not in st.session_state:
        st.session_state[CPR_LIKED_KEY] = []
    _normalize_posts(st.session_state[CPR_POSTS_KEY])


def _normalize_posts(posts: list[dict[str, Any]]) -> None:
    for post in posts:
        raw = post.get("comment_list")
        if not isinstance(raw, list):
            post["comment_list"] = []
        stored = len(post["comment_list"])
        display = int(post.get("comments", stored))
        if stored > display:
            post["comments"] = stored
        elif stored == 0 and display > 0:
            post["_legacy_comment_count"] = display


def _get_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = st.session_state.get(CPR_POSTS_KEY, SEED_POSTS)
    _normalize_posts(posts)
    return posts


def _find_post(post_id: int) -> dict[str, Any] | None:
    for post in _get_posts():
        if int(post.get("id", 0)) == post_id:
            return post
    return None


def _liked_post_ids() -> set[int]:
    return {int(x) for x in st.session_state.get(CPR_LIKED_KEY, [])}


def _is_post_liked(post_id: int) -> bool:
    return post_id in _liked_post_ids()


def _toggle_like(post_id: int) -> None:
    liked = _liked_post_ids()
    post = _find_post(post_id)
    if not post:
        return
    if post_id in liked:
        liked.remove(post_id)
        post["likes"] = max(0, int(post.get("likes", 0)) - 1)
    else:
        liked.add(post_id)
        post["likes"] = int(post.get("likes", 0)) + 1
    st.session_state[CPR_LIKED_KEY] = sorted(liked)


def _toggle_comment_panel(post_id: int) -> None:
    current = st.session_state.get(CPR_COMMENT_OPEN_KEY)
    if current == post_id:
        st.session_state.pop(CPR_COMMENT_OPEN_KEY, None)
    else:
        st.session_state[CPR_COMMENT_OPEN_KEY] = post_id


def _add_comment(post_id: int, author: str, body: str) -> bool:
    post = _find_post(post_id)
    if not post or not body.strip():
        return False
    comments: list[dict[str, Any]] = list(post.get("comment_list") or [])
    comments.append({"author": author, "body": body.strip(), "ago": "방금"})
    post["comment_list"] = comments
    post["comments"] = int(post.get("comments", 0)) + 1
    return True


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
            "author_key": author_key_for_user(user) or author_key_for_seed(author),
            "badge": member_badge,
            "body": body.strip(),
            "likes": 0,
            "comments": 0,
            "comment_list": [],
            "ago": "방금",
            "tag": "신규",
        },
    )
    st.session_state[CPR_POSTS_KEY] = posts
    st.session_state[CPR_CLEAR_DRAFT_KEY] = True


def _render_comment_panel(post: dict[str, Any]) -> None:
    post_id = int(post.get("id", 0))
    comment_list: list[dict[str, Any]] = list(post.get("comment_list") or [])
    legacy = int(post.get("_legacy_comment_count", 0))

    st.markdown("##### 💬 댓글")

    if comment_list:
        for comment in comment_list:
            c_author = str(comment.get("author", "익명"))
            c_body = str(comment.get("body", ""))
            c_ago = str(comment.get("ago", ""))
            st.markdown(f"**{html.escape(c_author)}** · {html.escape(c_body)}")
            st.caption(c_ago)
    elif legacy > 0:
        st.caption(f"이전 댓글 {legacy}개 · 아래에서 새 댓글을 남겨 보세요.")
    else:
        st.caption("아직 댓글이 없습니다. 첫 댓글을 남겨 보세요.")

    if is_member_ready():
        user = st.session_state.get(MEMBER_USER_KEY) or {}
        with st.form(key=f"cpr_comment_form_{post_id}", clear_on_submit=True):
            draft = st.text_input(
                "댓글 입력",
                placeholder="댓글을 입력하세요",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("댓글 등록", type="primary", use_container_width=True)
            if submitted:
                text = draft.strip()
                if not text:
                    st.warning("댓글 내용을 입력해 주세요.")
                else:
                    author = get_member_display_name(user)
                    if not author:
                        st.warning("닉네임 설정 후 댓글을 남길 수 있습니다.")
                    elif _add_comment(post_id, author, text):
                        st.rerun()
    elif is_member() and needs_nickname_setup():
        st.caption("닉네임 설정 후 댓글을 남길 수 있습니다.")
    else:
        st.caption("로그인 후 댓글을 남길 수 있습니다.")


def _render_post_card_interactive(post: dict[str, Any]) -> None:
    author = str(post.get("author", "익명"))
    body = str(post.get("body", ""))
    ago = str(post.get("ago", ""))
    likes = int(post.get("likes", 0))
    comment_count = int(post.get("comments", 0))
    post_id = int(post.get("id", 0))
    badge = normalize_post_badge(post)
    author_key = resolve_post_author_key(post)
    liked = _is_post_liked(post_id)
    comment_open = st.session_state.get(CPR_COMMENT_OPEN_KEY) == post_id

    with st.container(border=True):
        st.markdown('<span class="cpr-feed-card" style="display:none"></span>', unsafe_allow_html=True)

        line_col, prof_col = st.columns([0.88, 0.12], gap="small", vertical_alignment="center")
        with line_col:
            st.markdown(feed_nameplate_html(author, badge, ago), unsafe_allow_html=True)
        with prof_col:
            if st.button("👤", key=f"cpr_prof_{post_id}", help="프로필 보기", use_container_width=True):
                request_profile_open(author_key)
                st.rerun()

        st.markdown(body)

        with st.container():
            st.markdown('<span class="cpr-feed-actions" style="display:none"></span>', unsafe_allow_html=True)
            act_like, act_comment = st.columns(2, gap="small")
            with act_like:
                like_type = "primary" if liked else "secondary"
                if st.button(
                    f"👍 {likes}",
                    key=f"cpr_like_{post_id}",
                    use_container_width=True,
                    type=like_type,
                ):
                    _toggle_like(post_id)
                    st.rerun()
            with act_comment:
                open_mark = "▾" if comment_open else "▸"
                if st.button(
                    f"💬 댓글 {comment_count} {open_mark}",
                    key=f"cpr_comment_{post_id}",
                    use_container_width=True,
                ):
                    _toggle_comment_panel(post_id)
                    st.rerun()

        if comment_open:
            st.divider()
            _render_comment_panel(post)


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
    if is_member_ready():
        _render_member_compose_inner()
    elif is_member() and needs_nickname_setup():
        st.info("닉네임 설정을 완료하면 글쓰기가 열립니다.")
    else:
        _render_guest_onepass()


def _render_member_compose_inner() -> None:
    user = st.session_state.get(MEMBER_USER_KEY) or {}
    with st.form(key="cpr_post_form", clear_on_submit=True):
        draft = st.text_area(
            "곡소리",
            placeholder="오늘 나의 처절한 한탄이나 의견을 적어주세요",
            label_visibility="collapsed",
            height=72,
        )
        if st.form_submit_button("등록", use_container_width=True, type="primary"):
            text = draft.strip()
            if not text:
                st.warning("내용을 입력해 주세요.")
            else:
                author = get_member_display_name(user)
                if not author:
                    st.warning("닉네임 설정 후 글을 등록할 수 있습니다.")
                else:
                    _add_post(author, text, user=user)
                    st.rerun()


def render_cpr_post_feed() -> None:
    """심폐소생실 피드 — 닉네임 탭 시 프로필 팝업."""
    maybe_show_profile_dialog()
    for post in _get_posts():
        _render_post_card_interactive(post)


def render_cpr_room(stock_name: str, stock_code: str) -> None:
    """심폐소생실 피드 (투표·글쓰기는 tab_cpr에서 통합 카드로 렌더)."""
    _ = stock_name, stock_code
    init_cpr_session()
    inject_accuracy_badge_css()
    st.markdown(CPR_ROOM_CSS, unsafe_allow_html=True)
    render_cpr_post_feed()
