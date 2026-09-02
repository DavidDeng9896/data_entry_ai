<template>
  <div class="dialog-mask" @click.self="onMaskClick">
    <div class="workspace" :class="{ 'with-chat': chatOpen }">
      <div class="dialog">
        <div class="panel-header">
          <span class="title">新建结果表</span>
          <span class="sub">一次配置表名称与全部列</span>
          <button v-if="!chatOpen" class="btn ai-btn" type="button" @click="openChat">
            <i class="ri-sparkling-2-line"></i> AI 助手
            <span v-if="chatThinking" class="pulse-dot" title="助手仍在执行"></span>
            <span v-else-if="unreadDone" class="badge-dot" title="有新的结构"></span>
          </button>
          <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
        </div>

        <div class="panel-body">
          <div class="meta-row">
            <div class="meta-field">
              <label>表名称 <span class="req">*</span></label>
              <input v-model="name" class="inp" placeholder="如：Dog PK、Monkey PK、Thermodynamic Solubility (μg/mL)" />
            </div>
            <div class="meta-field desc">
              <label>描述</label>
              <input v-model="description" class="inp" placeholder="这张表是干什么的（可选）" />
            </div>
          </div>

          <div class="tabs">
            <button type="button" :class="['tab', leftTab === 'columns' && 'active']" @click="leftTab = 'columns'">
              列配置 <span class="sub">({{ draft.length }} 列)</span>
            </button>
            <button type="button" :class="['tab', leftTab === 'skill' && 'active']" @click="leftTab = 'skill'; skillDirty = false">
              Skill 草稿
              <span v-if="skillDirty" class="tab-dot" title="已更新"></span>
            </button>
          </div>

          <template v-if="leftTab === 'columns'">
            <table class="col-table">
              <thead>
                <tr>
                  <th style="width:130px">字段名</th>
                  <th style="width:160px">显示名称</th>
                  <th style="width:100px">类型</th>
                  <th style="width:60px">必填</th>
                  <th>下拉选项（逗号分隔）</th>
                  <th style="width:150px">列说明</th>
                  <th style="width:50px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(col, i) in draft" :key="i">
                  <td><input v-model="col.field" class="inp" placeholder="field" /></td>
                  <td><input v-model="col.title" class="inp" placeholder="列名" /></td>
                  <td>
                    <select v-model="col.type" class="inp">
                      <option value="text">文本</option>
                      <option value="number">数字</option>
                      <option value="date">日期</option>
                      <option value="select">下拉</option>
                    </select>
                  </td>
                  <td style="text-align:center"><input type="checkbox" v-model="col.required" /></td>
                  <td>
                    <input v-if="col.type === 'select'" class="inp" :value="col.options.join(',')"
                      @input="col.options = $event.target.value.split(',').map(s => s.trim()).filter(Boolean)"
                      placeholder="如: CHO01,CHO02" />
                    <span v-else class="muted">-</span>
                  </td>
                  <td><input v-model="col.description" class="inp" placeholder="供 AI 理解语义" /></td>
                  <td><button class="del" @click="draft.splice(i, 1)" title="删除列"><i class="ri-delete-bin-line"></i></button></td>
                </tr>
              </tbody>
            </table>
            <div class="quick-add">
              <button class="btn ghost" @click="addColumn"><i class="ri-add-line"></i> 添加列</button>
              <button v-if="tables.length" class="btn ghost" @click="copyFromOpen = !copyFromOpen"><i class="ri-file-copy-line"></i> 从现有表复制列</button>
            </div>
            <div v-if="copyFromOpen" class="copy-list">
              <span v-for="t in tables" :key="t.id" class="copy-chip" @click="copyColumns(t)">
                <i class="ri-file-list-3-line"></i> {{ t.name }}
              </span>
            </div>
          </template>

          <div v-else class="skill-draft">
            <label>Skill 名称</label>
            <input v-model="skillName" class="inp" placeholder="如：PK · 某 CRO 版式" />
            <label>Markdown</label>
            <textarea v-model="skillMd" class="md-editor" placeholder="# 模板名称&#10;&#10;匹配线索、主源、字段映射、不映射、特殊值…"></textarea>
          </div>
        </div>

        <div class="panel-footer">
          <span class="err">{{ error }}</span>
          <button class="btn" @click="$emit('close')">取消</button>
          <button class="btn primary" @click="create"><i class="ri-check-line"></i> 创建</button>
        </div>
      </div>

      <aside v-show="chatOpen" class="chat-drawer">
        <div class="chat-header">
          <div class="chat-header-main">
            <span class="chat-title">建表助手</span>
            <span v-if="chatThinking" class="chat-badge busy"><i class="ri-loader-4-line spin"></i> {{ thinkingLabel }} {{ runClock }}</span>
            <span v-else-if="unreadDone" class="chat-badge done">有新结构</span>
          </div>
          <button class="icon-btn" type="button" title="收起（后台继续）" @click="collapseChat">
            <i class="ri-contract-right-line"></i>
          </button>
        </div>

        <div class="chat-scroll" ref="chatMsgs">
          <div v-if="!chatLog.length && !chatThinking" class="chat-empty">
            <div class="chat-empty-title">上传结果文件或描述要哪些列</div>
            <div class="chat-empty-desc">点回形针上传（可多选）。助手会按内部规范抽出列，并生成可编辑的 Skill 草稿。</div>
          </div>
          <article
            v-for="(m, i) in chatLog"
            :key="i"
            :class="['turn', m.role, { pending: m.pending }]"
          >
            <div class="turn-label">{{ m.role === 'user' ? '你' : '助手' }}</div>
            <div class="turn-body">
              <ul v-if="m.steps?.length && (m.streaming || m.localOnly)" class="progress-steps">
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
              <template v-if="m.fileChip">
                <span class="turn-file"><i class="ri-file-text-line"></i>{{ m.content }}</span>
              </template>
              <template v-else-if="m.content">{{ m.content }}</template>
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
        </div>

        <div class="composer">
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
          <textarea
            v-model="chatInput"
            class="composer-input"
            rows="2"
            :placeholder="composerPlaceholder"
            @keydown="onComposerKeydown"
          />
          <div class="composer-toolbar">
            <label class="upload-btn" title="上传一个或多个附件">
              <input
                type="file"
                ref="fileInput"
                class="upload-input"
                multiple
                accept=".xlsx,.xls,.csv,.tsv,.pdf,.png,.jpg,.jpeg,.txt,.md"
                @change="onFileChange"
              />
              <i class="ri-attachment-2"></i>
            </label>
            <button
              type="button"
              class="btn send"
              :class="primaryAction.kind"
              :title="primaryAction.title"
              :disabled="primaryAction.disabled"
              @click="onPrimaryAction"
            >
              <i :class="primaryAction.icon"></i>
            </button>
          </div>
        </div>
      </aside>

      <button
        v-if="!chatOpen && chatSessionStarted"
        type="button"
        class="chat-handle"
        :class="{ busy: chatThinking, done: unreadDone }"
        @click="openChat"
        :title="chatThinking ? '助手执行中，点击展开' : '展开建表助手'"
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

