"""掃描近期學習吸收筆記（Learn/*.md），供 context bundle 銜接資訊流。"""

from datetime import datetime, timedelta

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ
from pensieve.learning.notes import LEARN_DIR

NOTE_PREFIX = "[Learn] "


def _parse_frontmatter(content: str) -> dict[str, str]:
    """解析 `---` 區塊內的簡單 `key: value` 欄位（不需 PyYAML）。"""
    if not content.startswith("---\n"):
        return {}

    end = content.find("\n---", 4)
    if end == -1:
        return {}

    fields: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    return fields


def load_recent_learning_notes(days: int) -> list[tuple[str, str, str]]:
    """掃描 vault/Learn/*.md，回傳近 days 天內的 [(title, date, source_url), ...]。"""
    learn_dir = config.OBSIDIAN_VAULT_PATH / LEARN_DIR
    if not learn_dir.is_dir():
        return []

    cutoff = datetime.now(TAIPEI_TZ).date() - timedelta(days=days)
    notes: list[tuple[str, str, str]] = []

    for path in learn_dir.glob("*.md"):
        fields = _parse_frontmatter(path.read_text(encoding="utf-8"))
        date_str = fields.get("date", "")
        try:
            note_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if note_date < cutoff:
            continue

        title = path.stem
        if title.startswith(NOTE_PREFIX):
            title = title[len(NOTE_PREFIX) :]

        notes.append((title, date_str, fields.get("source", "")))

    return notes
