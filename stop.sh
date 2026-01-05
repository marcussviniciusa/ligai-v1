#!/bin/bash
#
# LigAI - Script de parada
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Parando LigAI..."
docker compose down

echo "LigAI parado."
