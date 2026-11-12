from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PII_OR_KEY_COLUMNS = re.compile(
    r"(^id$|(^|_)id($|_)|patient|medical.?record|mrn|nik|"
    r"full.?name|(^|_)name($|_)|phone|mobile|email|address)",
    flags=re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research-only baseline for an inspected tabular typhoid dataset."
    )
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--target-column", required=True)
    parser.add_argument("--group-column", default=None)
    parser.add_argument("--drop-columns", default="")
    parser.add_argument("--out-dir", type=Path, default=Path("clinical-artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.csv.resolve()
    out_dir = args.out_dir.resolve()
    if not source.is_file():
        raise SystemExit(f"Dataset CSV not found: {source}")

    frame = pd.read_csv(source, low_memory=False)
    if args.target_column not in frame.columns:
        raise SystemExit(
            f"Target column {args.target_column!r} not found. "
            f"Available columns: {list(frame.columns)}"
        )
    if args.group_column and args.group_column not in frame.columns:
        raise SystemExit(f"Group column {args.group_column!r} not found.")

    frame = frame.dropna(subset=[args.target_column]).copy()
    y = frame[args.target_column].astype(str).str.strip()
    if y.nunique() < 2:
        raise SystemExit("Target must contain at least two classes.")
    if len(frame) < 100:
        raise SystemExit("At least 100 labelled rows are required for this starter baseline.")

    requested_drops = {
        value.strip() for value in args.drop_columns.split(",") if value.strip()
    }
    automatic_drops = {
        column for column in frame.columns
        if column != args.target_column and PII_OR_KEY_COLUMNS.search(str(column))
    }
    excluded = requested_drops | automatic_drops | {args.target_column}
    if args.group_column:
        excluded.add(args.group_column)

    unknown_drops = requested_drops - set(frame.columns)
    if unknown_drops:
        raise SystemExit(f"Unknown --drop-columns: {sorted(unknown_drops)}")

    feature_columns = [column for column in frame.columns if column not in excluded]
    if not feature_columns:
        raise SystemExit("No feature columns remain after identifier/target exclusions.")

    X = frame[feature_columns].copy()
    numeric_columns = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_columns = [column for column in X.columns if column not in numeric_columns]

    numeric_pipeline = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric_columns),
        ("categorical", categorical_pipeline, categorical_columns),
    ])

    model = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=500,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=args.seed,
            n_jobs=-1,
        )),
    ])

    indices = np.arange(len(frame))
    if args.group_column:
        groups = frame[args.group_column].astype(str).to_numpy()
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=args.seed)
        train_indices, test_indices = next(splitter.split(X, y, groups))
        split_method = "GroupShuffleSplit by supplied group column"
        if set(groups[train_indices]) & set(groups[test_indices]):
            raise RuntimeError("Group leakage detected.")
    else:
        train_indices, test_indices = train_test_split(
            indices,
            test_size=0.2,
            random_state=args.seed,
            stratify=y,
        )
        split_method = "stratified random split; patient-level grouping not verified"

    X_train, X_test = X.iloc[train_indices], X.iloc[test_indices]
    y_train, y_test = y.iloc[train_indices], y.iloc[test_indices]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise SystemExit("Train/test split does not contain enough target classes.")

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    labels = sorted(y.unique().tolist())

    metrics = {
        "task": "exploratory_tabular_classification_only",
        "target_column": args.target_column,
        "labels": labels,
        "rows_total": int(len(frame)),
        "rows_train": int(len(train_indices)),
        "rows_test": int(len(test_indices)),
        "features_used": feature_columns,
        "columns_excluded": sorted(excluded),
        "split_method": split_method,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
        "classification_report": classification_report(
            y_test, predictions, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "note": (
            "Research baseline only. Dataset provenance/labels require review. "
            "Not a diagnostic-performance estimate; no patient-level diagnosis "
            "or treatment recommendation is produced."
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "clinical_baseline.joblib")
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, default=str), encoding="utf-8"
    )
    pd.DataFrame({
        "actual_label": y_test.to_numpy(),
        "predicted_label": predictions,
    }).to_csv(out_dir / "test_predictions.csv", index=False)

    print(json.dumps({
        "model": str(out_dir / "clinical_baseline.joblib"),
        "metrics": str(out_dir / "metrics.json"),
        "accuracy": metrics["accuracy"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "macro_f1": metrics["macro_f1"],
        "warning": "Exploratory research only; not a medical diagnostic model.",
    }, indent=2))


if __name__ == "__main__":
    main()
