import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { supabase } from '../lib/supabase'
import { readJson, writeJson } from '../lib/storage'
import { PLAN_LIMITS } from '../config'
import type { AlertDirection, Position, PriceAlert } from '../lib/types'

// Toutes les données personnelles passent par ici.
// Invité : stockage local de l'appareil. Connecté : base Supabase.

export type AddResult = 'ok' | 'exists' | 'limit' | 'forbidden' | 'error'

interface DataValue {
  loading: boolean
  watchlist: string[]
  watchLimit: number
  addWatch: (symbol: string) => Promise<AddResult>
  removeWatch: (symbol: string) => Promise<void>
  positions: Position[]
  addPosition: (p: Omit<Position, 'id'>) => Promise<AddResult>
  removePosition: (id: string) => Promise<void>
  alerts: PriceAlert[]
  addAlert: (a: { symbol: string; direction: AlertDirection; target: number }) => Promise<AddResult>
  removeAlert: (id: string) => Promise<void>
}

const DataContext = createContext<DataValue | null>(null)

const GUEST = { watch: 'tg.guest.watchlist', positions: 'tg.guest.positions', alerts: 'tg.guest.alerts' }

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()))

export function DataProvider({ children }: { children: ReactNode }) {
  const { user, plan, ready } = useAuth()
  const limits = PLAN_LIMITS[plan]
  const [loading, setLoading] = useState(true)
  const [watchlist, setWatchlist] = useState<string[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [alerts, setAlerts] = useState<PriceAlert[]>([])

  const db = user && supabase ? supabase : null

  const load = useCallback(async () => {
    if (!ready) return
    setLoading(true)
    if (!db || !user) {
      setWatchlist(readJson<string[]>(GUEST.watch, []))
      setPositions(readJson<Position[]>(GUEST.positions, []))
      setAlerts(readJson<PriceAlert[]>(GUEST.alerts, []))
      setLoading(false)
      return
    }
    const [w, p, a] = await Promise.all([
      db.from('watchlist_items').select('symbol').order('position').order('created_at'),
      db.from('positions').select('id,symbol,quantity,buy_price,currency,bought_at').order('created_at'),
      db.from('price_alerts').select('id,symbol,direction,target,active,triggered_at,triggered_price').order('created_at', { ascending: false }),
    ])
    let list = (w.data ?? []).map((r) => r.symbol as string)

    // Première connexion : on reprend la watchlist créée en invité.
    const guest = readJson<string[]>(GUEST.watch, [])
    if (!list.length && guest.length) {
      const toImport = guest.slice(0, PLAN_LIMITS.free.watchlist)
      const { error } = await db.from('watchlist_items').insert(toImport.map((symbol, i) => ({ symbol, position: i })))
      if (!error) {
        list = toImport
        writeJson(GUEST.watch, [])
      }
    }
    setWatchlist(list)
    setPositions((p.data ?? []).map((r) => ({ ...r, quantity: Number(r.quantity), buy_price: Number(r.buy_price) })) as Position[])
    setAlerts((a.data ?? []).map((r) => ({ ...r, target: Number(r.target) })) as PriceAlert[])
    setLoading(false)
  }, [db, user, ready])

  useEffect(() => { void load() }, [load])

  const value = useMemo<DataValue>(() => {
    const saveGuest = (key: string, v: unknown) => writeJson(key, v)

    return {
      loading,
      watchlist,
      watchLimit: limits.watchlist,
      async addWatch(symbol) {
        if (watchlist.includes(symbol)) return 'exists'
        if (watchlist.length >= limits.watchlist) return 'limit'
        const next = [...watchlist, symbol]
        if (db) {
          const { error } = await db.from('watchlist_items').insert({ symbol, position: watchlist.length })
          if (error) return error.code === '42501' ? 'limit' : 'error'
        } else saveGuest(GUEST.watch, next)
        setWatchlist(next)
        return 'ok'
      },
      async removeWatch(symbol) {
        const next = watchlist.filter((s) => s !== symbol)
        if (db) await db.from('watchlist_items').delete().eq('symbol', symbol)
        else saveGuest(GUEST.watch, next)
        setWatchlist(next)
      },
      positions,
      async addPosition(p) {
        if (!limits.portfolio) return 'forbidden'
        if (db) {
          const { data, error } = await db.from('positions').insert(p).select('id').single()
          if (error || !data) return 'error'
          setPositions([...positions, { ...p, id: data.id as string }])
        } else {
          const next = [...positions, { ...p, id: uid() }]
          saveGuest(GUEST.positions, next)
          setPositions(next)
        }
        return 'ok'
      },
      async removePosition(id) {
        const next = positions.filter((p) => p.id !== id)
        if (db) await db.from('positions').delete().eq('id', id)
        else saveGuest(GUEST.positions, next)
        setPositions(next)
      },
      alerts,
      async addAlert(a) {
        if (!limits.alerts) return 'forbidden'
        if (db) {
          const { data, error } = await db.from('price_alerts').insert(a).select('id').single()
          if (error || !data) return 'error'
          setAlerts([{ ...a, id: data.id as string, active: true, triggered_at: null, triggered_price: null }, ...alerts])
        } else {
          const next = [{ ...a, id: uid(), active: true, triggered_at: null, triggered_price: null }, ...alerts]
          saveGuest(GUEST.alerts, next)
          setAlerts(next)
        }
        return 'ok'
      },
      async removeAlert(id) {
        const next = alerts.filter((a) => a.id !== id)
        if (db) await db.from('price_alerts').delete().eq('id', id)
        else saveGuest(GUEST.alerts, next)
        setAlerts(next)
      },
    }
  }, [loading, watchlist, positions, alerts, limits, db])

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useData() {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData doit être utilisé dans <DataProvider>')
  return ctx
}
