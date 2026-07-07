"""
포지션 적중률 기반 계급(티어) 시스템 — 롱/숏 투표 vs 실시간 주가 변동.
"""

from __future__ import annotations

import hashlib
import html
from typing import Any

import streamlit as st

ACCURACY_WINDOW_DAYS = 30  # 레거시 호환
VOTE_ACCURACY_KEY = "vote_accuracy_30d"
ACCURACY_CSS_INJECTED_KEY = "_accuracy_badge_css_v12"

FEED_TIER_CHIP_STYLE = (
    "display:inline-flex;align-items:center;gap:3px;"
    "background-color:#F4F6F8;color:#4E5968;"
    "padding:4px 10px;border-radius:15px;font-size:12px;font-weight:500;"
    "margin-left:8px;line-height:1.35;letter-spacing:-0.02em;"
)
FEED_NICK_STYLE = (
    "font-size:16px;font-weight:800;color:#111111;"
    "letter-spacing:-0.03em;flex-shrink:0;"
)
FEED_AUTHOR_BAR_STYLE = (
    "display:flex;flex-wrap:wrap;align-items:center;"
    "background:#F8F9FB;border:1px solid #EEF0F3;border-radius:10px;"
    "padding:10px 12px;margin:0 0 10px 0;width:100%;box-sizing:border-box;"
)

TIER_ROOKIE = "rookie"
TIER_NCO = "nco"
TIER_OFFICER = "officer"
TIER_ELITE = "elite"

LEGACY_TIER_MAP: dict[str, str] = {
    "master": TIER_ELITE,
    "expert": TIER_OFFICER,
    "challenger": TIER_NCO,
}

TIER_CONFIG: dict[str, dict[str, Any]] = {
    TIER_ROOKIE: {
        "label": "관망형 투자자",
        "hint": "시장 방향과 다른 포지션을 고르는 경향이 있습니다.",
        "icon": "📊",
        "css": "acc-badge-rookie",
        "min_pct": 0.0,
        "max_pct": 45.0,
    },
    TIER_NCO: {
        "label": "원금 사수형 투자자",
        "hint": "변동성 구간에서도 비교적 안정적인 예측을 유지합니다.",
        "icon": "⚖️",
        "css": "acc-badge-nco",
        "min_pct": 46.0,
        "max_pct": 55.0,
    },
    TIER_OFFICER: {
        "label": "추세 포착형 투자자",
        "hint": "단기 방향성 예측에서 높은 적중률을 보입니다.",
        "icon": "🎯",
        "css": "acc-badge-officer",
        "min_pct": 56.0,
        "max_pct": 70.0,
    },
    TIER_ELITE: {
        "label": "시그널 마스터",
        "hint": "상위 구간 적중률 — 시장 흐름을 선행하는 참여자입니다.",
        "icon": "⭐",
        "css": "acc-badge-elite",
        "min_pct": 71.0,
        "max_pct": 100.0,
    },
}

AUTHOR_ACCURACY_SEEDS: dict[str, float] = {
    "목동매입왕": 58.0,
    "역삼동10억": 74.0,
    "분당존버맨": 52.0,
    "강남재테크언니": 78.0,
    "텅장응급실": 41.0,
    "마이너스손절왕": 38.0,
}

