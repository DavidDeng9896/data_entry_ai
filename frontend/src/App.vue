<template>
  <div class="page">
    <!-- 顶部栏 -->
    <header class="topbar">
      <div class="brand">
        <i class="ri-flask-line logo"></i>
        <span class="brand-name">数据录入 Agent</span>
        <span class="brand-sub">Data Entry Agent</span>
      </div>
      <div class="topbar-right">
        <button class="btn ghost" @click="showSettings = true"><i class="ri-settings-3-line"></i> 设置</button>
        <button class="btn primary" @click="showCreate = true"><i class="ri-add-line"></i> 新建结果表</button>
      </div>
    </header>

    <!-- 结果表列表 -->
    <main class="content">
      <div class="content-inner">
        <div class="page-head">
          <div>
            <div class="page-title">结果表</div>
            <div class="page-desc">选择一张结果表进入 AI 识别导入，表头可独立配置</div>
          </div>
          <span class="table-count" v-if="tables.length">{{ tables.length }} 张表</span>
        </div>
        <div v-if="toast" class="toast">{{ toast }}</div>

        <div class="cards" v-if="tables.length">
          <div class="card" v-for="t in tables" :key="t.id">
            <div class="card-top">
              <i class="ri-table-line card-icon"></i>
              <div class="card-info">
                <div class="card-title">{{ t.name }}</div>
                <div class="card-desc">{{ t.description || '—' }}</div>
              </div>
            </div>
            <div class="card-meta">
              <span class="meta-chip"><i class="ri-layout-column-line"></i> {{ t.column_count }} 列</span>
              <span class="meta-chip rows" v-if="Number(t.row_count) > 0">
                <i class="ri-database-2-line"></i> {{ t.row_count }} 行已入库
              </span>
            </div>
            <div class="card-actions">
              <button class="btn primary" @click="openImport(t)"><i class="ri-sparkling-2-line"></i> AI 导入</button>
              <button class="btn ghost" @click="openData(t)" title="查看已导入数据"><i class="ri-table-line"></i> 数据</button>
              <button class="btn ghost" @click="openColumns(t)" title="表头设置"><i class="ri-settings-3-line"></i> 表头</button>
              <button class="btn ghost icon-only" @click="renameTable(t)" title="重命名"><i class="ri-edit-line"></i></button>
              <button class="btn ghost icon-only" @click="copyTable(t)" title="复制建新表"><i class="ri-file-copy-line"></i></button>
              <button class="btn ghost icon-only danger" @click="deleteTable(t)" title="删除"><i class="ri-delete-bin-line"></i></button>
            </div>
          </div>
        </div>

        <div class="empty-state" v-else>
          <i class="ri-inbox-line"></i>
          <div class="empty-title">还没有结果表</div>
          <div class="empty-desc">点击右上角「新建结果表」创建，如 Dog PK、Monkey PK、Thermodynamic Solubility 等</div>
          <button class="btn primary" @click="showCreate = true"><i class="ri-add-line"></i> 新建结果表</button>
        </div>
      </div>
    </main>

    <!-- 新建结果表弹窗 -->
    <TableCreateDialog v-if="showCreate" @close="showCreate = false" @created="onTableCreated" />

    <!-- 导入弹窗 -->
    <ImportDialog
      v-if="showImport && activeTable"
      :table-id="activeTable.id"
      :table-name="activeTable.name"
      @close="showImport = false"
      @imported="onImported"
    />

    <!-- 表头设置弹窗 -->
    <ColumnSettings
      v-if="showColumns && activeTable"
      :table-id="activeTable.id"
      @close="showColumns = false"
      @saved="onColumnsSaved"
    />

    <!-- 设置弹窗 -->
    <SettingsDialog v-if="showSettings" @close="showSettings = false" />

    <TableDataDialog
      v-if="showData && activeTable"
      :table-id="activeTable.id"
      :table-name="activeTable.name"
      @close="showData = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from './api'
import ImportDialog from './components/ImportDialog.vue'
import ColumnSettings from './components/ColumnSettings.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import TableCreateDialog from './components/TableCreateDialog.vue'
import TableDataDialog from './components/TableDataDialog.vue'

const tables = ref([])
const showCreate = ref(false)
const showImport = ref(false)
const showColumns = ref(false)
const showSettings = ref(false)
const showData = ref(false)
const activeTable = ref(null)
const toast = ref('')

onMounted(loadTables)

async function loadTables() {
  tables.value = await api.listTables()
}

function openImport(t) {
  activeTable.value = t
  showImport.value = true
}

