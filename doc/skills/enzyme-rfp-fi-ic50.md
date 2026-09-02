# 酶活 IC50 · RFP WRN FI（ATP preincubation）版式

WRN 等生化抑制 IC50 报告（RFP / FI assay）。

## 匹配线索

- 文件名含 `WRN` + `FI_IC50` 或 `ATP preincubation_FI_IC50`
- Signature `Assay Name` 含 `WRN` + `FI` + `IC50`
- Sheet：`Signature`, `Assay summary`, `Assay protocol`, `Raw data analysis`

## 目标结果表

`Biochemical Activity (ADP-Glo)`

> 注：总表侧还有 unwinding 等其它生化表。本 Skill 仅当报告为该 FI/ATP preincubation 模板且用户选择了 ADP-Glo 表时使用。若用户选错目标表，应少填并提示不匹配。

## 读取范围

- 读取：`Signature`、`Assay summary`
- 跳过：`Assay protocol`、`Raw data analysis`

## 主源

- `Assay summary` 表（含 Compounds ID、IC50 (nM) 等）
- Raw / Protocol 不落库

## 实体与过滤

- 实体：`Compounds ID`
- **丢弃**：`Comments` 或上下文标明 `Reference` 的参考化合物行
- 多化合物 → 多行

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compounds ID | 原样 |
| `ic50_nm` | IC50 (nM) | 数值；`>10000` 等不等式 → `""` |
| `inhib_1000nm` / `inhib_20000nm` / `echelon_ic50_nm` | 本模板通常无 | `""` |

## 特殊值

- `>10000`、`>` 开头 → `""`
- 空 → `""`
