from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from core.agent import AssistantAgentRuntime, load_seed_files
from core.config import AppConfig


class AgentRuntimeTests(TestCase):
    def test_load_seed_files_includes_agents_and_skills(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("root rules", encoding="utf-8")
            (root / "skills" / "demo").mkdir(parents=True)
            (root / "skills" / "demo" / "SKILL.md").write_text(
                "demo skill",
                encoding="utf-8",
            )

            files = load_seed_files(root)

            self.assertIn("/AGENTS.md", files)
            self.assertIn("/skills/demo/SKILL.md", files)

    def test_runtime_respond_returns_agent_text(self) -> None:
        config = AppConfig.from_env(
            env={
                "TELEGRAM_BOT_TOKEN": "token",
                "OPENAI_API_KEY": "key",
                "ASSISTANT_MODEL": "gpt-4.1-mini",
                "TELEGRAM_ALLOWED_CHAT_IDS": "123",
            },
            project_root=Path(".").resolve(),
        )
        runtime = AssistantAgentRuntime(config)

        class FakeGraph:
            def invoke(self, payload, config):  # noqa: A003
                assert payload["messages"][0]["role"] == "user"
                assert config["configurable"]["thread_id"] == "telegram:123"
                return {"messages": [{"role": "assistant", "content": "测试回复"}]}

        runtime._agent = FakeGraph()  # type: ignore[attr-defined]

        response = runtime.respond(
            chat_id=123,
            text="你好",
            sender_name="Yu",
            username="ywh",
        )

        self.assertEqual(response, "测试回复")
