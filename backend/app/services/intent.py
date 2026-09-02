"""根据用户本轮最后一句话判断：识别填表 vs 改已填格子 vs 普通问答。"""
import re

from .table_edit import looks_like_local_edit

CHAT_PHRASES = (
    "为啥", "为什么", "是不是", "对吗", "解释", "先别识别",
    "怎么来的", "没匹配", "没有匹配", "为何",
)
RECOGNIZE_PHRASES = (
    "识别", "导入", "提取", "填表", "重新识别", "覆盖", "再导", "再抽", "重新抽",
    "过滤", "只要", "按规则", "按这个规则",
)


def classify_intent(text: str, has_files: bool = False, has_rows: bool = False) -> str:
    """返回 'recognize' | 'chat' | 'edit'。"""
    t = (text or "").strip()
    if not t:
        return "recognize" if has_files else "chat"
    if any(p in t for p in CHAT_PHRASES):
        return "chat"
    if re.search(r"[吗呢？?]", t):
        return "chat"
    if looks_like_local_edit(t):
        return "edit" if has_rows else "chat"
    if any(p in t for p in RECOGNIZE_PHRASES):
        return "recognize"
    if has_rows:
        return "chat"
    return "chat"
