# HCT116 细胞增殖 · 检测报告版式

HCT116 细胞增殖抑制检测报告（多化合物 Summary）。

## 匹配线索

- 文件名含 `HCT116细胞增殖抑制检测报告` 或标题 `HCT116 Cell Proliferation` / `HCT116 proliferation Assay`
- Sheet：`Signature`, `Summary`, `Protocol`, `Compound Information`, `Raw Data IC50`, `IC50 Curve`

## 目标结果表

`SW48/HCT116增殖试验`

> 注：当前目标表列偏「宽指标」（%inhibition @ top / @10μM / IC50）。本版式 Summary 通常直接给 **IC50**；%inhibition 条件列若源中无对应汇总，则留空。

## 读取范围

- 读取：`Signature`、`Summary`
- 跳过：`Raw Data IC50`、`IC50 Curve`、`Protocol`

## 主源

- **主源**：`Summary` 中 `Summary-HCT116` 表（含 Compound ID、R_IC50 / A_IC50 等）
- `Raw Data IC50` / `IC50 Curve`：默认不落库

## 实体与过滤

- 一行一个 `Compound ID`（一份报告常含多个化合物 → 多行输出）
- 无额外阳性对照行时无需过滤；若出现明确 Reference 且非项目化合物，丢弃

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound ID | 原样 |
| `ic50_nm` | 优先 `A_IC50, nM`；若无则 `R_IC50, nM` | 数值（单位已是 nM） |
| `inhib_top` | 若 Summary 无对应 %inhibition @ top | 默认 `""` |
| `inhib_10um` | 若无 10μM 抑制率汇总 | 默认 `""` |

不要从曲线图臆造 %inhibition。

## 特殊值

- 空 → `""`
- 非数值 IC50 → `""`
