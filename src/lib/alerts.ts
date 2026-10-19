import type { AlertDirection } from './types'

export function shouldTrigger(direction: AlertDirection, target: number, price: number): boolean {
  return direction === 'above' ? price >= target : price <= target
}
