# Thermodynamic Solubility · Pharmaron / RFY 版式

热力学溶解度报告（FaSSGF / FaSSIF 或 FeSSIF / PBS）。

## 匹配线索

- 文件名含 `Thermodynamic Solubility` 或 `ADME-RFY-Thermodynamic Solubility`
- Signature 标题含 `Thermodynamic Solubility` + 介质名（FaSSGF、FaSSIF、PBS 等）
- Sheet：`Signature`, `Summary`, `Materials`, `Study Design`, …（可能无 Raw Data）

## 目标结果表

`Thermodynamic Solubility`

## 主源

- `Summary` 中按介质给出的溶解度表
- 优先使用 **μg/mL** 列（与目标表单位一致）；不要误用 μM 列去填 μg/mL 槽

## 实体与过滤

- 实体：受试 Compound ID
- 丢弃：control compounds 行

## 字段映射

| 目标字段 | 源（按介质标签匹配，勿死记列号） | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound ID | 原样 |
| `fassgf_ph16` | FaSSGF（约 pH 1.6）溶解度 μg/mL | 数值 |
| `fessif_ph65` | FeSSIF 或 FaSSIF（约 pH 6.5，以报告介质名为准）μg/mL | 数值 |
| `pbs_ph74` | PBS pH 7.4 μg/mL | 数值 |

若报告写作 FaSSIF 而目标列名为 FeSSIF：仍映射到 `fessif_ph65`，并在短说明中注明源标签为 FaSSIF。

## 不映射

μM 列（除非目标表将来增加）、对照化合物

## 特殊值

- 空 / NA → `""`
