#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m PyInstaller --noconfirm --windowed --name MambaFlow --osx-bundle-identifier com.blackmamba.mambaflow --add-data 'apps/webui/templates:apps/webui/templates' --add-data 'apps/webui/static:apps/webui/static' --add-data 'config/config.yml:config' --collect-all yt_dlp --collect-all uvicorn --hidden-import apps.webui.main launcher.py
if [[ "${1:-}" == "--dmg" ]]; then
  STAGE="$(mktemp -d)"
  ditto dist/MambaFlow.app "$STAGE/MambaFlow.app"
  ln -s /Applications "$STAGE/Applications"
  hdiutil create -volname MambaFlow -srcfolder "$STAGE" -ov -format UDZO dist/MambaFlow-0.2.0-arm64.dmg
fi
