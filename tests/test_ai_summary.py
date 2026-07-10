from unittest.mock import MagicMock

from morning_news.ai_summary import (
    enrich_with_ai_summaries,
    fetch_free_lead,
    needs_ai_summary,
)
from morning_news.digest import NewsItem, display_summary


SAMPLE_HTML = """
<html><head>
<meta name="description" content="北海道の漁港でサンマが高値となり、店頭では1匹8万円超で売られた。">
<meta property="og:description" content="北海道の漁港でサンマが高値となり、店頭では1匹8万円超で売られた。">
</head><body></body></html>
"""


def test_needs_ai_summary_for_thin_or_empty():
    thin = NewsItem("a", "A", "nikkei", 1, "t", "https://x", summary="short")
    rich = NewsItem(
        "b",
        "B",
        "nikkei",
        1,
        "t",
        "https://x",
        summary="This RSS summary is long enough to skip free-lead enrichment for the article.",
    )
    assert needs_ai_summary(thin) is True
    assert needs_ai_summary(rich) is False


def test_display_summary_prefers_fetched_lead():
    item = NewsItem(
        "a",
        "A",
        "nikkei",
        1,
        "見出し",
        "https://x",
        summary="RSS要約",
        ai_summary="無料リードから取った補足です。",
    )
    body, label = display_summary(item)
    assert label == "補足"
    assert "無料リード" in body


def test_fetch_free_lead_reads_og_description():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.text = SAMPLE_HTML
    response.url = "https://example.com/a"
    session.get.return_value = response

    lead = fetch_free_lead(
        "https://example.com/a",
        title="サンマが高値",
        session=session,
    )
    assert "8万円" in lead
    assert "サンマ" in lead


def test_fetch_free_lead_rejects_title_only():
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.text = (
        '<meta property="og:description" content="サンマが高値">'
    )
    session.get.return_value = response
    lead = fetch_free_lead(
        "https://example.com/a",
        title="サンマが高値",
        session=session,
    )
    assert lead == ""


def test_enrich_with_free_leads(monkeypatch):
    items = [
        NewsItem("a", "Yahoo", "economy", 1, "title-a", "https://x", summary=""),
        NewsItem(
            "b",
            "B",
            "economy",
            1,
            "title-b",
            "https://y",
            summary="This RSS summary is long enough to skip free-lead enrichment for the article.",
        ),
    ]

    def fake_fetch(url, *, title="", session=None):
        if url.endswith("x"):
            return "取得した無料リード。店頭価格が急騰した。"
        return ""

    monkeypatch.setattr("morning_news.ai_summary.fetch_free_lead", fake_fetch)
    warnings = enrich_with_ai_summaries(items, enabled=True)
    assert "無料リード" in items[0].ai_summary
    assert items[1].ai_summary == ""
    assert any("無料リード取得" in w for w in warnings)
