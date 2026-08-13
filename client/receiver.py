"""픽팟 관상 분석 — 결과 수신기 (상대 PC용).

분석 서버의 /api/results를 폴링해 새 결과(KioskData_*.json, analysis.json)를
지정 폴더에 실시간으로 내려받는다. 브라우저에서 서버 GUI로 분석을 돌리면
이 프로그램이 돌고 있는 PC의 대상 폴더에 파일이 자동으로 생긴다.

설정: 같은 폴더의 config.json
  {
    "server": "http://100.88.205.178:8123",   ← 분석 서버(GPU PC) 주소
    "target_dir": "C:/kiosk_project/data/readings",  ← 결과가 쌓일 폴더
    "poll_interval": 2,                        ← 폴링 주기(초)
    "flatten": false                           ← true면 배치 하위폴더 없이 저장
  }

수신 상태는 state.json에 기록되어 재시작해도 중복 다운로드하지 않는다.
"""
import json
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "state.json"

DEFAULT_CONFIG = {
    "server": "http://100.88.205.178:8123",
    "target_dir": str(BASE_DIR / "readings"),
    "poll_interval": 2,
    "flatten": False,
}


def load_json(path: Path, default: dict) -> dict:
    if path.exists():
        # utf-8-sig: 메모장/PowerShell이 넣는 BOM 허용
        return {**default, **json.loads(path.read_text(encoding="utf-8-sig"))}
    return dict(default)


def main():
    cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[설정] config.json 생성됨 — 서버 주소/대상 폴더 확인 후 재시작하세요: {CONFIG_PATH}")

    server = cfg["server"].rstrip("/")
    target = Path(cfg["target_dir"])
    target.mkdir(parents=True, exist_ok=True)
    state = load_json(STATE_PATH, {"last_batch": ""})

    print("=" * 56)
    print("  픽팟 관상 분석 — 결과 수신기")
    print(f"  서버   : {server}")
    print(f"  대상   : {target}")
    print(f"  주기   : {cfg['poll_interval']}초  (중지: Ctrl+C)")
    print("=" * 56)

    # 시작 시 서버 확인
    try:
        health = requests.get(f"{server}/health", timeout=5).json()
        print(f"[연결] 서버 OK — ollama={'on' if health.get('ollama') else 'OFF'}")
    except Exception as e:
        print(f"[경고] 서버 연결 실패: {e} — 계속 재시도합니다.")

    while True:
        try:
            batches = requests.get(
                f"{server}/api/results", params={"after": state["last_batch"]}, timeout=10
            ).json()
            for item in batches:
                batch, files = item["batch"], item["files"]
                dest = target if cfg["flatten"] else target / batch
                dest.mkdir(parents=True, exist_ok=True)
                for name in files:
                    r = requests.get(f"{server}/api/results/{batch}/{name}", timeout=15)
                    r.raise_for_status()
                    out_name = f"{batch}_{name}" if cfg["flatten"] else name
                    (dest / out_name).write_bytes(r.content)
                    print(f"[수신] {batch}/{name} → {dest / out_name}")
                state["last_batch"] = batch
                STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
        except KeyboardInterrupt:
            print("\n종료.")
            sys.exit(0)
        except Exception as e:
            print(f"[오류] {e} — {cfg['poll_interval']}초 후 재시도")
        time.sleep(cfg["poll_interval"])


if __name__ == "__main__":
    main()
