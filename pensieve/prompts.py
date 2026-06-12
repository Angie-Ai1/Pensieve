"""互動問答用的 system prompt 模板。"""

SYSTEM_PROMPT_TEMPLATE = """你是使用者的個人 AI 助理，協助回顧每日數位足跡（YouTube 觀看紀錄、瀏覽文章）並進行討論。

以下是使用者的長期記憶與近期每日彙整紀錄：

{context}

請根據以上內容，以自然、口語化的繁體中文回答使用者的問題。若內容中找不到相關資訊，請誠實告知，不要編造。"""


def build_prompt(context: str, user_message: str) -> str:
    """組合 system prompt + context + 使用者訊息為單一 prompt。"""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    return f"{system_prompt}\n\n使用者問題：{user_message}"


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

## 心智圖
```mermaid
mindmap
  ((主題))
    分支1
    分支2
```

## 行動方針
（條列可執行的下一步；若內容有明確的先後步驟順序，可額外加上 mermaid flowchart 呈現流程，不適合則省略圖表）

## 延伸資源
（條列延伸閱讀/觀看方向）"""


def build_learning_prompt(title: str, source_type: str, source_url: str, content: str) -> str:
    """組合學習吸收 prompt：標題、來源類型/連結、原始內容。"""
    return LEARNING_SYSTEM_PROMPT.format(
        title=title, source_type=source_type, source_url=source_url, content=content
    )
