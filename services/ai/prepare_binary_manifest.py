from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLITS = {"train": ("train",), "validation": ("valid", "validation", "val"), "test": ("test",)}
CLASS_DIRS = {
    "clumped": "clumped",
    "not_clumped": "not_clumped",
    "not-clumped": "not_clumped",
    "not clumped": "not_clumped",
}
# Report only: archive documentation does not define whether these tokens are specimen IDs.
GROUP_TOKEN_RE = re.compile(r"(?:^|_)(AB|A|B|O)-(\d+)-_(?:jpg|jpeg|png)(?:\.|$)", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_group_token(filename: str) -> str:
    match = GROUP_TOKEN_RE.search(filename)
    return f"{match.group(1).upper()}-{match.group(2)}" if match else ""


def find_splits(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for split, candidates in SPLITS.items():
        found = [root / name for name in candidates if (root / name).is_dir()]
        if len(found) != 1:
            raise ValueError(
                f"Expected exactly one directory for {split}; checked {', '.join(candidates)}."
            )
        result[split] = found[0]
    return result


def audit_dataset(root: Path):
    split_dirs = find_splits(root)
    records: list[dict] = []
    invalid_files: list[dict] = []
    ignored_files: list[str] = []
    hashes: dict[str, list[int]] = defaultdict(list)
    tokens: dict[str, list[int]] = defaultdict(list)
    dimensions, formats, modes = Counter(), Counter(), Counter()

    for split, split_dir in split_dirs.items():
        found_labels: set[str] = set()
        for class_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            label = CLASS_DIRS.get(class_dir.name.strip().lower())
            if label is None or label in found_labels:
                raise ValueError(f"Unexpected or duplicate class folder: {class_dir}")
            found_labels.add(label)

            for path in sorted(class_dir.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Symbolic links are not accepted: {path}")
                if not path.is_file():
                    continue
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    ignored_files.append(path.relative_to(root).as_posix())
                    continue
                resolved = path.resolve()
                if class_dir.resolve() not in resolved.parents:
                    raise ValueError(f"Image path escapes class directory: {path}")
                try:
                    with Image.open(resolved) as im:
                        im.verify()
                    with Image.open(resolved) as im:
                        width, height = im.size
                        image_format, mode = im.format or "unknown", im.mode
                except (UnidentifiedImageError, OSError, ValueError) as exc:
                    invalid_files.append({"path": path.relative_to(root).as_posix(), "error": str(exc)})
                    continue

                digest = sha256_file(resolved)
                token = extract_group_token(path.name)
                idx = len(records)
                records.append({
                    "image_path": path.relative_to(root).as_posix(),
                    "split": split,
                    "label": label,
                    "sha256": digest,
                    "potential_group_token": token,
                    "task": "external_agglutination_binary",
                    "width": width,
                    "height": height,
                    "format": image_format,
                    "mode": mode,
                })
                hashes[digest].append(idx)
                if token:
                    tokens[token].append(idx)
                dimensions[f"{width}x{height}"] += 1
                formats[image_format] += 1
                modes[mode] += 1

        if found_labels != {"clumped", "not_clumped"}:
            raise ValueError(f"{split} must contain both clumped and not_clumped folders.")

    excluded: dict[int, str] = {}
    duplicate_rows: list[dict] = []
    duplicate_summary = Counter()
    for digest, indexes in sorted(hashes.items()):
        if len(indexes) < 2:
            continue
        group = [records[i] for i in indexes]
        group_splits = {row["split"] for row in group}
        group_labels = {row["label"] for row in group}

        if len(group_labels) > 1:
            action, reason = "exclude_all", "identical_file_hash_has_conflicting_labels"
            for i in indexes:
                excluded[i] = reason
            duplicate_summary["conflicting_label_groups"] += 1
            duplicate_summary["conflicting_label_files"] += len(indexes)
        elif len(group_splits) > 1:
            action, reason = "exclude_all", "identical_file_hash_appears_in_multiple_splits"
            for i in indexes:
                excluded[i] = reason
            duplicate_summary["cross_split_groups"] += 1
            duplicate_summary["cross_split_files"] += len(indexes)
        else:
            keep = min(indexes, key=lambda i: records[i]["image_path"])
            action, reason = "keep_first_remove_rest", "exact_duplicate_within_same_split_and_label"
            for i in indexes:
                if i != keep:
                    excluded[i] = reason
            duplicate_summary["same_split_groups"] += 1
            duplicate_summary["same_split_extra_files_removed"] += len(indexes) - 1

        for row in group:
            duplicate_rows.append({
                "sha256": digest,
                "split": row["split"],
                "label": row["label"],
                "image_path": row["image_path"],
                "action": action,
                "reason": reason,
            })

    clean = [row for i, row in enumerate(records) if i not in excluded]
    split_counts = Counter((row["split"], row["label"]) for row in clean)

    token_collisions, mixed_tokens = [], []
    for token, indexes in sorted(tokens.items()):
        group = [records[i] for i in indexes]
        group_splits = sorted({row["split"] for row in group})
        group_labels = sorted({row["label"] for row in group})
        if len(group_splits) > 1:
            token_collisions.append({
                "token": token,
                "splits": group_splits,
                "image_count": len(group),
                "labels": group_labels,
                "sample_paths": [row["image_path"] for row in group[:8]],
            })
        if len(group_labels) > 1:
            mixed_tokens.append({
                "token": token,
                "labels": group_labels,
                "image_count": len(group),
                "sample_paths": [row["image_path"] for row in group[:8]],
            })

    report = {
        "task": "external_agglutination_binary",
        "not_widal": True,
        "source_image_count": len(records),
        "invalid_image_count": len(invalid_files),
        "invalid_files": invalid_files,
        "ignored_non_image_files": ignored_files,
        "dimensions": dict(dimensions),
        "formats": dict(formats),
        "modes": dict(modes),
        "duplicate_summary": dict(duplicate_summary),
        "duplicate_groups": len(duplicate_rows) and len({row["sha256"] for row in duplicate_rows}) or 0,
        "excluded_file_count": len(excluded),
        "clean_manifest_image_count": len(clean),
        "clean_manifest_split_counts": {
            f"{split}/{label}": split_counts[(split, label)]
            for split in ("train", "validation", "test")
            for label in ("clumped", "not_clumped")
        },
        "unique_hash_count_after_filtering": len({row["sha256"] for row in clean}),
        "potential_filename_group_token_count": len(tokens),
        "potential_filename_group_tokens_crossing_splits": len(token_collisions),
        "potential_filename_group_tokens_with_mixed_labels": len(mixed_tokens),
        "potential_filename_group_token_warning": (
            "Tokens such as A-14 or AB-75 may identify samples, but their meaning is undocumented. "
            "They are reported for human review and are not treated as specimen IDs."
        ),
        "cross_split_token_examples": token_collisions[:50],
        "mixed_label_token_examples": mixed_tokens[:50],
        "limitations": [
            "Exact-byte duplicate checking is performed; perceptual/near-duplicate checking is not.",
            "Patient/specimen-level split independence cannot be proven because specimen IDs are not documented.",
            "The source-provided train/validation/test partitions are retained.",
            "This is a binary blood-group/agglutination benchmark, not a Widal reaction-grade dataset.",
        ],
    }
    return clean, duplicate_rows, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit a separate external binary agglutination benchmark (not Widal)."
    )
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("external_binary_manifest.csv"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--duplicates-csv", type=Path)
    args = parser.parse_args()

    root = args.dataset_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Dataset folder not found: {root}")

    try:
        clean, duplicate_rows, report = audit_dataset(root)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = args.output.resolve()
    report_path = args.report.resolve() if args.report else output.with_suffix(".audit.json")
    duplicate_path = (
        args.duplicates_csv.resolve()
        if args.duplicates_csv
        else output.with_name(output.stem + "_duplicates.csv")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    duplicate_path.parent.mkdir(parents=True, exist_ok=True)

    report["manifest_path"] = output.name
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with duplicate_path.open("w", encoding="utf-8", newline="") as stream:
        fields = ["sha256", "split", "label", "image_path", "action", "reason"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(duplicate_rows)

    if report["invalid_image_count"]:
        raise SystemExit(f"Found {report['invalid_image_count']} unreadable images. See {report_path}.")

    for split in ("train", "validation", "test"):
        labels = {row["label"] for row in clean if row["split"] == split}
        if labels != {"clumped", "not_clumped"}:
            raise SystemExit(
                f"{split} lacks one or more classes after filtering. See {report_path}; "
                "source split requires curator review."
            )

    columns = [
        "image_path", "split", "label", "sha256", "potential_group_token", "task"
    ]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in sorted(clean, key=lambda x: (x["split"], x["label"], x["image_path"])):
            writer.writerow({key: row[key] for key in columns})

    print(json.dumps({
        "manifest": str(output),
        "audit_report": str(report_path),
        "duplicate_report": str(duplicate_path),
        "source_images": report["source_image_count"],
        "clean_manifest_images": report["clean_manifest_image_count"],
        "duplicate_summary": report["duplicate_summary"],
        "potential_filename_group_tokens_crossing_splits":
            report["potential_filename_group_tokens_crossing_splits"],
        "task": "external_agglutination_binary",
        "not_widal": True,
        "warning": "Verify source rights and sample-token meaning before interpreting model metrics.",
    }, indent=2))


if __name__ == "__main__":
    main()
