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
            <span class="tip">单击选中后可直接键入；支持方向键 / Tab / Enter，Delete 清空，Esc 取消编辑。可从 Excel 复制后粘贴。右侧 AI 助手可识别填表。</span>
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

          <div class="table-wrap">
            <vxe-table
              ref="tableRef"
              class="data-table"
              border
              keep-source
              height="100%"
              min-height="240"
              show-overflow="title"
              show-header-overflow="title"
              align="left"
              header-align="left"
              :data="tableData"
              :column-config="{ resizable: true }"
              :edit-config="{ trigger: 'dblclick', mode: 'cell', showStatus: true, showAsterisk: false }"
              :mouse-config="{ selected: true }"
              :keyboard-config="keyboardConfig"
              :valid-config="{ autoPos: true, showErrorMessage: true, message: 'inline', msgMode: 'single' }"
              :edit-rules="editRules"
              :menu-config="menuConfig"
              :row-class-name="'inv-' + invalidPaint"
              :cell-class-name="cellClassName"
              @edit-closed="onEditClosed"
              @menu-click="onMenuClick"
            >
              <vxe-column type="seq" title="#" width="50" align="left" header-align="left" fixed="left" :edit-render="null"></vxe-column>
              <vxe-column
                v-for="(col, ci) in columns"
                :key="col.field"
                :field="col.field"
                :title="col.title"
                min-width="120"
                align="left"
                header-align="left"
                :fixed="ci === 0 ? 'left' : ''"
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
                  <input
                    v-else
                    v-model="row[col.field]"
                    class="cell-editor"
                    type="text"
                    :placeholder="col.type === 'date' ? 'YYYY-MM-DD' : ''"
                  />
                </template>
              </vxe-column>
            </vxe-table>
          </div>

          <div class="table-footer">
            <button class="btn ghost" @click="addRows(1)"><i class="ri-add-line"></i> 添加行</button>
            <button class="btn ghost" @click="insertRowBelowCurrent"><i class="ri-add-line"></i> 下方插入</button>
            <button class="btn ghost" @click="removeCurrentRow"><i class="ri-delete-bin-line"></i> 删除行</button>
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
          <div class="chat-header-main">
            <span class="chat-title">导入助手</span>
            <span v-if="chatThinking" class="chat-badge busy"><i class="ri-loader-4-line spin"></i> 识别中 {{ runClock }}</span>
            <span v-else-if="unreadDone" class="chat-badge done">有新结果</span>
          </div>
          <button class="icon-btn" type="button" title="收起（后台继续）" @click="collapseChat">
            <i class="ri-contract-right-line"></i>
          </button>
        </div>

        <div class="chat-scroll" ref="chatMsgs" data-conversation-scroll>
          <div v-if="!chatLog.length && !chatThinking" class="chat-empty">
            <div class="chat-empty-title">描述规则或上传文件</div>
            <div class="chat-empty-desc">发送后识别并填入左侧表格；可在下方切换 Skill 模板。</div>
          </div>

          <article
            v-for="(m, i) in chatLog"
            :key="i"
            :class="['turn', m.role, { pending: m.pending }]"
          >
            <div class="turn-label">{{ m.role === 'user' ? '你' : '助手' }}</div>
            <div class="turn-body">
              <template v-if="m.fileChip">
                <span class="turn-file"><i class="ri-file-text-line"></i>{{ m.content }}</span>
              </template>
              <template v-else>{{ m.content }}</template>
            </div>
            <div v-if="m.pending" class="turn-meta">已排队，等待当前轮结束</div>
          </article>
        </div>

        <div v-if="chatQueue.length" class="queue-dock">
          <button type="button" class="queue-head" @click="queueOpen = !queueOpen">
            <i class="ri-time-line"></i>
            <span>{{ chatQueue.length }} 条排队</span>
            <i :class="queueOpen ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'"></i>
          </button>
          <ul v-if="queueOpen" class="queue-list">
            <li v-for="(q, qi) in chatQueue" :key="q.id">
              <span class="queue-text">{{ q.text }}</span>
              <button type="button" class="icon-btn sm" title="移出" @click="removeQueued(qi)">
                <i class="ri-close-line"></i>
              </button>
            </li>
          </ul>
        </div>

        <div class="composer">
          <div v-if="chatFileId && chatFile" class="composer-chips">
            <span class="file-chip" :title="chatFile.name">
              <i class="ri-file-text-line"></i>
              <span class="file-chip-name">{{ chatFile.name }}</span>
              <button type="button" class="chip-x" @click="clearFile" title="移除">
                <i class="ri-close-line"></i>
              </button>
            </span>
          </div>
          <textarea
            v-model="chatInput"
            class="composer-input"
            rows="3"
            :placeholder="composerPlaceholder"
            @keydown="onComposerKeydown"
          />
          <div class="composer-toolbar">
            <label class="skill-picker" title="导入 Skill 模板">
              <i class="ri-book-2-line"></i>
              <select v-model="pickedSkill" class="skill-select">
                <option value="">无模板</option>
                <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <i class="ri-arrow-down-s-line skill-caret"></i>
            </label>
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
                title="打断并按新指令重导"
                @click="steerNow"
              >
                <i class="ri-skip-forward-line"></i>
                <span>立即重导</span>
              </button>
              <button
                type="button"
                class="btn send"
                :title="chatThinking ? '排队' : '发送'"
                @click="sendOrQueue"
                :disabled="!canSubmit"
              >
                <i class="ri-arrow-up-line"></i>
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
import {
  parseClipboardText,
  isRowFilled,
  filledRows,
  isNumericLike,
  applyPasteGrid
} from '../utils/sheetClipboard'

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
const lastSheetKey = ref('')
const invalidPaint = ref(0)
const keyboardConfig = {
  isArrow: true,
  isDel: true,
  isEnter: true,
  isTab: true,
  isEdit: true,
  isEsc: true,
  isBack: true
}
const menuConfig = {
  enabled: true,
  body: {
    options: [
      [
        { code: 'insertBelow', name: '在下方插入行' },
        { code: 'removeRow', name: '删除行' },
        { code: 'clearCell', name: '清空单元格' }
      ]
    ]
  }
}
const hasDraft = computed(() => !!chatInput.value.trim())
const canSubmit = computed(() => chatThinking.value
  ? hasDraft.value
  : !!(hasDraft.value || chatFileId.value))
