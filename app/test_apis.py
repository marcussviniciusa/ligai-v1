#!/usr/bin/env python3
"""
LigAI - Script de teste das APIs
Verifica se as chaves de API estão funcionando corretamente
"""

import asyncio
import sys

from config import settings


async def test_deepgram():
    """Testa conexão com Deepgram"""
    print("\n[1/3] Testando Deepgram...")

    try:
        from deepgram import DeepgramClient

        client = DeepgramClient(settings.DEEPGRAM_API_KEY)

        # Testar com um request simples
        response = await client.manage.async_get_projects()

        if response:
            print("  ✓ Deepgram: Conexão OK")
            return True
        else:
            print("  ✗ Deepgram: Resposta vazia")
            return False

    except Exception as e:
        print(f"  ✗ Deepgram: Erro - {e}")
        return False


async def test_murf():
    """Testa conexão com Murf AI"""
    print("\n[2/3] Testando Murf AI...")

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            headers = {
                "api-key": settings.MURF_API_KEY,
                "Content-Type": "application/json"
            }

            async with session.get(
                "https://api.murf.ai/v1/speech/voices",
                headers=headers,
                params={"language": "pt-BR"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    voices = data.get("voices", [])
                    print(f"  ✓ Murf AI: Conexão OK ({len(voices)} vozes pt-BR disponíveis)")
                    return True
                elif response.status == 401:
                    print("  ✗ Murf AI: Chave de API inválida")
                    return False
                else:
                    print(f"  ✗ Murf AI: Erro HTTP {response.status}")
                    return False

    except Exception as e:
        print(f"  ✗ Murf AI: Erro - {e}")
        return False


async def test_openai():
    """Testa conexão com OpenAI"""
    print("\n[3/3] Testando OpenAI...")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Diga 'OK' se estiver funcionando."}],
            max_tokens=10
        )

        if response.choices:
            print("  ✓ OpenAI: Conexão OK")
            return True
        else:
            print("  ✗ OpenAI: Resposta vazia")
            return False

    except Exception as e:
        print(f"  ✗ OpenAI: Erro - {e}")
        return False


async def main():
    print("=" * 50)
    print("   LigAI - Teste de APIs")
    print("=" * 50)

    # Verificar configurações
    errors = settings.validate()
    if errors:
        print("\n⚠ Configurações ausentes:")
        for error in errors:
            print(f"  - {error}")
        print("\nEdite o arquivo .env e tente novamente.")
        sys.exit(1)

    # Executar testes
    results = await asyncio.gather(
        test_deepgram(),
        test_murf(),
        test_openai()
    )

    # Resumo
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✓ Todos os testes passaram! ({passed}/{total})")
        print("  O sistema está pronto para uso.")
        sys.exit(0)
    else:
        print(f"✗ Alguns testes falharam ({passed}/{total})")
        print("  Verifique as chaves de API no arquivo .env")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
