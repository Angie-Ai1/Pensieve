"""主題式對話記憶：vault/Memories/<主題>.md，每主題一份重點摘要（帶日期）。

由半夜萃取（memory_extract）寫入；近期有更新的「活躍主題」會注入對話 context。
暖存區（_archive/）與「提到才喚回」屬 P3，本模組以 glob('*.md') 只讀頂層、
天然略過 _archive/ 子資料夾。
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ

MEMORIES_DIR = "Memories"
ARCHIVE_DIRNAME = "_archive"

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
_MAX_FILENAME_LENGTH = 100
_DEFAULT_TOPIC = "未分類"


def _memories_dir() -> Path:
    return config.OBSIDIAN_VAULT_PATH / MEMORIES_DIR


def safe_topic_filename(topic: str) -> str:
    """移除檔名不可用字元、trim 並限制長度；空字串時回傳預設主題名。"""
    cleaned = _INVALID_FILENAME_CHARS.sub("", topic).strip()
    return cleaned[:_MAX_FILENAME_LENGTH] or _DEFAULT_TOPIC


def topic_path(topic: str) -> Path:
    return _memories_dir() / f"{safe_topic_filename(topic)}.md"


def _strip_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """解析開頭 `---` 區塊的簡單 key: value，回傳 (fields, 去除 frontmatter 後的內容)。"""
    content = content.lstrip("﻿")
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---", 4)
    if end == -1:
        return {}, content
    fields: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    body = content[end + len("\n---") :].lstrip("\n")
    return fields, body


def _existing_bullets(content: str) -> list[str]:
    """取出既有的 `- [日期] ...` 條目行。"""
    _, body = _strip_frontmatter(content)
    return [line for line in body.splitlines() if line.lstrip().startswith("- [")]


def append_entry(topic: str, summary: str, when: "datetime.date | None" = None) -> Path:
    """把一筆「- [日期] 摘要」append 到主題筆記（不存在則建立），並更新 frontmatter updated。"""
    when = when or datetime.now(TAIPEI_TZ).date()
    path = topic_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)

    bullets = _existing_bullets(path.read_text(encoding="utf-8")) if path.exists() else []
    bullets.append(f"- [{when:%Y-%m-%d}] {summary.strip()}")

    frontmatter = (
        "---\n"
        f"topic: {topic}\n"
        f"updated: {when:%Y-%m-%d}\n"
        "tags:\n"
        "  - topic-memory\n"
        "---\n\n"
    )
    path.write_text(
        frontmatter + f"# {topic}\n\n" + "\n".join(bullets) + "\n", encoding="utf-8-sig"
    )
    return path


def list_topic_names() -> list[str]:
    """列出目前活躍（頂層，非暖存）主題的名稱，供萃取時沿用既有主題、避免另創近義主題。"""
    directory = _memories_dir()
    if not directory.is_dir():
        return []
    return [path.stem for path in sorted(directory.glob("*.md"))]


def load_active(days: int) -> str:
    """組出近 days 天內有更新的主題筆記內容（注入對話 context）；無則回傳空字串。"""
    directory = _memories_dir()
    if not directory.is_dir():
        return ""

    cutoff = datetime.now(TAIPEI_TZ).date() - timedelta(days=days)
    parts: list[str] = []
    for path in sorted(directory.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        fields, body = _strip_frontmatter(content)
        try:
            updated = datetime.strptime(fields.get("updated", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if updated < cutoff:
            continue
        parts.append(body.strip())

    return "\n\n".join(parts)
