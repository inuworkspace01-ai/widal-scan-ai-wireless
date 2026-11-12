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
# Install torch and torchvision using the official selector:
# https://pytorch.org/get-started/locally/
pip install -r requirements.txt
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
