import json
from pathlib import Path

from morning_news.ai_summary import needs_ai_summary
from morning_news.digest import collect_news

result = collect_news()
thin = []
for index, item in enumerate(result.items):
    if needs_ai_summary(item):
        thin.append(
            {
                "index": index,
                "source": item.source_name,
                "category": item.category,
                "title": item.title,
                "summary": item.summary,
                "link": item.link,
            }
        )

out = Path("data/thin_items.json")
out.write_text(json.dumps(thin, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"total={len(result.items)} thin={len(thin)} wrote={out}")
for row in thin[:10]:
    print(f"- [{row['category']}] {row['title'][:70]}")
