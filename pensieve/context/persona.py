"""讀取 vault 根目錄的 Persona.md（pensieve 的人格設定，唯讀）。

人格是「穩定不變、由使用者手動維護」的自我設定（名字／個性／語氣），
每次對話都會注入 system prompt。檔案不存在時回傳空字串，由 prompts 端套用預設人格。
"""

import logging

from pensieve import config

logger = logging.getLogger(__name__)

PERSONA_FILENAME = "Persona.md"


def load_persona() -> str:
    """讀取 Persona.md 內容；檔案不存在時回傳空字串並記錄一筆 log（非致命）。"""
    persona_path = config.OBSIDIAN_VAULT_PATH / PERSONA_FILENAME
    if not persona_path.exists():
        logger.info("Persona.md 不存在於 %s，改用預設人格", persona_path)
        return ""
    return persona_path.read_text(encoding="utf-8")
