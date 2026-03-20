"""
Cliente LLM unificado — suporta múltiplos provedores:
  - Ollama        (local, 100% privado, sem internet)
  - OpenAI API    (GPT-4o / GPT-4o-mini, API não treina com seus dados)
  - Azure OpenAI  (nível enterprise/governo, recomendado para órgãos federais)
  - Anthropic     (Claude 3.5 Sonnet / Haiku, API não treina com seus dados)

Garantias de privacidade via API (diferente dos produtos gratuitos):
  OpenAI:    https://openai.com/policies/api-data-usage-policies
  Anthropic: https://www.anthropic.com/privacy
  Azure:     https://learn.microsoft.com/azure/ai-services/openai/faq#data-privacy
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Literal

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração do provedor
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    """Configuração unificada para qualquer provedor LLM."""

    provider: Literal[
        "ollama", "openai", "azure_openai", "anthropic", "groq", "mistral"
    ] = "ollama"

    # ---- Ollama (local) ----
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # ---- OpenAI ----
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ---- Azure OpenAI ----
    azure_endpoint: str = ""        # ex: https://meu-recurso.openai.azure.com/
    azure_api_key: str = ""
    azure_deployment: str = ""      # nome do deployment no Azure
    azure_api_version: str = "2024-08-01-preview"

    # ---- Anthropic ----
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    # ---- Groq (gratuito, rápido, privado) ----
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ---- Mistral AI (gratuito, europeu, GDPR) ----
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    # ---- Geral ----
    timeout: int = 600              # segundos (relevante para Ollama sem GPU)
    max_tokens: int = 4096


# ---------------------------------------------------------------------------
# Dispatcher principal
# ---------------------------------------------------------------------------

def gerar_texto(prompt: str, system: str, config: LLMConfig) -> Optional[str]:
    """Envia prompt+system para o provedor configurado e retorna o texto gerado."""
    try:
        if config.provider == "ollama":
            return _gerar_ollama(prompt, system, config, format_json=False)
        elif config.provider == "openai":
            return _gerar_openai(prompt, system, config)
        elif config.provider == "azure_openai":
            return _gerar_azure_openai(prompt, system, config)
        elif config.provider == "anthropic":
            return _gerar_anthropic(prompt, system, config)
        elif config.provider == "groq":
            return _gerar_openai_compat(
                prompt, system, config,
                api_key=config.groq_api_key,
                model=config.groq_model,
                base_url="https://api.groq.com/openai/v1",
            )
        elif config.provider == "mistral":
            return _gerar_openai_compat(
                prompt, system, config,
                api_key=config.mistral_api_key,
                model=config.mistral_model,
                base_url="https://api.mistral.ai/v1",
            )
        else:
            logger.error("Provedor desconhecido: %s", config.provider)
            return None
    except Exception as e:
        logger.error("Erro no provedor %s: %s", config.provider, e)
        return None


def gerar_json(prompt: str, system: str, config: LLMConfig) -> Optional[str]:
    """
    Solicita resposta em JSON para qualquer provedor.
    Todos os provedores usam geração de texto com instrução JSON + extração,
    evitando o modo format=json restrito do Ollama (muito lento em CPU).
    """
    try:
        if config.provider == "ollama":
            # Usa text generation com instruções explícitas — muito mais rápido
            # que o modo format=json que força gramática token-a-token
            raw = _gerar_ollama(prompt, system, config, format_json=True)
        else:
            system_json = (
                system + "\n\nIMPORTANTE: Retorne APENAS JSON válido, "
                "sem texto adicional, sem markdown, sem blocos de código."
            )
            raw = gerar_texto(prompt, system_json, config)

        if raw is None:
            return None
        return _extrair_json_texto(raw)

    except Exception as e:
        _msg = str(e)
        if "timeout" in _msg.lower() or "timed out" in _msg.lower():
            logger.error(
                "Ollama timeout (%s). Modelo lento em CPU — use Groq, OpenAI ou "
                "outro provedor de nuvem para análises mais rápidas.",
                config.ollama_model,
            )
        else:
            logger.error("Erro ao gerar JSON com %s (%s): %s",
                         config.provider, type(e).__name__, _msg)
        return None


# Modelos com suporte a visão por provedor
_MODELOS_VISAO = {
    "openai":       "gpt-4o",
    "azure_openai": None,          # usa o deployment configurado
    "anthropic":    "claude-3-5-sonnet-20241022",
    "groq":         "llama-3.2-11b-vision-preview",
    "mistral":      None,          # Mistral não suporta visão via API ainda
    "ollama":       None,          # depende do modelo (llava, etc.)
}

_PROMPT_VISAO_PT = (
    "Analise esta imagem e extraia todo o conteúdo relevante para análise técnica "
    "de projetos de infraestrutura urbana. Inclua:\n"
    "1. Todo texto visível (transcreva fielmente)\n"
    "2. Descrição de plantas, mapas ou diagramas técnicos\n"
    "3. Tabelas ou dados quantitativos presentes\n"
    "4. Localização geográfica se identificável\n"
    "5. Elementos relevantes para projetos de mobilidade, saneamento ou modernização urbana\n"
    "Seja detalhado e objetivo."
)


def gerar_visao(
    imagem_b64: str,
    media_type: str,
    config: LLMConfig,
    prompt: str = _PROMPT_VISAO_PT,
) -> Optional[str]:
    """
    Envia uma imagem (base64) para análise pelo modelo de visão do provedor.
    Retorna a descrição/texto extraído, ou None se o provedor não suportar visão.
    """
    try:
        if config.provider == "openai":
            return _visao_openai(imagem_b64, media_type, prompt, config)
        elif config.provider == "azure_openai":
            return _visao_azure(imagem_b64, media_type, prompt, config)
        elif config.provider == "anthropic":
            return _visao_anthropic(imagem_b64, media_type, prompt, config)
        elif config.provider == "groq":
            return _visao_groq(imagem_b64, media_type, prompt, config)
        elif config.provider == "ollama":
            return _visao_ollama(imagem_b64, media_type, prompt, config)
        else:
            logger.info("Provedor %s não suporta visão.", config.provider)
            return None
    except Exception as e:
        logger.warning("Visão falhou (%s): %s", config.provider, e)
        return None


def suporta_visao(config: LLMConfig) -> bool:
    """Verifica se o provedor/modelo configurado suporta análise de imagens."""
    if config.provider == "ollama":
        m = config.ollama_model.lower()
        return any(k in m for k in ("llava", "vision", "bakllava", "moondream"))
    if config.provider == "mistral":
        return False
    return _MODELOS_VISAO.get(config.provider) is not None


def _visao_openai(b64: str, media_type: str, prompt: str, config: LLMConfig) -> Optional[str]:
    try:
        from openai import OpenAI
    except ImportError:
        return None
    client = OpenAI(api_key=config.openai_api_key, timeout=config.timeout)
    resp = client.chat.completions.create(
        model=_MODELOS_VISAO["openai"],
        max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]}],
    )
    return resp.choices[0].message.content


def _visao_azure(b64: str, media_type: str, prompt: str, config: LLMConfig) -> Optional[str]:
    try:
        from openai import AzureOpenAI
    except ImportError:
        return None
    client = AzureOpenAI(
        azure_endpoint=config.azure_endpoint.rstrip("/"),
        api_key=config.azure_api_key,
        api_version=config.azure_api_version,
        timeout=config.timeout,
    )
    resp = client.chat.completions.create(
        model=config.azure_deployment,
        max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]}],
    )
    return resp.choices[0].message.content


def _visao_anthropic(b64: str, media_type: str, prompt: str, config: LLMConfig) -> Optional[str]:
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=config.anthropic_api_key, timeout=config.timeout)
    msg = client.messages.create(
        model=_MODELOS_VISAO["anthropic"],
        max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return msg.content[0].text


def _visao_groq(b64: str, media_type: str, prompt: str, config: LLMConfig) -> Optional[str]:
    try:
        from openai import OpenAI
    except ImportError:
        return None
    client = OpenAI(
        api_key=config.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=config.timeout,
    )
    resp = client.chat.completions.create(
        model=_MODELOS_VISAO["groq"],
        max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]}],
    )
    return resp.choices[0].message.content


def _visao_ollama(b64: str, media_type: str, prompt: str, config: LLMConfig) -> Optional[str]:
    """Ollama visão — funciona com modelos llava, bakllava, moondream."""
    url = f"{config.ollama_host.rstrip('/')}/api/generate"
    payload = {
        "model": config.ollama_model,
        "prompt": prompt,
        "images": [b64],
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=config.timeout)
    r.raise_for_status()
    return r.json().get("response", "")


def testar_conexao(config: LLMConfig) -> tuple:
    """
    Testa a conectividade com o provedor configurado.
    Returns: (ok: bool, mensagem: str)
    """
    try:
        if config.provider == "ollama":
            return _testar_ollama(config)
        elif config.provider == "openai":
            return _testar_openai(config)
        elif config.provider == "azure_openai":
            return _testar_azure_openai(config)
        elif config.provider == "anthropic":
            return _testar_anthropic(config)
        elif config.provider == "groq":
            return _testar_openai_compat(
                config.groq_api_key, config.groq_model,
                "https://api.groq.com/openai/v1", "Groq",
            )
        elif config.provider == "mistral":
            return _testar_openai_compat(
                config.mistral_api_key, config.mistral_model,
                "https://api.mistral.ai/v1", "Mistral AI",
            )
        return False, f"Provedor desconhecido: {config.provider}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Implementações por provedor
# ---------------------------------------------------------------------------

def _extrair_json_texto(texto: str) -> str:
    """
    Extrai JSON de uma resposta de texto que pode conter markdown ou texto extra.
    Tenta múltiplas estratégias de limpeza.
    """
    if not texto:
        return texto
    t = texto.strip()
    # Remove blocos de código markdown: ```json ... ``` ou ``` ... ```
    if "```" in t:
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
        if match:
            t = match.group(1).strip()
    # Se começar com { ou [, provavelmente é JSON direto
    if t.startswith("{") or t.startswith("["):
        return t
    # Tenta encontrar primeiro { ... } ou [ ... ]
    import re
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", t)
    if match:
        return match.group(1).strip()
    return t


def _gerar_ollama(prompt: str, system: str, config: LLMConfig,
                  format_json: bool = False) -> Optional[str]:
    """
    Chama a API do Ollama.

    IMPORTANTE: NÃO usa format="json" mesmo quando format_json=True.
    O modo JSON restrito do Ollama usa gramática token-a-token que é
    extremamente lento em CPU (pode levar >10min para 7B params).
    Em vez disso, instrui o modelo via system prompt e extrai o JSON
    do texto resultante — muito mais rápido e igualmente confiável.
    """
    url = f"{config.ollama_host.rstrip('/')}/api/generate"

    # Quando JSON é esperado, reforça via instrução no system prompt
    effective_system = system
    if format_json:
        effective_system = (
            system.rstrip()
            + "\n\nRESPONDA APENAS COM JSON VÁLIDO. Sem texto antes ou depois. "
            "Sem markdown. Sem blocos de código. Apenas o objeto JSON."
        )

    payload = {
        "model": config.ollama_model,
        "prompt": prompt,
        "system": effective_system,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=config.timeout)
    r.raise_for_status()
    resposta = r.json().get("response", "")

    # Limpa possíveis artefatos de formatação se JSON era esperado
    if format_json:
        resposta = _extrair_json_texto(resposta)

    return resposta


def _gerar_openai(prompt: str, system: str, config: LLMConfig) -> Optional[str]:
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("Pacote 'openai' não instalado. Execute: pip install openai")
        return None

    client = OpenAI(api_key=config.openai_api_key, timeout=config.timeout)
    response = client.chat.completions.create(
        model=config.openai_model,
        max_tokens=config.max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _gerar_azure_openai(prompt: str, system: str, config: LLMConfig) -> Optional[str]:
    try:
        from openai import AzureOpenAI
    except ImportError:
        logger.error("Pacote 'openai' não instalado. Execute: pip install openai")
        return None

    client = AzureOpenAI(
        azure_endpoint=config.azure_endpoint.rstrip("/"),
        api_key=config.azure_api_key,
        api_version=config.azure_api_version,
        timeout=config.timeout,
    )
    response = client.chat.completions.create(
        model=config.azure_deployment,
        max_tokens=config.max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _gerar_openai_compat(prompt: str, system: str, config: LLMConfig,
                         api_key: str, model: str, base_url: str) -> Optional[str]:
    """Geração via qualquer API compatível com OpenAI (Groq, Mistral, etc.)."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("Pacote 'openai' não instalado. Execute: pip install openai")
        return None

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=config.timeout)
    response = client.chat.completions.create(
        model=model,
        max_tokens=config.max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _gerar_anthropic(prompt: str, system: str, config: LLMConfig) -> Optional[str]:
    try:
        import anthropic
    except ImportError:
        logger.error("Pacote 'anthropic' não instalado. Execute: pip install anthropic")
        return None

    client = anthropic.Anthropic(
        api_key=config.anthropic_api_key,
        timeout=config.timeout,
    )
    message = client.messages.create(
        model=config.anthropic_model,
        max_tokens=config.max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Testes de conectividade
# ---------------------------------------------------------------------------

def _testar_openai_compat(api_key: str, model: str, base_url: str,
                           nome: str) -> tuple:
    """Testa provedores compatíveis com OpenAI (Groq, Mistral, etc.)."""
    try:
        from openai import OpenAI
    except ImportError:
        return False, f"Pacote 'openai' não instalado. Execute: pip install openai"

    if not api_key:
        return False, "API key não configurada."

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=10)
    r = client.chat.completions.create(
        model=model,
        max_tokens=5,
        messages=[{"role": "user", "content": "OK"}],
    )
    return True, f"{nome} OK — modelo {model} acessível."


def _testar_ollama(config: LLMConfig) -> tuple:
    r = requests.get(
        f"{config.ollama_host.rstrip('/')}/api/tags", timeout=5
    )
    r.raise_for_status()
    models = [m.get("name", "") for m in r.json().get("models", [])]
    if any(config.ollama_model in n for n in models):
        return True, f"Ollama OK — modelo {config.ollama_model} disponível."
    elif models:
        return False, (
            f"Ollama acessível, mas modelo '{config.ollama_model}' não encontrado. "
            f"Instalados: {', '.join(models[:3])}. "
            f"Execute: ollama pull {config.ollama_model}"
        )
    return False, "Ollama acessível, mas nenhum modelo instalado."


def _testar_openai(config: LLMConfig) -> tuple:
    try:
        from openai import OpenAI
    except ImportError:
        return False, "Pacote 'openai' não instalado. Execute: pip install openai"

    if not config.openai_api_key:
        return False, "API key não configurada."

    client = OpenAI(api_key=config.openai_api_key, timeout=10)
    # Usa o endpoint de modelos (não gera tokens, só verifica autenticação)
    models = client.models.list()
    names = [m.id for m in models.data]
    if config.openai_model in names or any(config.openai_model in n for n in names):
        return True, f"OpenAI API OK — modelo {config.openai_model} disponível."
    return True, f"OpenAI API OK — modelo solicitado '{config.openai_model}' não listado, mas API funcionando."


def _testar_azure_openai(config: LLMConfig) -> tuple:
    try:
        from openai import AzureOpenAI
    except ImportError:
        return False, "Pacote 'openai' não instalado. Execute: pip install openai"

    if not config.azure_api_key or not config.azure_endpoint:
        return False, "Endpoint ou API key do Azure não configurados."

    client = AzureOpenAI(
        azure_endpoint=config.azure_endpoint.rstrip("/"),
        api_key=config.azure_api_key,
        api_version=config.azure_api_version,
        timeout=10,
    )
    # Testa com uma chamada mínima
    r = client.chat.completions.create(
        model=config.azure_deployment,
        max_tokens=5,
        messages=[{"role": "user", "content": "OK"}],
    )
    return True, f"Azure OpenAI OK — deployment '{config.azure_deployment}' acessível."


def _testar_anthropic(config: LLMConfig) -> tuple:
    try:
        import anthropic
    except ImportError:
        return False, "Pacote 'anthropic' não instalado. Execute: pip install anthropic"

    if not config.anthropic_api_key:
        return False, "API key não configurada."

    client = anthropic.Anthropic(api_key=config.anthropic_api_key, timeout=10)
    msg = client.messages.create(
        model=config.anthropic_model,
        max_tokens=5,
        messages=[{"role": "user", "content": "OK"}],
    )
    return True, f"Anthropic OK — modelo {config.anthropic_model} acessível."


# ---------------------------------------------------------------------------
# Utilitário: descreve o provedor atual para exibição
# ---------------------------------------------------------------------------

DESCRICAO_PRIVACIDADE = {
    "ollama": {
        "label": "🖥️ Local (Ollama)",
        "privacidade": "🔒 100% local — nenhum dado sai da sua máquina.",
        "custo": "Gratuito",
        "velocidade": "Lento sem GPU (15–30 min/parecer)",
        "qualidade": "Boa",
    },
    "groq": {
        "label": "⚡ Groq API (gratuito)",
        "privacidade": "🛡️ API não usa seus dados para treino (política contratual). Servidores nos EUA.",
        "custo": "Gratuito (com limites de uso)",
        "velocidade": "Muito rápido (~30 segundos)",
        "qualidade": "Muito alta (Llama 3.3 70B)",
    },
    "mistral": {
        "label": "☁️ Mistral AI (gratuito, europeu)",
        "privacidade": "🇪🇺 Empresa europeia, GDPR. API não usa seus dados para treino.",
        "custo": "Gratuito (tier inicial)",
        "velocidade": "Rápido (30–60 segundos)",
        "qualidade": "Alta",
    },
    "openai": {
        "label": "☁️ OpenAI API",
        "privacidade": "🛡️ API não usa seus dados para treino (política contratual).",
        "custo": "~R$ 0,05–0,30 por parecer (gpt-4o-mini) / ~R$ 0,50–2,00 (gpt-4o)",
        "velocidade": "Rápido (30–90 segundos)",
        "qualidade": "Muito alta",
    },
    "azure_openai": {
        "label": "☁️ Azure OpenAI (Governo)",
        "privacidade": "🏛️ Nível enterprise/governo. Dados ficam na infraestrutura Microsoft. Recomendado para órgãos federais.",
        "custo": "Conforme contrato Azure do Ministério",
        "velocidade": "Rápido (30–90 segundos)",
        "qualidade": "Muito alta",
    },
    "anthropic": {
        "label": "☁️ Claude (Anthropic)",
        "privacidade": "🛡️ API não usa seus dados para treino (política contratual).",
        "custo": "~R$ 0,02–0,10 por parecer (Haiku) / ~R$ 0,30–1,00 (Sonnet)",
        "velocidade": "Rápido (30–90 segundos)",
        "qualidade": "Muito alta",
    },
}
