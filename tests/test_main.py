from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from channels.telegram.api import IncomingMessage
from channels.telegram.main import handle_message
from core.config import AppConfig


class MainLoopTests(TestCase):
    def test_handle_message_calls_agent_and_sends_reply(self) -> None:
        config = AppConfig.from_env(
            env={
                "TELEGRAM_BOT_TOKEN": "token",
                "OPENAI_API_KEY": "key",
                "ASSISTANT_MODEL": "gpt-4.1-mini",
                "TELEGRAM_ALLOWED_CHAT_IDS": "42",
            },
            project_root=Path(".").resolve(),
        )
        message = IncomingMessage(
            update_id=1,
            chat_id=42,
            message_id=7,
            text="你好",
            sender_name="Yu",
            username="ywh",
        )

        class FakeBot:
            def __init__(self) -> None:
                self.sent: list[tuple[int, str, int | None]] = []

            def send_message(
                self,
                chat_id: int,
                text: str,
                reply_to_message_id: int | None = None,
                **_: object,
            ) -> None:
                self.sent.append((chat_id, text, reply_to_message_id))

        class FakeAgent:
            def respond(self, **kwargs) -> str:
                self.kwargs = kwargs
                return "收到"

        bot = FakeBot()
        agent = FakeAgent()

        handle_message(message, config=config, bot=bot, agent=agent)

        self.assertEqual(
            bot.sent,
            [(42, "收到", 7)],
        )