const canSteer = computed(() => !!(hasDraft.value || chatFileId.value || chatQueue.value.length))
const composerPlaceholder = computed(() => {
  if (chatThinking.value) return '识别中… Enter 排队，或点「立即重导」打断'
  if (chatFileId.value) return '补充要求后发送；将按当前 Skill 识别导入'
  return '描述导入规则或要求，Enter 发送，Shift+Enter 换行'
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
  window.addEventListener('keydown', onWinKeydown, true)
  window.addEventListener('copy', onWinCopy)
  window.addEventListener('cut', onWinCut)
  window.addEventListener('paste', onWinPaste)
})

onUnmounted(() => {
  stopClock()
  abortCtrl.value?.abort()
  window.removeEventListener('keydown', onWinKeydown, true)
  window.removeEventListener('copy', onWinCopy)
  window.removeEventListener('cut', onWinCut)
  window.removeEventListener('paste', onWinPaste)
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
      validator: ({ cellValue }) => isNumericLike(cellValue) ? true : new Error('必须为数字')
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

function emptyRow() {
  const row = {}
  for (const c of columns.value) row[c.field] = ''
  return row
}

function addRows(n) {
  for (let i = 0; i < n; i++) tableData.value.push(emptyRow())
}

function cellClassName({ row, column }) {
  if (!column?.field) return ''
  const rowIndex = tableData.value.indexOf(row)
  if (invalidMap.value.has(`${rowIndex}-${column.field}`)) return 'cell-invalid'
  return ''
}

function currentAnchor() {
  const $table = tableRef.value
  if (!$table) return null
  return $table.getEditCell?.() || $table.getSelectedCell?.() || null
}

function insertRowBelow(row) {
  const idx = tableData.value.indexOf(row)
  const at = idx >= 0 ? idx + 1 : tableData.value.length
  tableData.value.splice(at, 0, emptyRow())
}

function insertRowBelowCurrent() {
  const sel = currentAnchor()
  insertRowBelow(sel?.row || tableData.value[tableData.value.length - 1])
}

function removeRow(row) {
  if (!row) return
  if (tableData.value.length <= 1) {
    const blank = emptyRow()
    for (const c of columns.value) row[c.field] = blank[c.field]
    return
  }
  const idx = tableData.value.indexOf(row)
  if (idx >= 0) tableData.value.splice(idx, 1)
}

function removeCurrentRow() {
  const sel = currentAnchor()
  removeRow(sel?.row || tableData.value[tableData.value.length - 1])
  validateFilled()
}

function onMenuClick({ menu, row, column }) {
  if (menu.code === 'insertBelow') insertRowBelow(row)
  else if (menu.code === 'removeRow') {
    removeRow(row)
    validateFilled()
  } else if (menu.code === 'clearCell' && column?.field) {
    row[column.field] = ''
    validateFilled()
  }
}

function isChatTarget(el) {
  const node = el && typeof el.closest === 'function' ? el : el?.parentElement
  return !!node?.closest?.('.composer, .chat-drawer, .skill-picker, .skill-select')
}

function isTypingElsewhere(el) {
  if (isChatTarget(el)) return true
  const tag = el?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
    return !el.classList?.contains('cell-editor')
  }
  return !!el?.isContentEditable
}

function onWinKeydown(e) {
  lastSheetKey.value = e.key
}

function onWinCopy(e) {
  if (isTypingElsewhere(e.target)) return
  if (window.getSelection?.()?.toString?.()) return
  const $table = tableRef.value
  if (!$table || $table.getEditCell?.()) return
  const sel = $table.getSelectedCell?.()
  if (!sel?.row || !sel.column?.field || !e.clipboardData) return
  const v = sel.row[sel.column.field]
  e.clipboardData.setData('text/plain', v == null ? '' : String(v))
  e.preventDefault()
}

function onWinCut(e) {
  if (isTypingElsewhere(e.target)) return
  const $table = tableRef.value
  if (!$table || $table.getEditCell?.()) return
  const sel = $table.getSelectedCell?.()
  if (!sel?.row || !sel.column?.field || !e.clipboardData) return
  const v = sel.row[sel.column.field]
  e.clipboardData.setData('text/plain', v == null ? '' : String(v))
  e.preventDefault()
  sel.row[sel.column.field] = ''
  validateFilled()
}

function onWinPaste(e) {
  if (isTypingElsewhere(e.target)) return
  const $table = tableRef.value
  if (!$table || !e.clipboardData) return
  const text = e.clipboardData.getData('text/plain')
  if (text == null || text === '') return
  const grid = parseClipboardText(text)
  const multi = grid.length > 1 || (grid[0] && grid[0].length > 1)
  const edit = $table.getEditCell?.()
  if (edit && !multi) return
  const sel = edit || $table.getSelectedCell?.()
  if (!sel?.row) return
  const fields = columns.value.map(c => c.field)
  let startColIndex = fields.indexOf(sel.column?.field)
  if (startColIndex < 0) startColIndex = 0
  const startRowIndex = tableData.value.indexOf(sel.row)
  if (startRowIndex < 0) return
  e.preventDefault()
  if (edit) $table.clearEdit?.()
  applyPasteGrid({
    data: tableData.value,
    fields,
    startRowIndex,
    startColIndex,
    grid,
    makeEmptyRow: emptyRow
  })
  nextTick(validateFilled)
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
      await validateFilled()
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

async function onEditClosed({ row, column } = {}) {
  if (lastSheetKey.value === 'Escape' && row && column?.field) {
    tableRef.value?.revertData?.(row, column.field)
  }
  lastSheetKey.value = ''
  await validateFilled()
}

function collectInvalid(rows) {
  const m = new Map()
  for (const row of rows) {
    const rowIndex = tableData.value.indexOf(row)
    if (rowIndex < 0) continue
    for (const c of columns.value) {
      const v = row[c.field]
      const empty = v === '' || v == null
      if (c.required && empty) m.set(`${rowIndex}-${c.field}`, `${c.title} 必填`)
      else if (c.type === 'number' && !isNumericLike(v)) m.set(`${rowIndex}-${c.field}`, '必须为数字')
      else if (c.type === 'select' && c.options?.length && !empty && !c.options.includes(v)) {
        m.set(`${rowIndex}-${c.field}`, '存在内容与选项不匹配')
      }
    }
  }
  return m
}

async function validateFilled() {
  const $table = tableRef.value
  const rows = filledRows(tableData.value, columns.value)
  invalidMap.value = collectInvalid(rows)
  invalidPaint.value += 1
  if ($table?.clearValidate) await $table.clearValidate()
  if (!$table || !rows.length) return
  try {
    await $table.fullValidate(rows)
  } catch {
    /* vxe 用 reject 表示有错误，格子会带 col--valid-error */
  }
}

function clearInvalid() {
  invalidMap.value = new Map()
  tableRef.value?.clearValidate?.()
}

async function confirmImport() {
  const filled = filledRows(tableData.value, columns.value)
  await validateFilled()
  if (invalidMap.value.size) {
    notice.value = '存在校验未通过的数据，请修正标红单元格后再导入'
    noticeType.value = 'error'
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
.workspace.with-chat .dialog { width: min(880px, calc(96vw - 420px)); }

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
  width: 400px; flex-shrink: 0; background: #fff; border-radius: 10px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08); display: flex; flex-direction: column;
  overflow: hidden; border: 1px solid #e8eaed; min-height: 560px; max-height: 92vh;
}
.chat-header {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 12px 14px; border-bottom: 1px solid #eef0f2; background: #fff; flex-shrink: 0;
}
.chat-header-main { display: flex; align-items: center; gap: 8px; min-width: 0; }
.chat-title { font-size: 14px; font-weight: 600; color: #1a1a1a; white-space: nowrap; }
.chat-badge {
  display: inline-flex; align-items: center; gap: 4px; font-size: 11px;
  padding: 2px 8px; border-radius: 999px; white-space: nowrap;
}
.chat-badge.busy { color: #2468DB; background: #eef4fd; }
.chat-badge.done { color: #389e0d; background: #f6ffed; }

.icon-btn {
  border: none; background: transparent; color: #8a8f98; cursor: pointer;
  width: 30px; height: 30px; border-radius: 8px; display: inline-flex;
  align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0;
}
.icon-btn:hover { color: #333; background: #f3f4f6; }
.icon-btn.sm { width: 22px; height: 22px; font-size: 14px; }
.icon-btn.attach { color: #5f6b7a; }

.chat-scroll {
  flex: 1; overflow-y: auto; padding: 14px 14px 10px; display: flex; flex-direction: column;
  gap: 14px; background: #f7f8fa; min-height: 0; scrollbar-gutter: stable;
}
.chat-empty { padding: 24px 8px; text-align: left; color: #8a8f98; }
.chat-empty-title { font-size: 13px; font-weight: 500; color: #4a4a4a; margin-bottom: 6px; }
.chat-empty-desc { font-size: 12px; line-height: 1.65; }

.turn { display: flex; flex-direction: column; gap: 4px; }
.turn-label { font-size: 11px; color: #9aa0a8; line-height: 1; }
.turn-body {
  font-size: 13px; line-height: 1.7; color: #2b2f36; word-break: break-word;
  white-space: pre-wrap;
}
.turn.user .turn-body {
  background: #fff; border: 1px solid #e8eaed; border-radius: 10px; padding: 10px 12px;
}
.turn.user.pending .turn-body { opacity: 0.72; }
.turn.assistant .turn-body { padding: 0 2px; }
.turn-meta { font-size: 11px; color: #8aa4d4; padding-left: 2px; }
.turn-file {
  display: inline-flex; align-items: center; gap: 6px; color: #2468DB;
  background: #eef4fd; border-radius: 6px; padding: 4px 8px; font-size: 12px;
}

.queue-dock {
  border-top: 1px solid #eef0f2; background: #fff; flex-shrink: 0;
  border-bottom: 1px solid #eef0f2;
}
.queue-head {
  width: 100%; display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border: none; background: transparent; color: #5f6b7a; font-size: 12px; cursor: pointer;
}
.queue-head:hover { background: #f7f8fa; color: #2468DB; }
.queue-list { list-style: none; padding: 0 10px 8px; margin: 0; }
.queue-list li {
  display: flex; align-items: center; gap: 6px; padding: 6px 8px;
  font-size: 12px; color: #555; border-radius: 6px; background: #f7f8fa;
}
.queue-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.composer {
  margin: 10px 12px 12px; border: 1px solid #dfe3e8; border-radius: 14px;
  background: #fff; padding: 10px 10px 8px; flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.composer:focus-within { border-color: #b8ccf5; box-shadow: 0 0 0 3px rgba(36, 104, 219, 0.08); }
.composer-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.file-chip {
  display: inline-flex; align-items: center; gap: 4px; max-width: 100%;
  background: #f3f6fb; color: #2b4f8f; border: 1px solid #e3ebf7;
  border-radius: 8px; padding: 4px 8px; font-size: 12px;
}
.file-chip-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 240px; }
.chip-x { border: none; background: transparent; color: #5f7db8; cursor: pointer; display: inline-flex; padding: 0; }
.composer-input {
  width: 100%; border: none; outline: none; resize: none; font-size: 13px; line-height: 1.6;
  min-height: 72px; color: #1f2329; background: transparent;
}
.composer-input::placeholder { color: #b0b6bf; }
.composer-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  margin-top: 8px; min-height: 34px;
}
.skill-picker {
  display: inline-flex; align-items: center; gap: 4px; min-width: 0; flex: 1;
  height: 32px; padding: 0 8px 0 6px; border-radius: 8px;
  border: 1px solid #e8eaed; background: #f7f8fa; cursor: pointer; position: relative;
}
.skill-picker:hover { border-color: #d5dae0; background: #f3f4f6; }
.skill-picker .ri-book-2-line { font-size: 15px; color: #6b7280; flex-shrink: 0; }
.skill-caret { font-size: 14px; color: #9aa0a8; flex-shrink: 0; pointer-events: none; }
.skill-select {
  flex: 1; min-width: 0; border: none; background: transparent; outline: none;
  font-size: 12px; color: #374151; cursor: pointer; appearance: none; padding-right: 2px;
}
.composer-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.btn.steer {
  border: 1px solid #c5d8f7; color: #2468DB; background: #fff; border-radius: 8px;
  padding: 0 10px; height: 32px; font-size: 12px; white-space: nowrap;
}
.btn.steer:hover { background: #eef4fd; }
.btn.send {
  width: 32px; height: 32px; padding: 0; justify-content: center;
  background: #2468DB; border: none; color: #fff; border-radius: 8px;
}
.btn.send:hover { background: #1d5bc4; }
.btn.send:disabled { background: #b8ccf5; cursor: not-allowed; }
.btn.send .ri { font-size: 16px; }

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

.data-table { height: 100%; }
.table-wrap { flex: 1; min-height: 0; }
.data-table :deep(.vxe-table--header-wrapper) { background: #fafafa; }
.data-table :deep(.vxe-header--column) { background: #fafafa !important; color: #4a4a4a; font-weight: 500; font-size: 12px; text-align: left !important; }
.data-table :deep(.vxe-header--column .vxe-cell) { justify-content: flex-start !important; }
.data-table :deep(.vxe-body--column) { font-size: 13px; color: #333; text-align: left !important; }
.data-table :deep(.vxe-body--column .vxe-cell) { justify-content: flex-start !important; }
.data-table :deep(.cell-invalid),
.data-table :deep(.col--valid-error) { background-color: #ffe9e8 !important; color: #e02b2b; }

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
