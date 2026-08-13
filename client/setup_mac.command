#!/bin/bash
# ============================================================
#  PicPod face-analysis client setup (macOS)
#  Just double-click. If Gatekeeper blocks it (first time only):
#  System Settings -> Privacy & Security -> "Open Anyway".
# ============================================================
set -e
cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  PicPod face-analysis client setup (macOS)"
echo "============================================================"
echo ""

# ---------- 1. python3 ----------
echo "[1/4] Checking python3..."
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import sys" >/dev/null 2>&1; then
  echo "python3 is missing - opening the installer dialog..."
  xcode-select --install 2>/dev/null || true
  echo ""
  echo "  A window should appear. Click [Install] and wait for it to finish,"
  echo "  then double-click this file again."
  read -r -p "Press Enter to close..."
  exit 1
fi
echo "      OK ($(python3 --version))"

# ---------- 2. venv + packages ----------
echo "[2/4] Installing packages (venv + requests)..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade --quiet pip requests
echo "      OK"

# ---------- 3. Config + result folder ----------
echo "[3/4] Config"
mkdir -p result
if [ -f config.json ]; then
  echo "      config.json already exists - keeping it."
else
  cat > config.json <<'EOF'
{ "server": "http://100.88.205.178:8123", "poll_interval": 2, "flatten": false, "target_dir": "" }
EOF
  echo "      Default config written. Edit config.json to change server."
fi

# ---------- 4. Shortcuts + autostart ----------
echo "[4/4] Shortcuts + autostart..."
chmod +x run_mac.command setup_mac.command
# 이 setup은 사용자가 Gatekeeper에서 직접 승인해 실행된 것 —
# 같은 폴더의 나머지 파일(run_mac 등)이 또 차단되지 않게 격리 속성 해제
xattr -dr com.apple.quarantine . 2>/dev/null || true

# Desktop shortcuts
ln -sf "$(pwd)/run_mac.command" "$HOME/Desktop/PicPod Result Receiver.command"
SERVER_URL=$(.venv/bin/python -c "import json;print(json.load(open('config.json'))['server'])")
cat > "$HOME/Desktop/PicPod Analysis GUI.webloc" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>URL</key><string>${SERVER_URL}</string></dict></plist>
EOF

# Autostart (LaunchAgent) — re-run this setup if you move the folder
PLIST="$HOME/Library/LaunchAgents/com.picpod.receiver.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.picpod.receiver</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(pwd)/.venv/bin/python</string>
    <string>$(pwd)/receiver.py</string>
  </array>
  <key>WorkingDirectory</key><string>$(pwd)</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>StandardOutPath</key><string>$(pwd)/receiver.log</string>
  <key>StandardErrorPath</key><string>$(pwd)/receiver.log</string>
</dict>
</plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "      OK"

echo ""
echo "============================================================"
echo "  Done. Receiver is running in the background (autostart on)."
echo "  - [PicPod Result Receiver] on Desktop : run receiver in Terminal"
echo "  - [PicPod Analysis GUI] on Desktop    : open analysis page"
echo "  - Results are saved into:  $(pwd)/result"
echo "  * If you move this folder, run setup_mac.command again."
echo "============================================================"