ACCURACY_BADGE_CSS = """
<style>
.acc-badge {
    display: inline-flex; align-items: center; gap: 5px;
    max-width: 100%; box-sizing: border-box;
    font-size: 0.6875rem; font-weight: 700; line-height: 1.35;
    padding: 6px 11px; border-radius: 999px;
    letter-spacing: -0.02em; vertical-align: middle;
    word-break: keep-all; overflow-wrap: anywhere;
}
.acc-badge--compact {
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; max-width: min(100%, 11.5rem);
}
.acc-badge-tier { font-weight: 800; line-height: 1.35; }
.acc-badge-icon {
    flex: 0 0 auto; font-size: 0.8125rem; line-height: 1;
}
.acc-badge-rookie {
    background: #fff0f0; color: #c62828; border: 1px solid #ffcdd2;
    box-shadow: 0 2px 8px rgba(198, 40, 40, 0.1);
}
.acc-badge-nco {
    background: #f2f4f6; color: #4e5968; border: 1px solid #d1d6db;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.acc-badge-officer {
    background: #e8f3ff; color: #1565c0; border: 1px solid #b3d4ff;
    box-shadow: 0 2px 8px rgba(49, 130, 246, 0.12);
}
.acc-badge-elite {
    background: linear-gradient(135deg, #1a1a2e 0%, #2d2a4a 100%);
    color: #ffe566; border: 1px solid rgba(255, 229, 102, 0.35);
    box-shadow: 0 2px 10px rgba(26, 26, 46, 0.28);
}
.acc-tier-profile-badge {
    width: 100%; box-sizing: border-box;
    margin: 0 0 8px 0; padding: 12px 14px;
    border-radius: 14px; border: 1px solid #eef0f4;
    background: #ffffff;
}
.acc-tier-profile-badge.acc-badge-rookie {
    background: #fff8f8; border-color: #ffcdd2;
}
.acc-tier-profile-badge.acc-badge-nco {
    background: #fafbfc; border-color: #e5e8eb;
}
.acc-tier-profile-badge.acc-badge-officer {
    background: #f5f9ff; border-color: #cfe3ff;
}
.acc-tier-profile-badge.acc-badge-elite {
    background: linear-gradient(135deg, #1a1a2e 0%, #2d2a4a 100%);
    border-color: rgba(255, 229, 102, 0.35);
}
.acc-tier-profile-head {
    display: flex; align-items: flex-start; gap: 8px;
    margin: 0 0 6px 0;
}
.acc-tier-profile-label {
    font-size: 0.875rem; font-weight: 800; line-height: 1.45;
    letter-spacing: -0.03em; word-break: keep-all;
    overflow-wrap: break-word; flex: 1 1 auto; min-width: 0;
}
.acc-tier-profile-badge.acc-badge-elite .acc-tier-profile-label {
    color: #ffe566;
}
.acc-tier-profile-hint {
    margin: 0; padding: 0 0 0 1.75rem;
    font-size: 0.75rem; font-weight: 600; line-height: 1.55;
    letter-spacing: -0.02em; word-break: keep-all;
    overflow-wrap: break-word; color: #6b7684;
}
.acc-tier-profile-badge.acc-badge-elite .acc-tier-profile-hint {
    color: rgba(255, 245, 180, 0.92);
}
.cpr-profile-row {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 8px; margin: 0 0 10px 0; width: 100%;
}
.cpr-profile-nick {
    font-size: 0.9375rem; font-weight: 800; color: #191f28;
    letter-spacing: -0.025em; word-break: keep-all;
}
.cpr-profile-stats {
    font-size: 0.75rem; color: #8b95a1; font-weight: 600;
    margin: 0 0 12px 0; letter-spacing: -0.01em; line-height: 1.5;
    word-break: keep-all; overflow-wrap: break-word;
}
.cpr-tier-card {
    margin: 0 0 12px 0; padding: 0;
    border-radius: 0; background: transparent; border: none;
}
.cpr-tier-card-title {
    font-size: 0.6875rem; font-weight: 700; color: #8b95a1;
    margin: 0 0 8px 0; letter-spacing: -0.01em;
}
.cpr-post-meta .acc-badge { max-width: calc(100% - 4rem); }
/* ── 피드: 티어 회색 칩 (닉네임 뒤) ── */
.feed-tier-chip {
    display: inline-flex; align-items: center; gap: 3px;
    background-color: #F4F6F8; color: #4E5968;
    padding: 4px 10px; border-radius: 15px;
    font-size: 12px; font-weight: 500;
    margin-left: 8px; line-height: 1.35;
    letter-spacing: -0.02em;
    max-width: min(100%, 18rem); overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
}
.feed-author-line {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 0; margin: 0 0 10px 0; width: 100%;
}
.feed-profile-line {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 6px; margin: 0 0 12px 0; width: 100%;
    line-height: 1.4;
}
.cpr-feed-nameplate {
    margin: 0 0 8px 0; padding: 0; line-height: 1.55;
    font-size: 13px; color: #6F7785; letter-spacing: -0.02em;
}
.cpr-feed-nick {
    font-size: 15px; font-weight: 700; color: #111111;
}
.cpr-feed-meta, .cpr-feed-ago {
    font-size: 13px; font-weight: 500; color: #6F7785;
}
.cpr-feed-ago { color: #8E94A0; }
.cpr-profile-nick {
    font-size: 15px; font-weight: 700; color: #111111;
    margin: 0 0 10px 0; padding: 0; letter-spacing: -0.02em;
}
.feed-profile-meta {
    display: inline-flex; flex-wrap: wrap; align-items: center; gap: 5px;
}
.feed-profile-sep {
    color: #d1d6db; font-weight: 700; font-size: 0.75rem;
}
.feed-profile-ago {
    font-size: 13px; font-weight: 500; color: #8E94A0;
    font-style: italic; letter-spacing: -0.01em;
}
.feed-profile-tag {
    margin-left: auto;
    font-size: 0.6875rem; font-weight: 600; color: #8b95a1;
    background: #f2f4f6; padding: 3px 8px; border-radius: 6px;
}
/* ── 극단 티어 카드 네온 테두리 ── */
.feed-card-highlight-elite {
    border: 1px solid #FFD700 !important;
    box-shadow: 0 0 0 1px rgba(255, 215, 0, 0.35),
                0 4px 18px rgba(255, 215, 0, 0.18) !important;
}
.feed-card-highlight-rookie {
    border: 1px solid #1890FF !important;
    box-shadow: 0 0 0 1px rgba(24, 144, 255, 0.35),
                0 4px 18px rgba(24, 144, 255, 0.14) !important;
}
/* ── 내 프로필 — 피드와 동일 인포 블록 ── */
.my-profile-block {
    background: #FFFFFF; border: 1px solid #EEF0F3;
    border-radius: 14px; padding: 14px 14px 12px 14px;
    margin: 0 0 12px 0;
}
.my-profile-block .feed-author-line { margin-bottom: 10px; }
.my-vote-stats-board {
    display: flex; flex-wrap: wrap; gap: 10px 16px;
    margin: 0; padding: 10px 0 0 0;
    border-top: 1px solid #F0F2F5;
}
.my-vote-stat {
    display: flex; flex-direction: column; gap: 2px;
    min-width: 0;
}
.my-vote-stat-label {
    font-size: 11px; font-weight: 600; color: #8E94A0;
    letter-spacing: -0.01em;
}
.my-vote-stat-value {
    font-size: 15px; font-weight: 800; color: #111111;
    letter-spacing: -0.02em;
}
.my-vote-stat-value.hit { color: #2E7D32; }
.my-vote-stat-value.miss { color: #C62828; }
.my-vote-stat-btn-wrap [data-testid="stButton"] > button {
    width: 100% !important;
    background: #F8F9FB !important;
    border: 1px solid #EEF0F3 !important;
    border-radius: 10px !important;
    padding: 8px 10px !important;
    min-height: 0 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
}
.my-vote-stat-btn-wrap [data-testid="stButton"] > button:hover {
    background: #EFF2F5 !important;
    border-color: #DDE1E6 !important;
}
.my-vote-stat-btn-wrap [data-testid="stButton"] > button p {
    font-size: 13px !important; font-weight: 700 !important;
    color: #111111 !important; margin: 0 !important;
    line-height: 1.45 !important;
}
.last-vote-result-card {
    background: #F8F9FB; border: 1px solid #EEF0F3;
    border-radius: 12px; padding: 14px 16px; margin: 0;
}
.last-vote-result-date {
    font-size: 14px; font-weight: 800; color: #111111;
    margin: 0 0 10px 0; letter-spacing: -0.02em;
}
.last-vote-result-pick, .last-vote-result-market {
    font-size: 13px; font-weight: 600; color: #4E5968;
    margin: 0 0 6px 0; line-height: 1.5;
}
.last-vote-result-verdict {
    font-size: 18px; font-weight: 800; margin: 12px 0 0 0;
    letter-spacing: -0.02em;
}
.my-profile-acc {
    font-size: 13px; font-weight: 600; color: #6F7785;
    margin: 0; letter-spacing: -0.01em;
}
.profile-dialog-nick {
    font-size: 1rem; font-weight: 700; color: #1E2022;
    margin: 0 0 10px 0; letter-spacing: -0.03em;
}
.profile-dialog-stats {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 8px; margin: 12px 0;
}
.profile-stat-box {
    background: #f8f9fb; border-radius: 12px; padding: 10px;
    text-align: center; border: 1px solid #eef0f4;
}
.profile-stat-label {
    display: block; font-size: 0.6875rem; font-weight: 600;
    color: #8E94A0;
}
.profile-stat-value {
    display: block; font-size: 1rem; font-weight: 800;
    color: #191f28; margin-top: 2px;
}
.profile-streak-title {
    font-size: 0.75rem; font-weight: 700; color: #6b7684;
    margin: 8px 0 4px 0;
}
.profile-streak-row {
    font-size: 1.25rem; letter-spacing: 0.12em; margin: 0 0 10px 0;
}
.profile-history-list {
    margin: 0; padding-left: 1.1rem; font-size: 0.75rem;
    color: #4e5968; line-height: 1.6;
}
@media (max-width: 640px) {
    .feed-profile-line {
        gap: 4px 5px; row-gap: 6px;
    }
    .feed-profile-nick {
        font-size: 0.875rem;
    }
    .feed-tier-chip {
        max-width: 100%; flex: 1 1 auto;
        font-size: 0.625rem; padding: 2px 7px;
    }
    .feed-profile-tag {
        margin-left: 0; flex: 0 0 100%;
    }
}
</style>
"""


