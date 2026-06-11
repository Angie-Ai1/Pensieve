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
