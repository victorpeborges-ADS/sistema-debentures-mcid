"""
Assistente de documento com RAG lógico restrito: a LLM só vê o contexto fornecido
(documento em sessão +, opcionalmente, repositório da mesma categoria).
Instruções de citação obrigatória no system prompt.
"""

from __future__ import annotations

import logging
from typing import Callable, Literal, Optional, Tuple

import streamlit as st

from llm_client import LLMConfig, gerar_texto

logger = logging.getLogger(__name__)

CategoryRepo = Literal["parecer", "portaria"]

SYSTEM_PROMPT_RAG_RESTRITO = """Você é um assistente especializado em análise de documentos administrativos.

HIERARQUIA DE FONTES (obrigatória):
1) CONTEXTO DO CASO EM ANÁLISE — inclui o instrumento gerado (Markdown) e, quando existir, a extração da proposta/documentos. É a FONTE DE VERDADE para o caso atual (município, valores, CAPAG, IBGE, objeto, percentuais).
2) REPOSITÓRIO DE REFERÊNCIA — textos de outros processos apenas como exemplo de redação ou estrutura. NUNCA use números, percentuais, nomes de município ou dados de outro processo do repositório para responder sobre o caso em análise. Se o repositório contradizer o CONTEXTO DO CASO, prevalece sempre o CONTEXTO DO CASO.

REGRAS ABSOLUTAS:
1) Você só pode usar informações que apareçam explicitamente no CONTEXTO abaixo (blocos do caso + repositório secundário).
2) Se a informação não estiver no contexto, responda exatamente: "Não consta no documento fornecido."
3) É PROIBIDO inventar dados, números, artigos, páginas ou trechos que não estejam no contexto.
4) Perguntas sobre "de onde saiu" um dado do parecer: cite primeiro trechos do bloco "PARECER/PORTARIA GERADO" ou "PROPOSTA E DOCUMENTOS CONSOLIDADOS"; só mencione o repositório se o utilizador pedir comparação com pareceres anteriores ou estilo.
5) Toda resposta que extrair um dado do contexto DEVE incluir a justificativa no formato de citação direta abaixo.

FORMATO OBRIGATÓRIO DE CITAÇÃO (use sempre que houver extração de conteúdo):
"No documento [NOME_DO_DOCUMENTO], [LOCALIZAÇÃO: use "página X" somente se o número de página aparecer no contexto; caso contrário indique que não há numeração de página no texto extraído], neste trecho: '{TRECHO_EXATO_COPIADO_DO_CONTEXTO}'"

- O trecho entre aspas simples deve ser cópia literal do CONTEXTO (pode ser curto, mas deve ser fiel).
- Se não houver indicação de página no texto, diga explicitamente que o trecho não traz número de página.

Seja conciso. Responda em português."""


def montar_contexto_para_llm(
    nome_documento: str,
    texto_documento: str,
    texto_repositorio: str = "",
) -> str:
    base = (
        f"NOME_DO_DOCUMENTO: {nome_documento}\n\n"
        f"CONTEXTO DO CASO EM ANÁLISE (prioridade máxima — dados do processo atual):\n"
        f"{texto_documento}"
    )
    tr = (texto_repositorio or "").strip()
    if tr:
        base += (
            "\n\n---\nREPOSITÓRIO DE REFERÊNCIA (secundário — estilo/redação; "
            "não usar dados numéricos ou de outros municípios como se fossem deste caso):\n"
            f"{tr}"
        )
    return base


def texto_documento_ativo_para_rag(
    markdown_gerado: str,
    texto_consolidado: str,
    *,
    max_chars_consolidado: int = 100_000,
) -> tuple[str, str]:
    """
    Junta parecer/portaria gerado com o texto bruto consolidado da proposta (quando existir),
    para o assistente priorizar análise do caso e não só o repositório.
    """
    md = (markdown_gerado or "").strip()
    tx = (texto_consolidado or "").strip()
    if tx and len(tx) > max_chars_consolidado:
        tx = (
            tx[:max_chars_consolidado]
            + "\n\n[... texto consolidado truncado por limite de contexto ...]"
        )
    blocos: list[str] = []
    if md:
        blocos.append(
            "=== PARECER/PORTARIA GERADO (Markdown) — texto do instrumento; cite daqui para redação final ===\n"
            + md
        )
    if tx:
        blocos.append(
            "=== PROPOSTA E DOCUMENTOS CONSOLIDADOS (extração) — projeto, município, anexos e bases da análise ===\n"
            + tx
        )
    if not blocos:
        return "", "Documento vazio"
    if len(blocos) > 1:
        return "\n\n".join(blocos), "Caso atual (gerado + proposta consolidada)"
    return blocos[0], "Parecer/portaria gerado" if md else "Proposta consolidada"


