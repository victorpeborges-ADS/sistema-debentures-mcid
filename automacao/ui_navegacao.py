"""
Áreas de interface: repositórios (PostgreSQL ou ficheiros) e importação para repositório.

Nomenclatura: “repositório”, não “aba de banco de dados” — o utilizador interage com
listagens e filtros sobre documentos persistidos, sem SQL exposto.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

import streamlit as st

from biblioteca import AVALIACOES, SECOES_OPCOES
from llm_client import LLMConfig
from motor import extrair_texto_arquivo
from repository_store import (
    clear_repository,
    delete_document,
    list_documents,
    list_feedbacks,
    read_document,
    resumo_feedbacks,
    save_document,
    save_feedback,
    total_chars,
)

REPO_UPLOAD_TYPES = ["pdf", "docx", "txt", "md", "htm", "html"]
Category = Literal["parecer", "portaria"]


def _painel_limpar_repositorio(
    category: Category,
    *,
    label_tipo: str,
    key_prefix: str,
    n_docs: int,
) -> None:
    """Botão para esvaziar o repositório desta aba, com confirmação explícita."""
    ck = f"{key_prefix}_confirm_limpar"
    if ck not in st.session_state:
        st.session_state[ck] = False

    st.markdown("#### Manutenção")
    if st.button(
        "🗑️ Limpar repositório",
        key=f"{key_prefix}_btn_limpar",
        help=f"Elimina todos os documentos guardados no repositório de {label_tipo}.",
    ):
        st.session_state[ck] = True

    if st.session_state.get(ck):
        st.error(
            f"**Confirmação necessária:** serão eliminados **todos** os documentos "
            f"do repositório de **{label_tipo}** "
            f"({'nenhum' if n_docs == 0 else f'{n_docs} documento(s)'}). "
            "Esta ação **não pode ser desfeita**. Os feedbacks da equipa **não** são apagados."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "Sim, eliminar tudo",
                type="primary",
                key=f"{key_prefix}_btn_confirmar_limpar",
            ):
                n = clear_repository(category)
                st.session_state[ck] = False
                st.success(
                    f"Repositório de {label_tipo} limpo. "
                    f"{'Nenhum ficheiro.' if n == 0 else f'{n} documento(s) removido(s).'}"
                )
                st.rerun()
        with c2:
            if st.button("Cancelar", key=f"{key_prefix}_btn_cancelar_limpar"):
                st.session_state[ck] = False
                st.rerun()


def render_repositorio_pareceres(llm_config: LLMConfig) -> None:
    """Leitura: listagem, filtro, pré-visualização, upload e feedback da equipa."""
    st.header("📂 Repositório de Pareceres")
    st.caption(
        "Consulta e importação direta de pareceres. "
        "Para **gerar** novos pareceres, use **Gerador de Pareceres**."
    )

    docs = list_documents("parecer")
    n_docs = len(docs)
    tchars = total_chars("parecer")
    m1, m2 = st.columns(2)
    m1.metric("Documentos no repositório", n_docs)
    m2.metric(
        "Volume total",
        f"{round(tchars / 1000)} mil chars" if tchars else "—",
    )

    _painel_limpar_repositorio(
        "parecer",
        label_tipo="pareceres",
        key_prefix="repo_par",
        n_docs=n_docs,
    )

    st.markdown("#### Importar documentos")
    st.caption(
        f"Formatos aceites: **{', '.join(REPO_UPLOAD_TYPES)}**. "
        "O texto é extraído e guardado como referência para a IA."
    )
    up_p = st.file_uploader(
        "Ficheiros:",
        type=REPO_UPLOAD_TYPES,
        accept_multiple_files=True,
        key="upload_repo_pareceres_multi",
    )
    if up_p and len(up_p) > 15:
        st.warning("Máximo 15 ficheiros por vez.")
        up_p = up_p[:15]

    if st.button("Importar para o repositório", key="btn_import_repo_pareceres"):
        if not up_p:
            st.warning("Selecione pelo menos um ficheiro.")
        else:
            salvos, erros = [], []
            barra = st.progress(0, text="A processar…")
            for i, arq in enumerate(up_p):
                barra.progress(
                    (i + 1) / len(up_p),
                    text=f"{arq.name} ({i + 1}/{len(up_p)})",
                )
                stem = arq.name.rsplit(".", 1)[0].replace(" ", "_").replace(".", "_")
                ext = arq.name.rsplit(".", 1)[-1].lower() if "." in arq.name else ""
                try:
                    if ext in ("md", "txt", "htm", "html"):
                        conteudo = arq.read().decode("utf-8", errors="replace")
                    else:
                        conteudo = extrair_texto_arquivo(arq, arq.name)
                    if conteudo and conteudo.strip():
                        fname = f"{stem}.md"
                        save_document("parecer", fname, conteudo.strip())
                        salvos.append(fname)
                    else:
                        erros.append(f"{arq.name} — vazio")
                except Exception as e:
                    erros.append(f"{arq.name} — {e}")
            barra.empty()
            if salvos:
                st.success(f"Importados: {', '.join(salvos)}")
            if erros:
                st.error("\n".join(erros))
            if salvos:
                st.rerun()

    st.divider()
    filtro = st.text_input("Filtrar por nome (contém):", key="repo_pareceres_filtro")

    arquivos = docs
    if filtro.strip():
        f_low = filtro.strip().lower()
        arquivos = [a for a in arquivos if f_low in a["nome"].lower()]

    if not arquivos:
        st.info("Nenhum documento corresponde ao filtro ou o repositório está vazio.")
    else:
        nomes = [a["nome"] for a in arquivos]
        escolha = st.selectbox("Selecione para pré-visualizar:", nomes, key="repo_prev_parecer")
        conteudo = read_document("parecer", escolha)
        st.text_area(
            "Pré-visualização",
            conteudo or "(vazio)",
            height=320,
            disabled=True,
            key="repo_prev_texto",
        )
        if st.button("Remover do repositório", key="repo_del_parecer"):
            delete_document("parecer", escolha)
            st.rerun()

    st.divider()
    st.subheader("Feedback da equipa")
    st.caption("Sugestões sobre a qualidade dos pareceres gerados.")

    resumo = resumo_feedbacks(category="parecer")
    if resumo["total"] > 0:
        f1, f2 = st.columns(2)
        f1.metric("Total de feedbacks", resumo["total"])
        f2.metric(
            "Avaliação média",
            f"{resumo['media']} / 5" if resumo["media"] else "—",
        )

    municipio_fb = st.text_input(
        "Município / proposta (referência):",
        value=(st.session_state.get("dados_extraidos") or {}).get("municipio", ""),
        key="fb_municipio_repo",
    )
    secao_fb = st.selectbox(
        "Secção avaliada:",
        options=SECOES_OPCOES,
        key="fb_secao_repo",
    )
    avaliacao_fb = st.select_slider(
        "Avaliação:",
        options=[1, 2, 3, 4, 5],
        value=3,
        format_func=lambda v: AVALIACOES[v],
        key="fb_avaliacao_repo",
    )
    comentario_fb = st.text_area(
        "Comentário:",
        height=100,
        key="fb_comentario_repo",
    )
    autor_fb = st.text_input("Nome (opcional):", key="fb_autor_repo")

    if st.button("Registar feedback", key="btn_feedback_repo"):
        if comentario_fb.strip():
            ok = save_feedback(
                "parecer",
                municipio_fb,
                secao_fb,
                avaliacao_fb,
                comentario_fb,
                autor=autor_fb,
                provedor_ia=llm_config.provider,
            )
            if ok:
                st.success("Feedback registado.")
                st.rerun()
            else:
                st.error("Não foi possível guardar.")
        else:
            st.warning("Escreva um comentário.")

    feedbacks = list_feedbacks(category="parecer", limite=15)
    if feedbacks:
        st.markdown("#### Feedbacks recentes")
        for fb in feedbacks:
            with st.expander(
                f"{AVALIACOES.get(fb.get('avaliacao', 3), '?')} · "
                f"{fb.get('municipio', '—')} · {str(fb.get('timestamp', ''))[:10]}",
                expanded=False,
            ):
                if fb.get("comentario"):
                    st.markdown(fb["comentario"])


def render_repositorio_portarias(llm_config: LLMConfig) -> None:
    """Repositório de portarias: leitura, upload múltiplo e feedback (paridade com pareceres)."""
    st.header("📂 Repositório de Portarias")
    st.caption(
        "Consulta e importação de portarias. Para **redigir** novas, use **Gerador de Portarias**."
    )

    docs = list_documents("portaria")
    n_docs = len(docs)
    tchars = total_chars("portaria")
    m1, m2 = st.columns(2)
    m1.metric("Documentos no repositório", n_docs)
    m2.metric(
        "Volume total",
        f"{round(tchars / 1000)} mil chars" if tchars else "—",
    )

    _painel_limpar_repositorio(
        "portaria",
        label_tipo="portarias",
        key_prefix="repo_port",
        n_docs=n_docs,
    )

    st.markdown("#### Importar documentos")
    st.caption(
        f"Formatos aceites: **{', '.join(REPO_UPLOAD_TYPES)}**. "
        "O texto extraído alimenta o contexto do assistente (RAG)."
    )
    up_pt = st.file_uploader(
        "Ficheiros:",
        type=REPO_UPLOAD_TYPES,
        accept_multiple_files=True,
        key="upload_repo_portarias_multi",
    )
    if up_pt and len(up_pt) > 15:
        st.warning("Máximo 15 ficheiros por vez.")
        up_pt = up_pt[:15]

    if st.button("Importar para o repositório", key="btn_import_repo_portarias"):
        if not up_pt:
            st.warning("Selecione pelo menos um ficheiro.")
        else:
            salvos, erros = [], []
            barra = st.progress(0, text="A processar…")
            for i, arq in enumerate(up_pt):
                barra.progress(
                    (i + 1) / len(up_pt),
                    text=f"{arq.name} ({i + 1}/{len(up_pt)})",
                )
                stem = arq.name.rsplit(".", 1)[0].replace(" ", "_").replace(".", "_")
                ext = arq.name.rsplit(".", 1)[-1].lower() if "." in arq.name else ""
                try:
                    if ext in ("md", "txt", "htm", "html"):
                        conteudo = arq.read().decode("utf-8", errors="replace")
                    else:
                        conteudo = extrair_texto_arquivo(arq, arq.name)
                    if conteudo and conteudo.strip():
                        fname = f"{stem}.md"
                        save_document("portaria", fname, conteudo.strip())
                        salvos.append(fname)
                    else:
                        erros.append(f"{arq.name} — vazio")
                except Exception as e:
                    erros.append(f"{arq.name} — {e}")
            barra.empty()
            if salvos:
                st.success(f"Importados: {', '.join(salvos)}")
            if erros:
                st.error("\n".join(erros))
            if salvos:
                st.rerun()

    st.divider()
    filtro = st.text_input("Filtrar por nome (contém):", key="repo_portarias_filtro")
    arquivos = docs
    if filtro.strip():
        f_low = filtro.strip().lower()
        arquivos = [a for a in arquivos if f_low in a["nome"].lower()]

    if not arquivos:
        st.info("Nenhum documento corresponde ao filtro ou o repositório está vazio.")
    else:
        nomes = [a["nome"] for a in arquivos]
        escolha = st.selectbox("Selecione para pré-visualizar:", nomes, key="repo_prev_portarias")
        conteudo = read_document("portaria", escolha)
        st.text_area(
            "Pré-visualização",
            conteudo or "(vazio)",
            height=320,
            disabled=True,
            key="repo_prev_texto_port",
        )
        if st.button("Remover do repositório", key="repo_del_portaria"):
            delete_document("portaria", escolha)
            st.rerun()

    st.divider()
    st.subheader("Feedback da equipa")
    st.caption("Sugestões sobre a qualidade das portarias e do fluxo de geração.")

    resumo = resumo_feedbacks(category="portaria")
    if resumo["total"] > 0:
        f1, f2 = st.columns(2)
        f1.metric("Total de feedbacks", resumo["total"])
        f2.metric(
            "Avaliação média",
            f"{resumo['media']} / 5" if resumo["media"] else "—",
        )

    municipio_fb = st.text_input(
        "Município / proposta (referência):",
        value=(st.session_state.get("dados_extraidos") or {}).get("municipio", ""),
        key="fb_municipio_repo_port",
    )
    secao_fb = st.selectbox(
        "Secção avaliada:",
        options=SECOES_OPCOES,
        key="fb_secao_repo_port",
    )
    avaliacao_fb = st.select_slider(
        "Avaliação:",
        options=[1, 2, 3, 4, 5],
        value=3,
        format_func=lambda v: AVALIACOES[v],
        key="fb_avaliacao_repo_port",
    )
    comentario_fb = st.text_area(
        "Comentário:",
        height=100,
        key="fb_comentario_repo_port",
    )
    autor_fb = st.text_input("Nome (opcional):", key="fb_autor_repo_port")

    if st.button("Registar feedback", key="btn_feedback_repo_port"):
        if comentario_fb.strip():
            ok = save_feedback(
                "portaria",
                municipio_fb,
                secao_fb,
                avaliacao_fb,
                comentario_fb,
                autor=autor_fb,
                provedor_ia=llm_config.provider,
            )
            if ok:
                st.success("Feedback registado.")
                st.rerun()
            else:
                st.error("Não foi possível guardar.")
        else:
            st.warning("Escreva um comentário.")

    feedbacks = list_feedbacks(category="portaria", limite=15)
    if feedbacks:
        st.markdown("#### Feedbacks recentes")
        for fb in feedbacks:
            with st.expander(
                f"{AVALIACOES.get(fb.get('avaliacao', 3), '?')} · "
                f"{fb.get('municipio', '—')} · {str(fb.get('timestamp', ''))[:10]}",
                expanded=False,
            ):
                if fb.get("comentario"):
                    st.markdown(fb["comentario"])


def render_aba_enviar_ao_repositorio(
    _llm_config: LLMConfig,
    tipos_aceitos: list,
    tipos_label: str,
    *,
    category: Category = "parecer",
) -> None:
    """Importação de documentos validados e gravação do Markdown da sessão."""
    if category == "parecer":
        st.subheader("📚 Enviar ao repositório de pareceres")
        st.caption(
            "Aqui **escreve-se** no repositório (importação ou gravação do parecer gerado). "
            "Para **consultar** o histórico, use **Repositório de Pareceres**."
        )
        md_state_key = "parecer_md"
        prefixo = "Parecer"
    else:
        st.subheader("📚 Enviar ao repositório de portarias")
        st.caption(
            "Aqui **escreve-se** no repositório (importação ou gravação da portaria gerada). "
            "Para **consultar** o histórico, use **Repositório de Portarias**."
        )
        md_state_key = "portaria_md"
        prefixo = "Portaria"

    st.markdown("#### Importar documentos validados")
    st.caption(
        f"Formatos: **{tipos_label}** e **.md**, **.txt**, **.html**. "
        "O texto extraído alimenta a referência de estilo da IA."
    )
    arquivos_bib = st.file_uploader(
        "Ficheiros:",
        type=tipos_aceitos + ["md", "txt", "htm", "html"],
        accept_multiple_files=True,
        key=f"upload_biblioteca_{category}",
    )
    if arquivos_bib and len(arquivos_bib) > 10:
        st.warning("Máximo 10 ficheiros por vez.")
        arquivos_bib = arquivos_bib[:10]

    if st.button("Importar para o repositório", key=f"btn_salvar_bib_{category}"):
        if not arquivos_bib:
            st.warning("Selecione pelo menos um ficheiro.")
        else:
            salvos, erros = [], []
            barra = st.progress(0, text="A processar…")
            for i, arq in enumerate(arquivos_bib):
                barra.progress(
                    (i + 1) / len(arquivos_bib),
                    text=f"{arq.name} ({i + 1}/{len(arquivos_bib)})",
                )
                ext = arq.name.rsplit(".", 1)[-1].lower()
                nome_auto = arq.name.rsplit(".", 1)[0].replace(" ", "_").replace(".", "_")
                try:
                    if ext in ("md", "txt", "htm", "html"):
                        conteudo = arq.read().decode("utf-8", errors="replace")
                    else:
                        conteudo = extrair_texto_arquivo(arq, arq.name)
                    if conteudo and conteudo.strip():
                        fname = f"{nome_auto}.md"
                        save_document(category, fname, conteudo.strip())
                        salvos.append(fname)
                    else:
                        erros.append(f"{arq.name} — vazio")
                except Exception as e:
                    erros.append(f"{arq.name} — {e}")
            barra.empty()
            if salvos:
                st.success(f"Importados: {', '.join(salvos)}")
            if erros:
                st.error("\n".join(erros))
            if salvos:
                st.rerun()

    if st.session_state.get(md_state_key):
        st.divider()
        st.markdown(f"#### Gravar {prefixo.lower()} desta sessão")
        mun_atual = (st.session_state.get("dados_extraidos") or {}).get(
            "municipio", "municipio"
        )
        nome_auto = st.text_input(
            "Nome do ficheiro:",
            value=f"{prefixo}_{mun_atual.replace(' ', '_')}_{datetime.now().strftime('%Y%m')}",
            key=f"nome_auto_bib_{category}",
        )
        if st.button(
            f"Gravar {prefixo.lower()} atual no repositório",
            key=f"btn_salvar_atual_{category}",
        ):
            if nome_auto.strip():
                body = st.session_state[md_state_key]
                save_document(category, f"{nome_auto.strip()}.md", body)
                st.success("Gravado.")
                st.rerun()
