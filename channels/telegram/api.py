from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TELEGRAM_MESSAGE_LIMIT = 4096


@dataclass(frozen=True)
class IncomingMessage:
    update_id: int
    chat_id: int
    message_id: int
    text: str
    sender_name: str
    username: str | None


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = text
    while len(current) > limit:
        boundary = current.rfind("\n", 0, limit)
        if boundary <= 0:
            boundary = limit
        chunks.append(current[:boundary].rstrip())
        current = current[boundary:].lstrip()
    if current:
        chunks.append(current)
    return chunks


class TelegramBotClient:
    def __init__(self, token: str, request_timeout_seconds: int = 60) -> None:
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._request_timeout_seconds = request_timeout_seconds

    def prepare_polling(self, drop_pending_updates: bool) -> None:
        self._call_api(
            "deleteWebhook",
            {"drop_pending_updates": bool(drop_pending_updates)},
        )

    def get_updates(self, offset: int | None, timeout: int) -> list[IncomingMessage]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        response = self._call_api("getUpdates", payload)
        updates = response.get("result", [])
        return parse_updates(updates)

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        *,
        parse_mode: str | None = None,
        disable_web_page_preview: bool = False,
    ) -> None:
        for chunk in split_message(text):
            payload: dict[str, Any] = {"chat_id": chat_id, "text": chunk}
            if reply_to_message_id is not None:
                payload["reply_parameters"] = {"message_id": reply_to_message_id}
            if parse_mode is not None:
                payload["parse_mode"] = parse_mode
            if disable_web_page_preview:
                payload["link_preview_options"] = {"is_disabled": True}
            self._call_api("sendMessage", payload)

    def _call_api(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url=f"{self._base_url}/{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._request_timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram API {method} failed: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Telegram API {method} network error: {exc}") from exc

        data = json.loads(body)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API {method} failed: {body}")
        return data


def parse_updates(updates: list[dict[str, Any]]) -> list[IncomingMessage]:
    result: list[IncomingMessage] = []
    for update in updates:
        message = update.get("message")
        if not message:
            continue
        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        chat = message.get("chat", {})
        sender = message.get("from", {})
        sender_name = (
            sender.get("first_name")
            or sender.get("username")
            or chat.get("title")
            or "user"
        )
        result.append(
            IncomingMessage(
                update_id=int(update["update_id"]),
                chat_id=int(chat["id"]),
                message_id=int(message["message_id"]),
                text=text,
                sender_name=str(sender_name),
                username=sender.get("username"),
            )
        )
    return result
