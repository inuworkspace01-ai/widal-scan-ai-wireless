from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = False
ALLOWED_LABELS = {"0", "1+", "2+", "3+", "4+"}
REQUIRED_COLUMNS = {
    "image_path", "specimen_id", "well_id",
    "x", "y", "width", "height", "label",
}


def safe_name(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_")
    return text[:60] or "item"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crop individually annotated Widal slide reaction wells."
    )
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    annotations_path = args.annotations.resolve()
    image_root = args.image_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(annotations_path, dtype={"specimen_id": str, "well_id": str})
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {', '.join(sorted(missing))}")
    if df.empty:
        raise SystemExit("The annotation file is empty.")

    rows: list[dict[str, str]] = []
    errors: list[str] = []

    for index, row in df.iterrows():
        try:
            label = str(row["label"]).strip()
            if label not in ALLOWED_LABELS:
                raise ValueError(f"invalid label {label!r}")

            specimen_id = str(row["specimen_id"]).strip()
            well_id = str(row["well_id"]).strip()
            if not specimen_id or specimen_id.lower() == "nan":
                raise ValueError("specimen_id is required")
            if not well_id or well_id.lower() == "nan":
                raise ValueError("well_id is required")

            rel_path = Path(str(row["image_path"]))
            source_path = (image_root / rel_path).resolve()
            if image_root not in source_path.parents:
                raise ValueError("image_path must stay inside --image-root")
            if not source_path.is_file():
                raise FileNotFoundError(source_path)

            x = int(row["x"])
            y = int(row["y"])
            width = int(row["width"])
            height = int(row["height"])
            if min(x, y) < 0 or min(width, height) <= 0:
                raise ValueError("crop coordinates and dimensions must be positive")

            with Image.open(source_path) as source:
                image = source.convert("RGB")
                right, bottom = x + width, y + height
                if right > image.width or bottom > image.height:
                    raise ValueError(
                        f"crop ({x},{y},{width},{height}) exceeds "
                        f"image size {image.width}x{image.height}"
                    )
                crop = image.crop((x, y, right, bottom))

            filename = (
                f"{safe_name(specimen_id)}_{safe_name(well_id)}_"
                f"{index:06d}.jpg"
            )
            crop_path = output_root / filename
            crop.save(crop_path, format="JPEG", quality=95, subsampling=0)

            rows.append({
                "image_path": filename,
                "specimen_id": specimen_id,
                "label": label,
            })
        except Exception as exc:
            errors.append(f"row {index + 2}: {type(exc).__name__}: {exc}")

    if errors:
        print("Some annotations could not be processed:")
        for error in errors[:50]:
            print(f" - {error}")
        if len(errors) > 50:
            print(f" ... and {len(errors) - 50} more")
        raise SystemExit("No dataset manifest written; fix annotation errors first.")

    manifest_path = output_root / "dataset.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    print(f"Created {len(rows)} crops.")
    print(f"Dataset manifest: {manifest_path}")


if __name__ == "__main__":
    main()
