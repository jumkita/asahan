import re
from html import unescape

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

URLS = [
    "https://news.yahoo.co.jp/pickup/6587316",
    "https://mainichi.jp/articles/20260710/k00/00m/020/017000c",
    "https://www.nikkei.com/article/DGXZQOUB297UO0Z20C26A6000000/",
    "https://business.nikkei.com/atcl/gen/19/00081/052600949/",
]


def meta_content(html: str, *, name: str | None = None, prop: str | None = None) -> str:
    if name:
        patterns = [
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
    else:
        assert prop is not None
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{re.escape(prop)}["\']',
        ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I | re.S)
        if match:
            return unescape(match.group(1)).strip()
    return ""


for url in URLS:
    response = requests.get(url, timeout=20, headers=HEADERS, allow_redirects=True)
    html = response.text
    print("URL", url)
    print(" status", response.status_code, "final", response.url[:100])
    print(" desc", meta_content(html, name="description")[:180])
    print(" og  ", meta_content(html, prop="og:description")[:180])
    print("---")
