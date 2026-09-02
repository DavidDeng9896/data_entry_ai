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
              border="full"
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
                <template #default="{ row }">
                  <span :title="conflictTitle(row, col) || undefined">{{ row[col.field] }}</span>
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
            <span class="conflict-count" v-if="conflictCount > 0"><i class="ri-alert-line"></i> {{ conflictCount }} 个单元格分页冲突（黄）</span>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" :disabled="confirming" @click="confirmImport">
            <i :class="confirming ? 'ri-loader-4-line spin' : 'ri-check-line'"></i>
            {{ confirming ? '写入中…' : '确认导入' }}
          </button>
        </div>
      </div>

      <aside v-show="chatOpen" class="chat-drawer">
        <div class="chat-header">
          <div class="chat-header-main">
            <span class="chat-title">导入助手</span>
            <span v-if="chatThinking" class="chat-badge busy"><i class="ri-loader-4-line spin"></i> {{ thinkingLabel }} {{ runClock }}</span>
            <span v-else-if="unreadDone" class="chat-badge done">有新结果</span>
          </div>
          <button class="icon-btn" type="button" title="收起（后台继续）" @click="collapseChat">
            <i class="ri-contract-right-line"></i>
          </button>
        </div>

        <div class="chat-scroll" ref="chatMsgs" data-conversation-scroll>
          <div v-if="!chatLog.length && !chatThinking" class="chat-empty">
            <div class="chat-empty-title">描述规则或上传文件</div>
            <div class="chat-empty-desc">点击左上角上传附件（可多选），或输入规则后发送识别。</div>
          </div>

          <article
            v-for="(m, i) in chatLog"
            :key="i"
            :class="['turn', m.role, { pending: m.pending }]"
          >
            <div class="turn-label">{{ m.role === 'user' ? '你' : '助手' }}</div>
            <div class="turn-body">
              <ul v-if="m.streaming && m.steps?.length" class="progress-steps">
                <li
                  v-for="(s, si) in m.steps"
                  :key="si"
                  :class="{ done: s.done, current: !s.done && si === m.steps.length - 1 }"
                >
                  <i :class="s.done ? 'ri-checkbox-circle-fill' : 'ri-loader-4-line spin'"></i>
                  <span>{{ s.text }}<span v-if="!s.done && s.waitHint" class="step-wait"> · {{ s.waitHint }}</span></span>
                </li>
              </ul>
              <ul v-else-if="m.streaming" class="progress-steps">
                <li class="current">
                  <i class="ri-loader-4-line spin"></i>
                  <span>正在连接服务…</span>
                </li>
              </ul>
              <template v-else-if="m.fileChip">
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
          <div class="composer-attach-row">
            <label class="upload-btn" title="上传一个或多个附件">
              <input
                type="file"
                ref="fileInput"
                class="upload-input"
                multiple
                accept=".xlsx,.xls,.csv,.tsv,.pdf,.png,.jpg,.jpeg,.txt,.md"
                @change="onFileChange"
              />
              <i class="ri-upload-cloud-2-line"></i>
              <span>上传附件</span>
            </label>
            <div v-if="chatAttachments.length" class="composer-chips">
              <span
                v-for="att in chatAttachments"
                :key="att.localId"
                class="file-chip"
                :class="{ uploading: att.uploading, error: att.error }"
                :title="att.error || att.name"
              >
                <i v-if="att.uploading" class="ri-loader-4-line spin"></i>
                <i v-else-if="att.error" class="ri-error-warning-line"></i>
                <i v-else class="ri-file-text-line"></i>
                <span class="file-chip-name">{{ att.name }}</span>
                <button type="button" class="chip-x" @click="removeAttachment(att.localId)" title="移除">
                  <i class="ri-close-line"></i>
                </button>
              </span>
            </div>
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
                <option value="auto">自动匹配</option>
                <option value="">无模板（仅基线）</option>
                <option v-for="s in skills" :key="s.id" :value="String(s.id)">{{ s.name }}</option>
              </select>
              <i class="ri-arrow-down-s-line skill-caret"></i>
            </label>
            <div class="composer-actions">
              <button
                v-if="chatThinking"
                type="button"
                class="btn steer"
                title="停止当前识别"
                @click="abortTurn"
              >
                <span>停止</span>
              </button>
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
  applyPasteGrid,
  validateTable,
  validateRowCells
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
const chatAttachments = ref([])
const chatThinking = ref(false)
const chatMsgs = ref(null)
const pickedSkill = ref('auto')
const streamIntent = ref('recognize')
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
const confirming = ref(false)
const lastSkillName = ref('')