const emit = defineEmits(['close', 'created'])

const name = ref('')
const description = ref('')
const draft = ref([])
const error = ref('')
const copyFromOpen = ref(false)
const tables = ref([])
const leftTab = ref('columns')
const skillName = ref('')
const skillMd = ref('')
const skillDirty = ref(false)

const chatOpen = ref(false)
const chatSessionStarted = ref(false)
const chatLog = ref([])
const chatInput = ref('')
const chatAttachments = ref([])
const chatThinking = ref(false)
const chatMsgs = ref(null)
const streamIntent = ref('schema')
const unreadDone = ref(false)
const fileInput = ref(null)
const chatQueue = ref([])
const queueOpen = ref(false)
const abortCtrl = ref(null)
const runStartedAt = ref(0)
const runClock = ref('0:00')
let clockTimer = null
let turnSeq = 0

const hasDraft = computed(() => !!chatInput.value.trim())
const readyFileIds = computed(() =>
  chatAttachments.value.filter(a => a.fileId && !a.uploading && !a.error).map(a => a.fileId))
const hasReadyFiles = computed(() => readyFileIds.value.length > 0)
const isUploadingFiles = computed(() => chatAttachments.value.some(a => a.uploading))
const canSubmit = computed(() => {
  if (isUploadingFiles.value) return false
  return !!(hasDraft.value || hasReadyFiles.value)
})
const primaryAction = computed(() => {
  if (isUploadingFiles.value) {
    return { kind: 'wait', icon: 'ri-loader-4-line spin', title: '上传中', disabled: true }
  }
  if (!chatThinking.value) {
    return { kind: 'send', icon: 'ri-arrow-up-line', title: '发送', disabled: !canSubmit.value }
  }
  if (hasDraft.value) {
    return { kind: 'steer', icon: 'ri-arrow-up-line', title: '立即按新指令重出', disabled: false }
  }
  return { kind: 'stop', icon: 'ri-stop-mini-fill', title: '停止', disabled: false }
})
const thinkingLabel = computed(() => (streamIntent.value === 'chat' ? '思考中' : '设计列'))
const composerPlaceholder = computed(() => {
  if (isUploadingFiles.value) return '正在上传附件…'
  if (chatThinking.value) {
    if (hasDraft.value) return '发送即打断并按新指令重出结构'
    return streamIntent.value === 'chat' ? '思考中…' : '正在设计列，点方块停止'
  }
  if (hasReadyFiles.value) return '可补充要求后发送，或直接发送抽出列'
  return '上传结果文件或描述要哪些列，Enter 发送'
})

