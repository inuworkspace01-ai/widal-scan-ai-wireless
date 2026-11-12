create table if not exists private.bootstrap_settings (
  setting_key text primary key,
  token_hash text not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);
revoke all on private.bootstrap_settings from public, anon, authenticated;

insert into private.bootstrap_settings(setting_key, token_hash)
values (
  'initial_account_setup',
  'eefd7e5a4b64e4e5068fb63be0642ec77fe16c60fd39548800e24c64f5d4cb0f'
)
on conflict (setting_key) do update
set token_hash = excluded.token_hash, used_at = null;

create or replace function public.validate_bootstrap_token(p_token_hash text)
returns boolean
language sql
security definer
set search_path = ''
as $$
  select exists(
    select 1
    from private.bootstrap_settings
    where setting_key = 'initial_account_setup'
      and token_hash = p_token_hash
      and used_at is null
  );
$$;

create or replace function public.consume_bootstrap_token(p_token_hash text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  affected integer;
begin
  update private.bootstrap_settings
  set used_at = now()
  where setting_key = 'initial_account_setup'
    and token_hash = p_token_hash
    and used_at is null;
  get diagnostics affected = row_count;
  return affected = 1;
end;
$$;

revoke all on function public.validate_bootstrap_token(text) from public, anon, authenticated;
revoke all on function public.consume_bootstrap_token(text) from public, anon, authenticated;
grant execute on function public.validate_bootstrap_token(text) to service_role;
grant execute on function public.consume_bootstrap_token(text) to service_role;
