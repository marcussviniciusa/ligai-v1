#!/bin/bash
# Script para fazer ligação com IA - AUTOMATIZADO
# Uso: ./ligar.sh 5584991516506

NUMERO="$1"
if [ -z "$NUMERO" ]; then
    echo "Uso: $0 <numero>"
    echo "Exemplo: $0 5584991516506"
    exit 1
fi

# Gerar UUID único para a chamada
UUID="call-$(date +%s)-$$"

echo "Fazendo ligação para $NUMERO..."
echo "UUID: $UUID"

# Fazer a chamada com api_on_answer para conectar audio_fork automaticamente
RESULT=$(docker exec ligai-freeswitch fs_cli -x "originate {origination_uuid=$UUID,ignore_early_media=true,api_on_answer='uuid_audio_fork $UUID start ws://127.0.0.1:8000/ws/$UUID mono 8000 {\"uuid\":\"$UUID\"}'}sofia/gateway/ligai-trunk/1290#$NUMERO &park" 2>&1)

if echo "$RESULT" | grep -q "+OK"; then
    echo "Chamada iniciada com sucesso!"
    echo ""
    echo "Quando a pessoa atender, a IA começará a falar automaticamente."
    echo ""
    echo "Para encerrar: docker exec ligai-freeswitch fs_cli -x \"uuid_kill $UUID\""
else
    echo "Erro ao iniciar chamada: $RESULT"
    exit 1
fi
