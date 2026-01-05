#!/usr/bin/env python3
"""
LigAI - Fazer chamada com IA
Liga para um número e reproduz uma saudação gerada pela IA
"""

import asyncio
import socket
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


async def generate_greeting():
    """Gera saudação com IA e converte para áudio"""
    from openai import AsyncOpenAI
    import aiohttp

    print("\n[1/2] Gerando saudação com OpenAI...")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um assistente de atendimento telefônico. Gere uma saudação curta e amigável para iniciar uma ligação."},
            {"role": "user", "content": "Gere uma saudação de boas-vindas para um cliente que está ligando."}
        ],
        max_tokens=100
    )

    greeting = response.choices[0].message.content
    print(f"    Texto: {greeting}")

    print("\n[2/2] Convertendo para áudio com Murf AI...")

    async with aiohttp.ClientSession() as session:
        headers = {
            "api-key": settings.MURF_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": greeting,
            "voiceId": settings.MURF_VOICE_ID,
            "style": "conversational",
            "format": "WAV",
            "sampleRate": 8000,
            "channelType": "MONO"
        }

        async with session.post(
            "https://api.murf.ai/v1/speech/generate",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                audio_url = result.get("audioFile")

                if audio_url:
                    # Baixar áudio
                    async with session.get(audio_url) as audio_resp:
                        if audio_resp.status == 200:
                            audio_data = await audio_resp.read()
                            audio_file = "/audio/greeting.wav"
                            with open(audio_file, "wb") as f:
                                f.write(audio_data)
                            print(f"    Áudio salvo: {audio_file}")
                            return audio_file

    return None


def send_esl_command(command, host='ligai-freeswitch', port=8021, password='ClueCon'):
    """Envia comando ESL ao FreeSWITCH"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        # Receber saudação
        sock.recv(1024)

        # Autenticar
        sock.send(f"auth {password}\n\n".encode())
        data = sock.recv(1024).decode()

        if "+OK" not in data:
            print(f"Erro auth: {data}")
            return None

        # Enviar comando
        sock.send(f"{command}\n\n".encode())
        time.sleep(0.5)
        result = sock.recv(4096).decode()

        sock.close()
        return result

    except Exception as e:
        print(f"Erro ESL: {e}")
        return None


async def make_call(phone_number):
    """Faz chamada com IA"""
    print("="*50)
    print("  LigAI - Chamada com Inteligência Artificial")
    print("="*50)

    # Gerar saudação
    audio_file = await generate_greeting()

    if not audio_file:
        print("\n✗ Erro ao gerar áudio")
        return False

    print(f"\n[3/3] Originando chamada para {phone_number}...")

    # Comando para ligar e reproduzir áudio
    # Usa playback para tocar o áudio gerado, depois echo para teste
    cmd = f"api originate {{ignore_early_media=true}}sofia/gateway/ligai-trunk/1290#{phone_number} 'playback:/var/lib/freeswitch/sounds/custom/greeting.wav,sleep:2000,echo' inline"

    result = send_esl_command(cmd)

    if result and "+OK" in result:
        print(f"    ✓ Chamada iniciada!")
        print(f"\n    Seu telefone vai tocar.")
        print(f"    Ao atender, você ouvirá a saudação da IA.")
        print(f"    Depois, entrará no modo echo (ouvirá sua própria voz).")
        return True
    else:
        print(f"    ✗ Erro: {result}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Uso: python make_ai_call.py <numero>")
        print("Exemplo: python make_ai_call.py 5584991516506")
        sys.exit(1)

    phone = sys.argv[1]
    asyncio.run(make_call(phone))


if __name__ == "__main__":
    main()
