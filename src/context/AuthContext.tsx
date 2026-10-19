import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { env, premiumModeActive, type Plan } from '../config'

interface AuthValue {
  configured: boolean
  ready: boolean
  user: User | null
  session: Session | null
  plan: Plan
  renewsAt: string | null
  hasBilling: boolean
  refreshPlan: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export const DEV_PREMIUM_KEY = 'tg.devPremium'

function guestPlan(): Plan {
  // Uniquement pour les tests locaux : jamais actif sur le site en ligne.
  try {
    return env.testHooks && localStorage.getItem(DEV_PREMIUM_KEY) === '1' ? 'premium' : 'free'
  } catch {
    return 'free'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!supabase)
  const [plan, setPlan] = useState<Plan>(guestPlan)
  const [renewsAt, setRenewsAt] = useState<string | null>(null)
  const [hasBilling, setHasBilling] = useState(false)

  const user = session?.user ?? null

  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setReady(true)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [])

  const refreshPlan = async () => {
    if (!supabase || !user) {
      setPlan(guestPlan())
      setRenewsAt(null)
      setHasBilling(false)
      return
    }
    const { data } = await supabase.from('profiles').select('plan,plan_renews_at,stripe_customer_id').eq('id', user.id).maybeSingle()
    setPlan(data?.plan === 'premium' ? 'premium' : 'free')
    setRenewsAt((data?.plan_renews_at as string | null) ?? null)
    setHasBilling(!!data?.stripe_customer_id)
  }

  useEffect(() => {
    void refreshPlan()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id])

  const value = useMemo<AuthValue>(() => ({
    configured: !!supabase,
    ready,
    user,
    session,
    // Tout gratuit : chacun a accès à toutes les fonctions.
    plan: premiumModeActive() ? plan : 'premium',
    renewsAt,
    hasBilling,
    refreshPlan,
    signOut: async () => { await supabase?.auth.signOut() },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [ready, user, session, plan, renewsAt, hasBilling])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans <AuthProvider>')
  return ctx
}
