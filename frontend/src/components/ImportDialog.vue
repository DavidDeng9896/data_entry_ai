<template>
  <div class="dialog-mask" @click.self="onMaskClick">
    <div class="workspace" :class="{ 'with-chat': chatOpen }">
      <!-- 左侧：导入弹窗主体 -->
      <div class="dialog">
        <div class="dialog-header">
          <span class="title">导入结果数据</span>
          <span class="assay-name">{{ tableName }}</span>
          <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
        </div>

        <div class="dialog-body">
          <div class="toolbar">
            <span class="tip">请批量填入需要进行导入的数据，确认后将进行导入校验。可用右侧 AI 助手对话识别与修正。</span>
            <div class="toolbar-right">
              <button v-if="!chatOpen" class="btn ai-btn" @click="openChat">
                <i class="ri-sparkling-2-line"></i> AI识别导入
                <span v-if="chatThinking" class="pulse-dot" title="助手仍在执行"></span>
                <span v-else-if="unreadDone" class="badge-dot" title="有新的识别结果"></span>
              </button>
            </div>
          </div>

          <div v-if="notice" class="notice" :class="noticeType">
            <i :class="noticeIcon"></i> {{ notice }}
          </div>

          <vxe-table
            ref="tableRef"
            class="data-table"
            border
            show-overflow
            keep-source
            :height="430"
            :data="tableData"
            :edit-config="{ trigger: 'dblclick', mode: 'cell', showStatus: true }"
            :mouse-config="{ selected: true, area: true }"
            :keyboard-config="{ isArrow: true, isDel: true, isEnter: true, isTab: true, isEdit: true }"
            :clip-config="{ isCopy: true, isCut: true, isPaste: true }"
            :valid-config="{ msgMode: 'full' }"
            :edit-rules="editRules"
            @edit-closed="onEditClosed"
          >
            <vxe-column type="seq" title="" width="50" align="center" :edit-render="null"></vxe-column>
            <vxe-column
              v-for="col in columns"
              :key="col.field"
              :field="col.field"
              :title="col.title"
              min-width="120"
              :edit-render="editorFor(col)"
            >
              <template #header>
                <span :class="{ 'required-mark': col.required }">{{ col.title }}</span>
                <span v-if="col.description" class="col-info" :title="col.description"><i class="ri-information-line"></i></span>
              </template>
              <template #edit="{ row }">
                <template v-if="col.type === 'select'">
                  <select v-model="row[col.field]" class="cell-editor">
                    <option value=""></option>
                    <option v-for="opt in col.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </template>
                <input v-else v-model="row[col.field]" class="cell-editor"
                  :type="col.type === 'number' ? 'number' : col.type === 'date' ? 'date' : 'text'" />
              </template>
            </vxe-column>
          </vxe-table>

          <div class="table-footer">
            <button class="btn ghost" @click="addRows(1)"><i class="ri-add-line"></i> 添加行</button>
            <button class="btn ghost" @click="clearInvalid"><i class="ri-eraser-line"></i> 清除标红</button>
            <span class="invalid-count" v-if="invalidCount > 0"><i class="ri-error-warning-line"></i> {{ invalidCount }} 个单元格待修正</span>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="confirmImport"><i class="ri-check-line"></i> 确认导入</button>
        </div>
      </div>

      <!-- 右侧：AI 会话侧栏（展开） -->
      <aside v-show="chatOpen" class="chat-drawer">
        <div class="chat-header">
          <span class="chat-title"><i class="ri-sparkling-2-line"></i> AI 导入助手</span>
          <select v-model="pickedSkill" class="skill-select" title="导入模板 Skill">
            <option value="">不使用模板</option>
            <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <button class="chat-close" type="button" title="收起助手（后台继续执行）" @click="collapseChat">
            <i class="ri-close-line"></i>
          </button>
        </div>

        <div class="chat-messages" ref="chatMsgs">
          <div v-if="!chatLog.length" class="chat-empty">
            <i class="ri-chat-smile-2-line"></i>
            <div>上传文件或描述规则（如单位换算、过滤对照），发送后识别填入左侧表格。结果不对可继续对话让我重新导入。</div>
          </div>
          <div v-for="(m, i) in chatLog" :key="i" :class="['chat-msg', m.role]">
            <div class="msg-bubble">
              <template v-if="m.fileChip">
                <i class="ri-file-text-line"></i> {{ m.content }}
              </template>
              <template v-else>{{ m.content }}</template>
            </div>
          </div>
          <div v-if="chatThinking" class="chat-msg assistant">
            <div class="msg-bubble thinking"><i class="ri-loader-4-line spin"></i> 思考中…</div>
          </div>
        </div>

        <div class="chat-input-row">
          <label class="attach-btn" title="上传文件">
            <input type="file" ref="fileInput" style="display:none" @change="onFileChange"
              accept=".xlsx,.xls,.csv,.tsv,.pdf,.png,.jpg,.jpeg,.txt,.md" />
            <i class="ri-attachment-2"></i>
          </label>
          <div v-if="chatFileId && chatFile" class="file-chip" :title="chatFile.name">
            <i class="ri-file-text-line"></i>
            <span class="file-chip-name">{{ chatFile.name }}</span>
            <i class="ri-close-line file-chip-x" @click.stop="clearFile" title="移除文件"></i>
          </div>
          <input v-model="chatInput" class="chat-input"
            :placeholder="chatFileId ? '继续提要求，或说「重新识别导入」' : '输入规则或要求，Enter 发送'"
            @keydown.enter.exact.prevent="sendChat" :disabled="chatThinking" />
          <button class="send-btn" @click="sendChat" :disabled="chatThinking || (!chatInput.trim() && !chatFileId)">
            <i class="ri-send-plane-fill"></i>
          </button>
        </div>
      </aside>

      <!-- 收起后的侧边把手：可点开；思考中显示状态 -->
      <button
        v-if="!chatOpen && chatSessionStarted"
        type="button"
        class="chat-handle"
        :class="{ busy: chatThinking, done: unreadDone }"
        @click="openChat"
        :title="chatThinking ? '助手执行中，点击展开' : '展开 AI 导入助手'"
      >
        <i class="ri-sparkling-2-line"></i>
        <span v-if="chatThinking" class="handle-label">执行中</span>
        <span v-else-if="unreadDone" class="handle-label">有结果</span>
        <span v-else class="handle-label">助手</span>
      </button>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { api } from '../api'

