# PK · 普瑞昇 WinNonlin「PK 参数」版式

小鼠 / 大鼠 / 比格犬 PK 检测报告（合肥中科普瑞昇等），中文 sheet：`封面` / `结果汇总` / `PK 参数` / …

同一版式服务多张目标表：**Mouse PK / Rat PK / Dog PK**——以封面物种与用户所选目标表对齐。

## 匹配线索

- 封面含「合肥中科普瑞昇」或同类；项目编号 `D-RF-…` / `DM-RF-…`
- 文件名含 `MPK` / `RPK` / `DPK` 检测报告
- Sheet 含：`封面`, `结果汇总`, `PK 参数`, `原始数据`, …

**不要**用于 3D BioOptima 英文/Cover 结构，或外部食蟹猴终稿版式（另补 Skill）。

## 目标结果表

按物种选择其一：

- 小鼠 → `Mouse PK`
- 大鼠 → `Rat PK`
- 比格犬 → `Dog PK`

封面或结果汇总标题中的物种必须与目标表一致，否则少填并说明不匹配。

## 主源

- **主源**：`PK 参数`（WinNonlin 宽表；含 IV / PO 分段）
- `结果汇总` 为血药浓度–时间过程表 → **不要**当 CL/AUC 主源
- 原始数据 / 标曲 / LC-MS 方法 → 不落库

## 实体与过滤

- 实体：封面「化合物名称」或 `PK 参数` 页左上化合物 ID
- 通常一份报告一个主测化合物 → 一行
- 多动物（sort=1,2,3…）：对需要的参数做 **算术平均**（仅同给药段、同剂量组内）

## 字段映射（列名以实际表头为准，按下表语义匹配）

IV 段（Dose 约 1 mg/kg，表头含 `IV`）：

| 目标字段（示例） | 源表头偏好 | 变换 |
| --- | --- | --- |
| `iv_1mpk_cl_l_h_kg` | `Cl_obs (L/h/kg)`（优于 Cl_pred） | 多动物均值 |
| `iv_1mpk_vss_l_kg` | `Vss_obs (L/kg)` | 均值 |
| `iv_1mpk_auc0_t_h_ng_ml` | `AUClast (h*ng/mL)`（优于 AUCINF，除非 Skill 修订） | 均值 |
| `iv_1mpk_t1_2_hr` | `HL_Lambda_z (h)` | 均值 |

PO 段：按目标表已有剂量列匹配（如 Mouse 的 10/30/100 mpk，Rat 10 mpk，Dog 5 mpk）。源 `Dose (mg/kg)` 必须对上目标列剂量，对不上的剂量组不填。

| 目标字段模式 | 源表头偏好 |
| --- | --- |
| `po_<dose>_cmax_ng_ml` | `Cmax (ng/mL)` |
| `po_<dose>_tmax_hr` | `Tmax (h)` |
| `po_<dose>_auc0_t_h_ng_ml` | `AUClast (h*ng/mL)` |
| `po_<dose>_t1_2_hr` | `HL_Lambda_z (h)` |
| `po_<dose>_pct_f` | 生物利用度 `%F` / `F` 相关列（若有）；没有 → `""` |

`cpds_id` ← 化合物 ID。

## 不映射

Rsq、Lambda_z、AUMC、MRT、大量 pred/obs 重复列中未被上表选中者。

## 特殊值

- 空 → `""`
- 聚合时跳过空值再平均；全空则 `""`
