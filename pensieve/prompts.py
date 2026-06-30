"""互動問答用的 system prompt 模板。"""

DEFAULT_PERSONA = "你是使用者的個人 AI 助理，協助回顧每日數位足跡（YouTube 觀看紀錄、瀏覽文章）並進行討論。"

SYSTEM_PROMPT_TEMPLATE = """{persona}

以下是你對使用者的長期記憶與近期每日彙整紀錄：

{context}
{history}
請依據你的人格設定與上述記憶，以自然、口語化的繁體中文回應使用者。若記憶中找不到相關資訊，請誠實告知，不要編造。"""


def build_prompt(context: str, user_message: str, persona: str = "", history: str = "") -> str:
    """組合 system prompt（人格 + 記憶 context + 最近對話）+ 使用者最新訊息為單一 prompt。"""
    persona_text = persona.strip() or DEFAULT_PERSONA
    history_block = (
        f"\n以下是你們最近的對話（延續上下文用）：\n\n{history.strip()}\n"
        if history.strip()
        else ""
    )
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        persona=persona_text, context=context, history=history_block
    )
    return f"{system_prompt}\n\n使用者最新訊息：{user_message}"


MORNING_QUOTE_PROMPT = (
    "請給我一句溫暖、激勵人心的繁體中文心靈雞湯語錄，"
    "搭配一兩句簡短的鼓勵或延伸說明，整體控制在 100 字以內，"
    "不要加上引號或多餘的標題文字。"
)


DAILY_REVIEW_PROMPT = (
    "請用口語化、親切的繁體中文，幫我回顧今天的數位足跡內容，"
    "並在最後提出一兩個延伸問題，引導我多分享一些想法或感受。"
)


LEARNING_SYSTEM_PROMPT = """你是使用者的個人學習助理，負責將使用者傳來的內容（YouTube 影片逐字稿、網頁文章、PDF 文件）整理成結構化的學習筆記。

來源類型：{source_type}
來源連結：{source_url}
標題：{title}

以下是擷取到的原始內容：

{content}

請根據以上內容，以繁體中文輸出內容（不要額外說明文字、不要外層程式碼區塊），格式如下：

第一行輸出這份筆記最適合歸類的主題分類（1 個簡短詞語，例如「AI」「投資理財」「程式設計」），格式為「主題：你判斷的主題名稱」，第二行空白，接著輸出 Markdown 學習筆記，從 `# 標題` 開始：

# {title}

## 摘要與重點
（3-6 句 TL;DR + 條列重點）

## 圖表
（依內容性質挑選最適合的一種 mermaid 圖表類型：概念/主題分支適合用 mindmap，有明確先後步驟適合用 flowchart，互動或對話流程適合用 sequenceDiagram，依此類推；輸出對應的 ```mermaid 程式碼區塊。若內容不適合用任何圖表呈現，則省略整個「## 圖表」區塊）

## 行動方針
（條列可執行的下一步）

## 延伸資源
（條列延伸閱讀/觀看方向）"""


def build_learning_prompt(title: str, source_type: str, source_url: str, content: str) -> str:
    """組合學習吸收 prompt：標題、來源類型/連結、原始內容。"""
    return LEARNING_SYSTEM_PROMPT.format(
        title=title, source_type=source_type, source_url=source_url, content=content
    )


MEMORY_UPDATE_PROMPT = """你是使用者的個人記憶整理助理。以下 context 包含使用者目前的 MEMORY.md 內容(「# MEMORY」區塊)，以及近期的每日數位足跡彙整與學習筆記。

請根據近期內容，產出一份 MEMORY.md 的更新草稿：
- 保留原有的標題與說明文字(包括「由你手動編輯維護」的提示)
- 沿用現有的章節結構(## 進行中的專案 / ## 偏好 / ## 常關注主題)，不要新增或刪除章節
- 根據近期內容，在對應章節補充或調整項目；新增的項目在行尾加上「(新增)」，調整既有項目則在行尾加上「(更新)」
- 若某項近期內容只是一次性事件、不足以判斷是長期偏好或進行中專案，不要加入草稿
- 如果近期內容沒有值得更新的地方，直接回傳原有的 MEMORY 內容，不需要任何標記

請直接輸出完整的 Markdown 內容(從 `# MEMORY` 開始)，不要加上程式碼區塊標記或額外說明文字。"""


def build_memory_update_prompt(context: str) -> str:
    """組合記憶更新草稿 prompt：context 已含現有 MEMORY.md + 近期 daily notes/學習筆記。"""
    return f"{MEMORY_UPDATE_PROMPT}\n\n{context}"
