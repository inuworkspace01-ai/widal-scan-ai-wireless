# WIDAL-SCAN AI — Data-source plan

This registry deliberately separates **visual agglutination grading** from **clinical/epidemiology research**. They are different prediction tasks and must not share labels or be presented as one diagnostic model.

## 1. Visual model: per-well reaction grade

**Required primary dataset:** locally captured Widal slide images, acquired with the WIDAL-SCAN optical setup and annotated by qualified ATLM readers against the exact reagent manufacturer's instructions and the laboratory SOP.

Target labels are visual grades only: 0, 1+, 2+, 3+, 4+. They are not typhoid-positive/negative labels. Keep slide and tube methods, reagent brands/lots, and grading schemes separately versioned. Split train/validation/test by pseudonymous specimen ID, never by crop, to prevent data leakage.

No public Kaggle clinical dataset can substitute for these real, method-specific images.

## 2. Candidate tabular dataset from Kaggle

- **Name:** Typhoid Dataset
- **URL:** https://www.kaggle.com/datasets/rajmohnani12/typhoid-dataset
- **Potential task:** exploratory clinical-feature classification only, after provenance, target definition, schema, licensing, and label quality have been independently reviewed.
- **Published description:** A 2026 study links to this exact Kaggle listing in its Data Availability statement and describes a "Typhoid Multi-Class" dataset of 31,087 anonymised records, 21 variables and four classes (normal/no typhoid, acute, relapsing, complicated): https://www.mdpi.com/2227-9059/14/5/1010. It reports substantial class imbalance. The paper reports results from its own clinical-feature model; those results are not performance evidence for WIDAL-SCAN AI. This confirms the listing is the one referenced by the paper, but it does not independently audit the original records or labels.
- **Important limitation:** the Kaggle page's full metadata/schema/license could not be independently read during setup. Treat this dataset as a candidate, not a validated clinical reference. Do not upload patient-identifiable data. Do not infer visual Widal grades from its tabular features.

The optional `train_clinical_baseline.py` script is a research-only baseline runner. It requires the user to inspect the CSV, explicitly choose the target column, and exclude identifiers/leakage features. It does not return a patient diagnosis or treatment recommendation.

## 3. Related agglutination image dataset (not Widal)

- **BloodyWell:** https://zenodo.org/records/14285035
- **Repository and public test subset:** https://github.com/createcolor/bloody_well
- The Zenodo record describes 3,139 anonymised 512×512 well images from 92 plates and 550 blood samples mixed with 13 reagents for ABO, Rh and Kell blood-group systems. The dataset includes medical-record-derived blood group ground truth and six-expert certainty assessments for agglutination.
- The public GitHub README says the full dataset is not available from the repository and exposes a 529-image test subset (228 MB) with binary `gt_result` (0/1), reagent type, plate row and reagent column.
- **Use in this project:** external morphology/quality-control research only, or a separate binary agglutination benchmark. Do not convert its labels into Widal grades 0, 1+, 2+, 3+, 4+ and do not merge it with Widal training/validation/test partitions. It uses different biological targets and reagent chemistry.
- **Rights/access:** verify the Zenodo record's current licence and any dataset-specific terms before download, redistribution or model training. The GitHub repository's software licence should not automatically be assumed to license every linked image file.
- **Status:** candidate source recorded; not downloaded or trained in this project.

A separate one-image illustration is available on Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Widal_Test_Slide.jpg. It is licensed CC BY-SA 3.0 and shows a Widal slide with O/H agglutination. This is a single illustrative image without machine-readable per-well grade annotations; use it for reference/demo only, not model training.

## 3. WHO reference material

- **WHO laboratory manual for typhoid and paratyphoid (enteric fever), 2026:** https://www.who.int/publications/b/65402
- **Use:** laboratory-method reference and study-protocol context; not a labelled training dataset.
- **Rights:** the WHO publication page lists CC BY-NC-SA 3.0 IGO. Attribute the work and preserve the non-commercial/share-alike conditions when adapting it. Re-check the rights statement before redistribution or commercial use.

## 4. Indonesian Ministry of Health reference

- **Kepmenkes RI No. HK.01.07/MENKES/875/2026 — PNPK Tata Laksana Demam Tifoid pada Dewasa:** https://jdih.kemkes.go.id/storage/documents/pdfs/2026kepmenkes875.pdf
- **Use:** Indonesian clinical-context and governance reference for the adult population. This is a clinical guideline, not a table of labelled training samples. Do not scrape it into pseudo-patient records or train a classifier on recommendation text.

## 5. Additional diagnostic limitation reference

- **CDC Clinical Guidance for Typhoid Fever and Paratyphoid Fever:** https://www.cdc.gov/typhoid-fever/hcp/clinical-guidance/index.html
- CDC identifies blood culture as the mainstay of diagnosis and does not recommend Widal serology because of its high false-positive rate. Apply the intended-use and validation limits locally; this international guidance is not a replacement for Indonesian protocols.

## 6. Safety / intended use

WHO and CDC sources describe limitations of serological diagnosis and the importance of laboratory confirmation. A visual-grade classifier must only report a tentative visual observation for ATLM review. It must not diagnose, rule out, triage, or recommend treatment for typhoid. A good visual grading score does not validate the Widal test as a standalone diagnostic test.

## 7. Data-governance checklist before ingestion

1. Verify source provenance, licence, allowed purpose, and data dictionary.
2. Verify what the target label actually means and how it was adjudicated.
3. Remove direct identifiers and inspect indirect identifiers.
4. Check duplicates, class imbalance, missingness, label leakage and repeated patients.
5. Keep a patient/specimen-level group identifier for data splitting.
6. Lock a held-out test set before model selection and report per-class recall, macro-F1, balanced accuracy, confusion matrix and confidence intervals.
7. Validate externally across time, operators, devices, reagent lots and sites before any clinical pilot.