def _limite_chars_repositorio_chat(tamanho_doc: int) -> int:
    """Quanto maior o documento do caso, menor o repositório (evita deslocar atenção da LLM)."""
    if tamanho_doc > 80_000:
        return 18_000
    if tamanho_doc > 40_000:
        return 28_000
    if tamanho_doc > 15_000:
        return 42_000
    return 60_000


def responder_chat_rag(
    pergunta: str,
    nome_documento: str,
    texto_documento: str,
    config: LLMConfig,
    *,
    categoria_repositorio: Optional[CategoryRepo] = None,
) -> Optional[str]:
    doc = (texto_documento or "").strip()
    repo_txt = ""
    if categoria_repositorio:
        from repository_store import texto_repositorio_concatenado

        repo_txt = texto_repositorio_concatenado(
            categoria_repositorio,
            max_chars=_limite_chars_repositorio_chat(len(doc)),
        )
    if not doc and not (repo_txt or "").strip():
        return None
    if not doc and repo_txt:
        doc = "[Documento ativo vazio — responda apenas com base no REPOSITÓRIO abaixo.]"
    ctx = montar_contexto_para_llm(nome_documento, doc, repo_txt)
    prompt_user = f"{ctx}\n\n---\nPERGUNTA DO USUÁRIO:\n{pergunta}"
    return gerar_texto(prompt_user, SYSTEM_PROMPT_RAG_RESTRITO, config)


def render_painel_chat_documento(
    llm_config: LLMConfig,
    nome_documento: str,
    obter_contexto: Callable[[], Tuple[str, str]],
    *,
    key_prefix: str,
    categoria_repositorio: Optional[CategoryRepo] = None,
) -> None:
    """
    Painel lateral de chat. `obter_contexto()` retorna (texto_para_rag, etiqueta_opcional).
    Se `categoria_repositorio` for definido, o texto do repositório correspondente é
    concatenado ao contexto (RAG restrito ao documento + esse repositório).
    """
    st.markdown("##### Assistente ao documento")
    cap = (
        "**Prioridade:** parecer/portaria gerado + proposta consolidada. "
        + (
            "Repositório de pareceres só como referência de estilo."
            if categoria_repositorio == "parecer"
            else (
                "Repositório de portarias só como referência de estilo."
                if categoria_repositorio == "portaria"
                else ""
            )
        )
        + " Citações obrigatórias quando houver extração."
    )
    st.caption(cap)

    msg_key = f"{key_prefix}_chat_messages"
    if msg_key not in st.session_state:
        st.session_state[msg_key] = []

    texto_ctx, _ = obter_contexto()
    from repository_store import texto_repositorio_concatenado as _repo_concat

    _repo_ok = bool(
        categoria_repositorio and _repo_concat(categoria_repositorio).strip()
    )
    if not (texto_ctx or "").strip() and not _repo_ok:
        st.info(
            "Carregue ficheiros, gere o documento ou adicione ficheiros ao repositório "
            "para ativar o contexto do assistente."
        )

    for m in st.session_state[msg_key]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("Limpar conversa", key=f"{key_prefix}_clear_chat"):
            st.session_state[msg_key] = []
            st.rerun()

    prompt = st.chat_input(
        "Pergunta sobre o documento…",
        key=f"{key_prefix}_chat_input",
    )

    if prompt:
        texto_doc, nome_doc2 = obter_contexto()
        nome_ef = (nome_doc2 or "").strip() or nome_documento
        has_repo = bool(
            categoria_repositorio and _repo_concat(categoria_repositorio).strip()
        )
        if not (texto_doc or "").strip() and not has_repo:
            st.warning("Sem texto de documento nem repositório no contexto.")
            return
        with st.spinner("Consultando o documento…"):
            resp = responder_chat_rag(
                prompt,
                nome_ef,
                texto_doc,
                llm_config,
                categoria_repositorio=categoria_repositorio,
            )
        if resp:
            st.session_state[msg_key].append({"role": "user", "content": prompt})
            st.session_state[msg_key].append(
                {"role": "assistant", "content": resp}
            )
            st.rerun()
        else:
            st.error(
                "Não foi possível obter resposta. Verifique a ligação ao modelo."
            )
