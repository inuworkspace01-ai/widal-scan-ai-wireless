from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image


SPLITS = {
    "train": ("train",),
    "validation": ("valid", "validation", "val"),
    "test": ("test",),
}
CLASS_DIRS = {
    "clumped": "clumped",
    "not_clumped": "not_clumped",
    "not-clumped": "not_clumped",
    "not clumped": "not_clumped",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a separate manifest for Blood Agglutination Curated V1. "
            "This is an external binary benchmark, not Widal."
        )
    )
    parser.add_argument("--dataset-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("external_binary_manifest.csv"))
    args = parser.parse_args()

    root = args.dataset_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Dataset folder not found: {root}")

    # Accept common archive names, but require exactly one folder per split.
    split_dirs: dict[str, Path] = {}
    for split, candidates in SPLITS.items():
        found = [root / candidate for candidate in candidates if (root / candidate).is_dir()]
        if len(found) != 1:
            raise SystemExit(
                f"Expected exactly one folder for split {split}; "
                f"checked {', '.join(candidates)} under {root}."
            )
        split_dirs[split] = found[0]

    rows: list[dict[str, str]] = []
    hash_to_split: dict[str, tuple[str, str]] = {}
    seen_paths: set[str] = set()

    for split, split_root in split_dirs.items():
        class_counts = {"clumped": 0, "not_clumped": 0}
        for class_dir in sorted(p for p in split_root.iterdir() if p.is_dir()):
            normalized = CLASS_DIRS.get(class_dir.name.strip().lower())
            if normalized is None:
                raise SystemExit(
                    f"Unknown class folder {class_dir.name!r}. "
                    "Expected clumped or not_clumped."
                )

            label = "clumped" if normalized == "clumped" else "not_clumped"
            for image_path in sorted(class_dir.rglob("*")):
                if not image_path.is_file() or image_path.suffix.lower() not in {
                    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
                }:
                    continue

                resolved = image_path.resolve()
                if split_root.resolve() not in resolved.parents:
                    raise SystemExit(f"Image path escapes split directory: {image_path}")

                try:
                    with Image.open(resolved) as image:
                        image.verify()
                except Exception as exc:
                    raise SystemExit(f"Unreadable image {resolved}: {exc}") from exc

                digest = sha256(resolved)
                prior = hash_to_split.get(digest)
                if prior and prior[0] != split:
                    raise SystemExit(
                        f"Exact duplicate detected across splits: {prior[1]} and {resolved}. "
                        "Do not train until the source split is reconciled."
                    )
                hash_to_split[digest] = (split, str(resolved))

                rel = resolved.relative_to(root).as_posix()
                if rel in seen_paths:
                    raise SystemExit(f"Duplicate path in manifest: {rel}")
                seen_paths.add(rel)
                rows.append({
                    "image_path": rel,
                    "split": split,
                    "label": label,
                    "task": "external_agglutination_binary",
                })
                class_counts[label] += 1

        if not all(class_counts.values()):
            raise SystemExit(
                f"Split {split} has no images for one or more classes: {class_counts}"
            )

    if not rows:
        raise SystemExit("No supported images found in the dataset folders.")

    result = pd.DataFrame(rows).sort_values(["split", "label", "image_path"])
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    print({
        "manifest": str(output),
        "image_count": len(result),
        "split_counts": result.groupby(["split", "label"]).size().to_dict(),
        "unique_image_hashes": len(hash_to_split),
        "cross_split_exact_duplicates": 0,
        "task": "external_agglutination_binary",
        "note": (
            "The source Data Card declares fixed splits but does not provide specimen IDs. "
            "Exact file duplicates are checked; patient-level independence cannot be verified. "
            "This is not Widal data."
        ),
    })


if __name__ == "__main__":
    main()
