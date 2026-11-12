-- Username aliases support ID-based login in the web dashboard.
-- Actual authentication remains Supabase Auth (email/password); passwords are
-- never stored in public.profiles or source control.

alter table public.profiles
  add column if not exists username text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'profiles_username_format'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_username_format
      check (username is null or username ~ '^[a-z][a-z0-9_]{2,19}$');
  end if;
end
$$;

create unique index if not exists profiles_username_lower_unique
  on public.profiles (lower(username))
  where username is not null;

comment on column public.profiles.username is
  'Login ID shown in the application; password is managed by Supabase Auth.';
