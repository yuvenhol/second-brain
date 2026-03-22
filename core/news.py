from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


UTC = timezone.utc


@dataclass(frozen=True)
class NewsItem:
    topic: str
    source: str
    title: str
    url: str
    published_at: str


TOPIC_FEEDS = {
    "finance": [
        "https://news.google.com/rss/search?q=finance%20OR%20economy%20OR%20markets&hl=en-US&gl=US&ceid=US:en",
    ],
    "politics": [
        "https://rss.politico.com/politics-news.xml",
    ],
    "military": [
        "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10",
        "https://www.defensenews.com/arc/outboundfeeds/rss/category/pentagon/?outputType=xml",
        "https://www.defensenews.com/arc/outboundfeeds/rss/category/global/?outputType=xml",
    ],
    "technology": [
        "https://techcrunch.com/feed/",
        "https://news.google.com/rss/search?q=artificial%20intelligence%20OR%20semiconductor%20OR%20big%20tech&hl=en-US&gl=US&ceid=US:en",
    ],
}


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_feed(topic: str, xml_text: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    channel_items = root.findall("./channel/item")
    atom_entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    items: list[NewsItem] = []

    if channel_items:
        for item in channel_items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            if not title or not link or not pub_date:
                continue
            source, clean_title = split_source_from_title(title)
            published = parsedate_to_datetime(pub_date).astimezone(UTC).isoformat()
            items.append(
                NewsItem(
                    topic=topic,
                    source=source,
                    title=clean_title,
                    url=link,
                    published_at=published,
                )
            )
    else:
        for entry in atom_entries:
            title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link_node = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.attrib.get("href", "").strip() if link_node is not None else ""
            updated = (
                entry.findtext("{http://www.w3.org/2005/Atom}updated")
                or entry.findtext("{http://www.w3.org/2005/Atom}published")
                or ""
            ).strip()
            if not title or not link or not updated:
                continue
            published = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(
                UTC
            ).isoformat()
            items.append(
                NewsItem(
                    topic=topic,
                    source="",
                    title=title,
                    url=link,
                    published_at=published,
                )
            )

    return dedupe_items(items)


def split_source_from_title(title: str) -> tuple[str, str]:
    if " - " in title:
        left, right = title.rsplit(" - ", 1)
        if left.strip() and right.strip():
            return right.strip(), left.strip()
    return "", title.strip()


def dedupe_items(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    result: list[NewsItem] = []
    for item in items:
        key = item.url or f"{item.topic}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def filter_items(
    items: Iterable[NewsItem], *, hours: int, now: datetime | None = None
) -> list[NewsItem]:
    current_time = now.astimezone(UTC) if now else datetime.now(tz=UTC)
    threshold = current_time - timedelta(hours=hours)
    result = [
        item for item in items if datetime.fromisoformat(item.published_at) >= threshold
    ]
    return sorted(result, key=lambda item: item.published_at, reverse=True)


def discover_recent_news(
    *, hours: int = 24, now: datetime | None = None
) -> dict[str, list[NewsItem]]:
    results: dict[str, list[NewsItem]] = {}
    current_time = now.astimezone(UTC) if now else datetime.now(tz=UTC)
    for topic, feed_urls in TOPIC_FEEDS.items():
        topic_items: list[NewsItem] = []
        for feed_url in feed_urls:
            try:
                xml_text = fetch_text(feed_url)
                topic_items.extend(parse_feed(topic, xml_text))
            except Exception:
                continue
        results[topic] = filter_items(dedupe_items(topic_items), hours=hours, now=current_time)
    return results


def main() -> None:
    results = discover_recent_news(hours=24)
    print(
        json.dumps(
            {
                topic: [asdict(item) for item in items]
                for topic, items in results.items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