def inject_accuracy_badge_css() -> None:
    if st.session_state.get(ACCURACY_CSS_INJECTED_KEY):
        return
    st.markdown(ACCURACY_BADGE_CSS, unsafe_allow_html=True)
    st.session_state[ACCURACY_CSS_INJECTED_KEY] = True


def normalize_vote_side(vote_type: str) -> str:
    if vote_type in ("long", "greed"):
        return "long"
    if vote_type in ("short", "fear"):
        return "short"
    return vote_type


def tier_from_accuracy_rate(accuracy_pct: float) -> str:
    if accuracy_pct >= 71.0:
        return TIER_ELITE
    if accuracy_pct >= 56.0:
        return TIER_OFFICER
    if accuracy_pct >= 46.0:
        return TIER_NCO
    return TIER_ROOKIE


def build_badge(tier: str) -> dict[str, Any]:
    cfg = TIER_CONFIG[tier]
    return {
        "tier": tier,
        "label": cfg["label"],
        "hint": cfg["hint"],
        "icon": cfg["icon"],
        "css": cfg["css"],
    }


def init_vote_accuracy_session() -> None:
    if VOTE_ACCURACY_KEY not in st.session_state:
        st.session_state[VOTE_ACCURACY_KEY] = {
            "history": [],
            "total_votes": 0,
            "hits": 0,
            "accuracy_pct": 0.0,
            "tier": TIER_ROOKIE,
        }


