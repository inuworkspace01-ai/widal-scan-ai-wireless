-- Move the role lookup out of the exposed public API schema.
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create or replace function private.current_app_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select p.role
  from public.profiles as p
  where p.user_id = (select auth.uid())
    and p.is_active = true
$$;

revoke all on function private.current_app_role() from public, anon, authenticated;
grant execute on function private.current_app_role() to authenticated;

do $$
declare
  policy_row record;
begin
  for policy_row in
    select schemaname, tablename, policyname, qual, with_check
    from pg_policies
    where schemaname = 'public'
      and (
        coalesce(qual, '') like '%current_app_role%'
        or coalesce(with_check, '') like '%current_app_role%'
      )
  loop
    execute format('drop policy if exists %I on %I.%I',
      policy_row.policyname, policy_row.schemaname, policy_row.tablename);

    execute format(
      'create policy %I on %I.%I %s',
      policy_row.policyname,
      policy_row.schemaname,
      policy_row.tablename,
      case
        when policy_row.policyname like '%select%' then
          'for select to authenticated using (' ||
          replace(coalesce(policy_row.qual, 'true'), 'public.current_app_role()', 'private.current_app_role()') || ')'
        else
          'for ' ||
          case
            when policy_row.policyname like '%insert%' then 'insert'
            when policy_row.policyname like '%update%' then 'update'
            when policy_row.policyname like '%delete%' then 'delete'
            else 'all'
          end ||
          ' to authenticated ' ||
          case
            when policy_row.policyname like '%insert%' then ''
            else 'using (' || replace(coalesce(policy_row.qual, 'true'), 'public.current_app_role()', 'private.current_app_role()') || ') '
          end ||
          case
            when policy_row.with_check is not null then
              'with check (' || replace(policy_row.with_check, 'public.current_app_role()', 'private.current_app_role()') || ')'
            when policy_row.policyname like '%insert%' then
              'with check (' || replace(coalesce(policy_row.qual, 'true'), 'public.current_app_role()', 'private.current_app_role()') || ')'
            else ''
          end
      end
    );
  end loop;
end
$$;

revoke all on function public.current_app_role() from public, anon, authenticated;
