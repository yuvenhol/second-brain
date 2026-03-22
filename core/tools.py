from __future__ import annotations

import json
from dataclasses import asdict

from langchain_core.tools import tool

from core.blogs import (
    DEFAULT_SITES,
    discover_recent_posts,
    parse_window_days,
)


@tool
def fetch_recent_blog_posts(window: str = "7d", sites_csv: str = "") -> str:
    """Fetch recent blog posts from tracked sources.

    Use this when the user asks for recently updated technical blog posts.
    The window must use the Nd format, for example 7d or 30d.
    sites_csv is optional and should be a comma-separated list of site URLs.
    """

    window_days = parse_window_days(window)
    sites = [site.strip() for site in sites_csv.split(",") if site.strip()] or DEFAULT_SITES
    posts = discover_recent_posts(window_days=window_days, sites=sites)
    return json.dumps([asdict(post) for post in posts], ensure_ascii=False, indent=2)