def sync_accuracy_from_ledger(
    ledger: dict[str, Any] | None = None,
    *,
    user_email: str = "",
) -> None:
    """정산된 vote_ledger → 누계 적중률·티어 갱신."""
    init_vote_accuracy_session()
    store = st.session_state[VOTE_ACCURACY_KEY]
    if ledger is None:
        from stock_votes import init_vote_ledger

        ledger = init_vote_ledger()
    email = str(user_email or "").strip()
    history: list[dict[str, Any]] = list(ledger.get("history") or [])
    if email:
        history = [h for h in history if str(h.get("email", "")) == email]
    else:
        history = []
    store["history"] = [
        {
            "date": str(h.get("date", "")),
            "vote": str(h.get("vote", "")),
            "stock_code": str(h.get("stock_code", "")),
            "change_pct": float(h.get("change_pct", 0.0)),
            "hit": bool(h.get("hit")),
        }
        for h in history
        if isinstance(h, dict)
    ]
    _recompute_accuracy_stats(store)


def _recompute_accuracy_stats(store: dict[str, Any]) -> None:
    history: list[dict[str, Any]] = store.get("history", [])
    total = len(history)
    hits = sum(1 for item in history if item.get("hit"))
    accuracy = round(hits / total * 100, 1) if total else 0.0
    tier = tier_from_accuracy_rate(accuracy)
    store.update(
        {
            "total_votes": total,
            "hits": hits,
            "accuracy_pct": accuracy,
            "tier": tier,
        }
    )


