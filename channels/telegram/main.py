from __future__ import annotations

import logging
import os
import time

from channels.telegram.api import IncomingMessage, TelegramBotClient
from channels.telegram.scheduler import DailyDigestScheduler
from core.agent import AssistantAgentRuntime
from core.config import AppConfig


LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def should_process(chat_id: int, allowed_chat_ids: frozenset[int] | None) -> bool:
    return allowed_chat_ids is None or chat_id in allowed_chat_ids


def handle_message(
    message: IncomingMessage,
    *,
    config: AppConfig,
    bot: TelegramBotClient,
    agent: AssistantAgentRuntime,
) -> None:
    if not should_process(message.chat_id, config.telegram_allowed_chat_ids):
        LOGGER.info("Ignoring message from chat_id=%s", message.chat_id)
        return

    if message.text.strip() == "/start":
        bot.send_message(
            message.chat_id,
            "助手已连接。直接发消息即可；如需长期记忆，请明确说“帮我记住 xxx”。",
            reply_to_message_id=message.message_id,
        )
        return

    try:
        response = agent.respond(
            chat_id=message.chat_id,
            text=message.text,
            sender_name=message.sender_name,
            username=message.username,
        )
    except Exception:
        LOGGER.exception("Agent processing failed for chat_id=%s", message.chat_id)
        response = "处理这条消息时失败了。请稍后重试。"

    bot.send_message(
        message.chat_id,
        response,
        reply_to_message_id=message.message_id,
    )


def main() -> None:
    configure_logging()
    os.environ.setdefault("LANGSMITH_TRACING", "false")
    config = AppConfig.from_env()
    bot = TelegramBotClient(
        config.telegram_bot_token,
        request_timeout_seconds=config.telegram_request_timeout_seconds,
    )
    agent = AssistantAgentRuntime(config)
    bot.prepare_polling(drop_pending_updates=config.telegram_drop_pending_updates)
    DailyDigestScheduler(config=config, bot=bot).start()

    next_offset: int | None = None
    LOGGER.info("Telegram bot started")
    while True:
        try:
            updates = bot.get_updates(
                offset=next_offset,
                timeout=config.telegram_poll_timeout_seconds,
            )
            for message in updates:
                next_offset = message.update_id + 1
                handle_message(message, config=config, bot=bot, agent=agent)
        except KeyboardInterrupt:
            LOGGER.info("Telegram bot stopped")
            return
        except Exception:
            LOGGER.exception("Polling loop failed; retrying in 3 seconds")
            time.sleep(3)


if __name__ == "__main__":
    main()
