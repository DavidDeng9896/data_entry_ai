"""AI 识别：把解析后的文件内容 + 表头定义 + 可选 skill 规则 → OpenAI 兼容接口 → 结构化行数据。
支持文本模型（Excel/CSV/PDF）和视觉模型（图片扫描件）。mock 模式返回演示数据。
"""
import base64
import json
import re
import time

from openai import OpenAI

from .. import database as db
from ..schemas import ColumnDef, ChatMessage
from . import file_parser

_BASELINE_PROMPT = """# 导入识别基线

## 1. 角色与任务

你是科研 **结果表导入助手**。用户会提供：

1. 一份已解析的源文件内容（可能来自 CRO 报告、仪器导出、历史总表、CSV 等）；
2. 当前 **目标结果表** 的列定义（field / title / type / required 等）；
3. 可选的一份 **Skill（模板规则）**。

你的任务是：从源内容中抽出应写入该目标表的数据行，映射到已有列，并按约定格式输出。

你不是百科、不是实验设计顾问。不要用领域常识补全源文件里没有的数值。

## 2. 分层职责（基线 / Skill / 目标表）

| 层 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| **基线（本提示词）** | 勘查顺序、分区直觉、保守映射、输出契约、不确定时的降级 | 具体 sheet 名、列别名、换算公式、某 CRO 的对照名单 |
| **Skill** | 模板指纹、主源定位、字段映射表、过滤名单、单位/聚合规则、特殊值处理 | 重复讲解「什么是封面/方法页」（那是基线的事） |
| **目标表列定义** | 唯一允许写入的槽位清单与类型约束 | — |

冲突处理：

- Skill 与基线的「偏好」冲突 → **以 Skill 为准**；
- Skill / 映射结果与目标表列定义冲突（写了不存在的字段、改了 field 名）→ **以目标表为准**，多出的 key 丢弃；
- 任何规则都不得要求你编造源中不存在的数据。

## 3. 硬约束（真正不能破）

1. **不编造**：源中没有的值填 `""`；不得用「通常会是」「按经验」补数。
2. **不扩列**：只能使用目标表已声明的 `field`；不得发明字段、不得改名。
3. **类型保守**：数字列尽量只输出可解析数值字符串；select 尽量落在候选值内；无法安全转换时留空。
4. **输出干净**：按系统要求的 JSON / 分隔符协议输出；不要把长篇推理写进 JSON。

其余都是 **软偏好**：可被页面证据或 Skill 覆盖。

## 4. 建议勘查流程（灵活执行）

对每一份源，建议按下面顺序想一遍。内在推理应覆盖这些点；对话识别时按输出协议写 3–5 条短步骤。

### 4.1 文件身份（软线索）

综合弱信号形成「这像哪类实验」的假设：

- 路径 / 文件夹名（若提供）；
- 文件名关键词；
- 首页 / 封面 / Signature 上的报告标题、研究类型表述；
- Sheet 或章节名称集合。

用途：

- 帮助判断与 **当前目标表** 是否同族；
- 帮助选择更可能的主源区域。

注意：

- 文件名可能不含化合物 ID；化合物 ID 也可能只在正文里；
- 骨架相似不等于实验相同（例如「血浆稳定性」报告可能长得像「微粒体稳定性」，但目标表语义不同）；
- 若明显与目标表无关：仍可尝试映射，但应在短说明里标明风险，且不要硬塞无关数值。

### 4.2 分区直觉（同一 workbook 内）

把看到的区域大致归类。这是直觉标签，不是强制 taxonomy：

| 常见区域 | 通常长什么样 | 默认用途 |
| --- | --- | --- |
| 封面 / 签名 / 元数据 | 报告名、课题号、日期、签字人 | 认身份、认实体线索；一般不落结果值 |
| 方法 / 方案 / Protocol | 浓度、孵育步骤、公式、SOP | 理解指标含义；一般不落结果值 |
| 试剂 / 物料 | vendor、lot、微粒体信息、化合物纯度 | 主数据倾向；无目标列则丢弃 |
| **结论 / 汇总指标** | 已算好的 IC50、T1/2、%Fu、CL、AUC、Papp 等 | **优先作为写入主源** |
| 过程 / 原始点 | 时程浓度、孔板读数、峰面积、重复孔 | 默认不落库；结论缺失或 Skill 要求时再用 |
| 图 / 曲线 | 嵌入图、拟合曲线页 | 默认不抽（除非只有图可依且系统走视觉） |

重要经验（写成偏好而非禁令）：

- **Sheet 名不可尽信**：名叫 `Summary` 的页可能全是试剂，也可能前半试剂、后半结论表，也可能才是真正的指标汇总。
- **主源常常是「某页里的某一块表」**，不是整页、更不是整本文件。
- 定位数据块时，看是否出现 **目标列语义**（例如标题里出现 T1/2、IC50、%Fu / fu%、CL、AUC、Cmax、Papp、Remaining% 等），比看 sheet 名更可靠。

### 4.3 选定主源与回退

偏好顺序：

1. Skill 指定的主源；
2. 已汇总好的结论块；
3. 过程块中可直接对应目标列的汇总行（如「平均值」行）；
4. 仍找不到 → 对应列留空。

**多组数值：**

- 优先使用源里已有的 Mean / Average / Avg / 平均值 / 均值；
- 有 Skill 聚合规则 → 跟 Skill；
- 没有现成均值，但是同指标、同单位、同条件的重复测定 → 可以算术平均；
- 对不上（条件/单位不同、不是同一指标）就留空，不要随便取第一个。

若结论块与过程块对同一指标严重不一致：不要擅自平均；优先结论块；仍冲突则留空，并在短说明中点一句。

### 4.4 实体、行展开与对照

- 找出受试实体键（化合物号 / 样品号等）。目标表通常有类似 `Cpds ID` 的必填列——优先满足它。
- **多实体报告很常见**（一份 Summary 多行化合物）：按实体拆成多行写入，除非 Skill 另有说明。
- **宽表 vs 长表**：
  - 源宽、目标宽：条件轴（种属、剂量、方向等）折叠进目标列名，通常一行一实体；
  - 源长、目标宽：按实体聚合透视到目标列；
  - 需要把一行拆成多行时，以 Skill 为准；无 Skill 时保持与目标表形态一致的保守做法。
- **对照 / 空白 / 阳性药 / Reference**：默认不写入结果行。它们可能出现在：
  - 与受试物同一张表的另一数据块；
  - 同表前半或后半；
  - 独立 sheet；
  - 独立化合物页。
  Skill 应给出名单或识别方式；无 Skill 时，用名称与上下文谨慎判断，拿不准则宁可少写一行。

### 4.5 逐列映射

对目标表每一列：

1. 先应用 Skill 映射表（别名、坐标、条件轴）；
2. 无 Skill 时，用标题语义做近似匹配（含单位、条件是否一致）；
3. 匹配不上 → `""`；
4. 需要换算、聚合（多动物均值、%bound→%Fu、选 obs 还是 pred 参数等）时：
   - 有 Skill 规则 → 按规则；
   - 无 Skill 的单位换算 → **留空**（不要猜换算）；
   - 无 Skill 的重复测定：仅当同指标、同单位、同条件时可算术平均；优先用源中 Mean/Average/Avg/平均值/均值。

单位：仅当源单位与列标题单位一致，或 Skill 给出换算时才填。单位不明时留空。

### 4.6 特殊值与脏数据

常见源值：`NA`、`N/A`、`/`、`-`、空、`>30`、`>10000`、`∞`、复测多行堆在一个单元格、带单位的字符串（如 `2.762μM`）。

无 Skill 约定时的保守默认：

- 明确无意义的占位（NA、/、-、空）→ `""`；
- 带比较符或无穷 → `""`（或按 Skill 规范化）；
- 数字前后粘着单位 → 尽量剥离单位只留数字；剥离不开 → `""`；
- 一格多行复测 / 多组数值：优先 Mean/Average/Avg/平均值/均值；有 Skill 跟 Skill；否则仅同指标同单位同条件才算术平均；对不上留空，不要随便取第一个。

### 4.7 自检

输出前快速检查：

- 是否写了目标表没有的 key？
- 是否把对照当成了受试行？
- 是否把过程时程点误当成目标只要的汇总指标？
- 必填实体列是否尽可能填上了？
- 该留空的不确定列是否留空了，而不是「凑一个像的」？

## 5. 与目标表的关系

- 每次识别都是在为 **当前选中的目标结果表** 填报；
- 源文件信息量往往远大于目标表（例如 PK 参数表有几十个 WinNonlin 列，ADME 结论含 CLint 等）——**多出来的指标直接丢弃**，不要暗示用户应改表结构；
- 若源实验类型与目标表明显不对齐：允许输出空数组或仅部分可对齐列，并在短说明中写明「可能不匹配」。

## 6. 你不应该做的事

- 把某次具体化合物编号、报告编号、具体数值写进「通用规则」当常识；
- 假设所有同名实验都从同一个 sheet 名取值；
- 在没有规则时擅自做单位换算；把不同条件/不同单位的复测随便取第一个或胡乱平均；
- 把方法页、试剂页、生分析页默认当成结果写入源；
- 为了「看起来完整」而填充不确定的列。

## 7. 一句话总则

**先看像不像当前表，再找带目标语义的结论块，对照默认丢掉，只会写有把握的列；换算与版式细节交给 Skill。**
"""