def ensure_member_accuracy_profile(user: dict[str, Any] | None) -> dict[str, Any]:
    init_vote_accuracy_session()
    store = st.session_state[VOTE_ACCURACY_KEY]
    email = str((user or {}).get("email", "")).strip()
    if email:
        from stock_votes import get_member_settled_history, init_vote_ledger

        init_vote_ledger()
        settled = get_member_settled_history(user)
        if settled or not store.get("history"):
            store["history"] = [
                {
                    "date": str(h.get("date", "")),
                    "vote": str(h.get("vote", "")),
                    "stock_code": str(h.get("stock_code", "")),
                    "change_pct": float(h.get("change_pct", 0.0)),
                    "hit": bool(h.get("hit")),
                }
                for h in settled
            ]
            _recompute_accuracy_stats(store)
    return store


def record_member_vote(*, vote_type: str, stock_code: str) -> None:
    """(호환) 즉시 정산 대신 pending 큐에 적재 — 정산은 vote_settlement가 수행."""
    _ = vote_type, stock_code


def get_member_badge(user: dict[str, Any] | None) -> dict[str, Any]:
    stats = ensure_member_accuracy_profile(user)
    tier = str(stats.get("tier") or TIER_ROOKIE)
    badge = build_badge(tier)
    badge["accuracy_pct"] = float(stats.get("accuracy_pct", 0.0))
    badge["total_votes"] = int(stats.get("total_votes", 0))
    badge["hits"] = int(stats.get("hits", 0))
    return badge


def badge_for_author(author: str) -> dict[str, Any]:
    accuracy = AUTHOR_ACCURACY_SEEDS.get(author)
    if accuracy is None:
        digest = hashlib.md5(author.encode()).hexdigest()
        accuracy = 35 + int(digest[:2], 16) % 50
    tier = tier_from_accuracy_rate(float(accuracy))
    badge = build_badge(tier)
    badge["accuracy_pct"] = float(accuracy)
    badge["total_votes"] = 20
    badge["hits"] = int(round(20 * accuracy / 100))
    return badge


def normalize_post_badge(post: dict[str, Any]) -> dict[str, Any]:
    badge = post.get("badge")
    author = str(post.get("author", "익명"))
    fallback = badge_for_author(author)
    if isinstance(badge, dict):
        tier_key = str(badge.get("tier", ""))
        tier_key = LEGACY_TIER_MAP.get(tier_key, tier_key)
        if tier_key in TIER_CONFIG:
            built = build_badge(tier_key)
            accuracy = float(badge.get("accuracy_pct") or 0.0)
            if accuracy <= 0:
                accuracy = float(fallback.get("accuracy_pct", 0.0))
            built["accuracy_pct"] = accuracy
            built["total_votes"] = int(
                badge.get("total_votes") or fallback.get("total_votes", 0)
            )
            built["hits"] = int(
                round(built["total_votes"] * accuracy / 100)
                if built["total_votes"]
                else 0
            )
            return built
    return fallback


def render_tier_name_chip_html(badge: dict[str, Any] | None) -> str:
    """계급명 알약 배지 (적중률 제외)."""
    if not badge:
        return ""
    label = html.escape(str(badge.get("label", "")))
    icon = html.escape(str(badge.get("icon", "")))
    style = (
        "display:inline-flex;align-items:center;gap:4px;"
        "background-color:#F4F6F8;color:#4E5968;"
        "padding:5px 11px;border-radius:15px;font-size:12px;font-weight:600;"
        "line-height:1.35;letter-spacing:-0.02em;"
    )
    return f'<span class="feed-tier-name-chip" style="{style}">{icon} {label}</span>'


def render_accuracy_chip_html(badge: dict[str, Any] | None) -> str:
    """적중률 전용 알약 배지."""
    if not badge:
        return ""
    acc = float(badge.get("accuracy_pct", 0.0))
    acc_text = f"{acc:.0f}%" if acc == int(acc) else f"{acc:.1f}%"
    style = (
        "display:inline-flex;align-items:center;"
        "background-color:#EEF2FF;color:#3D5AFE;"
        "padding:5px 11px;border-radius:15px;font-size:12px;font-weight:700;"
        "line-height:1.35;letter-spacing:-0.02em;"
    )
    return (
        f'<span class="feed-acc-chip" style="{style}">적중률 {acc_text}</span>'
    )


