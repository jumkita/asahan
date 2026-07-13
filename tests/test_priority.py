from morning_news.digest import NewsItem
from morning_news.priority import attach_priorities, curated_items, score_item


def test_score_item_marks_macro_news_as_a():
    item = NewsItem(
        "nikkei_gnews",
        "日経",
        "nikkei",
        100,
        "イラン革命防衛隊、ホルムズ再封鎖を宣言",
        "https://example.com/1",
        "原油輸送への影響が懸念される",
    )
    result = score_item(item)
    assert result.level == "A"
    assert "ホルムズ" in result.reason or "原油" in result.reason


def test_score_item_marks_sports_as_c():
    item = NewsItem(
        "yahoo_top",
        "Yahoo",
        "general",
        40,
        "サッカーワールドカップでイングランドが4強",
        "https://example.com/2",
        "延長戦の末に勝利した",
    )
    result = score_item(item)
    assert result.level == "C"


def test_curated_items_prefers_a_and_b():
    items = [
        NewsItem("a", "A", "general", 40, "サッカーW杯速報", "https://ex.com/a", ""),
        NewsItem("b", "B", "economy", 90, "日銀の金利見通しとドル円", "https://ex.com/b", ""),
        NewsItem("c", "C", "economy", 80, "同一労働同一賃金の法改正", "https://ex.com/c", ""),
        NewsItem("d", "D", "general", 50, "映画の新作情報", "https://ex.com/d", ""),
    ]
    attach_priorities(items)
    picks = curated_items(items, limit=3)
    assert len(picks) == 3
    assert picks[0].priority in {"A", "B"}
    assert all(p.priority != "C" or p.title.startswith("映画") is False for p in picks[:2])
