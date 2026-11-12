# Blood Agglutination Curated Dataset V1 — archive audit

**Audit date:** 13 November 2026  
**Archive reviewed:** `BloodAgglutinationCuratedDataset_v1.0.zip`  
**Archive SHA-256:** `6ffae33bfad4a0a90442cbcf9c8043e19658856c23c5670e689c85b3d60334f6`  
**Research task:** external binary blood-group/agglutination benchmark only — **not Widal**.

## Results

| Check | Result |
|---|---:|
| Image files discovered | 8,043 |
| Readable image files | 8,043 |
| Corrupt/unreadable images | 0 |
| Dimensions / format / mode | 224×224 / JPEG / RGB (all) |
| Exact duplicate groups within same split and same label | 174 |
| Redundant exact duplicate copies removed | 174 |
| Exact image hashes assigned to conflicting labels | 22 groups |
| Files excluded due to conflicting labels | 44 |
| Exact duplicates repeated across provided splits | 0 |
| Unique images in filtered candidate manifest | 7,825 |
| Distinct filename tokens that appear in multiple splits | 438 |
| Distinct filename tokens that appear under both labels | 441 |

### Filtered candidate split counts

| Split | `clumped` | `not_clumped` | Total |
|---|---:|---:|---:|
| Train | 5,636 | 703 | 6,339 |
| Validation | 841 | 186 | 1,027 |
| Test | 373 | 86 | 459 |
| **Total** | **6,850** | **975** | **7,825** |

## Duplicate handling

The audit uses SHA-256 over the original file bytes.

- When the exact same file occurs more than once under the same label and split, the manifest keeps one deterministic path and drops the redundant copies.
- When the exact same file hash appears under conflicting labels, all copies of that hash are excluded. The two labels cannot both be correct for byte-identical images without further source adjudication.
- An identical hash appearing in more than one split would be excluded from every split. None were found in this archive.
- The source images inside the ZIP are not modified or deleted. The filtering affects only the generated research manifest.

This is exact-byte duplicate detection. Perceptual or near-duplicate matching has not been performed.

## Potential specimen/sample leakage

The filenames contain repeated tokens such as `A-14`, `AB-75`, and `O-105`. The audit found 800 distinct tokens; 438 occur in multiple splits and 441 occur under both binary labels.

The archive does not define these tokens or provide a specimen data dictionary. They may identify donors/samples, reaction wells, blood-group labels, or another source indexing scheme. We therefore do **not** automatically treat them as patient/specimen IDs or silently reshuffle the source partitions.

However, if the tokens represent specimens, the supplied train/validation/test partitions are not specimen-independent and test metrics could be inflated by sample leakage. The curator must explain the naming convention and provide a reliable specimen-group key before any claim of patient-level or specimen-level generalization. Until then, the pipeline marks all results as **image-level only** and requires explicit acknowledgement before training.

## Provenance and licence

The uploaded archive contains conflicting/unfinished provenance statements:

- `CITATION.cff` says: `License pending verification of original dataset redistribution terms`.
- `DATASET_CARD.md` says the original dataset source is not available from its notebook or metadata.
- `README.md` attributes the data to a Roboflow Universe Blood Group Detection project: https://universe.roboflow.com/minor-project-5th-semester/blood-group-detection-4yvdx
- That Roboflow page currently displays CC BY 4.0, but its visible page metadata describes 2,365 images and four versions; the uploaded 8,043-image archive does not document precisely which source version(s) were copied, curated, or redistributed.

Therefore the archive's reuse/redistribution rights remain **pending verification**. Obtain confirmation from the dataset curator or trace the complete source/version/licence chain. Do not redistribute, publish, or use commercially before that review is complete.

## Intended use boundary

These labels describe binary agglutination in blood-group testing. They are not Widal slide reaction grades and must never be converted into Widal `0`, `1+`, `2+`, `3+`, or `4+` annotations. The archive cannot train or validate the WIDAL-SCAN visual-grade model.

No model was trained from this archive during this audit. No performance metric, diagnostic accuracy, or clinically validated capability is claimed.

## Generated outputs

The locally generated output bundle contains:

- `external_binary_manifest.csv` — 7,825 unique image paths with labels, splits and SHA-256.
- `external_binary_manifest.audit.json` — counts, QC results and filename-token warnings.
- `external_binary_manifest_duplicates.csv` — exact duplicate groups and the action taken for each source file.

The images themselves are excluded from the repository. Keep the source archive, images, manifest and model artifacts in an access-controlled local research folder.
