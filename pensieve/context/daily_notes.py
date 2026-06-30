"""定位、讀取每日彙整 Markdown，並組裝成 Gemini context bundle。"""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pensieve import config
from pensieve.context.memory import load_memory

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def daily_note_path(target_date: date) -> Path:
    """組出 Daily/{YYYY}/{MM}/{YYYY-MM-DD}.md 路徑，與 n8n「寫入 Markdown」節點命名規則一致。"""
    return (
        config.OBSIDIAN_VAULT_PATH
        / "Daily"
        / f"{target_date:%Y}"
        / f"{target_date:%m}"
        / f"{target_date:%Y-%m-%d}.md"
    )


def read_daily_note(target_date: date) -> str | None:
    """UTF-8 讀取指定日期的每日彙整；檔案不存在回傳 None。"""
    path = daily_note_path(target_date)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_recent_daily_notes(days: int, end_date: date | None = None) -> list[tuple[date, str]]:
    """從 end_date（預設今天，Asia/Taipei）往回 days 天，跳過缺漏，由舊到新排序。"""
    if end_date is None:
        end_date = datetime.now(TAIPEI_TZ).date()

    notes: list[tuple[date, str]] = []
    for offset in range(days):
        target_date = end_date - timedelta(days=offset)
        content = read_daily_note(target_date)
        if content is not None:
            notes.append((target_date, content))

    notes.reverse()
    return notes


def build_context_bundle(days: int = config.DAILY_NOTES_LOOKBACK_DAYS) -> str:
    """組裝 MEMORY.md + 近 N 天 daily notes + 近期學習筆記為單一段落，作為所有 Gemini 呼叫的共用 context。"""
    from pensieve.context.learning_notes import load_recent_learning_notes
    from pensieve.context.topic_memory import load_active

    parts: list[str] = []

    memory = load_memory()
    if memory:
        parts.append(f"# MEMORY\n\n{memory}")

    topics = load_active(days)
    if topics:
        parts.append(f"# 主題記憶（近期聊過的主題）\n\n{topics}")

    for target_date, content in load_recent_daily_notes(days):
        parts.append(f"# Daily Note ({target_date:%Y-%m-%d})\n\n{content}")

    notes = load_recent_learning_notes(days)
    if notes:
        lines = [f"- {title}（{date}）來源：{source_url}" for title, date, source_url in notes]
        parts.append("# 近期學習筆記\n\n" + "\n".join(lines))

    return "\n\n---\n\n".join(parts)
