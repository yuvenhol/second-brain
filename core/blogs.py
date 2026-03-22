from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


UTC = timezone.utc


@dataclass
class Post:
    site: str
    title: str
    url: str
    published_at: str


DEFAULT_SITES = [
    "https://blog.langchain.com",
    "https://karpathy.bearblog.dev/blog/",
    "https://baoyu.io",
]

FEED_URLS = {
    "https://blog.langchain.com": "https://blog.langchain.com/rss/",
    "https://karpathy.bearblog.dev/blog/": "https://karpathy.bearblog.dev/feed/?type=rss",
    "https://baoyu.io": "https://baoyu.io/feed.xml",
}


def parse_window_days(value: str) -> int:
    match = re.fullmatch(r"(\d+)d", value.strip())
    if not match:
        raise argparse.ArgumentTypeError("window must be in Nd format, e.g. 7d")
    days = int(match.group(1))
    if days <= 0:
        raise argparse.ArgumentTypeError("window must be positive")
    return days


def normalize_datetime(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in ("%B %d, %Y", "%d %b, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"unsupported date format: {raw}")


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


def parse_feed(site: str, xml_text: str) -> list[Post]:
    root = ET.fromstring(xml_text)
    items = root.findall("./channel/item")
    posts: list[Post] = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title or not link or not pub_date:
            continue
        published = parsedate_to_datetime(pub_date).astimezone(UTC).isoformat()
        posts.append(Post(site=site, title=title, url=link, published_at=published))
    return dedupe_posts(posts)


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if href:
            self._href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = "".join(self._text_parts).strip()
            self.anchors.append((self._href, text))
            self._href = None
            self._text_parts = []


def parse_langchain(site: str, html: str) -> list[Post]:
    pattern = re.compile(
        r'href="(?P<href>/[^"#]+)"[^>]*>.*?<h2[^>]*>(?P<title>.*?)</h2>.*?'
        r'<time[^>]*datetime="(?P<dt>\d{4}-\d{2}-\d{2})',
        re.DOTALL,
    )
    posts: list[Post] = []
    for match in pattern.finditer(html):
        title = strip_tags(match.group("title"))
        href = urljoin(site, match.group("href"))
        published = normalize_datetime(match.group("dt")).isoformat()
        posts.append(Post(site=site, title=title, url=href, published_at=published))
    return dedupe_posts(posts)


def parse_karpathy(site: str, html: str) -> list[Post]:
    pattern = re.compile(
        r"\*\s+(?P<date>\d{2}\s+\w{3},\s+\d{4})\s+"
        r"<a\s+href=\"(?P<href>[^\"]+)\">(?P<title>.*?)</a>",
        re.DOTALL,
    )
    posts: list[Post] = []
    for match in pattern.finditer(html):
        title = strip_tags(match.group("title"))
        href = match.group("href")
        published = normalize_datetime(match.group("date")).isoformat()
        posts.append(
            Post(
                site=site,
                title=title,
                url=urljoin(site, href),
                published_at=published,
            )
        )
    return dedupe_posts(posts)


def parse_baoyu(site: str, html: str) -> list[Post]:
    pattern = re.compile(
        r"<h2>\s*(?P<title>.*?)\s*</h2>.*?"
        r"(?P<date>[A-Z][a-z]+ \d{1,2}, \d{4}).*?"
        r'href="(?P<href>[^"]+)">View Article',
        re.DOTALL,
    )
    posts: list[Post] = []
    for match in pattern.finditer(html):
        title = strip_tags(match.group("title"))
        published = normalize_datetime(match.group("date")).isoformat()
        posts.append(
            Post(
                site=site,
                title=title,
                url=urljoin(site, match.group("href")),
                published_at=published,
            )
        )
    return dedupe_posts(posts)


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def dedupe_posts(posts: Iterable[Post]) -> list[Post]:
    seen: set[str] = set()
    result: list[Post] = []
    for post in posts:
        if post.url in seen:
            continue
        seen.add(post.url)
        result.append(post)
    return result


def parse_site(site: str, html: str) -> list[Post]:
    netloc = urlparse(site).netloc
    if "blog.langchain.com" in netloc:
        return parse_langchain(site, html)
    if "karpathy.bearblog.dev" in netloc:
        return parse_karpathy(site, html)
    if "baoyu.io" in netloc:
        return parse_baoyu(site, html)
    raise ValueError(f"unsupported site: {site}")


def filter_posts(posts: Iterable[Post], days: int, now: datetime) -> list[Post]:
    threshold = now - timedelta(days=days)
    result = [
        post
        for post in posts
        if datetime.fromisoformat(post.published_at) >= threshold
    ]
    return sorted(result, key=lambda post: post.published_at, reverse=True)


def discover_recent_posts(
    *,
    window_days: int,
    sites: list[str] | None = None,
    now: datetime | None = None,
) -> list[Post]:
    current_time = now.astimezone(UTC) if now else datetime.now(tz=UTC)
    results: list[Post] = []
    for site in sites or DEFAULT_SITES:
        feed_url = FEED_URLS.get(site)
        if feed_url:
            feed_text = fetch_text(feed_url)
            posts = parse_feed(site, feed_text)
        else:
            html = fetch_text(site)
            posts = parse_site(site, html)
        results.extend(filter_posts(posts, window_days, current_time))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=parse_window_days, default=7)
    parser.add_argument("--site", action="append", dest="sites")
    parser.add_argument("--site-file")
    parser.add_argument("--now", help="override current time in ISO 8601")
    args = parser.parse_args()

    if isinstance(args.window, int):
        window_days = args.window
    else:
        window_days = int(args.window)

    now = (
        datetime.fromisoformat(args.now).astimezone(UTC)
        if args.now
        else datetime.now(tz=UTC)
    )

    results = discover_recent_posts(
        window_days=window_days,
        sites=args.sites or DEFAULT_SITES,
        now=now,
    )

    print(json.dumps([asdict(post) for post in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
