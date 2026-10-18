import { beforeEach, describe, expect, it } from 'vitest'
import { applyTheme, readTheme, storedTheme } from './theme'

describe('readTheme', () => {
  it('keeps a stored day or night choice', () => {
    expect(readTheme('day')).toBe('day')
    expect(readTheme('night')).toBe('night')
  })

  it('rejects an unknown stored value', () => {
    expect(readTheme('disco')).toBe('day')
  })

  it('uses day when nothing is stored', () => {
    expect(readTheme(null)).toBe('day')
    expect(readTheme('')).toBe('day')
  })
})

describe('applyTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    delete document.documentElement.dataset.theme
  })

  it('stores the choice and paints it on the page', () => {
    applyTheme('night')
    expect(document.documentElement.dataset.theme).toBe('night')
    expect(localStorage.getItem('papertrail-theme')).toBe('night')
    expect(storedTheme()).toBe('night')
  })

  it('can return to day after night', () => {
    applyTheme('night')
    applyTheme('day')
    expect(document.documentElement.dataset.theme).toBe('day')
    expect(storedTheme()).toBe('day')
  })
})
