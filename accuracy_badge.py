"""
30일 적중률 기반 계급장 뱃지 — 토스 감성 칩 UI + 백분위 표기.
"""

from __future__ import annotations

import hashlib
import html
from datetime import date, timedelta
from typing import Any

import streamlit as st

ACCURACY_WINDOW_DAYS = 30
VOTE_ACCURACY_KEY = "vote_accuracy_30d"
ACCURACY_CSS_INJECTED_KEY = "_accuracy_badge_css_injected"

TIER_MASTER = "master"
TIER_CHALLENGER = "challenger"
TIER_EXPERT = "expert"

TIER_CONFIG: dict[str, dict[str, Any]] = {
    TIER_MASTER: {
        "label": "마스터",
        "percentile": 1,
        "icon": "👑",
        "css": "acc-badge-master",
    },
    TIER_CHALLENGER: {
        "label": "챌린저",
        "percentile": 5,
        "icon": "🥇",
        "css": "acc-badge-challenger",
    },
    TIER_EXPERT: {
        "label": "전문가",
        "percentile": 10,
        "icon": "🥈",
        "css": "acc-badge-expert",
    },
}

# 시드 작성자별 30일 적중률 백분위 (Mock DB)
AUTHOR_TIER_SEEDS: dict[str, str] = {
    "목동매입왕": TIER_EXPERT,
    "역삼동10억": TIER_MASTER,
    "분당존버맨": TIER_CHALLENGER,
    "강남재테크언니": TIER_MASTER,
}

ACCURACY_BADGE_CSS = """
<style>
.acc-badge {
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 0.6875rem; font-weight: 700; line-height: 1.2;
    padding: 5px 10px; border-radius: 999px;
    letter-spacing: -0.02em; white-space: nowrap;
    vertical-align: middle;
}
.acc-badge-tier { font-weight: 800; }
.acc-badge-dot { opacity: 0.55; font-weight: 600; }
.acc-badge-pct { font-weight: 900 !important; letter-spacing: -0.03em; }
.acc-badge-icon { font-size: 0.75rem; line-height: 1; }
.acc-badge-master {
    background: linear-gradient(135deg, #1a1a2e 0%, #2d2a4a 100%);
    color: #ffe566;
    box-shadow: 0 2px 10px rgba(26, 26, 46, 0.28);
    border: 1px solid rgba(255, 229, 102, 0.35);
}
.acc-badge-master .acc-badge-pct { color: #fff3a0; }
.acc-badge-challenger {
    background: #e8f3ff;
    color: #1565c0;
    border: 1px solid #b3d4ff;
    box-shadow: 0 2px 8px rgba(49, 130, 246, 0.12);
}
.acc-badge-challenger .acc-badge-pct { color: #0d47a1; }
.acc-badge-expert {
    background: #f2f4f6;
    color: #4e5968;
    border: 1px solid #d1d6db;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.acc-badge-expert .acc-badge-pct { color: #333d4b; }
.cpr-profile-row {
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 8px; margin: 0 0 12px 0;
}
.cpr-profile-nick {
    font-size: 0.9375rem; font-weight: 800; color: #191f28;
    letter-spacing: -0.025em;
}
.cpr-profile-stats {
    font-size: 0.75rem; color: #8b95a1; font-weight: 600;
    margin: 0 0 14px 0; letter-spacing: -0.01em;
}
</style>
"""


def inject_accuracy_badge_css() -> None:
    if st.session_state.get(ACCURACY_CSS_INJECTED_KEY):
        return
    st.markdown(ACCURACY_BADGE_CSS, unsafe_allow_html=True)
    st.session_state[ACCURACY_CSS_INJECTED_KEY] = True


def tier_from_percentile(percentile: int) -> str | None:
    if percentile <= 1:
        return TIER_MASTER
    if percentile <= 5:
        return TIER_CHALLENGER
    if percentile <= 10:
        return TIER_EXPERT
    return None


def tier_from_accuracy_rate(accuracy_pct: float) -> str | None:
    """30일 적중률 → 상위 백분위 티어 (Mock 랭킹)."""
    if accuracy_pct >= 92.0:
        return TIER_MASTER
    if accuracy_pct >= 82.0:
        return TIER_CHALLENGER
    if accuracy_pct >= 72.0:
        return TIER_EXPERT
    return None


def build_badge(tier: str) -> dict[str, Any]:
    cfg = TIER_CONFIG[tier]
    return {
        "tier": tier,
        "label": cfg["label"],
        "percentile": cfg["percentile"],
        "icon": cfg["icon"],
        "css": cfg["css"],
    }


def badge_for_author(author: str) -> dict[str, Any] | None:
    tier = AUTHOR_TIER_SEEDS.get(author)
    if tier:
        return build_badge(tier)
    digest = hashlib.md5(author.encode()).hexdigest()
    bucket = int(digest[:2], 16) % 100
    if bucket < 3:
        return build_badge(TIER_MASTER)
    if bucket < 12:
        return build_badge(TIER_CHALLENGER)
    if bucket < 25:
        return build_badge(TIER_EXPERT)
    return None