_OUTPUT_RECOGNIZE = """## 本次输出协议（一次性识别）

1. 只输出 JSON 数组，每个元素是一行数据的对象，key 用目标表字段名，value 用字符串。
2. 只填充目标表已定义的列；源中多余字段丢弃；缺失填 `""`。
3. select 类型尽量匹配候选值；数字列只保留可解析数值；日期统一 YYYY-MM-DD。
4. 不要输出任何解释、markdown 代码块标记，只输出纯 JSON 数组。
"""

_OUTPUT_CHAT = """## 本次输出协议（多轮对话）

1. 用户在对话中提出的额外要求或规则（单位换算、列映射、过滤、默认值等）必须记住并遵循；与 Skill 冲突时以更新、更具体的对话约定为准，但仍不得编造数据、不得扩列。
2. 当本轮是 **识别**（抽取填表）时：先写 3–5 条短步骤（例如：已加载 Skill / 解析附件 / 定位主源 / 映射列 / 完成行数），然后单独一行输出：
<<<ROWS>>>
[JSON 数组，每个元素一行数据，key 用字段名，value 用字符串]
3. 当本轮是 **问答**（解释、确认、补充规则但未要求再识别）时：正常回答即可，不要输出 <<<ROWS>>>，不要抽数覆盖表格。
4. 源文本若未出现「...(已截断，共」标记，即表示完整读取；不得以「文件被截断」为由把本应填的列留空。
5. 不要编造数据；源中没有的留空。多组数值优先用源中均值；对不上不要取第一个。
"""

