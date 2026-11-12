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

## 3. Blood Agglutination Curated Dataset V1 (not Widal)

- **DOI:** https://doi.org/10.5281/zenodo.21384197
- **Archive citation/repository:** https://github.com/sayon-mitra024/BloodGroupDataset_V1
- **README attribution:** https://universe.roboflow.com/minor-project-5th-semester/blood-group-detection-4yvdx
- **Declared composition:** 8,043 JPEG RGB images at 224×224; 6,550 train / 1,030 validation / 463 test; binary `clumped` / `not_clumped`; reported source counts 7,009 and 1,034.
- **Rights status:** **pending verification**. The uploaded archive's `CITATION.cff` explicitly says `License pending verification of original dataset redistribution terms`; its `DATASET_CARD.md` says the original source is unavailable. Its README points to a Roboflow Universe project that currently displays CC BY 4.0, but the exact derivation and version mapping from that project to the 8,043-image archive are not documented. Do not treat the archive as automatically cleared for reuse or redistribution on the basis of the Roboflow page alone. Obtain written/source-level confirmation from the dataset curator or verify the archive's provenance and licence chain first.
- **Uploaded archive audit (13 November 2026):** 8,043/8,043 images readable and consistently 224×224 JPEG RGB; 174 exact duplicate groups with same labels (174 redundant copies); 22 exact-image groups assigned conflicting labels (44 files excluded); no exact-byte duplicate across the provided splits. After exact-duplicate handling, 7,825 unique images remain in the candidate manifest.
- **Possible group leakage:** filenames contain tokens such as `A-14` / `AB-75`. 438 distinct tokens appear in more than one split. The archive does not define these tokens, so they are not treated as verified specimen IDs; their meaning must be confirmed by the curator before any claim of independent test performance. The current manifest is only image-level.
- **Related third-party model:** https://huggingface.co/sayon-mitra024/blood-agglutination-classifier. Its reported metrics belong to that model author's experiment and are not WIDAL-SCAN results.
- **Use:** separate external blood-group/agglutination binary benchmark only. Never convert these labels to Widal reaction grades or combine these images with the Widal-specific training partitions.
- **Status:** registered in Supabase as `external_agglutination_binary`, still `pending_review`; archive audited locally; candidate manifest generated after exact duplicate filtering; model not trained; no performance metrics produced.

See [DATASET-AUDIT.md](DATASET-AUDIT.md) for the audit methodology and counts.

## 4. Related agglutination image dataset (not Widal)

- **BloodyWell:** https://zenodo.org/records/14285035
- **Repository and public test subset:** https://github.com/createcolor/bloody_well
- The study describes 3,139 anonymised 512×512 well images from 92 plates and 550 donor blood samples mixed with 13 reagents for ABO, Rh and Kell systems. Each image has a blood-group ground truth and confidence assessments from six serology experts.
- The GitHub project states that the **full dataset is not publicly downloadable there** and exposes only a 529-image test subset (228 MB) with binary `gt_result` (0/1), reagent type, plate row and reagent column. The Zenodo record lists an `imgs.zip` file of 1.7 GB, but this conflicts with the paper/repository access statement; verify the current version and permission with the authors before acquiring any full data.
- Expert confidence labels use `0, 0.25, 0.5, 0.75, 1.0`; they represent confidence in agglutination presence, not Widal reaction grades `0, 1+, 2+, 3+, 4+`.
- **Use in this project:** a separate external binary-agglutination benchmark or morphology research only, after data permission is confirmed. Do not convert its labels into Widal grades or merge it into Widal training/validation/test partitions. It uses different biological targets and reagent chemistry.
- **Rights/access:** the record's dataset-specific licence is not clearly specified in the accessible metadata. Verify permissions with the authors before downloading, training, redistribution or commercial use. The GitHub software licence does not automatically license linked images.
- **Status:** catalogued in Supabase as `external_agglutination_binary`, pending rights/access review; not downloaded and not trained in this project.

A separate one-image illustration is available on Wikimedia Commons: https://commons.wikimedia.org/wiki/File:Widal_Test_Slide.jpg. It is licensed CC BY-SA 3.0 and shows a Widal slide with O/H agglutination. This is a single illustrative image without machine-readable per-well grade annotations; use it for reference/demo only, not model training.

## 5. WHO reference material

- **WHO laboratory manual for typhoid and paratyphoid (enteric fever), 2026:** https://www.who.int/publications/b/65402
- **Use:** laboratory-method reference and study-protocol context; not a labelled training dataset.
- **Rights:** the WHO publication page lists CC BY-NC-SA 3.0 IGO. Attribute the work and preserve the non-commercial/share-alike conditions when adapting it. Re-check the rights statement before redistribution or commercial use.

## 6. Indonesian Ministry of Health reference

- **Kepmenkes RI No. HK.01.07/MENKES/875/2026 — PNPK Tata Laksana Demam Tifoid pada Dewasa:** https://jdih.kemkes.go.id/storage/documents/pdfs/2026kepmenkes875.pdf
- **Use:** Indonesian clinical-context and governance reference for the adult population. This is a clinical guideline, not a table of labelled training samples. Do not scrape it into pseudo-patient records or train a classifier on recommendation text.

## 7. Additional diagnostic limitation reference

- **CDC Clinical Guidance for Typhoid Fever and Paratyphoid Fever:** https://www.cdc.gov/typhoid-fever/hcp/clinical-guidance/index.html
- CDC identifies blood culture as the mainstay of diagnosis and does not recommend Widal serology because of its high false-positive rate. Apply the intended-use and validation limits locally; this international guidance is not a replacement for Indonesian protocols.

## 8. Safety / intended use

WHO and CDC sources describe limitations of serological diagnosis and the importance of laboratory confirmation. A visual-grade classifier must only report a tentative visual observation for ATLM review. It must not diagnose, rule out, triage, or recommend treatment for typhoid. A good visual grading score does not validate the Widal test as a standalone diagnostic test.

## 9. Data-governance checklist before ingestion

1. Verify source provenance, licence, allowed purpose, and data dictionary.
2. Verify what the target label actually means and how it was adjudicated.
3. Remove direct identifiers and inspect indirect identifiers.
4. Check duplicates, class imbalance, missingness, label leakage and repeated patients.
5. Keep a patient/specimen-level group identifier for data splitting.
6. Lock a held-out test set before model selection and report per-class recall, macro-F1, balanced accuracy, confusion matrix and confidence intervals.
7. Validate externally across time, operators, devices, reagent lots and sites before any clinical pilot.