def render_feed_tier_chip_html(badge: dict[str, Any] | None) -> str:
    """계급 + 적중률 알약 배지."""
    if not badge:
        return ""
    label = html.escape(str(badge.get("label", "")))
    icon = html.escape(str(badge.get("icon", "")))
    acc = float(badge.get("accuracy_pct", 0.0))
    acc_text = f"{acc:.0f}%" if acc == int(acc) else f"{acc:.1f}%"
    return (
        f'<span class="feed-tier-chip" style="{FEED_TIER_CHIP_STYLE}">'
        f"{icon} {label} · {acc_text}</span>"
    )


def render_author_line_html(
    nick: str,
    badge: dict[str, Any] | None,
    *,
    ago: str = "",
) -> str:
    """닉네임 + 티어 배지 한 줄 (정적 HTML)."""
    nick_html = html.escape(nick or "익명")
    tier = render_feed_tier_chip_html(badge)
    ago_html = ""
    if ago:
        ago_html = (
            f'<span class="feed-profile-ago" style="margin-left:auto;font-size:13px;'
            f'font-weight:500;color:#8E94A0;">{html.escape(ago)}</span>'
        )
    return (
        f'<div class="feed-author-line" style="{FEED_AUTHOR_BAR_STYLE}">'
        f'<span class="feed-profile-nick" style="{FEED_NICK_STYLE}">{nick_html}</span>'
        f"{tier}{ago_html}"
        f"</div>"
    )


def render_feed_profile_meta_html(
    badge: dict[str, Any] | None,
    *,
    ago: str = "",
    tag: str = "",
) -> str:
    """티어칩 · 시간 · 태그 (닉네임 제외)."""
    parts: list[str] = []
    tier_chip = render_feed_tier_chip_html(badge)
    if tier_chip:
        parts.append(f'<span class="feed-profile-meta">{tier_chip}')
        if ago:
            parts.append('<span class="feed-profile-sep">·</span>')
            parts.append(
                f'<span class="feed-profile-ago">{html.escape(ago)}</span>'
            )
        parts.append("</span>")
    elif ago:
        parts.append(
            f'<span class="feed-profile-ago">{html.escape(ago)}</span>'
        )
    tag_html = ""
    if tag:
        tag_html = (
            f'<span class="feed-profile-tag">{html.escape(tag)}</span>'
        )
    return f'{"".join(parts)}{tag_html}'


def render_feed_profile_line_html(
    badge: dict[str, Any] | None,
    nick: str,
    *,
    ago: str = "",
    tag: str = "",
) -> str:
    """닉네임 · 티어칩 · 시간 — 미니멀 피드 프로필 한 줄."""
    nick_html = html.escape(nick or "익명")
    parts: list[str] = [
        f'<span class="feed-profile-nick">{nick_html}</span>',
    ]
    tier_chip = render_feed_tier_chip_html(badge)
    if tier_chip:
        parts.append('<span class="feed-profile-sep">·</span>')
        parts.append(tier_chip)
    if ago:
        parts.append('<span class="feed-profile-sep">·</span>')
        parts.append(
            f'<span class="feed-profile-ago">{html.escape(ago)}</span>'
        )
    tag_html = ""
    if tag:
        tag_html = (
            f'<span class="feed-profile-tag">{html.escape(tag)}</span>'
        )
    return (
        f'<div class="feed-profile-line">{"".join(parts)}{tag_html}</div>'
    )


def _sanitize_feed_author(author: str, badge: dict[str, Any] | None) -> str:
    """닉네임 필드에 등급·적중률이 중복 합쳐진 경우 분리."""
    nick = str(author or "익명").strip() or "익명"
    if not badge:
        return nick
    label = str(badge.get("label", "")).strip()
    icon = str(badge.get("icon", "")).strip()
    acc = float(badge.get("accuracy_pct", 0.0))
    acc_t = f"{acc:.0f}%" if acc == int(acc) else f"{acc:.1f}%"
    for fragment in (
        f"{icon} {label} ({acc_t})".strip(),
        f"{label} ({acc_t})",
        label,
        acc_t,
        "적중률",
    ):
        if fragment and fragment in nick:
            nick = nick.replace(fragment, "")
    nick = nick.replace("()", "").replace("·", " ").strip()
    while "  " in nick:
        nick = nick.replace("  ", " ")
    return nick or "익명"