const props = defineProps({
  tableId: { type: Number, required: true },
  tableName: { type: String, default: '' }
})
const emit = defineEmits(['close', 'imported'])

const tableRef = ref(null)
const columns = ref([])
const tableData = ref([])
const skills = ref([])

const chatOpen = ref(false)
const chatSessionStarted = ref(false) // 曾经打开过；收起后仍保留会话
const chatLog = ref([])
const chatInput = ref('')
const chatFile = ref(null)
const chatFileId = ref(null)
const chatThinking = ref(false)
const chatMsgs = ref(null)
const pickedSkill = ref('')
const unreadDone = ref(false) // 收起期间完成识别时提示
const fileInput = ref(null)

const notice = ref('')
const noticeType = ref('info')
const invalidMap = ref(new Map())

const invalidCount = computed(() => invalidMap.value.size)

const noticeIcon = computed(() => ({
  info: 'ri-information-line',
  success: 'ri-checkbox-circle-line',
  warning: 'ri-alert-line',
  error: 'ri-error-warning-line'
}[noticeType.value] || 'ri-information-line'))

onMounted(async () => {
  await loadColumns()
  skills.value = await api.listSkills()
  const enabled = skills.value.find(s => s.enabled)
  if (enabled) pickedSkill.value = enabled.id
  addRows(14)
})

async function loadColumns() {
  columns.value = await api.getColumns(props.tableId)
}

async function reloadColumns() {
  await loadColumns()
}
defineExpose({ reloadColumns })

