"""CLI 테스트: python tools/analyze_cli.py <이미지> [--persona KIND,T,ROAST]"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from app.pipeline import analyze_image
from app import llm

parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("--persona", default="")
args = parser.parse_args()

img = cv2.imread(args.image)
if img is None:
    sys.exit(f"이미지를 열 수 없음: {args.image}")

t0 = time.time()
analysis = analyze_image(img)
print(f"\n=== 공통 분석 ({time.time() - t0:.2f}s) ===")
print(json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2))

for p in [x.strip().upper() for x in args.persona.split(",") if x.strip()]:
    t0 = time.time()
    result = llm.generate_persona(p, analysis.model_dump())
    print(f"\n=== 페르소나 {p} ({time.time() - t0:.1f}s) ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
