# MMS · 3D BioOptima 版式

适用于 3D BioOptima（圣苏等）肝微粒体代谢稳定性报告。

## 匹配线索

- CoverPage 含 `3D BioOptima` 或「实验报告」+ 标题含 **肝微粒体代谢稳定性**
- 文件名含 `Stability in LMs` / `Stability_in_LMs`
- Sheet 常见：`CoverPage`, `Summary`, 以化合物 ID 命名的 sheet, `Midazolam`, `7-HC`, `Raw Data`, `Analytical Method`

**不要**用于人福 `D-RF-…-MMS-…` 英文 Signature 版式。

## 目标结果表

`MMS`

## 主源（注意：Summary 前半经常是试剂）

1. **T1/2（优先）**：`Summary` 页中出现表头类似 `化合物 | 种属 | k | T1/2 (min) | CLint…` 的 **小结表**（通常在试剂信息、孵育体系之后）。跳过前面的试剂/品牌/货号区。
2. **30 min Remaining%**：化合物 **同名 sheet**（如 `HW356009-P1`）中，按种属分块；取孵育时间 = **30** 的「原药剩余量%」；若有平行样，用已给出的平均值；没有平均值则按 Skill 要求对平行样算术平均（仅此场景允许平均）。

`Raw Data` / `Analytical Method` 不落库。

## 实体与过滤

- 实体：CoverPage「化合物」或小结表「化合物」列；文件名中的 `HW…` 可作辅助
- **丢弃**：`Midazolam`、`7-HC` 等对照 sheet 与小结表中的对照行
- 种属名可能是 Human/Monkey/Dog/Rat/Mouse 或中文；映射到目标列时统一到 human/rat/mouse/dog/monkey

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | 化合物 ID | 原样 |
| `t12_*` | Summary 小结表对应种属 `T1/2 (min)` | 数值；`NA`→`""` |
| `remain30_*` | 化合物 sheet 中该种属 30 min 原药剩余量% | 数值；缺失→`""` |

若某物种 T1/2 为 `NA` 但 30 min 有值：仍可只填 remain；反之亦然。

## 不映射

CLint 系列、k、对照数据、试剂信息

## 特殊值

- `NA` / `N/A` → `""`
- 无法解析 → `""`
