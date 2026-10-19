-- =====================================================================
-- Tickglass — structure de la base de données (Supabase / PostgreSQL)
-- À coller une seule fois dans Supabase : SQL Editor → New query → Run.
-- =====================================================================

-- ---------- Profils (plan Gratuit / Premium) ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'premium')),
  plan_renews_at timestamptz,
  stripe_customer_id text unique,
  stripe_subscription_id text,
  locale text not null default 'fr',
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;

-- Chacun lit son propre profil. Personne ne peut modifier son plan depuis le
-- navigateur : seul le serveur (clé service_role, ex. paiement Stripe) le peut.
drop policy if exists "profiles: lecture du sien" on public.profiles;
create policy "profiles: lecture du sien" on public.profiles
  for select to authenticated using (id = auth.uid());

-- Création automatique du profil à l'inscription.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, locale)
  values (new.id, coalesce(nullif(new.raw_user_meta_data ->> 'locale', ''), 'fr'))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users for each row execute function public.handle_new_user();

-- ---------- Interrupteur « tout gratuit » ----------
-- all_features_free = true : tout le monde a accès à tout (comme src/config.ts).
-- Pour vendre le Premium plus tard : Table Editor → app_settings → false.
create table if not exists public.app_settings (
  id boolean primary key default true check (id),
  all_features_free boolean not null default true
);
insert into public.app_settings (id) values (true) on conflict (id) do nothing;
alter table public.app_settings enable row level security;

create or replace function public.is_premium(uid uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select all_features_free from public.app_settings where id), false)
      or coalesce((select plan = 'premium' from public.profiles where id = uid), false)
$$;

-- ---------- Watchlist ----------
create table if not exists public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  symbol text not null check (symbol ~ '^[A-Z0-9_]{1,20}:[A-Z0-9._!-]{1,20}$'),
  position int not null default 0,
  created_at timestamptz not null default now(),
  unique (user_id, symbol)
);
create index if not exists watchlist_items_user_idx on public.watchlist_items (user_id);
alter table public.watchlist_items enable row level security;

create or replace function public.watchlist_count(uid uuid)
returns int language sql stable security definer set search_path = public as $$
  select count(*)::int from public.watchlist_items where user_id = uid
$$;

drop policy if exists "watchlist: lecture" on public.watchlist_items;
create policy "watchlist: lecture" on public.watchlist_items
  for select to authenticated using (user_id = auth.uid());

-- Plan gratuit : 5 valeurs maximum (même limite que src/config.ts).
drop policy if exists "watchlist: ajout" on public.watchlist_items;
create policy "watchlist: ajout" on public.watchlist_items
  for insert to authenticated
  with check (user_id = auth.uid() and (public.is_premium(auth.uid()) or public.watchlist_count(auth.uid()) < 5));

drop policy if exists "watchlist: modification" on public.watchlist_items;
create policy "watchlist: modification" on public.watchlist_items
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "watchlist: suppression" on public.watchlist_items;
create policy "watchlist: suppression" on public.watchlist_items
  for delete to authenticated using (user_id = auth.uid());

-- ---------- Portefeuille (Premium) ----------
create table if not exists public.positions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  symbol text not null check (symbol ~ '^[A-Z0-9_]{1,20}:[A-Z0-9._!-]{1,20}$'),
  quantity numeric not null check (quantity > 0),
  buy_price numeric not null check (buy_price >= 0),
  currency text not null default 'CHF' check (currency ~ '^[A-Z]{3}$'),
  bought_at date,
  created_at timestamptz not null default now()
);
create index if not exists positions_user_idx on public.positions (user_id);
alter table public.positions enable row level security;

drop policy if exists "positions: lecture" on public.positions;
create policy "positions: lecture" on public.positions
  for select to authenticated using (user_id = auth.uid());
drop policy if exists "positions: ajout premium" on public.positions;
create policy "positions: ajout premium" on public.positions
  for insert to authenticated with check (user_id = auth.uid() and public.is_premium(auth.uid()));
drop policy if exists "positions: modification premium" on public.positions;
create policy "positions: modification premium" on public.positions
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid() and public.is_premium(auth.uid()));
drop policy if exists "positions: suppression" on public.positions;
create policy "positions: suppression" on public.positions
  for delete to authenticated using (user_id = auth.uid());

-- ---------- Alertes de prix (Premium) ----------
create table if not exists public.price_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  symbol text not null check (symbol ~ '^[A-Z0-9_]{1,20}:[A-Z0-9._!-]{1,20}$'),
  direction text not null check (direction in ('above', 'below')),
  target numeric not null check (target > 0),
  active boolean not null default true,
  triggered_at timestamptz,
  triggered_price numeric,
  created_at timestamptz not null default now()
);
create index if not exists price_alerts_active_idx on public.price_alerts (active) where active;
alter table public.price_alerts enable row level security;

drop policy if exists "alertes: lecture" on public.price_alerts;
create policy "alertes: lecture" on public.price_alerts
  for select to authenticated using (user_id = auth.uid());
-- Un utilisateur ne peut créer que des alertes actives, jamais « déjà déclenchées ».
drop policy if exists "alertes: ajout premium" on public.price_alerts;
create policy "alertes: ajout premium" on public.price_alerts
  for insert to authenticated
  with check (user_id = auth.uid() and public.is_premium(auth.uid()) and active and triggered_at is null);
drop policy if exists "alertes: suppression" on public.price_alerts;
create policy "alertes: suppression" on public.price_alerts
  for delete to authenticated using (user_id = auth.uid());

-- ---------- Appareils inscrits aux notifications ----------
create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now()
);
alter table public.push_subscriptions enable row level security;

drop policy if exists "push: lecture" on public.push_subscriptions;
create policy "push: lecture" on public.push_subscriptions
  for select to authenticated using (user_id = auth.uid());
drop policy if exists "push: ajout" on public.push_subscriptions;
create policy "push: ajout" on public.push_subscriptions
  for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "push: suppression" on public.push_subscriptions;
create policy "push: suppression" on public.push_subscriptions
  for delete to authenticated using (user_id = auth.uid());

-- ---------- Cache des prix (serveur uniquement) ----------
-- RLS activé sans aucune règle : invisible depuis le navigateur,
-- accessible seulement aux fonctions serveur (service_role).
create table if not exists public.quote_cache (
  symbol text primary key,
  price numeric not null,
  change_pct numeric not null default 0,
  prev_close numeric,
  quote_time timestamptz not null,
  fetched_at timestamptz not null default now()
);
alter table public.quote_cache enable row level security;
