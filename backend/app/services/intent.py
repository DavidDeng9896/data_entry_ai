"""根据用户本轮最后一句话判断：识别填表 vs 普通问答。"""
import re

CHAT_PHRASES = ("为啥", "为什么", "是不是", "对吗", "解释", "先别识别")
RECOGNIZE_PHRASES = ("识别", "导入", "提取", "填表", "重新识别", "覆盖", "再导")


def classify_intent(text: str, has_files: bool = False) -> str:
    """返回 'recognize' 或 'chat'。"""
    t = (text or "").strip()
    if not t:
        return "recognize" if has_files else "chat"
    if any(p in t for p in CHAT_PHRASES):
        return "chat"
    if any(p in t for p in RECOGNIZE_PHRASES):
        return "recognize"
    if re.search(r"[吗呢？?]", t):
        return "chat"
    return "chat"
