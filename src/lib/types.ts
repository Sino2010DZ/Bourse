export interface Quote {
  symbol: string
  price: number
  changePct: number
  prevClose: number | null
  time: number
}

export interface Position {
  id: string
  symbol: string
  quantity: number
  buy_price: number
  currency: string
  bought_at: string | null
}

export type AlertDirection = 'above' | 'below'

export interface PriceAlert {
  id: string
  symbol: string
  direction: AlertDirection
  target: number
  active: boolean
  triggered_at: string | null
  triggered_price: number | null
}
