from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms
from torch import nn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict the visual agglutination grade of one well crop."
    )
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    args = parser.parse_args()

    checkpoint_path = args.checkpoint.resolve()
    image_path = args.image.resolve()
    if not checkpoint_path.is_file():
        raise SystemExit(f"Checkpoint not found: {checkpoint_path}")
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(
        checkpoint_path, map_location=device, weights_only=True
    )
    labels = checkpoint["labels"]
    if checkpoint.get("architecture") != "resnet18":
        raise SystemExit("Unsupported model architecture.")

    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(labels))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(int(checkpoint["image_size"])),
        transforms.ToTensor(),
        transforms.Normalize(checkpoint["mean"], checkpoint["std"]),
    ])

    with Image.open(image_path) as source:
        image = source.convert("RGB")
    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0]
        score, index = probabilities.max(dim=0)

    print(json.dumps({
        "visual_grade_prediction": labels[int(index.item())],
        "raw_softmax_score": round(float(score.item()), 4),
        "score_is_calibrated_probability": False,
        "scope": "visual_agglutination_grade_only",
        "requires_atlm_review": True,
        "clinical_diagnosis": None,
        "model_epoch": checkpoint.get("best_epoch"),
    }, indent=2))


if __name__ == "__main__":
    main()
