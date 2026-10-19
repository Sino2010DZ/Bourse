import type { Position, Quote } from './types'

export interface PositionRow {
  position: Position
  price: number | null
  cost: number
  value: number | null
  pnl: number | null
  pnlPct: number | null
}

export interface CurrencyTotal {
  currency: string
  cost: number
  value: number | null
  pnl: number | null
  pnlPct: number | null
}

// Calcule valeur, gains et pertes. On ne mélange jamais deux devises :
// les totaux sont donnés devise par devise.
export function computePortfolio(positions: Position[], quotes: Record<string, Quote>) {
  const rows: PositionRow[] = positions.map((p) => {
    const price = quotes[p.symbol]?.price ?? null
    const cost = p.quantity * p.buy_price
    const value = price === null ? null : p.quantity * price
    const pnl = value === null ? null : value - cost
    return { position: p, price, cost, value, pnl, pnlPct: pnl === null || cost === 0 ? null : (pnl / cost) * 100 }
  })

  const byCurrency = new Map<string, CurrencyTotal>()
  for (const r of rows) {
    const t = byCurrency.get(r.position.currency) ?? { currency: r.position.currency, cost: 0, value: 0, pnl: 0, pnlPct: null }
    t.cost += r.cost
    // Si un seul prix manque, le total de la devise est inconnu.
    t.value = t.value === null || r.value === null ? null : t.value + r.value
    byCurrency.set(r.position.currency, t)
  }
  const totals = [...byCurrency.values()].map((t) => {
    const pnl = t.value === null ? null : t.value - t.cost
    return { ...t, pnl, pnlPct: pnl === null || t.cost === 0 ? null : (pnl / t.cost) * 100 }
  })
  return { rows, totals }
}
