from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from prepare_binary_manifest import audit_dataset


class PrepareBinaryManifestTests(unittest.TestCase):
    def write_image(self, path: Path, color: tuple[int, int, int]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (224, 224), color).save(path, format="JPEG", quality=90)

    def test_duplicate_and_conflicting_labels_are_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "train/clumped/A_1_AB-10-_jpg.rf.one.jpg"
            self.write_image(first, (200, 10, 10))
            duplicate = root / "train/clumped/A_2_AB-10-_jpg.rf.two.jpg"
            duplicate.parent.mkdir(parents=True, exist_ok=True)
            duplicate.write_bytes(first.read_bytes())

            conflict_positive = root / "train/clumped/conflict-positive.jpg"
            self.write_image(conflict_positive, (180, 80, 20))
            conflict_negative = root / "train/not_clumped/conflict.jpg"
            conflict_negative.parent.mkdir(parents=True, exist_ok=True)
            conflict_negative.write_bytes(conflict_positive.read_bytes())

            self.write_image(root / "train/not_clumped/B_3_B-4-_jpg.rf.three.jpg", (10, 200, 10))
            self.write_image(root / "valid/clumped/A_4_AB-10-_jpg.rf.four.jpg", (10, 10, 200))
            self.write_image(root / "valid/not_clumped/B_5_B-5-_jpg.rf.five.jpg", (200, 200, 10))
            self.write_image(root / "test/clumped/A_6_A-6-_jpg.rf.six.jpg", (200, 10, 200))
            self.write_image(root / "test/not_clumped/B_7_B-7-_jpg.rf.seven.jpg", (10, 200, 200))

            clean, duplicate_rows, report = audit_dataset(root)
            self.assertEqual(len(clean), 6)
            self.assertEqual(len({row["sha256"] for row in clean}), 6)
            self.assertEqual(report["duplicate_summary"]["same_split_extra_files_removed"], 1)
            self.assertEqual(report["duplicate_summary"]["conflicting_label_files"], 2)
            self.assertEqual(report["potential_filename_group_tokens_crossing_splits"], 1)
            self.assertEqual(len(duplicate_rows), 4)

    def test_cross_split_exact_duplicate_excludes_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train_image = root / "train/clumped/train.jpg"
            self.write_image(train_image, (120, 40, 40))
            test_image = root / "test/clumped/test.jpg"
            test_image.parent.mkdir(parents=True, exist_ok=True)
            test_image.write_bytes(train_image.read_bytes())
            self.write_image(root / "train/not_clumped/train-negative.jpg", (40, 120, 40))
            self.write_image(root / "valid/clumped/val-positive.jpg", (40, 40, 120))
            self.write_image(root / "valid/not_clumped/val-negative.jpg", (120, 120, 40))
            self.write_image(root / "test/not_clumped/test-negative.jpg", (40, 120, 120))

            clean, _, report = audit_dataset(root)
            self.assertEqual(report["duplicate_summary"]["cross_split_groups"], 1)
            paths = {row["image_path"] for row in clean}
            self.assertNotIn("train/clumped/train.jpg", paths)
            self.assertNotIn("test/clumped/test.jpg", paths)


if __name__ == "__main__":
    unittest.main()
