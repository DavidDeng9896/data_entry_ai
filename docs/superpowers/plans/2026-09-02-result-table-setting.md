# AI 建表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在「新建结果表」弹窗右侧展开与导入一致的 AI 侧栏，从文件/对话生成内部列配置和可编辑 Skill 草稿，用户点「创建」后建表并可选保存未启用 Skill。

**Architecture:** 新建独立 schema 服务与 `/api/tables/schema/chat`（及 stream），不改导入填表提示词。前端扩展 `TableCreateDialog`：workspace + 侧栏，左侧「列配置 / Skill 草稿」页签。回写规则在后端 `compose_schema_response` 一次算完，前端只在 `intent=schema` 且 `columns` 非空时整份套用。

**Tech Stack:** FastAPI、unittest、Vue 3、现有 `file_parser` / SSE / `api.upload`。

## Global Constraints

- 抽列按内部规范翻译，不照抄源表头
- 入口只在「新建结果表」弹窗；侧栏交互对齐 `ImportDialog`（无 Skill 下拉）
- AI 只填草稿；点「创建」才落库
- 文件与文字可混用；列和 Skill 可手改或继续对话
- Skill 另存且不启用；建表成功 Skill 失败不回滚表
- 文件类型与导入相同，可多文件；全 sheet 都看；只抽结果列
- 不改 `/api/recognize/chat` 语义；不做已有表改表头、不自动导入行
- 自动化测试可 Mock；手工验收关 Mock 用真实文本模型
- 表名/描述：草稿已有则保留，除非用户明确要求改

---

### Task 1: schema 意图、解析、校验、回写

**Files:**
- Create: `backend/app/services/schema_intent.py`
- Create: `backend/app/services/schema_extract.py`
- Test: `backend/tests/test_schema_intent.py`
- Test: `backend/tests/test_schema_extract.py`

**Interfaces:**
- Produces: `classify_schema_intent(text: str, has_files: bool = False) -> Literal["schema","chat"]`
- Produces: `wants_meta_change(text: str) -> bool`
- Produces: `sanitize_columns(raw) -> list[dict]`
- Produces: `split_schema_reply(raw: str) -> tuple[str, dict | None]`
- Produces: `compose_schema_response(intent, reply, parsed, draft) -> dict`

- [ ] Write failing tests then implement (TDD)
- [ ] Commit `feat: add schema intent parse and writeback helpers`

### Task 2: schema chat 服务 + HTTP/SSE

**Files:**
- Create: `backend/app/services/schema_prompt.py`
- Create: `backend/app/services/schema_chat.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/tables.py`（`POST /schema/chat` 与 `/schema/chat/stream` 写在 `/{table_id}` 之前）
- Test: `backend/tests/test_schema_chat.py`
- Test: `backend/tests/test_schema_api.py`

**Interfaces:**
- Consumes: Task 1 helpers；`file_parser`；`ai_service._client/_complete`；`db.load_model_settings`
- Produces: `run_schema_chat(req) -> dict` 字段：`reply, intent, name, description, columns, skill_name, skill_md`
- Produces: `SchemaChatRequest` / 路由

- [ ] Mock：纯聊天出 Dog PK 列；问答不改列；0 列不清草稿（由 compose 返回空 columns）
- [ ] Stream 发出 `step`/`done`，done 含 intent
- [ ] Commit `feat: add schema chat API and mock`

### Task 3: 新建结果表弹窗 + 侧栏

**Files:**
- Modify: `frontend/src/api/index.js`（`schemaChat` / `schemaChatStream`）
- Modify: `frontend/src/components/TableCreateDialog.vue`

**Interfaces:**
- Consumes: `/api/tables/schema/chat/stream`、`/api/recognize/upload`
- Produces: 侧栏「建表助手」；左侧页签；`schema` 且 columns 非空时套用响应

- [ ] 布局对齐 ImportDialog workspace
- [ ] 创建：`POST /tables`；Skill 非空再 `POST /skills`，不 enable
- [ ] Commit `feat: AI assistant in create-table dialog`

### Task 4: 验收

- [ ] `cd backend && python -m unittest discover -s tests`
- [ ] 启动前后端；关 Mock 用真实 API 跑口述出列（若环境有 key）
