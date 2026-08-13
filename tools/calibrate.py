"""테스트 사진 전체의 raw feature 분포 덤프 — 기준선/임계값 캘리브레이션용."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from app.landmarks import extract_landmarks
from app.features import compute_features

faces_dir = Path(__file__).resolve().parent.parent / "tests" / "faces"
rows = {}
for img_path in sorted(faces_dir.glob("*.jpg")):
    img = cv2.imread(str(img_path))
    pts, _ = extract_landmarks(img)
    rows[img_path.stem] = compute_features(pts)

keys = list(next(iter(rows.values())).keys())
name_w = max(len(n) for n in rows)
print(f"{'feature':<18}" + "".join(f"{n[:12]:>14}" for n in rows) + f"{'mean':>10}{'std':>9}")
for k in keys:
    vals = [rows[n][k] for n in rows]
    print(f"{k:<18}" + "".join(f"{v:>14.4f}" for v in vals) + f"{np.mean(vals):>10.4f}{np.std(vals):>9.4f}")
