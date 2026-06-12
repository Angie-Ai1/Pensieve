"""寫入學習吸收筆記至 vault/Learn/，並依主題建立硬連結子資料夾。"""

import os
import re
from datetime import datetime
from pathlib import Path

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ

LEARN_DIR = "Learn"

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
_MAX_FILENAME_LENGTH = 150

_TOPIC_PREFIXES = ("主題：", "主題:")
_DEFAULT_TOPIC = "未分類"


def safe_filename(title: str) -> str:
    """移除 Windows 檔名不可用字元，trim 並限制長度。"""
    cleaned = _INVALID_FILENAME_CHARS.sub("", title).strip()
    return cleaned[:_MAX_FILENAME_LENGTH]


def _split_topic(markdown: str) -> tuple[str, str]:
    """從 Gemini 回應第一行解析主題分類（「主題：xxx」），回傳 (topic, 去除該行後的 markdown)。"""
    stripped = markdown.lstrip()
    first_line, _, rest = stripped.partition("\n")
    first_line = first_line.strip()

    for prefix in _TOPIC_PREFIXES:
        if first_line.startswith(prefix):
            topic = first_line[len(prefix) :].strip()
            return topic or _DEFAULT_TOPIC, rest.lstrip("\n")

    return _DEFAULT_TOPIC, markdown


def write_learning_note(title: str, source_url: str, markdown: str) -> Path:
    """寫入 vault/Learn/[Learn] {safe_title}.md，並於 Learn/{主題}/ 建立硬連結；回傳 vault-relative 路徑。"""
    topic, body = _split_topic(markdown)

    learn_dir = config.OBSIDIAN_VAULT_PATH / LEARN_DIR
    learn_dir.mkdir(parents=True, exist_ok=True)

    filename = f"[Learn] {safe_filename(title)}.md"
    file_path = learn_dir / filename
    today = datetime.now(TAIPEI_TZ).date()

    frontmatter = (
        "---\n"
        f"date: {today:%Y-%m-%d}\n"
        f"source: {source_url}\n"
        "tags:\n"
        "  - learning\n"
        "---\n\n"
    )
    file_path.write_text(frontmatter + body, encoding="utf-8")

    topic_dir = learn_dir / safe_filename(topic)
    topic_dir.mkdir(parents=True, exist_ok=True)
    link_path = topic_dir / filename
    if link_path.exists():
        link_path.unlink()
    os.link(file_path, link_path)

    return file_path.relative_to(config.OBSIDIAN_VAULT_PATH)
