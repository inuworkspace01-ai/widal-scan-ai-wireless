from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm


LABELS = ["clumped", "not_clumped"]
LABEL_TO_INDEX = {label: index for index, label in enumerate(LABELS)}
IMAGE_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
TASK = "external_agglutination_binary"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class BinaryAgglutinationDataset(Dataset):
    def __init__(self, frame: pd.DataFrame, image_root: Path, transform):
        self.frame = frame.reset_index(drop=True)
        self.image_root = image_root
        self.transform = transform

    def __len__(self) -> int:
        return len(self.frame)

    def __getitem__(self, index: int):
        row = self.frame.iloc[index]
        image_path = (self.image_root / str(row["image_path"])).resolve()
        if self.image_root not in image_path.parents:
            raise ValueError(f"Image path escapes image root: {row['image_path']}")
        with Image.open(image_path) as source:
            image = source.convert("RGB")
        return self.transform(image), LABEL_TO_INDEX[str(row["label"])]


def read_manifest(path: Path, image_root: Path) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(
        path,
        dtype={
            "image_path": str,
            "split": str,
            "label": str,
            "sha256": str,
            "potential_group_token": str,
            "task": str,
        },
    )
    required = {"image_path", "split", "label", "sha256", "task"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Manifest missing required columns: {sorted(missing)}")

    frame = frame.dropna(subset=list(required)).copy()
    frame["split"] = frame["split"].str.strip().str.lower()
    frame["label"] = frame["label"].str.strip().str.lower()
    frame["task"] = frame["task"].str.strip()
    frame["sha256"] = frame["sha256"].str.strip().str.lower()

    if set(frame["task"]) != {TASK}:
        raise ValueError(f"Manifest task must be exactly {TASK!r}; do not mix it with Widal labels.")
    if set(frame["split"]) != {"train", "validation", "test"}:
        raise ValueError("Manifest must contain exactly train, validation and test splits.")
    if set(frame["label"]) != set(LABELS):
        raise ValueError(f"Manifest labels must be exactly {LABELS}.")
    if frame["image_path"].duplicated().any():
        raise ValueError("Duplicate image_path in manifest.")
    if frame["sha256"].duplicated().any():
        raise ValueError("Exact duplicate hashes remain in the manifest; rerun prepare_binary_manifest.py.")

    root = image_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Image root does not exist: {root}")

    for row in frame.itertuples(index=False):
        resolved = (root / row.image_path).resolve()
        if root not in resolved.parents:
            raise ValueError(f"Image path escapes image root: {row.image_path}")
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        if sha256_file(resolved) != row.sha256:
            raise ValueError(f"Image checksum mismatch for {row.image_path}; rerun the audit and do not train.")

    for split in ("train", "validation", "test"):
        part = frame.loc[frame["split"] == split]
        if set(part["label"]) != set(LABELS):
            raise ValueError(f"Split {split} must contain both binary classes.")

    group_audit = {"tokens_crossing_splits": 0, "example_tokens": []}
    if "potential_group_token" in frame.columns:
        token_frame = frame.loc[frame["potential_group_token"].fillna("").str.len() > 0]
        for token, group in token_frame.groupby("potential_group_token"):
            if group["split"].nunique() > 1:
                group_audit["tokens_crossing_splits"] += 1
                if len(group_audit["example_tokens"]) < 20:
                    group_audit["example_tokens"].append(str(token))
    group_audit["semantics"] = (
        "unverified filename tokens; they may or may not identify a specimen/sample. "
        "No patient/specimen-level independence claim is permitted."
    )
    group_audit["evaluation_scope"] = "image-level only"
    return frame, group_audit


def make_transforms():
    train_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomRotation(degrees=8),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.08, contrast=0.08, saturation=0.05),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return train_transform, eval_transform