def _mock_vote_history(user_key: str) -> list[dict[str, Any]]:
    seed = int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16)
    history: list[dict[str, Any]] = []
    today = date.today()
    for i in range(ACCURACY_WINDOW_DAYS):
        day = today - timedelta(days=ACCURACY_WINDOW_DAYS - 1 - i)
        if (seed + i * 13) % 5 == 0:
            continue
        hit = (seed + i * 17) % 10 != 0
        history.append(
            {
                "date": day.isoformat(),
                "vote": "fear" if (seed + i) % 2 else "greed",
                "hit": hit,
            }
        )
    return history


def init_vote_accuracy_session() -> None:
    if VOTE_ACCURACY_KEY not in st.session_state:
        st.session_state[VOTE_ACCURACY_KEY] = {
            "history": [],
            "total_votes": 0,
            "hits": 0,
            "accuracy_pct": 0.0,
            "percentile_rank": 50,
            "tier": None,
        }


def _recompute_accuracy_stats(store: dict[str, Any]) -> None:
    history: list[dict[str, Any]] = store.get("history", [])
    total = len(history)
    hits = sum(1 for item in history if item.get("hit"))
    accuracy = round(hits / total * 100, 1) if total else 0.0
    tier = tier_from_accuracy_rate(accuracy)
    percentile = TIER_CONFIG[tier]["percentile"] if tier else 50
    store.update(
        {
            "total_votes": total,
            "hits": hits,
            "accuracy_pct": accuracy,
            "percentile_rank": percentile,
            "tier": tier,
        }
    )


def ensure_member_accuracy_profile(user: dict[str, Any] | None) -> dict[str, Any]:
    """회원 30일 누적 투표 적중률 프로필 (세션 Mock)."""
    init_vote_accuracy_session()
    store = st.session_state[VOTE_ACCURACY_KEY]
    if not store.get("history"):
        name = str((user or {}).get("name", "guest"))
        store["history"] = _mock_vote_history(name)
        _recompute_accuracy_stats(store)
    return store


def record_member_vote(*, vote_type: str) -> None:
    """한강 투표 1건 기록 → 30일 적중률 갱신."""
    init_vote_accuracy_session()
    store = st.session_state[VOTE_ACCURACY_KEY]
    history: list[dict[str, Any]] = list(store.get("history", []))
    seed = hashlib.md5(f"{vote_type}:{date.today().isoformat()}".encode()).hexdigest()
    hit = int(seed[:2], 16) % 3 != 0
    history.append(
        {
            "date": date.today().isoformat(),
            "vote": vote_type,
            "hit": hit,
        }
    )
    cutoff = (date.today() - timedelta(days=ACCURACY_WINDOW_DAYS - 1)).isoformat()
    history = [item for item in history if str(item.get("date", "")) >= cutoff]
    store["history"] = history
    _recompute_accuracy_stats(store)


def get_member_badge(user: dict[str, Any] | None) -> dict[str, Any] | None:
    stats = ensure_member_accuracy_profile(user)
    tier = stats.get("tier")
    if not tier:
        return None
    badge = build_badge(str(tier))
    badge["accuracy_pct"] = stats.get("accuracy_pct", 0.0)
    badge["total_votes"] = stats.get("total_votes", 0)
    return badge


def normalize_post_badge(post: dict[str, Any]) -> dict[str, Any] | None:
    badge = post.get("badge")
    if not badge:
        return badge_for_author(str(post.get("author", "")))
    if isinstance(badge, dict) and badge.get("tier"):
        return build_badge(str(badge["tier"]))
    if isinstance(badge, dict) and badge.get("percentile"):
        tier = tier_from_percentile(int(badge["percentile"]))
        return build_badge(tier) if tier else None
    return badge_for_author(str(post.get("author", "")))


def render_accuracy_badge_html(badge: dict[str, Any] | None) -> str:
    if not badge:
        return ""
    label = html.escape(str(badge.get("label", "")))
    pct = int(badge.get("percentile", 10))
    icon = html.escape(str(badge.get("icon", "")))
    css = html.escape(str(badge.get("css", "acc-badge-expert")))
    return (
        f'<span class="acc-badge {css}">'
        f'<span class="acc-badge-tier">{label}</span>'
        f'<span class="acc-badge-dot">·</span>'
        f'<span class="acc-badge-pct">상위 {pct}%</span>'
        f'<span class="acc-badge-icon">{icon}</span>'
        f"</span>"
    )


def render_profile_badge_row(
    nick: str,
    badge: dict[str, Any] | None,
    *,
    accuracy_pct: float | None = None,
    total_votes: int | None = None,
) -> str:
    nick_html = html.escape(nick)
    badge_html = render_accuracy_badge_html(badge)
    stats = ""
    if accuracy_pct is not None and total_votes:
        stats = (
            f'<p class="cpr-profile-stats">'
            f"30일 투표 적중률 <b>{accuracy_pct:.1f}%</b> · 누적 {total_votes}표"
            f"</p>"
        )
    return (
        f'<div class="cpr-profile-row">'
        f'<span class="cpr-profile-nick">{nick_html}</span>'
        f"{badge_html}"
        f"</div>{stats}"
    )
