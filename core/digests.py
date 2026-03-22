from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

from core.blogs import DEFAULT_SITES, Post, discover_recent_posts
from core.news import NewsItem, discover_recent_news


UTC = timezone.utc


@dataclass(frozen=True)
class DomainDigest:
    domain: str
    title: str
    body: str
    has_content: bool


def build_daily_digests(
    *, now: datetime | None = None, timezone_name: str = "Asia/Shanghai"
) -> list[DomainDigest]:
    local_tz = ZoneInfo(timezone_name)
    local_now = now.astimezone(local_tz) if now else datetime.now(tz=local_tz)

    return [
        build_tech_digest(local_now),
        build_news_digest(local_now),
        DomainDigest(
            domain="market",
            title=f"市场简报 | {local_now:%Y-%m-%d %H:%M}",
            body="",
            has_content=False,
        ),
    ]


def build_tech_digest(local_now: datetime) -> DomainDigest:
    posts_24h = discover_recent_posts(
        window_days=1,
        sites=DEFAULT_SITES,
        now=local_now.astimezone(UTC),
    )
    if posts_24h:
        body = format_post_lines(
            posts=posts_24h,
            heading=f"最近 24h 共 {len(posts_24h)} 篇更新：",
            local_now=local_now,
        )
        has_content = True
    else:
        body = ""
        has_content = False

    return DomainDigest(
        domain="tech",
        title=f"技术简报 | {local_now:%Y-%m-%d %H:%M}",
        body=body,
        has_content=has_content,
    )


def build_news_digest(local_now: datetime) -> DomainDigest:
    grouped = discover_recent_news(hours=24, now=local_now.astimezone(UTC))
    sections: list[str] = []
    total = 0
    for topic in ["finance", "politics", "military", "technology"]:
        items = grouped.get(topic, [])
        if not items:
            continue
        total += len(items)
        sections.append(format_news_section(topic=topic, items=items[:5], local_now=local_now))

    return DomainDigest(
        domain="news",
        title=f"新闻简报 | {local_now:%Y-%m-%d %H:%M}",
        body="\n\n".join(sections) if sections else "",
        has_content=total > 0,
    )


def format_post_lines(*, posts: list[Post], heading: str, local_now: datetime) -> str:
    lines = [heading]
    for post in posts:
        source = normalize_source_name(post.site)
        published_local = datetime.fromisoformat(post.published_at).astimezone(
            local_now.tzinfo or UTC
        )
        lines.append(
            f"- [{escape(source)}] {published_local:%m-%d %H:%M} "
            f"<a href=\"{escape(post.url, quote=True)}\">{escape(post.title)}</a>"
        )
    return "\n".join(lines)


def format_news_section(*, topic: str, items: list[NewsItem], local_now: datetime) -> str:
    topic_name = {
        "finance": "财经",
        "politics": "政治",
        "military": "军事",
        "technology": "科技",
    }.get(topic, topic)
    lines = [f"{topic_name} | 最近 24h {len(items)} 条："]
    for item in items:
        published_local = datetime.fromisoformat(item.published_at).astimezone(
            local_now.tzinfo or UTC
        )
        source = f" | {item.source}" if item.source else ""
        lines.append(
            f"- {published_local:%m-%d %H:%M}{escape(source)} "
            f"<a href=\"{escape(item.url, quote=True)}\">{escape(item.title)}</a>"
        )
    return "\n".join(lines)


def normalize_source_name(site: str) -> str:
    if "langchain" in site:
        return "LangChain"
    if "karpathy" in site:
        return "Karpathy"
    if "baoyu" in site:
        return "宝玉"
    return site