def feed_nameplate_html(author: str, badge: dict[str, Any] | None, ago: str = "") -> str:
    """피드 이름표 — 닉네임 · 등급(적중률) · 시간 한 줄."""
    clean_author = _sanitize_feed_author(author, badge)
    nick = html.escape(clean_author)
    segs: list[str] = [
        f'<strong class="cpr-feed-nick">{nick}</strong>',
    ]
    if badge:
        icon = str(badge.get("icon", "")).strip()
        label_raw = str(badge.get("label", "")).strip()
        label = html.escape(label_raw)
        acc = float(badge.get("accuracy_pct", 0.0))
        acc_t = f"{acc:.0f}%" if acc == int(acc) else f"{acc:.1f}%"
        prefix = f"{icon} " if icon else ""
        meta_plain = f"{prefix}{label_raw} ({acc_t})".strip()
        if meta_plain and meta_plain not in clean_author:
            segs.append(
                f'<span class="cpr-feed-meta">{prefix}{label} ({acc_t})</span>'
            )
    ago_clean = str(ago or "").strip()
    if ago_clean:
        segs.append(f'<span class="cpr-feed-ago">{html.escape(ago_clean)}</span>')
    return f'<p class="cpr-feed-nameplate">{" · ".join(segs)}</p>'


def tier_caption_text(badge: dict[str, Any] | None) -> str:
    """피드용 — 등급 · 적중률 한 줄."""
    if not badge:
        return ""
    icon = str(badge.get("icon", "")).strip()
    label = str(badge.get("label", "")).strip()
    acc = float(badge.get("accuracy_pct", 0.0))
    acc_text = f"{acc:.0f}%" if acc == int(acc) else f"{acc:.1f}%"
    prefix = f"{icon} " if icon else ""
    return f"{prefix}{label} · 적중률 {acc_text}"


def _render_vote_timeline_row(item: dict[str, Any]) -> None:
    """최근 투표 이력 — 타임라인 한 줄."""
    from datetime import date

    from stock_votes import format_korean_date_label

    try:
        session_d = date.fromisoformat(str(item.get("date", "")))
        date_label = format_korean_date_label(session_d)
    except ValueError:
        date_label = str(item.get("date", ""))

    vote_raw = str(item.get("vote", "")).lower()
    vote_label = "롱" if vote_raw == "long" else "숏"
    hit = bool(item.get("hit"))
    result_label = "적중" if hit else "미적중"
    change_pct = float(item.get("change_pct", 0.0))
    code = str(item.get("stock_code", ""))

    st.markdown(
        f"**{html.escape(date_label)}** · `{html.escape(code)}` · "
        f"{html.escape(vote_label)} 포지션 · "
        f"{'✓' if hit else '✗'} {result_label} "
        f"({change_pct:+.2f}%)"
    )


def render_trader_profile_ui(
    nick: str,
    badge: dict[str, Any],
    *,
    recent_items: list[dict[str, Any]] | None = None,
    show_last_vote_cta: bool = False,
    last_vote_label: str = "—",
    last_vote_btn_key: str = "member_last_vote_btn",
) -> None:
    """통합 투자자 프로필 — 팝업 · 내 프로필 공용 (Streamlit 네이티브)."""
    inject_accuracy_badge_css()

    display_nick = html.escape(nick or "투자자")
    tier_label = str(badge.get("label", "—"))
    tier_icon = str(badge.get("icon", "")).strip()
    acc = float(badge.get("accuracy_pct", 0.0))
    total = int(badge.get("total_votes", 0))
    hits = int(badge.get("hits", 0))

    st.markdown(f'<p class="cpr-profile-nick">{display_nick}</p>', unsafe_allow_html=True)

    with st.container(border=True):
        tier_col, acc_col = st.columns(2, gap="medium")
        with tier_col:
            st.caption("현재 등급")
            st.markdown(f"**{tier_icon} {html.escape(tier_label)}**".strip())
        with acc_col:
            st.caption("누계 적중률")
            st.markdown(f"**{acc:.1f}%**")
        st.caption(f"누적 투표 {total}회 · 예측 적중 {hits}회")

    if show_last_vote_cta:
        hint = "탭하면 상세 결과" if last_vote_label not in ("—", "") else "정산 후 표시"
        from stock_votes import request_last_vote_dialog

        if st.button(
            f"전날 투표 결과 · {last_vote_label}",
            key=last_vote_btn_key,
            use_container_width=True,
            type="secondary",
            help=hint,
        ):
            request_last_vote_dialog()
            st.rerun()

    if recent_items is not None:
        st.markdown("#### 최근 포지션 예측 결과")
        if recent_items:
            for item in recent_items:
                _render_vote_timeline_row(item)
        else:
            st.caption("아직 정산된 투표 기록이 없습니다.")


