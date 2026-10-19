import { beforeAll, describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { PGlite } from '@electric-sql/pglite'

// Vérifie le script SQL et les règles de sécurité (RLS) dans un vrai PostgreSQL
// en mémoire, avec une imitation minimale de l'environnement Supabase.
const SUPABASE_STUB = `
  create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
  create schema auth;
  create table auth.users (id uuid primary key, raw_user_meta_data jsonb default '{}');
  create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  grant usage on schema auth to anon, authenticated, service_role;
  grant usage on schema public to anon, authenticated, service_role;
`
const GRANTS = `
  grant select, insert, update, delete on all tables in schema public to anon, authenticated, service_role;
`
const A = '00000000-0000-0000-0000-00000000000a'
const B = '00000000-0000-0000-0000-00000000000b'

let db: PGlite

async function as(user: string | null, sql: string, params: unknown[] = []) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${user ?? ''}', false); set role ${user ? 'authenticated' : 'anon'};`)
  try {
    return await db.query(sql, params)
  } finally {
    await db.exec('reset role;')
  }
}

describe('base de données', () => {
  beforeAll(async () => {
    db = new PGlite()
    await db.exec(SUPABASE_STUB)
    await db.exec(readFileSync('supabase/migrations/001_init.sql', 'utf8'))
    // Le script doit pouvoir être relancé sans erreur.
    await db.exec(readFileSync('supabase/migrations/001_init.sql', 'utf8'))
    await db.exec(GRANTS)
    await db.exec(`insert into auth.users (id, raw_user_meta_data) values ('${A}', '{"locale":"en"}'), ('${B}', '{}')`)
  })

  it('par défaut, tout est gratuit : pas de limite, portefeuille et alertes ouverts', async () => {
    const C = '00000000-0000-0000-0000-00000000000c'
    await db.query(`insert into auth.users (id) values ($1)`, [C])
    for (let i = 0; i < 7; i++) await as(C, `insert into watchlist_items (symbol) values ($1)`, [`SIX:T${i}`])
    await as(C, `insert into positions (symbol, quantity, buy_price) values ('SIX:NESN', 1, 80)`)
    await as(C, `insert into price_alerts (symbol, direction, target) values ('SIX:NESN', 'above', 100)`)
    expect((await as(C, `select count(*)::int as n from watchlist_items`)).rows[0]).toEqual({ n: 7 })
    // On passe en mode Premium payant pour vérifier les règles des deux plans.
    await db.query(`update app_settings set all_features_free = false`)
  })

  it('personne ne peut changer l’interrupteur depuis le navigateur', async () => {
    await as(A, `update app_settings set all_features_free = true`)
    expect((await db.query<{ f: boolean }>(`select all_features_free as f from app_settings`)).rows[0].f).toBe(false)
  })

  it('crée un profil gratuit à l’inscription', async () => {
    const { rows } = await db.query<{ plan: string; locale: string }>(`select plan, locale from profiles where id = $1`, [A])
    expect(rows[0]).toEqual({ plan: 'free', locale: 'en' })
  })

  it('plan gratuit : 5 valeurs maximum dans la watchlist', async () => {
    for (const s of ['SIX:NESN', 'SIX:ROG', 'SIX:NOVN', 'NASDAQ:AAPL', 'NASDAQ:MSFT']) {
      await as(A, `insert into watchlist_items (symbol) values ($1)`, [s])
    }
    await expect(as(A, `insert into watchlist_items (symbol) values ('NASDAQ:NVDA')`)).rejects.toThrow(/row-level security/)
  })

  it('chacun ne voit que ses propres données', async () => {
    const { rows } = await as(B, `select * from watchlist_items`)
    expect(rows).toHaveLength(0)
    await expect(as(B, `insert into watchlist_items (user_id, symbol) values ($1, 'SIX:UBSG')`, [A])).rejects.toThrow()
  })

  it('un visiteur non connecté ne voit rien', async () => {
    const { rows } = await as(null, `select * from watchlist_items`)
    expect(rows).toHaveLength(0)
  })

  it('portefeuille et alertes réservés au Premium', async () => {
    await expect(as(B, `insert into positions (symbol, quantity, buy_price) values ('SIX:NESN', 1, 80)`)).rejects.toThrow(/row-level security/)
    await expect(as(B, `insert into price_alerts (symbol, direction, target) values ('SIX:NESN', 'above', 100)`)).rejects.toThrow(/row-level security/)
  })

  it('personne ne peut se passer Premium tout seul', async () => {
    await as(B, `update profiles set plan = 'premium' where id = $1`, [B])
    const { rows } = await db.query<{ plan: string }>(`select plan from profiles where id = $1`, [B])
    expect(rows[0].plan).toBe('free')
  })

  it('Premium : watchlist illimitée, portefeuille et alertes', async () => {
    await db.query(`update profiles set plan = 'premium' where id = $1`, [A])
    await as(A, `insert into watchlist_items (symbol) values ('NASDAQ:NVDA')`)
    await as(A, `insert into positions (symbol, quantity, buy_price, currency) values ('SIX:NESN', 10, 80, 'CHF')`)
    await as(A, `insert into price_alerts (symbol, direction, target) values ('SIX:NESN', 'above', 100)`)
    const { rows } = await as(A, `select count(*)::int as n from price_alerts`)
    expect(rows[0]).toEqual({ n: 1 })
  })

  it('refuse une alerte créée « déjà déclenchée » et les valeurs absurdes', async () => {
    await expect(as(A, `insert into price_alerts (symbol, direction, target, active) values ('SIX:NESN', 'above', 100, false)`)).rejects.toThrow()
    await expect(as(A, `insert into positions (symbol, quantity, buy_price) values ('SIX:NESN', -1, 80)`)).rejects.toThrow()
    await expect(as(A, `insert into watchlist_items (symbol) values ('pas un symbole')`)).rejects.toThrow()
  })

  it('le cache des prix est invisible depuis le navigateur', async () => {
    await db.query(`insert into quote_cache (symbol, price, quote_time) values ('SIX:NESN', 90, now())`)
    expect((await as(A, `select * from quote_cache`)).rows).toHaveLength(0)
    await expect(as(A, `insert into quote_cache (symbol, price, quote_time) values ('X:Y', 1, now())`)).rejects.toThrow()
  })

  it('supprimer le compte efface toutes les données', async () => {
    await db.query(`delete from auth.users where id = $1`, [A])
    for (const t of ['profiles', 'watchlist_items', 'positions', 'price_alerts']) {
      const col = t === 'profiles' ? 'id' : 'user_id'
      const { rows } = await db.query<{ n: number }>(`select count(*)::int as n from ${t} where ${col} = $1`, [A])
      expect(rows[0].n, t).toBe(0)
    }
  })
})
