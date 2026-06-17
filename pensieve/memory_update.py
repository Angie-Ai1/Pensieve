"""產生 MEMORY.md 更新草稿，經使用者在 Telegram 確認後寫回 MEMORY.md。"""

from pensieve import config, gemini_client, prompts
from pensieve.context.daily_notes import build_context_bundle
from pensieve.context.memory import MEMORY_FILENAME


async def generate_memory_draft() -> str:
    """根據現有 MEMORY.md + 近期 daily notes/學習筆記，產生更新草稿內容。"""
    bundle = build_context_bundle()
    prompt = prompts.build_memory_update_prompt(bundle)
    return await gemini_client.generate(prompt)


def write_memory(content: str) -> None:
    """將確認後的內容寫回 MEMORY.md。"""
    memory_path = config.OBSIDIAN_VAULT_PATH / MEMORY_FILENAME
    memory_path.write_text(content, encoding="utf-8")
