<template>
  <div class="dialog-mask" @click.self="$emit('close')">
    <div class="panel">
      <div class="panel-header">
        <span class="title">设置</span>
        <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
      </div>

      <div class="panel-body">
        <!-- 页签：模型 API / Skill -->
        <div class="tabs">
          <span :class="['tab', tab === 'model' && 'active']" @click="tab = 'model'"><i class="ri-cpu-line"></i> 模型 API</span>
          <span :class="['tab', tab === 'skill' && 'active']" @click="tab = 'skill'"><i class="ri-file-list-3-line"></i> Skill 模板</span>
        </div>

        <!-- 模型 API 设置 -->
        <div v-show="tab === 'model'" class="tab-body">
          <div class="mock-row">
            <label class="switch-label">
              <input type="checkbox" v-model="settings.mock" />
              <span>Mock 模式（无 API key 时返回演示数据，先跑通交互）</span>
            </label>
          </div>

          <div class="model-block">
            <div class="block-title">文本模型 <span class="hint">用于 Excel / CSV / PDF 文本类文件</span></div>
            <div class="form-row"><label>Base URL</label><input v-model="settings.text_model.base_url" class="inp" placeholder="https://api.openai.com/v1" /></div>
            <div class="form-row"><label>API Key</label><input v-model="settings.text_model.api_key" class="inp" type="password" placeholder="sk-..." /></div>
            <div class="form-row"><label>模型名</label><input v-model="settings.text_model.model" class="inp" placeholder="gpt-4o-mini" /></div>
            <button class="btn ghost" @click="test('text_model')" :disabled="testing.text"><i v-if="testing.text" class="ri-loader-4-line spin"></i><i v-else class="ri-links-line"></i> 测试连接</button>
            <span class="test-result" :class="testResult.text?.ok ? 'ok' : 'fail'">{{ testResult.text?.message }}</span>
          </div>

          <div class="model-block">
            <div class="block-title">视觉模型 <span class="hint">用于图片扫描件表格识别</span></div>
            <div class="form-row"><label>Base URL</label><input v-model="settings.vision_model.base_url" class="inp" placeholder="https://api.openai.com/v1" /></div>
            <div class="form-row"><label>API Key</label><input v-model="settings.vision_model.api_key" class="inp" type="password" placeholder="sk-..." /></div>
            <div class="form-row"><label>模型名</label><input v-model="settings.vision_model.model" class="inp" placeholder="gpt-4o" /></div>
            <button class="btn ghost" @click="test('vision_model')" :disabled="testing.vision"><i v-if="testing.vision" class="ri-loader-4-line spin"></i><i v-else class="ri-links-line"></i> 测试连接</button>
            <span class="test-result" :class="testResult.vision?.ok ? 'ok' : 'fail'">{{ testResult.vision?.message }}</span>
          </div>
        </div>

        <!-- Skill 管理 -->
        <div v-show="tab === 'skill'" class="tab-body skill-layout">
          <div class="skill-list">
            <div class="skill-list-header">
              <span>模板列表</span>
              <div class="list-btns">
                <button class="btn ghost mini" @click="importMd" title="从 .md 文件导入"><i class="ri-upload-2-line"></i></button>
                <button class="btn ghost mini" @click="newSkill" title="新建"><i class="ri-add-line"></i></button>
              </div>
            </div>
            <input type="file" ref="mdInput" style="display:none" accept=".md" @change="onMdPicked" />
            <div v-for="s in skills" :key="s.id"
              :class="['skill-item', currentId === s.id && 'active']"
              @click="openSkill(s.id)">
              <span class="skill-name">{{ s.name }}</span>
              <span class="skill-actions">
                <i v-if="s.enabled" class="enabled-dot ri-checkbox-circle-fill" title="已启用"></i>
                <i class="del ri-delete-bin-line" @click.stop="removeSkill(s.id)" title="删除"></i>
              </span>
            </div>
            <div v-if="!skills.length" class="empty">暂无模板，点 <i class="ri-add-line"></i> 新建或 <i class="ri-upload-2-line"></i> 导入 .md</div>
          </div>
          <div class="skill-editor">
            <div class="editor-toolbar">
              <span class="current-file">{{ currentName || '未选择' }}</span>
              <div>
                <button v-if="currentId" class="btn ghost mini" @click="toggleEnable"><i :class="currentEnabled ? 'ri-close-circle-line' : 'ri-play-circle-line'"></i> {{ currentEnabled ? '取消启用' : '启用' }}</button>
                <button v-if="currentId" class="btn ghost mini" @click="exportMd" title="导出为 .md 文件"><i class="ri-download-2-line"></i> 导出</button>
                <button v-if="currentId" class="btn primary mini" @click="saveSkill"><i class="ri-save-line"></i> 保存</button>
              </div>
            </div>
            <textarea v-model="content" class="md-editor" placeholder="# 模板名称&#10;&#10;在这里用 Markdown 描述列映射规则、单位换算、格式约定等，AI 识别时会遵循这些规则。"></textarea>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <span class="save-tip">{{ saveTip }}</span>
        <button class="btn" @click="$emit('close')">关闭</button>
        <button v-show="tab === 'model'" class="btn primary" @click="saveSettings"><i class="ri-save-line"></i> 保存设置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const emit = defineEmits(['close', 'skills-changed'])

const tab = ref('model')
const settings = ref({ text_model: {}, vision_model: {}, mock: true })
const testing = ref({ text: false, vision: false })
const testResult = ref({ text: null, vision: null })
const saveTip = ref('')

const skills = ref([])
const currentId = ref(null)
const currentName = ref('')
const currentEnabled = ref(false)
const content = ref('')
const mdInput = ref(null)

