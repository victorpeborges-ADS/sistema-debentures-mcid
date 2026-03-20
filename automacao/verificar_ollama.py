#!/usr/bin/env python3
"""
Script de diagnóstico — verifica se o Ollama está acessível.
Execute: python3 verificar_ollama.py
"""

import sys
import requests

HOST = "http://localhost:11434"
TIMEOUT = 10

def main():
    print("=== Diagnóstico Ollama ===\n")
    print(f"Host: {HOST}\n")

    # 1. Testar API base
    try:
        r = requests.get(f"{HOST}/api/tags", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        print("✓ Ollama está rodando e acessível!")
        if models:
            print(f"  Modelos instalados: {[m.get('name') for m in models]}")
        else:
            print("  ⚠ Nenhum modelo instalado. Execute: ollama pull qwen2.5:7b")
    except requests.exceptions.ConnectionError:
        print("✗ Falha de conexão. O Ollama está rodando?")
        print("  - No Mac: abra o app Ollama (ícone na barra de menu)")
        print("  - Ou execute no terminal: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("✗ Timeout. O Ollama demorou para responder.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro: {e}")
        sys.exit(1)

    # 2. Testar geração (opcional)
    print("\nTestando geração (pode demorar na primeira vez)...")
    try:
        r = requests.post(
            f"{HOST}/api/generate",
            json={"model": "qwen2.5:7b", "prompt": "Diga apenas OK", "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        print("✓ Geração funcionando!")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("✗ Modelo qwen2.5:7b não encontrado. Execute: ollama pull qwen2.5:7b")
        else:
            print(f"✗ Erro HTTP: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro na geração: {e}")
        sys.exit(1)

    print("\n=== Tudo OK! O app deve funcionar. ===")

if __name__ == "__main__":
    main()
