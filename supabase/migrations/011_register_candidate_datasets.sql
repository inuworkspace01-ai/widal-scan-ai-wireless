insert into public.dataset_versions
  (name, source, task, specimen_count, image_count, label_schema, provenance, license, status)
select
  'BloodyWell Agglutination Image Dataset',
  'Zenodo 14285035; GitHub createcolor/bloody_well',
  'external_agglutination_binary',
  550,
  3139,
  '{"ground_truth":{"gt_result":[0,1],"meaning":"binary blood-group agglutination result"},"expert_assessment":{"confidence_scores":[0,0.25,0.5,0.75,1],"meaning":"six experts confidence that agglutination occurred"},"reagents":["ABO","Rh","Kell"],"image_resolution":"512x512"}'::jsonb,
  '{"url":"https://zenodo.org/records/14285035","github":"https://github.com/createcolor/bloody_well","study":"https://pmc.ncbi.nlm.nih.gov/articles/PMC10987457/","total_well_images":3139,"plates":92,"donor_samples":550,"reagents":13,"public_github_test_subset_images":529,"public_github_test_subset_size_mb":228,"availability_note":"The paper and project README state the full training dataset is not publicly available; a 529-image test subset is exposed. The Zenodo record lists an imgs.zip file, so current access and version availability must be verified with the authors before acquisition.","source_note":"Different blood-group chemistry and ABO/Rh/Kell reagents. External binary agglutination benchmark only; never convert labels into Widal 0-4+ grades."}'::jsonb,
  'Not clearly specified for all image files; confirm dataset-specific reuse terms with authors before download or training',
  'pending_review'
where not exists (
  select 1 from public.dataset_versions
  where name = 'BloodyWell Agglutination Image Dataset'
);

insert into public.dataset_versions
  (name, source, task, specimen_count, image_count, label_schema, provenance, license, status)
select
  'Typhoid Dataset — Kaggle (tabular)',
  'Kaggle rajmohnani12/typhoid-dataset',
  'clinical_tabular_research',
  31087,
  0,
  '{"classes":["normal/no typhoid","acute","relapsing","complicated"],"variables_reported":21,"format":"tabular"}'::jsonb,
  '{"url":"https://www.kaggle.com/datasets/rajmohnani12/typhoid-dataset","paper":"https://www.mdpi.com/2227-9059/14/5/1010","source_note":"Separate exploratory clinical-feature task; not image training and not diagnosis."}'::jsonb,
  'Verify Kaggle dataset licence and source metadata before ingestion',
  'pending_review'
where not exists (
  select 1 from public.dataset_versions
  where name = 'Typhoid Dataset — Kaggle (tabular)'
);

insert into public.dataset_versions
  (name, source, task, specimen_count, image_count, label_schema, provenance, license, status)
select
  'Widal Test Slide — Wikimedia reference image',
  'Wikimedia Commons File:Widal Test Slide.jpg',
  'visual_grade',
  0,
  1,
  '{"labels":[],"semantics":"illustrative slide photo; no per-well machine-readable annotations"}'::jsonb,
  '{"url":"https://commons.wikimedia.org/wiki/File:Widal_Test_Slide.jpg","note":"Single illustrative Widal O/H slide image; reference/demo only, not sufficient for training."}'::jsonb,
  'CC BY-SA 3.0 Unported — attribution and share-alike required',
  'pending_review'
where not exists (
  select 1 from public.dataset_versions
  where name = 'Widal Test Slide — Wikimedia reference image'
);
