# 数据导入工具 · Spec 

> **本文状态：** v0.4.24。相对 v0.4.23：新增 §16 多实体报告导入（可复用形状 + 角色选择器 + `multi_entity_report` 配方）；附录 F 增步骤；第二部分 L.4 仅作实例示意（不绑死表头）。
> **产品：** **库配导入**——与化合物库一起销售的数据导入功能；开通化合物库后才能使用。抗体导入复用同一套流程，但单独打包，不包含在本 SKU 中。
> **工具核心流程：** 文件解析 → 模板匹配 → 确认环节 → observation/master 双通道 → 关联 Sample → Ingress/注册写入。具体 assay 表 / `attr_key` 清单放在 ImportProfile 中配置（见第二部分）。
> **数据存储：** 以目标库为准（本 SKU 为化合物库）。ImportSession 只记录导入过程，不存储最终数据。ELN 可选同步方法/附件/链接，观测数据以库为准（**导入目标位置勾选**）。
> **上游参考：** [CONTEXT.md](./CONTEXT.md)、[MolRelay-AI-spec-v2.1.md](./MolRelay-AI-spec-v2.1.md)、[MolRelay-AI-roadmap.md](./MolRelay-AI-roadmap.md)。
> **开源依赖（P2）：** [Benchling allotropy](https://github.com/Benchling-Open-Source/allotropy)（MIT）· 支持列表 [SUPPORTED_INSTRUMENT_SOFTWARE.adoc](https://github.com/Benchling-Open-Source/allotropy/blob/main/SUPPORTED_INSTRUMENT_SOFTWARE.adoc)

---

## 版本说明


| 版本              | 要点                                                                                      |
| --------------- | --------------------------------------------------------------------------------------- |
| **v0.4.24（本版）** | §16 多实体报告导入：一份报告 → N Sample 观测；角色选择器与版式模板分层；配方 `multi_entity_report`；L.4 实例仅示意 |
| v0.4.23         | 附录 K · LLM 数据安全：五层防线（不调 · 脱敏 · 策略 · 隔离 · 审计）；LLM 接触数据分级表；客户应答框架 |
| v0.4.22         | 并发冲突 · content_hash 规范化 · LLM 上下文最小化 · IntentHint 注入防护 · 模板冷启动/可见性 · 超时限额 · 降级策略 · 边界处理（空文件/编码/日期/精度）· 多候选 UX · 部分提交重试 · 导入历史视图 · 运行时遥测 · 错误码体系（附录 J）|
| v0.4.21         | ContentClass · IntentPreset · 能力白名单编排 · 计划卡 · IntentHint 权威序；Demo 板块清单后置 |
| v0.4.20         | 库配导入产品定位；ImportProfile 挂载；单文件「工具 / 库适配」分区；多入口 · 落点勾选 · 许可绑库 |
| v0.4.18         | 用语：去掉别扭中文，改成好懂说法；规则同 v0.4.17                                                            |
| v0.4.17         | 附录 H：allotropy 仪器轨 · 用法 · AsmMapper · 与模板/AI 轨怎么分工                                      |
| v0.4.16         | §8.4 导入模式与样本策略；附录 F 步骤/配方；附录 G ELN 回写                                                   |
| v0.4.15         | 用语：部分匹配 / 对不上 替代 软破版 / 硬破版；正文去拗口说法                                                      |
| v0.4.14         | §0.3 / §7.3：字段映射确认卡列义；禁止同名直通；样本键列走卡 2                                                   |
| v0.4.13         | 全文去 AI 腔润色；规则与 v0.4.12 一致                                                               |
| v0.4.12         | §6.1 / §11：ImportPrimarySource 单主源 + 只读附件（grill 决议 A）                                   |
| v0.4.11         | §3.2 / §6.2：P0 禁止 either；通道仅 observation                                                |
| v0.4.10         | §10.5：ImportPartialCommit 默认尽力而为 + 可选原子（grill 决议 A）                                     |
| v0.4.9          | §10.4：再导入冲突与显式 supersede（grill 决议 A）                                                    |
| v0.4.8          | §7.5：单位/轴/StudyRef 规则（grill 决议 A）                                                       |
| v0.4.7          | §12：导入完成 Notice + 去对照预填；禁止自动对照/Feedback（grill 决议 A）                                     |
| v0.4.6          | §7.4：TemplatePublish 权限/作用域/升版规则（grill 决议 A）                                            |
| v0.4.5          | §7.0.1：模板匹配签名；对不上则整份 AI；部分匹配则规则+未知列混合（grill 决议 A）                                       |
| v0.4.4          | §7.3：导入确认 = C2 特化；与 CONTEXT「导入确认」对齐；禁止标量双确认 / 图谱跳过 C2                                   |
| v0.4.3          | §1.4 / §7.0：规则轨 + AI 轨分流；确认通过的映射须沉淀为 ImportTemplate；上传 UX 区分快/慢路径                       |
| v0.4.2          | 附录 E：Benchling Data Import 对照                                                           |
| v0.4.1          | 终点改为化合物库/抗体库；TargetView → LibraryProjection；RowKeyResolver → SampleResolver；双写通道；库写入对照表 |
| v0.4            | Scene Pack.import · ObservationIngress · P0 湿实验竖切                                       |
| v0.3            | DomainPack / TargetView / CMO（探索）                                                       |
| v0.2–v0.1       | 分桶 · 轴侦查 · 三层定位 · 两卡                                                                    |


**标注：** Must = P0 必做；Should = 尽量做；Later = P1+ 占位

---

## 目录

### 第一部分 · 通用导入工具

0. [产品定位与名词](#0-产品定位与名词)
1. [设计原则](#1-设计原则与平台对齐)
2. [P0 边界（工具竖切）](#2-p0-边界竖切)
3. [配置层：ImportProfile](#3-配置层importprofile)
4. [从文件列对到投影槽](#4-从文件列对到库字段含查轴)
5. [LibraryProjection（投影槽清单）](#5-libraryprojection库投影原-targetview)
6. [数据模型与双写通道](#6-数据模型与双写通道)
7. [导入流程与确认](#7-agent-流水线与确认闸)
8. [SampleResolver](#8-sampleresolver原-rowkeyresolver)
9. [用户交互与多入口](#9-用户交互)
10. [归属、审计、回滚](#10-归属审计回滚)
11. [文件格式](#11-文件格式)
12. [查询与下游](#12-查询与下游)
13. [验收指标（工具）](#13-验收指标)
14. [分期路线](#14-分期路线)
15. [与既有 spec 接口](#15-与既有-spec-接口)
16. [多实体报告导入](#16-多实体报告导入)

- [附录 A · 版本迁移](#附录-a--版本迁移)
- [附录 D · Later 占位](#附录-d--later-占位)
- [附录 E · Benchling Data Import 对照](#附录-e--benchling-data-import-对照)
- [附录 F · 导入模式 · 样本策略 · 流程配方](#附录-f--导入模式--样本策略--流程配方)
- [附录 G · ELN 回写与落点勾选](#附录-g--eln-回写)
- [附录 H · 仪器解析（allotropy）](#附录-h--仪器解析allotropy)
- [附录 I · PDF / 图片解析](#附录-i--pdf--图片解析)
- [附录 J · 错误码清单](#附录-j--错误码清单)
- [附录 K · LLM 数据安全](#附录-k--llm-数据安全)

### 第二部分 · 化合物库适配（内容可后置）

- [§L · 适配说明与 Demo 投影](#l-化合物库适配说明)
- [§L.4 · 多实体报告 · 实例示意（非绑定）](#l4-多实体报告--实例示意非绑定)
- [附录 B · EO035 → 化合物库验收剧本](#附录-b--eo035--化合物库验收剧本)
- [附录 C · 库写入对照表（主数据 vs 观测）](#附录-c--库写入对照表主数据-vs-观测)

---

# 第一部分 · 通用导入工具

## 0. 产品定位与名词

### 0.0 库配导入（Must）

| 项 | 决议 |
| --- | --- |
| 商业 | 与**化合物库**同售；导入是进库信息入口，非独立导入 SaaS |
| 许可 | **化合物库开通后**才开放导入（含设计台等入口的同一检查） |
| SKU | 本 Spec 商业范围 = 化合物库 + 库配导入；抗体另打包，管线可复用 |
| 配置 | 配置以库/租户级 **ImportProfile** 为准；不绑定某个 AI/工作台「业务场景」才能用；Scene Pack 可引用 |
| 多入口 | 库列表/详情为主入口；设计台「导到此分子」、可选导入工作台页、日后 ELN 触发 = 同一流程 |
| 目标位置 | 结构化观测数据**必须**写入库；ELN 为可选同步（方法/附件/链接）。界面可像「选位置」，底层不是库/ELN 二选一 |
| 投影交付 | 标准 Demo 可演示；按客户需求增删改由**我方实施**配置；不开放客户自助改投影（P0） |
| 工具 vs 内容 | 工具核心流程见上；具体表/`attr_key` 见**第二部分**（可后置） |
| 上传三轴 | **ContentClass**（内容板块）· **ArtifactKind**（主源类型）· **ImportMode**；不要揉成一个「文件类型」下拉 |
| 能力编排 | 步骤白名单（附录 F）；LLM 只提议流程配置，确定性引擎执行；命中模板则**跳过**编排 LLM（§1.4） |
| 意图预置 | **ImportIntentPreset** 绑定 ContentClass；字段关注清单 ⊆ 投影；用户补充为弱信号 IntentHint |
| 多实体报告 | 一份主源含「结果表多行 + 方法/证据区」时，走 **多实体报告导入**（§16）：行展开 → N Sample 锚点 → 库观测；版式细节只进 ImportTemplate，不写死进内核 |

术语见 CONTEXT：**库配导入** · **导入多入口** · **导入目标位置勾选** · **导入配置挂载** · **导入工具核心流程** · **导入投影交付** · **内容板块** · **导入意图预置** · **导入计划卡** · **意图提示** · **多实体报告导入**。

### 0.1 存储链路（Must）

```
源文件
  → 科学数据管理（ImportSession / Artifact / 审计）
  → 关联到 Sample（化合物库分子 MR-xxxx / 抗体 Registry）
  → 结构化写入（主数据 或 ObservedValue）
  → 库详情 / 工作台读取（以库为准，不在导入缓存中）
```

### 0.2 两类输入（Must）


| 类别             | 含义                                    | 落点                                   |
| -------------- | ------------------------------------- | ------------------------------------ |
| **A · 库投影参照**  | 可选：用户指认「字段清单 / 总表样例」帮助生成或校验导入映射 | 不当作权威库；以库 schema + Scene Pack 属性目录为准 |
| **B · Source** | assay 报告 / 注册表 / 序列表 / ELN 导出等        | 解析后写入库主数据或观测                         |


### 0.3 字段怎么对应（Must）

对应关系：

`[源文件 · sheet · 表 · 列] → [库内 Sample × 属性槽或主数据字段]` → 固化为 `ImportTemplate`。

**字段映射**（确认卡 1）只回答：文件里这一列要不要写、写到库的哪个槽。  
**样本对齐**（确认卡 2）只回答：这一行对应哪个 `MR-xxxx` / Registry ID。

化合物内部编号这类样本键不要写成观测属性，交给卡 2 处理。

### 0.4 常见问题（Must）

文件名不可靠、实验条件分散各处、多 sheet 只有部分有用：用分桶 + 模板签名 + 查轴 + 找表/找列（同 v0.4）。

### 0.5 不在范围内（Later / 不做）

CMO 报价等非科学库总表；另外再维护一本「项目总表」作为正式数据。  
手写笔记作为主源、结构图 OCR 静默写 SMILES、任意扫描件/照片分钟级入库（见附录 I）。

---

## 1. 设计原则与平台对齐

### 1.1 原则（Must）

1. 目标库是最终数据源，导入只是入口。Session 可回放，不能替代库。
2. 配置以 **ImportProfile**（库/租户级）为准；核心逻辑与领域无关。Scene Pack 可引用同一套配置，不是唯一挂载点。
3. 先关联 Sample，再写值。未解析到库实体不得静默建库（须走注册确认）。
4. 双写通道分离：`master` vs `observation`，桶级声明，防止混写。
5. 同一结构反复导入走已保存模板，不必每次用 AI 拆表；没见过或对不上再提议确认。（细则见 §1.4）
6. 源文件列对到投影槽要看得见；LLM 说了不算，要有单元格证据。
7. 确认环节 + 可回滚 + 全审计（用 supersede，不物理删除库历史）。
8. 上传时声明桶；文件名仅用于辅助判断。
9. 无目标库许可则不开导入（库配导入许可规则）。
10. LLM 只在允许能力内提议流程；不能关闭确认环节/写入环节；模板完全匹配时不跑编排 LLM。
11. **LLM 上下文最小化（Must）：** 送入模型的内容 = 当前步骤所需最小集（投影槽名、源列名、少量示例值），不传完整源文件。`ImportProfile.llm_data_policy` 控制脱敏级别（见 §3.1）。

### 1.2 概念对照（Must）


| v0.4 / v0.3        | v0.4.1                 | 平台对应                                                          |
| ------------------ | ---------------------- | ------------------------------------------------------------- |
| TargetView（可写总表）   | **LibraryProjection**  | 库实体类型 + 可导入槽的只读投影                                             |
| RowEntity / RowKey | **Sample / SampleKey** | `Sample`：`MR-xxxx` / Registry 抗体                              |
| RowKeyResolver     | **SampleResolver**     | + `sample_link_rule`                                          |
| 写入总表格              | **WriteChannel**       | `registry_register` / 化合物更新 · `observation_upsert`            |
| DomainPack / Scene Pack.`import` | **ImportProfile**（可被 Scene Pack 引用） | 库/租户级导入配置；本 SKU 绑化合物库 |


### 1.3 数据怎么写入库（Must · 骨架）

```
extract → SampleResolver
  ├─ write_channel = observation
  │     → ObservationIngress (awaiting_extraction → confirm → active)
  │     → ObservedValue 挂 sample_id
  └─ write_channel = master
        → registry_register / compound_master_upsert（既有注册能力）
        → 库主数据字段更新（须确认；与注册向导去重）
```

凝胶等需 C2 / categorical+image 的规则 **继承主规格**，本模块不另开例外。

### 1.4 反复导入走模板，不必每次用 AI 拆表（Must）

> 同一类实验结果、版式大致固定时：第一次（或版式大改）用 AI/人确认建好模板；之后命中模板就按规则抽数，**不要每份都让模型重新拆表结构**。

| 什么时候 | 怎么走 | 还要不要调 AI | 体感 |
| --- | --- | --- | --- |
| 模板**完全匹配**（vendor / 表头指纹 / 必需 sheet 等签名够阈值） | 按已保存的 ImportTemplate 抽 Sheet→字段→轴→Sample | 少调或不调 | 快到确认卡 |
| 模板**部分匹配**（多一列、改了个别表头） | 已知列仍按模板；未知列单独处理 | 只对未知列提议 | 比整份重认快 |
| **对不上**、分数不够、或用户点「重新识别」 | 分桶、找表、给出整份映射草案 | 要，等人确认 | 首份慢；确认并保存模板后，下次变快 |

保存（Must）：确认通过的映射要写入或升级 ImportTemplate（带版本与签名），不能只留在当次 Session。  
以模板为准（Must）：完全匹配时以模板规则为准；没授权时 AI 不能改模板坐标。  
细则见 §7.0 / §7.0.1（怎么判定匹配）；怎么和竞品对照见附录 E.3。

---

## 2. P0 范围（最小可用版本）

### 2.1 P0 目标（Must）

> 通用工具：xlsx 主源 → 模板匹配或 AI 提议 → SampleResolver → 确认环节 → observation_upsert（Ingress）→ 目标库详情可反查。  
> 本 SKU 目标库 = 化合物库；具体投影/桶示例见第二部分（可后置 Demo）。

抗体 Registry：同一流程、另 ImportProfile / 另打包（Should），**不**纳入本 SKU 验收。

### 2.2 P0 包含（Must）


| 项                 | 说明                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------- |
| ImportProfile     | 库/租户级：桶 + 模板 + SampleKey 策略 + projections；Scene Pack 可引用                         |
| LibraryProjection | 从**库 schema + 属性目录**生成的可写槽清单；标准 Demo + 实施按客户增删改                                      |
| 格式                | xlsx（Should：csv）                                                                    |
| 流水线               | 桶 → 模板 → Sheet/Table/Field → Axis → **SampleResolver** → Extract → Confirm → Commit |
| 写通道               | P0 主做 **observation**；master 仅 Should（或与注册向导联调一条）                                   |
| 确认                | 卡 1 字段映射 + 卡 2 样本对齐；目标位置勾选（库必写，ELN 可选）                                              |
| 多入口               | 库列表/详情 Must；设计台入口 Should（同一管线）                                                      |
| 多实体报告形状         | §16 契约 + 配方骨架 Must（P0 可先单行退化）；版式模板 / ContentClass 清单可后置                              |
| 审计 / 回滚           | session 级 superseded；库侧遵循既有 supersede/amendment                                     |
| 模板                | ≤3 个湿实验 vendor（Demo；可随客户增删）                                                        |


### 2.3 P0 不做（Later）

Introspection 自动新建行业、CMO、multi_variant、按 CAS 广播改多行主数据、导入侧静默批量注册分子、客户自助改投影。  
PDF / 图片作为**主源抽数**：P0 不做（P0 仅可作只读附件 / 证据预览）；分期见 §11、§14、附录 I。不承诺任意 PDF / 任意照片分钟级入库。  
无化合物库许可时开放导入。把导入卖成与库无关的独立 SaaS。

---

## 3. 配置层：ImportProfile

### 3.1 配置挂在哪（Must）

```
ImportProfile（库 / 租户级 · 配置以这里为准）
├─ library_ref: compound_library   # 本 SKU；抗体另 profile
├─ sample_type: compound
├─ projections[]                   # LibraryProjection
├─ buckets[]                       # 含 write_channel
├─ content_classes[]               # 内容板块 → 默认桶 / IntentPreset / 默认配方
├─ intent_presets[]                # 意图预置（见 §3.5）
├─ templates[]                     # 含 visibility（见 §7.4）
├─ sample_key_policies[]
├─ sample_link_rules[]             # CAS/实验号/内部码 → sample_id
├─ llm_data_policy: standard       # strict | standard | open（见下）
├─ resource_limits                 # 超时/文件上限（见 §6.4）
└─ degradation_rules               # 降级策略（见 §7.2）

Scene Pack（可选引用）
└─ import_profile_ref: <ImportProfile id>
   # 工作台 scene 可指向同一套配置；不是「只有挂 scene 才能导入」
```

**`llm_data_policy`（Must）：**

| 取值 | 行为 |
| --- | --- |
| `strict` | 送入 LLM 前过滤 CAS/结构/项目号等敏感字段；示例值脱敏为占位符；监管租户默认 |
| `standard` | 过滤 PII（人名/邮箱），保留业务字段；默认值 |
| `open` | 不过滤；仅限内部/非监管环境 |

`ContextSanitizer` 组件在每次 LLM 调用前执行，按 policy 过滤。审计日志记录脱敏前后的 token 数差异。

### 3.2 UploadBucket 增量（Must）

在既有桶字段上：

- `write_channel: 'observation' | 'master'`（**P0 禁止** `either`；配置加载遇到 `either` → 拒绝该 ImportProfile）
- `supplies_attr_keys[]`（observation）或 `supplies_master_fields[]`（master）；须与通道一致，不得混声明
- 系统自带备用桶：`unknown` / `custom_new` / `projection_assist`（只帮助映射，不写入权威库）

同一文件既要观测又要主数据：P0 拆成两次导入（两桶），或主数据走注册向导。P1+ 再议 `either`（确认卡须按通道拆组）。术语见 CONTEXT「导入写通道」。

### 3.3 本 SKU 与其它打包（Must / Should）


| 目标库 | ImportProfile | 商业 |
| --- | --- | --- |
| 化合物库 | **Must**（本 Spec SKU） | 与库同售 |
| 抗体 Registry | Should（另 profile / 另打包） | 不入本 SKU |


### 3.4 UI（Must）

入口读取当前租户已开通的库 → 加载对应 ImportProfile；文案用「导入到化合物库」，不用「刷新项目总表」。  
无库许可：隐藏导入入口，API 拒绝（§0.0）。  
上传页须能选 **ContentClass**（及可修改的 ArtifactKind / Mode），见 §9.0.2。

### 3.5 内容板块与意图预置（Must）

> 术语：CONTEXT **内容板块** · **导入意图预置** · **意图提示**。  
> Demo 级 ContentClass 清单：**后置**（第二部分 §L.3 占位）；本款只定契约。

**ContentClass（内容板块）** 绑定：

| 字段 | 含义 |
| --- | --- |
| `content_class_id` | 稳定 id |
| `label` | 上传页展示名 |
| `default_bucket_id` | 预填桶（须存在于本 Profile） |
| `intent_preset_id` | 绑定的意图预置 |
| `default_recipe_id` | 默认配方骨架（可空 = 仅模式枚举） |
| `allowed_artifact_kinds[]` | 允许的主源形态；空 = 不限制 |

**ImportIntentPreset（意图预置）**：

| 字段 | 含义 |
| --- | --- |
| `system_brief` | 给模型的任务说明（做什么 / 不做什么） |
| `focus_attr_keys[]` | 本板块关注字段；**Must ⊆** 当前投影可写槽 |
| `user_prompt_placeholder` | 补充说明框占位文案 |
| `disallowed_hints[]` | 如禁止要求跳过确认、禁止写未供应的 master 字段 |

**优先级顺序（Must，冲突时前者赢）：**

`ImportProfile / 投影 / 桶 supplies_*` ⊃ `ContentClass + IntentPreset` ⊃ `模板匹配结果` ⊃ `用户 IntentHint` ⊃ `LLM 自由发挥`

IntentHint（用户补充说明）为弱信号：可影响提议映射与计划文案，**不能**扩大供应表、不能关闭确认环节、不能改写通道。

**IntentHint 注入防护（Must）：**

1. IntentHint **不**原样拼入 system prompt；先经 `IntentHintSanitizer` 做结构化预处理（提取字段名/关键词），再以标签形式传入。
2. `disallowed_hints[]` 增加运行时检测：对 IntentHint 做正则 + 分类，命中注入模式（如"忽略所有规则""跳过确认""全部映射到 master"）→ 拒绝该条 Hint 并在计划卡标红提示。
3. 审计日志记录被拦截的 Hint 原文（脱敏后）与触发规则。

配置加载时：`focus_attr_keys` 越权投影 → 拒绝该 IntentPreset（或剔除越权键并告警，P0 建议直接拒绝）。

---

## 4. 从文件列对到库字段（含查轴）

顺序与 v0.4 §4 相同：找 sheet → 找表 → 定轴 → 定列（字段映射）→ 解析样本 → 抽值。

定列时，目标只能是本桶允许的观测属性（`attr_key`）或主数据字段（`master_field`）。  
禁止映射到库里不存在、或未出现在 LibraryProjection 里的列名。  
禁止把源列名原样当成目标属性（光同名不算映射完成），除非该名确实在投影槽清单中且经过确认。

P0 只做实验条件轴（Axis）；跨列 Variant 见附录 D。

---

## 5. LibraryProjection（库投影，原 TargetView）

### 5.1 定义（Must）

LibraryProjection = **当前 ImportProfile 下，允许导入写入的槽位清单**（Sample 类型、SampleKey、attr / master 字段、轴、value_kind 约束）。

- 来源：目标库 schema ∪ 属性目录（由 ImportProfile 绑定）  
- 不是：再存一份可修改的「网格总表」作为权威  
- 用途：驱动定列、确认卡预览、权限校验（桶 supplies_*）  
- 交付：标准 Demo + 我方实施按客户增删改（见第二部分；P0 不开放客户自助）

### 5.2 P0 生成方式（Must）

YAML 预置在 `ImportProfile.projections`；由实施按库字段检入。  
用户上传「总表样例」→ 仅 **对比差异 / 提示缺列**（Should），不自动建库表。

### 5.3 Introspection（Later）

自助从样例表生成 import 配置 → 附录 D；不能挡住第一次导入。

---

## 6. 数据模型与双写通道

### 6.1 核心对象（Must · 正文补全类型）

- `ImportTemplate` / `ImportSession` / `ImportAuditRecord`（从 v0.4 迁入；`row_*` 更名为 `sample_*`）
- **ImportPrimarySource（Must）：** 每 Session **恰好一个** 参与 TemplateMatch / Sheet·Table·Field / ValueExtract 的主源 Artifact；`content_hash` 幂等键取自主源。**`content_hash` = 规范化后哈希**：去除空白行/列、统一日期格式、去除 Excel 保存元数据后再算 SHA-256；避免"只改了一个空格就 hash 变了"。幂等判定维度 = `(content_hash, import_profile_id, bucket_id, content_class_id)`，跨 profile 不互判。P0 主源为 xlsx（csv Should）；PDF / 拍表图作主源见附录 I（P1.5+）
- **只读附件 / 证据图（Should）：** 同 Session 可挂 PDF/图等，仅 Provenance/留痕或补观测 `image`/`curve` 证据；**不**进指纹、不进 FieldHunt（除非该文件被标为主源）；确认卡可展示附件列表
- `ProposedWrite`：
  - `sample_id`（或 pending 新建）
  - `channel: observation | master`
  - `attr_key` + `axes` + `value` **或** `master_field` + `value`
  - `artifact_ref_slice`（指向**主源**证据切片；形态随主源类型，见下）

`artifact_ref_slice`（Must 能反查）：


| 主源类型         | 切片形态（逻辑）                | 确认卡要能    |
| ------------ | ----------------------- | -------- |
| xlsx / csv   | `sheet!cell` 或区域        | 点回格子     |
| 数字 / 扫描 PDF  | `pdf!page!bbox`（或页+表锚点） | 点回原页并高亮框 |
| 拍表 / 截图      | `image!bbox` 或网格坐标      | 点回原图并高亮框 |
| 仪器 ASM（附录 H） | ASM 路径 + 原始导出 ref       | 展开路径与源值  |


多份可抽取 xlsx → **多次 Session**（P0）；多主源合并确认 = Later（附录 D）。术语见 CONTEXT：**导入主源**。

**ReportPackage / result_rows（Must · 多实体报告）：** 当主源符合 §16 形状时，Session 内持有逻辑包（可不落独立 SoR）：`entity_key` 列逻辑名、`result_rows[]`（每行 metrics / 行级轴 / 证据 ref）、`package_axes`、`method_blob_ref?`、`evidence_block_refs[]`。流水线以 `result_rows` 驱动 SampleResolver 与 ProposedWrite，不依赖某 vendor 的 sheet 专名。

### 6.2 双写通道（Must）


| 通道              | WriteOperation                   | 典型内容                 | 确认                 |
| --------------- | -------------------------------- | -------------------- | ------------------ |
| **observation** | `observation_upsert` via Ingress | assay 读数、曲线、凝胶分类+图   | 字段卡 + 样本卡；图谱类继承 C2 |
| **master**      | `registry_register` / 化合物主数据更新   | 结构、SMILES、CAS、序列、显示名 | 走**现有注册向导**；导入只出提议 |


同一桶 **P0 不得**使用 `either`；通道与 `supplies_`* 必须一致（见 §3.2）。

### 6.3 value_kind（Must）

跟平台 ObservedValue / 库字段类型一致；扩展 kind 须库与 Ingress 都能接受。详见附录 C。

### 6.4 API / 幂等 / 资源限额（Must · 占位）

会话 CRUD、确认、提交、回滚；`content_hash` 幂等；错误：样本未解析、轴缺失（必需）、通道越权、单位不可换算（见 §7.5）。

**资源限额（Must）：**

| 项 | 默认上限 | 行为 |
| --- | --- | --- |
| 单文件大小 | 50 MB | 超限 → 阻断上传，提示拆文件 |
| 单 sheet 行数 | 100,000 | 超限 → 引导拆 sheet 或走异步队列 |
| Session 超时（无操作） | 30 min | 自动取消 Session，已分析数据丢弃（未 Commit） |
| Session 总时长 | 2 h | 超时强制终止；Notice 提示重新上传 |
| 单租户并发 Session | 10 | 超限 → 排队，返回 `IMP-RESOURCE-001` |
| PDF 页数（P1.5+） | 200 页 | 超限 → 引导拆文件 |
| OCR 页数（P2+） | 50 页/Session | 超限 → 引导拆文件 |

上限可在 `ImportProfile.resource_limits` 租户级调整（只允许收紧，不允许松过系统硬上限）。

大文件异步处理（Should）：行数 >10,000 或体积 >10 MB 时走异步队列，完成后投递 Notice 通知用户回来确认。

**错误码体系（Must）：** 所有组件错误统一编码，前缀按组件分组；完整清单见**附录 J**。确认卡和 Notice 展示错误码 + 人话解释 + 建议动作。

---

## 7. Agent 流水线与确认闸

### 7.0 走哪条导入路径（Must）

```
选桶(upload)
  → 模板匹配（§7.0.1）
       ├─ 完全匹配 → 按模板规则抽 → … → path=template
       ├─ 部分匹配 → 已知列按模板 + 未知列单独处理 → … → path=template_partial
       └─ 对不上 / 用户点「重新识别」 → AI 提议 → … → path=ai_propose
  → 导入确认（C2 特化）→ Committer → Provenance
  → （智能提议或部分匹配改过映射后）可保存模板 → ImportTemplate 版本库
```

P0 固定 CRO（如普瑞昇类 PK xlsx）必须先备好 ≥1 条能命中的模板；AI 用来补充新 vendor 和版式对不上的情况，不能代替 P0.3 的模板交付。

### 7.0.1 模板匹配：什么时候用旧模板（Must）

> 见 CONTEXT「模板匹配」「对不上」「部分匹配」。禁止只看文件名就认定匹配（§1.1.8）。

每条 ImportTemplate 要声明的签名：


| 分量                   | 含义                            | 权重（P0 默认）   |
| -------------------- | ----------------------------- | ----------- |
| `vendor_hint`        | 可选：封面/页眉/已知 vendor 词表         | 低（缺了也不否决）   |
| `header_fingerprint` | 表头或关键列名集合（规范化后排序哈希 / Jaccard） | 高           |
| `required_sheets`    | 必需 sheet 名或命名表是否存在            | 高（缺一即「对不上」） |


`match_score` 达到模板阈值 → 完全匹配，走规则路径。阈值与关键列清单写在模板 YAML；P0 用固定 fixture 锁定阈值，上线后不靠人工临时调整。

**模板阈值冷启动（Must）：**

1. 新模板初始阈值 = 1.0（所有签名分量必须全命中），防止误匹配。
2. 经过 N 次成功匹配（N 由 Admin 配置，默认 N=5）且无用户纠正后，Admin 可下调阈值。
3. 每次匹配的 `match_score` 和各分量得分 Must 记入审计日志，便于事后调阈值。
4. 验收指标增加：`误匹配（匹配到错误模板且用户未纠正）≤ 1%`。

三种结果：


| 判定   | 条件（P0）                              | 怎么走                                            |
| ---- | ----------------------------------- | ---------------------------------------------- |
| 对不上  | 缺任一必需 sheet；或关键列命中率低于模板下限           | 整份走智能提议 `path=ai_propose`；不能偷偷继续用旧列坐标          |
| 部分匹配 | 必需表在、关键列够，但多了未知列，和/或非关键 sheet 改名/增减 | 已知列按模板；未知列单独处理（可局部 AI）；`path=template_partial` |
| 完全匹配 | 没有上述问题（装饰性差异可忽略）                    | `path=template`                                |


部分匹配时，确认卡 Must 列出：哪些列沿用模板、未知列选 map / skip / defer。禁止静默丢掉未知列还不提示用户。

`ImportPlanProposal` Must 含：`path: template \| template_partial \| ai_propose` · `template_id?` · `match_score?` · `match_kind?: full \| partial \| none`（实现若仍用 `break_kind: soft\|hard`，对外文案用上表）；Should 含 `coverage`（附录 E.5）。

### 7.1 流水线（Must）

与 §7.0 / §7.0.1 同构；完全匹配时可跳过 AI 定列，但仍要 SampleResolver + 导入确认 + `artifact_ref_slice`。部分匹配时只对未知列做局部提议，不要整份文件无约束重新跑一遍。

### 7.2 组件约束（Must）

与 v0.4 相同；**SampleResolver** 替换 RowKeyResolver：可提议候选，**禁止**静默 `registry_register`。  
规则轨 ValueExtract **以模板坐标/规则为主**；AI 轨抽取要有证据 cell，确认后坐标可写入模板。

**降级策略（Must）：** 各组件依赖不可用时的行为：

| 组件不可用 | 降级行为 | 错误码 |
| --- | --- | --- |
| LLM 服务 | 只允许模板完全匹配路径（`path=template`）；AI 提议路径阻断，提示"智能分析暂不可用，请使用已知模板" | `IMP-DEGRADE-001` |
| 库 API | 阻断上传入口，不允许进入流水线；已打开的 Session 冻结（可重试） | `IMP-DEGRADE-002` |
| Ingress | 允许完成分析/确认，Commit 排队重试（最长 15 min）；超时则 Session 标 `commit_pending`，Notice 提示 | `IMP-DEGRADE-003` |
| ELN | 库写入成功，ELN 标待补同步（§G.4） | `IMP-DEGRADE-004` |
| 模板匹配服务 | 降级为全量 AI 提议路径 | `IMP-DEGRADE-005` |

降级状态在上传页顶部展示横幅提示。`ImportProfile.degradation_rules` 可配各组件超时与重试次数。

### 7.3 确认环节 = 导入确认（ImportConfirm / C2 特化）（Must）

> 见 CONTEXT「导入确认」。语义仍是 `propose_confirm`；界面跟 DualTrackConfirmDialog 一套，不要另造第三种确认弹窗。

**两张卡：**

- 卡 1：字段 / 轴 / 通道（观测还是主数据）  
- 卡 2：样本对齐（源键 → `MR-xxxx` / Registry ID；未命中则跳过 / 注册提议 / 手动关联）  
- 冲突少时可合并成一屏；regulatory 必须分卡并 sign-off  
- 页头要看得见：桶、通道、主源文件名、路径（已知模板 / 部分模板 / 智能提议）、模板 id（若有）、本批预览行数  
- AI 轨或改过映射后，Should 提示「保存为模板」；真正写入走 §7.4

#### 7.3.1 卡 1 · 字段映射表（Must）

用户要看懂的是「文件哪一列 → 库哪个槽」，不是一串同名拷贝。


| 列（建议文案） | 含义                                                        | 规则                                                                      |
| ------- | --------------------------------------------------------- | ----------------------------------------------------------------------- |
| 源列      | 主源表头 / 列名；可附 value_kind（如 scalar）。PDF/图主源时展示「逻辑列」或 ROI 标签 | 展示                                                                      |
| 目标属性    | 写入的库槽；观测用 `attr_key`，主数据用 `master_field`。界面可用业务名，技术键可次要展示 | 下拉只列本桶 `supplies_*` ∩ LibraryProjection。禁止默认「源列名 = 目标属性」。对不上投影槽则标错，不可确认 |
| 单位      | 源单位 → 规范单位（若有）                                            | 有单位的列 Must 展示；换不了则该列不能 `map` 提交                                         |
| 示例      | 从预览行抽 1～2 个源值；须能追溯到 `artifact_ref_slice`                  | Should；P0 至少在预览写入 >0 时给示例。PDF/图主源 Must 能预览源页/源图裁切                       |
| 处置      | 本列怎么处理                                                    | 见下表                                                                     |


处置取值：


| 处置           | 含义                      |
| ------------ | ----------------------- |
| `map`        | 按所选目标属性写入               |
| `skip`       | 本批不写，可记审计               |
| `defer`      | 暂缓（未知列常见）；不进本次 Commit   |
| `sample_key` | 此列是样本标识，交给卡 2，不写观测/主数据槽 |


`internal_compound_code`、实验号、CAS 等样本键列：处置应为 `sample_key`（或移出本表只在卡 2 出现），禁止映射成观测 `attr_key`。

轴映射区：有必需轴则逐行列出轴 / 值 / 是否必填 / 处置；本桶无轴时折叠并注明「本桶无必需轴」，不要留一张空白表。

按钮文案建议直白：`确认并继续`（或合并卡时的 `确认导入`）、`保存修改后确认`、`拒绝`。避免「按编辑提交」这类难懂说法。

**边界输入处理（Must）：**

| 场景 | 行为 | 错误码 |
| --- | --- | --- |
| xlsx/csv 全空或有效行数 = 0 | Sheet/Table Hunt 阶段阻断，提示"文件中无有效数据" | `IMP-PARSE-001` |
| 表头行有重复列名 | 确认卡标红重复列，要求用户手动区分或 skip；禁止静默取第一个 | `IMP-PARSE-002` |
| 数据行全为 null/空值 | 等同于空表处理 | `IMP-PARSE-001` |
| 文件编码非 UTF-8（如 GBK/Shift-JIS） | 解析层自动检测编码（chardet），检测失败时提示用户选择编码；禁止乱码后静默继续 | `IMP-PARSE-003` |
| 日期/时间字段含时区 | 统一转为 UTC 存储；确认卡展示「原始值 → UTC 值」；无法解析的日期格式 → 该行不可 Commit | `IMP-PARSE-004` |
| 浮点精度/科学计数法 | ValueExtract 保留源文件原始精度，不做隐式四舍五入；确认卡展示「源值 → 存储值」，精度差异 >0.01% 时标黄 | `IMP-PARSE-005` |

#### 7.3.2 与 Ingress / C2（Must）


| 写入内容                                    | 导入确认通过后                                       | 是否还要通用 C2      |
| --------------------------------------- | --------------------------------------------- | -------------- |
| 已具备可比标量 + `artifact_ref_slice`（P0 PK 等） | Committer → Ingress，观测置 `active`（本确认即 C2）     | 否（禁止再强制第二遍）    |
| 图谱 / 峰表 / 必须看图才能核对的 kind                | 只建 `awaiting_extraction` + ExtractionProposal | 是（不能跳过）        |
| `write_channel = master`                | 走注册/主数据确认，不要假装成 ObservationConfirm            | 按注册向导 / 既有主数据闸 |


### 7.4 TemplatePublish（Must）

> 见 CONTEXT「模板发布」。风险与 `propose_confirm` 同级：改的是租户可复用的映射。


| 项       | 规则                                                                                                |
| ------- | ------------------------------------------------------------------------------------------------- |
| 提议      | 完成导入确认的分析员可发起「保存/升级模板」（含智能提议、部分匹配时改过的映射）                                                          |
| 生效      | 项目域管理员（或 Template Editor）批准后入版本库。P0 若无角色体系：仅项目 Admin 可直发，其他人只能提议                                  |
| 作用域     | 默认 `tenant_id × scene_id`。禁止跨 scene（抗体模板不能进小分子桶）。项目私有模板 Should：匹配时项目优先于租户 scene                   |
| 升版      | 改关键列、`header_fingerprint` 或 `required_sheets` → 新版本号；旧版保留；历史 Session 仍引用当时的 `template_id@version` |
| 对不上之后新建 | AI 产出候选模板（draft），与旧版并存；Admin 退役旧版前，匹配器取最高生效版（可钉选）                                                 |
| 禁止      | 任意用户静默覆盖租户共享模板；改签名不升版                                                                             |


**模板可见性与读取权限（Must）：**

| 项 | 规则 |
| --- | --- |
| `visibility` | 每条 ImportTemplate 声明 `tenant \| project \| private`；默认 `tenant` |
| 匹配范围 | 模板匹配时只匹配当前用户有权读取的模板（`tenant` = 全租户可见；`project` = 本项目；`private` = 仅创建者） |
| 越权防护 | 低权限用户构造文件触发匹配 → 不返回无权模板的签名信息，防止间接泄露映射配置 |
| 验收指标 | `低权限用户触发越权模板匹配 = 0` |


P0.3 验收：至少一条租户×scene 生效模板，并能演示「提议→批准」或 Admin 直发。

### 7.5 单位 · 轴 · StudyRef（Must）

> 见 CONTEXT「导入单位规范」「导入轴完备」。轴的含义与平台「实验条件维度」一致。


| 项        | 规则                                                                          |
| -------- | --------------------------------------------------------------------------- |
| 规范单位     | 以 Scene Pack 属性目录为准（经 LibraryProjection）。模板只存源单位/换算提示，不能和目录冲突               |
| 换算       | 规则轨按模板换算；AI 轨只提议，确认卡写清「源值+单位 → 规范值+单位」。无法换算就跳过该行，禁止当无量纲写入                    |
| 必需轴      | 目录标 required 的轴（如 PK 的 species/route）缺了：确认卡补全或整行跳过。禁止靠文件名猜测                  |
| 桶默认轴     | Should：只预填，确认卡上可见可修改                                                         |
| StudyRef | Should：有 study/报告号就写入元数据。P0 不因缺 `study_id` 阻挡标量入库；Session 摘要里提示同 study 关联会变弱 |


Committer 建议顺序：通道越权 → 样本已解析 → 单位可规范化 → 必需轴齐全 → 写入 Ingress。

---

## 8. SampleResolver（原 RowKeyResolver）

### 8.1 P0（Must）

1. 按 `sample_link_rules` 规范化源键（CAS 校验、去空格等）
2. 若入口已带 `context_sample_id` 且策略允许优先上下文 → 直接绑定（设计台回写常见）
3. 查化合物库 / Registry → 唯一命中则绑定
4. 多候选 → `propose_confirm`
5. 零命中 → **不得**静默建样；按 §8.4 `sample_policy.on_miss` 处理（历史严格模式默认阻断并提醒注册）

**多候选 UX（Must）：**

- 候选数 ≤10：确认卡卡 2 全部列出，用户点选。
- 候选数 >10 且 ≤50：确认卡卡 2 展示前 10 + 搜索/过滤框，用户可缩小范围。
- 候选数 >50：阻断该行，要求用户添加辅助键（如 CAS + 内部编号双键）或手动选样；禁止全部列出。
- 验收指标：`多候选 >50 时未引导用户缩小范围 = 0`。

### 8.2 匹配策略（Must）

`exact_match` | `alias_single` | `propose_confirm` | `reject` | `first_match_wins`（慎用）  
**Later：** `broadcast_matching_alias`（一源行更新多库实体；主数据慎用）

### 8.3 与注册去重（Must）

新建 Sample **只**走现有注册能力；Import Agent 可以出 `pending_registration` 草案，或给「去注册」链接，不要自己再做一套注册页面。  
历史严格模式：未注册分子默认不能 Commit（见 §8.4），先注册完再开新 Session 或重试本批。

### 8.4 导入模式与样本策略（Must）

> 术语见 CONTEXT「导入模式」「导入样本策略」。还是同一条导入流程，用策略区分业务场景，不要做成两个导入产品。

**内置模式（P0 至少能切换；也可由入口直接带上）：**


| 模式                  | 典型场景              | 默认 sample_policy                                                               |
| ------------------- | ----------------- | ------------------------------------------------------------------------------ |
| `historical_strict` | 历史报告导入；分子可能尚未入库   | `require_registered=true`；`on_miss=block_row` 或 `abort_batch`；确认卡列出未注册键 +「去注册」 |
| `design_writeback`  | 设计工作台已注册分子后回写实测   | `prefer_context_sample_id=true`；`on_miss=block_row`（仍禁止静默建样）                   |
| `flexible`（可选）      | 行为接近旧版 §8.1 的宽松处理 | `on_miss` 允许 `skip` / `propose_register` / 手动选样                                |



| 字段                         | 含义                                                        |
| -------------------------- | --------------------------------------------------------- |
| `require_registered`       | true 时：未解析到库实体的行不得 Commit                                 |
| `on_miss`                  | `abort_batch` | `block_row` | `propose_register` | `skip` |
| `prefer_context_sample_id` | 优先用入口带来的当前分子 ID，而不是文件里含糊的键（文件里有多个分子时，卡 2 仍要核对）            |


入口约定（Should）：

- 库列表 / 全局导入 → 默认 `historical_strict`，或让用户自己选  
- 设计台 Portfolio / 分子工作区「导入到此分子」→ `design_writeback`，并预填 `context_sample_id`  
- Session 要记下本次用的 `import_mode` 和生效的 `sample_policy`（方便审计）

步骤怎么拆、以后让人/LLM 配置流程 → 见附录 F（Later）。同步到 ELN → 见附录 G（P1）。

---

## 9. 用户交互与多入口

### 9.0 主路径（Must）

```
选 ContentClass（内容板块）+ ArtifactKind（可检测预填）+ ImportMode（可入口预填）
  → 可选填写 IntentHint（补充说明）
  → 选/确认观测桶（默认来自 ContentClass）
  → 上传主源
  →（P2 / 对不上时）LLM 提议 recipe → 【计划卡】人确认
  → 模板匹配
       ├─ 完全匹配 → 规则抽（不跑编排 LLM）
       ├─ 部分匹配 → 已知列规则 + 未知列局部提议
       └─ 对不上 → 按已确认 recipe / IntentPreset 做映射提议
  → 卡 1 字段映射 → 卡 2 样本对齐
  → 落点勾选：写入库观测（必选）+ 可选同步 ELN
  → 确认 → Ingress（→ 可选 ElnWriteback）
  → （若改过映射）可选保存模板
  → 打开库详情 / 设计台表看新观测 + 反查
```

上传页文案 Should 写清：「已知模板（快）」vs「智能提议（须确认，可保存为模板）」。细则见附录 E.5.4。

### 9.0.1 多入口（Must）

| 入口 | 分期 | 预填 |
| --- | --- | --- |
| 化合物库列表 / 详情「导入」 | Must（主售卖入口） | 默认可选 historical_strict |
| 可选「数据导入」工作台页 | Should | 同库入口；不另卖成第二产品 |
| 设计台「导到此分子」 | Should | design_writeback + context_sample_id |
| ELN 内触发导入 | Later | 仍写库；ELN 仅可选回写 |

所有入口调用同一导入流程与 ImportProfile；禁止每个入口复制确认/写库契约。无库许可则全部入口不可用。

### 9.0.2 上传三轴与计划卡（Must / Should）

**三轴（Must 可区分；不要合并成一个「文件类型」）：**

| 轴 | 含义 | 谁定 |
| --- | --- | --- |
| ContentClass | 内容板块（意图） | 用户选；「不确定」→ 强制计划卡 + AI 提议 |
| ArtifactKind | 主源形态（xlsx / 数字PDF / 扫描 / 拍表 / 仪器导出 / 仅附件） | 检测预填 + 人可改 |
| ImportMode | 历史严格 / 设计台回写等 | 入口预填或用户选 |

**计划卡 ImportPlanCard（Should P0 骨架；P2 Must 用于 LLM 编排路径；regulatory Must）：**

展示：将使用的步骤（用通俗语言）、桶/通道、关注字段（IntentPreset ∩ 投影）、快通道或智能提议。  
用户确认「按此计划继续」后再抽数。模板完全匹配且无 IntentHint 冲突时，可将计划卡折叠为只读摘要（Should）。

**禁止：** 空白大模型对话框作为唯一入口；用用户 prompt 覆盖投影供应表。

确认卡交互约束见 §7.3.1。模式与未注册阻断见 §8.4。ELN 勾选项见附录 G。

### 9.1 分支


| 分支                        | 分期                 |
| ------------------------- | ------------------ |
| 模板完全匹配 → 规则轨至确认卡          | Must               |
| 模板未匹配 → AI 提议 → 确认 → 保存模板 | Must（P0.3 起保存模板）   |
| 历史严格：样本未在库 → 阻断 + 去注册     | Must（§8.4）         |
| 设计台回写：预填 sample_id 命中     | Must（§8.4）         |
| 宽松模式：样本未在库 → 注册提议 / 跳过    | Should（`flexible`） |
| 用户强制「重新识别」                | Should             |
| master 通道补结构/CAS          | Should             |
| 抗体 scene                  | Should             |
| 未知列单独处理                   | Should             |
| 同步到 ELN 实验记录              | P1（附录 G）           |
| 仪器原始导出（allotropy）         | P2（附录 H）           |
| 自助生成 projection / 自定义配方   | Later（附录 F）        |


---

## 10. 归属、审计、回滚

### 10.1 数据归属（Must）

- 观测：`(sample_id, attr_key, axes)` 的最新 ObservedValue  
- 主数据：库实体字段最新值 + 变更审计  
- 反查：库详情 / 科学数据侧栏 → Artifact 切片 + session + template

### 10.2 通道权限（Must）

桶未声明的 `attr_key` / `master_field` → Committer 拒绝。

### 10.3 回滚（Must）

ImportSession 回滚 → 本 session 产生的观测被 supersede；主数据回滚怎么做，与库 amendment 规则一致（与库团队确认正文细节）。

### 10.4 重复导入冲突（Must）

> 术语见 CONTEXT：**导入冲突覆盖**。冲突键 = `(sample_id, attr_key, axes)` 已存在 **active** 最新值。


| 情况                                 | 行为                                                       |
| ---------------------------------- | -------------------------------------------------------- |
| 新文件 `content_hash` 与某成功 Session 相同 | **幂等短路**：不重复写入；Notice 提示已导入                              |
| hash 不同且键冲突                         | 确认卡标 **冲突行**；默认 **跳过该行**（不静默覆盖）                          |
| 用户显式「以本批 supersede」                | Committer 走平台 supersede/amendment；旧值可审计；最新值指向本 Session |
| 样本集合高度重叠但未勾选覆盖                     | 不能整批自动 supersede；要逐行，或用「全选冲突行覆盖」这类明确动作                   |
| StudyRef / 报告号不同                   | 写入元数据；**不**默认扩成新 axes（P0）；若需「同条件多报告并存」→ 属性目录显式加轴（Later）  |


确认卡要展示：冲突键、旧最新值来源 session、本批新值预览。

**并发导入冲突（Must）：**

| 情况 | 行为 |
| --- | --- |
| 两个 Session 同时写同一 `(sample_id, attr_key, axes)` | Committer 用乐观锁（最新版本号）；先到者 active，后到者返回 `IMP-CONFLICT-001`，该行标冲突并跳过 |
| 确认卡打开到点击确认之间最新值被其他 Session 修改 | 点击时检查最新版本，若已变 → 弹出警告「该数据已被其他导入修改」，用户选择覆盖/跳过/刷新 |
| 同一用户在不同标签页同时提交 | 同上乐观锁机制；后提交的 Session 收到冲突通知 |

### 10.5 部分提交（Must）

> 术语见 CONTEXT：**导入部分提交**。


| 项          | 规则                                                                              |
| ---------- | ------------------------------------------------------------------------------- |
| 默认         | 尽力而为：只提交用户确认的可写行；跳过与提交期失败不阻断成功行                                                 |
| Session 状态 | 全成功 → `committed`；有成功也有跳过/失败 → `committed_partial`；零成功 → `failed` / `cancelled` |
| Notice     | Must 包含写入 / 跳过 / 失败三类计数；禁止部分成功却只显示「成功」                                             |
| 原子模式       | Should：regulatory 项目默认开启，或确认卡勾选「全部成功才写入」；任一拟提交行失败 → 整批回滚、零写入                     |
| Rollback   | 按 Session 撤销本批已写入的最新值（含 `committed_partial` 中的成功行）                             |


**部分提交后重试（Should）：**

- `committed_partial` 的 Session 允许"重试失败行"：新 Session 引用旧 Session 的 skip/fail 列表，只重新处理未成功的行。
- 重试 Session 的 Notice 标注"基于 Session X 的重试"，便于审计追踪。
- 回滚粒度：P0 整 Session；P1 支持按行子集回滚。


---

## 11. 文件格式

> 先分**角色**（主源 / 证据附件 / OCR 辅源），再看扩展名。细则与流程见附录 I。不承诺「任意 PDF / 任意照片分钟级入库」。


| 格式                  | 角色                      | 分期                    | 可否作主源               |
| ------------------- | ----------------------- | --------------------- | ------------------- |
| xlsx                | 主源                      | Must                  | **是**（P0 主源）        |
| csv                 | 主源                      | Should                | 是                   |
| PDF · L1（文本层 + 可检表） | 主源候选                    | P1.5 / P2 前半          | 是（固定 CRO 模板起步）      |
| PDF · L2（文本烂 / 双栏等） | 主源，须 ROI                | P2                    | 是（无人框选则阻断抽值）        |
| PDF · L3（扫描纯图页）     | OCR 辅源                  | P2 后 / P3             | 是（租户开关；指标与 L1 分开报）  |
| PDF（任意）             | 证据附件                    | P0 Should             | **否**（只留痕 / 可挂 ELN） |
| 图片 · A（凝胶/光谱等证据）    | 证据附件或观测 `image`/`curve` | P0 Should；P1 打磨绑定 UX  | **否**（不当表格主源）       |
| 图片 · B（拍表 / 截图表）    | OCR 辅源                  | P2                    | 是（强制确认；默认无快通道）      |
| docx                | 附件或 Later 主源            | P0 附件 Should；主源 Later | P0 否                |
| 手写笔记 / 结构图 OCR 静默注册 | —                       | 不做                    | —                   |


上传 UX（Must）：

1. 标明「主文件（用于识别/抽数）」vs「附件（仅留痕）」；误选多主源 → 阻断并提示拆 Session。
2. PDF/图若选为主文件：展示检测结果（可抽取表 / 需框选 / 仅宜留痕）。
3. 同一 Session 一个主源：「xlsx + 报告 PDF」→ xlsx 主源、PDF 附件；「只有 PDF」→ PDF 主源（P1.5+）。
4. 快路径文案写「已知模板」；PDF/图慢路径写「须核对原页/原图」，禁止写「已自动识别正确」。
5. 限额：页数、像素、体积、OCR 页上限；超限引导拆文件或改传 xlsx。监管租户可关闭云端 OCR / 多模态。

---

## 12. 查询与下游

### 12.1 查询（Must）

- **库详情 / 列表：** 读库 + ObservedValue  
- **Session 视图：** 本批写了哪些 sample×attr；引用 `template_id@version`（若有）

### 12.2 导入完成后下游（Must）

> 术语见 CONTEXT：**导入完成通知**。Commit 成功（含部分成功）后投递 **Context Notice**（P1–P3，无强弹窗）。


| 行为                         | 分期     | 规则                                                                             |
| -------------------------- | ------ | ------------------------------------------------------------------------------ |
| **ImportCompletionNotice** | Must   | 摘要：写入 / 跳过 / 失败条数；链到 Session；**禁止**业务强写回 CTA                                   |
| **去对照入口**                  | Should | Notice 可跳转预测-实测对照，预填本次 `sample_ids` + 相关 `attr_keys` → 进入**数据确认卡**（不跳过、不自动跑引擎） |
| **自动跑对照引擎**                | 不做（P0） | —                                                                              |
| **自动生成 FeedbackRecord**    | **禁止** | 训练池仍走反馈配对 / 手动配对队列；导入路径不入池                                                     |
| **显式 prediction_run_id**   | Should | 若观测偶带该引用：Notice **文案提示**「可生成反馈配对」，仍须人确认；不得静默建 FeedbackRecord                   |


### 12.3 导入历史视图（Should）

用户可查看自己的导入历史列表，便于审计追踪和重做：

| 列 | 含义 |
| --- | --- |
| 时间 | Session 创建/完成时间 |
| 状态 | `committed` / `committed_partial` / `failed` / `cancelled` / `commit_pending` |
| 主源文件名 | ImportPrimarySource 的文件名 |
| 写入/跳过/失败条数 | 来自 Notice 的三类计数 |
| 模板 | `template_id@version`（若有） |
| ContentClass / 桶 | 本次导入的板块与桶 |
| 操作 | 查看详情 / 回滚 / 补同步到 ELN / 重试失败行（仅 `committed_partial`） |

按时间倒序排列；支持按状态、ContentClass、时间范围过滤。


---

## 13. 验收指标


| 指标                            | 目标                             |
| ----------------------------- | ------------------------------ |
| EO035 → 化合物库端到端               | 通过（附录 B）                       |
| 样本误挂（错 MR）静默提交                | **0**                          |
| 未解析样本静默建库                     | **0**                          |
| 历史严格模式：未注册行仍 Commit active    | **0**                          |
| 设计台回写：入口 sample_id 被文件模糊键静默覆盖 | **0**（未在卡 2 确认前）               |
| 模板完全匹配后字段映射正确率                | ≥ 95%（以投影槽为准；源列名原样当目标且槽不存在计失败） |
| 样本键列误写成观测 attr 并提交            | **0**                          |
| 源列名默认填目标属性且未经确认可选槽            | **0**                          |
| 必需轴一次命中                       | ≥ 85%                          |
| 详情反查至源 cell                   | 100%                           |
| session 回滚观测                  | 100%                           |
| 观测桶写入 master 字段               | **0**（越权拦截）                    |
| 无换算却写入非规范单位                   | **0**                          |
| 缺必需轴仍 Commit active           | **0**                          |
| 键冲突未显式 supersede 却覆盖最新值      | **0**                          |
| 相同 content_hash 重复写入          | **0**（幂等）                      |
| 部分成功却 Notice 只显示成功      | **0**                          |
| 误匹配（匹配到错误模板且用户未纠正）          | ≤ 1%                           |
| 空文件/全空行静默提交                  | **0**                          |
| 因编码问题导致表头匹配失败且未提示             | **0**                          |
| 隐式精度损失导致值变化 >0.01%           | **0**                          |
| IntentHint 注入导致越权映射            | **0**                          |
| 低权限用户触发越权模板匹配                  | **0**                          |
| 多候选 >50 时未引导用户缩小范围            | **0**                          |
| 并发 Session 同键静默覆盖               | **0**（乐观锁拦截）                 |


### 13.2 运行时遥测指标（Should P0）

上线后持续监控，便于快速发现系统性问题：

| 指标 | 采集方式 | 告警阈值建议 |
| --- | --- | --- |
| 模板匹配率（完全/部分/对不上） | 按 `template_id` 分桶统计 | 对不上率 >50% 告警 |
| AI 提议 → 用户接受率 | 按 ContentClass 分桶 | 接受率 <30% 说明提议质量差 |
| 确认卡修改率 | 用户改了几列 / 总列数 | 修改率 >40% 说明模板/提议不准 |
| Commit 成功率 | 按 `import_mode` 分桶 | 成功率 <80% 告警 |
| Session 耗时分布 | P50 / P95 / P99 | P95 >10 min 排查 |
| LLM 调用次数 / token 消耗 | 按 `path` 分桶 | 模板匹配路径不应有 LLM 调用 |
| 降级事件计数 | 按错误码分桶 | 任何降级事件都告警 |
| 并发冲突计数 | `IMP-CONFLICT-001` 计数 | 频率突增排查 |


---

## 14. 分期路线


| 阶段       | 交付                                                                                                    |
| -------- | ----------------------------------------------------------------------------------------------------- |
| **P0.1** | ImportProfile 挂化合物库 · LibraryProjection Demo YAML · 观测桶 · xlsx 流水线 · SampleResolver · Ingress · 库许可门闸 · **资源限额** · **错误码体系** · **降级策略** · **LLM 上下文最小化** |
| **P0.2** | 导入确认 · 目标位置勾选骨架 · Audit/回滚 · 详情反查 · Notice · 库入口 · **上传选 ContentClass**（清单可后置）· 计划卡只读摘要 · **边界输入处理（空文件/编码/日期/精度）** · **并发冲突乐观锁** · **IntentHint 注入防护** |
| **P0.3** | 规则轨快通道 + ≤3 CRO 模板 · 未匹配→AI 映射提议→确认 · TemplatePublish · 导入模式 · **多实体报告配方骨架（§16）** · **模板冷启动规则** · **模板可见性** · **多候选 UX** |
| **P0.4** | csv · 未知列单独处理 · 去对照预填 · master 联调（Should）· 设计台入口（Should）· **导入历史视图** · **运行时遥测** · **部分提交重试** |
| **P1**   | ELN 回写（附录 G）· 证据图绑定 UX · link_rule 增强 |
| **P1.1** | ELN：按桶模板新建实验记录；补同步 ELN |
| **P1.5** | PDF L1 模板主源（附录 I） |
| **P2**   | LLM 提议配方 + **计划卡 Must** · 附录 F 编排 · allotropy · PDF L2 / 拍表 OCR · 模板治理 |
| **P3**   | PDF L3 · 多图/多主源；抗体另打包 |
| **后置** | 第二部分：assay 表清单、**ContentClass Demo 清单**、客户定制投影 |


---

## 15. 与既有 spec 的接口


| 模块                 | 要点                                                 |
| ------------------ | -------------------------------------------------- |
| 化合物库               | 本 SKU 权威 SoR；主数据 API；详情反查；库开通门闸                     |
| ImportProfile      | 库/租户级导入配置权威；投影/桶/模板/策略                              |
| Scene Pack         | 可 `import_profile_ref` 引用；非唯一挂载；可挂 ELN 默认方法模板 id   |
| ObservationIngress | 观测只能从这里写入（含 import_batch；ELN 是另一路，和「导入后回写 ELN」配合用） |
| WriteOperation     | `observation_upsert` / `registry_register`         |
| AutonomyMatrix     | 新建样 / override / 提交                                |
| 设计工作台              | 多入口之一；预填 design_writeback + 当前分子 id；表读库观测           |
| ELN                | 可选回写；观测仍以库为准（附录 G · 导入目标位置勾选）                         |
| allotropy（开源）      | 仪器导出 → ASM JSON；附录 H；不替代 CRO 模板导入                  |
| PDF / 图片解析         | 附录 I；与 H 按桶分流                                      |
| 预测-实测对照            | 导入后可建议去对照                                          |
| 抗体 Registry        | 另打包；同流程另 ImportProfile                              |
| §3.18 Raw Data     | 无关                                                 |
| 多实体报告导入           | §16 · 附录 F `multi_entity_report`；版式实例见 L.4（非绑定） |


---

## 16. 多实体报告导入

> **目的：** 覆盖「一份报告文件里有多分子结果表 + 方法/原始区，要写回库观测并可勾选 ELN」这一**类**场景。  
> **不绑：** 具体 ContentClass 名、具体 CRO、具体 sheet/列名。那些只进 **ImportTemplate** 与投影槽。  
> **术语：** CONTEXT **多实体报告导入（MultiEntityReportImport）**。

### 16.1 适用范围（Must）

凡同时满足以下，默认走本节配方（或 ContentClass 的 `default_recipe_id = multi_entity_report`）：

```text
单主源 ImportSession
  ├─ 结果表区：多行；每行含可解析的实体键（分子/样本）+ 若干标量结果
  ├─ 方法区（可选）：协议/步骤叙事 → 供 ELN，不写进 ObservedValue 真值
  ├─ 证据区（可选）：板图、剂量点、曲线、峰图 → 证据切片或后置结构化
  └─ 包级元数据（可选）：报告日、细胞系/种属等 → package_axes
       ↓
  N × Sample 锚点 + 每 Sample 若干观测（库 SoR）
  + 可选 1 × ELN Entry（方法 + 附件 + 本批摘要深链）
```

**退化：** 结果表仅 1 行时仍用同一管线（不必另产品）。  
**设计台「只导当前分子」：** 同一管线加 `row_filter`（或 prefer_context_sample_id 后只提交匹配行），不是第二套导入。

**不适用（另路径）：** 整表只注册结构/主数据（master 桶）；纯仪器导出 ASM（附录 H）；无「实体键列」的宽表转置（Later / multi_variant）。

### 16.2 三层分离（Must）

| 层 | 稳定内容 | 配置落点 | 换客户/换 CRO 时 |
| --- | --- | --- | --- |
| **A · 管线契约** | 单主源、行→Sample、确认闸、观测写闸、ELN 可选 | 本节 + 附录 F | 基本不改 |
| **B · 报告角色与版式** | 哪一块是结果表/方法/证据；列→逻辑字段 | ImportTemplate（`role_selectors` + `column_map`） | 新模板一条 |
| **C · 业务槽与轴** | 可写哪些 attr / 必需轴 | LibraryProjection + ContentClass IntentPreset | 改投影或板块 |

禁止把 B/C 的专有名词（某 sheet 英文名、某客户 Compound ID 列名）写进 A 层代码路径名。

### 16.3 逻辑对象（Must）

```text
ReportPackage
  primary_artifact
  entity_key_field          # 逻辑名，如 compound_id / sample_key（非源列字面）
  result_rows[]             # { entity_key, metrics{}, row_axes{}, evidence_refs[] }
  package_axes{}            # 整批共用轴（细胞系、种属、报告日…）
  method_blob_ref?          # 方法区 → ELN
  evidence_block_refs[]     # 原始/曲线区 → 附件或证据
```

从源文件到 `result_rows` 的步骤见 §16.4；写回规则见 §16.5。

### 16.4 流水线步骤（Must）

在通用 §7 流水线上，多实体报告**插入/特化**如下（步骤 id 见附录 F.1）：

| 顺序 | 步骤 | 说明 |
| --- | --- | --- |
| 1 | DetectArtifactKind / SelectBucket | 同既有；桶须 observation |
| 2 | MatchTemplate | 命中则用模板 `role_selectors`；对不上则 AI **提议角色与列映射**（仍须确认） |
| 3 | **LocateRoles** | 标出 `result_table` / `method_block?` / `evidence_block?` / `package_meta?` |
| 4 | **ExpandResultRows** | 结果表 → `result_rows[]`；空键行跳过；可选 `row_filter` |
| 5 | ResolveAxes | `package_axes ∪ row_axes`；单位规范同 §7.5 |
| 6 | ResolveSample | **逐行** `entity_key` → Sample（读 sample_policy / ImportMode） |
| 7 | MapFields / ExtractValues | metrics → 投影槽；证据 ref 指向结果 cell 或证据区 |
| 8 | Confirm | 卡 1 可批；卡 2 多样本对齐；展示「本批将写入 N 个分子」；落点勾选 |
| 9 | CommitRegistry | 按确认行写观测；未对齐行按部分提交跳过 |
| 10 | ElnWriteback | 可；默认**一条** Entry 挂方法+主源+本批摘要（附录 G） |
| 11 | PublishTemplate | 可；把本次角色+列映射沉淀为 ImportTemplate |

模板完全匹配时跳过编排 LLM（§1.4）；LocateRoles / ExpandResultRows 走规则选择器。

### 16.5 写回口径（Must）

| 目标 | 规则 |
| --- | --- |
| Registry / 库实体 | **只做身份**：键 → Sample；未注册按 §8.4。禁止把 assay 读数写进主数据字段 |
| 库观测 | 每 `(sample, attr, axes)` 一条；轴 = 包级 ∪ 行级；权威在库 |
| ELN | 方法叙事 + 附件 + 深链；禁止 ELN 内可编辑结果表当 SoR |
| 一对多 | 默认 `1 Session : N Sample`；幂等键仍含主源 `content_hash`（同 §6.1） |

### 16.6 ImportTemplate 扩展（Must）

版式模板除既有签名外，多实体报告须声明：

```yaml
# 示意 · 逻辑字段，非某客户实表
role_selectors:
  result_table: { sheet_hint?: string, header_fingerprint: [...] }
  method_block: { ... }      # optional
  evidence_block: { ... }    # optional
  package_meta: { ... }      # optional
column_map:
  entity_key: <源列逻辑绑定>
  metrics.<attr_key>: <源列>
package_axis_extractors:
  <axis_key>: <从元数据区抽取规则>
```

换 vendor：新增 Template（B），不改 §16 契约（A）。换可写属性：改投影/板块（C）。

### 16.7 确认卡与入口（Must / Should）

- 确认卡摘要 Must 含：本批行数、对齐成功/失败/跳过、将写 attr 列表、包级轴。  
- 上传三轴不变（ContentClass · ArtifactKind · ImportMode）；**不要**做成「某某 CRO 场景」独占壳。  
- 计划卡 Should 显示 `recipe_id: multi_entity_report` 与是否命中模板。

### 16.8 禁止（Must）

- 内核写死某一 sheet 名 / 某一 ContentClass 才能走多实体路径  
- 整表结果灌进 Registry 主数据  
- 跳过确认闸批量写 N 分子  
- 为每个 CRO 复制一套导入产品（只允许复制 Template）

实例示意（非绑定）→ 第二部分 **L.4**。


---

## 附录 A · 版本迁移


| 来源                  | v0.4.1                             |
| ------------------- | ---------------------------------- |
| TargetView 可写总表     | 废除权威含义 → LibraryProjection         |
| RowKeyResolver      | SampleResolver + sample_link_rules |
| target_view_upload  | projection_assist（只辅助）             |
| CMO / multi_variant | 附录 D                               |
| v0.4 平台对齐、P0 缩减范围    | 继承                                 |
| Scene Pack.import 唯一挂载 | v0.4.20 → ImportProfile 权威；Scene 可引用 |
| 单表单分子假设 | v0.4.24 → 多实体报告（§16）为一等形状；单行退化为 N=1 |


---

# 第二部分 · 化合物库适配（内容可后置）

## L. 化合物库适配说明

> 本部分描述**本 SKU**（化合物库）上的 Demo 投影、验收剧本与字段分类示例。  
> **可后置：** 不挡第一部分工具 P0；具体 assay 表清单按客户合同由我方实施增删改。  
> **不做：** 把客户定制表结构写进工具核心；客户自助改投影（P0）。

### L.1 Demo 投影（Should）

- 产品提供可演示的标准 LibraryProjection + 少量 CRO 模板（如 PK 类桶）。  
- 实施可按客户需求增删槽位、桶、模板；升版规则同 §7.4。  
- 标准包可部分关闭或整包替换为客户投影。

### L.2 与工具的边界

| 在工具（第一部分） | 在本适配（第二部分） |
| --- | --- |
| 确认环节、双通道、SampleResolver、模板匹配算法 | 具体 attr_key 列表、桶供应清单示例 |
| ImportProfile 结构 · ContentClass/IntentPreset **契约** | 化合物库 Demo YAML / 验收剧本 / **板块清单** |
| **多实体报告导入**契约与配方（§16 / 附录 F） | 某客户/某 CRO 的 **ImportTemplate 实例**（列名、sheet 提示） |
| 目标位置勾选 · 编排白名单 | 某客户实际开通了哪些槽与板块 |

### L.3 ContentClass Demo 清单（后置）

> **本轮不定。** 后续补：板块 id/展示名、默认桶、IntentPreset、关注字段示例。  
> 未定清单前：P0 可用占位类 `unknown` / `generic_observation`（须人确认桶），不得假装已覆盖 PK/体外等业务板块。

### L.4 多实体报告 · 实例示意（非绑定）

> **地位：** 仅说明「怎么把一张真实报告填进 §16」，**不是**产品绑定场景，也不是唯一验收表。  
> **换表：** 另建 ImportTemplate；勿改 §16。

**形状对照（示意）：**

| §16 角色 | 实例里常见对应（可换） |
| --- | --- |
| result_table | 汇总结果 sheet：多行 Compound/Sample ID + IC50 等标量 |
| entity_key | 报告内化合物编号列 → SampleResolver |
| package_axes | 细胞系 / 检测日 / 实验类型（从封面或协议区抽一次） |
| method_block | Protocol / 方法说明 → ELN 预填 |
| evidence_block | Raw / Curve 区 → 附件或证据切片（P0 可只挂主源） |

**验收要点（与附录 B 同类，可后置具体文件）：** 库内预置 N 个 MR → 上传命中模板 → 确认卡显示 N 分子 → Commit 后各详情可见观测且可反查 → 可选 ELN 一条挂方法与深链 → 回滚 session 观测 superseded。

具体列绑定 YAML：实施仓库维护，不进工具内核。


---

## 附录 B · EO035 → 化合物库验收剧本

> 属第二部分；验证「工具 + 化合物库 Demo」联调。

1. 库内预置相关 `MR-*`（或 CAS 可解析）
2. 预置化合物库 ImportProfile（如 `pk_in_vivo` 桶 + 模板；或 Scene Pack 引用该 profile）
3. 上传普瑞昇类 PK xlsx → 签名命中 → Axis → 样本对齐到 MR → 提交 Ingress
4. 打开化合物详情：见新观测；点开反查至源 cell
5. 回滚 session：观测被 superseded，详情最新值恢复

模板 YAML：从 git 历史 v0.3 §7 迁入并改 `target_attr` → 库 attr_key。

---

## 附录 C · 库写入对照表（主数据 vs 观测）

> **第二部分。** 实施时与库字段表、ImportProfile 属性目录逐行核对；下表为分类原则与 Demo 示例，具体清单可后置定制。

### C.1 小分子 · 化合物库


| 数据项                           | 通道              | 落点                                        | P0                |
| ----------------------------- | --------------- | ----------------------------------------- | ----------------- |
| 结构图 / SMILES / InChI          | master          | 化合物结构字段                                   | Should            |
| CAS / 内部编号 / 显示名              | master          | 标识字段；并参与 SampleResolver                   | Should（解析 Must）   |
| 分子量、分子式等计算/登记属性               | master          | 库属性                                       | Later / 随注册       |
| AUC / Fu% / IC50 / 溶解度等 assay | observation     | ObservedValue + axes（species/route/dose…） | **Must**          |
| 曲线、峰表、报告 PDF 附件               | observation     | kind=curve/image + ArtifactRef            | Should（图谱规则继承主规格） |
| 实验批次号 / 报告号 / 检测日             | observation 元数据 | Run / Ingress metadata                    | Must              |
| 项目号（若仅业务标签）                   | 元数据或库 tag       | 勿与 sample_id 混淆                           | 按库模型              |


### C.2 大分子 · 抗体 Registry


| 数据项                 | 通道           | 落点                      | P0         |
| ------------------- | ------------ | ----------------------- | ---------- |
| 序列 / 同种型 / 名称       | master       | Registry 主数据            | Later（随注册） |
| Registry ID / 内部抗体号 | master + 解析键 | SampleResolver          | Should     |
| 八维等**预测**快照         | **非本模块**     | 预测 run / Registry 快照    | —          |
| 湿实验标量、DSC、凝胶分类+图    | observation  | Ingress → ObservedValue | Should     |
| study / 方法学         | 观测元数据        | assay 目录约束              | Should     |


### C.3 桶声明示例（Must 原则）

```yaml
# 观测桶：只许 supplies_attr_keys
- bucket_id: pk_in_vivo
  write_channel: observation
  supplies_attr_keys: [pk.auc_0_t, pk.cmax, ...]

# 主数据桶：只许 supplies_master_fields（P0 Should；与观测分桶/分次）
- bucket_id: compound_structure_sheet
  write_channel: master
  supplies_master_fields: [structure, smiles, cas]

# P0 非法：write_channel: either
```

**禁止：** assay 报告桶写入 `smiles`；结构注册桶写入 `pk.auc_0_t`；P0 出现 `either`。

---

## 附录 D · Later 占位

> 第一部分附录续。

- multi_variant / 跨列 variant  
- CMO 等非库总表  
- TargetViewIntrospection → 自助生成导入配置  
- Sample 广播更新、docx 作为主源、模板市场  
- PDF / 图片主源抽数 → **附录 I**（P1.5+）；P0 仅附件  
- 仪器确定性解析路径 → **附录 H（allotropy，P2）**；不再仅占位  
- `write_channel: either`（同文件双通道 + 确认卡拆组；P0 禁止）  
- 多主源同 Session 合并确认；多图自动拼总表  
- 自定义 Import Recipe 可视化排步骤、LLM 自动改写步骤顺序（见附录 F；须人批准）  
- 从报告抽方法正文进 ELN 且免确认（禁止；有确认版见附录 G P2）  
- 手写笔记主源、结构图 OCR 静默写 SMILES（明确不做，见附录 I）

---

## 附录 E · Benchling Data Import 对照

> 检索口径（2025–2026）：[AI Data Import](https://www.benchling.com/ai/data-import)、Help · Data Entry Agent、Ashu Singhal《Why I quit my job to build AI agents for scientists》（2025-03）、Biotech AI Guide、Benchling Connect / Runs。  
> 用途：看他们怎么做导入，方便我们取舍。不改本模块 P0（xlsx → 化合物库观测）。  
> 他们的定义：导入 = 用 Notebook + Schema 当翻译词典的 LLM 流程，不是通用 OCR。

### E.1 他们在做什么


| 层           | Benchling 做法                                                                                               |
| ----------- | ---------------------------------------------------------------------------------------------------------- |
| 产品分层        | AI 路径：Data Entry Agent（CRO PDF、CDMO 批记录、CoA、遗留 ELN/Word、不规则表）。确定性路径：Connect Runs + 仪器 parser + Registry 批量导入 |
| 写入位置          | 写入 Result / Registration / Plate·Box·Container 等结构化表，不是自由笔记；源文件挂在 Notebook Entry                           |
| 流程          | Plan（拆任务）→ 分块处理 → 多模型交叉校验 → 人 Approve 后再 insert                                                            |
| 上下文         | 当前打开的 Notebook Entry + 用户指令/示例。例如供应商样本号 `C1` 映射到租户 Registry ID `BNCH157`                                   |
| Entity Chip | 不是单独导入产品；写入实体链接字段后，平台渲染可跳转 Chip（可显示 Registry ID）                                                           |
| 下游          | 结构化之后，Ask / Deep Research 等 Agent 才能跨实验用                                                                   |
| 公开用例        | CRO 非临床表 → Results；CDMO 批记录按步骤路由 PD schema；CoA → 注册；遗留 ELN → 搜 schema 再映射                                  |


### E.2 概念映射（Benchling → 本 Spec）


| Benchling                         | 本 Spec（v0.4.3）                                          | 备注                                    |
| --------------------------------- | ------------------------------------------------------- | ------------------------------------- |
| Notebook Entry + Structured Table | ImportSession + 确认卡预览 / 库详情                             | 我们不以 ELN 页为权威；以库为准                    |
| Results / Registration schema     | write_channel: observation 或 master + LibraryProjection | 双写通道更硬，防止 assay 改 SMILES               |
| Entity Chip / Registry link       | SampleResolver → sample_id（MR-xxxx / Registry）          | Chip 是壳层 UX；Agent 负责填对链接              |
| Plan → Chunk → Verify             | ImportPlanProposal + Sheet/Table Hunt + 确认环节             | P0 以规则/模板为主；多模型 verify = Later/Should |
| Approve & insert                  | 两卡确认 + Committer；禁止静默覆盖                                  | 已一致，Must 保持                           |
| Connect parser 路径                  | 附录 H · allotropy 仪器路径（P2）                                | 开源 ASM 解析 + AsmMapper；不照搬 Connect 产品  |
| Entry 全文当上下文                      | Scene Pack.import + 桶声明 + 显式映射提案                        | 不要默认整页塞进模型（见 E.4）                     |


### E.3 可采纳（Adopt）


| 优先级          | 采纳点                        | 落入本 Spec                       | 说明                                                  |
| ------------ | -------------------------- | ------------------------------ | --------------------------------------------------- |
| Must（已有/强化）  | Schema-first：输出进投影槽，不进自由文本 | §1.1 · §5 · §6                 | 与「库是权威」一致；禁止「导入结果只落 Session 笔记」                     |
| Must（已有/强化）  | 人在回路：Approve 才 commit      | §7.3 · §8.1                    | 样本误挂 / 静默建库 = 0（§13）                                |
| Must（已有）     | ID 翻译显性化                   | SampleResolver + 卡 2           | 类似 C1→BNCH157；用映射表提案，不黑盒改写                          |
| Must（已有）     | 源文件留痕可反查                   | Artifact + Provenance · §10    | 对应 Entry 附件 + chip 溯源                               |
| Should       | Plan 阶段给出「行数/段落清单」给人核对     | §7.1 `ImportPlanProposal` 增补字段 | 防止 Planning 漏段/重复（Benchling 自承风险）                    |
| Should       | 大文件分块（按 sheet / 命名表 / 章节）  | §4 Sheet/Table Hunt · §11      | P0 先吃 xlsx 分 sheet；PDF Later 同构                     |
| Must（v0.4.3） | 同构反复导入走模板，AI 只建模板/版式对不上时重认 | §1.4 · §7.0 · §9.0             | CRO 固定版式走规则；AI 建模板/版式对不上时重认；仪器 Connect 类仍见附录 D（P2+） |
| Should       | 跨表/跨槽一致性检查                 | ProposedWrite 批次校验             | 他们检测跨表公式；我们做 sample×attr 冲突清单                       |
| Later        | 多模型交叉验证                    | 验收增强，非 P0 阻塞                   | 成本高；可用「规则校验 + 二次抽取抽检」替代                             |
| Later        | Compose→Import 衔接          | UX                             | 先有草稿 Entry/说明再导入，可选，非库入库必需                          |
| 勿照搬          | 默认把整本 Notebook 塞进模型上下文     | —                              | 噪音大、泄密面大；见 E.4                                      |
| 勿照搬          | 以 ELN 结构化表为权威终点            | —                              | 我们终点是化合物库/抗体库 + Ingress                             |
| 勿照搬          | 把「任意大型复杂文档分钟级」写成 P0 承诺     | §2 · §11                       | P0 锁定 xlsx；PDF/CDMO 长文档分阶段                           |
| 勿照搬          | 把 Entity Chip 当成差异化本身      | —                              | 差异化在 SampleResolver、双写通道、合规闸                        |


### E.4 Benchling 暴露的问题 → 规避 / 新方案


| #   | 暴露问题（官方或可推断）                  | 我们的规避或替代方案                                                                                        | Spec 落点                                |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 1   | Planning 漏行/重复/漏段             | Plan 必须输出：拟处理 sheet/table 列表、预计行数、跳过段及原因；确认闸展示 diff；总行数不符 → 阻断或强制人勾选                              | §7.1 Proposal；§13 可加「计划行数误差」指标（Should） |
| 2   | 分块后跨块主键/轴不一致                  | 分块前跑 AxisSniffer + SampleKey 全局签名；块间用同一 `sample_link_rules`；跨块冲突进卡 2，禁止块内各裁各的                     | §4 · §8                                |
| 3   | 错行错列（邻行邻列取值）                  | LLM 不算数：ValueExtract 须带 `artifact_ref_slice`（sheet!cell）；确认卡预览「源 cell → 值」；完全匹配时以模板坐标为主           | §1.1.6 · §7 · §13 反查 100%              |
| 4   | PDF 文本层烂（上下标、双栏）              | P0 不做 PDF 主源；P1.5+ 按附录 I：L1 模板 / L2 ROI / L3 OCR 分档，不承诺通用 PDF                                     | §11 · 附录 I · §2.3                      |
| 5   | 过大过复杂直接失败或静默错                 | 显式限额：单文件 sheet 数 / 行数 / 体积；超限 → 引导拆文件或走模板快通道；失败要可诊断错误码，禁止半成功写入                                    | §6.4 错误码；§14 P0.1                      |
| 6   | 整 Entry 上下文 → 噪音与泄密           | 默认上下文 = `scene.import` + 本 Session 上传物 + 用户勾选的说明段落；禁止默认上传历史附件全文；监管项目可关云端 LLM                      | §3 · AutonomyMatrix（既有）                |
| 7   | Chip/实体详情 Agent 不可见 → 映射猜错    | SampleResolver 只查库 API，不靠笔记里偶发出现的 ID；多候选必须 propose_confirm；零命中不建样                                 | §8 · §13                               |
| 8   | 表类型限制过死，能抽却写不进库               | LibraryProjection 预先声明可写槽；桶 `supplies_*` 越权 Committer 拒绝；未知列单独处理，不假装写入                            | §3.2 · §10.2                           |
| 9   | 自定义指令还没产品化成可共享模板              | 映射要存成 ImportTemplate（签名命中），不是聊天 prompt；Scene Pack.import 版本化进配置库                                  | §3 · §7 TemplateMatch                  |
| 10  | AI 轨与仪器轨混谈，客户预期膨胀             | 对内/对外口径分开：模板/parser = 默认路径；Agent = 未见过文件的提议器；汇报不承诺「任意 CDMO 批记录一次吃完」                               | 跟商业口径一致；本附录 E.3 勿照搬                    |
| 11  | 交叉验证仍非正确保证，易过度信任 UI           | UI 文案写 `propose` 非 `truth`；高风险字段（剂量、单位、sample_id）默认分卡 + 必勾「已核对源 cell」；可选二次规则：单位维、轴枚举、CAS checksum | §7.3 · §9                              |
| 12  | CDMO/长文档「按步骤路由」依赖成熟 PD schema | 我们 P0 不接 CDMO；若将来做，按桶 × 工艺步骤模板配置，而不是一次让模型读完整本书                                                    | 附录 D；非 P0                              |


### E.5 建议写入流水线的增量（相对 v0.4.1，非全量 P0）

下列为 Should 级增强，实施排期挂 §14，不扩大 P0 文件格式：

1. `ImportPlanProposal.coverage`：`sheets_planned[]` · `estimated_rows` · `skipped_regions[]` · `chunk_plan`
2. 上下文清单（ContextManifest）：显式列出送入模型的字段（scene 配置摘要、本文件、用户指令）；审计可回放
3. 冲突清单统一对象：字段冲突 / 样本多候选 / 跨块不一致 → 同一确认 UX
4. 双轨入口文案：上传页区分「已知模板（快）」vs「智能提议（慢，须确认）」

### E.6 决策摘要（给评审）


| 问题                            | 结论                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------- |
| 要不要学 Benchling 做 PDF CRO 分钟级？ | P0 否。P1.5+ 按附录 I 模板/ROI/OCR 分档，不接「任意 PDF」                                     |
| 要不要多模型 verify？                | Later/Should。P0 用证据链 + 人审 + 规则                                                |
| 最该跟谁一致？                       | Schema/库权威、Approve、实体对应关系要看得见（骨架已有）                                           |
| 最该避开的？                        | 整页上下文黑盒翻译；把 ELN 当真理；宣传超工程能力                                                   |
| 相对 Benchling 差在哪？             | 库双写通道（master/observation）、ObservationIngress、Sample 锚化合物/抗体库、合规确认闸。不是 Chip UI |
| CRO 怎么提效？                     | 反复导入走模板，不必每次用 AI 拆表（§1.4）；命中后少调 LLM；确认过的映射必须写成 ImportTemplate                       |


---

## 附录 F · 导入模式 · 样本策略 · 流程配置

> §8.4 写的是 P0 必做的模式与策略。这里补充：步骤怎么拆、流程配置以后能不能配（Later / P2）。规则引擎按步骤跑；LLM 只提议流程配置，人确认后再执行。写库环节和确认环节，流程配置关不掉。

### F.1 允许的步骤


| 步骤 id                    | 职责                            | 可否跳过             |
| ------------------------ | ----------------------------- | ---------------- |
| SelectBucket             | 选桶 / 通道                       | 否（必须有桶）          |
| MatchTemplate            | 完全匹配 / 部分匹配 / 对不上             | 否                |
| MapFields                | 字段映射                          | 否                |
| ResolveAxes              | 轴与单位                          | 否（无必需轴的桶可空跑）     |
| ResolveSample            | 样本解析（读 sample_policy）         | 否                |
| ExtractValues            | 抽值 + 证据 cell                  | 否                |
| Confirm                  | 导入确认（C2 特化）                   | 不可跳过             |
| CommitRegistry           | Committer → Ingress / 主数据     | 不可跳过             |
| LocateRoles              | 标出结果表 / 方法 / 证据 / 包元数据角色（§16） | 多实体配方不可跳过；其它配方可空跑 |
| ExpandResultRows         | 结果表 → result_rows[]（§16）     | 多实体配方不可跳过；单行表可退化 1 行 |
| ElnWriteback             | 同步实验记录（附录 G）                  | 可（无 ELN 或用户不勾选）  |
| ParseInstrumentAllotropy | 仪器导出 → ASM（附录 H）              | 可（仅仪器桶 / 用户选仪器轨） |
| MapAsmToProjection       | ASM → attr_key / 轴 / 样本键      | 跟上一仪器步骤绑定；不能单跳确认 |
| DetectArtifactKind       | 判主源/附件/OCR；数字 PDF vs 扫描（附录 I） | 主源为 PDF/图时不可跳过   |
| ParsePdfTables           | PDF → 逻辑表（L1/L2）              | 可（仅 PDF 主源）      |
| ParseImageTable          | 拍表图 → 逻辑表（图片 B）               | 可（仅拍表主源）         |
| RequireRoi               | L2/L3/拍表：无人框选则阻断抽值            | 与上绑定；条件触发时不可跳过   |
| PublishTemplate          | 保存/升级模板                       | 可                |


流程配置不能加表外步骤（尤其「直接写库」「跳过确认」）。

### F.2 内置流程配置（P0 用模式表达即可）


| recipe_id             | 对应模式       | 要点                                                        |
| --------------------- | ---------- | --------------------------------------------------------- |
| historical_strict     | 历史导入       | require_registered=true；on_miss 为 block_row 或 abort_batch |
| design_writeback      | 设计台回写      | prefer_context_sample_id=true；入口预填分子                      |
| **multi_entity_report** | 上述模式之一 + §16 | LocateRoles → ExpandResultRows → 逐行 ResolveSample；默认可挂 with_eln |
| with_eln（P1）          | 上述任一 + ELN | Confirm 后跑 ElnWriteback                                   |
| pdf_l1_template（P1.5） | PDF L1     | DetectArtifactKind → ParsePdfTables → … → Confirm         |
| pdf_l2_roi（P2）        | PDF L2     | RequireRoi 后 ParsePdfTables                               |
| image_table_ocr（P2）   | 拍表图        | ParseImageTable + 强制确认；默认无完全匹配快通道                         |
| pdf_l3_scan（P3）       | 扫描 PDF     | 标页 → OCR → RequireRoi/确认；租户开关                             |


`multi_entity_report` 可与 `historical_strict` / `design_writeback` 组合（模式管样本策略，配方管行展开）。禁止本配方关闭 Confirm / CommitRegistry，或把结果表整表写入 master。

P0 不必做流程配置编辑器；实现上用模式枚举，内部对应固定步骤顺序即可。

### F.3 用户配置与 LLM（Later / P2）

1. 管理端编辑 Recipe（步骤开关、policy、默认桶/方法模板）→ 版本化进租户配置。
2. 用户自然语言 / Copilot / 上传页 IntentHint：data_import 意图 → LLM 输出候选 recipe_id + 参数（仅白名单步骤）→ **计划卡**人确认 → Session 记下 resolved_recipe。
3. 跑的时候仍是确定性流程引擎；局部未知列可以智能提议，但不能改 Commit / Confirm 约定。
4. **模板完全匹配 → 不调用编排 LLM**（§1.4）；编排只服务对不上、部分匹配未知列、或用户点「重新识别」。

### F.4 能力编排边界（Must）

| 允许 | 禁止 |
| --- | --- |
| 从 F.1 白名单组装有序步骤 + 参数 | 生成 SkipConfirm / DirectWrite / 表外步骤 |
| 按 ContentClass 预填桶与默认 recipe | 用 IntentHint 扩大 supplies_* 或改 write_channel |
| 计划卡上展示并给人改桶/步骤开关（仅允许跳过的步骤） | 关掉 Confirm / CommitRegistry |
| 命中模板后跳过编排 | 每份文件强制全量 LLM 编排 |

对外可称步骤为 **ImportCapability**；与 F.1 步骤 id 一一对应。

---

## 附录 G · ELN 回写与目标位置勾选

> 分期：P1 起。没有 ELN 的租户可以把整附录关掉。  
> 原则：观测数据仍以库里的 ObservedValue 为准；ELN 放方法说明、原始附件、结果摘要或链接。  
> **导入目标位置勾选：** 确认卡话术可做成「写入位置 / 按内容分流」的感觉；底层是库必写 + ELN 可选，不是二选一。见 CONTEXT。

### G.1 一次确认，两边落账

```
导入确认通过
  → CommitRegistry（Must）→ Ingress / 库
  → ElnWriteback（可选）
       ├─ 绑定已有实验记录，或按模板新建
       ├─ 挂主源 Artifact（同一 artifact_id）
       ├─ 写入/预填方法（方法模板或经确认的摘录）
       └─ 插入结果摘要表或深链到库观测
```

禁止：只写 ELN、不写库，却说「观测已入库」。  
禁止：在 ELN 再存一份可修改、且与库对不上的观测表。

### G.2 三种挂法


| 模式          | 行为                     | 分期               |
| ----------- | ---------------------- | ---------------- |
| 绑定已有 Entry  | 用户选实验记录 ID；回写附件 + 结果链接 | P1 Must（有 ELN 时） |
| 导入时新建 Entry | 按桶/方法模板生成记录骨架          | P1.1 Should      |
| 仅深链         | ELN 只插「本批已导入，点此看库」     | P1 兜底            |


### G.3 确认卡勾选（导入目标位置勾选）

```
写入位置（话术可按内容分流展示）
[✓] 化合物库 · 结构化观测 / 读数（必选，不可关闭）
[ ] 实验记录 · 方法说明 / 附件 / 结果链接（可选）
      ○ 绑定已有：[搜索…]
      ○ 新建记录：模板 […]  方法 […]
      [✓] 附带原始文件
      [✓] 在记录中插入结果摘要（链到库）
```

无 ELN 租户：只显示库一行。  
禁止：只勾选 ELN、不写库，却显示「已入库」。

历史严格模式下：未注册分子仍按 §8.4 阻断；不要先建空 ELN 再导数据。

### G.4 幂等与失败


| 情况                | 行为                              |
| ----------------- | ------------------------------- |
| 同 content_hash 再导 | 库幂等；ELN 不重复建 Entry，可提示已关联记录     |
| 库成功、ELN 失败        | 库已成功 + Notice「ELN 失败，可补同步」      |
| 补同步               | 对已有成功 Session 提供「补同步到实验记录」，不重抽数 |
| 库观测 supersede     | ELN 摘要标更新或刷新链接；不自动改已签字方法正文      |


### G.5 与 Ingress eln 通道

- 导入 → ELN 回写（本附录）：以文件导入为主，结果进库，笔记侧补充说明和链接。
- ELN → Ingress：实验在 ELN 做完后，再推/拉观测进库（主规格里已有这条通道）。

两条路径配合使用，不是互相替代；同一 (sample, attr, axes) 的冲突规则与 §10.4 相同。

---

## 附录 H · 仪器解析（allotropy）

> **分期：** P2（P0 仍以 CRO/湿实验 xlsx 模板路径为主）。  
> **开源库：** [Benchling allotropy](https://github.com/Benchling-Open-Source/allotropy)（MIT）。  
> **支持列表：** [SUPPORTED_INSTRUMENT_SOFTWARE.adoc](https://github.com/Benchling-Open-Source/allotropy/blob/main/SUPPORTED_INSTRUMENT_SOFTWARE.adoc)。  
> **用途：** 仪器软件导出的文本/Excel → Allotrope Simple Model（ASM）JSON → 再经 AsmMapper 进本模块的确认环节和写库。  
> **不做：** 私有二进制解析、厂商客户端联机、替代 CRO 业务表模板路径、跳过导入确认。

### H.1 能力边界


| 项    | 说明                                                                     |
| ---- | ---------------------------------------------------------------------- |
| 输入   | 仪器软件导出的 txt / csv / xlsx 等（库本身不解析专有二进制）                                |
| 调用约定 | 必须指定 Vendor 枚举；见下方用法                                                   |
| 输出   | 符合 ASM（或库内标注的 BENCHLING/ 变体）的 JSON dict                                |
| 成熟度  | 列表分 Recommended / Candidate Release / Working Draft；生产默认只开 Recommended |
| 与模板路径 | 并行：仪器桶走本附录；CRO 报告仍走 §7 模板匹配 / 智能提议                                     |


### H.2 如何使用（工程用法）

#### H.2.1 安装

```
pip install allotropy
```

要求 Python ≥ 3.10。版本写死在后端依赖锁文件里；升级要拿 Top Vendor 样例集做回归。

#### H.2.2 基本转换

官方入口（见仓库 README）：

```
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file, allotrope_from_io

# 本地路径
asm = allotrope_from_file("softmax_export.txt", Vendor.MOLDEV_SOFTMAX_PRO)

# 上传流（导入服务推荐）
asm = allotrope_from_io(uploaded_file_stream, Vendor.MOLDEV_SOFTMAX_PRO)
```

要点：

1. 第二个参数必须是 `Vendor` 中某一项（与支持列表中的 Instrument Software 对应）。
2. 返回值是 dict，可序列化成 JSON Artifact 存档备查。
3. 解析失败 → 给出明确错误码（vendor_mismatch / parse_error），引导用户改选 Vendor 或改走模板/AI 轨；禁止静默当成空表提交。

#### H.2.3 Vendor 怎么定（产品侧）

官方 API **不会**自动猜 Vendor。本模块允许三种方式（可组合）：


| 方式     | 行为                                                        | 建议          |
| ------ | --------------------------------------------------------- | ----------- |
| 用户手选   | 上传页「仪器软件」下拉（展示中文名，存 Vendor 枚举）                            | P2 Must     |
| 桶默认    | 桶配置 `default_allotropy_vendor`（如 SoftMax 专用桶）             | Should      |
| 试跑识别   | 在允许列表里依次试 1～N 个 Candidate，取第一个成功且通过 schema 校验的；多个都成功就给人确认 | Should      |
| LLM 提议 | 只提议 Vendor，人确认后再 parse                                    | Later（附录 F） |


租户/scene 维护 **InstrumentCatalog**：从 SUPPORTED 表同步类目、软件名、Vendor、Release Status、Detection Modes；未列入或 Working Draft 默认不对终端用户开放。

### H.3 接入本导入流水线

```
选桶（仪器类）或用户勾选「仪器原始导出」
  → 确定 Vendor（H.2.3）
  → ParseInstrumentAllotropy：allotrope_from_io → asm_dict
  → 将 asm_dict 存为 Session Artifact（content_hash 可含 asm 规范化后哈希）
  → MapAsmToProjection：ASM → ProposedWrite 草案（attr_key / axes / 单位 / 样本键）
  → 卡 1 字段映射 + 卡 2 样本对齐（§7.3 / §8.4 仍适用）
  → Confirm → CommitRegistry
  → （可选）ElnWriteback：挂原始导出 + ASM JSON
```

与 CRO 模板路径怎么分（Must）：


| 信号                              | 路径                      |
| ------------------------------- | ----------------------- |
| 桶声明 `parser: allotropy` 或用户选仪器路径 | 附录 H                    |
| 桶为 pk_in_vivo 等业务报告             | §7 模板 / AI              |
| allotropy 失败且用户同意               | 可降级为智能提议或手选模板；审计里记录降级原因 |


### H.4 AsmMapper（需要自己实现）

allotropy 只产出 ASM，**不**写化合物库。映射层按仪器**类别**自己实现（优先少套适配器）：


| 类目（示例）            | 典型 Vendor                         | 映射关注点                           |
| ----------------- | --------------------------------- | ------------------------------- |
| Plate Reader      | SoftMax Pro、Gen5、SkanIt、Envision… | 孔位/样品 ID、读数、波长、单位 → attr + axes |
| qPCR              | QuantStudio、CFX Maestro           | 靶标、Ct/拷贝、孔板样号                   |
| Spectrophotometry | NanoDrop、Qubit、Genesys            | 浓度/吸光、样品名                       |
| 其他                | 流式、LC、细胞计数等                       | 按客户 PoC 再开类别                    |


映射规则（Must）：

1. 目标槽 ∈ 本桶 supplies_attr_keys ∩ LibraryProjection。
2. 单位走 §7.5；换不了则该行不可 map。
3. 样品标识进 sample_key / 卡 2，禁止当成观测 attr 乱写。
4. 确认卡要能展开「ASM 路径 → 源值示例 → 目标属性」（跟 §7.3.1 的源列/示例同级）。
5. ASM schema 版本（REC/…、BENCHLING/…）写入 Session；升级 allotropy 要回归映射表。

### H.5 内置流程配置（对应附录 F）


| recipe_id                | 要点                                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------- |
| instrument_allotropy     | parser=allotropy；步骤含 ParseInstrumentAllotropy → MapAsmToProjection → … → Confirm → Commit |
| instrument_allotropy_eln | 上式 + ElnWriteback（挂原始文件与 ASM）                                                             |


可以与 historical_strict / design_writeback 的 sample_policy 组合（例如设计台回写 + SoftMax 导出）。

### H.6 实施清单（建议顺序）

1. 对照 SUPPORTED 表，跟客户定 Top 3～5 Vendor（只开 Recommended）。
2. 用真实导出跑 `allotrope_from_file`，人工看 ASM 字段够不够映射。
3. 做 InstrumentCatalog + 上传页 Vendor 选择。
4. 先实现一类 AsmMapper（建议 Plate Reader）。
5. 挂进导入 Session：Artifact（原始 + ASM）→ 确认卡 → Ingress。
6. 失败与降级、幂等（同文件同 Vendor 同 hash 不重复写）。
7. （可选）ELN 挂附件；再扩 qPCR / NanoDrop 类目。

### H.7 验收（P2）


| 指标                        | 目标                   |
| ------------------------- | -------------------- |
| 允许列表内样例文件 parse 成功率       | ≥ 95%（按 Vendor 分桶统计） |
| 未选 Vendor 却调用 allotropy   | 0                    |
| ASM 没映射完就静默 Commit        | 0                    |
| 列表外/二进制文件被当成成功仪器导入        | 0                    |
| 详情能反查到原始导出 + ASM Artifact | 100%                 |


### H.8 参考链接

- 仓库：[https://github.com/Benchling-Open-Source/allotropy](https://github.com/Benchling-Open-Source/allotropy)  
- 支持仪器：[https://github.com/Benchling-Open-Source/allotropy/blob/main/SUPPORTED_INSTRUMENT_SOFTWARE.adoc](https://github.com/Benchling-Open-Source/allotropy/blob/main/SUPPORTED_INSTRUMENT_SOFTWARE.adoc)  
- PyPI：[https://pypi.org/project/allotropy/](https://pypi.org/project/allotropy/)  
- Allotrope 概述：[https://www.allotrope.org/product-overview](https://www.allotrope.org/product-overview)  
- 本 Spec 附录 E：Benchling Connect / AI 导入对照（战略语境）

---

## 附录 I · PDF / 图片解析

> **分期：** P0 仅附件/证据预览；主源抽数自 **P1.5**（PDF L1）起，见 §14。  
> **原则：** 先分角色，再分可解析性；确认环节与写库环节关不掉；不承诺任意 PDF / 任意照片分钟级入库。  
> **分流：** 仪器软件**原始导出**（txt/csv/xlsx）→ 附录 H；**仪器/CRO 报告 PDF** 与拍表图 → 本附录。按桶或 `parser` 声明分流，不混谈。

### I.1 角色（Must）


| 角色         | 含义                          | 是否抽数写库                    |
| ---------- | --------------------------- | ------------------------- |
| **主源**     | 参与识别、映射、抽值、幂等 hash          | 是                         |
| **证据附件**   | 留痕、预览、可挂观测/ELN；不进 FieldHunt | 否（或只补 `image`/`curve` 证据） |
| **OCR 辅源** | 扫描件/拍表「猜」表；须框选或人确认          | 是；默认 AI 提议 + 高摩擦确认        |


产品口径：xlsx / 可抽取 PDF 走快路径；扫描件和照片默认慢路径；纯图证据不当表格主源。

```
上传
  → DetectArtifactKind
       ├─ 主源 xlsx/csv → §7 模板 / AI
       ├─ 主源 数字 PDF（L1/L2）→ ParsePdfTables（L2 先 RequireRoi）
       ├─ 主源 扫描 PDF（L3）/ 拍表图 → OCR 辅源路径
       ├─ 仪器导出 → 附录 H
       └─ 证据附件 → 挂 Artifact，不进 FieldHunt
  → MapFields → ResolveSample → Confirm → Commit
```

### I.2 PDF 分层（按可解析性，不是只看扩展名）


| 层      | 判定              | 路径                                                                                                  | 分期                        |
| ------ | --------------- | --------------------------------------------------------------------------------------------------- | ------------------------- |
| **L1** | 有可选中文本，表格可检出    | ParsePdfTables → 逻辑伪 sheet/table → 复用 FieldHunt；模板签名可用 `vendor + page_set + header_fingerprint` 或锚点 | P1.5：先 1～2 个固定 CRO PDF 模板 |
| **L2** | 文本烂 / 双栏 / 上下标乱 | **Must** 人框选 ROI 或指定「本页哪张表」后再抽；禁止无 ROI、无模板时整本塞模型后静默 Commit                                          | P2                        |
| **L3** | 扫描纯图页           | 逐页预览 → 用户标含数据页 → OCR → 提议表结构；确认卡展示「页/框 → 值」；验收与 L1 **分开报**                                          | P2 后 / P3；租户可关云端 OCR      |


PDF 与确认环节：

- 标量可比行：确认通过即可 `active`（同 §7.3）。  
- 报告内嵌图谱：标量走观测；图作证据或 `kind=image/curve`；图谱核对仍继承通用 C2，不跳过。  
- 方法正文：默认不入库为观测；经确认可摘进 ELN（附录 G）；禁止免确认抽取方法作为真理。

### I.3 图片两类用途（Must 拆开）


| 类                | 典型         | 行为                                                                                  | 分期             |
| ---------------- | ---------- | ----------------------------------------------------------------------------------- | -------------- |
| **A · 证据图**      | 凝胶、光谱截图、峰图 | png/jpeg/webp/tiff；挂附件或与已抽标量同行的 image 证据；**不**把整图当 Excel                            | P0 附件；P1 绑定 UX |
| **B · 拍表 / 截图表** | 仪器屏、打印表拍照  | ParseImageTable → 伪 table → **强制**卡 1/卡 2；高风险字段必勾「已对照原图」；默认无完全匹配快通道（弱签名仅提示「疑似再来一张」） | P2             |


明确不做：

- 手写笔记任意识别作为主源  
- 化学结构图 OCR 直接当 SMILES 静默注册（结构走注册向导 / 专用能力）  
- 多张图自动拼成一张总表且无人切分（多图 = 多 Session，或 Later 多主源合并）

### I.4 证据切片与确认卡（Must）

- 切片形态见 §6.1；PDF/图主源写入的每一条 ProposedWrite 必须带可反查切片。  
- 卡 1「示例」列：PDF/图 Must 能预览源页/源图裁切（§7.3.1）。  
- L2/L3/拍表：无 ROI（或未标数据页）→ 阻断 ValueExtract，错误码可诊断。

### I.5 限额与租户开关（Must / Should）


| 项                     | 规则                            |
| --------------------- | ----------------------------- |
| 页数 / 体积 / 像素 / OCR 页数 | 显式上限；超限 → 拆文件或改传 xlsx；禁止半成功写入 |
| 云端多模态 / OCR           | 监管或租户可关；降级为「仅附件」或本地 OCR（若有）   |
| 文案                    | 慢路径禁止「已自动识别正确」                |


### I.6 与附录 H / 模板路径


| 信号                            | 路径                      |
| ----------------------------- | ----------------------- |
| 桶 `parser: allotropy` 或仪器原始导出 | 附录 H                    |
| 桶为业务报告 PDF / 用户选 PDF 主源       | 本附录                     |
| 拍表图主源                         | 本附录图片 B                 |
| PDF/OCR 失败且用户同意               | 可降级为附件留痕或改传 xlsx；须记录审计原因 |


### I.7 验收（与 §13 分报，避免稀释 xlsx 指标）


| 指标                    | 目标   |
| --------------------- | ---- |
| L1 固定模板：抽数可反查到页/框     | 100% |
| L1 无模板静默 Commit       | 0    |
| L3 / 拍表：无 ROI 或未确认就写入 | 0    |
| 证据图被误标主源并整图当表写入       | 0    |
| 详情反查主源 + 附件列表         | 100% |


---

## 附录 J · 错误码清单

> **v0.4.22 新增。** 所有组件错误统一编码，确认卡和 Notice 展示错误码 + 人话解释 + 建议动作。  
> 前缀按组件分组，编号按发现顺序递增。实现时按此清单扩展，不允许表外自定义错误码。

### J.1 文件解析（IMP-PARSE）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-PARSE-001` | 文件无有效数据（空表/全空行） | 检查文件内容，确认有数据行 |
| `IMP-PARSE-002` | 表头行有重复列名 | 修改源文件列名使其唯一，或在确认卡手动区分 |
| `IMP-PARSE-003` | 编码检测失败 | 手动选择文件编码（UTF-8 / GBK / Shift-JIS） |
| `IMP-PARSE-004` | 日期/时间格式无法解析 | 检查日期列格式，统一为标准格式 |
| `IMP-PARSE-005` | 浮点精度损失超阈值 | 检查源值精度，确认存储值可接受 |

### J.2 模板匹配（IMP-MATCH）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-MATCH-001` | 无模板命中 | 走 AI 提议路径，或联系 Admin 新建模板 |
| `IMP-MATCH-002` | 模板匹配分数低于阈值 | 检查文件版式是否变化，或点「重新识别」 |
| `IMP-MATCH-003` | 模板已退役 | 联系 Admin 确认替代模板 |

### J.3 样本解析（IMP-RESOLVE）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-RESOLVE-001` | 样本键零命中 | 检查样本标识是否正确，或先注册分子 |
| `IMP-RESOLVE-002` | 样本键多候选（>50） | 加辅助键缩小范围，或手动选样 |
| `IMP-RESOLVE-003` | 历史严格模式：未注册分子 | 先注册分子，再重新导入 |

### J.4 单位与轴（IMP-UNIT / IMP-AXIS）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-UNIT-001` | 单位不可换算 | 检查源单位与规范单位是否兼容 |
| `IMP-AXIS-001` | 必需轴缺失 | 在确认卡补全轴值，或跳过该行 |

### J.5 写库（IMP-COMMIT）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-COMMIT-001` | 通道越权（桶未声明的 attr_key/master_field） | 检查桶配置 `supplies_*` 与映射目标 |
| `IMP-COMMIT-002` | Ingress 写入失败 | 重试或联系管理员 |

### J.6 并发与冲突（IMP-CONFLICT）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-CONFLICT-001` | 并发 Session 同键冲突 | 该行已跳过，查看其他 Session 的写入结果 |
| `IMP-CONFLICT-002` | 确认期间 head 被修改 | 刷新确认卡，重新核对数据 |

### J.7 资源与降级（IMP-RESOURCE / IMP-DEGRADE）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-RESOURCE-001` | 并发 Session 数超限 | 等待其他 Session 完成后重试 |
| `IMP-RESOURCE-002` | 文件大小超限 | 拆文件后重新上传 |
| `IMP-RESOURCE-003` | 行数超限 | 拆 sheet 或走异步队列 |
| `IMP-RESOURCE-004` | Session 超时 | 重新上传文件 |
| `IMP-DEGRADE-001` | LLM 服务不可用 | 使用已知模板重试 |
| `IMP-DEGRADE-002` | 库 API 不可用 | 等待恢复后重试 |
| `IMP-DEGRADE-003` | Ingress 不可用 | Commit 排队中，等待通知 |
| `IMP-DEGRADE-004` | ELN 不可用 | 库写入成功，稍后补同步 |
| `IMP-DEGRADE-005` | 模板匹配服务不可用 | 降级为 AI 提议路径 |

### J.8 安全（IMP-SEC）

| 错误码 | 含义 | 建议动作 |
| --- | --- | --- |
| `IMP-SEC-001` | IntentHint 注入检测命中 | 修改补充说明，去除指令性语句 |
| `IMP-SEC-002` | 模板越权访问 | 联系 Admin 申请模板权限 |
| `IMP-SEC-003` | 无库许可 | 联系管理员开通化合物库 |

---

## 附录 K · LLM 数据安全

> **v0.4.23 新增。** 回应客户对"调用 LLM 会导致数据泄露"的担忧。  
> **核心原则：** 能不调就不调；调的时候最小化；租户可控制；全程可审计。

### K.1 LLM 在导入流程中的接触面（Must 明确）

| 环节 | LLM 是否参与 | 接触的数据 | 风险等级 |
|---|---|---|---|
| 模板完全匹配（`path=template`） | **不参与** | 零接触 | 无 |
| 模板部分匹配 — 未知列提议 | 参与 | 源列名 + 少量示例值 + 投影槽名 | 中 |
| AI 提议（`path=ai_propose`） | 参与 | 源列名 + 示例值 + 投影槽名 + IntentHint | 高 |
| IntentHint 理解 | 参与 | 用户补充说明文本 | 中 |
| 样本解析 SampleResolver | **不参与** | 走库 API 查询，不过 LLM | 无 |
| 值抽取 ValueExtract（规则轨） | **不参与** | 按模板坐标直接读 cell | 无 |
| 值抽取 ValueExtract（AI 轨） | 参与 | 源 cell 值 + 目标属性名 | 高 |

**关键事实：** 模板完全匹配路径（快通道）全程不调 LLM。反复导入同一 CRO 版式，第 2 次起零 LLM 调用。  
验收指标：`模板匹配路径出现 LLM 调用 = 0`。

### K.2 五层防线（Must）

#### 第 1 层：能不调就不调

```
模板完全匹配 → 规则轨 → 零 LLM 调用
                          ↓
              只有「对不上」和「部分匹配未知列」才调 LLM
```

- 模板签名命中 → 整条流水线确定性执行，LLM 完全不介入（§1.4 / §7.0）
- 反复导入同一 CRO 版式，第 2 次起零 LLM 调用
- 验收指标：`模板匹配路径出现 LLM 调用 = 0`

#### 第 2 层：调的时候最小化上下文

`ContextSanitizer` 组件在每次 LLM 调用前执行，只传入当前步骤所需的最小信息：

| 传入 | 不传入 |
|---|---|
| 源列名（如 `AUC_0_t`） | 完整源文件内容 |
| 投影槽名（如 `pk.auc_0_t`） | 化合物结构 / SMILES / CAS |
| 1-2 个示例值（脱敏后） | 客户项目号 / 报告编号 |
| IntentHint 结构化标签 | IntentHint 原文（防注入） |

**不传完整文件，只传列名和少量样本值。** 模型需要的是"这个列名应该映射到哪个槽"，不需要看到具体数据行。

#### 第 3 层：租户级数据策略

`ImportProfile.llm_data_policy` 三档（§3.1）：

| 策略 | 行为 | 适用客户 |
|---|---|---|
| `strict` | 示例值全部替换为占位符（`[VALUE_1]`）；列名保留；完全不传业务数据 | 监管严格 / 对 LLM 零信任 |
| `standard` | 过滤 PII（人名/邮箱），保留业务字段名和少量示例值 | 默认值；大多数客户 |
| `open` | 不过滤 | 内部环境 / 非敏感数据 |

`strict` 模式下，LLM 看到的是：

```
源列名: [COL_A], [COL_B], [COL_C]
目标槽名: pk.auc_0_t, pk.cmax, pk.half_life
请提议映射关系。
```

没有具体数值，只有结构信息。

#### 第 4 层：基础设施隔离

`ImportProfile.llm_deployment_mode`：

| 部署模式 | 数据流向 | 适用 |
|---|---|---|
| `private_vpc` | LLM 跑在客户 VPC 内（如私有 Ollama / Azure Private Endpoint），数据不出网 | `strict` 客户首选 |
| `dedicated_endpoint` | 用商业 LLM API 的私有端点，合同约定零训练/零日志保留 | `standard` 客户 |
| `shared` | 经 ContextSanitizer 脱敏后调用 | `open` 客户 |

- 私有化部署时，`strict` 模式自动生效
- 与 LLM 提供商签 DPA（Data Processing Agreement），明确零训练、零保留

#### 第 5 层：审计可追溯

每次 LLM 调用记录：

```json
{
  "session_id": "imp_20240724_001",
  "step": "MapFields",
  "path": "ai_propose",
  "llm_data_policy": "strict",
  "llm_deployment_mode": "private_vpc",
  "context_tokens_before_sanitize": 1200,
  "context_tokens_after_sanitize": 340,
  "fields_sent_to_llm": ["col_name_1", "col_name_2", "slot_name_a"],
  "sample_values_sent": ["[VALUE_1]", "[VALUE_2]"],
  "llm_response_summary": "proposed mapping: col_1→slot_a",
  "timestamp": "2024-07-24T10:30:00Z"
}
```

客户可以随时审计：哪些 Session 调了 LLM、送了什么、脱敏前后差异。

### K.3 客户应答框架（Must 内部培训）

当客户问"调用 LLM 会不会泄露我的数据"，按此结构回答：

#### 第一句：先给定心丸

> 导入 Agent 的常规路径（模板匹配命中时）**全程不调用 LLM**。只有第一次遇到新版式、或文件结构发生变化时，才会触发 AI 提议，且您可以控制它能看到什么。

#### 第二句：讲分级控制

> 我们提供三级数据策略：
> - **严格模式**：LLM 只看到列名，看不到任何数值；可以部署在您自己的网络内，数据不出您的 VPC。
> - **标准模式**：过滤个人信息，保留少量业务示例值用于映射提议。
> - **开放模式**：适用于非敏感数据。
>
> 默认是标准模式，您可以在租户设置中调整为严格模式。

#### 第三句：讲技术保障

> 即使走 AI 提议路径，系统也只会把**列名和 1-2 个脱敏示例值**送给模型，不会上传完整文件。所有 LLM 调用都有审计日志，您可以随时查看每次调用送了什么内容。

#### 第四句：讲合规

> 我们与 LLM 服务商签有数据处理协议（DPA），约定零训练使用、零日志保留。如果您需要，也可以选择私有化部署，LLM 完全运行在您的基础设施内。

#### 如果客户追问"那我的化合物结构/CAS 号会不会被看到"

> 不会。化合物结构、SMILES、CAS 号属于主数据（master channel），走注册向导而不走 LLM。导入 Agent 的 LLM 调用只涉及**列名映射**，不接触分子结构信息。在严格模式下，连 assay 数值都会被替换为占位符。

### K.4 验收指标（Must）

| 指标 | 目标 |
|---|---|
| 模板匹配路径出现 LLM 调用 | **0** |
| `strict` 模式下 LLM 上下文含业务数值 | **0** |
| 未签 DPA 的 LLM 端点被使用 | **0** |
| LLM 调用无审计日志 | **0** |
| 客户审计请求响应时间 | ≤ 24 h |

### K.5 与既有 Spec 的关系

- §1.1 原则 11（LLM 上下文最小化）→ 本附录 K.2 第 2 层
- §3.1 `llm_data_policy` → 本附录 K.2 第 3 层
- §3.5 IntentHint 注入防护 → 本附录 K.2 第 2 层（IntentHint 不原样传入）
- §7.0 / §7.0.1 模板匹配 → 本附录 K.2 第 1 层（能不调就不调）
- 附录 J 错误码 `IMP-SEC-*` → 本附录 K.2 第 3/4 层（策略与部署违规拦截）

---

**END v0.4.23**