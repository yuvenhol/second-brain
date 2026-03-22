from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

from channels.telegram.scheduler import DailyDigestScheduler, seconds_until_next_run
from core.blogs import Post
from core.digests import build_daily_digests
from core.news import NewsItem


class DigestTests(TestCase):
    @patch("core.digests.discover_recent_posts")
    def test_build_daily_digests_formats_tech_posts(self, mock_discover) -> None:
        mock_discover.return_value = [
            Post(
                site="https://blog.langchain.com",
                title="Test Post",
                url="https://example.com/post",
                published_at="2026-03-22T00:30:00+00:00",
            )
        ]

        digests = build_daily_digests(
            now=datetime(2026, 3, 22, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        )

        self.assertEqual([digest.domain for digest in digests], ["tech", "news", "market"])
        self.assertIn("Test Post", digests[0].body)
        self.assertIn("LangChain", digests[0].body)
        self.assertIn("<a href=", digests[0].body)

    @patch("core.digests.discover_recent_news")
    @patch("core.digests.discover_recent_posts")
    def test_build_daily_digests_skips_empty_domains(self, mock_posts, mock_news) -> None:
        mock_posts.return_value = []
        mock_news.return_value = {
            "finance": [
                NewsItem(
                    topic="finance",
                    source="Politico",
                    title="Market moves",
                    url="https://example.com/news",
                    published_at="2026-03-22T00:30:00+00:00",
                )
            ],
            "politics": [],
            "military": [],
            "technology": [],
        }

        digests = build_daily_digests(
            now=datetime(2026, 3, 22, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        )

        self.assertFalse(digests[0].has_content)
        self.assertTrue(digests[1].has_content)
        self.assertIn("财经", digests[1].body)
        self.assertIn("<a href=", digests[1].body)

    def test_seconds_until_next_run_is_positive(self) -> None:
        value = seconds_until_next_run(
            timezone_name="Asia/Shanghai",
            target_hour=9,
        )
        self.assertGreater(value, 0)

    def test_scheduler_localizes_before_sending(self) -> None:
        sent: list[tuple[str, str | None, bool]] = []

        class FakeBot:
            def send_message(
                self,
                chat_id: int,
                text: str,
                reply_to_message_id=None,
                *,
                parse_mode: str | None = None,
                disable_web_page_preview: bool = False,
            ) -> None:
                sent.append((text, parse_mode, disable_web_page_preview))

        from core.config import AppConfig

        config = AppConfig.from_env(
            env={
                "TELEGRAM_BOT_TOKEN": "token",
                "OPENAI_API_KEY": "key",
                "ASSISTANT_MODEL": "gpt-4.1-mini",
                "TELEGRAM_ALLOWED_CHAT_IDS": "1",
                "TELEGRAM_PUSH_CHAT_IDS": "1",
            }
        )
        scheduler = DailyDigestScheduler(
            config=config,
            bot=FakeBot(),
            localize_html=lambda text: f"中文::{text}",
        )

        with patch("channels.telegram.scheduler.build_daily_digests") as mock_build:
            mock_build.return_value = [
                type(
                    "Digest",
                    (),
                    {
                        "title": "news 简报",
                        "body": "Finance <a href=\"https://example.com\">hello</a>",
                        "has_content": True,
                    },
                )()
            ]
            scheduler.send_due_digest()

        self.assertEqual(
            sent,
            [("中文::news 简报\n\nFinance <a href=\"https://example.com\">hello</a>", "HTML", True)],
        )
