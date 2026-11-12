from __future__ import annotations

import argparse
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
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms
from tqdm import tqdm

LABELS = ["0", "1+", "2+", "3+", "4+"]
LABEL_TO_INDEX = {label: index for index, label in enumerate(LABELS)}
IMAGE_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class WellDataset(Dataset):
    def __init__(
        self,
        frame: pd.DataFrame,
        image_root: Path,
        transform: transforms.Compose,
    ) -> None:
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
        tensor = self.transform(image)
        label = LABEL_TO_INDEX[str(row["label"])]
        return tensor, label


def build_transforms():
    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomRotation(degrees=10),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.ColorJitter(
            brightness=0.12, contrast=0.12, saturation=0.08, hue=0.015
        ),
        transforms.CenterCrop(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return train_transform, eval_transform


def load_manifest(csv_path: Path, image_root: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, dtype={"specimen_id": str, "label": str})
    required = {"image_path", "specimen_id", "label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
    frame = frame.dropna(subset=list(required)).copy()
    frame["image_path"] = frame["image_path"].astype(str)
    frame["specimen_id"] = frame["specimen_id"].astype(str).str.strip()
    frame["label"] = frame["label"].astype(str).str.strip()

    invalid = sorted(set(frame["label"]) - set(LABELS))
    if invalid:
        raise ValueError(f"Unsupported labels: {invalid}. Allowed: {LABELS}")
    if frame.empty:
        raise ValueError("No valid rows in dataset CSV.")
    if frame["image_path"].duplicated().any():
        duplicates = int(frame["image_path"].duplicated().sum())
        raise ValueError(f"Manifest contains {duplicates} duplicate image_path rows.")

    for rel_path in frame["image_path"]:
        path = (image_root / rel_path).resolve()
        if image_root not in path.parents:
            raise ValueError(f"Image path escapes image root: {rel_path}")
        if not path.is_file():
            raise FileNotFoundError(path)

    counts = frame.groupby("label")["specimen_id"].nunique()
    missing_classes = [label for label in LABELS if label not in counts.index]
    if missing_classes:
        raise ValueError(f"Dataset is missing grades: {missing_classes}")
    too_small = {label: int(counts[label]) for label in LABELS if counts[label] < 5}
    if too_small:
        raise ValueError(
            "Need at least 5 distinct specimen groups per grade for this "
            f"5-fold starter split. Current counts: {too_small}"
        )
    return frame.reset_index(drop=True)


def make_group_splits(frame: pd.DataFrame, seed: int):
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    y = frame["label"].to_numpy()
    groups = frame["specimen_id"].to_numpy()
    folds = list(splitter.split(np.zeros(len(frame)), y, groups))

    test_indices = folds[0][1]
    validation_indices = folds[1][1]
    excluded = set(test_indices.tolist()) | set(validation_indices.tolist())
    train_indices = np.array(
        [index for index in range(len(frame)) if index not in excluded],
        dtype=int,
    )

    train = frame.iloc[train_indices].reset_index(drop=True)
    validation = frame.iloc[validation_indices].reset_index(drop=True)
    test = frame.iloc[test_indices].reset_index(drop=True)

    group_sets = [
        set(train["specimen_id"]),
        set(validation["specimen_id"]),
        set(test["specimen_id"]),
    ]
    if (
        group_sets[0] & group_sets[1]
        or group_sets[0] & group_sets[2]
        or group_sets[1] & group_sets[2]
    ):
        raise RuntimeError("Specimen leakage detected between data splits.")

    for name, subset in (("train", train), ("validation", validation), ("test", test)):
        absent = sorted(set(LABELS) - set(subset["label"]))
        if absent:
            raise ValueError(
                f"The {name} split is missing grades {absent}. "
                "Collect more independent specimens or revise the study split."
            )
    return train, validation, test


def create_model(pretrained: bool) -> nn.Module:
    weights = models.ResNet18_Weights.DEFAULT if pretrained else None
    model = models.resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, len(LABELS))
    return model


def evaluate(model, loader, device, criterion=None):
    model.eval()
    actual: list[int] = []
    predicted: list[int] = []
    scores: list[float] = []
    total_loss = 0.0
    total_items = 0

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            logits = model(images)
            if criterion is not None:
                total_loss += float(criterion(logits, labels).item()) * labels.size(0)
            probabilities = torch.softmax(logits, dim=1)
            confidence, prediction = probabilities.max(dim=1)
            actual.extend(labels.cpu().tolist())
            predicted.extend(prediction.cpu().tolist())
            scores.extend(confidence.cpu().tolist())
            total_items += labels.size(0)

    metrics = {
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "classification_report": classification_report(
            actual,
            predicted,
            labels=list(range(len(LABELS))),
            target_names=LABELS,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            actual, predicted, labels=list(range(len(LABELS)))
        ).tolist(),
    }
    if criterion is not None and total_items:
        metrics["loss"] = total_loss / total_items
    predictions = pd.DataFrame({
        "true_label": [LABELS[index] for index in actual],
        "predicted_label": [LABELS[index] for index in predicted],
        "raw_softmax_score": scores,
    })
    return metrics, predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a Widal visual-grade ResNet-18.")
    parser.add_argument("--data-csv", required=True, type=Path)
    parser.add_argument("--image-root", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-pretrained", action="store_true")
    args = parser.parse_args()

    if args.epochs < 1 or args.batch_size < 1 or args.lr <= 0:
        raise SystemExit("epochs, batch-size, and learning rate must be positive.")

    seed_everything(args.seed)
    csv_path = args.data_csv.resolve()
    image_root = args.image_root.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = load_manifest(csv_path, image_root)
    train_frame, val_frame, test_frame = make_group_splits(frame, args.seed)
    train_transform, eval_transform = build_transforms()

    train_ds = WellDataset(train_frame, image_root, train_transform)
    val_ds = WellDataset(val_frame, image_root, eval_transform)
    test_ds = WellDataset(test_frame, image_root, eval_transform)

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

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = create_model(pretrained=not args.no_pretrained).to(device)

    counts = train_frame["label"].value_counts()
    class_weights = torch.tensor(
        [len(train_frame) / (len(LABELS) * counts[label]) for label in LABELS],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3
    )

    best_macro_f1 = -1.0
    best_epoch = 0
    patience = 8
    epochs_without_improvement = 0
    checkpoint_path = out_dir / "best_model.pt"

    print(f"Device: {device}")
    print(
        "Specimen groups — "
        f"train: {train_frame['specimen_id'].nunique()}, "
        f"validation: {val_frame['specimen_id'].nunique()}, "
        f"test: {test_frame['specimen_id'].nunique()}"
    )

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        progress = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs}")
        for images, labels in progress:
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * labels.size(0)
            seen += labels.size(0)
            progress.set_postfix(loss=f"{running_loss / max(seen, 1):.4f}")

        val_metrics, _ = evaluate(model, val_loader, device, criterion)
        scheduler.step(val_metrics["macro_f1"])
        val_score = val_metrics["macro_f1"]
        print(
            f"Epoch {epoch}: train_loss={running_loss / max(seen, 1):.4f}, "
            f"val_macro_f1={val_score:.4f}, val_accuracy={val_metrics['accuracy']:.4f}"
        )

        if val_score > best_macro_f1:
            best_macro_f1 = val_score
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save({
                "model_state_dict": model.cpu().state_dict(),
                "labels": LABELS,
                "architecture": "resnet18",
                "image_size": IMAGE_SIZE,
                "mean": MEAN,
                "std": STD,
                "best_epoch": best_epoch,
                "validation_macro_f1": best_macro_f1,
                "training_scope": "visual_agglutination_grade_only",
            }, checkpoint_path)
            model.to(device)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print("Early stopping: validation macro-F1 did not improve.")
                break

    if not checkpoint_path.is_file():
        raise RuntimeError("Training did not produce a model checkpoint.")

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_metrics, test_predictions = evaluate(model, test_loader, device)

    test_predictions.insert(0, "specimen_id", test_frame["specimen_id"].tolist())
    test_predictions.insert(1, "image_path", test_frame["image_path"].tolist())
    test_metrics.update({
        "selected_epoch": best_epoch,
        "validation_macro_f1_at_selection": best_macro_f1,
        "labels": LABELS,
        "test_images": len(test_frame),
        "test_specimens": int(test_frame["specimen_id"].nunique()),
        "split_method": "StratifiedGroupKFold by specimen_id (5 folds)",
        "note": (
            "Research-only visual grading metrics. Raw softmax scores are not "
            "calibrated probabilities. Not a diagnostic-performance estimate."
        ),
    })

    (out_dir / "metrics.json").write_text(
        json.dumps(test_metrics, indent=2), encoding="utf-8"
    )
    test_predictions.to_csv(out_dir / "test_predictions.csv", index=False)

    print(json.dumps({
        "checkpoint": str(checkpoint_path),
        "metrics_file": str(out_dir / "metrics.json"),
        "test_predictions": str(out_dir / "test_predictions.csv"),
        "test_accuracy": test_metrics["accuracy"],
        "test_balanced_accuracy": test_metrics["balanced_accuracy"],
        "test_macro_f1": test_metrics["macro_f1"],
        "warning": "Visual-grade research output only; ATLM review required.",
    }, indent=2))


if __name__ == "__main__":
    main()
