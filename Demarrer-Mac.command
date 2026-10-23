#!/bin/bash
# Double-cliquez sur ce fichier pour lancer Tradevantage sur votre Mac.
cd "$(dirname "$0")"
echo ""
echo " === Tradevantage : démarrage en local ==="
echo ""
if ! command -v node >/dev/null 2>&1; then
  echo " Node.js n'est pas installé."
  echo " Installez la version « LTS » depuis https://nodejs.org puis relancez ce fichier."
  open https://nodejs.org
  read -n 1 -s -r -p " Appuyez sur une touche pour fermer…"
  exit 1
fi
if [ ! -d node_modules ]; then
  echo " Première fois : installation des composants, 1 à 3 minutes…"
  npm install || { echo " L'installation a échoué."; read -n 1 -s -r; exit 1; }
fi
echo ""
echo " Le site va s'ouvrir dans votre navigateur : http://localhost:5173"
echo " Gardez cette fenêtre ouverte. Pour arrêter : fermez-la (ou Ctrl + C)."
echo ""
npm run dev -- --host --open
