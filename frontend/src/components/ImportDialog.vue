<template>
  <div class="dialog-mask" @click.self="$emit('close')">
    <div class="dialog">
      <div class="dialog-header">
        <span class="title">导入结果数据</span>
        <span class="assay-name">{{ tableName }}</span>
        <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
      </div>

      <div class="dialog-body">
        <div class="toolbar">
          <span class="tip">请批量填入需要进行导入的数据，确认后将进行导入校验。</span>
          <div class="toolbar-right">
            <button v-if="!chatOpen" class="btn ai-btn" @click="chatOpen = true">
              <i class="ri-sparkling-2-line"></i> AI识别导入
            </button>
          </div>
        </div>

        <!-- AI 多轮对话气泡 -->
        <div v-if="chatOpen" class="chat-panel">
          <div class="chat-header">
            <span class="chat-title"><i class="ri-sparkling-2-line"></i> AI 导入助手</span>
            <select v-model="pickedSkill" class="skill-select">
              <option value="">不使用模板</option>
              <option v-for="s in skills" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <span class="chat-close" @click="chatOpen = false"><i class="ri-close-line"></i></span>
          </div>
          <div class="chat-messages" ref="chatMsgs">
            <div v-if="!chatLog.length" class="chat-empty">
              <i class="ri-chat-smile-2-line"></i>
              <div>上传文件或直接描述导入规则，如「浓度单位从 mM 换算成 uM」，然后让我识别导入。</div>
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
            <input v-model="chatInput" class="chat-input" placeholder="输入规则或要求，Enter 发送"
              @keydown.enter.exact.prevent="sendChat" :disabled="chatThinking" />
            <button class="send-btn" @click="sendChat" :disabled="chatThinking || (!chatInput.trim() && !chatFile)">
              <i class="ri-send-plane-fill"></i>
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
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
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
const chatLog = ref([])          // [{role:'user'|'assistant', content, fileChip?}]
const chatInput = ref('')
const chatFile = ref(null)       // 已上传文件 {file_id, filename}
const chatFileId = ref(null)
const chatThinking = ref(false)
const chatMsgs = ref(null)
const pickedSkill = ref('')

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

function editorFor(col) {
  return { autofocus: '.cell-editor' }
}

function addRows(n) {
  for (let i = 0; i < n; i++) {
    const row = {}
    for (const c of columns.value) row[c.field] = ''
    tableData.value.push(row)
  }
}

function onFileChange(e) {
  const f = e.target.files[0]
  if (!f) return
  chatFile.value = f
  // 立即上传拿 file_id
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
      applyRows(res.rows)
      notice.value = `AI 识别完成，填入 ${res.rows.length} 行数据`
      noticeType.value = 'success'
      await validateAll()
    }
    scrollChat()
  } catch (e) {
    chatLog.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    scrollChat()
  } finally {
    chatThinking.value = false
    // 识别完成后保留 file_id，用户可继续对话调整规则后再次发送重新识别
  }
}

function scrollChat() {
  setTimeout(() => {
    if (chatMsgs.value) chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
  }, 30)
}