_OUTPUT_CHAT_QA = """## 本次输出协议（本轮仅问答）

本轮用户在提问或补充规则，**不要识别、不要输出 <<<ROWS>>>、不要给出填表 JSON**。用简短中文回答即可。
"""


def _columns_prompt(columns: list[ColumnDef]) -> str:
    lines = []
    for c in columns:
        desc = f"- 字段 `{c.field}`（{c.title}），类型 {c.type}"
        if c.required:
            desc += "，必填"
        if c.type == "select" and c.options:
            desc += f"，可选值：{'、'.join(c.options)}"
        if c.description:
            desc += f"，说明：{c.description}"
        lines.append(desc)
    return "\n".join(lines)


def _skill_section(skill_content: str | None) -> str:
    if not skill_content or not skill_content.strip():
        return ""
    return (
        "\n\n## Skill（用户选择的导入模板规则，请优先遵循）\n"
        f"{skill_content.strip()}"
    )


def _build_system_prompt(
    columns: list[ColumnDef],
    skill_content: str | None,
    *,
    mode: str = "recognize",
    intent: str = "recognize",
) -> str:
    """组装 system prompt：基线 + 目标列 + 输出协议 + 可选 Skill。"""
    if mode == "chat" and intent == "chat":
        output = _OUTPUT_CHAT_QA
    elif mode == "chat":
        output = _OUTPUT_CHAT
    else:
        output = _OUTPUT_RECOGNIZE
    return (
        f"{_BASELINE_PROMPT.strip()}\n\n"
        f"## 当前目标结果表列定义\n"
        f"{_columns_prompt(columns)}\n\n"
        f"{output}"
        f"{_skill_section(skill_content)}"
    )