onMounted(async () => {
  tables.value = await api.listTables()
  addColumn()
})

onUnmounted(() => {
  stopClock()
  abortCtrl.value?.abort()
})

function addColumn() {
  draft.value.push({ field: `col_${draft.value.length + 1}`, title: '', type: 'text', required: false, options: [], description: '' })
}

async function copyColumns(t) {
  const cols = await api.getColumns(t.id)
  draft.value = JSON.parse(JSON.stringify(cols))
  copyFromOpen.value = false
}

function onMaskClick() {}

function openChat() {
  chatOpen.value = true
  chatSessionStarted.value = true
  unreadDone.value = false
  nextTick(scrollChat)
}

function collapseChat() {
  chatOpen.value = false
}

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

function scrollChat() {
  setTimeout(() => {
    if (chatMsgs.value) chatMsgs.value.scrollTop = chatMsgs.value.scrollHeight
  }, 30)
}

function removeAttachment(localId) {
  chatAttachments.value = chatAttachments.value.filter(a => a.localId !== localId)
}

async function onFileChange(e) {
  const files = [...(e.target.files || [])]
  e.target.value = ''
  if (!files.length) return
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
    ? `已上传 ${ok} 个附件，可补充要求后发送，或直接发送抽出列。`
    : '附件上传失败，请重试。'
  scrollChat()
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
    if (chatThinking.value && primaryAction.value.kind === 'stop') return
    onPrimaryAction()
  }
}

function onPrimaryAction() {
  if (primaryAction.value.kind === 'stop') {
    abortTurn()
    return
  }
  if (primaryAction.value.kind === 'steer') {
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
    return
  }
  sendOrQueue()
}