function applyRows(rows) {
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
/* ===== 截图风格：纯白底、细边框、紫色AI按钮、蓝色确认按钮 ===== */
.dialog-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.12); display: flex; align-items: center; justify-content: center; z-index: 100; }
.dialog { width: 1080px; max-width: 96vw; background: #fff; border-radius: 8px; display: flex; flex-direction: column; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08); }

.dialog-header { display: flex; align-items: center; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.assay-name { color: #999; font-size: 13px; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; align-items: center; }
.close-btn:hover { color: #333; }

.dialog-body { padding: 14px 20px 12px; flex: 1; overflow: hidden; display: flex; flex-direction: column; }

.toolbar { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 10px; min-height: 34px; }
.tip { color: #b3b3b3; font-size: 13px; padding-top: 7px; }
.toolbar-right { display: flex; align-items: flex-start; gap: 8px; }

.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }

.btn.ai-btn { border-color: #644bdc; color: #644bdc; background: #fff; }
.btn.ai-btn:hover { background: #f5f2ff; }
.btn.ai-btn .ri-sparkling-2-line { font-size: 14px; }

/* AI 多轮对话面板 */
.chat-panel { border: 1px solid #ececec; border-radius: 8px; margin-bottom: 10px; background: #fff; display: flex; flex-direction: column; overflow: hidden; }
.chat-header { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-bottom: 1px solid #f0f0f0; background: #faf9ff; }
.chat-title { font-size: 13px; font-weight: 600; color: #644bdc; display: inline-flex; align-items: center; gap: 4px; }
.chat-title .ri { font-size: 14px; }
.chat-header .skill-select { margin-left: auto; width: 160px; border: 1px solid #e5e5e5; border-radius: 4px; padding: 3px 6px; font-size: 12px; color: #555; background: #fff; outline: none; }
.chat-close { color: #999; cursor: pointer; font-size: 16px; display: flex; align-items: center; }
.chat-close:hover { color: #333; }

.chat-messages { max-height: 220px; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; background: #fcfcfd; }
.chat-empty { text-align: center; color: #b3b3b3; font-size: 12px; padding: 14px 20px; line-height: 1.7; }
.chat-empty .ri { font-size: 26px; display: block; margin-bottom: 6px; color: #d9d3f8; }
.chat-msg { display: flex; }
.chat-msg.user { justify-content: flex-end; }
.msg-bubble { max-width: 72%; padding: 7px 12px; border-radius: 10px; font-size: 13px; line-height: 1.6; word-break: break-word; }
.chat-msg.user .msg-bubble { background: #644bdc; color: #fff; border-bottom-right-radius: 3px; }
.chat-msg.assistant .msg-bubble { background: #fff; border: 1px solid #ececec; color: #333; border-bottom-left-radius: 3px; }
.msg-bubble.thinking { color: #999; display: inline-flex; align-items: center; gap: 6px; }
.msg-bubble .ri-file-text-line { margin-right: 4px; }

.chat-input-row { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-top: 1px solid #f0f0f0; }
.attach-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: #644bdc; background: #f0edff; cursor: pointer; font-size: 15px; flex-shrink: 0; }
.attach-btn:hover { background: #e4deff; }
.chat-input { flex: 1; border: 1px solid #e5e5e5; border-radius: 16px; padding: 6px 14px; font-size: 13px; outline: none; }
.chat-input:focus { border-color: #644bdc; }
.send-btn { width: 32px; height: 32px; border: none; background: #1c62d7; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: background 0.12s; flex-shrink: 0; }
.send-btn:hover { background: #2a6fe0; }
.send-btn:disabled { background: #b5cff2; cursor: not-allowed; }
.send-btn .ri { font-size: 15px; }

.spin { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

.notice { border-radius: 4px; padding: 7px 12px; font-size: 13px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.notice .ri { font-size: 15px; flex-shrink: 0; }
.notice.info { background: #f0f5ff; color: #2f54eb; }
.notice.success { background: #f6ffed; color: #389e0d; }
.notice.warning { background: #fffbe6; color: #d48806; }
.notice.error { background: #fff1f0; color: #cf1322; }

/* vxe-table 截图风格：白底、灰表头、细边框 */
.data-table { flex: 1; }
.data-table :deep(.vxe-table--header-wrapper) { background: #fafafa; }
.data-table :deep(.vxe-header--column) { background: #fafafa !important; color: #4a4a4a; font-weight: 500; font-size: 12px; }
.data-table :deep(.vxe-body--column) { font-size: 13px; color: #333; }
.data-table :deep(.vxe-cell--label) { color: #333; }
.data-table :deep(.vxe-table--body-wrapper) { background: #fff; }

/* 必填星号 + 说明 icon */
.required-mark::after { content: ' *'; color: #e02b2b; }
.col-info { color: #c0c0c0; margin-left: 4px; cursor: help; font-size: 13px; }
.col-info:hover { color: #999; }

/* 单元格编辑器 */
.cell-editor { width: 100%; height: 100%; border: none; outline: none; padding: 4px 8px; font-size: 13px; background: #fff; }
select.cell-editor { padding: 4px 4px; }

/* 表格底部 */
.table-footer { display: flex; align-items: center; gap: 10px; padding-top: 10px; }
.invalid-count { color: #e02b2b; font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }
.invalid-count .ri { font-size: 14px; }

.dialog-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; }
</style>