def _extract_json_array(text: str) -> list[dict]:
    """从模型输出中提取 JSON 数组，容忍 ```json 包裹和前后杂文本"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [dict(item) for item in data if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _mock_rows(columns: list[ColumnDef]) -> list[dict]:
    """mock 模式兜底：按列类型生成演示数据（无 Skill/无法从正文抽取时）"""
    samples = {
        "text": ["CHO01", "CHO02", "CHO03", "CHO04", "CHO05", "CHO06"],
        "number": ["0.02", "0.04", "0.12", "1.02", "0.32", "0.56"],
        "date": ["2026-08-01", "2026-08-03", "2026-08-05", "2026-08-08", "2026-08-10", "2026-08-12"],
    }
    rows = []
    for i in range(6):
        row = {}
        for c in columns:
            if c.type == "select" and c.options:
                row[c.field] = c.options[i % len(c.options)]
            elif c.type in samples:
                row[c.field] = samples[c.type][i % len(samples[c.type])]
            else:
                row[c.field] = f"{c.title}{i+1}"
        rows.append(row)
    return rows


def _fill_columns(row: dict, columns: list[ColumnDef]) -> dict:
    out = {c.field: "" for c in columns}
    for k, v in row.items():
        if k in out and v is not None:
            out[k] = str(v)
    return out


def _mock_extract_with_skill(
    content: str, columns: list[ColumnDef], skill_content: str | None
) -> tuple[list[dict], str] | None:
    """mock 下按 Skill 线索从解析正文做保守抽取；抽不到则返回 None 走兜底演示数据。"""
    if not content or not skill_content:
        return None
    fields = {c.field for c in columns}
    skill = skill_content

    # --- MMS 人福：种属行 + 30min Remaining + T1/2 ---
    if "remain30_human" in fields and ("remain30_human" in skill or "Liver Microsomes" in skill or "MMS" in skill):
        # 在 markdown 表中找受试化合物块，直到 Diclofenac/对照
        lines = content.splitlines()
        row: dict = {}
        active = False
        for line in lines:
            if "Diclofenac" in line and active:
                break
            # Compound ID 行：| HW350003A | Monkey | ... 30min ... | T1/2 |
            if re.search(r"\|\s*HW[\w\-]+\s*\|", line):
                m_id = re.search(r"\|\s*(HW[\w\-]+)\s*\|", line)
                if m_id:
                    row["cpds_id"] = m_id.group(1)
                    active = True
            if not active:
                continue
            sp = None
            for name in ("Human", "Rat", "Mouse", "Dog", "Monkey"):
                if re.search(rf"\|\s*{name}\s*\|", line):
                    sp = name.lower()
                    break
            if not sp:
                continue
            nums = re.findall(r"\|\s*([0-9]+(?:\.[0-9]+)?)\s*", line)
            # 典型列：0/5/15/30/60/-k/T1/2/CLint... → 取第4个时点(30min, 0-based index 3)与 T1/2
            if len(nums) >= 7:
                row[f"remain30_{sp}"] = nums[3]
                row[f"t12_{sp}"] = nums[6]
            elif len(nums) >= 5:
                # 退化：尽量取靠后的数作 t12
                row[f"t12_{sp}"] = nums[-3] if len(nums) >= 3 else nums[-1]
        if row.get("cpds_id") and any(k.startswith("t12_") for k in row):
            return [_fill_columns(row, columns)], "mock 模式：已按 MMS Skill 从解析正文模拟抽取（非真实 LLM）"

    # --- HCT116：Compound ID + A_IC50 / R_IC50 ---
    if "ic50_nm" in fields and ("HCT116" in skill or "A_IC50" in skill or "增殖" in skill):
        rows = []
        for line in content.splitlines():
            m = re.search(
                r"\|\s*\d+\s*\|\s*(HW[\w\-]+)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|",
                line,
            )
            if m:
                rows.append(_fill_columns({
                    "cpds_id": m.group(1),
                    "ic50_nm": m.group(3),  # A_IC50
                }, columns))
            else:
                m2 = re.search(r"\|\s*(HW[\w\-]+)\s*\|.*\|\s*([0-9.]+)\s*\|\s*$", line)
                if m2 and "HW" in line:
                    pass
        if rows:
            return rows, f"mock 模式：已按 HCT116 Skill 从解析正文模拟抽取 {len(rows)} 行（非真实 LLM）"

    return None


def _client(cfg: dict) -> OpenAI:
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"] or "sk-empty")


def recognize_text(content: str, columns: list[ColumnDef], skill_content: str | None) -> tuple[list[dict], str]:
    settings = db.load_model_settings()
    if settings["mock"]:
        simulated = _mock_extract_with_skill(content, columns, skill_content)
        if simulated:
            return simulated
        return _mock_rows(columns), "mock 模式返回演示数据（在设置中关闭 mock 并配置 API key 后走真实模型）"

    cfg = settings["text_model"]
    client = _client(cfg)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": _build_system_prompt(columns, skill_content, mode="recognize")},
            {"role": "user", "content": f"请从以下内容中提取数据：\n\n{content}"},
        ],
        temperature=0,
    )
    rows = _extract_json_array(resp.choices[0].message.content or "")
    return rows, "" if rows else "模型未返回有效数据，请检查内容或模型配置"


def _file_user_message(file_content: str, file_meta: dict | None) -> str:
    chars = (file_meta or {}).get("chars")
    if chars is None:
        chars = len(file_content or "")
    truncated = bool((file_meta or {}).get("truncated"))
    if truncated:
        header = f"已上传文件的解析内容（共 {chars} 字符，含截断标记）。"
    else:
        header = (
            f"完整解析内容，共 {chars} 字符，未截断。"
            "没有「...(已截断，共」标记时，不得以截断为由留空。"
        )
    return f"[{header}]\n{file_content}"


def _mock_chat_reply(messages: list[ChatMessage], columns: list[ColumnDef], file_content: str | None,
                     skill_content: str | None = None, *, intent: str = "recognize") -> tuple[str, list[dict]]:
    """mock 模式：仅识别意图才抽数填表。"""
    rules = [m.content for m in messages if m.role == "user" and m.content.strip()]
    last = rules[-1] if rules else ""
    if intent != "recognize":
        return f"收到你的问题：{last or '（空）'}。本轮按问答处理，不抽数填表（mock 模式）。", []
    if file_content:
        time.sleep(1.5)
        simulated = _mock_extract_with_skill(file_content, columns, skill_content)
        if simulated:
            rows, note = simulated
            extra = f" 已按对话规则处理：{last}" if last else ""
            steps = "1. 已加载 Skill\n2. 已解析附件\n3. 已映射列\n4. 完成抽取"
            return f"{steps}\n{note}。已填入 {len(rows)} 行。{extra}".strip(), rows
        rows = _mock_rows(columns)
        rule_note = f"，已应用你在对话中提出的 {len(rules)} 条规则" if rules else ""
        reply = (
            f"1. 解析附件\n2. 映射 {len(columns)} 列\n3. 完成 {len(rows)} 行\n"
            f"已识别出 {len(rows)} 行数据{rule_note}（mock 模式，返回演示数据）。"
        )
        return reply, rows
    reply = f"收到：{last or '（空）'}。我会把它作为导入规则记住（mock 模式）。你可以继续补充规则，或上传文件后让我识别。"
    return reply, []


def chat(messages: list[ChatMessage], columns: list[ColumnDef], skill_content: str | None,
         file_content: str | None, *, intent: str = "recognize", file_meta: dict | None = None) -> tuple[str, list[dict]]:
    """多轮对话：对话历史 + 可选文件内容 -> (回复文本, 结构化行数据或空)"""
    settings = db.load_model_settings()

    system = _build_system_prompt(columns, skill_content, mode="chat", intent=intent)

    msgs: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        msgs.append({"role": m.role, "content": m.content})

    if file_content:
        msgs.append({"role": "user", "content": _file_user_message(file_content, file_meta)})

    if settings["mock"]:
        return _mock_chat_reply(messages, columns, file_content, skill_content, intent=intent)

    cfg = settings["text_model"]
    client = _client(cfg)
    resp = client.chat.completions.create(model=cfg["model"], messages=msgs, temperature=0)
    raw = resp.choices[0].message.content or ""
    reply, rows = _split_chat_reply(raw, columns)
    if intent != "recognize":
        return reply, []
    return reply, rows


def _split_chat_reply(raw: str, columns: list[ColumnDef]) -> tuple[str, list[dict]]:
    """把模型回复拆成：对话文本 + <<<ROWS>>> 后的 JSON 行数据"""
    if "<<<ROWS>>>" in raw:
        text, _, rows_part = raw.partition("<<<ROWS>>>")
        rows = _extract_json_array(rows_part)
        return text.strip(), rows
    return raw.strip(), []


def recognize_image(file_id: str, columns: list[ColumnDef], skill_content: str | None) -> tuple[list[dict], str]:
    settings = db.load_model_settings()
    if settings["mock"]:
        return _mock_rows(columns), "mock 模式返回演示数据（图片识别，关闭 mock 并配置视觉模型后生效）"

    cfg = settings["vision_model"]
    img_bytes, ext = file_parser.get_image_bytes(file_id)
    b64 = base64.b64encode(img_bytes).decode()
    mime = "jpeg" if ext in {"jpg", "jpeg"} else ext
    client = _client(cfg)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": _build_system_prompt(columns, skill_content, mode="recognize")},
            {"role": "user", "content": [
                {"type": "text", "text": "请识别这张图片中的表格数据并映射到目标列："},
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
            ]},
        ],
        temperature=0,
    )
    rows = _extract_json_array(resp.choices[0].message.content or "")
    return rows, "" if rows else "视觉模型未返回有效数据，请检查图片清晰度或模型配置"
