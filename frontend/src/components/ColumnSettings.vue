<template>
  <div class="dialog-mask" @click.self="$emit('close')">
    <div class="panel">
      <div class="panel-header">
        <span class="title">表头设置</span>
        <span class="sub">配置列的名称、类型和格式，用于确定模拟导入的数据格式</span>
        <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
      </div>
      <div class="panel-body">
        <table class="col-table">
          <thead>
            <tr>
              <th style="width:130px">字段名</th>
              <th style="width:140px">显示名称</th>
              <th style="width:110px">类型</th>
              <th style="width:70px">必填</th>
              <th>下拉选项（逗号分隔）</th>
              <th style="width:150px">列说明</th>
              <th style="width:60px"></th>
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
                <span v-else class="muted">—</span>
              </td>
              <td><input v-model="col.description" class="inp" placeholder="供 AI 理解语义" /></td>
              <td><button class="del" @click="draft.splice(i, 1)" title="删除列"><i class="ri-delete-bin-line"></i></button></td>
            </tr>
          </tbody>
        </table>
        <button class="btn ghost add-btn" @click="addColumn"><i class="ri-add-line"></i> 添加列</button>
      </div>

      <div class="panel-footer">
        <button class="btn" @click="$emit('close')">取消</button>
        <button class="btn primary" @click="save"><i class="ri-save-line"></i> 保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'

const props = defineProps({ tableId: { type: Number, required: true } })
const emit = defineEmits(['close', 'saved'])

const draft = ref([])

onMounted(async () => {
  const cols = await api.getColumns(props.tableId)
  draft.value = JSON.parse(JSON.stringify(cols))
})

function addColumn() {
  draft.value.push({ field: `col_${Date.now() % 10000}`, title: '新列', type: 'text', required: false, options: [], description: '' })
}

async function save() {
  // 基本校验：字段名唯一且非空
  const fields = draft.value.map(c => c.field.trim())
  if (fields.some(f => !f)) return alert('字段名不能为空')
  if (new Set(fields).size !== fields.length) return alert('字段名不能重复')
  await api.saveColumns(props.tableId, draft.value)
  emit('saved')
  emit('close')
}
</script>

<style scoped>
.dialog-mask { position: fixed; inset: 0; background: rgba(0,0,0,.12); display: flex; align-items: center; justify-content: center; z-index: 200; }
.panel { width: 960px; max-width: 95vw; background: #fff; border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,.08); }
.panel-header { display: flex; align-items: baseline; gap: 10px; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.title { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.sub { color: #999; font-size: 12px; }
.close-btn { margin-left: auto; cursor: pointer; color: #999; font-size: 18px; display: flex; align-self: center; }
.close-btn:hover { color: #333; }
.panel-body { padding: 16px 20px; max-height: 60vh; overflow: auto; }
.col-table { width: 100%; border-collapse: collapse; }
.col-table th { text-align: left; font-weight: 500; color: #666; font-size: 12px; padding: 6px 8px; border-bottom: 1px solid #eee; background: #fafafa; }
.col-table td { padding: 6px 8px; border-bottom: 1px solid #f5f5f5; }
.inp { width: 100%; border: 1px solid #e5e5e5; border-radius: 4px; padding: 5px 8px; font-size: 13px; }
.inp:focus { outline: none; border-color: #2468DB; }
.muted { color: #ccc; }
.del { border: none; background: none; color: #e02b2b; cursor: pointer; font-size: 15px; display: inline-flex; }
.add-btn { margin-top: 10px; }
.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #1c62d7; border-color: #1c62d7; color: #fff; }
.btn.primary:hover { background: #2a6fe0; }
.btn.ghost { color: #666; }
.panel-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 20px; border-top: 1px solid #f0f0f0; }
</style>
