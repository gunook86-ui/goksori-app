"""토스증권 커뮤니티 — wts-cert-api requests 전용 (Selenium 없음)"""

from __future__ import annotations

import re
import time
from typing import Any

from http_client import get_http_session
from sentiment_core import (
    MAX_SCAN_PAGES,
    MAX_SCAN_POSTS,
    POST_LIMIT,
    SKIP_TITLE_KEYWORDS,
    build_analysis_result,
    combine_post_text,
    has_sentiment_keyword,
)
from stock_config import DEFAULT_STOCK_CODE, STOCK_CATALOG, normalize_stock_code

API_BASE = "https://wts-cert-api.tossinvest.com"
COMMENTS_PATH = "/api/v4/comments"
STOCK_INFO_PATH = "/api/v1/stock-infos"

SUBJECT_TYPE = "STOCK"
SORT_TYPE = "RECENT"
REQUEST_TIMEOUT = (2, 4)
MAX_DISPLAY_TITLE_LENGTH = 120
MAX_BODY_LENGTH = 4000
FALLBACK_TEXT = "(토스 글)"

IGNORE_EXACT_TITLES = {"토스증권"}


def _clean_text(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).replace("\u200b", "").strip()
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _pick_text_block(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_text(value)
    return ""


def _extract_post(comment: dict[str, Any]) -> tuple[str, str]:
    """토스 댓글 JSON에서 제목·본문을 최대한 복원."""
    title = ""
    body = ""
    message_block = comment.get("message")

    if isinstance(message_block, dict):
        title = _pick_text_block(message_block, ("title", "subject", "headline"))
        body = _pick_text_block(message_block, ("message", "content", "body", "text"))
    elif isinstance(message_block, str):
        body = _clean_text(message_block)

    if not title:
        title = _pick_text_block(comment, ("title", "subject", "headline"))
    if not body:
        body = _pick_text_block(comment, ("message", "content", "body", "text"))

    title, body = _normalize_post_text(title, body)
    return title, body


def _normalize_post_text(title: str, body: str) -> tuple[str, str]:
    title = title[:MAX_DISPLAY_TITLE_LENGTH]
    body = body[:MAX_BODY_LENGTH]

    if not title and body:
        title = body[:MAX_DISPLAY_TITLE_LENGTH]
    if not body and title:
        body = title
    if not title and not body:
        title = FALLBACK_TEXT
        body = FALLBACK_TEXT
    return title, body


def _display_title(title: str, body: str) -> str:
    if title and title != FALLBACK_TEXT:
        return title[:MAX_DISPLAY_TITLE_LENGTH]
    if body:
        return body[:MAX_DISPLAY_TITLE_LENGTH]
    return FALLBACK_TEXT


def _is_valid_post(title: str, body: str, stock_name: str) -> bool:
    display = _display_title(title, body)
    if display == FALLBACK_TEXT:
        return False
    if len(display) < 2:
        return False
    if display in IGNORE_EXACT_TITLES or display == stock_name:
        return False
    if any(keyword in display for keyword in SKIP_TITLE_KEYWORDS):
        return False
    if "좋아요" in display and "댓글" in display:
        return False
    if re.fullmatch(r"[\d,.\-+()%원\s]+", display):
        return False
    return True


def _api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Referer": "https://www.tossinvest.com/",
    }
    response = get_http_session().get(
        f"{API_BASE}{path}",
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("토스 API 응답 형식이 올바르지 않습니다.")
    return payload


def resolve_stock_guid(stock_code: str) -> tuple[str, str]:
    """항상 stock-infos API로 최신 GUID를 조회 (하드코딩 캐시 사용 안 함)."""
    stock_code = normalize_stock_code(stock_code)
    meta = STOCK_CATALOG.get(stock_code, {})
    product_code = meta.get("toss_product") or f"A{stock_code}"

    payload = _api_get(STOCK_INFO_PATH, params={"codes": product_code})
    items = payload.get("result") or []
    if not items:
        raise ValueError(f"토스 종목 정보 없음: {product_code}")

    item = items[0]
    resolved_guid = item.get("guid") or item.get("isinCode")
    if not resolved_guid:
        raise ValueError(f"토스 GUID 없음: {product_code}")
    return product_code, str(resolved_guid)


def _fetch_comments_page(
    session,
    headers: dict[str, str],
    subject_id: str,
    cursor: str | int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "subjectType": SUBJECT_TYPE,
        "subjectId": subject_id,
        "commentSortType": SORT_TYPE,
    }
    if cursor is not None:
        params["lastCommentId"] = cursor

    response = session.get(
        f"{API_BASE}{COMMENTS_PATH}",
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("토스 댓글 API 응답 형식이 올바르지 않습니다.")
    return payload.get("result") or {}


def _toss_post_url(product_code: str, comment_id: int | str | None) -> str:
    """토스 커뮤니티 글 상세 — commentId 기반 공식 딥링크."""
    product = str(product_code or "").strip()
    if not product:
        return "https://www.tossinvest.com/"

    community_fallback = f"https://www.tossinvest.com/stocks/{product}/community"
    if comment_id is None:
        return community_fallback

    cid = str(comment_id).strip()
    if not cid.isdigit():
        return community_fallback

    return f"https://www.tossinvest.com/community/posts/{cid}"


def get_toss_community_posts(
    stock_code: str,
    stock_name: str,
    limit: int = POST_LIMIT,
) -> tuple[list[tuple[str, str, str]], dict[str, int]]:
    """제목+본문+URL. 키워드 글 수집."""
    product_code, subject_id = resolve_stock_guid(stock_code)
    collected: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    stats = {
        "scanned": 0,
        "parsed": 0,
        "valid": 0,
        "keyword_hits": 0,
        "api_pages": 0,
        "empty_pages": 0,
    }

    cursor: str | int | None = None
    session = get_http_session()
    referer = f"https://www.tossinvest.com/stocks/{product_code}/community"
    headers = {"Accept": "application/json", "Referer": referer}

    while stats["api_pages"] < MAX_SCAN_PAGES and stats["scanned"] < MAX_SCAN_POSTS:
        if len(collected) >= limit:
            break

        try:
            result = _fetch_comments_page(session, headers, subject_id, cursor)
        except Exception:
            break

        stats["api_pages"] += 1
        comments = result.get("results") or []
        if not comments:
            stats["empty_pages"] += 1
            break

        for comment in comments:
            if stats["scanned"] >= MAX_SCAN_POSTS or len(collected) >= limit:
                break

            stats["scanned"] += 1
            try:
                title, body = _extract_post(comment)
            except Exception:
                title, body = FALLBACK_TEXT, FALLBACK_TEXT

            if title == FALLBACK_TEXT and body == FALLBACK_TEXT:
                continue

            stats["parsed"] += 1
            if not _is_valid_post(title, body, stock_name):
                continue

            stats["valid"] += 1
            if not has_sentiment_keyword(title, body):
                continue

            stats["keyword_hits"] += 1
            dedupe_key = combine_post_text(_display_title(title, body), body)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            comment_id = comment.get("commentId")
            post_url = _toss_post_url(product_code, comment_id)
            collected.append((_display_title(title, body), body, post_url))

        if len(collected) >= limit or stats["scanned"] >= MAX_SCAN_POSTS:
            break
        if not result.get("hasNext"):
            break
        next_cursor = result.get("key")
        if next_cursor is None or next_cursor == cursor:
            break
        cursor = next_cursor

    return collected[:limit], stats


def analyze_toss_community(
    stock_code: str = DEFAULT_STOCK_CODE,
    stock_name: str | None = None,
    *,
    post_limit: int | None = None,
) -> dict:
    started = time.perf_counter()
    stock_code = normalize_stock_code(stock_code)
    meta = STOCK_CATALOG.get(stock_code, {})
    name = stock_name or meta.get("name") or stock_code
    limit = post_limit if post_limit is not None else POST_LIMIT
    posts, stats = get_toss_community_posts(stock_code, name, limit)
    elapsed = time.perf_counter() - started
    return build_analysis_result(
        posts,
        stock_name=name,
        stock_code=stock_code,
        source="토스증권 커뮤니티",
        collect_info=(
            f"제목+본문 키워드 {len(posts)}개 · "
            f"탐색 {stats['scanned']}건 · {stats['api_pages']}페이지 · {elapsed:.2f}초"
        ),
    )


if __name__ == "__main__":
    data = analyze_toss_community("000660", "SK하이닉스")
    print(f"수집 {data['post_count']}개 · {data['collect_info']}")
    print(f"📊 [{data['stock_name']}] {data['score']}점 ({data['status']})")
    print(f"공포 {data['fear_count']} · 탐욕 {data['greed_count']}")
