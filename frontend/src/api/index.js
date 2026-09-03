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
  commitImport: (tableId, payload) => req(`/tables/${tableId}/imports`, { method: 'POST', body: JSON.stringify(payload) }),
  listImports: (tableId) => req(`/tables/${tableId}/imports`),
  listTableRows: (tableId) => req(`/tables/${tableId}/rows`),

  // 设置
  getSettings: () => req('/settings'),
  saveSettings: (s) => req('/settings', { method: 'PUT', body: JSON.stringify(s) }),
  testModel: (cfg) => req('/settings/test', { method: 'POST', body: JSON.stringify(cfg) }),

  // skill
  listSkills: () => req('/skills'),
  getSkill: (id) => req(`/skills/${id}`),
  saveSkill: (payload) => req('/skills', { method: 'POST', body: JSON.stringify(payload) }),
  mergeSkill: (payload) => req('/skills/merge', { method: 'POST', body: JSON.stringify(payload) }),
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
  chat: (payload, extra = {}) => req('/recognize/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
    ...extra,
  }),
  chatStream: async (payload, extra = {}) => {
    const res = await fetch(`${BASE}/recognize/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: extra.signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || data.message || `请求失败 ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let donePayload = null
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop()
      for (const block of parts) {
        if (!block.trim()) continue
        let event = 'message'
        const dataLines = []
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
        }
        if (!dataLines.length) continue
        let json
        try {
          json = JSON.parse(dataLines.join('\n'))
        } catch {
          continue
        }
        if (event === 'step' && extra.onStep) extra.onStep(json)
        if (event === 'ping' && extra.onPing) extra.onPing(json)
        if (event === 'error') throw new Error(json.message || '对话失败')
        if (event === 'done') donePayload = json
      }
    }
    if (!donePayload) throw new Error('流式响应未完成')
    return donePayload
  },

  schemaChat: (payload) => req('/tables/schema/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  schemaChatStream: async (payload, extra = {}) => {
    const res = await fetch(`${BASE}/tables/schema/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: extra.signal,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || data.message || `请求失败 ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let donePayload = null
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop()
      for (const block of parts) {
        if (!block.trim()) continue
        let event = 'message'
        const dataLines = []
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
        }
        if (!dataLines.length) continue
        let json
        try {
          json = JSON.parse(dataLines.join('\n'))
        } catch {
          continue
        }
        if (event === 'step' && extra.onStep) extra.onStep(json)
        if (event === 'ping' && extra.onPing) extra.onPing(json)
        if (event === 'error') throw new Error(json.message || '对话失败')
        if (event === 'done') donePayload = json
      }
    }
    if (!donePayload) throw new Error('流式响应未完成')
    return donePayload
  }
}
