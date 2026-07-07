"""Streamlit Cloud 배포 전 — 필수 모듈 import 검사."""

from __future__ import annotations

import importlib
import sys

REQUIRED_MODULES = (
    "app",
    "member_auth",
    "stock_votes",
    "vote_settlement",
    "member_profile",
    "accuracy_badge",
    "cpr_room",
    "stock_config",
    "naver_scraper",
    "toss_scraper",
    "backtest_core",
    "naver_price",
    "toss_price",
    "sentiment_core",
    "http_client",
)

REQUIRED_FILES = tuple(f"{name}.py" for name in REQUIRED_MODULES if name != "app")


def main() -> int:
    failed: list[str] = []
    for name in REQUIRED_MODULES:
        try:
            if name in sys.modules:
                sys.modules.pop(name, None)
            importlib.import_module(name)
            print(f"OK  {name}")
        except Exception as exc:
            print(f"FAIL {name}: {exc}")
            failed.append(name)
    if failed:
        print("\n누락/오류 모듈:", ", ".join(failed))
        print("GitHub(goksori-app) 저장소에 위 .py 파일을 모두 업로드한 뒤 재배포하세요.")
        return 1
    print("\n배포 검사 통과 — Streamlit Cloud에 올릴 준비가 되었습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
