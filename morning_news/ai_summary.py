"""無料公開のリード（meta/og:description）を取得して補足する。"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from typing import Protocol
from urllib.parse import urlparse

import requests

AI_SUMMARY_MAX_CHARS = 180
HTTP_TIMEOUT_SEC = 8
MAX_WORKERS = 8
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class SummarizableItem(Protocol):
    source_name: str
    category: str
    title: str
    summary: str
    link: str
    ai_summary: str


def needs_ai_summary(item: SummarizableItem) -> bool:
    """RSS要約が薄い／無い記事だけ無料リード取得する。"""
    return len((item.summary or "").strip()) < 40


def _strip_html(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def _truncate(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" 。．")
    if text and not text.endswith(("。", "！", "？", "…")):
        text += "。"
    if len(text) > AI_SUMMARY_MAX_CHARS:
        return text[: AI_SUMMARY_MAX_CHARS - 1].rstrip() + "…"
    return text


def _extract_head(html: str) -> str:
    """巨大HTMLでも高速にするため <head> 付近だけ見る。"""
    lower = html.lower()
    start = lower.find("<head")
    end = lower.find("</head>")
    if start != -1 and end != -1 and end > start:
        return html[start : end + 7]
    # head が取れない場合は先頭だけ
    return html[:120_000]


def _meta_content(html: str, *, name: str | None = None, prop: str | None = None) -> str:
    head = _extract_head(html)
    if name:
        key = "name"
        value = name
    else:
        assert prop is not None
        key = "property"
        value = prop

    # content の前後どちらでも取れるよう、属性順を両方見る（head内のみ）
    patterns = [
        rf'<meta\b[^>]*\b{key}=["\']{re.escape(value)}["\'][^>]*\bcontent=["\']([^"\']+)["\']',
        rf'<meta\b[^>]*\bcontent=["\']([^"\']+)["\'][^>]*\b{key}=["\']{re.escape(value)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, head, flags=re.I)
        if match:
            return _strip_html(match.group(1))
    return ""


def _is_useful_lead(title: str, lead: str) -> bool:
    if not lead or len(lead) < 28:
        return False
    compact_title = re.sub(r"[\s　]+", "", title)
    compact_lead = re.sub(r"[\s　]+", "", lead)
    if not compact_lead:
        return False
    if compact_lead == compact_title:
        return False
    if compact_title and compact_title in compact_lead and len(compact_lead) <= len(compact_title) + 18:
        return False
    return True


def fetch_free_lead(
    url: str,
    *,
    title: str = "",
    session: requests.Session | None = None,
) -> str:
    """公式ページの無料公開リード（description / og:description）を取得する。"""
    if not url or not url.startswith("http"):
        return ""
    host = urlparse(url).netloc.lower()
    if "news.google.com" in host:
        return ""

    sess = session or requests.Session()
    response = sess.get(
        url,
        timeout=HTTP_TIMEOUT_SEC,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en;q=0.8",
        },
        allow_redirects=True,
    )
    if response.status_code >= 400:
        return ""

    html = response.text
    candidates = [
        _meta_content(html, prop="og:description"),
        _meta_content(html, name="description"),
        _meta_content(html, name="twitter:description"),
    ]
    for lead in candidates:
        if _is_useful_lead(title, lead):
            return _truncate(lead)
    return ""


def _fetch_one(item: SummarizableItem) -> tuple[SummarizableItem, str, str]:
    try:
        lead = fetch_free_lead(item.link, title=item.title)
        return item, lead, ""
    except Exception as exc:  # noqa: BLE001
        return item, "", str(exc)


def enrich_with_ai_summaries(
    items: list[SummarizableItem],
    *,
    enabled: bool = True,
    session: requests.Session | None = None,
) -> list[str]:
    """薄い記事へ、無料公開リードを取得して補足する。"""
    del session  # 並列取得では各ワーカーが個別セッションを使う
    warnings: list[str] = []
    if not enabled:
        return warnings

    targets = [item for item in items if needs_ai_summary(item)]
    if not targets:
        return warnings

    filled = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_fetch_one, item) for item in targets]
        for future in as_completed(futures):
            item, lead, error = future.result()
            if lead:
                item.ai_summary = lead
                filled += 1
            else:
                failed += 1
                if error:
                    warnings.append(f"lead_fetch:{item.source_name}: {error}")

    warnings.append(f"ai_summary: 無料リード取得 {filled}/{len(targets)} 件（失敗 {failed}）")
    return warnings
