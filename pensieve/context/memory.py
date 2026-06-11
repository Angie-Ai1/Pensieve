"""讀取 vault 根目錄的 MEMORY.md（唯讀）。"""

import logging

from pensieve import config

logger = logging.getLogger(__name__)

MEMORY_FILENAME = "MEMORY.md"


def load_memory() -> str:
    """讀取 MEMORY.md 內容；檔案不存在時回傳空字串並記錄一筆 log（非致命錯誤）。"""
    memory_path = config.OBSIDIAN_VAULT_PATH / MEMORY_FILENAME
    if not memory_path.exists():
        logger.info("MEMORY.md 不存在於 %s，視為空白", memory_path)
        return ""
    return memory_path.read_text(encoding="utf-8")
