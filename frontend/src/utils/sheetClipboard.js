/** Excel / 表格剪贴板与空行判定（开源 vxe-table 无 clip/area 插件时自用） */

export function parseClipboardText(text) {
  if (text == null) return []
  let s = String(text).replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (s.endsWith('\n')) s = s.slice(0, -1)
  if (s === '') return [['']]
  return s.split('\n').map((line) => line.split('\t'))
}

export function isRowFilled(row, columns) {
  if (!row || !columns?.length) return false
  return columns.some((c) => {
    const v = row[c.field]
    return v !== '' && v != null
  })
}

export function filledRows(data, columns) {
  return (data || []).filter((row) => isRowFilled(row, columns))
}

/** 实验数据常见写法：空、纯数字、不等式、NA 等视为可接受的“数字格” */
export function isNumericLike(value) {
  if (value === '' || value == null) return true
  const s = String(value).trim()
  if (!s) return true
  if (/^(na|n\/a|nd|blq|n\.d\.|-|\/|—)$/i.test(s)) return true
  if (/^[<>]=?\s*[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(s)) return true
  const n = Number(s)
  return Number.isFinite(n)
}

export function applyPasteGrid({ data, fields, startRowIndex, startColIndex, grid, makeEmptyRow }) {
  if (!grid.length) return { added: 0 }
  let added = 0
  const colCount = fields.length
  const startCol = Math.max(0, startColIndex)
  for (let r = 0; r < grid.length; r++) {
    const ri = startRowIndex + r
    while (data.length <= ri) {
      data.push(makeEmptyRow())
      added++
    }
    const cells = grid[r] || []
    for (let c = 0; c < cells.length; c++) {
      const fi = startCol + c
      if (fi >= colCount) break
      data[ri][fields[fi]] = cells[c]
    }
  }
  return { added }
}

function cellKey(rowIndex, field) {
  return `${rowIndex}::${field}`
}

function isCellEmpty(value) {
  return value === '' || value == null || (typeof value === 'string' && !value.trim())
}

/** 只校验「至少填过一格」的行；空行跳过；有内容的格才做类型校验 */
export function validateRowCells(row, rowIndex, columns) {
  const errors = new Map()
  if (!isRowFilled(row, columns)) return errors
  for (const c of columns) {
    const v = row[c.field]
    const empty = isCellEmpty(v)
    if (c.required && empty) {
      errors.set(cellKey(rowIndex, c.field), `${c.title} 必填`)
    } else if (!empty && c.type === 'number' && !isNumericLike(v)) {
      errors.set(cellKey(rowIndex, c.field), '必须为数字')
    } else if (!empty && c.type === 'select' && c.options?.length && !c.options.includes(String(v))) {
      errors.set(cellKey(rowIndex, c.field), '存在内容与选项不匹配')
    }
  }
  return errors
}

export function validateTable(data, columns) {
  const errors = new Map()
  ;(data || []).forEach((row, rowIndex) => {
    validateRowCells(row, rowIndex, columns).forEach((msg, key) => errors.set(key, msg))
  })
  return errors
}

export function parseCellKey(key) {
  const i = key.indexOf('::')
  if (i < 0) return { rowIndex: -1, field: '' }
  return { rowIndex: Number(key.slice(0, i)), field: key.slice(i + 2) }
}
