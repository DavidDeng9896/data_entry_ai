<template>
  <div class="dialog-mask" @click.self="$emit('close')">
    <div class="panel">
      <div class="panel-header">
        <span class="title">新建结果表</span>
        <span class="sub">一次配置表名称与全部列</span>
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

        <div class="cols-title">列配置 <span class="sub">({{ draft.length }} 列)</span></div>
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
      </div>

      <div class="panel-footer">
        <span class="err">{{ error }}</span>
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn primary" @click="create"><i class="ri-check-line"></i> 创建</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const emit = defineEmits(['close', 'created'])

const name = ref('')
const description = ref('')
const draft = ref([])
const error = ref('')
const copyFromOpen = ref(false)
const tables = ref([])

onMounted(async () => {
  tables.value = await api.listTables()
  addColumn()
})

function addColumn() {
  draft.value.push({ field: `col_${draft.value.length + 1}`, title: '', type: 'text', required: false, options: [], description: '' })
}

async function copyColumns(t) {
  const cols = await api.getColumns(t.id)
  draft.value = JSON.parse(JSON.stringify(cols))
  copyFromOpen.value = false
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
    emit('created', t)
    emit('close')
  } catch (e) {
    error.value = e.message
  }
}
</script>

<style scoped>
.dialog-mask { position: fixed; inset: 0; background: rgba(0,0,0,.12); display: flex; align-items: center; justify-content: center; z-index: 200; }
.panel { width: 960px; max-width: 95vw; background: #fff; border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,.08); max-height: 90vh; display: flex; flex-direction: column; }
.panel-header { display: flex; align-items: baseline; gap: 10px; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.sub { color: #999; font-size: 12px; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; align-self: center; }
.close-btn:hover { color: #333; }
.panel-body { padding: 16px 20px; overflow: auto; }

.meta-row { display: flex; gap: 16px; margin-bottom: 16px; }
.meta-field { display: flex; flex-direction: column; gap: 6px; }
.meta-field label { font-size: 13px; color: #666; }
.meta-field.desc { flex: 1; }
.req { color: #e02b2b; }
.inp { width: 100%; border: 1px solid #e5e5e5; border-radius: 4px; padding: 6px 10px; font-size: 13px; }
.inp:focus { outline: none; border-color: #644bdc; }
.meta-field .inp { width: 320px; }
.meta-field.desc .inp { width: 100%; }

.cols-title { font-size: 14px; font-weight: 600; color: #1a1a1a; margin-bottom: 10px; }
.col-table { width: 100%; border-collapse: collapse; }
.col-table th { text-align: left; font-weight: 500; color: #666; font-size: 12px; padding: 6px 8px; border-bottom: 1px solid #eee; background: #fafafa; }
.col-table td { padding: 6px 8px; border-bottom: 1px solid #f5f5f5; }
.muted { color: #ccc; }
.del { border: none; background: none; color: #e02b2b; cursor: pointer; font-size: 15px; display: inline-flex; }

.quick-add { display: flex; gap: 8px; margin-top: 10px; }
.copy-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; padding: 10px; background: #fafafa; border-radius: 4px; }
.copy-chip { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #644bdc; border: 1px solid #d9d3f8; border-radius: 4px; padding: 4px 10px; cursor: pointer; }
.copy-chip:hover { background: #f5f2ff; }
.copy-chip .ri { font-size: 13px; }

.panel-footer { display: flex; justify-content: flex-end; align-items: center; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; }
.err { color: #e02b2b; font-size: 13px; margin-right: auto; }
.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }
</style>
