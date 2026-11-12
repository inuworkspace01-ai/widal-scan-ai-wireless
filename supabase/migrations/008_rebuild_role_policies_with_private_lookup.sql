-- Rebuild role-aware policies explicitly and preserve correct command scopes.
drop policy if exists "profiles_select_own_or_admin" on public.profiles;
create policy "profiles_select_own_or_admin"
on public.profiles for select to authenticated
using (user_id = (select auth.uid()) or private.current_app_role() = 'admin');

drop policy if exists "devices_select_authenticated" on public.devices;
create policy "devices_select_authenticated"
on public.devices for select to authenticated using (true);
drop policy if exists "devices_admin_all" on public.devices;
create policy "devices_admin_all"
on public.devices for all to authenticated
using (private.current_app_role() = 'admin')
with check (private.current_app_role() = 'admin');

drop policy if exists "examinations_insert_staff" on public.examinations;
create policy "examinations_insert_staff"
on public.examinations for insert to authenticated
with check (created_by = (select auth.uid()) and private.current_app_role() in ('admin','atlm'));
drop policy if exists "examinations_select_by_role_and_owner" on public.examinations;
create policy "examinations_select_by_role_and_owner"
on public.examinations for select to authenticated
using (created_by = (select auth.uid()) or private.current_app_role() in ('admin','reviewer'));
drop policy if exists "examinations_update_by_role_and_owner" on public.examinations;
create policy "examinations_update_by_role_and_owner"
on public.examinations for update to authenticated
using (
  private.current_app_role() in ('admin','reviewer')
  or (private.current_app_role() = 'atlm' and created_by = (select auth.uid()))
)
with check (
  private.current_app_role() in ('admin','reviewer')
  or (private.current_app_role() = 'atlm' and created_by = (select auth.uid()))
);

drop policy if exists "analysis_select_by_examination_owner" on public.analysis_runs;
create policy "analysis_select_by_examination_owner"
on public.analysis_runs for select to authenticated
using (
  exists (
    select 1 from public.examinations e
    where e.id = analysis_runs.examination_id
      and (e.created_by = (select auth.uid()) or private.current_app_role() in ('admin','reviewer'))
  )
);
drop policy if exists "analysis_insert_by_examination_owner" on public.analysis_runs;
create policy "analysis_insert_by_examination_owner"
on public.analysis_runs for insert to authenticated
with check (
  private.current_app_role() in ('admin','atlm','reviewer')
  and exists (
    select 1 from public.examinations e
    where e.id = analysis_runs.examination_id
      and (e.created_by = (select auth.uid()) or private.current_app_role() in ('admin','reviewer'))
  )
);

drop policy if exists "readings_select_by_examination_owner" on public.reaction_readings;
create policy "readings_select_by_examination_owner"
on public.reaction_readings for select to authenticated
using (
  exists (
    select 1 from public.examinations e
    where e.id = reaction_readings.examination_id
      and (e.created_by = (select auth.uid()) or private.current_app_role() in ('admin','reviewer'))
  )
);
drop policy if exists "readings_insert_by_examination_owner" on public.reaction_readings;
create policy "readings_insert_by_examination_owner"
on public.reaction_readings for insert to authenticated
with check (
  private.current_app_role() in ('admin','atlm','reviewer')
  and exists (
    select 1 from public.examinations e
    where e.id = reaction_readings.examination_id
      and (e.created_by = (select auth.uid()) or private.current_app_role() in ('admin','reviewer'))
  )
);
drop policy if exists "readings_update_by_examination_owner" on public.reaction_readings;
create policy "readings_update_by_examination_owner"
on public.reaction_readings for update to authenticated
using (
  private.current_app_role() in ('admin','reviewer')
  or exists (
    select 1 from public.examinations e
    where e.id = reaction_readings.examination_id
      and e.created_by = (select auth.uid())
      and private.current_app_role() = 'atlm'
  )
)
with check (
  private.current_app_role() in ('admin','reviewer')
  or exists (
    select 1 from public.examinations e
    where e.id = reaction_readings.examination_id
      and e.created_by = (select auth.uid())
      and private.current_app_role() = 'atlm'
  )
);

drop policy if exists "audit_admin_read" on public.audit_logs;
create policy "audit_admin_read"
on public.audit_logs for select to authenticated
using (private.current_app_role() = 'admin');

drop policy if exists "dataset_versions_admin_read" on public.dataset_versions;
create policy "dataset_versions_admin_read"
on public.dataset_versions for select to authenticated
using (private.current_app_role() = 'admin');
drop policy if exists "dataset_versions_admin_write" on public.dataset_versions;
create policy "dataset_versions_admin_write"
on public.dataset_versions for all to authenticated
using (private.current_app_role() = 'admin')
with check (private.current_app_role() = 'admin');

drop policy if exists "training_runs_admin_read" on public.training_runs;
create policy "training_runs_admin_read"
on public.training_runs for select to authenticated
using (private.current_app_role() = 'admin');
drop policy if exists "training_runs_admin_write" on public.training_runs;
create policy "training_runs_admin_write"
on public.training_runs for all to authenticated
using (private.current_app_role() = 'admin')
with check (private.current_app_role() = 'admin');

drop policy if exists "model_registry_authenticated_read" on public.model_registry;
create policy "model_registry_authenticated_read"
on public.model_registry for select to authenticated using (true);
drop policy if exists "model_registry_admin_write" on public.model_registry;
create policy "model_registry_admin_write"
on public.model_registry for all to authenticated
using (private.current_app_role() = 'admin')
with check (private.current_app_role() = 'admin');

drop policy if exists "training_feedback_owner_or_admin_read" on public.training_feedback;
create policy "training_feedback_owner_or_admin_read"
on public.training_feedback for select to authenticated
using (reviewer_id = (select auth.uid()) or private.current_app_role() = 'admin');
drop policy if exists "training_feedback_reviewer_insert" on public.training_feedback;
create policy "training_feedback_reviewer_insert"
on public.training_feedback for insert to authenticated
with check (reviewer_id = (select auth.uid()) and private.current_app_role() in ('admin','reviewer','atlm'));

revoke all on function public.current_app_role() from public, anon, authenticated;
