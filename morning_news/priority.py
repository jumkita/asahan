"""ストラテジスト視点の重要度（A/B/C）付与。

推測はせず、見出し・要約テキストに含まれる語彙で機械的に判定する。
目的は「全部読む」ではなく「今日の必読だけ先に見る」時短。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PrioritizableItem(Protocol):
    title: str
    summary: str
    ai_summary: str
    source_name: str
    category: str
    weight: int
    priority: str
    priority_reason: str
    priority_score: int


PRIORITY_A = "A"
PRIORITY_B = "B"
PRIORITY_C = "C"

PRIORITY_LABEL = {
    PRIORITY_A: "必読",
    PRIORITY_B: "確認推奨",
    PRIORITY_C: "後回し可",
}

# ビジネス意思決定・マクロ・規制・プラットフォームに直結しやすい語
HIGH_KEYWORDS = (
    "金利",
    "日銀",
    "FRB",
    "為替",
    "ドル円",
    "円安",
    "円高",
    "原油",
    "WTI",
    "ホルムズ",
    "制裁",
    "関税",
    "インフレ",
    "景気",
    "GDP",
    "半導体",
    "メモリー",
    "AI",
    "Amazon",
    "アマゾン",
    "EC",
    "プラットフォーム",
    "自動車",
    "トヨタ",
    "ホンダ",
    "サプライチェーン",
    "供給網",
    "同一労働同一賃金",
    "労働",
    "規制",
    "法改正",
    "セキュリティ",
    "サイバー",
    "株価",
    "日経平均",
    "上場",
    "M&A",
    "倒産",
    "赤字",
    "増税",
    "減税",
)

# 押さえるとよいが、今日中に必須とは限らない語
MEDIUM_KEYWORDS = (
    "企業統治",
    "取締役",
    "人事",
    "採用",
    "賃金",
    "賃上げ",
    "消費",
    "小売",
    "物流",
    "スタートアップ",
    "IPO",
    "DX",
    "生成AI",
    "ロボ",
    "エネルギー",
    "電力",
    "不動産",
    "住宅",
    "地方創生",
    "観光",
)

# 娯楽・スポーツ・雑報寄り（網羅確認には残すが厳選からは外しやすい）
LOW_KEYWORDS = (
    "サッカー",
    "ワールドカップ",
    "W杯",
    "野球",
    "大谷",
    "芸能",
    "エンタメ",
    "映画",
    "アニメ",
    "グルメ",
    "レシピ",
    "天気",
    "気温",
    "五輪",
)


@dataclass(frozen=True)
class PriorityResult:
    level: str
    reason: str
    score: int


def _haystack(item: PrioritizableItem) -> str:
    return f"{item.title} {item.summary} {item.ai_summary} {item.source_name} {item.category}"


def score_item(item: PrioritizableItem) -> PriorityResult:
    text = _haystack(item)
    high_hits = [kw for kw in HIGH_KEYWORDS if kw in text]
    medium_hits = [kw for kw in MEDIUM_KEYWORDS if kw in text]
    low_hits = [kw for kw in LOW_KEYWORDS if kw in text]

    score = 0
    score += 30 * len(high_hits)
    score += 12 * len(medium_hits)
    score -= 20 * len(low_hits)
    if item.category in {"nikkei", "economy"}:
        score += 8
    if item.weight >= 80:
        score += 5

    if low_hits and not high_hits and score < 20:
        return PriorityResult(
            level=PRIORITY_C,
            reason=f"娯楽・雑報寄り（例: {low_hits[0]}）",
            score=score,
        )
    if high_hits or score >= 30:
        reason_kw = high_hits[0] if high_hits else "経済・規制・市場関連"
        return PriorityResult(
            level=PRIORITY_A,
            reason=f"意思決定に直結しやすい論点（{reason_kw}）",
            score=score,
        )
    if medium_hits or score >= 12:
        reason_kw = medium_hits[0] if medium_hits else "事業環境の変化"
        return PriorityResult(
            level=PRIORITY_B,
            reason=f"押さえると時短になる論点（{reason_kw}）",
            score=score,
        )
    return PriorityResult(
        level=PRIORITY_C,
        reason="網羅確認向け（本日の必読優先度は低め）",
        score=score,
    )


def attach_priorities(items: list[PrioritizableItem]) -> list[PrioritizableItem]:
    for item in items:
        result = score_item(item)
        item.priority = result.level
        item.priority_reason = result.reason
        item.priority_score = result.score
    return items


def curated_items(items: list[PrioritizableItem], *, limit: int = 10) -> list[PrioritizableItem]:
    ranked = sorted(
        items,
        key=lambda item: (
            {"A": 0, "B": 1, "C": 2}.get(item.priority, 2),
            -int(item.priority_score or 0),
            -int(item.weight),
        ),
    )
    selected = [item for item in ranked if item.priority in {PRIORITY_A, PRIORITY_B}]
    if len(selected) < min(5, limit):
        selected = ranked[:limit]
    return selected[:limit]
