from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from core.config import AppConfig


class ConfigTests(TestCase):
    def test_from_env_parses_expected_fields(self) -> None:
        config = AppConfig.from_env(
            env={
                "TELEGRAM_BOT_TOKEN": "token",
                "OPENAI_API_KEY": "key",
                "ASSISTANT_MODEL": "gpt-4.1-mini",
                "OPENAI_BASE_URL": "https://example.com/v1",
                "TELEGRAM_ALLOWED_CHAT_IDS": "1, 2",
                "TELEGRAM_DROP_PENDING_UPDATES": "false",
                "TELEGRAM_POLL_TIMEOUT_SECONDS": "15",
                "TELEGRAM_REQUEST_TIMEOUT_SECONDS": "45",
            },
            project_root=Path("/tmp/project"),
        )

        self.assertEqual(config.telegram_bot_token, "token")
        self.assertEqual(config.openai_api_key, "key")
        self.assertEqual(config.assistant_model, "gpt-4.1-mini")
        self.assertEqual(config.openai_base_url, "https://example.com/v1")
        self.assertEqual(config.telegram_allowed_chat_ids, frozenset({1, 2}))
        self.assertFalse(config.telegram_drop_pending_updates)
        self.assertEqual(config.telegram_poll_timeout_seconds, 15)
        self.assertEqual(config.telegram_request_timeout_seconds, 45)
        self.assertEqual(config.agents_file, Path("/tmp/project/AGENTS.md"))

    def test_required_values_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            AppConfig.from_env(
                env={"TELEGRAM_BOT_TOKEN": "x", "OPENAI_API_KEY": "y"},
                project_root=Path("/tmp/project"),
            )

    def test_push_chat_ids_must_be_subset_of_allowed_chat_ids(self) -> None:
        with self.assertRaises(ValueError):
            AppConfig.from_env(
                env={
                    "TELEGRAM_BOT_TOKEN": "token",
                    "OPENAI_API_KEY": "key",
                    "ASSISTANT_MODEL": "gpt-4.1-mini",
                    "TELEGRAM_ALLOWED_CHAT_IDS": "1",
                    "TELEGRAM_PUSH_CHAT_IDS": "2",
                },
                project_root=Path("/tmp/project"),
            )

    def test_placeholder_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AppConfig.from_env(
                env={
                    "TELEGRAM_BOT_TOKEN": "123456:replace-me",
                    "OPENAI_API_KEY": "replace-me",
                    "ASSISTANT_MODEL": "gpt-4.1-mini",
                    "TELEGRAM_ALLOWED_CHAT_IDS": "1",
                },
                project_root=Path("/tmp/project"),
            )
