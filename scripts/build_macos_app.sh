#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$ROOT_DIR/build/pyinstaller-config}"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

PYTHON_BIN="${PYTHON:-venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python venv not found: $PYTHON_BIN" >&2
  echo "Run: python3 -m venv venv && venv/bin/python -m pip install -e '.[dev]'" >&2
  exit 1
fi

if [[ ! -f "assets/formblatt9.pdf" ]]; then
  echo "Missing PDF template: assets/formblatt9.pdf" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
  echo "PyInstaller is not installed." >&2
  echo "Run: $PYTHON_BIN -m pip install -e '.[dev]'" >&2
  exit 1
fi

ICON_ARGS=()
APP_ICON_ICNS="assets/icons/app-icon-blue.icns"
ICON_PNG="assets/icons/app-icon-blue.png"
ICON_ICNS="build/app-icon.icns"
ICONSET="build/app-icon.iconset"
if [[ -f "$APP_ICON_ICNS" ]]; then
  ICON_ARGS=(--icon "$APP_ICON_ICNS")
elif [[ -f "$ICON_PNG" ]] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  sips -z 16 16 "$ICON_PNG" --out "$ICONSET/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_PNG" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_PNG" --out "$ICONSET/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
  if iconutil -c icns "$ICONSET" -o "$ICON_ICNS"; then
    ICON_ARGS=(--icon "$ICON_ICNS")
  else
    echo "Icon generation failed; continuing without custom app icon." >&2
  fi
fi

PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name "Fachabi Diary"
)
if [[ ${#ICON_ARGS[@]} -gt 0 ]]; then
  PYINSTALLER_ARGS+=("${ICON_ARGS[@]}")
fi
PYINSTALLER_ARGS+=(
  --add-data "assets/formblatt9.pdf:assets"
  --add-data "assets/icons:assets/icons"
  scripts/pyinstaller_entry.py
)

"$PYTHON_BIN" -m PyInstaller "${PYINSTALLER_ARGS[@]}"

echo "Built: dist/Fachabi Diary.app"
