alter table public.dataset_versions
  drop constraint if exists dataset_versions_task_check;
alter table public.dataset_versions
  add constraint dataset_versions_task_check
  check (task in ('visual_grade','clinical_tabular_research','external_agglutination_binary'));

alter table public.training_runs
  drop constraint if exists training_runs_task_check;
alter table public.training_runs
  add constraint training_runs_task_check
  check (task in ('visual_grade','clinical_tabular_research','external_agglutination_binary'));

alter table public.model_registry
  drop constraint if exists model_registry_task_check;
alter table public.model_registry
  add constraint model_registry_task_check
  check (task in ('visual_grade','clinical_tabular_research','external_agglutination_binary'));

update public.dataset_versions
set task='external_agglutination_binary'
where name='BloodyWell Agglutination Image Dataset';
