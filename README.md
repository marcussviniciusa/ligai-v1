# LigAI - Sistema de Ligação com Inteligência Artificial

Sistema de atendimento telefônico com IA que integra FreeSWITCH, Deepgram (STT), Murf AI (TTS) e OpenAI (LLM).

## Arquitetura

```
[SIP Trunk] → [FreeSWITCH] → [WebSocket] → [LigAI App]
                                              ↓
                              [Deepgram STT] ←→ [OpenAI GPT] ←→ [Murf TTS]
```

## Requisitos

- Docker e Docker Compose
- Conta Deepgram (https://console.deepgram.com/)
- Conta Murf AI (https://murf.ai/api)
- Conta OpenAI (https://platform.openai.com/)
- SIP Trunk contratado

## Instalação Rápida

```bash
# 1. Copiar arquivo de configuração
cp .env.example .env

# 2. Editar com suas chaves de API
nano .env

# 3. Iniciar o sistema
./start.sh
```

## Configuração

### Arquivo .env

```env
# APIs
DEEPGRAM_API_KEY=sua_chave_deepgram
MURF_API_KEY=sua_chave_murf
OPENAI_API_KEY=sua_chave_openai

# SIP Trunk
SIP_TRUNK_HOST=seu_provedor.com
SIP_TRUNK_USER=usuario
SIP_TRUNK_PASSWORD=senha
```

### Vozes Murf AI

Para listar vozes disponíveis em português:

```python
from app.murf_client import MurfClient
import asyncio

async def main():
    client = MurfClient()
    voices = await client.list_voices("pt-BR")
    for v in voices:
        print(f"{v['voiceId']}: {v['name']}")

asyncio.run(main())
```

## Estrutura do Projeto

```
ligai/
├── app/
│   ├── main.py           # Servidor WebSocket principal
│   ├── config.py         # Configurações
│   ├── call_handler.py   # Handler de chamadas
│   ├── deepgram_client.py# Cliente Deepgram (STT)
│   ├── murf_client.py    # Cliente Murf AI (TTS)
│   ├── llm_client.py     # Cliente OpenAI (LLM)
│   └── test_apis.py      # Script de teste
├── freeswitch/
│   └── conf/
│       ├── dialplan.xml  # Roteamento de chamadas
│       ├── sip_trunk.xml # Config do SIP Trunk
│       └── vars.xml      # Variáveis
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── start.sh
├── stop.sh
└── .env
```

## Comandos

```bash
# Iniciar
./start.sh

# Parar
./stop.sh

# Ver logs
docker compose logs -f

# Logs só da aplicação
docker compose logs -f ligai-app

# Testar APIs
docker compose exec ligai-app python test_apis.py

# Reiniciar
docker compose restart
```

## Fluxo de uma Chamada

1. **Chamada entra** via SIP Trunk
2. **FreeSWITCH atende** e conecta ao WebSocket
3. **Saudação** é enviada ao usuário
4. **Usuário fala** → áudio enviado ao Deepgram
5. **Deepgram transcreve** → texto enviado ao GPT
6. **GPT gera resposta** → texto enviado ao Murf
7. **Murf converte** → áudio enviado ao usuário
8. Loop continua até desligar

## Personalização

### Alterar comportamento do assistente

Edite o `system_prompt` em `app/call_handler.py`:

```python
self.system_prompt = """Você é um assistente de vendas...
Seu objetivo é ajudar clientes com informações sobre produtos..."""
```

### Alterar voz

Edite `MURF_VOICE_ID` no `.env` ou `config.py`:

```env
MURF_VOICE_ID=pt-BR-marcos  # Voz masculina
```

### Alterar modelo LLM

Edite `LLM_MODEL` no `.env`:

```env
LLM_MODEL=gpt-4o  # Para respostas mais complexas
```

## Troubleshooting

### Chamadas não conectam
- Verifique configuração do SIP Trunk
- Confirme que as portas 5060 (SIP) e 16384-32768 (RTP) estão abertas

### Transcrição não funciona
- Verifique a chave do Deepgram
- Execute `docker compose exec ligai-app python test_apis.py`

### Áudio não é gerado
- Verifique a chave do Murf AI
- Confirme que o voice_id existe para pt-BR

### Alta latência
- Considere usar servidor mais próximo das APIs
- Verifique conexão de internet

## Custos Estimados

| Serviço | Custo | Observação |
|---------|-------|------------|
| Deepgram | ~$4.30/1000 min | STT streaming |
| Murf AI | Varia por plano | TTS |
| OpenAI | ~$0.15/1M tokens | gpt-4o-mini |

## Licença

MIT
# ligai-v1
