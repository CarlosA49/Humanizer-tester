-- AI Humanizer — free account backend (Supabase).
-- Run this once in: Supabase project -> SQL editor -> New query -> Run.
-- Then: Authentication -> Providers -> Email = enabled.
--
-- Design: clients can only SELECT their own profile row. Every mutation
-- (trial counting, coupon redemption, device registration) goes through a
-- SECURITY DEFINER function, so a logged-in user cannot tamper with their
-- own word count, unlock flag, or device list from the browser.

create extension if not exists pgcrypto with schema extensions;

-- Private config (coupon secret). Never readable by clients; only the
-- SECURITY DEFINER functions (owned by postgres) can read it.
create table if not exists public.private_config (
  key text primary key,
  value text not null
);
revoke all on public.private_config from anon, authenticated;
-- Deny-all RLS (no policies). SECURITY DEFINER functions still read it.
alter table public.private_config enable row level security;

-- IMPORTANT: this MUST equal COUPON_SECRET in docs/config.js
insert into public.private_config (key, value)
values ('coupon_secret', 'hmz-launch-v1-mvp-rotate-with-backend')
on conflict (key) do update set value = excluded.value;

-- Per-user profile.
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  plan text,                                   -- null = trial only
  trial_words integer not null default 0,
  unlocked boolean not null default false,
  devices jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Read-only: a user may read ONLY their own row. No client writes at all.
drop policy if exists "read own profile" on public.profiles;
create policy "read own profile" on public.profiles
  for select using (auth.uid() = id);

-- Explicit grants so the Data API works whether or not "Automatically
-- expose new tables" is enabled. RLS still limits reads to the own row;
-- all writes go only through the SECURITY DEFINER functions below.
grant usage on schema public to anon, authenticated;
grant select on public.profiles to authenticated;

-- Auto-create the profile row on signup.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Tamper-resistant trial counter.
create or replace function public.consume_words(n integer)
returns public.profiles language plpgsql security definer
set search_path = public as $$
declare r public.profiles;
begin
  update public.profiles
     set trial_words = trial_words + greatest(0, n),
         updated_at = now()
   where id = auth.uid()
   returning * into r;
  return r;
end; $$;

-- Register / verify this device against the plan's device cap.
create or replace function public.register_device(device text, cap integer)
returns public.profiles language plpgsql security definer
set search_path = public as $$
declare r public.profiles;
begin
  select * into r from public.profiles where id = auth.uid();
  if not (r.devices ? device) then
    if jsonb_array_length(r.devices) >= greatest(1, cap) then
      raise exception 'device_limit_reached';
    end if;
    update public.profiles
       set devices = r.devices || to_jsonb(device), updated_at = now()
     where id = auth.uid()
     returning * into r;
  end if;
  return r;
end; $$;

-- Drop every other device, keep only this one.
create or replace function public.forget_other_devices(keep text)
returns public.profiles language plpgsql security definer
set search_path = public as $$
declare r public.profiles;
begin
  update public.profiles
     set devices = jsonb_build_array(keep), updated_at = now()
   where id = auth.uid()
   returning * into r;
  return r;
end; $$;

-- Server-side coupon redemption. Mirrors the client signing scheme:
-- code = PLAN-KIND-VALUE-EXP-SIG
-- SIG  = upper( substr( sha256_hex( secret|PLAN|KIND|VALUE|EXP ), 1, 8 ) )
create or replace function public.redeem_coupon(code text)
returns jsonb language plpgsql security definer
set search_path = public, extensions as $$
declare
  parts text[]; p text; k text; v text; e text; sig text;
  secret text; good text; planmap jsonb; mapped text; r public.profiles;
begin
  parts := string_to_array(upper(regexp_replace(coalesce(code,''), '\s', '', 'g')), '-');
  if coalesce(array_length(parts, 1), 0) <> 5 then
    return jsonb_build_object('ok', false, 'msg', 'Invalid code format.');
  end if;
  p := parts[1]; k := parts[2]; v := parts[3]; e := parts[4]; sig := parts[5];

  select value into secret from public.private_config where key = 'coupon_secret';
  good := upper(substr(
    encode(digest(secret || '|' || p || '|' || k || '|' || v || '|' || e, 'sha256'), 'hex'),
    1, 8));
  if good is distinct from sig then
    return jsonb_build_object('ok', false, 'msg', 'Invalid or tampered code.');
  end if;
  if e <> '0' and floor(extract(epoch from now()) / 86400)::int > e::int then
    return jsonb_build_object('ok', false, 'msg', 'This code has expired.');
  end if;

  planmap := '{"STARTER":"starter","PRO":"pro","SEMI":"semiannual",
               "UNLI":"unlimited","ANNUAL":"annual","LIFE":"lifetime",
               "ALL":"all"}'::jsonb;
  if not (planmap ? p) then
    return jsonb_build_object('ok', false, 'msg', 'Invalid plan.');
  end if;
  mapped := planmap ->> p;

  if k = 'FREE' then
    update public.profiles
       set unlocked = true, plan = mapped, updated_at = now()
     where id = auth.uid()
     returning * into r;
    return jsonb_build_object('ok', true, 'free', true, 'plan', mapped);
  elsif k in ('PCT', 'AMT') then
    -- discount validated; checkout/payment stays manual in this phase
    return jsonb_build_object('ok', true, 'free', false,
      'kind', k, 'value', v::int, 'plan', mapped);
  end if;
  return jsonb_build_object('ok', false, 'msg', 'Invalid code.');
end; $$;

grant execute on function public.consume_words(integer) to authenticated;
grant execute on function public.register_device(text, integer) to authenticated;
grant execute on function public.forget_other_devices(text) to authenticated;
grant execute on function public.redeem_coupon(text) to authenticated;
