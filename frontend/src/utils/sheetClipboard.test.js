import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseClipboardText,
  isRowFilled,
  filledRows,
  isNumericLike,
  applyPasteGrid,
  validateRowCells
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

describe('validateRowCells', () => {
  const cols = [
    { field: 'id', title: 'ID', type: 'text', required: true },
    { field: 'val', title: 'Val', type: 'number', required: false }
  ]
  it('skips completely empty rows', () => {
    assert.equal(validateRowCells({ id: '', val: '' }, 0, cols).size, 0)
  })
  it('flags only missing required on partial rows', () => {
    const errs = validateRowCells({ id: '', val: '1.2' }, 1, cols)
    assert.equal(errs.size, 1)
    assert.equal(errs.get('1::id'), 'ID 必填')
  })
  it('does not flag empty optional number cells', () => {
    const errs = validateRowCells({ id: 'A1', val: '' }, 0, cols)
    assert.equal(errs.size, 0)
  })
  it('flags bad number only when cell has content', () => {
    const errs = validateRowCells({ id: 'A1', val: 'abc' }, 0, cols)
    assert.equal(errs.size, 1)
    assert.equal(errs.get('0::val'), '必须为数字')
  })
})
