-- Tighten laboratory data isolation:
-- lab/ATLM users can only access examinations they created.
-- Admins and reviewers retain cross-user review access.

drop policy if exists "examinations_select_authenticated" on public.examinations;
drop policy if exists "examinations_update_reviewer" on public.examinations;
drop policy if exists "analysis_select_authenticated" on public.analysis_runs;
drop policy if exists "analysis_insert_staff" on public.analysis_runs;
drop policy if exists "readings_select_authenticated" on public.reaction_readings;
drop policy if exists "readings_insert_staff" on public.reaction_readings;
drop policy if exists "readings_update_staff" on public.reaction_readings;

create policy "examinations_select_by_role_and_owner"
on public.examinations
for select
to authenticated
using (
  created_by = auth.uid()
  or public.current_app_role() in ('admin', 'reviewer')
);

create policy "examinations_update_by_role_and_owner"
on public.examinations
for update
to authenticated
using (
  public.current_app_role() in ('admin', 'reviewer')
  or (
    public.current_app_role() = 'atlm'
    and created_by = auth.uid()
  )
)
with check (
  public.current_app_role() in ('admin', 'reviewer')
  or (
    public.current_app_role() = 'atlm'
    and created_by = auth.uid()
  )
);

create policy "analysis_select_by_examination_owner"
on public.analysis_runs
for select
to authenticated
using (
  exists (
    select 1
    from public.examinations e
    where e.id = analysis_runs.examination_id
      and (
        e.created_by = auth.uid()
        or public.current_app_role() in ('admin', 'reviewer')
      )
  )
);

create policy "analysis_insert_by_examination_owner"
on public.analysis_runs
for insert
to authenticated
with check (
  public.current_app_role() in ('admin', 'atlm', 'reviewer')
  and exists (
    select 1
    from public.examinations e
    where e.id = analysis_runs.examination_id
      and (
        e.created_by = auth.uid()
        or public.current_app_role() in ('admin', 'reviewer')
      )
  )
);

create policy "readings_select_by_examination_owner"
on public.reaction_readings
for select
to authenticated
using (
  exists (
    select 1
    from public.examinations e
    where e.id = reaction_readings.examination_id
      and (
        e.created_by = auth.uid()
        or public.current_app_role() in ('admin', 'reviewer')
      )
  )
);

create policy "readings_insert_by_examination_owner"
on public.reaction_readings
for insert
to authenticated
with check (
  public.current_app_role() in ('admin', 'atlm', 'reviewer')
  and exists (
    select 1
    from public.examinations e
    where e.id = reaction_readings.examination_id
      and (
        e.created_by = auth.uid()
        or public.current_app_role() in ('admin', 'reviewer')
      )
  )
);

create policy "readings_update_by_examination_owner"
on public.reaction_readings
for update
to authenticated
using (
  public.current_app_role() in ('admin', 'reviewer')
  or exists (
    select 1
    from public.examinations e
    where e.id = reaction_readings.examination_id
      and e.created_by = auth.uid()
      and public.current_app_role() = 'atlm'
  )
)
with check (
  public.current_app_role() in ('admin', 'reviewer')
  or exists (
    select 1
    from public.examinations e
    where e.id = reaction_readings.examination_id
      and e.created_by = auth.uid()
      and public.current_app_role() = 'atlm'
  )
);