onMounted(async () => {
  settings.value = await api.getSettings()
  await loadSkills()
})

async function loadSkills() {
  skills.value = await api.listSkills()
  emit('skills-changed', skills.value)
}

async function saveSettings() {
  await api.saveSettings(settings.value)
  saveTip.value = '已保存 ✓'
  setTimeout(() => saveTip.value = '', 2000)
}

async function test(key) {
  const rKey = key === 'text_model' ? 'text' : 'vision'
  testing.value[rKey] = true
  testResult.value[rKey] = null
  try {
    testResult.value[rKey] = await api.testModel(settings.value[key])
  } catch (e) {
    testResult.value[rKey] = { ok: false, message: e.message }
  } finally {
    testing.value[rKey] = false
  }
}

function newSkill() {
  const name = prompt('输入模板名称（如: 药明CRO模板）')
  if (!name) return
  currentId.value = null
  currentName.value = name
  content.value = `# ${name}\n\n## 列映射规则\n\n## 注意事项\n`
  currentEnabled.value = false
}

function importMd() {
  mdInput.value?.click()
}

async function onMdPicked(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const res = await api.importSkillMd(file)
    saveTip.value = `已导入「${res.name}」✓`
    setTimeout(() => saveTip.value = '', 2000)
    await loadSkills()
    await openSkill(res.id)
  } catch (err) {
    alert('导入失败：' + err.message)
  } finally {
    mdInput.value.value = ''
  }
}

function exportMd() {
  if (!currentId.value) return
  window.open(api.exportSkillMdUrl(currentId.value), '_blank')
}

async function openSkill(id) {
  const res = await api.getSkill(id)
  currentId.value = res.id
  currentName.value = res.name
  content.value = res.content
  currentEnabled.value = res.enabled
}

async function saveSkill() {
  if (!currentName.value.trim()) return
  const res = await api.saveSkill({ id: currentId.value, name: currentName.value.trim(), content: content.value })
  currentId.value = res.id
  await loadSkills()
  saveTip.value = '模板已保存 ✓'
  setTimeout(() => saveTip.value = '', 2000)
}

async function removeSkill(id) {
  const s = skills.value.find(x => x.id === id)
  if (!confirm(`删除模板「${s?.name}」？`)) return
  await api.deleteSkill(id)
  if (currentId.value === id) { currentId.value = null; currentName.value = ''; content.value = '' }
  await loadSkills()
}

async function toggleEnable() {
  if (currentEnabled.value) {
    await api.enableSkill(null)
    currentEnabled.value = false
  } else {
    await api.enableSkill(currentId.value)
    currentEnabled.value = true
  }
  await loadSkills()
}
</script>

<style scoped>
.dialog-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 200; }
.panel { width: 880px; max-width: 95vw; height: 600px; background: #fff; border-radius: 8px; display: flex; flex-direction: column; box-shadow: 0 6px 24px rgba(0,0,0,.08); }
.panel-header { display: flex; align-items: center; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; }
.close-btn:hover { color: #333; }
.panel-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.tabs { display: flex; gap: 4px; padding: 10px 20px 0; border-bottom: 1px solid #f0f0f0; }
.tab { padding: 8px 16px; cursor: pointer; color: #666; font-size: 14px; border-bottom: 2px solid transparent; display: inline-flex; align-items: center; gap: 5px; }
.tab .ri { font-size: 15px; }
.tab.active { color: #644bdc; border-bottom-color: #644bdc; font-weight: 500; }
.tab-body { flex: 1; overflow: auto; padding: 16px 20px; }

.mock-row { margin-bottom: 16px; padding: 10px 12px; background: #faf9ff; border-radius: 4px; }
.switch-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #555; cursor: pointer; }
.model-block { border: 1px solid #f0f0f0; border-radius: 6px; padding: 14px 16px; margin-bottom: 14px; }
.block-title { font-weight: 600; margin-bottom: 12px; color: #1a1a1a; }
.hint { font-weight: 400; color: #999; font-size: 12px; margin-left: 8px; }
.form-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.form-row label { width: 80px; color: #666; font-size: 13px; }
.inp { flex: 1; border: 1px solid #e5e5e5; border-radius: 4px; padding: 6px 10px; font-size: 13px; }
.inp:focus { outline: none; border-color: #644bdc; }
.test-result { margin-left: 10px; font-size: 12px; }
.test-result.ok { color: #389e0d; }
.test-result.fail { color: #cf1322; }

.skill-layout { display: flex; gap: 0; padding: 0; }
.skill-list { width: 220px; border-right: 1px solid #f0f0f0; padding: 12px; overflow: auto; }
.list-btns { display: flex; gap: 4px; }
.skill-list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; color: #666; }
.skill-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.skill-item:hover { background: #f5f5f5; }
.skill-item.active { background: #f5f2ff; color: #644bdc; }
.skill-actions { display: flex; gap: 8px; align-items: center; }
.enabled-dot { color: #52c41a; font-size: 14px; }
.del { color: #e02b2b; font-size: 14px; cursor: pointer; }
.del:hover { color: #c01818; }
.empty { color: #bbb; font-size: 12px; text-align: center; padding: 30px 0; }
.skill-editor { flex: 1; display: flex; flex-direction: column; }
.editor-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.current-file { font-size: 13px; color: #666; }
.md-editor { flex: 1; border: none; outline: none; padding: 14px; resize: none; font-family: Consolas, monospace; font-size: 13px; line-height: 1.6; }

.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }
.btn.mini { padding: 3px 10px; font-size: 12px; }
.btn.mini .ri { font-size: 13px; }
.panel-footer { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; }
.save-tip { color: #389e0d; font-size: 13px; margin-right: auto; }
.spin { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
