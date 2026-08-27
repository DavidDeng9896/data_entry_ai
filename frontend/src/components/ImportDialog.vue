<template>
  <div class="dialog-mask" @click.self="onMaskClick">
    <div class="workspace" :class="{ 'with-chat': chatOpen }">
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

      <aside v-show="chatOpen" class="chat-drawer">
        <div class="chat-header">
          <span class="chat-title"><i class="ri-chat-3-line"></i> AI 导入助手</span>
          <select v-model="pickedSkill" class="skill-select" title="导入模板 Skill">
            <option value="">不使用模板</option>
            <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
          <button class="icon-btn" type="button" title="收起助手（后台继续执行）" @click="collapseChat">
            <i class="ri-close-line"></i>
          </button>
        </div>

        <div class="chat-scroll" ref="chatMsgs" data-conversation-scroll>
          <div v-if="!chatLog.length && !chatThinking" class="chat-empty">
            <i class="ri-chat-smile-2-line"></i>
            <div>上传文件或描述规则，发送后识别填入左侧表格。结果不对可继续对话重新导入。</div>
          </div>

          <div v-for="(m, i) in chatLog" :key="i" :class="['node', m.role, { pending: m.pending }]">
            <div class="node-body">
              <template v-if="m.fileChip">
                <i class="ri-file-text-line"></i> {{ m.content }}
              </template>
              <template v-else>{{ m.content }}</template>
            </div>
            <div v-if="m.pending" class="node-meta">排队中</div>
          </div>

          <div v-if="chatThinking" class="node status">
            <div class="status-row">
              <i class="ri-loader-4-line spin"></i>
              <span>正在识别…</span>
              <span class="run-clock">{{ runClock }}</span>
            </div>
          </div>
        </div>

        <!-- Queue dock -->
        <div v-if="chatQueue.length" class="queue-dock">
          <button type="button" class="queue-head" @click="queueOpen = !queueOpen">
            <i class="ri-play-list-2-line"></i>
            <span>{{ chatQueue.length }} 条已排队</span>
            <i :class="queueOpen ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'"></i>
          </button>
          <ul v-if="queueOpen" class="queue-list">
            <li v-for="(q, qi) in chatQueue" :key="q.id">
              <span class="queue-text">{{ q.text }}</span>
              <button type="button" class="icon-btn sm" title="移出队列" @click="removeQueued(qi)">
                <i class="ri-close-line"></i>
              </button>
            </li>
          </ul>
        </div>

        <!-- Harness-style composer card -->
        <div class="composer">
          <div v-if="chatFileId && chatFile" class="composer-chips">
            <span class="file-chip" :title="chatFile.name">
              <i class="ri-file-text-line"></i>
              <span class="file-chip-name">{{ chatFile.name }}</span>
              <button type="button" class="chip-x" @click="clearFile" title="移除文件">
                <i class="ri-close-line"></i>
              </button>
            </span>
          </div>
          <textarea
            v-model="chatInput"
            class="composer-input"
            rows="3"
            :placeholder="composerPlaceholder"
            :disabled="false"
            @keydown="onComposerKeydown"
          />
          <div class="composer-bar">
            <span v-if="!chatThinking" class="composer-hint">Enter 发送</span>
            <div class="composer-actions">
              <label class="icon-btn attach" title="上传文件">
                <input type="file" ref="fileInput" style="display:none" @change="onFileChange"
                  accept=".xlsx,.xls,.csv,.tsv,.pdf,.png,.jpg,.jpeg,.txt,.md" />
                <i class="ri-attachment-2"></i>
              </label>
              <button
                v-if="chatThinking && canSteer"
                type="button"
                class="btn steer"
                title="打断当前轮，立即按本条指令重新导入"
                @click="steerNow"
                :disabled="!canSteer"
              >
                <i class="ri-skip-forward-line"></i> 立即重导
              </button>
              <button
                type="button"
                class="btn send"
                :title="chatThinking ? '排队，等本轮结束后自动执行' : '发送'"
                @click="sendOrQueue"
                :disabled="!canSubmit"
              >
                <i class="ri-send-plane-line"></i>
                <span>{{ chatThinking ? '排队' : '发送' }}</span>
              </button>
            </div>
          </div>
        </div>
      </aside>

      <button
        v-if="!chatOpen && chatSessionStarted"
        type="button"
        class="chat-handle"
        :class="{ busy: chatThinking, done: unreadDone }"
        @click="openChat"
        :title="chatThinking ? '助手执行中，点击展开' : '展开 AI 导入助手'"
      >
        <i class="ri-chat-3-line"></i>
        <span v-if="chatThinking" class="handle-label">执行中</span>
        <span v-else-if="unreadDone" class="handle-label">有结果</span>
        <span v-else class="handle-label">助手</span>
      </button>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
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
const chatSessionStarted = ref(false)
const chatLog = ref([])
const chatInput = ref('')
const chatFile = ref(null)
const chatFileId = ref(null)
const chatThinking = ref(false)
const chatMsgs = ref(null)
const pickedSkill = ref('')
const unreadDone = ref(false)
const fileInput = ref(null)
const chatQueue = ref([])
const queueOpen = ref(false)
const abortCtrl = ref(null)
const runStartedAt = ref(0)
const runClock = ref('0:00')
let clockTimer = null
let turnSeq = 0

