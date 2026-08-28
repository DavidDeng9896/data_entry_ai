# CYP inhibition · 人福 DDI 版式

人肝微粒体 CYP 抑制（DDI）报告，人福 `D-RF-…-DDI-…`。

## 匹配线索

- 文件名含 `-DDI-`
- Signature 标题含 `Inhibition of CYP2C9, CYP2D6, CYP3A4`（或同类 CYP 亚型列表）
- Sheet：`Signature`, `Summary`, `Materials`, `Study Design`, `Data`, …

## 目标结果表

`CYP inhibition`

## 主源

- `Summary` 中 IC50 汇总表（标题含 `IC50 values`）
- `Data` 页为浓度–剩余活性过程数据：仅当 Summary 缺某亚型 IC50 且 Skill 未禁止时才考虑；默认不从 Data 拟合 IC50

## 实体与过滤

- 实体：受试 Compound
- 丢弃：已知抑制剂阳性对照行（如各 CYP 的标准抑制剂）；只保留受试化合物行

## 字段映射

目标表同时有「10μM (%)」与「IC50 (μM)」两套列。本版式 Summary 通常直接给 IC50；若 Summary 只有 IC50：

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound | 原样 |
| `ic50_2c9` | CYP2C9 的 IC50 (μM) | 数值 |
| `ic50_2d6` | CYP2D6 | 数值 |
| `ic50_3a4_m` | CYP3A4（底物为 Midazolam / 标为 3A4 M 或同类） | 数值 |
| `ic50_3a4_t` | CYP3A4（底物为 Testosterone / 3A4 T） | 数值 |
| `pct_10um_*` | 若 Summary/Data 明确给出 10μM 剩余活性或抑制% | 按目标列语义填；没有则 `""` |

3A4 双底物务必按报告表头区分 M / T，不要合并。

## 特殊值

- `>x` 类不等式 → `""`（除非产品后续约定存文本；当前目标列为 number）
- NA → `""`
