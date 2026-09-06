#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${MAMBAFLOW_VERSION:-0.2.0}"
ARCH="arm64"

.venv/bin/python -m PyInstaller \
  --noconfirm \
  --windowed \
  --name MambaFlow \
  --osx-bundle-identifier com.blackmamba.mambaflow \
  --add-data 'apps/webui/templates:apps/webui/templates' \
  --add-data 'apps/webui/static:apps/webui/static' \
  --add-data 'config/config.yml:config' \
  --collect-all yt_dlp \
  --collect-all uvicorn \
  --hidden-import apps.webui.main \
  launcher.py

if [[ "${1:-}" == "--dmg" ]]; then
  STAGE="$(mktemp -d)"
  trap 'rm -rf "$STAGE"' EXIT

  ditto dist/MambaFlow.app "$STAGE/MambaFlow.app"
  ln -s /Applications "$STAGE/Applications"

  VERSIONED_DMG="dist/MambaFlow-${VERSION}-${ARCH}.dmg"
  STABLE_DMG="dist/MambaFlow-latest-${ARCH}.dmg"

  hdiutil create \
    -volname MambaFlow \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$VERSIONED_DMG"

  # Stable filename for QR codes, release pages and permanent download links.
  cp "$VERSIONED_DMG" "$STABLE_DMG"

  echo "Built $VERSIONED_DMG"
  echo "Stable release alias: $STABLE_DMG"
fi