const notice = ref('')
const noticeType = ref('info')
const invalidMap = ref(new Map())

const invalidCount = computed(() => invalidMap.value.size)
const hasDraft = computed(() => !!chatInput.value.trim())
const canSubmit = computed(() => chatThinking.value
  ? hasDraft.value
  : !!(hasDraft.value || chatFileId.value))
const canSteer = computed(() => !!(hasDraft.value || chatFileId.value || chatQueue.value.length))
const composerPlaceholder = computed(() => {
  if (chatThinking.value) return '本轮进行中：Enter 排队；或点「立即重导」打断并按新指令覆盖表格'
  if (chatFileId.value) return '继续提要求，或直接发送识别导入'
  return '输入规则或要求，Enter 发送，Shift+Enter 换行'
})

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

onUnmounted(() => {
  stopClock()
  abortCtrl.value?.abort()
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
  chatOpen.value = false
}

function onMaskClick() {}

function startClock() {
  runStartedAt.value = Date.now()
  runClock.value = '0:00'
  stopClock()
  clockTimer = setInterval(() => {
    const s = Math.floor((Date.now() - runStartedAt.value) / 1000)
    runClock.value = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
  }, 1000)
}

function stopClock() {
  if (clockTimer) {
    clearInterval(clockTimer)
    clockTimer = null
  }
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

function onComposerKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendOrQueue()
  }
}

function enqueueDraft() {
  const text = chatInput.value.trim()
  if (!text && !chatFileId.value) return false
  if (text) {
    chatQueue.value.push({ id: `${Date.now()}-${Math.random()}`, text })
    chatLog.value.push({ role: 'user', content: text, pending: true })
    chatInput.value = ''
    queueOpen.value = true
    scrollChat()
  }
  return true
}

function sendOrQueue() {
  if (!canSubmit.value) return
  chatSessionStarted.value = true
  if (chatThinking.value) {
    enqueueDraft()
    return
  }
  const text = chatInput.value.trim()
  if (text) {
    chatLog.value.push({ role: 'user', content: text })
    chatInput.value = ''
  }
  runTurn()
}

function steerNow() {
  if (!canSteer.value) return
  chatSessionStarted.value = true
  turnSeq += 1
  abortCtrl.value?.abort()
  const text = chatInput.value.trim()
  if (text) {
    chatLog.value.push({ role: 'user', content: text })
    chatInput.value = ''
  }
  runTurn()
}

function removeQueued(index) {
  const [removed] = chatQueue.value.splice(index, 1)
  if (!removed) return
  const i = chatLog.value.findIndex(m => m.pending && m.content === removed.text)
  if (i >= 0) chatLog.value.splice(i, 1)
}

