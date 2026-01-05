#!/usr/bin/env python3
"""
LigAI - Handler ESL (Event Socket Library)
Conecta ao FreeSWITCH via ESL para processar chamadas com IA
"""

import asyncio
import socket
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


class ESLClient:
    """Cliente ESL simplificado para FreeSWITCH"""

    def __init__(self, host='localhost', port=8021, password='ClueCon'):
        self.host = host
        self.port = port
        self.password = password
        self.sock = None
        self.connected = False

    def connect(self):
        """Conecta ao FreeSWITCH ESL"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

            # Receber saudação
            data = self.sock.recv(1024).decode()
            print(f"ESL: {data.strip()}")

            # Autenticar
            self.sock.send(f"auth {self.password}\n\n".encode())
            data = self.sock.recv(1024).decode()

            if "+OK accepted" in data:
                print("ESL: Autenticado com sucesso!")
                self.connected = True
                return True
            else:
                print(f"ESL: Falha na autenticação - {data}")
                return False

        except Exception as e:
            print(f"ESL: Erro ao conectar - {e}")
            return False

    def send_command(self, command):
        """Envia comando ao FreeSWITCH"""
        if not self.connected:
            return None

        try:
            self.sock.send(f"{command}\n\n".encode())
            data = self.sock.recv(4096).decode()
            return data
        except Exception as e:
            print(f"ESL: Erro ao enviar comando - {e}")
            return None

    def originate_call(self, number, app="echo"):
        """Origina uma chamada"""
        cmd = f"api originate {{ignore_early_media=true}}sofia/gateway/ligai-trunk/1290#{number} &{app}"
        return self.send_command(cmd)

    def close(self):
        """Fecha conexão"""
        if self.sock:
            self.sock.close()
            self.connected = False


async def generate_ai_response(text):
    """Gera resposta da IA e converte para áudio"""
    from openai import AsyncOpenAI
    import aiohttp

    print(f"\n[IA] Processando: {text}")

    # 1. Gerar resposta com OpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um assistente de atendimento telefônico. Responda de forma curta e natural."},
            {"role": "user", "content": text}
        ],
        max_tokens=150
    )

    ai_text = response.choices[0].message.content
    print(f"[IA] Resposta: {ai_text}")

    # 2. Converter para áudio com Murf
    async with aiohttp.ClientSession() as session:
        headers = {
            "api-key": settings.MURF_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": ai_text,
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
        ) as response:
            if response.status == 200:
                result = await response.json()
                audio_url = result.get("audioFile")
                if audio_url:
                    # Baixar áudio
                    async with session.get(audio_url) as audio_resp:
                        if audio_resp.status == 200:
                            audio_data = await audio_resp.read()
                            audio_file = "/tmp/ligai_response.wav"
                            with open(audio_file, "wb") as f:
                                f.write(audio_data)
                            print(f"[IA] Áudio salvo: {audio_file}")
                            return audio_file, ai_text

    return None, ai_text


def main():
    """Teste de conexão ESL"""
    print("="*50)
    print("  LigAI - Teste de Conexão ESL")
    print("="*50)

    # Conectar ao FreeSWITCH
    esl = ESLClient(host='ligai-freeswitch', port=8021)

    if esl.connect():
        print("\n✓ Conectado ao FreeSWITCH!")

        # Testar comando
        result = esl.send_command("api status")
        print(f"\nStatus FreeSWITCH:\n{result}")

        esl.close()
    else:
        print("\n✗ Falha ao conectar ao FreeSWITCH")


if __name__ == "__main__":
    main()
