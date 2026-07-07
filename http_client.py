"""공통 HTTP 세션 (연결 재사용으로 API 연속 호출 가속)"""

from __future__ import annotations

import requests

from stock_config import USER_AGENT

_SESSION: requests.Session | None = None


def get_http_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        _SESSION = session
    return _SESSION
