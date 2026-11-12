# WIDAL-SCAN AI — Training Foundation

**Status: training pipeline starter, NOT a trained or clinically validated model.**

This package prepares a reproducible computer-vision workflow for **per-well slide-agglutination grading**. It does not diagnose typhoid fever. It predicts only the visual reaction grade on an image crop.

## Scope

Initial visual labels:

- \`0\`: no visible agglutination
- \`1+\`
- \`2+\`
- \`3+\`
- \`4+\`

Before collecting data, the laboratory lead must confirm that these grades match the exact reagent manufacturer's instructions and the local SOP. Do not mix slide and tube methods, different reagent systems, or different grading rules in one label set.

The pipeline is:

1. Capture full test images in a fixed camera, distance, angle and lighting setup.
2. An ATLM annotates the individual reaction wells and assigns the reference grade.
3. \`prepare_crops.py\` exports one image crop per well.
4. \`train.py\` trains a ResNet-18 classifier with specimen-grouped train/validation/test splits.
5. \`predict.py\` predicts a visual grade for a single cropped well.
6. A separate, deterministic interpretation layer may combine confirmed grades with the test kit's instructions. It must not infer a typhoid diagnosis.

## Dataset policy

Never commit patient images, patient identifiers, names, dates of birth, medical record numbers, or other identifiable information to GitHub. Use pseudonymous specimen IDs, approved access-controlled storage, and the facility's data-governance process. Do not upload real patient images to public repositories or public labeling services.

Each row in \`annotations.csv\` represents one well:

| Column | Meaning |
|---|---|
| \`image_path\` | Relative path to the original full test image |
| \`specimen_id\` | Pseudonymous ID; same specimen must always use the same ID |
| \`well_id\` | Pseudonymous well/position label |
| \`x\`, \`y\` | Top-left crop coordinate in original image pixels |
| \`width\`, \`height\` | Crop width and height in pixels |
| \`label\` | ATLM-confirmed visual grade: 0, 1+, 2+, 3+, or 4+ |

Two qualified readers should grade images independently where feasible. Resolve disagreements by a predefined senior-reader procedure and retain the adjudicated label. Record reader agreement (for example, weighted Cohen's kappa) in the study report.

## Setup (Windows)

Use a dedicated Python 3.11 or 3.12 environment. Install a PyTorch build appropriate for the PC (CPU or CUDA) from the official PyTorch installation selector, then install this package's remaining dependencies:

\`\`\`powershell
cd services/ai
py -3.11 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
# For CPU-only PCs, install the CPU wheels first:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# Then install the remaining project requirements:
pip install -r requirements.txt

# For NVIDIA CUDA, choose the matching command at:
# https://pytorch.org/get-started/locally/
# Avoid installing a CPU wheel after installing a CUDA build.
\`\`\`

## Prepare cropped well images

Place de-identified source images under \`data/raw/\`. Create \`annotations.csv\` using the schema above. Coordinates must refer to the original image, not a resized preview.

\`\`\`powershell
python prepare_crops.py --annotations annotations.csv --image-root data/raw --output-root data/crops
\`\`\`

This creates \`data/crops/dataset.csv\` and one crop per annotation. Keep the source-to-crop mapping in the protected research workspace, not in a public repo.

## Train

\`\`\`powershell
python train.py --data-csv data/crops/dataset.csv --image-root data/crops --out-dir artifacts --epochs 40 --batch-size 32
\`\`\`

The script uses five-fold stratified group splitting by \`specimen_id\`: one fold for test, one for validation, and the remaining folds for training. This prevents crops from the same specimen leaking into different subsets. At least five distinct specimens per grade are required by this starter split; more independent specimens are strongly preferred.

Outputs:

- \`artifacts/best_model.pt\`
- \`artifacts/metrics.json\`
- \`artifacts/test_predictions.csv\`

The model-selection score is validation macro-F1. The test set is evaluated only after the best checkpoint is selected.

## Predict one cropped well

\`\`\`powershell
python predict.py --checkpoint artifacts/best_model.pt --image data/crops/example.jpg
\`\`\`

The returned score is the model's raw softmax score, **not a calibrated clinical probability**. Every result must be reviewed by an ATLM until a prospective validation study and an approved clinical workflow demonstrate otherwise.

## Validation checklist before any real-world pilot

- Use a locked, independent test set with no specimen overlap.
- Include multiple operators, devices, reagent lots, days, and realistic lighting variation.
- Include negative, weak, borderline, strong, invalid, blurry, overexposed, underexposed, and out-of-focus images.
- Report per-grade sensitivity/recall, specificity where appropriate, precision, macro-F1, balanced accuracy, confusion matrix, and confidence intervals.
- Assess performance on a later time period and, ideally, a second site/device.
- Define an abstain/review rule for low-quality, unfamiliar, or uncertain images.
- Have an ATLM and clinical/laboratory governance team approve the intended use.

**Important:** good image-grading performance does not make Widal a reliable standalone test for typhoid. CDC does not recommend Widal serology because of false positives; blood culture is the mainstay of diagnosis. This software must not diagnose, rule out, triage, or recommend treatment for typhoid.


## Optional clinical tabular research baseline

A separate exploratory runner is available for a locally inspected Kaggle CSV:

```powershell
python train_clinical_baseline.py --csv data/typhoid.csv --target-column YOUR_LABEL_COLUMN --out-dir clinical-artifacts
```

When repeated-patient/specimen identifiers exist, pass a verified grouping column:

```powershell
python train_clinical_baseline.py --csv data/typhoid.csv --target-column YOUR_LABEL_COLUMN --group-column YOUR_PATIENT_GROUP_COLUMN --drop-columns PII_OR_LEAKAGE_COLUMN --out-dir clinical-artifacts
```

Inspect the CSV schema and licence before running this. The runner excludes common direct identifiers by column-name pattern, but that is not a substitute for manual de-identification and leakage review. Do not feed its class predictions into the Widal image-grade workflow. Outputs are exploratory research only and do not diagnose a patient.

See [DATA-SOURCES.md](DATA-SOURCES.md) for the source register, WHO/Kemenkes reference use, and the data-governance checklist.


## Guarded automatic candidate retraining (Windows)

The scheduled job is intended to keep a research candidate up to date when new **ATLM-approved visual labels** are added. It does not train from every captured image, does not invent labels, and does not promote a new model to a live workflow.

1. Finish the manual data preparation steps above. Keep the specimen images and manifest in a protected local research folder. Do not put them in GitHub.
2. Create an approval file beside the manifest by copying `data/dataset_approval.example.json` to `data/crops/dataset_approval.json`.
3. Calculate the manifest hash in PowerShell:

```powershell
(Get-FileHash .\data\crops\dataset.csv -Algorithm SHA256).Hash.ToLower()
```

4. Put that exact hash in `manifest_sha256`, set `approved` to `true`, and record the authorized ATLM reviewer and timestamp in `approved_by` and `approved_at`. Any modification to the manifest invalidates the approval hash.
5. From the repository root, register the weekly Windows Task Scheduler job:

```powershell
powershell -ExecutionPolicy Bypass -File .\services\ai\windows\register-weekly-training.ps1 -ProjectRoot (Get-Location).Path
```

The default schedule is Sunday at 03:00 local PC time. The PC must be available for the scheduled task to run. The job checks for a changed, approved manifest and skips if the hash is unchanged.

6. Candidate checkpoints and metrics are written under `services/ai/artifacts/auto/`. Each candidate is marked `awaiting_atlm_and_research_review`.

To remove the schedule:

```powershell
powershell -ExecutionPolicy Bypass -File .\services\ai\windows\remove-weekly-training-task.ps1
```

**Release gate:** automatic promotion is deliberately disabled. An ATLM/research reviewer must inspect the locked test metrics, confusion matrix, subgroup performance, and data provenance before a candidate can replace any approved model. The weekly job only trains the visual-grade classifier; it does not train on Kaggle tabular data or use WHO/Kemenkes PDFs as image labels.


## Guarded automatic candidate retraining (Windows)

The scheduled job trains a research candidate when new **ATLM-approved visual labels** are available. It does not train from every camera capture, invent labels, or promote a model to the live workflow.

1. Finish the manual data preparation steps above. Keep source images and the dataset manifest in a protected local research folder, not GitHub.
2. Copy `data/dataset_approval.example.json` to `data/crops/dataset_approval.json`.
3. Calculate the manifest hash in PowerShell:

```powershell
(Get-FileHash .\data\crops\dataset.csv -Algorithm SHA256).Hash.ToLower()
```

4. Put that exact hash in `manifest_sha256`, set `approved` to `true`, and record the authorized ATLM reviewer and timestamp in `approved_by` and `approved_at`. Any manifest modification invalidates the approval hash.
5. From the repository root, register the weekly Windows Task Scheduler job:

```powershell
powershell -ExecutionPolicy Bypass -File .\services\ai\windows\register-weekly-training.ps1 -ProjectRoot (Get-Location).Path
```

The default schedule is Sunday at 03:00 local PC time. The PC must be available for the task to run. The runner skips if the approved manifest hash has not changed.

6. Candidate checkpoints and metrics are written to `services/ai/artifacts/auto/`. Each candidate is marked `awaiting_atlm_and_research_review`.

Remove the task with:

```powershell
powershell -ExecutionPolicy Bypass -File .\services\ai\windows\remove-weekly-training-task.ps1
```

**Release gate:** automatic production promotion is deliberately disabled. An ATLM/research reviewer must inspect the locked test metrics, confusion matrix, subgroup performance, and data provenance before a candidate can replace an approved model. This weekly job trains the visual-grade classifier only; it does not train on Kaggle tabular data or use WHO/Kemenkes PDFs as image labels.

## External binary agglutination benchmark (not Widal)

The following public research datasets may be used to explore image quality, morphology, calibration and binary clumping recognition. They are **not Widal O/H/AH/BH reaction-grade data** and must remain in the separate `external_agglutination_binary` task.

### Blood Agglutination Curated Dataset V1

- DOI: https://doi.org/10.5281/zenodo.21384197
- Dataset Data Card: https://github.com/sayon-mitra024/blood-agglutination-calibration-framework/blob/main/DATA_CARD.md
- Repository: https://github.com/sayon-mitra024/blood-agglutination-calibration-framework
- Declared size: 8,043 images (6,550 train / 1,030 validation / 463 test), binary clumped/not-clumped, resized to 224×224 RGB
- Declared licence: CC BY 4.0, as stated by the dataset Data Card. Retain attribution and verify the current Zenodo record / original Roboflow terms before reuse.
- Provenance: curated from Roboflow Universe “Blood Group Detection”; the Data Card does not provide donor/specimen IDs. It declares fixed train/validation/test splits and no cross-split image leakage, but this does not establish patient-level independence.
- Reported external paper/model: https://huggingface.co/sayon-mitra024/blood-agglutination-classifier. Its paper/model reports its own binary blood-agglutination experiment; those metrics are not WIDAL-SCAN results.
- Use only as an external binary agglutination benchmark or exploratory transfer-learning source. Do not convert labels into 0, 1+, 2+, 3+, 4+ or treat it as Widal.

### BloodyWell

- DOI: https://zenodo.org/records/14285035
- Repository: https://github.com/createcolor/bloody_well
- 3,139 ABO/Rh/Kell blood-group well images; only a 529-image test subset is described as publicly available in the GitHub README.
- Different reagent chemistry and target labels. Use as an external binary-agglutination test only, not for Widal grade training.

Neither dataset is a substitute for the required locally captured Widal images annotated against the selected kit instructions and laboratory SOP. Do not use the benchmark metrics or pretrained external model as evidence of Widal performance.