const editRules = computed(() => {
  const rules = {}
  for (const c of columns.value) {
    const list = []
    if (c.required) list.push({ required: true, message: `${c.title} 必填` })
    if (c.type === 'number') list.push({
      validator: ({ cellValue }) => cellValue === '' || cellValue == null || !isNaN(Number(cellValue)) ? true : new Error('必须为数字')
    })
    if (c.type === 'select' && c.options.length) list.push({
      validator: ({ cellValue }) => !cellValue || c.options.includes(cellValue) ? true : new Error('存在内容与选项不匹配')
    })
    if (list.length) rules[c.field] = list
  }
  return rules
})

function editorFor() {
  return { autofocus: '.cell-editor' }
}

function addRows(n) {
  for (let i = 0; i < n; i++) {
    const row = {}
    for (const c of columns.value) row[c.field] = ''
    tableData.value.push(row)
  }
}

function openChat() {
  chatOpen.value = true
  chatSessionStarted.value = true
  unreadDone.value = false
  nextTick(scrollChat)
}

function collapseChat() {
  // 只收起 UI，不中断 chatThinking / 不丢会话与 file_id
  chatOpen.value = false
}

function onMaskClick() {
  // 点遮罩不强制关助手会话；仅关闭整个导入弹窗由 header/取消负责
}

function clearFile() {
  chatFile.value = null
  chatFileId.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function onFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  chatFile.value = f
  api.upload(f).then(up => {
    chatFileId.value = up.file_id
    chatLog.value.push({ role: 'user', content: f.name, fileChip: true })
    scrollChat()
  }).catch(err => {
    notice.value = `文件上传失败：${err.message}`
    noticeType.value = 'error'
  })
}

async function sendChat() {
  const text = chatInput.value.trim()
  if (!text && !chatFileId.value) return
  if (chatThinking.value) return

  chatSessionStarted.value = true
  if (text) {
    chatLog.value.push({ role: 'user', content: text })
    chatInput.value = ''
  }

  chatThinking.value = true
  scrollChat()
  try {
    const res = await api.chat({
      messages: chatLog.value
        .filter(m => !m.fileChip)
        .map(m => ({ role: m.role, content: m.content })),
      columns: columns.value,
      skill_id: pickedSkill.value || null,
      file_id: chatFileId.value
    })
    chatLog.value.push({ role: 'assistant', content: res.reply })
    if (res.rows && res.rows.length) {
      applyRows(res.rows, { replace: true })
      notice.value = `AI 识别完成，填入 ${res.rows.length} 行（可继续对话修正后重新导入）`
      noticeType.value = 'success'
      await validateAll()
      if (!chatOpen.value) unreadDone.value = true
    }
    scrollChat()
  } catch (e) {
    chatLog.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    scrollChat()
  } finally {
    chatThinking.value = false
  }
}

function scrollChat() {
  setTimeout(() => {
    if (chatMsgs.value) chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
  }, 30)
}

/** replace=true：重新导入时清空并重填，避免叠在旧行上 */
function applyRows(rows, { replace = true } = {}) {
  if (replace) {
    tableData.value = []
    addRows(Math.max(rows.length, 14))
  }
  let idx = tableData.value.findIndex(r => columns.value.every(c => !r[c.field]))
  if (idx === -1) { idx = tableData.value.length; addRows(rows.length) }
  for (const row of rows) {
    if (idx >= tableData.value.length) addRows(1)
    const target = tableData.value[idx]
    for (const c of columns.value) target[c.field] = row[c.field] ?? ''
    idx++
  }
}

async function onEditClosed() {
  await validateAll()
}

async function validateAll() {
  invalidMap.value = new Map()
  const $table = tableRef.value
  if (!$table) return
  const errMap = await $table.validate(tableData.value, true).catch(e => e)
  if (errMap) {
    const m = new Map()
    for (const rowid in errMap) {
      for (const field in errMap[rowid]) {
        const rowIndex = tableData.value.findIndex(r => $table.getRowid(r) === rowid)
        m.set(`${rowIndex}-${field}`, errMap[rowid][field]?.content || errMap[rowid][field]?.message || '校验失败')
      }
    }
    invalidMap.value = m
    applyInvalidStyle()
  }
}

