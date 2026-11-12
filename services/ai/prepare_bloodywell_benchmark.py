from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a metadata manifest for the public BloodyWell test subset. "
            "This is an external ABO/Rh/Kell benchmark, NOT Widal training data."
        )
    )
    parser.add_argument("--markup", required=True, type=Path, help="Path to BloodyWell test_markup.json")
    parser.add_argument("--image-root", required=True, type=Path, help="Directory containing downloaded PNG files")
    parser.add_argument("--out", type=Path, default=Path("bloodywell_external_benchmark.csv"))
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="Write metadata-only rows when files are absent. Such rows cannot be used for training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markup_path = args.markup.resolve()
    image_root = args.image_root.resolve()
    out_path = args.out.resolve()

    if not markup_path.is_file():
        raise SystemExit(f"Markup file not found: {markup_path}")
    if not image_root.is_dir():
        raise SystemExit(f"Image folder not found: {image_root}")

    try:
        metadata = json.loads(markup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not parse markup JSON: {exc}") from exc

    if not isinstance(metadata, dict) or not metadata:
        raise SystemExit("Markup must be a non-empty JSON object.")

    rows: list[dict[str, object]] = []
    missing: list[str] = []

    for filename, item in metadata.items():
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid annotation for {filename}")

        ground_truth = item.get("gt_result")
        if ground_truth not in (0, 1):
            raise SystemExit(f"Unexpected gt_result for {filename}: {ground_truth!r}")

        image_name = Path(str(filename))
        if image_name.name != str(filename) or image_name.is_absolute():
            raise SystemExit(f"Unsafe image filename in markup: {filename}")

        image_path = (image_root / image_name.name).resolve()
        if image_root not in image_path.parents:
            raise SystemExit(f"Image path escapes image root: {filename}")

        exists = image_path.is_file()
        if not exists:
            missing.append(str(filename))
            if not args.allow_missing_images:
                continue

        rows.append({
            "image_path": image_name.name,
            "reagent": str(item.get("reagent", "")),
            "plate_row_idx": item.get("row_idx"),
            "plate_col_idx": item.get("col_idx"),
            "binary_agglutination_gt": int(ground_truth),
            "task": "external_agglutination_binary",
            "source_dataset": "BloodyWell",
            "image_exists": exists,
            "specimen_group_id": "",
            "grouping_verified": False,
            "not_widal": True,
        })

    if missing and not args.allow_missing_images:
        sample = ", ".join(missing[:10])
        raise SystemExit(
            f"{len(missing)} referenced images are missing (examples: {sample}). "
            "No manifest was written. Restore the complete 529-image subset or use "
            "--allow-missing-images for a metadata-only catalogue."
        )

    if not rows:
        raise SystemExit("No metadata rows were written.")

    result = pd.DataFrame(rows).sort_values(
        ["plate_row_idx", "plate_col_idx", "image_path"],
        kind="stable",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)

    summary = {
        "manifest": str(out_path),
        "rows_written": int(len(result)),
        "images_present": int(result["image_exists"].sum()),
        "images_missing": len(missing),
        "binary_label_counts": {
            str(label): int(count)
            for label, count in result["binary_agglutination_gt"].value_counts().sort_index().items()
        },
        "task": "external_agglutination_binary",
        "specimen_grouping": "not verified from the published public markup",
        "warning": (
            "ABO/Rh/Kell blood-grouping benchmark only. Do not train or evaluate "
            "Widal 0/1+/2+/3+/4+ classification with these labels."
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
