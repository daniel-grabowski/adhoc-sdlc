#!/bin/bash
# Instalacja umiejętności (skills) adhoc-sdlc dla Antigravity
set -e

# Ustalenie absolutnej ścieżki do katalogu ze skillami
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/plugins/adhoc-sdlc/skills"

CONFIG_DIR="$HOME/.gemini/config"
SKILLS_JSON="$CONFIG_DIR/skills.json"

echo "⚙️ Konfiguracja Antigravity..."
mkdir -p "$CONFIG_DIR"

# Używamy pythona do bezpiecznej modyfikacji JSON-a, żeby nie polegać na jq
python3 -c "
import json, os

file_path = '$SKILLS_JSON'
skills_dir = '$SKILLS_DIR'

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {'entries': []}

if 'entries' not in data:
    data['entries'] = []

# Dodaj tylko jeśli jeszcze nie istnieje
if not any(e.get('path') == skills_dir for e in data['entries']):
    data['entries'].append({'path': skills_dir})
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'✅ Zarejestrowano pomyślnie ścieżkę: {skills_dir}')
    print(f'📄 Plik zaktualizowany: {file_path}')
else:
    print(f'ℹ️ Wtyczka jest już zainstalowana (ścieżka istnieje w {file_path}).')
"

echo "🚀 Gotowe! Narzędzie Antigravity powinno teraz automatycznie wykrywać umiejętności: adhoc-sdlc, cove oraz temper."
