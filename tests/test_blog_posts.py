import unittest
from datetime import datetime, timezone

from core.blogs import filter_posts, parse_site


UTC = timezone.utc


class DiscoverRecentPostsTest(unittest.TestCase):
    def test_parse_karpathy_recent_window(self) -> None:
        html = """
        <html><body>
        * 19 Dec, 2025  <a href="/2025-review/">2025 LLM Year in Review</a>
        * 10 Dec, 2025  <a href="/older/">Older Post</a>
        </body></html>
        """
        posts = parse_site("https://karpathy.bearblog.dev/blog/", html)
        recent = filter_posts(posts, 7, datetime(2025, 12, 20, tzinfo=UTC))
        self.assertEqual([post.title for post in recent], ["2025 LLM Year in Review"])

    def test_parse_baoyu_recent_window(self) -> None:
        html = """
        <html><body>
        <h2>AI 发展太快跟不上？一张四象限图帮你做减法</h2>
        <p>March 20, 2026</p>
        <a href="/blog/latest">View Article</a>
        <h2>更早的文章</h2>
        <p>March 1, 2026</p>
        <a href="/blog/older">View Article</a>
        </body></html>
        """
        posts = parse_site("https://baoyu.io", html)
        recent = filter_posts(posts, 7, datetime(2026, 3, 21, tzinfo=UTC))
        self.assertEqual([post.title for post in recent], ["AI 发展太快跟不上？一张四象限图帮你做减法"])

    def test_parse_langchain_recent_window(self) -> None:
        html = """
        <html><body>
        <a href="/latest-post/">
          <h2>Latest LangChain Post</h2>
          <time datetime="2026-03-19"></time>
        </a>
        <a href="/older-post/">
          <h2>Older LangChain Post</h2>
          <time datetime="2026-02-20"></time>
        </a>
        </body></html>
        """
        posts = parse_site("https://blog.langchain.com", html)
        recent = filter_posts(posts, 7, datetime(2026, 3, 21, tzinfo=UTC))
        self.assertEqual([post.title for post in recent], ["Latest LangChain Post"])


if __name__ == "__main__":
    unittest.main()
