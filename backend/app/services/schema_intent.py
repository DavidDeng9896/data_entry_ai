"""建表对话意图：出/改结构 vs 只问答。"""
import re

SCHEMA_PHRASES = (
    "抽出列", "抽列", "建表", "建一张", "生成列", "列配置",
    "去掉", "删掉", "只要", "按内部",
    "改成 number", "改成数字", "改成 text", "改成日期",
    "加一列", "添加列", "补一列", "再加",
    "表名改成", "改表名", "改名为", "描述改成",
)

CHAT_PHRASES = (
    "为啥", "为什么", "是不是", "对吗", "解释",
    "怎么来的", "什么意思", "为何",
)

META_PHRASES = (
    "表名改成", "改表名", "改名为", "名叫", "表名叫",
    "描述改成", "改描述",
)

_ASSAY_HINT = re.compile(
    r"(PK|表|列|CL|AUC|Vss|T1/?2|IC50|%F|Fu|MMS|PPB|hERG)",
    re.I,
)


def classify_schema_intent(text: str, has_files: bool = False) -> str:
    """返回 'schema' | 'chat'。"""
    t = (text or "").strip()
    if not t:
        return "schema" if has_files else "chat"
    chat_hit = any(p in t for p in CHAT_PHRASES)
    schema_hit = any(p in t for p in SCHEMA_PHRASES)
    if chat_hit and not schema_hit:
        return "chat"
    if schema_hit:
        return "schema"
    if re.search(r"[吗？?]", t):
        return "chat"
    if has_files:
        return "schema"
    if _ASSAY_HINT.search(t):
        return "schema"
    return "chat"


def wants_meta_change(text: str) -> bool:
    t = text or ""
    return any(p in t for p in META_PHRASES)