function applyInvalidStyle() {
  const $table = tableRef.value
  if (!$table) return
  $table.clearCellStyle?.()
  const cells = []
  invalidMap.value.forEach((msg, key) => {
    const [rowIndex, field] = key.split('-')
    cells.push({
      row: tableData.value[Number(rowIndex)],
      field,
      style: { color: '#e02b2b', backgroundColor: '#ffe9e8' }
    })
  })
  if (cells.length) $table.setCellStyle(cells)
}

function clearInvalid() {
  invalidMap.value = new Map()
  tableRef.value?.clearCellStyle?.()
}

async function confirmImport() {
  const $table = tableRef.value
  const errMap = await $table.validate(tableData.value, true).catch(e => e)
  const filled = tableData.value.filter(r => columns.value.some(c => r[c.field] !== '' && r[c.field] != null))
  if (errMap) {
    notice.value = '存在校验未通过的数据，请修正标红单元格后再导入'
    noticeType.value = 'error'
    await validateAll()
    return
  }
  if (!filled.length) {
    notice.value = '没有可导入的数据'
    noticeType.value = 'warning'
    return
  }
  notice.value = `导入校验通过，共 ${filled.length} 行数据`
  noticeType.value = 'success'
  emit('imported', filled)
}
</script>
<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.12);
  display: flex; align-items: center; justify-content: center; z-index: 100;
  padding: 16px;
}
.workspace {
  display: flex; align-items: stretch; gap: 12px; max-width: 96vw; max-height: 92vh;
  position: relative;
}

.dialog {
  width: 1080px; max-width: min(1080px, 96vw); background: #fff; border-radius: 8px;
  display: flex; flex-direction: column; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  min-height: 560px; max-height: 92vh;
}
.workspace.with-chat .dialog { width: min(920px, calc(96vw - 380px)); }