function settlePending(text) {
  const m = chatLog.value.find(x => x.pending && x.content === text)
  if (m) m.pending = false
}

async function runTurn() {
  turnSeq += 1
  const myTurn = turnSeq
  abortCtrl.value = new AbortController()
  chatThinking.value = true
  startClock()
  scrollChat()
  try {
    const res = await api.chat({
      messages: chatLog.value
        .filter(m => !m.fileChip && !m.pending)
        .map(m => ({ role: m.role, content: m.content })),
      columns: columns.value,
      skill_id: pickedSkill.value || null,
      file_id: chatFileId.value
    }, { signal: abortCtrl.value.signal })
    if (myTurn !== turnSeq) return
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
    if (e.name === 'AbortError' || e.message?.includes('abort')) return
    if (myTurn !== turnSeq) return
    chatLog.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    scrollChat()
  } finally {
    if (myTurn === turnSeq) {
      chatThinking.value = false
      stopClock()
      drainQueue()
    }
  }
}

function drainQueue() {
  if (chatThinking.value || !chatQueue.value.length) return
  const next = chatQueue.value.shift()
  if (!next) return
  settlePending(next.text)
  runTurn()
}

function scrollChat() {
  setTimeout(() => {
    if (chatMsgs.value) chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
  }, 30)
}

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
.workspace.with-chat .dialog { width: min(900px, calc(96vw - 400px)); }

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
.btn.primary { background: #2468DB; border-color: #2468DB; color: #fff; }
.btn.primary:hover { background: #1d5bc4; }
.btn.ghost { color: #666; }

.btn.ai-btn { border-color: #2468DB; color: #2468DB; background: #fff; }
.btn.ai-btn:hover { background: #eef4fd; }
.pulse-dot, .badge-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #2468DB; margin-left: 4px;
}
.pulse-dot { animation: pulse 1s ease-in-out infinite; }
.badge-dot { background: #52c41a; }

.chat-drawer {
  width: 380px; flex-shrink: 0; background: #fff; border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08); display: flex; flex-direction: column;
  overflow: hidden; border: 1px solid #ececec; min-height: 560px; max-height: 92vh;
}
.chat-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0; background: #fff; flex-shrink: 0;
}
.chat-title { font-size: 13px; font-weight: 600; color: #2468DB; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.chat-title .ri { font-size: 16px; }
.skill-select {
  flex: 1; min-width: 0; border: 1px solid #e5e5e5; border-radius: 4px;
  padding: 3px 6px; font-size: 12px; color: #555; background: #fff; outline: none;
}
.skill-select:focus { border-color: #2468DB; }
.icon-btn {
  border: none; background: transparent; color: #888; cursor: pointer;
  width: 28px; height: 28px; border-radius: 6px; display: inline-flex;
  align-items: center; justify-content: center; font-size: 16px;
}
.icon-btn:hover { color: #2468DB; background: #eef4fd; }
.icon-btn.sm { width: 22px; height: 22px; font-size: 14px; }
.icon-btn.attach { color: #2468DB; }

.chat-scroll {
  flex: 1; overflow-y: auto; padding: 14px 14px 8px; display: flex; flex-direction: column;
  gap: 10px; background: #fafbfc; min-height: 0; scrollbar-gutter: stable;
}
.chat-empty { text-align: center; color: #b3b3b3; font-size: 12px; padding: 28px 16px; line-height: 1.7; }
.chat-empty .ri { font-size: 28px; display: block; margin-bottom: 8px; color: #bcd2f5; }

.node { display: flex; flex-direction: column; max-width: 92%; }
.node.user { align-self: flex-end; align-items: flex-end; }
.node.assistant, .node.status { align-self: flex-start; }
.node-body {
  padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.65; word-break: break-word;
}
.node.user .node-body { background: #2468DB; color: #fff; border-bottom-right-radius: 4px; }
.node.user.pending .node-body { background: #9bb8ea; }
.node.assistant .node-body { background: #fff; border: 1px solid #ececec; color: #333; border-bottom-left-radius: 4px; }
.node-meta { font-size: 11px; color: #8aa4d4; margin-top: 3px; }
.status-row {
  display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #5b7db8;
  background: #eef4fd; border-radius: 8px; padding: 6px 10px;
}
.run-clock { font-variant-numeric: tabular-nums; color: #8aa4d4; }

.queue-dock { border-top: 1px solid #f0f0f0; background: #fff; flex-shrink: 0; }
.queue-head {
  width: 100%; display: flex; align-items: center; gap: 6px; padding: 8px 12px;
  border: none; background: transparent; color: #2468DB; font-size: 12px; cursor: pointer;
}
.queue-head:hover { background: #eef4fd; }
.queue-list { list-style: none; padding: 0 8px 8px; margin: 0; }
.queue-list li {
  display: flex; align-items: center; gap: 6px; padding: 4px 6px;
  font-size: 12px; color: #555; border-radius: 4px;
}
.queue-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.composer {
  margin: 8px 10px 10px; border: 1px solid #e5e5e5; border-radius: 14px;
  background: #fff; padding: 10px 10px 8px; flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(36, 104, 219, 0.06);
}
.composer:focus-within { border-color: #2468DB; }
.composer-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.file-chip {
  display: inline-flex; align-items: center; gap: 4px; max-width: 100%;
  background: #eef4fd; color: #2468DB; border-radius: 8px; padding: 3px 8px; font-size: 12px;
}
.file-chip-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 220px; }
.chip-x { border: none; background: transparent; color: #2468DB; cursor: pointer; display: inline-flex; padding: 0; }
.composer-input {
  width: 100%; border: none; outline: none; resize: none; font-size: 13px; line-height: 1.55;
  min-height: 64px; color: #333; background: transparent;
}
.composer-input::placeholder { color: #b3b3b3; }
.composer-bar { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 6px; min-height: 32px; }
.composer-hint { font-size: 11px; color: #b3b3b3; white-space: nowrap; margin-right: auto; }
.composer-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.btn.steer {
  border-color: #2468DB; color: #2468DB; background: #fff; border-radius: 8px; padding: 5px 10px;
}
.btn.steer:hover { background: #eef4fd; }
.btn.steer:disabled { opacity: 0.45; cursor: not-allowed; }
.btn.send {
  background: #2468DB; border-color: #2468DB; color: #fff; border-radius: 8px; padding: 5px 12px;
}
.btn.send:hover { background: #1d5bc4; }
.btn.send:disabled { background: #9bb8ea; border-color: #9bb8ea; cursor: not-allowed; }

.chat-handle {
  position: absolute; right: -14px; top: 72px; transform: translateX(100%);
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  border: 1px solid #c5d8f7; background: #fff; color: #2468DB;
  border-radius: 0 8px 8px 0; padding: 10px 8px; cursor: pointer;
  box-shadow: 2px 2px 10px rgba(36, 104, 219, 0.12); font-size: 12px;
}
.chat-handle .ri { font-size: 18px; }
.handle-label { writing-mode: vertical-rl; letter-spacing: 2px; font-size: 11px; }
.chat-handle.busy { border-color: #2468DB; background: #eef4fd; }
.chat-handle.busy .ri { animation: pulse 1s ease-in-out infinite; }
.chat-handle.done { border-color: #95de64; color: #389e0d; }

.spin { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { opacity: 0.45; } }

.notice { border-radius: 4px; padding: 7px 12px; font-size: 13px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.notice .ri { font-size: 15px; flex-shrink: 0; }
.notice.info { background: #eef4fd; color: #2468DB; }
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
  .chat-handle { right: 8px; top: auto; bottom: 24px; transform: none; flex-direction: row; border-radius: 20px; }
  .handle-label { writing-mode: horizontal-tb; letter-spacing: 0; }
}
</style>
