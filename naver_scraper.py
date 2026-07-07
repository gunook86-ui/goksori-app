"""네이버 증권 토론방 — API + 제목·본문 키워드 매칭 (Selenium 없음)"""

from __future__ import annotations

import re
import time
from typing import Any

from http_client import get_http_session
from sentiment_core import (
    MAX_SCAN_PAGES,
    MAX_SCAN_POSTS,
    POST_LIMIT,
    build_analysis_result,
    combine_post_text,
    has_sentiment_keyword,
)
from stock_config import DEFAULT_STOCK_CODE, STOCK_CATALOG, USER_AGENT, normalize_stock_code

NAVER_DISCUSSION_API = "https://m.stock.naver.com/front-api/discussion/list"
DISCUSSION_TYPE = "domesticStock"
PAGE_SIZE = 20
REQUEST_TIMEOUT = (2, 4)


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def _fetch_discussion_page(
    stock_code: str,
    offset: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    params: dict[str, Any] = {
        "discussionType": DISCUSSION_TYPE,
        "itemCode": stock_code,
        "pageSize": PAGE_SIZE,
    }
    if offset:
        params["offset"] = offset

    headers = {
        "Accept": "application/json",
        "Referer": f"https://m.stock.naver.com/pc/domestic/stock/{stock_code}/discussion",
        "User-Agent": USER_AGENT,
    }
    response = get_http_session().get(
        NAVER_DISCUSSION_API,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") or {}
    posts = result.get("posts") or []
    next_offset = result.get("lastOffset")
    if next_offset is not None:
        next_offset = str(next_offset)
    return posts, next_offset


def _naver_post_url(stock_code: str, post_id: str) -> str:
    """네이버 finance PC 토론방 상세 — API id == board_read nid."""
    code = normalize_stock_code(stock_code)
    nid = str(post_id).strip()
    if nid.isdigit():
        return f"https://finance.naver.com/item/board_read.naver?code={code}&nid={nid}"
    return f"https://finance.naver.com/item/board.naver?code={code}"


def get_board_posts(stock_code: str, limit: int = POST_LIMIT) -> list[tuple[str, str, str]]:
    """제목+본문+URL. 키워드 글만 수집. 100개 채울 때까지 최대 20페이지·400개 탐색."""
    collected: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    scanned = 0
    offset: str | None = None

    for _ in range(MAX_SCAN_PAGES):
        if len(collected) >= limit or scanned >= MAX_SCAN_POSTS:
            break

        posts, next_offset = _fetch_discussion_page(stock_code, offset)
        if not posts:
            break

        for post in posts:
            scanned += 1
            post_id = str(post.get("id") or "")
            title = _clean_text(post.get("title") or "")
            body = _clean_text(
                post.get("contentSwReplacedButImg")
                or post.get("contentSwReplaced")
                or ""
            )
            dedupe_key = post_id or combine_post_text(title, body)
            if not dedupe_key or dedupe_key in seen:
                if scanned >= MAX_SCAN_POSTS:
                    break
                continue
            seen.add(dedupe_key)
            if not has_sentiment_keyword(title, body):
                if scanned >= MAX_SCAN_POSTS:
                    break
                continue
            post_url = _naver_post_url(stock_code, post_id) if post_id else ""
            collected.append((title or body[:80], body, post_url))
            if len(collected) >= limit:
                return collected[:limit]
            if scanned >= MAX_SCAN_POSTS:
                break

        if len(collected) >= limit or scanned >= MAX_SCAN_POSTS:
            break
        if not next_offset or next_offset == offset:
            break
        offset = next_offset

    return collected[:limit]


def analyze_naver_board(
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
    posts = get_board_posts(stock_code, limit)
    elapsed = time.perf_counter() - started
    return build_analysis_result(
        posts,
        stock_name=name,
        stock_code=stock_code,
        source="네이버 증권 토론방",
        collect_info=(
            f"제목+본문 키워드 {len(posts)}개 · 최대 {MAX_SCAN_PAGES}페이지 · {elapsed:.2f}초"
        ),
    )