function sendOrQueue() {
  if (!canSubmit.value) return
  chatSessionStarted.value = true
  if (chatThinking.value) {
    const text = chatInput.value.trim()
    if (text) {
      chatQueue.value.push({ id: `${Date.now()}-${Math.random()}`, text })
      chatLog.value.push({ role: 'user', content: text, pending: true })
      chatInput.value = ''
      queueOpen.value = true
      scrollChat()
    }
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

function stepFamily(text) {
  return String(text || '')
    .replace(/（[^）]*）/g, '')
    .replace(/·.*/, '')
    .replace(/\d+\/\d+/g, '')
    .replace(/\s+/g, '')
    .slice(0, 12)
}

function applySchema(res) {
  if (res.intent !== 'schema' || !Array.isArray(res.columns) || !res.columns.length) return
  name.value = res.name || name.value
  description.value = res.description || description.value
  draft.value = res.columns.map(c => ({
    field: c.field,
    title: c.title,
    type: c.type || 'text',
    required: !!c.required,
    options: Array.isArray(c.options) ? c.options : [],
    description: c.description || ''
  }))
  if (res.skill_name) skillName.value = res.skill_name
  if (res.skill_md) {
    skillMd.value = res.skill_md
    skillDirty.value = true
  }
  leftTab.value = 'columns'
  if (!chatOpen.value) unreadDone.value = true
}

async function runTurn() {
  turnSeq += 1
  const myTurn = turnSeq
  abortCtrl.value = new AbortController()
  chatThinking.value = true
  streamIntent.value = 'schema'
  startClock()
  const assistant = {
    role: 'assistant',
    content: '',
    steps: [{ text: '已发送，正在连接服务…', done: false }],
    streaming: true
  }
  chatLog.value.push(assistant)
  scrollChat()
  try {
    const res = await api.schemaChatStream({
      messages: chatLog.value
        .filter(m => !m.fileChip && !m.localOnly && !m.pending && !m.streaming && m.content)
        .map(m => ({ role: m.role, content: m.content })),
      file_ids: readyFileIds.value,
      name: name.value,
      description: description.value,
      columns: draft.value,
      skill_name: skillName.value,
      skill_md: skillMd.value
    }, {
      signal: abortCtrl.value.signal,
      onStep: (step) => {
        if (myTurn !== turnSeq) return
        if (step.intent) streamIntent.value = step.intent
        const prev = assistant.steps[assistant.steps.length - 1]
        if (prev && !prev.done && stepFamily(prev.text) === stepFamily(step.text)) {
          prev.text = step.text
          prev.waitHint = ''
          scrollChat()
          return
        }
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
    assistant.streaming = false
    assistant.content = res.reply || ''
    if (res.intent) streamIntent.value = res.intent
    applySchema(res)
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
      if (chatQueue.value.length) {
        const next = chatQueue.value.shift()
        const m = chatLog.value.find(x => x.pending && x.content === next.text)
        if (m) m.pending = false
        runTurn()
      }
    }
  }
}

async function create() {
  error.value = ''
  if (!name.value.trim()) { error.value = '请填写表名称'; return }
  const cols = draft.value.filter(c => c.field.trim() && c.title.trim())
  if (!cols.length) { error.value = '至少配置一列（字段名和显示名称都要填）'; return }
  const fields = cols.map(c => c.field.trim())
  if (new Set(fields).size !== fields.length) { error.value = '字段名不能重复'; return }
  try {
    const t = await api.createTable(name.value.trim(), description.value.trim(), cols)
    if (skillMd.value.trim()) {
      try {
        await api.saveSkill({
          name: (skillName.value || `${name.value.trim()} Skill`).trim(),
          content: skillMd.value
        })
      } catch (e) {
        error.value = `表已创建，但 Skill 未保存：${e.message}`
        emit('created', t)
        return
      }
    }
    emit('created', t)
    emit('close')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.12);
  display: flex; align-items: center; justify-content: center; z-index: 200;
  padding: 16px;
}
.workspace {
  display: flex; align-items: stretch; gap: 12px; max-width: 96vw; max-height: 92vh;
  position: relative;
}
.dialog {
  width: 960px; max-width: min(960px, 96vw); background: #fff; border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0,0,0,.08); max-height: 90vh; display: flex; flex-direction: column;
}
.workspace.with-chat .dialog { width: min(880px, calc(96vw - 420px)); }

.panel-header { display: flex; align-items: center; gap: 10px; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.sub { color: #999; font-size: 12px; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; align-self: center; }
.close-btn:hover { color: #333; }
.panel-body { padding: 16px 20px; overflow: auto; flex: 1; min-height: 0; }

.meta-row { display: flex; gap: 16px; margin-bottom: 12px; }
.meta-field { display: flex; flex-direction: column; gap: 6px; }
.meta-field label { font-size: 13px; color: #666; }
.meta-field.desc { flex: 1; }
.req { color: #e02b2b; }
.inp { width: 100%; border: 1px solid #e5e5e5; border-radius: 4px; padding: 6px 10px; font-size: 13px; }
.inp:focus { outline: none; border-color: #2468DB; }
.meta-field .inp { width: 320px; }
.meta-field.desc .inp { width: 100%; }

.tabs { display: flex; gap: 8px; margin-bottom: 10px; }
.tab {
  border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 4px 10px;
  font-size: 13px; color: #666; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
}
.tab.active { border-color: #2468DB; color: #2468DB; background: #eef4fd; }
.tab-dot { width: 7px; height: 7px; border-radius: 50%; background: #52c41a; }

.col-table { width: 100%; border-collapse: collapse; }
.col-table th { text-align: left; font-weight: 500; color: #666; font-size: 12px; padding: 6px 8px; border-bottom: 1px solid #eee; background: #fafafa; }
.col-table td { padding: 6px 8px; border-bottom: 1px solid #f5f5f5; }
.muted { color: #ccc; }
.del { border: none; background: none; color: #e02b2b; cursor: pointer; font-size: 15px; display: inline-flex; }

.quick-add { display: flex; gap: 8px; margin-top: 10px; }
.copy-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; padding: 10px; background: #fafafa; border-radius: 4px; }
.copy-chip { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #2468DB; border: 1px solid #c5d8f7; border-radius: 4px; padding: 4px 10px; cursor: pointer; }
.copy-chip:hover { background: #eef4fd; }

.skill-draft { display: flex; flex-direction: column; gap: 8px; }
.skill-draft label { font-size: 13px; color: #666; }
.md-editor {
  width: 100%; min-height: 280px; border: 1px solid #e5e5e5; border-radius: 4px;
  padding: 10px; font-size: 13px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  line-height: 1.55; resize: vertical;
}
.md-editor:focus { outline: none; border-color: #2468DB; }

.panel-footer { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; flex-shrink: 0; }
.err { color: #e02b2b; font-size: 13px; margin-right: auto; }
.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }
.btn.ai-btn { border-color: #2468DB; color: #2468DB; background: #fff; margin-left: auto; }
.btn.ai-btn:hover { background: #eef4fd; }
.pulse-dot, .badge-dot { width: 8px; height: 8px; border-radius: 50%; background: #2468DB; margin-left: 4px; }
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
.chat-scroll {
  flex: 1; overflow-y: auto; padding: 14px 14px 10px; display: flex; flex-direction: column;
  gap: 14px; background: #f7f8fa; min-height: 0;
}
.chat-empty { padding: 24px 8px; text-align: left; color: #8a8f98; }
.chat-empty-title { font-size: 13px; font-weight: 500; color: #4a4a4a; margin-bottom: 6px; }
.chat-empty-desc { font-size: 12px; line-height: 1.65; }
.turn { display: flex; flex-direction: column; gap: 4px; }
.turn-label { font-size: 11px; color: #9aa0a8; }
.turn-body { font-size: 13px; line-height: 1.7; color: #2b2f36; word-break: break-word; white-space: pre-wrap; }
.turn.user .turn-body { background: #fff; border: 1px solid #e8eaed; border-radius: 10px; padding: 10px 12px; }
.turn.user.pending .turn-body { opacity: 0.72; }
.turn-meta { font-size: 11px; color: #8aa4d4; }
.turn-file {
  display: inline-flex; align-items: center; gap: 6px; color: #2468DB;
  background: #eef4fd; border-radius: 6px; padding: 4px 8px; font-size: 12px;
}
.progress-steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.progress-steps li { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #5f6b7a; }
.progress-steps li.current { color: #1f2329; }
.progress-steps li.current .ri { color: #2468DB; }
.progress-steps li.done { color: #389e0d; }
.progress-steps li.done .ri { color: #52c41a; }
.step-wait { color: #8a8f98; font-size: 12px; }
.queue-dock { border-top: 1px solid #eef0f2; background: #fff; flex-shrink: 0; }
.queue-head {
  width: 100%; display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border: none; background: transparent; color: #5f6b7a; font-size: 12px; cursor: pointer;
}
.composer {
  margin: 10px 12px 12px; border: 1px solid #dfe3e8; border-radius: 14px;
  background: #fff; padding: 8px 10px; flex-shrink: 0;
}
.composer:focus-within { border-color: #b8ccf5; box-shadow: 0 0 0 3px rgba(36, 104, 219, 0.08); }
.upload-input { display: none; }
.upload-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px; cursor: pointer;
  border: 1px solid #e8eaed; background: #f7f8fa; color: #5f6b7a;
}
.upload-btn:hover { background: #eef4fd; border-color: #c5d8f7; color: #2468DB; }
.composer-chips { display: flex; flex-wrap: nowrap; gap: 6px; overflow-x: auto; padding-bottom: 8px; }
.file-chip {
  display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0;
  max-width: 148px; background: #f3f6fb; color: #2b4f8f; border: 1px solid #e3ebf7;
  border-radius: 8px; padding: 3px 7px; font-size: 12px;
}
.file-chip.uploading { opacity: 0.85; border-style: dashed; }
.file-chip.error { color: #cf1322; background: #fff1f0; border-color: #ffccc7; }
.file-chip-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 104px; }
.chip-x { border: none; background: transparent; color: #5f7db8; cursor: pointer; }
.composer-input {
  width: 100%; border: none; outline: none; resize: none; font-size: 13px; line-height: 1.6;
  min-height: 48px; color: #1f2329; background: transparent;
}
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.btn.send {
  width: 32px; height: 32px; padding: 0; justify-content: center;
  background: #2468DB; border: none; color: #fff; border-radius: 8px;
}
.btn.send:hover { background: #1d5bc4; }
.btn.send:disabled { background: #b8ccf5; cursor: not-allowed; }
.btn.send.stop { background: #1f2329; }
.btn.send.steer { background: #2468DB; }
.btn.send.wait { background: #b8ccf5; }

.chat-handle {
  position: absolute; right: -14px; top: 72px; transform: translateX(100%);
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  border: 1px solid #c5d8f7; background: #fff; color: #2468DB;
  border-radius: 0 8px 8px 0; padding: 10px 8px; cursor: pointer;
  box-shadow: 2px 2px 10px rgba(36, 104, 219, 0.12); font-size: 12px;
}
.handle-label { writing-mode: vertical-rl; letter-spacing: 2px; font-size: 11px; }
.chat-handle.busy { border-color: #2468DB; background: #eef4fd; }
.chat-handle.done { border-color: #95de64; color: #389e0d; }

.spin { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { opacity: 0.45; } }

@media (max-width: 1100px) {
  .workspace { flex-direction: column; align-items: center; overflow: auto; }
  .workspace.with-chat .dialog { width: min(920px, 96vw); }
  .chat-drawer { width: min(920px, 96vw); min-height: 360px; max-height: 50vh; }
  .chat-handle { right: 8px; top: auto; bottom: 24px; transform: none; flex-direction: row; border-radius: 20px; }
  .handle-label { writing-mode: horizontal-tb; letter-spacing: 0; }
}
</style>