def render_member_tier_profile(user: dict[str, Any] | None) -> None:
    """내 프로필 — 투표 패널 상단 (통합 규격)."""
    from member_auth import get_member_display_name
    from stock_votes import (
        format_last_vote_result,
        get_last_settled_vote,
        maybe_show_last_vote_dialog,
    )

    badge = get_member_badge(user)
    nick = get_member_display_name(user) or "투자자"
    last = get_last_settled_vote(user)
    result_text = format_last_vote_result(last)

    render_trader_profile_ui(
        nick,
        badge,
        show_last_vote_cta=True,
        last_vote_label=result_text,
    )
    maybe_show_last_vote_dialog(user)


def get_feed_card_highlight_class(badge: dict[str, Any] | None) -> str:
    """71%+ 또는 45%- 극단 티어 카드 네온 하이라이트."""
    if not badge:
        return ""
    tier = str(badge.get("tier", ""))
    if tier == TIER_ELITE:
        return "feed-card-highlight-elite"
    if tier == TIER_ROOKIE:
        return "feed-card-highlight-rookie"
    return ""


def render_accuracy_badge_html(badge: dict[str, Any] | None, *, compact: bool = True) -> str:
    """게시글 등 인라인 배지 — compact 시 티어 회색 칩."""
    if compact:
        return render_feed_tier_chip_html(badge)
    if not badge:
        return ""
    label = html.escape(str(badge.get("label", "")))
    icon = html.escape(str(badge.get("icon", "")))
    css = html.escape(str(badge.get("css", "acc-badge-nco")))
    return (
        f'<span class="acc-badge {css}">'
        f'<span class="acc-badge-icon">{icon}</span>'
        f'<span class="acc-badge-tier">{label}</span>'
        f"</span>"
    )


def render_tier_profile_card_html(badge: dict[str, Any] | None) -> str:
    """프로필 전용 — 계급명 + 위트 있는 안내 문구."""
    if not badge:
        return ""
    label = html.escape(str(badge.get("label", "")))
    hint = html.escape(str(badge.get("hint", "")))
    icon = html.escape(str(badge.get("icon", "")))
    css = html.escape(str(badge.get("css", "acc-badge-nco")))
    return (
        f'<div class="acc-tier-profile-badge {css}">'
        f'<div class="acc-tier-profile-head">'
        f'<span class="acc-badge-icon">{icon}</span>'
        f'<span class="acc-tier-profile-label">{label}</span>'
        f"</div>"
        f'<p class="acc-tier-profile-hint">{hint}</p>'
        f"</div>"
    )


def render_profile_badge_row(
    nick: str,
    badge: dict[str, Any] | None,
    *,
    accuracy_pct: float | None = None,
    total_votes: int | None = None,
    hits: int | None = None,
) -> str:
    nick_html = html.escape(nick)
    tier_card = render_tier_profile_card_html(badge)
    stats = ""
    if accuracy_pct is not None and total_votes is not None:
        hit_text = f" · 적중 {hits}회" if hits is not None else ""
        stats = (
            f'<p class="cpr-profile-stats">'
            f"누계 적중률 <b>{accuracy_pct:.1f}%</b> · "
            f"총 투표 {total_votes}회{hit_text}"
            f"</p>"
        )
    return (
        f'<div class="cpr-tier-card">'
        f'<div class="cpr-profile-row">'
        f'<span class="cpr-profile-nick">{nick_html}</span>'
        f"</div>"
        f"{tier_card}"
        f"{stats}"
        f"</div>"
    )


