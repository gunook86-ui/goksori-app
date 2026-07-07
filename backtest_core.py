"""역발상 백테스팅 — 일별 공포 지수 추정 + 매수 타점 탐색"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from naver_price import fetch_daily_bars


@dataclass(frozen=True)
class ContrarianBacktest:
    x_dates: list[str]
    y_prices: list[int]
    buy_idx: int
    buy_date: str
    buy_price: int
    buy_fear_score: int
    current_date: str
    current_price: int
    return_pct: float
    daily_scores: list[int]


def estimate_daily_fear_scores(bars: list[dict[str, Any]]) -> list[int]:
    """
    일별 공포·탐욕 지수(0=극단적 공포, 100=극단적 탐욕) 추정.
    - 급락·낙폭 → 점수 하락(공포), 급등 → 점수 상승(탐욕)
    """
    closes = [int(bar["close"]) for bar in bars]
    changes = [float(bar["change_pct"]) for bar in bars]
    scores: list[int] = []

    for i, (close, change_pct) in enumerate(zip(closes, changes)):
        recent_high = max(closes[max(0, i - 19) : i + 1])
        drawdown_pct = (close - recent_high) / recent_high * 100 if recent_high else 0.0

        score = 50.0
        score += change_pct * 2.8
        score += drawdown_pct * 1.6

        if i >= 4:
            avg_abs_move = sum(abs(changes[j]) for j in range(i - 4, i + 1)) / 5
            if change_pct < 0 and abs(change_pct) >= avg_abs_move * 1.2:
                score -= 6

        scores.append(int(max(5, min(95, round(score)))))

    return scores


FEAR_EPISODE_LOOKBACK = 7


def _select_contrarian_buy_index(
    bars: list[dict[str, Any]],
    daily_scores: list[int],
) -> int:
    """
    최저 공포 점수(=최고 공포) 구간에서 찐바닥 매수 타점 선정.
    1) 최저 점수와 동일한 날을 모두 후보로 추출
    2) 후보가 2일 이상이면 → 종가 최저일(동률 시 더 늦은 날)
    3) 공포 구간 직전 lookback 윈도우 내 후보 중에서도 종가 최저일 재확인
    """
    min_score = min(daily_scores)
    candidates = [index for index, score in enumerate(daily_scores) if score == min_score]
    if not candidates:
        raise ValueError("매수 타점 후보를 찾지 못했습니다.")

    first_signal = min(candidates)
    last_signal = max(candidates)
    window_start = max(0, first_signal - FEAR_EPISODE_LOOKBACK)
    episode_indices = [
        index
        for index in range(window_start, last_signal + 1)
        if daily_scores[index] == min_score
    ]
    if not episode_indices:
        episode_indices = candidates

    return min(
        episode_indices,
        key=lambda index: (int(bars[index]["close"]), -index),
    )


def build_contrarian_backtest(stock_code: str, count: int = 30) -> ContrarianBacktest:
    bars = fetch_daily_bars(stock_code, count=count)
    return build_contrarian_backtest_from_bars(bars)


EPISODE_MIN_GAP_DAYS = 5


def find_top_contrarian_episodes(
    bars: list[dict[str, Any]],
    daily_scores: list[int],
    current_price: int,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """공포 지수가 가장 낮았던 역발상 타점 TOP N (근접 구간 중복 제외)."""
    count = len(bars)
    if count < 2 or current_price <= 0:
        return []

    # 마지막 거래일(=현재가 기준일)은 역사적 타점 후보에서 제외
    history_end = count - 1

    local_minima: list[int] = []
    for index in range(history_end):
        left = daily_scores[index - 1] if index > 0 else daily_scores[index] + 1
        right = daily_scores[index + 1] if index < count - 1 else daily_scores[index] + 1
        if daily_scores[index] <= left and daily_scores[index] <= right:
            local_minima.append(index)

    ranked_indices = sorted(
        local_minima or list(range(history_end)),
        key=lambda index: (daily_scores[index], -index),
    )

    picked: list[int] = []
    for index in ranked_indices:
        if any(abs(index - chosen) < EPISODE_MIN_GAP_DAYS for chosen in picked):
            continue
        picked.append(index)
        if len(picked) >= limit:
            break

    if len(picked) < limit:
        for index in sorted(range(history_end), key=lambda idx: (daily_scores[idx], -idx)):
            if index in picked:
                continue
            if any(abs(index - chosen) < EPISODE_MIN_GAP_DAYS for chosen in picked):
                continue
            picked.append(index)
            if len(picked) >= limit:
                break

    episodes: list[dict[str, Any]] = []
    for index in picked[:limit]:
        buy_price = int(bars[index]["close"])
        if buy_price <= 0:
            continue
        return_pct = round((current_price - buy_price) / buy_price * 100, 1)
        episodes.append(
            {
                "rank": 0,
                "buy_date": str(bars[index]["date"]),
                "buy_price": buy_price,
                "buy_fear_score": int(daily_scores[index]),
                "return_pct": return_pct,
            }
        )

    episodes.sort(
        key=lambda item: (item["buy_fear_score"], -item["return_pct"], item["buy_date"])
    )
    for rank, item in enumerate(episodes[:limit], 1):
        item["rank"] = rank
    return episodes[:limit]


def build_contrarian_backtest_from_bars(bars: list[dict[str, Any]]) -> ContrarianBacktest:
    if len(bars) < 2:
        raise ValueError("백테스트에 필요한 일별 시세가 부족합니다.")

    daily_scores = estimate_daily_fear_scores(bars)
    buy_idx = _select_contrarian_buy_index(bars, daily_scores)

    buy_bar = bars[buy_idx]
    current_bar = bars[-1]
    buy_price = int(buy_bar["close"])
    current_price = int(current_bar["close"])
    return_pct = (current_price - buy_price) / buy_price * 100

    return ContrarianBacktest(
        x_dates=[bar["date"][5:].replace("-", "/") for bar in bars],
        y_prices=[int(bar["close"]) for bar in bars],
        buy_idx=buy_idx,
        buy_date=str(buy_bar["date"]),
        buy_price=buy_price,
        buy_fear_score=int(daily_scores[buy_idx]),
        current_date=str(current_bar["date"]),
        current_price=current_price,
        return_pct=round(return_pct, 1),
        daily_scores=daily_scores,
    )
