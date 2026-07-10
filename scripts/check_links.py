from morning_news.digest import fetch_source, load_sources, normalize_link
import requests

srcs = {s.id: s for s in load_sources()}
r = fetch_source(srcs["nikkei_gnews"])
print("nikkei items", len(r.items))
for i in r.items[:3]:
    print("TITLE", i.title)
    print("LINK ", i.link)
    print("SUM  ", (i.summary or "")[:120])
    print("NORM ", normalize_link(i.link))
    try:
        resp = requests.get(
            i.link,
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        print("FINAL", resp.url[:160], "status", resp.status_code)
    except Exception as e:
        print("ERR", e)
    print("---")

for sid in ["yahoo_business", "nhk_economy", "nikkei_biz", "mainichi_flash"]:
    r = fetch_source(srcs[sid])
    i = r.items[0]
    print(sid, "title=", i.title[:50])
    print(" link=", i.link)
    print(" sum=", (i.summary or "")[:120])
    print("---")
