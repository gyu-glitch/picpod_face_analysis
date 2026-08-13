"""celeb_comparison.html에 임베드된 base64 얼굴 사진을 tests/faces/로 추출."""
import base64
import re
import sys
from pathlib import Path

HTML = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\Downloads\celeb_comparison.html")
OUT = Path(__file__).resolve().parent.parent / "tests" / "faces"
OUT.mkdir(parents=True, exist_ok=True)

html = HTML.read_text(encoding="utf-8")
pattern = re.compile(r'src="data:image/jpeg;base64,([^"]+)"\s+alt="([^"]+)"')
count = 0
for b64, name in pattern.findall(html):
    (OUT / name).write_bytes(base64.b64decode(b64))
    count += 1
    print(f"저장: {name}")
print(f"총 {count}장 → {OUT}")
