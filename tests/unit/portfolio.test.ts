import { describe, expect, it } from 'vitest'
import { computePortfolio } from '../../src/lib/portfolio'
import { shouldTrigger } from '../../src/lib/alerts'
import type { Position, Quote } from '../../src/lib/types'

const pos = (symbol: string, quantity: number, buy_price: number, currency: string): Position =>
  ({ id: symbol, symbol, quantity, buy_price, currency, bought_at: null })
const q = (symbol: string, price: number): Quote => ({ symbol, price, changePct: 0, prevClose: null, time: 0 })

describe('portefeuille', () => {
  it('calcule valeur, gain et pourcentage', () => {
    const { rows } = computePortfolio([pos('SIX:NESN', 10, 80, 'CHF')], { 'SIX:NESN': q('SIX:NESN', 90) })
    expect(rows[0]).toMatchObject({ cost: 800, value: 900, pnl: 100 })
    expect(rows[0].pnlPct).toBeCloseTo(12.5)
  })
  it('totalise par devise sans mélanger', () => {
    const { totals } = computePortfolio(
      [pos('SIX:NESN', 10, 80, 'CHF'), pos('SIX:ROG', 1, 300, 'CHF'), pos('NASDAQ:AAPL', 2, 100, 'USD')],
      { 'SIX:NESN': q('SIX:NESN', 90), 'SIX:ROG': q('SIX:ROG', 270), 'NASDAQ:AAPL': q('NASDAQ:AAPL', 150) },
    )
    const chf = totals.find((t) => t.currency === 'CHF')!
    expect(chf).toMatchObject({ cost: 1100, value: 1170, pnl: 70 })
    expect(totals.find((t) => t.currency === 'USD')).toMatchObject({ cost: 200, value: 300, pnl: 100 })
  })
  it('sans prix : valeur inconnue, coût connu', () => {
    const { rows, totals } = computePortfolio([pos('SIX:NESN', 10, 80, 'CHF')], {})
    expect(rows[0]).toMatchObject({ value: null, pnl: null, cost: 800 })
    expect(totals[0]).toMatchObject({ value: null, pnl: null, cost: 800 })
  })
  it('perte affichée en négatif', () => {
    const { rows } = computePortfolio([pos('A:B', 4, 50, 'EUR')], { 'A:B': q('A:B', 40) })
    expect(rows[0].pnl).toBe(-40)
    expect(rows[0].pnlPct).toBe(-20)
  })
})

describe('alertes', () => {
  it('au-dessus', () => {
    expect(shouldTrigger('above', 100, 100)).toBe(true)
    expect(shouldTrigger('above', 100, 99.99)).toBe(false)
  })
  it('en dessous', () => {
    expect(shouldTrigger('below', 100, 100)).toBe(true)
    expect(shouldTrigger('below', 100, 100.01)).toBe(false)
  })
})
