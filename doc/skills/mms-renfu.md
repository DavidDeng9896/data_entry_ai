# MMS · 人福 D-RF 版式

适用于肝微粒体代谢稳定性（MMS）报告，人福 / 同类 `Signature + Summary + Materials + …` 英文结构。

## 匹配线索

- 文件名含 `-MMS-`，或 Report Number / 标题含 `MMS` / `Metabolic Stability` + `Liver Microsomes`
- Sheet 大致包含：`Signature`, `Summary`, `Materials`, `Study Design`, `Raw Data`
- Signature 中 Report Name 类似：*Metabolic Stability of \<ID\> in Human, Mouse, Rat, Dog, Monkey Liver Microsomes*

**不要**用于：标题为 Plasma Stability（PLS）、S9、3D BioOptima「Stability in LMs」中文封面版式（另有 Skill）。

## 目标结果表

`MMS`

## 读取范围

- 读取：`Signature`、`Summary`
- 跳过：`Raw Data`、`Materials`、`Study Design`

## 主源

- **主数据块**：`Summary` 中标题含 `Remaining percentage and metabolic stability` 的表（通常为 Table 2）
- **不要**用同页的 Scaling factors 表（Table 1）当结果
- `Raw Data` 仅作校验；默认不从 Raw 落库

## 实体与过滤

- 实体：`Compound ID`（合并单元格时向下填充理解）
- **丢弃**：`Diclofenac` 等阳性对照整块（对照名以报告为准，凡非受试化合物块均丢弃）
- 一行输出 = 一个受试 Compound ID（种属展开进列，不拆行）

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound ID | 原样字符串 |
| `remain30_human` | Species=Human 行，Percent Remaining 的 **30 min** 列 | 数值 |
| `remain30_rat` | Species=Rat，30 min | 数值 |
| `remain30_mouse` | Species=Mouse，30 min | 数值 |
| `remain30_dog` | Species=Dog，30 min | 数值 |
| `remain30_monkey` | Species=Monkey，30 min | 数值 |
| `t12_human` | Human 行，`T1/2 (minute)` | 数值 |
| `t12_rat` | Rat，`T1/2 (minute)` | 数值 |
| `t12_mouse` | Mouse，`T1/2 (minute)` | 数值 |
| `t12_dog` | Dog，`T1/2 (minute)` | 数值 |
| `t12_monkey` | Monkey，`T1/2 (minute)` | 数值 |

## 不映射（目标表无列）

`-k`、`CLint(mic)`、`CLint (mL/min/kg)`、0/5/15/60 min 除 30 min 外的 Remaining%、Materials 中的 MW/Lot

## 特殊值

- 空 / 缺失 → `""`
- 无穷或无法解析 → `""`
