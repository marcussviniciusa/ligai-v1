#!/bin/bash
#
# LigAI - Script de inicialização
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          LigAI - Iniciando           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[!] Arquivo .env não encontrado. Criando a partir do exemplo...${NC}"
    cp .env.example .env
    echo -e "${RED}[!] IMPORTANTE: Edite o arquivo .env com suas chaves de API antes de continuar!${NC}"
    echo -e "${RED}    nano .env${NC}"
    exit 1
fi

# Verificar chaves de API
source .env
if [ -z "$DEEPGRAM_API_KEY" ] || [ "$DEEPGRAM_API_KEY" = "your_deepgram_api_key_here" ]; then
    echo -e "${RED}[!] DEEPGRAM_API_KEY não configurada no .env${NC}"
    exit 1
fi

if [ -z "$MURF_API_KEY" ] || [ "$MURF_API_KEY" = "your_murf_api_key_here" ]; then
    echo -e "${RED}[!] MURF_API_KEY não configurada no .env${NC}"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo -e "${RED}[!] OPENAI_API_KEY não configurada no .env${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Variáveis de ambiente verificadas${NC}"

# Criar diretórios necessários
mkdir -p logs/freeswitch logs/app audio

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[!] Docker não está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Docker encontrado${NC}"

# Build e start dos containers
echo -e "${YELLOW}[...] Construindo containers...${NC}"
docker compose build

echo -e "${YELLOW}[...] Iniciando containers...${NC}"
docker compose up -d

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        LigAI - Iniciado!             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "WebSocket Server: ${GREEN}ws://localhost:8765${NC}"
echo -e "FreeSWITCH SIP:   ${GREEN}sip:localhost:5060${NC}"
echo ""
echo -e "Para ver logs:    ${YELLOW}docker compose logs -f${NC}"
echo -e "Para parar:       ${YELLOW}./stop.sh${NC}"
echo ""
