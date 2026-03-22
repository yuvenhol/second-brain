from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from channels.telegram.api import TelegramBotClient
from core.config import AppConfig
from core.digests import build_daily_digests
from core.localization import ChineseLocalizer


LOGGER = logging.getLogger(__name__)


class DailyDigestScheduler:
    def __init__(
        self,
        *,
        config: AppConfig,
        bot: TelegramBotClient,
        localize_html: Callable[[str], str] | None = None,
    ) -> None:
        self._config = config
        self._bot = bot
        self._localize_html = localize_html or ChineseLocalizer(
            model=config.assistant_model,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        ).localize_html
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if not self._config.digest_enabled:
            LOGGER.info("Daily digest scheduler disabled")
            return
        if not self._config.telegram_push_chat_ids:
            LOGGER.info("Daily digest scheduler disabled: no push chat ids configured")
            return
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            name="daily-digest-scheduler",
            daemon=True,
        )
        self._thread.start()

    def _run_loop(self) -> None:
        if self._config.digest_run_on_startup:
            self.send_due_digest()
        while not self._stop_event.is_set():
            sleep_seconds = seconds_until_next_run(
                timezone_name=self._config.digest_timezone,
                target_hour=self._config.digest_hour,
            )
            LOGGER.info("Next daily digest in %.0f seconds", sleep_seconds)
            if self._stop_event.wait(timeout=sleep_seconds):
                return
            self.send_due_digest()

    def send_due_digest(self) -> None:
        digests = [
            digest
            for digest in build_daily_digests(timezone_name=self._config.digest_timezone)
            if digest.has_content
        ]
        if not digests:
            LOGGER.info("Skipped daily digest: no real content available")
            return
        for chat_id in self._config.telegram_push_chat_ids or []:
            for digest in digests:
                message = self._localize_html(f"{digest.title}\n\n{digest.body}")
                self._bot.send_message(
                    chat_id,
                    message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
        LOGGER.info(
            "Sent %s daily digest messages to %s chats",
            len(digests),
            len(self._config.telegram_push_chat_ids or []),
        )


def seconds_until_next_run(*, timezone_name: str, target_hour: int) -> float:
    now = datetime.now(tz=ZoneInfo(timezone_name))
    next_run = now.replace(
        hour=target_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    if next_run <= now:
        next_run += timedelta(days=1)
    return max((next_run - now).total_seconds(), 1.0)
