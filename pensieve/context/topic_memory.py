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

    # 若該主題已在暖存區、現在又被聊到，先救回頂層接續寫，避免活躍/暖存兩份分歧。
    archived = path.parent / ARCHIVE_DIRNAME / path.name
    if not path.exists() and archived.exists():
        archived.rename(path)

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


def archive_stale_topics(days: int) -> int:
    """把超過 days 天沒更新的活躍主題移進 _archive/；回傳移動的主題數。"""
    directory = _memories_dir()
    if not directory.is_dir():
        return 0

    cutoff = datetime.now(TAIPEI_TZ).date() - timedelta(days=days)
    archive_dir = directory / ARCHIVE_DIRNAME
    moved = 0
    for path in sorted(directory.glob("*.md")):
        fields, _ = _strip_frontmatter(path.read_text(encoding="utf-8"))
        try:
            updated = datetime.strptime(fields.get("updated", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if updated >= cutoff:
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / path.name
        if target.exists():
            target.unlink()
        path.rename(target)
        moved += 1

    return moved


def _bigrams(text: str) -> set[str]:
    """取出字串的 2-gram 集合（去空白），供主題與訊息的關鍵字比對。"""
    cleaned = re.sub(r"\s", "", text)
    return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)}


def _match_score(topic: str, message: str) -> int:
    """主題與訊息的相關度：完整命中（主題名為訊息子字串）給高分，否則為共用 2-gram 數。"""
    if len(topic) >= 2 and topic in message:
        return 1000
    return len(_bigrams(topic) & _bigrams(message))


def _topic_matches(topic: str, message: str) -> bool:
    """判斷使用者訊息是否提到某暖存主題（完整命中，或至少共用 1 個 2-gram）。"""
    return _match_score(topic, message) > 0


def load_archived_matches(message: str, limit: int = 3) -> str:
    """掃描 _archive/，回傳被訊息「提到」的暖存主題內容（喚回）；依相關度取前 limit 個。"""
    archive_dir = _memories_dir() / ARCHIVE_DIRNAME
    if not archive_dir.is_dir():
        return ""

    scored: list[tuple[int, str]] = []
    for path in sorted(archive_dir.glob("*.md")):
        score = _match_score(path.stem, message)
        if score > 0:
            _, body = _strip_frontmatter(path.read_text(encoding="utf-8"))
            scored.append((score, body.strip()))

    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(body for _, body in scored[:limit])
