# AI Intent + Session Rules Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace keyword intent hard-routing with a short AI decision (`extract`/`answer`/`edit`/`clarify`), silently accumulate session rules for the import dialog, and full-replace preview rows on extract.

**Architecture:** New `intent_router.decide_action` runs before parse/chat. `ChatRequest.session_rules` round-trips with the frontend. Extract injects session rules above Skill. Clarify returns a natural-language question without reading files.

**Tech Stack:** FastAPI, existing OpenAI-compatible client, Vue ImportDialog, unittest.

## Global Constraints

- Session rules: this import session only; clear on dialog close; do not auto-save Skill.
- Extract overwrites preview table entirely.
- Uncertain → `clarify` in chat (no buttons).
- Empty send + files → force `extract`.
- Keep API `intent` values `recognize`/`chat`/`edit` for frontend compatibility (`extract`→`recognize`, `answer`/`clarify`→`chat`).

---

### Task 1: Intent router service + unit tests

**Files:**
- Create: `backend/app/services/intent_router.py`
- Create: `backend/tests/test_intent_router.py`

- [ ] Implement `IntentDecision`, `merge_session_rules`, `decide_action` (mock heuristics + live JSON).
- [ ] Tests: empty+files→extract; 快速分析+files+empty→extract; 为啥→answer; decimal+rows→edit; vague+rows→clarify; merge/clear rules.
- [ ] Commit

### Task 2: Schema + wire recognize router

**Files:**
- Modify: `backend/app/schemas.py` (`session_rules` on request/response)
- Modify: `backend/app/routers/recognize.py`
- Modify: `backend/tests/test_chat_stream.py`, `backend/tests/test_intent.py` (keep legacy helpers or point to router)

- [ ] `_classify_req` uses `decide_action`; empty+files short-circuit extract.
- [ ] Stream/JSON return updated `session_rules`.
- [ ] Commit

### Task 3: Inject session rules into extract/answer prompts

**Files:**
- Modify: `backend/app/services/ai_service.py`

- [ ] `_session_rules_section` + pass `session_rules` into `chat` / system prompt.
- [ ] Soften empty-table QA copy (no “没收到附件”).
- [ ] Commit

### Task 4: Frontend session_rules round-trip

**Files:**
- Modify: `frontend/src/components/ImportDialog.vue`

- [ ] `sessionRules` ref; send on chatStream; apply from done; clear on mount/close.
- [ ] Commit

### Task 5: Verify + PR

- [ ] `DATA_ENTRY_FORCE_MOCK=1 python3 -m unittest discover -s tests`
- [ ] Push + create/update PR