def evaluate(model, loader, device):
    model.eval()
    actual: list[int] = []
    predicted: list[int] = []
    with torch.no_grad():
        for images, labels in loader:
            logits = model(images.to(device))
            predicted.extend(logits.argmax(dim=1).cpu().tolist())
            actual.extend(labels.tolist())

    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "classification_report": classification_report(
            actual,
            predicted,
            labels=[0, 1],
            target_names=LABELS,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=[0, 1]).tolist(),
        "class_support": {
            label: int(sum(value == LABEL_TO_INDEX[label] for value in actual))
            for label in LABELS
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Train a separate binary blood-agglutination benchmark model. "
            "This is not a Widal reaction-grade model or clinical diagnostic model."
        )
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/external_binary"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-pretrained", action="store_true")
    parser.add_argument(
        "--confirm-dataset-rights-reviewed",
        action="store_true",
        help="Confirm that exact dataset reuse/redistribution rights have been independently verified.",
    )
    parser.add_argument(
        "--acknowledge-image-level-split-only",
        action="store_true",
        help="Acknowledge that specimen-level split independence is unverified; metrics are image-level only.",
    )
    args = parser.parse_args()

    if not args.confirm_dataset_rights_reviewed:
        raise SystemExit(
            "Training blocked: verify the exact dataset licence and reuse rights, "
            "then pass --confirm-dataset-rights-reviewed."
        )
    if not args.acknowledge_image_level_split_only:
        raise SystemExit(
            "Training blocked: specimen-level independence is unknown. "
            "After reviewing this limitation, pass --acknowledge-image-level-split-only for an image-level experiment."
        )
    if args.epochs < 1 or args.batch_size < 1 or args.lr <= 0:
        raise SystemExit("epochs, batch-size and learning rate must be positive.")

    seed_everything(args.seed)
    manifest_path = args.manifest.resolve()
    image_root = args.image_root.resolve()
    out_dir = args.out_dir.resolve()
    if not manifest_path.is_file() or not image_root.is_dir():
        raise SystemExit("Manifest or image root does not exist.")

    frame, group_audit = read_manifest(manifest_path, image_root)
    train_frame = frame.loc[frame["split"] == "train"].reset_index(drop=True)
    val_frame = frame.loc[frame["split"] == "validation"].reset_index(drop=True)
    test_frame = frame.loc[frame["split"] == "test"].reset_index(drop=True)

    train_tf, eval_tf = make_transforms()
    train_ds = BinaryAgglutinationDataset(train_frame, image_root, train_tf)
    val_ds = BinaryAgglutinationDataset(val_frame, image_root, eval_tf)
    test_ds = BinaryAgglutinationDataset(test_frame, image_root, eval_tf)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=args.workers, pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=torch.cuda.is_available(),
    )
    test_loader = DataLoader(
        test_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=torch.cuda.is_available(),
    )

    weights = None if args.no_pretrained else models.MobileNet_V3_Small_Weights.DEFAULT
    model = models.mobilenet_v3_small(weights=weights)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 2)
    model.to(device)

    counts = train_frame["label"].value_counts()
    class_weights = torch.tensor(
        [len(train_frame) / (2 * counts[label]) for label in LABELS],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "best_external_binary.pt"
    manifest_hash = sha256_file(manifest_path)
    best_score, best_epoch, stagnant = -1.0, 0, 0
    patience = 7

    print(f"Device: {device}; task={TASK}; NOT WIDAL; evaluation=image-level only")
    print(
        f"Split sizes: train={len(train_ds)}, validation={len(val_ds)}, test={len(test_ds)}; "
        f"unverified filename tokens crossing splits={group_audit['tokens_crossing_splits']}"
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss, seen = 0.0, 0
        progress = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs}")
        for images, labels in progress:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * labels.size(0)
            seen += labels.size(0)
            progress.set_postfix(loss=f"{running_loss / max(seen, 1):.4f}")

        val_metrics = evaluate(model, val_loader, device)
        scheduler.step(val_metrics["macro_f1"])
        score = val_metrics["macro_f1"]
        print(
            f"Epoch {epoch}: train_loss={running_loss / max(seen, 1):.4f}, "
            f"val_macro_f1={score:.4f}"
        )

        if score > best_score:
            best_score, best_epoch, stagnant = score, epoch, 0
            torch.save(
                {
                    "model_state_dict": model.cpu().state_dict(),
                    "labels": LABELS,
                    "architecture": "mobilenet_v3_small",
                    "image_size": IMAGE_SIZE,
                    "mean": MEAN,
                    "std": STD,
                    "best_epoch": best_epoch,
                    "validation_macro_f1": best_score,
                    "manifest_sha256": manifest_hash,
                    "task": TASK,
                    "not_widal": True,
                    "evaluation_scope": "image-level only; specimen-level independence not verified",
                },
                checkpoint_path,
            )
            model.to(device)
        else:
            stagnant += 1
            if stagnant >= patience:
                print("Early stopping based on validation macro-F1.")
                break

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_metrics = evaluate(model, test_loader, device)
    test_metrics.update({
        "labels": LABELS,
        "best_epoch": best_epoch,
        "test_images": len(test_ds),
        "split_source": "fixed source dataset split (train/validation/test)",
        "filename_group_audit": group_audit,
        "patient_level_independence": "not verified; no documented specimen IDs",
        "evaluation_scope": "image-level only",
        "task": TASK,
        "not_widal": True,
        "manifest_sha256": manifest_hash,
        "dataset_rights_confirmed_by_operator": True,
        "note": (
            "External binary blood-group/agglutination benchmark only. Metrics do not transfer "
            "to Widal reaction grades, patient-level generalization, or clinical diagnosis."
        ),
    })
    (out_dir / "metrics.json").write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")
    print(json.dumps({
        "checkpoint": str(checkpoint_path),
        "metrics": test_metrics,
        "warning": "NOT a Widal model. Do not use in clinical workflows.",
    }, indent=2))


if __name__ == "__main__":
    main()
