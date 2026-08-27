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
