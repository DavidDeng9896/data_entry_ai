import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseClipboardText,
  isRowFilled,
  filledRows,
  isNumericLike,
  applyPasteGrid
} from './sheetClipboard.js'

describe('parseClipboardText', () => {
  it('parses excel tsv block', () => {
    assert.deepEqual(parseClipboardText('A\tB\nC\tD\n'), [['A', 'B'], ['C', 'D']])
  })
  it('keeps a single cell', () => {
    assert.deepEqual(parseClipboardText('hello'), [['hello']])
  })
})

describe('isRowFilled / filledRows', () => {
  const cols = [{ field: 'a' }, { field: 'b' }]
  it('treats all-empty as empty', () => {
    assert.equal(isRowFilled({ a: '', b: '' }, cols), false)
    assert.equal(isRowFilled({ a: null, b: undefined }, cols), false)
  })
  it('filters filled rows only', () => {
    const data = [{ a: '', b: '' }, { a: 'x', b: '' }, { a: '', b: 0 }]
    assert.equal(filledRows(data, cols).length, 2)
  })
})

describe('isNumericLike', () => {
  it('accepts empty, number, inequality and NA', () => {
    assert.equal(isNumericLike(''), true)
    assert.equal(isNumericLike('1.2'), true)
    assert.equal(isNumericLike('<0.1'), true)
    assert.equal(isNumericLike('NA'), true)
    assert.equal(isNumericLike('abc'), false)
  })
})

describe('applyPasteGrid', () => {
  it('writes from anchor and appends rows', () => {
    const data = [{ a: '', b: '', c: '' }]
    const fields = ['a', 'b', 'c']
    const { added } = applyPasteGrid({
      data,
      fields,
      startRowIndex: 0,
      startColIndex: 1,
      grid: [['1', '2'], ['3', '4']],
      makeEmptyRow: () => ({ a: '', b: '', c: '' })
    })
    assert.equal(added, 1)
    assert.deepEqual(data, [
      { a: '', b: '1', c: '2' },
      { a: '', b: '3', c: '4' }
    ])
  })
})
