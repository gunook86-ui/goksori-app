"""네이버·토스 병렬 수집 속도 검증 (Selenium 없음)"""

import time
from concurrent.futures import ThreadPoolExecutor

from naver_scraper import analyze_naver_board
from toss_scraper import analyze_toss_community

if __name__ == "__main__":
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_n = pool.submit(analyze_naver_board, stock_code="005930", stock_name="삼성전자")
        f_t = pool.submit(analyze_toss_community, stock_code="005930", stock_name="삼성전자")
        naver = f_n.result()
        toss = f_t.result()
    total = time.perf_counter() - t0
    print(f"병렬 총 {total:.2f}초")
    print(f"  네이버 {naver['post_count']}개 · {naver['collect_info']}")
    print(f"  토스   {toss['post_count']}개 · {toss['collect_info']}")
