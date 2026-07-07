"""공포·탐욕 인간지표 공통 분석 로직 (네이버·토스 공용)"""

import re

POST_LIMIT = 100
MAX_SCAN_PAGES = 20
MAX_SCAN_POSTS = 400
NEUTRAL_SCORE = 50.0
NEUTRAL_STATUS = "평온"

FEAR_WORDS = [
    "한강", "살려줘", "손절", "망했다", "끝", "휴지", "신용", "반대매매",
    "상폐", "지옥", "폭락", "개미무덤", "탈출", "손실", "눈물", "공포",
    "매도", "돔황차", "흑우", "패닉", "음봉", "파란불", "녹는다", "대피",
    "추락", "자살", "곡소리", "멸망", "상장폐지", "패닉셀", "뇌동매매",
    "구조대", "상투", "고점", "물렸다", "기절", "한숨", "파산", "거품",
    "매도세", "하방", "저점깨짐", "숏", "청산", "도망쳐", "망함", "깡통",
    "개박살", "나락", "한강물",
    "물림", "설거지", "쌉창", "녹아내린다", "개털", "시퍼런", "그지",
]

GREED_WORDS = [
    "풀매수", "가자", "상한가", "익절", "떡상", "풀미수", "인생역전", "폭등",
    "천당", "대박", "호재", "부자", "날아가네", "홀딩", "줍줍", "펜트하우스",
    "영끌", "양봉", "빨간불", "환호", "급등", "롱", "폭발", "가즈아", "무지성",
    "투더문", "수익인증", "소고기", "숏스퀴즈", "매수타이밍", "인생픽", "상방",
    "랠리", "불장", "대세상승", "킹성전자", "갓성전자", "째려보기", "날아감",
    "전고점", "돌파", "가치투자", "상따", "야수의심장", "텐배거", "대박재료",
    "호재뉴스", "매수세", "전고돌파", "가즈앗",
    "수익률", "보너스", "돔황차", "숏충이", "꺼억", "싱글벙글", "달달하다",
]

STATUS_COLORS = {
    "극단적 공포": "#e53935",
    "공포": "#ff7043",
    "평온": "#ffb300",
    "탐욕": "#7cb342",
    "극단적 탐욕": "#2e7d32",
}

SKIP_TITLE_KEYWORDS = (
    "실시간 차트",
    "인기 급상승",
    "커뮤니티",
    "글 ",
    "개,",
    "종토방",
)


def normalize_for_match(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", "", lowered)


def combine_post_text(title: str, body: str = "") -> str:
    parts = [part.strip() for part in (title, body) if part and part.strip()]
    return " ".join(parts)


def has_sentiment_keyword(title: str, body: str = "") -> bool:
    """공포·탐욕 단어장 키워드가 제목+본문에 부분 포함(contains)됐는지 확인."""
    combined = combine_post_text(title, body)
    if not combined.strip():
        return False

    raw_text = combined.lower()
    normalized_text = normalize_for_match(combined)
    for word in FEAR_WORDS + GREED_WORDS:
        raw_word = word.lower().strip()
        normalized_word = normalize_for_match(word)
        if raw_word and raw_word in raw_text:
            return True
        if normalized_word and normalized_word in normalized_text:
            return True
    return False


def posts_to_match_texts(
    posts: list[str] | list[tuple[str, str]] | list[tuple[str, str, str]],
) -> tuple[list[str], list[str], list[str]]:
    if posts and isinstance(posts[0], tuple):
        titled_posts = posts  # type: ignore[assignment]
        if len(titled_posts[0]) >= 3:
            titles = [str(item[0]) for item in titled_posts]
            match_texts = [combine_post_text(str(item[0]), str(item[1])) for item in titled_posts]
            urls = [str(item[2]) for item in titled_posts]
            return titles, match_texts, urls

        titles = [title for title, _ in titled_posts]  # type: ignore[misc]
        match_texts = [combine_post_text(title, body) for title, body in titled_posts]  # type: ignore[misc]
        return titles, match_texts, [""] * len(titles)

    title_list = list(posts)  # type: ignore[arg-type]
    return title_list, title_list, [""] * len(title_list)


def count_word_breakdown(text: str, words: list[str]) -> dict[str, int]:
    normalized_text = normalize_for_match(text)
    hits: dict[str, int] = {}
    for word in words:
        normalized_word = normalize_for_match(word)
        if not normalized_word:
            continue
        count = normalized_text.count(normalized_word)
        if count > 0:
            hits[word] = count
    return hits


def format_keyword_breakdown(hits: dict[str, int], limit: int = 6) -> str:
    if not hits:
        return ""
    ordered = sorted(hits.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{word} {count}회" for word, count in ordered[:limit])


def calculate_sentiment_index(
    titles: list[str],
) -> tuple[int, int, int, float, bool, dict[str, int], dict[str, int]]:
    if not titles:
        return 0, 0, 0, NEUTRAL_SCORE, True, {}, {}

    combined_text = " ".join(titles)
    fear_hits = count_word_breakdown(combined_text, FEAR_WORDS)
    greed_hits = count_word_breakdown(combined_text, GREED_WORDS)
    fear_count = sum(fear_hits.values())
    greed_count = sum(greed_hits.values())
    total_hits = fear_count + greed_count

    if total_hits == 0:
        return fear_count, greed_count, total_hits, NEUTRAL_SCORE, True, {}, {}

    ratio = (greed_count - fear_count) / total_hits
    score = max(0.0, min(100.0, ((ratio + 1) / 2) * 100))
    return fear_count, greed_count, total_hits, score, False, fear_hits, greed_hits


def get_status_label(score: float, is_neutral: bool = False) -> str:
    if is_neutral:
        return NEUTRAL_STATUS
    if score <= 20:
        return "극단적 공포"
    if score <= 40:
        return "공포"
    if score <= 60:
        return "평온"
    if score <= 80:
        return "탐욕"
    return "극단적 탐욕"


def build_analysis_result(
    posts: list[str] | list[tuple[str, str]] | list[tuple[str, str, str]],
    *,
    stock_name: str,
    stock_code: str,
    source: str,
    collect_info: str,
) -> dict:
    titles, match_texts, post_urls = posts_to_match_texts(posts)
    fear_count, greed_count, total_hits, score, is_neutral, fear_hits, greed_hits = (
        calculate_sentiment_index(match_texts)
    )
    status = get_status_label(score, is_neutral=is_neutral)

    return {
        "stock_name": stock_name,
        "stock_code": stock_code,
        "source": source,
        "collect_info": collect_info,
        "titles": titles,
        "post_urls": post_urls,
        "post_count": len(titles),
        "fear_count": fear_count,
        "greed_count": greed_count,
        "fear_breakdown": format_keyword_breakdown(fear_hits),
        "greed_breakdown": format_keyword_breakdown(greed_hits),
        "total_hits": total_hits,
        "score": round(score),
        "score_raw": score,
        "status": status,
        "status_color": STATUS_COLORS[status],
        "is_neutral": is_neutral,
    }
