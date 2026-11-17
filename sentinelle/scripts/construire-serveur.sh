#!/bin/bash
# Empaquette le serveur Python (cerveau de Sentinelle) en un dossier autonome : dist/sentinelle-serveur/
# Utilisé par la construction de Sentinelle.app (pas besoin de Python sur le Mac de l'utilisateur).
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
RACINE="$(pwd -W 2>/dev/null || pwd)"   # sous Windows (Git Bash) : chemin au format D:/…

"$PYTHON" -m PyInstaller backend/main.py \
  --name sentinelle-serveur \
  --onedir --noconfirm --clean \
  --distpath dist --workpath build/pyinstaller --specpath build \
  --paths backend \
  --add-data "$RACINE/backend/agents:agents" \
  --collect-data tzdata \
  --collect-all claude_agent_sdk \
  --collect-all yfinance \
  --collect-all curl_cffi \
  --collect-submodules uvicorn \
  --collect-submodules apscheduler \
  --collect-all icalendar \
  --collect-all recurring_ical_events \
  --collect-all x_wr_timezone \
  --hidden-import plateforme.mac.systeme \
  --hidden-import plateforme.windows.systeme

# Le cerveau Claude (programme « claude » inclus dans le SDK) doit rester exécutable.
find dist/sentinelle-serveur -path "*claude_agent_sdk/_bundled/claude*" -type f ! -name "*.version" -exec chmod +x {} \; || true
echo "Serveur empaqueté : dist/sentinelle-serveur/"
