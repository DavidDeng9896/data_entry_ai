const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: options.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...options
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || data.message || `请求失败 ${res.status}`)
  return data
}

export const api = {
  // 结果表管理
  listTables: () => req('/tables'),
  getTable: (id) => req(`/tables/${id}`),
  createTable: (name, description, columns) => req('/tables', { method: 'POST', body: JSON.stringify({ name, description, columns }) }),
  updateTable: (id, payload) => req(`/tables/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTable: (id) => req(`/tables/${id}`, { method: 'DELETE' }),
  copyTable: (id, name) => req(`/tables/${id}/copy`, { method: 'POST', body: JSON.stringify({ name }) }),
  getColumns: (tableId) => req(`/tables/${tableId}/columns`),
  saveColumns: (tableId, columns) => req(`/tables/${tableId}/columns`, { method: 'PUT', body: JSON.stringify({ columns }) }),

  // 设置
  getSettings: () => req('/settings'),
  saveSettings: (s) => req('/settings', { method: 'PUT', body: JSON.stringify(s) }),
  testModel: (cfg) => req('/settings/test', { method: 'POST', body: JSON.stringify(cfg) }),

  // skill
  listSkills: () => req('/skills'),
  getSkill: (id) => req(`/skills/${id}`),
  saveSkill: (payload) => req('/skills', { method: 'POST', body: JSON.stringify(payload) }),
  deleteSkill: (id) => req(`/skills/${id}`, { method: 'DELETE' }),
  enableSkill: (id) => req('/skills/enable', { method: 'POST', body: JSON.stringify({ id: id ?? null }) }),
  importSkillMd: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('/skills/import-md', { method: 'POST', body: fd })
  },
  exportSkillMdUrl: (id) => `${BASE}/skills/${id}/export-md`,

  // 识别
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('/recognize/upload', { method: 'POST', body: fd })
  },
  recognize: (payload) => req('/recognize/run', { method: 'POST', body: JSON.stringify(payload) }),
  chat: (payload) => req('/recognize/chat', { method: 'POST', body: JSON.stringify(payload) })
}
