insert into public.dataset_versions
  (name, source, task, specimen_count, image_count, label_schema, provenance, license, status)
select
  'Blood Agglutination Curated Dataset V1',
  'Zenodo DOI 10.5281/zenodo.21384197; curated from Roboflow Universe Blood Group Detection',
  'external_agglutination_binary',
  0,
  8043,
  '{"classes":{"0":"clumped / visible red-cell agglutination","1":"not clumped / no visible agglutination"},"splits":{"train":6550,"validation":1030,"test":463},"class_counts":{"clumped":7009,"not_clumped":1034},"resolution":"224x224 RGB","task":"binary agglutination"}'::jsonb,
  '{"doi":"https://doi.org/10.5281/zenodo.21384197","repository":"https://github.com/sayon-mitra024/blood-agglutination-calibration-framework","data_card":"DATA_CARD.md","original_source":"https://universe.roboflow.com/minor-project-5th-semester/blood-group-detection-4yvdx/dataset/4","model_reference":"https://huggingface.co/sayon-mitra024/blood-agglutination-classifier","limitations":["binary clumped/not-clumped task","blood-group agglutination, not Widal","single image source","unknown demographics","no specimen identifiers available for independently verifying patient-level split"],"use":"external binary agglutination benchmark only; never map to Widal 0–4+"}'::jsonb,
  'CC BY 4.0 as declared by the dataset Data Card; preserve attribution and verify original Roboflow terms',
  'pending_review'
where not exists (
  select 1 from public.dataset_versions
  where name = 'Blood Agglutination Curated Dataset V1'
);
