#!/usr/bin/env python3
"""
LigAI - Teste das APIs de IA
Testa Deepgram, OpenAI e Murf sem precisar de chamada telefônica
"""

import asyncio
import os
import sys

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings


async def test_openai():
    """Testa conexão com OpenAI"""
    print("\n[1/3] Testando OpenAI GPT...")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um assistente de atendimento telefônico. Responda de forma curta e natural."},
                {"role": "user", "content": "Olá, gostaria de informações sobre horário de atendimento."}
            ],
            max_tokens=150
        )

        answer = response.choices[0].message.content
        print(f"  ✓ OpenAI: Funcionando!")
        print(f"    Resposta: {answer}")
        return True, answer

    except Exception as e:
        print(f"  ✗ OpenAI: Erro - {e}")
        return False, None


async def test_deepgram():
    """Testa conexão com Deepgram"""
    print("\n[2/3] Testando Deepgram STT...")

    try:
        import aiohttp

        # Usar API REST diretamente
        url = "https://api.deepgram.com/v1/listen?model=nova-2&language=en"
        audio_url = "https://static.deepgram.com/examples/interview_speech-analytics.wav"

        headers = {
            "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json={"url": audio_url},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
                    print(f"  ✓ Deepgram: Funcionando!")
                    print(f"    Transcrição (amostra): {transcript[:100]}...")
                    return True
                else:
                    error = await response.text()
                    print(f"  ✗ Deepgram: Erro HTTP {response.status} - {error}")
                    return False

    except Exception as e:
        print(f"  ✗ Deepgram: Erro - {e}")
        return False


async def test_murf():
    """Testa conexão com Murf AI"""
    print("\n[3/3] Testando Murf AI TTS...")

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            headers = {
                "api-key": settings.MURF_API_KEY,
                "Content-Type": "application/json"
            }

            # Listar vozes disponíveis
            async with session.get(
                "https://api.murf.ai/v1/speech/voices",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # A resposta pode ser uma lista direta ou um objeto com "voices"
                    if isinstance(data, list):
                        voices = data
                    else:
                        voices = data.get("voices", [])

                    # Filtrar vozes pt-BR (usando locale)
                    pt_voices = [v for v in voices if 'pt-BR' in str(v.get('locale', '')) or 'pt-BR' in str(v.get('voiceId', ''))]

                    print(f"  ✓ Murf AI: Funcionando!")
                    print(f"    Total de vozes: {len(voices)}")
                    print(f"    Vozes pt-BR: {len(pt_voices)}")
                    if pt_voices:
                        for v in pt_voices[:3]:
                            name = v.get('displayName') or v.get('name') or v.get('voiceId', 'N/A')
                            vid = v.get('voiceId', 'N/A')
                            print(f"      - {name} ({vid})")
                    return True
                elif response.status == 401:
                    print("  ✗ Murf AI: Chave de API inválida")
                    return False
                else:
                    error = await response.text()
                    print(f"  ✗ Murf AI: Erro HTTP {response.status} - {error}")
                    return False

    except Exception as e:
        print(f"  ✗ Murf AI: Erro - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_flow(text_input: str = "Olá, qual o horário de funcionamento?"):
    """Testa o fluxo completo: entrada de texto -> LLM -> TTS"""
    print("\n" + "="*50)
    print("TESTE DE FLUXO COMPLETO")
    print("="*50)
    print(f"\nEntrada simulada: '{text_input}'")

    try:
        # 1. Gerar resposta com LLM
        print("\n1. Gerando resposta com OpenAI...")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um assistente de atendimento telefônico. Responda de forma curta e natural, como se estivesse em uma ligação."},
                {"role": "user", "content": text_input}
            ],
            max_tokens=150
        )

        ai_response = response.choices[0].message.content
        print(f"   Resposta IA: {ai_response}")

        # 2. Converter para áudio com Murf
        print("\n2. Convertendo para áudio com Murf AI...")
        import aiohttp

        async with aiohttp.ClientSession() as session:
            headers = {
                "api-key": settings.MURF_API_KEY,
                "Content-Type": "application/json"
            }

            payload = {
                "text": ai_response,
                "voiceId": settings.MURF_VOICE_ID,
                "style": "conversational",
                "format": "WAV",
                "sampleRate": 24000,
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
                        print(f"   ✓ Áudio gerado!")
                        print(f"   URL: {audio_url}")

                        # Baixar o áudio
                        async with session.get(audio_url) as audio_response:
                            if audio_response.status == 200:
                                audio_data = await audio_response.read()
                                audio_file = "/tmp/ligai_test_response.wav"
                                with open(audio_file, "wb") as f:
                                    f.write(audio_data)
                                print(f"   ✓ Áudio salvo em: {audio_file}")
                                print(f"   Tamanho: {len(audio_data)} bytes")
                                return True
                else:
                    error = await response.text()
                    print(f"   ✗ Erro ao gerar áudio: {error}")
                    return False

    except Exception as e:
        print(f"   ✗ Erro no fluxo: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*50)
    print("   LigAI - Teste de APIs de IA")
    print("="*50)

    # Validar configurações
    errors = settings.validate()
    if errors:
        print("\n⚠ Configurações ausentes:")
        for error in errors:
            print(f"  - {error}")
        print("\nEdite o arquivo .env e tente novamente.")
        sys.exit(1)

    # Executar testes individuais
    results = []

    openai_ok, ai_response = await test_openai()
    results.append(("OpenAI", openai_ok))

    deepgram_ok = await test_deepgram()
    results.append(("Deepgram", deepgram_ok))

    murf_ok = await test_murf()
    results.append(("Murf AI", murf_ok))

    # Resumo
    print("\n" + "="*50)
    print("RESUMO DOS TESTES")
    print("="*50)

    all_passed = True
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    # Se todas APIs funcionam, testar fluxo completo
    if all_passed:
        await test_full_flow()
        print("\n" + "="*50)
        print("✓ SISTEMA PRONTO PARA USO!")
        print("="*50)
    else:
        print("\n⚠ Corrija os erros acima antes de usar o sistema.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
