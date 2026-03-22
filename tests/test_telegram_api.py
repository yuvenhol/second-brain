from __future__ import annotations

from unittest import TestCase

from channels.telegram.api import parse_updates, split_message


class TelegramApiTests(TestCase):
    def test_parse_updates_keeps_text_messages(self) -> None:
        updates = [
            {
                "update_id": 10,
                "message": {
                    "message_id": 20,
                    "text": "hello",
                    "chat": {"id": 30},
                    "from": {"first_name": "Yu", "username": "ywh"},
                },
            },
            {
                "update_id": 11,
                "message": {
                    "message_id": 21,
                    "chat": {"id": 31},
                },
            },
        ]

        parsed = parse_updates(updates)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].chat_id, 30)
        self.assertEqual(parsed[0].text, "hello")
        self.assertEqual(parsed[0].sender_name, "Yu")

    def test_split_message_prefers_newline_boundaries(self) -> None:
        text = "a" * 10 + "\n" + "b" * 10
        chunks = split_message(text, limit=12)
        self.assertEqual(chunks, ["a" * 10, "b" * 10])