.dialog-header { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.assay-name { color: #999; font-size: 13px; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; align-items: center; }
.close-btn:hover { color: #333; }

.dialog-body { padding: 14px 20px 12px; flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }

.toolbar { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 10px; min-height: 34px; gap: 12px; }
.tip { color: #b3b3b3; font-size: 13px; padding-top: 7px; line-height: 1.5; }
.toolbar-right { display: flex; align-items: flex-start; gap: 8px; flex-shrink: 0; }

.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; position: relative; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }

.btn.ai-btn { border-color: #644bdc; color: #644bdc; background: #fff; }
.btn.ai-btn:hover { background: #f5f2ff; }
.pulse-dot, .badge-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #644bdc; margin-left: 4px;
}
.pulse-dot { animation: pulse 1s ease-in-out infinite; }
.badge-dot { background: #52c41a; }

/* ===== 右侧 AI 抽屉 ===== */
.chat-drawer {
  width: 360px; flex-shrink: 0; background: #fff; border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08); display: flex; flex-direction: column;
  overflow: hidden; border: 1px solid #ececec; min-height: 560px; max-height: 92vh;
}
.chat-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0; background: #faf9ff; flex-shrink: 0;
}
.chat-title { font-size: 13px; font-weight: 600; color: #644bdc; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.chat-title .ri { font-size: 14px; }
.skill-select {
  flex: 1; min-width: 0; border: 1px solid #e5e5e5; border-radius: 4px;
  padding: 3px 6px; font-size: 12px; color: #555; background: #fff; outline: none;
}
.chat-close {
  border: none; background: transparent; color: #999; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; padding: 2px; border-radius: 4px;
}
.chat-close:hover { color: #333; background: #f0f0f0; }

.chat-messages {
  flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column;
  gap: 10px; background: #fcfcfd; min-height: 0;
}
.chat-empty { text-align: center; color: #b3b3b3; font-size: 12px; padding: 24px 16px; line-height: 1.7; }
.chat-empty .ri { font-size: 28px; display: block; margin-bottom: 8px; color: #d9d3f8; }
.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.msg-bubble { max-width: 88%; padding: 7px 12px; border-radius: 10px; font-size: 13px; line-height: 1.6; word-break: break-word; }
.chat-msg.user .msg-bubble { background: #644bdc; color: #fff; border-bottom-right-radius: 3px; }
.chat-msg.assistant .msg-bubble { background: #fff; border: 1px solid #ececec; color: #333; border-bottom-left-radius: 3px; }
.msg-bubble.thinking { color: #999; display: inline-flex; align-items: center; gap: 6px; }

.chat-input-row {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  border-top: 1px solid #f0f0f0; flex-shrink: 0; flex-wrap: wrap;
}
.attach-btn {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  border-radius: 50%; color: #644bdc; background: #f0edff; cursor: pointer; font-size: 15px; flex-shrink: 0;
}
.attach-btn:hover { background: #e4deff; }
.file-chip {
  display: inline-flex; align-items: center; gap: 4px; max-width: 100%;
  background: #f0edff; color: #644bdc; border-radius: 12px; padding: 2px 8px; font-size: 12px;
}
.file-chip-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px; }
.file-chip-x { cursor: pointer; font-size: 14px; }
.chat-input {
  flex: 1; min-width: 120px; border: 1px solid #e5e5e5; border-radius: 16px;
  padding: 6px 14px; font-size: 13px; outline: none;
}
.chat-input:focus { border-color: #644bdc; }
.send-btn {
  width: 32px; height: 32px; border: none; background: #1c62d7; color: #fff; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.send-btn:hover { background: #2a6fe0; }
.send-btn:disabled { background: #b5cff2; cursor: not-allowed; }

/* 收起把手 */
.chat-handle {
  position: absolute; right: -14px; top: 72px; transform: translateX(100%);
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  border: 1px solid #d9d3f8; background: #fff; color: #644bdc;
  border-radius: 0 8px 8px 0; padding: 10px 8px; cursor: pointer;
  box-shadow: 2px 2px 10px rgba(100, 75, 220, 0.12); font-size: 12px;
}
.chat-handle .ri { font-size: 18px; }
.handle-label { writing-mode: vertical-rl; letter-spacing: 2px; font-size: 11px; }
.chat-handle.busy { border-color: #644bdc; background: #faf9ff; }
.chat-handle.busy .ri { animation: pulse 1s ease-in-out infinite; }
.chat-handle.done { border-color: #95de64; color: #389e0d; }

.spin { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { opacity: 0.45; } }

.notice { border-radius: 4px; padding: 7px 12px; font-size: 13px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.notice .ri { font-size: 15px; flex-shrink: 0; }
.notice.info { background: #f0f5ff; color: #2f54eb; }
.notice.success { background: #f6ffed; color: #389e0d; }
.notice.warning { background: #fffbe6; color: #d48806; }
.notice.error { background: #fff1f0; color: #cf1322; }

.data-table { flex: 1; min-height: 0; }
.data-table :deep(.vxe-table--header-wrapper) { background: #fafafa; }
.data-table :deep(.vxe-header--column) { background: #fafafa !important; color: #4a4a4a; font-weight: 500; font-size: 12px; }
.data-table :deep(.vxe-body--column) { font-size: 13px; color: #333; }

.required-mark::after { content: ' *'; color: #e02b2b; }
.col-info { color: #c0c0c0; margin-left: 4px; cursor: help; font-size: 13px; }
.cell-editor { width: 100%; height: 100%; border: none; outline: none; padding: 4px 8px; font-size: 13px; background: #fff; }
select.cell-editor { padding: 4px 4px; }

.table-footer { display: flex; align-items: center; gap: 10px; padding-top: 10px; flex-shrink: 0; }
.invalid-count { color: #e02b2b; font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }

.dialog-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; flex-shrink: 0; }

@media (max-width: 1100px) {
  .workspace { flex-direction: column; align-items: center; overflow: auto; }
  .workspace.with-chat .dialog { width: min(920px, 96vw); }
  .chat-drawer { width: min(920px, 96vw); min-height: 360px; max-height: 50vh; }
  .chat-handle { right: 8px; top: auto; bottom: 24px; transform: none; flex-direction: row; border-radius: 20px; writing-mode: horizontal-tb; }
  .handle-label { writing-mode: horizontal-tb; letter-spacing: 0; }
}
</style>
