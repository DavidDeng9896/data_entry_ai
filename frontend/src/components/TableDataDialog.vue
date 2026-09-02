<template>
  <div class="dialog-mask" @click.self="$emit('close')">
    <div class="panel">
      <div class="panel-header">
        <span class="title">已导入数据 · {{ tableName }}</span>
        <span class="close-btn" @click="$emit('close')"><i class="ri-close-line"></i></span>
      </div>
      <div class="panel-body">
        <div v-if="error" class="err">{{ error }}</div>
        <div class="batches" v-if="batches.length">
          <div class="batch" v-for="b in batches" :key="b.batch_id">
            <span>{{ formatTime(b.created_at) }}</span>
            <span>{{ b.row_count }} 行</span>
            <span v-if="b.skill_name">{{ b.skill_name }}</span>
            <span v-if="(b.source_files || []).length">{{ (b.source_files || []).join('、') }}</span>
          </div>
        </div>
        <div class="table-wrap" v-if="columns.length">
          <vxe-table border="full" height="420" :data="tableData" show-overflow="title">
            <vxe-column type="seq" title="#" width="50"></vxe-column>
            <vxe-column
              v-for="col in columns"
              :key="col.field"
              :field="col.field"
              :title="col.title"
              min-width="120"
            />
          </vxe-table>
        </div>
        <div v-else-if="!error" class="muted">还没有导入记录。请先 AI 导入并点「确认导入」。</div>
      </div>
      <div class="panel-footer">
        <button class="btn" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const props = defineProps({
  tableId: { type: Number, required: true },
  tableName: { type: String, default: '' }
})
defineEmits(['close'])

const columns = ref([])
const tableData = ref([])
const batches = ref([])
const error = ref('')

onMounted(load)

async function load() {
  try {
    columns.value = await api.getColumns(props.tableId)
    batches.value = await api.listImports(props.tableId)
    const rows = await api.listTableRows(props.tableId)
    tableData.value = rows.map(r => r.data || {})
  } catch (e) {
    error.value = e.message
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleString()
}
</script>

<style scoped>
.dialog-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.12);
  display: flex; align-items: center; justify-content: center; z-index: 100; padding: 16px;
}
.panel {
  width: min(1080px, 96vw); background: #fff; border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.08); display: flex; flex-direction: column; max-height: 92vh;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid #f0f0f0;
}
.title { font-weight: 600; }
.close-btn { cursor: pointer; color: #888; }
.panel-body { padding: 14px 18px; overflow: auto; }
.panel-footer { padding: 12px 18px; border-top: 1px solid #f0f0f0; display: flex; justify-content: flex-end; }
.batches { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.batch { font-size: 12px; color: #666; display: flex; gap: 12px; flex-wrap: wrap; }
.table-wrap { min-height: 240px; }
.muted { color: #999; font-size: 13px; padding: 24px 0; }
.err { color: #cf1322; margin-bottom: 8px; }
.btn { border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; }
</style>
