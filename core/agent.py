from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from deepagents.backends.utils import create_file_data
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from core.config import AppConfig
from core.tools import fetch_recent_blog_posts


LOGGER = logging.getLogger(__name__)


SYSTEM_PROMPT = """你是我的长期个人助手。

工作原则：
- 默认用中文回复；如果用户显式使用其他语言或要求其他语言，再切换。
- 所有用户可见输出默认都使用中文，包括普通回复、提醒、简报、摘要和任务说明。
- 如果输入材料是英文，优先翻译成中文后再输出；必要时可在括号中保留英文原文。
- 对话是统一入口，消息对外平级。
- 长期记忆默认不自动写入。只有当用户明确要求“帮我记住”“记住这个”“以后按这个来”时，才可以写入 /memories/ 下的文件。
- 如果用户要求忘记、修正或覆盖长期记忆，应直接在 /memories/ 下更新对应内容。
- 固定逻辑优先通过 skills 和 tools 完成，不要编造外部数据。
- 当用户询问最近博客更新时，优先使用 fetch_recent_blog_posts 工具。
- 当前运行时已接入 Telegram 对话闭环、技术博客获取工具和外部每日简报调度。
- 定时任务和主动推送由外部调度器负责，不由你自行后台创建。
- 股票相关内容只允许研究、提醒建议和模拟交易讨论，不允许真实交易。
"""


def load_seed_files(project_root: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    skill_docs = sorted((project_root / "skills").rglob("SKILL.md"))
    for local_path in [project_root / "AGENTS.md", *skill_docs]:
        if not local_path.is_file():
            continue
        relative_path = "/" + local_path.relative_to(project_root).as_posix()
        files[relative_path] = create_file_data(local_path.read_text(encoding="utf-8"))
    return files


def build_backend(memories_dir: Path):
    return lambda runtime: CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": FilesystemBackend(root_dir=str(memories_dir), virtual_mode=True),
        },
    )


class AssistantAgentRuntime:
    def __init__(self, config: AppConfig, model: Any | None = None) -> None:
        config.memories_dir.mkdir(parents=True, exist_ok=True)
        self._config = config
        self._seed_files = load_seed_files(config.project_root)
        self._agent = create_deep_agent(
            model=model
            or ChatOpenAI(
                model=config.assistant_model,
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
            ),
            system_prompt=SYSTEM_PROMPT,
            tools=[fetch_recent_blog_posts],
            backend=build_backend(config.memories_dir),
            checkpointer=MemorySaver(),
            skills=["/skills/"],
            memory=["/AGENTS.md"],
        )

    def respond(
        self,
        *,
        chat_id: int,
        text: str,
        sender_name: str,
        username: str | None,
    ) -> str:
        message_content = text.strip()
        if not message_content:
            return "当前只支持文本消息。"

        config = {"configurable": {"thread_id": f"telegram:{chat_id}"}}
        user_line = (
            f"来自 Telegram 用户 {sender_name}"
            + (f" (@{username})" if username else "")
            + f" 的消息：\n{message_content}"
        )
        LOGGER.info("Invoking agent for chat_id=%s", chat_id)
        result = self._agent.invoke(
            {
                "messages": [{"role": "user", "content": user_line}],
                "files": self._seed_files,
            },
            config=config,
        )
        return extract_text_response(result)


def extract_text_response(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        content = message.content if hasattr(message, "content") else message.get("content")
        text = flatten_content_to_text(content)
        if text:
            return text
    raise RuntimeError("Agent returned no text response")


def flatten_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part.strip() for part in parts if part.strip()).strip()
    return ""