const invalidCount = computed(() => invalidMap.value.size)
const conflictCount = computed(() =>
  tableData.value.reduce((n, row) => n + Object.keys(row?._conflicts || {}).length, 0)
)
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
const readyFileIds = computed(() =>
  chatAttachments.value.filter(a => a.fileId && !a.uploading && !a.error).map(a => a.fileId))
const hasReadyFiles = computed(() => readyFileIds.value.length > 0)
const isUploadingFiles = computed(() => chatAttachments.value.some(a => a.uploading))
const canSubmit = computed(() => {
  if (isUploadingFiles.value) return false
  return chatThinking.value ? hasDraft.value : !!(hasDraft.value || hasReadyFiles.value)
})
const canSteer = computed(() => !!(hasDraft.value || hasReadyFiles.value || chatQueue.value.length))
const thinkingLabel = computed(() => (streamIntent.value === 'chat' ? '思考中' : '识别中'))
const composerPlaceholder = computed(() => {
  if (isUploadingFiles.value) return '正在上传附件…'
  if (chatThinking.value) {
    return streamIntent.value === 'chat'
      ? '思考中… Enter 排队'
      : '识别中… Enter 排队，或点「立即重导」打断'
  }
  if (hasReadyFiles.value) return '可补充要求后发送；空发送会识别附件，追问则只聊天'
  return '上传附件或描述规则，Enter 发送，Shift+Enter 换行'
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
  pickedSkill.value = 'auto'
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
  if (rowIndex < 0) return ''
  if (invalidMap.value.has(`${rowIndex}::${column.field}`)) return 'cell-invalid'
  if (row?._conflicts && row._conflicts[column.field]) return 'cell-conflict'
  return ''
}

function conflictTitle(row, col) {
  const vals = row?._conflicts?.[col.field]
  if (!vals) return ''
  const list = Array.isArray(vals) ? vals.map(v => String(v).trim()).filter(Boolean) : [String(vals)]
  const kept = String(row[col.field] ?? list[0] ?? '').trim()
  const others = list.filter(v => v !== kept)
  if (!others.length) return '分页取值不一致，已保留先出现的值'
  return `分页冲突：表内保留 ${kept}；其它段还有 ${others.join('、')}`
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

function removeAttachment(localId) {
  chatAttachments.value = chatAttachments.value.filter(a => a.localId !== localId)
  if (!chatAttachments.value.length && fileInput.value) fileInput.value.value = ''
}

async function onFileChange(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  if (fileInput.value) fileInput.value.value = ''
  chatSessionStarted.value = true
  const uploadTurn = {
    role: 'assistant',
    content: '',
    steps: files.map(f => ({ text: `准备上传 ${f.name}`, done: false })),
    streaming: true,
    localOnly: true
  }
  chatLog.value.push(uploadTurn)
  scrollChat()
  let ok = 0
  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    const localId = `${Date.now()}-${Math.random()}`
    const item = { localId, name: f.name, fileId: null, uploading: true, error: null }
    chatAttachments.value.push(item)
    uploadTurn.steps[i].text = `正在上传 ${f.name}`
    scrollChat()
    try {
      const up = await api.upload(f)
      const idx = chatAttachments.value.findIndex(a => a.localId === localId)
      if (idx >= 0) {
        chatAttachments.value[idx] = { ...chatAttachments.value[idx], fileId: up.file_id, uploading: false }
      }
      uploadTurn.steps[i].done = true
      uploadTurn.steps[i].text = `已上传 ${f.name}`
      ok += 1
    } catch (err) {
      const idx = chatAttachments.value.findIndex(a => a.localId === localId)
      if (idx >= 0) {
        chatAttachments.value[idx] = {
          ...chatAttachments.value[idx],
          uploading: false,
          error: err.message || '上传失败'
        }
      }
      uploadTurn.steps[i].done = true
      uploadTurn.steps[i].text = `上传失败 ${f.name}：${err.message || '未知错误'}`
    }
    scrollChat()
  }
  uploadTurn.streaming = false
  uploadTurn.content = ok
    ? `已上传 ${ok} 个附件，可补充要求后发送，或直接发送开始识别。`
    : '附件上传失败，请重试。'
}

function pushAttachmentBubbleIfNeeded() {
  const names = chatAttachments.value
    .filter(a => a.fileId && !a.error)
    .map(a => a.name)
  if (!names.length) return
  chatLog.value.push({ role: 'user', content: names.join('、'), fileChip: true })
}

function onComposerKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendOrQueue()
  }
}

