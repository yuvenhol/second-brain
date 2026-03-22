from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def _parse_chat_ids(value: str | None) -> frozenset[int] | None:
    if value is None or not value.strip():
        return None
    result: set[int] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        result.add(int(item))
    return frozenset(result)


def _require_non_placeholder(value: str, env_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{env_name} is required")
    placeholders = {
        "replace-me",
        "your-token",
        "your-api-key",
        "123456:replace-me",
    }
    if normalized.lower() in placeholders:
        raise ValueError(f"{env_name} must not use a placeholder value")
    return normalized


@dataclass(frozen=True)
class AppConfig:
    telegram_bot_token: str
    openai_api_key: str
    assistant_model: str
    openai_base_url: str | None
    telegram_allowed_chat_ids: frozenset[int] | None
    telegram_push_chat_ids: frozenset[int] | None
    telegram_poll_timeout_seconds: int
    telegram_request_timeout_seconds: int
    telegram_drop_pending_updates: bool
    digest_enabled: bool
    digest_run_on_startup: bool
    digest_hour: int
    digest_timezone: str
    project_root: Path
    agents_file: Path
    skills_dir: Path
    memories_dir: Path

    @classmethod
    def from_env(
        cls, env: dict[str, str] | None = None, project_root: Path | None = None
    ) -> "AppConfig":
        data = dict(os.environ if env is None else env)
        root = project_root or Path(__file__).resolve().parents[1]
        telegram_bot_token = _require_non_placeholder(
            data.get("TELEGRAM_BOT_TOKEN", ""),
            "TELEGRAM_BOT_TOKEN",
        )
        openai_api_key = _require_non_placeholder(
            data.get("OPENAI_API_KEY", ""),
            "OPENAI_API_KEY",
        )
        assistant_model = data.get("ASSISTANT_MODEL", "").strip()
        if not assistant_model:
            raise ValueError("ASSISTANT_MODEL is required")
        poll_timeout = int(data.get("TELEGRAM_POLL_TIMEOUT_SECONDS", "30"))
        request_timeout = int(data.get("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "60"))
        if poll_timeout <= 0:
            raise ValueError("TELEGRAM_POLL_TIMEOUT_SECONDS must be positive")
        if request_timeout <= 0:
            raise ValueError("TELEGRAM_REQUEST_TIMEOUT_SECONDS must be positive")
        digest_hour = int(data.get("DIGEST_SCHEDULE_HOUR", "9"))
        if digest_hour < 0 or digest_hour > 23:
            raise ValueError("DIGEST_SCHEDULE_HOUR must be between 0 and 23")
        allowed_chat_ids = _parse_chat_ids(data.get("TELEGRAM_ALLOWED_CHAT_IDS"))
        if not allowed_chat_ids:
            raise ValueError(
                "TELEGRAM_ALLOWED_CHAT_IDS is required for public-safe startup"
            )
        push_chat_ids = _parse_chat_ids(data.get("TELEGRAM_PUSH_CHAT_IDS"))
        if push_chat_ids is not None and not push_chat_ids.issubset(allowed_chat_ids):
            raise ValueError(
                "TELEGRAM_PUSH_CHAT_IDS must be a subset of TELEGRAM_ALLOWED_CHAT_IDS"
            )
        return cls(
            telegram_bot_token=telegram_bot_token,
            openai_api_key=openai_api_key,
            assistant_model=assistant_model,
            openai_base_url=(data.get("OPENAI_BASE_URL") or "").strip() or None,
            telegram_allowed_chat_ids=allowed_chat_ids,
            telegram_push_chat_ids=push_chat_ids or allowed_chat_ids,
            telegram_poll_timeout_seconds=poll_timeout,
            telegram_request_timeout_seconds=request_timeout,
            telegram_drop_pending_updates=_parse_bool(
                data.get("TELEGRAM_DROP_PENDING_UPDATES"), default=True
            ),
            digest_enabled=_parse_bool(data.get("DIGEST_ENABLED"), default=True),
            digest_run_on_startup=_parse_bool(
                data.get("DIGEST_RUN_ON_STARTUP"), default=False
            ),
            digest_hour=digest_hour,
            digest_timezone=(data.get("DIGEST_TIMEZONE") or "Asia/Shanghai").strip(),
            project_root=root,
            agents_file=root / "AGENTS.md",
            skills_dir=root / "skills",
            memories_dir=root / "memories",
        )
