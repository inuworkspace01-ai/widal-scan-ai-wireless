from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert the public BloodyWell metadata into a separate binary "
            "agglutination benchmark manifest. This is NOT a Widal dataset."
        )
    )
    parser.add_argument("--markup", required=True, type=Path, help="Path to BloodyWell test_markup.json")
    parser.add_argument("--image-root", required=True, type=Path, help="Directory containing the downloaded PNG files")
    parser.add_argument("--out", type=Path, default=Path("bloodywell_external_benchmark.csv"))
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="Write manifest rows even if image files are not present yet.",
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

        gt = item.get("gt_result")
        if gt not in (0, 1):
            raise SystemExit(f"Unexpected gt_result for {filename}: {gt!r}")

        file_path = Path(str(filename))
        if file_path.name != str(filename) or file_path.is_absolute():
            raise SystemExit(f"Unsafe image filename in markup: {filename}")

        prefix = file_path.stem.split("_", 1)[0]
        if not prefix.isdigit():
            raise SystemExit(f"Could not derive sample group from filename: {filename}")

        resolved_image = (image_root / file_path.name).resolve()
        if image_root not in resolved_image.parents:
            raise SystemExit(f"Image path escapes image root: {filename}")
        exists = resolved_image.is_file()
        if not exists:
            missing.append(str(filename))
            if not args.allow_missing_images:
                continue

        rows.append({
            "image_path": str(file_path.name),
            "sample_group_id": prefix,
            "reagent": str(item.get("reagent", "")),
            "source_row_idx": item.get("row_idx"),
            "source_col_idx": item.get("col_idx"),
            "binary_agglutination_gt": int(gt),
            "task": "external_agglutination_binary",
            "source_dataset": "BloodyWell",
            "image_exists": exists,
            "not_widal": True,
        })

    if not rows:
        raise SystemExit(
            "No image rows were written. Place the 529-image public test subset "
            "in --image-root or use --allow-missing-images to create a metadata-only manifest."
        )

    result = pd.DataFrame(rows).sort_values(["sample_group_id", "source_col_idx", "image_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)

    summary = {
        "manifest": str(out_path),
        "rows_written": int(len(result)),
        "unique_sample_groups": int(result["sample_group_id"].nunique()),
        "missing_images": len(missing),
        "label_counts": {
            str(label): int(count)
            for label, count in result["binary_agglutination_gt"].value_counts().sort_index().items()
        },
        "task": "external_agglutination_binary",
        "warning": (
            "This is a blood-grouping ABO/Rh/Kell agglutination benchmark. "
            "It must never be used as Widal 0/1+/2+/3+/4+ labels."
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
