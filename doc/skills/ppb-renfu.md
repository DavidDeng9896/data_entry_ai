# PPB · 人福 D-RF 版式

血浆蛋白结合（PPB）报告，人福 `D-RF-…-PPB-…` 结构。

## 匹配线索

- 文件名含 `-PPB-`
- Signature 标题含 `plasma protein binding`
- Sheet：`Signature`, `Summary`, `Materials`, `Study Design`, `Raw Data`, …

## 目标结果表

`PPB %Fu`

## 主源

- `Summary` 中 **受试化合物** 的汇总表（通常 Table 2，标题含 test compound）
- **不要**把 warfarin 等对照表（通常 Table 1）写入结果行

## 实体与过滤

- 实体：受试表 `Compound` / Compound ID
- 丢弃：Warfarin 等对照整表

## 字段映射（注意换算）

本版式给出的是 **%bound**（结合率），目标表要 **%Fu**（游离分数）。

| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | Compound | 原样 |
| `fu_human` | Species=Human 的 %bound（多 replicate 时用 mean；若只有单点 %bound 则用该值；若有 `%bound mean` 列优先） | **`%Fu = 100 - %bound`** |
| `fu_rat` / `fu_mouse` / `fu_dog` / `fu_monkey` | 同上按种属 | 同上 |

若某物种 %bound 为 `/` 或无法计算 → 对应 `fu_*` 为 `""`。

## 不映射

Receiver/Donor 峰面积比、Materials、Raw Data

## 特殊值

- `/`、空、NA → `""`
- 换算后保留合理数值字符串即可（不必强行固定小数位）
