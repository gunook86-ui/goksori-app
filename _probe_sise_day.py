import re
from http_client import get_http_session
from naver_price import _fetch_from_mobile_api

code = "005930"
s = get_http_session()
r = s.get(
    f"https://finance.naver.com/item/sise_day.naver?code={code}&page=1",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=8,
)
text = r.text

# Each row: date + close + change + open + high + low + volume
pattern = re.compile(
    r'<span class="tah p10">(\d{4}\.\d{2}\.\d{2})</span>.*?'
    r'<span class="tah p11[^"]*">([\d,]+)</span>',
    re.S,
)
rows = pattern.findall(text)
print("sise_day (date, first_price_after_date):", rows[:8])

mobile = _fetch_from_mobile_api(code, 8)
print("mobile (date, close):")
for b in mobile:
    print(" ", b["date"][:10], b["close"])

# Also try api.stock chart with start/end range
h = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
for start, end in [("20260501", "20260706"), ("20250601", "20250706")]:
    r = s.get(
        f"https://api.stock.naver.com/chart/domestic/item/{code}/day",
        params={
            "includeOverMarketClose": "true",
            "startDateTime": start,
            "endDateTime": end,
        },
        headers=h,
        timeout=8,
    )
    data = r.json() if r.status_code == 200 else []
    print(f"chart {start}-{end} len={len(data) if isinstance(data, list) else r.status_code}")
    if isinstance(data, list) and len(data) > 1:
        print(" sample", data[0], data[1])
