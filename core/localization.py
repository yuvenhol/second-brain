from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI


class ChineseLocalizer:
    def __init__(self, *, model: str, api_key: str, base_url: str | None = None) -> None:
        self._model = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)

    def localize_html(self, text: str) -> str:
        if not text.strip():
            return text
        prompt = (
            "把下面这段将要发给用户的 Telegram HTML 消息改写成自然、简洁、完整的中文。\n"
            "严格要求：\n"
            "1. 保留原有的 HTML 结构，特别是 <a href=\"...\">...</a> 超链接，不要删除链接。\n"
            "2. 只翻译用户可见文本；链接地址不要改。\n"
            "3. 标题、来源、新闻条目都翻译成中文；必要时可在括号中保留英文原名。\n"
            "4. 不要添加原文没有的信息。\n"
            "5. 输出必须仍然是合法的 Telegram HTML 文本。\n\n"
            f"原文：\n{text}"
        )
        response = self._model.invoke(prompt)
        return flatten_text(response.content).strip() or text


def flatten_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                value = item.get("text", "")
                if isinstance(value, str):
                    parts.append(value)
        return "\n".join(parts)
    return ""
