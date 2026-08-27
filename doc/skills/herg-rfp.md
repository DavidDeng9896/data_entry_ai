# hERG · RFP 手动膜片钳版式

手动膜片钳 hERG 报告（RFP）。

## 匹配线索

- 文件名含 `hERG` / `hERG assay`
- 封面标题含「手动膜片钳」+ `hERG`
- Sheet：`封面`, `Assay Summary`, `Protocol`, 阳性对照名 sheet（如 `Cisapride`）, 受试化合物名 sheet

## 目标结果表

`hERG`

## 主源

- **主源**：`Assay Summary` 中 `Compound ID | IC50` 小结
- 化合物同名 sheet 为浓度–抑制率过程数据，默认不落库

## 实体与过滤

- 实体：Assay Summary 的受试 Compound ID
- **丢弃**：Positive control（如 Cisapride）及其 sheet

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound ID | 原样 |
| `ic50_um` | IC50 单元格 | 剥离单位，统一为 **μM 数值**。若源为 `16.20nM` 这类对照单位，对照行本就不导入；受试物若以 nM 给出，则 `/1000` 转为 μM |

## 特殊值

- 带单位字符串：去掉单位后写入
- 空 / NA → `""`
- Note 备注文字不写入结果列