function openColumns(t) {
  activeTable.value = t
  showColumns.value = true
}

async function onTableCreated() {
  await loadTables()
}

async function onColumnsSaved() {
  showColumns.value = false
  await loadTables()
  // 表头保存后重开导入弹窗（重新拉列）
  if (activeTable.value) {
    showImport.value = false
    setTimeout(() => { showImport.value = true }, 50)
  }
}

function openData(t) {
  activeTable.value = t
  showData.value = true
}

async function onImported(payload) {
  await loadTables()
  const n = payload?.row_count ?? payload?.rows?.length ?? 0
  toast.value = `已写入 ${n} 行，可在卡片上点「数据」回看`
  setTimeout(() => { toast.value = '' }, 4000)
}

async function renameTable(t) {
  const name = prompt('新的表名称：', t.name)
  if (!name || name.trim() === t.name) return
  const description = prompt('表描述（可留空）：', t.description || '')
  try {
    await api.updateTable(t.id, { name: name.trim(), description })
    await loadTables()
    if (activeTable.value?.id === t.id) activeTable.value = tables.value.find(x => x.id === t.id)
  } catch (e) {
    alert(e.message)
  }
}

async function copyTable(t) {
  const name = prompt(`复制「${t.name}」的列配置，新表名称：`)
  if (!name || !name.trim()) return
  try {
    await api.copyTable(t.id, name.trim())
    await loadTables()
  } catch (e) {
    alert(e.message)
  }
}

async function deleteTable(t) {
  if (!confirm(`删除结果表「${t.name}」？其列配置将一并删除。`)) return
  await api.deleteTable(t.id)
  if (activeTable.value?.id === t.id) {
    activeTable.value = null
    showImport.value = false
    showColumns.value = false
  }
  await loadTables()
}
</script>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; background: #fff; }
.topbar { height: 52px; background: #fff; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; }
.brand { display: flex; align-items: center; gap: 10px; }
.logo { color: #2468DB; font-size: 22px; }
.brand-name { font-size: 15px; font-weight: 600; color: #1a1a1a; }
.brand-sub { color: #b3b3b3; font-size: 12px; }
.topbar-right { display: flex; gap: 8px; }

.content { flex: 1; padding: 24px; overflow: auto; }
.content-inner { max-width: 1080px; margin: 0 auto; }

.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.page-title { font-size: 18px; font-weight: 600; color: #1a1a1a; }
.page-desc { color: #999; font-size: 13px; margin-top: 4px; }
.table-count { color: #999; font-size: 13px; }

/* 卡片列表 */
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card { border: 1px solid #f0f0f0; border-radius: 8px; padding: 18px; transition: border-color 0.12s; background: #fff; }
.card:hover { border-color: #c5d8f7; }
.card-top { display: flex; gap: 12px; align-items: flex-start; }
.card-icon { font-size: 22px; color: #2468DB; background: #eef4fd; border-radius: 6px; padding: 8px; }
.card-info { flex: 1; min-width: 0; }
.card-title { font-size: 15px; font-weight: 600; color: #1a1a1a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-desc { color: #999; font-size: 12px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-meta { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.meta-chip { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #888; background: #fafafa; border-radius: 4px; padding: 3px 8px; }
.meta-chip .ri { font-size: 13px; color: #2468DB; }
.meta-chip.rows { color: #1d5bc4; background: #eef4fd; font-weight: 600; }
.card-actions { display: flex; gap: 6px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #f5f5f5; }
.card-actions .btn.primary { flex: 1; justify-content: center; }

/* 空状态 */
.empty-state { text-align: center; padding: 80px 0; color: #bbb; }
.empty-state .ri-inbox-line { font-size: 48px; }
.empty-title { font-size: 15px; color: #888; margin-top: 12px; }
.empty-desc { font-size: 13px; color: #bbb; margin: 6px 0 18px; }

.toast {
  margin-bottom: 12px; background: #f6ffed; color: #389e0d;
  border-radius: 4px; padding: 8px 12px; font-size: 13px;
}

.btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #e5e5e5; background: #fff; border-radius: 4px; padding: 5px 12px; font-size: 13px; color: #4a4a4a; transition: all 0.12s; }
.btn:hover { border-color: #c9c9c9; }
.btn .ri { font-size: 15px; }
.btn.primary { background: #2468DB; border-color: #2468DB; color: #fff; }
.btn.primary:hover { background: #1d5bc4; }
.btn.ghost { color: #666; }
.btn.icon-only { padding: 5px 8px; }
.btn.icon-only.danger:hover { color: #e02b2b; border-color: #ffc5c2; }
</style>
