from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a research candidate only after explicit ATLM dataset approval."
    )
    parser.add_argument("--data-csv", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path)
    parser.add_argument("--approval-file", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/auto"))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_approval(path: Path, expected_hash: str) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"ATLM approval file not found: {path}. Refusing to train.")

    try:
        approval = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Could not read approval file: {exc}") from exc

    if approval.get("approved") is not True:
        raise SystemExit("Dataset is not marked approved. Refusing to train.")

    approved_by = str(approval.get("approved_by", "")).strip()
    if not approved_by:
        raise SystemExit("approval file must contain approved_by.")

    approved_at = str(approval.get("approved_at", "")).strip()
    try:
        timestamp = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit("approved_at must be an ISO-8601 timestamp.") from exc

    if timestamp.tzinfo is None:
        raise SystemExit("approved_at must include an explicit timezone.")
    if timestamp > datetime.now(timezone.utc):
        raise SystemExit("approved_at cannot be in the future.")

    approved_hash = str(approval.get("manifest_sha256", "")).lower().strip()
    if approved_hash != expected_hash:
        raise SystemExit(
            "The approval hash does not match dataset.csv. "
            "Any data change requires a fresh ATLM approval."
        )

    return {
        "approved_by": approved_by,
        "approved_at": timestamp.astimezone(timezone.utc).isoformat(),
        "approval_reference": str(approval.get("approval_reference", "")).strip(),
    }


def main() -> None:
    args = parse_args()
    data_csv = args.data_csv.resolve()
    image_root = args.image_root.resolve()
    approval_file = args.approval_file.resolve()
    out_dir = args.out_dir.resolve()

    if not data_csv.is_file():
        raise SystemExit(f"Dataset manifest not found: {data_csv}")
    if not image_root.is_dir():
        raise SystemExit(f"Image directory not found: {image_root}")

    manifest_hash = sha256_file(data_csv)
    approval = load_approval(approval_file, manifest_hash)

    out_dir.mkdir(parents=True, exist_ok=True)
    state_file = out_dir / "auto_training_state.json"

    if state_file.is_file() and not args.force:
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = {}
        if state.get("last_successful_manifest_sha256") == manifest_hash:
            print(json.dumps({
                "status": "skipped",
                "reason": "No new approved dataset manifest.",
                "manifest_sha256": manifest_hash,
            }, indent=2))
            return

    candidate_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + manifest_hash[:12]
    )
    candidate_dir = out_dir / candidate_id
    if candidate_dir.exists():
        raise SystemExit(f"Candidate directory already exists: {candidate_dir}")
    candidate_dir.mkdir(parents=True, exist_ok=False)

    train_script = Path(__file__).resolve().with_name("train.py")
    command = [
        sys.executable,
        str(train_script),
        "--data-csv", str(data_csv),
        "--image-root", str(image_root),
        "--out-dir", str(candidate_dir),
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--workers", str(args.workers),
        "--lr", str(args.lr),
        "--seed", str(args.seed),
    ]

    print("Starting candidate training for a newly approved dataset.")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"Training failed with exit code {result.returncode}. "
            "The previous model remains unchanged."
        )

    metrics_path = candidate_dir / "metrics.json"
    checkpoint_path = candidate_dir / "best_model.pt"
    if not metrics_path.is_file() or not checkpoint_path.is_file():
        raise SystemExit("Training did not produce both metrics and checkpoint.")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": candidate_id,
        "candidate_status": "awaiting_atlm_and_research_review",
        "automatic_production_promotion": False,
        "manifest_sha256": manifest_hash,
        "approval": approval,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(checkpoint_path),
        "metrics_file": str(metrics_path),
        "metrics": {
            "accuracy": metrics.get("accuracy"),
            "balanced_accuracy": metrics.get("balanced_accuracy"),
            "macro_f1": metrics.get("macro_f1"),
            "test_specimens": metrics.get("test_specimens"),
            "test_images": metrics.get("test_images"),
            "labels": metrics.get("labels"),
        },
        "note": (
            "Candidate only. Review the locked test report, subgroup performance, "
            "data provenance, and laboratory governance before any release."
        ),
    }

    candidate_file = candidate_dir / "candidate.json"
    candidate_file.write_text(json.dumps(candidate, indent=2), encoding="utf-8")

    state_file.write_text(
        json.dumps({
            "last_successful_manifest_sha256": manifest_hash,
            "last_candidate_id": candidate_id,
            "last_candidate_status": "awaiting_atlm_and_research_review",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "candidate_trained",
        "candidate_id": candidate_id,
        "candidate_file": str(candidate_file),
        "metrics": candidate["metrics"],
        "next_step": "ATLM/research review is required; production model was not changed.",
    }, indent=2))


if __name__ == "__main__":
    main()
