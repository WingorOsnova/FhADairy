#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="dist/Fachabi Diary.app"
VERSION="${VERSION:-$(awk -F '"' '/^version = / { print $2; exit }' pyproject.toml)}"
ARCH="${ARCH:-$(uname -m)}"
RELEASE_DIR="dist/release"
BASE_NAME="Fachabi-Diary-${VERSION}-macOS-${ARCH}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found. Building first..."
  bash scripts/build_macos_app.sh
fi

mkdir -p "$RELEASE_DIR"

ZIP_PATH="$RELEASE_DIR/${BASE_NAME}.zip"
DMG_PATH="$RELEASE_DIR/${BASE_NAME}.dmg"

rm -f "$ZIP_PATH" "$DMG_PATH"

ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
hdiutil create \
  -volname "Fachabi Diary" \
  -srcfolder "$APP_PATH" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "Created:"
echo "  $ZIP_PATH"
echo "  $DMG_PATH"
