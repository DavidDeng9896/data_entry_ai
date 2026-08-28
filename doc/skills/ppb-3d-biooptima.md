# PPB · 3D BioOptima 版式

3D BioOptima 血浆蛋白结合率报告。

## 匹配线索

- CoverPage 含 `3D BioOptima`，标题含 **血浆** + **蛋白结合**
- 文件名含 `_PPB_` / `PPB_results`
- Sheet 常见：`CoverPage`, `Summary`, 化合物同名 sheet, `Controls`, `Raw data`, …

## 目标结果表

`PPB %Fu`

## 主源

- `Summary` 中同时列出对照与受试物、分种属给出 **`fu%`** 的表
- 直接使用 **fu%** 列（不要用 fb% 再换算，除非 fu% 缺失且 Skill 后续版本明确允许 `100-fb%`）

## 实体与过滤

- 实体：受试化合物行（与 Cover「受试化合物」一致）
- **丢弃**：华法林、对乙酰氨基酚等对照行

## 字段映射

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | 化合物名 | 原样 |
| `fu_human` | 人 / Human 列下 `fu%` | 数值 |
| `fu_monkey` | 食蟹猴 / Monkey `fu%` | 数值 |
| `fu_dog` | 比格犬 / Dog `fu%` | 数值 |
| `fu_rat` | 大鼠 / Rat `fu%`（若表中有） | 数值 |
| `fu_mouse` | 小鼠 / Mouse `fu%`（若表中有） | 数值 |

种属在表头中的左右分块位置以实际表头为准；按种属中文/英文标签对齐，不要按固定列号死记。

## 不映射

回收率 %、稳定性 %、fb%、过程峰面积定义说明

## 特殊值

- `-` / 空 / NA → `""`
