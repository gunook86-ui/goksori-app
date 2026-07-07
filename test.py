"""네이버 증권 토론방 공포·탐욕 인간지표 (터미널 버전)"""

import sys

import requests

from naver_scraper import analyze_naver_board
from sentiment_core import POST_LIMIT

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    print(f"\n네이버 증권 토론방 {POST_LIMIT}개를 불러오는 중...")

    try:
        data = analyze_naver_board()
    except requests.RequestException as error:
        print(f"\n오류: {error}")
        sys.exit(1)

    titles = data["titles"]
    print(f"\n{'=' * 55}")
    print(f"  {data['stock_name']}({data['stock_code']}) · {data['source']}")
    print(f"{'=' * 55}")

    if not titles:
        print("  (가져온 글이 없습니다.)")
        sys.exit(1)

    for index, title in enumerate(titles, start=1):
        print(f"  {index:3d}. {title}")

    print(f"\n{'─' * 55}")
    print(f"  공포 {data['fear_count']}회 / 탐욕 {data['greed_count']}회")
    print(f"  (키워드 {data['total_hits']}회 · 글 {data['post_count']}개 · {data['collect_info']})")
    if data["is_neutral"]:
        print("  ※ 키워드 없음 → 50점(평온) 고정")
    print(f"{'─' * 55}")
    print(
        f"\n📊 [{data['stock_name']}] 실시간 인간지표: {data['score']}점 "
        f"(현재 상태: {data['status']})\n"
    )


if __name__ == "__main__":
    main()
