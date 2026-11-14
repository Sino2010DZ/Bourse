#!/bin/bash
# Sentinelle — lancement sur Mac (double-cliquez sur ce fichier).
# La première fois, il installe ce qu'il faut (quelques minutes). Ensuite, c'est rapide.
cd "$(dirname "$0")" || exit 1

manque() {
  echo ""
  echo "❌ Il manque : $1"
  echo "   Tapez dans le Terminal :  $2"
  echo "   Puis relancez ce fichier."
  echo ""
  read -r -p "Appuyez sur Entrée pour fermer…"
  exit 1
}

# 1. Les outils nécessaires
PYTHON=""
for p in python3.13 python3.12 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; exit(0 if sys.version_info >= (3, 12) else 1)'; then
    PYTHON="$p"; break
  fi
done
[ -z "$PYTHON" ] && manque "Python 3.12 ou plus récent" "brew install python@3.12"
command -v npm   >/dev/null 2>&1 || manque "Node.js" "brew install node"
command -v cargo >/dev/null 2>&1 || [ -x "$HOME/.cargo/bin/cargo" ] || \
  manque "Rust" "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
export PATH="$HOME/.cargo/bin:$PATH"

# 2. La clé API
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📝 J'ai créé le fichier .env. Ouvrez-le et collez votre clé API après ANTHROPIC_API_KEY="
  open -e .env
fi

# 3. Le cerveau (Python)
if [ ! -x .venv/bin/python ]; then
  echo "⏳ Installation du cerveau Python…"
  "$PYTHON" -m venv .venv || exit 1
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r backend/requirements.txt || exit 1

# 4. La fenêtre (Tauri)
cd app || exit 1
if [ ! -d node_modules ]; then
  echo "⏳ Installation de la fenêtre…"
  npm install --silent || exit 1
fi
echo "🚀 Ouverture de Sentinelle… (la toute première fois : 2 à 5 minutes de compilation)"
npm run dev