function enqueueDraft() {
  const text = chatInput.value.trim()
  if (!text && !hasReadyFiles.value) return false
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
  } else {
    pushAttachmentBubbleIfNeeded()
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
  } else {
    pushAttachmentBubbleIfNeeded()
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

function abortTurn() {
  turnSeq += 1
  abortCtrl.value?.abort()
  chatThinking.value = false
  stopClock()
  const last = chatLog.value[chatLog.value.length - 1]
  if (last && last.streaming) {
    last.streaming = false
    last.content = last.content || '已停止'
  }
}

function skillPayload() {
  if (pickedSkill.value === 'auto') return { skill_id: null, auto_skill: true }
  if (!pickedSkill.value) return { skill_id: null, auto_skill: false }
  const id = Number(pickedSkill.value)
  return { skill_id: Number.isFinite(id) ? id : null, auto_skill: false }
}

async function runTurn() {
  turnSeq += 1
  const myTurn = turnSeq
  abortCtrl.value = new AbortController()
  chatThinking.value = true
  streamIntent.value = 'recognize'
  startClock()
  scrollChat()
  const assistant = {
    role: 'assistant',
    content: '',
    steps: [{ text: '已发送，正在连接服务…', done: false }],
    streaming: true
  }
  chatLog.value.push(assistant)
  scrollChat()
  try {
    const res = await api.chatStream({
      messages: chatLog.value
        .filter(m => !m.fileChip && !m.localOnly && !m.pending && !m.streaming && m.content)
        .map(m => ({ role: m.role, content: m.content })),
      columns: columns.value,
      ...skillPayload(),
      file_ids: readyFileIds.value,
      table_name: props.tableName || ''
    }, {
      signal: abortCtrl.value.signal,
      onStep: (step) => {
        if (myTurn !== turnSeq) return
        if (step.intent) streamIntent.value = step.intent
        const prev = assistant.steps[assistant.steps.length - 1]
        if (prev) prev.done = true
        assistant.steps.push({ text: step.text, done: false })
        scrollChat()
      },
      onPing: (ping) => {
        if (myTurn !== turnSeq) return
        const last = assistant.steps[assistant.steps.length - 1]
        if (!last || last.done) return
        last.pings = (last.pings || 0) + 1
        if (last.pings < 2) return
        const elapsed = ping?.elapsed ?? Math.floor((Date.now() - runStartedAt.value) / 1000)
        last.waitHint = `已等待 ${elapsed}s`
        scrollChat()
      }
    })
    if (myTurn !== turnSeq) return
    assistant.steps.forEach(s => { s.done = true })
    await nextTick()
    if (assistant.steps.length) {
      await new Promise(r => setTimeout(r, 450))
    }
    if (myTurn !== turnSeq) return
    assistant.streaming = false
    assistant.content = res.reply || ''
    if (res.intent) streamIntent.value = res.intent
    if (res.intent !== 'chat' && res.rows && res.rows.length) {
      applyRows(res.rows, { replace: true })
      lastSkillName.value = res.skill_name || ''
      const skillHint = res.skill_name ? `（Skill：${res.skill_name}）` : ''
      const conflictHint = conflictCount.value ? `，${conflictCount.value} 格分页冲突已标黄` : ''
      notice.value = `AI 识别完成，填入 ${res.rows.length} 行${skillHint}${conflictHint}`
      noticeType.value = conflictCount.value ? 'warning' : 'success'
      validateFilled()
      if (!chatOpen.value) unreadDone.value = true
    }
    scrollChat()
  } catch (e) {
    if (e.name === 'AbortError' || e.message?.includes('abort')) {
      const i = chatLog.value.lastIndexOf(assistant)
      if (i >= 0 && assistant.streaming) chatLog.value.splice(i, 1)
      return
    }
    if (myTurn !== turnSeq) return
    assistant.streaming = false
    assistant.content = `出错了：${e.message}`
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
    target._conflicts = row._conflicts && Object.keys(row._conflicts).length ? row._conflicts : undefined
    idx++
  }
  invalidPaint.value += 1
}

async function onEditClosed({ row, column } = {}) {
  if (lastSheetKey.value === 'Escape' && row && column?.field) {
    tableRef.value?.revertData?.(row, column.field)
  }
  lastSheetKey.value = ''
  if (row) validateFilled(row)
}

function applyValidationMap(nextMap, { rowIndex = null } = {}) {
  if (rowIndex == null) {
    invalidMap.value = nextMap
  } else {
    const merged = new Map(invalidMap.value)
    for (const key of merged.keys()) {
      const idx = Number(key.split('::')[0])
      if (idx === rowIndex) merged.delete(key)
    }
    nextMap.forEach((msg, key) => merged.set(key, msg))
    invalidMap.value = merged
  }
  invalidPaint.value += 1
}

function validateFilled(changedRow = null) {
  if (changedRow) {
    const rowIndex = tableData.value.indexOf(changedRow)
    if (rowIndex < 0) return
    applyValidationMap(validateRowCells(changedRow, rowIndex, columns.value), { rowIndex })
    return
  }
  applyValidationMap(validateTable(tableData.value, columns.value))
}

function clearInvalid() {
  invalidMap.value = new Map()
  invalidPaint.value += 1
}

async function confirmImport() {
  validateFilled()
  const filled = filledRows(tableData.value, columns.value)
  if (invalidMap.value.size) {
    notice.value = `有 ${invalidMap.value.size} 个单元格需要修正（仅校验已填写行中的必填与格式）`
    noticeType.value = 'error'
    return
  }
  if (!filled.length) {
    notice.value = '没有可导入的数据'
    noticeType.value = 'warning'
    return
  }
  const conflicts = []
  for (const row of filled) {
    const cmap = row._conflicts || {}
    for (const [field, values] of Object.entries(cmap)) {
      conflicts.push({
        cpds_id: row.cpds_id || '',
        field,
        kept: row[field],
        others: Array.isArray(values) ? values.slice(1) : values,
      })
    }
  }
  confirming.value = true
  try {
    const res = await api.commitImport(props.tableId, {
      rows: filled.map(({ _conflicts, ...rest }) => rest),
      source_files: chatAttachments.value.map(a => a.name).filter(Boolean),
      skill_name: lastSkillName.value,
      conflicts,
    })
    notice.value = `已写入结果表 ${res.row_count} 行`
    noticeType.value = 'success'
    emit('imported', { rows: filled, batch_id: res.batch_id, row_count: res.row_count })
    emit('close')
  } catch (e) {
    notice.value = e.message || '写入失败'
    noticeType.value = 'error'
  } finally {
    confirming.value = false
  }
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
.progress-steps {
  list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px;
}
.progress-steps li {
  display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #5f6b7a; line-height: 1.45;
}
.progress-steps li .ri { font-size: 15px; margin-top: 1px; color: #9aa0a8; }
.progress-steps li.current { color: #1f2329; }
.progress-steps li.current .ri { color: #2468DB; }
.progress-steps li.done { color: #389e0d; }
.progress-steps li.done .ri { color: #52c41a; }
.step-wait { color: #8a8f98; font-size: 12px; }

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
.composer-attach-row {
  display: flex; align-items: flex-start; gap: 8px; flex-wrap: wrap;
  margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px dashed #e8eaed;
}
.upload-input { display: none; }
.upload-btn {
  display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0;
  height: 34px; padding: 0 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid #c5d8f7; background: #eef4fd; color: #2468DB;
  font-size: 13px; font-weight: 500; transition: all 0.12s;
}
.upload-btn:hover { background: #dfeafb; border-color: #9bb8ea; }
.upload-btn .ri { font-size: 17px; }
.composer-chips { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; min-width: 0; }
.file-chip {
  display: inline-flex; align-items: center; gap: 4px; max-width: 100%;
  background: #f3f6fb; color: #2b4f8f; border: 1px solid #e3ebf7;
  border-radius: 8px; padding: 4px 8px; font-size: 12px;
}
.file-chip.uploading { opacity: 0.85; border-style: dashed; }
.file-chip.error { color: #cf1322; background: #fff1f0; border-color: #ffccc7; }
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
.table-wrap { flex: 1; min-height: 0; border: 1px solid #e8eaec; border-radius: 4px; overflow: hidden; }
.data-table :deep(.vxe-table--header-wrapper) { background: #fafafa; }
.data-table :deep(.vxe-table--border-line) { border-color: #e8eaec !important; }
.data-table :deep(.vxe-header--column) {
  background: #fafafa !important; color: #4a4a4a; font-weight: 500; font-size: 12px;
  text-align: left !important; border-color: #e8eaec !important;
}
.data-table :deep(.vxe-header--column .vxe-cell) { justify-content: flex-start !important; }
.data-table :deep(.vxe-body--column) {
  font-size: 13px; color: #333; text-align: left !important; border-color: #e8eaec !important;
}
.data-table :deep(.vxe-body--column .vxe-cell) { justify-content: flex-start !important; }
.data-table :deep(.cell-invalid) { background-color: #ffe9e8 !important; color: #e02b2b; }
.data-table :deep(.cell-conflict) { background-color: #fff7d6 !important; }
.conflict-count { color: #d48806; font-size: 12px; margin-left: 8px; }

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
