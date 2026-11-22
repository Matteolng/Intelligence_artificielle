#!/usr/bin/env bash
# Installation des dépendances et lancement d'EPA Studio (Onyxia / SSP Cloud ou poste local).
# Usage : bash lancer.sh            -> port 5000 (port personnalisé par défaut des services Onyxia)
#         PORT=8501 bash lancer.sh  -> autre port
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-5000}"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
echo "EPA Studio : http://0.0.0.0:${PORT} (sur Onyxia, utilisez l'adresse du port personnalisé indiquée dans la page du service)"
exec streamlit run app.py --server.port "${PORT}" --server.address 0.0.0.0
