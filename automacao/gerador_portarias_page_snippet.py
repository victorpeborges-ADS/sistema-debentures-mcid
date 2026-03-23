_col_trabalho, _col_assistente = st.columns([1.65, 1.0], gap="large")
with _col_trabalho:
    tab_rapido, tab1, tab2, tab3, tab4, tab_envio = st.tabs([
        "Submissão Rápida",
        "1. Upload do PDF",
        "2. Dados do Município",
        "3. Crivo Normativo",
        "4. Portaria Final",
        "📚 Enviar ao repositório",
    ])

    # ===== TAB SUBMISSÃO RÁPIDA (Intranet) =====
    with tab_rapido:
        st.header(PORTARIA_RAPIDO_HEADER)

        st.info(texto_info_submissao_portaria(TIPOS_LABEL))

        col_up, col_mun = st.columns([1, 1])

        with col_up:
            uploads_rapido = st.file_uploader(
                f"Arquivos da proposta ({TIPOS_LABEL}):",
                type=TIPOS_ACEITOS,
                accept_multiple_files=True,
                key="rapido_upload",
            )

        with col_mun:
            estados = ibge_listar_estados()
            uf_opcoes = {e["sigla"]: e for e in estados}
            uf_rapido = st.selectbox(
                "UF do município beneficiado:",
                options=list(uf_opcoes.keys()),
                index=list(uf_opcoes.keys()).index("PR") if "PR" in uf_opcoes else 0,
                key="rapido_uf",
            )
            if uf_rapido:
                uf_obj = uf_opcoes[uf_rapido]
                municipios = ibge_listar_municipios(uf_obj["id"])
                mun_map = {m["nome"]: m for m in municipios}
                mun_rapido = st.selectbox(
                    "Município beneficiado:",
                    options=list(mun_map.keys()),
                    key="rapido_mun",
                )
                municipio_rapido = mun_map.get(mun_rapido) if mun_rapido else None

        # Painel de arquivos carregados
        if uploads_rapido:
            st.subheader(f"{len(uploads_rapido)} arquivo(s) carregado(s)")
            cols = st.columns(min(len(uploads_rapido), 4))
            for i, arq in enumerate(uploads_rapido):
                fmt = detectar_formato(arq.name)
                ext = arq.name.lower().rsplit(".", 1)[-1]
                icone = {
                    "pdf": "📄", "html": "🌐", "htm": "🌐",
                    "docx": "📝", "doc": "📝",
                    "xlsx": "📊", "xls": "📊", "csv": "📊",
                    "kml": "🗺️", "kmz": "🗺️",
                    "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️",
                    "tiff": "🖼️", "tif": "🖼️", "bmp": "🖼️",
                    "gif": "🖼️", "webp": "🖼️",
                }.get(ext, "📎")
                cols[i % 4].metric(
                    label=f"{icone} {arq.name[:25]}{'…' if len(arq.name) > 25 else ''}",
                    value=fmt,
                    delta=f"{arq.size / 1024:.0f} KB",
                )

            tem_kml = any(
                f.name.lower().endswith((".kml", ".kmz")) for f in uploads_rapido
            )
            tem_img = any(
                f.name.lower().rsplit(".", 1)[-1] in {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif", "webp"}
                for f in uploads_rapido
            )
            if tem_kml:
                st.success("🗺️ KML/KMZ detectado — item 1 do checklist (perímetro) será marcado como **Cumprida** automaticamente.")
            if tem_img:
                _metodo_img = (
                    "visão por IA + OCR" if suporta_visao(llm_config) else "OCR"
                )
                st.info(f"🖼️ Imagem(ns) detectada(s) — serão processadas por **{_metodo_img}**.")

        # ---- Contexto Adicional (opcional) ----
        with st.expander("➕ Contexto adicional (opcional)", expanded=False):
            st.caption(
                "Use este painel para enriquecer a análise com informações específicas do município "
                "ou do projeto que não estão nos arquivos enviados. Tudo aqui é **eletivo** — "
                "deixe em branco se não precisar."
            )

            ctx_texto = st.text_area(
                "Observações do analista sobre o município / projeto:",
                placeholder=(
                    "Ex: O município tem histórico de atrasos em licitações.\n"
                    "A PPP foi homologada pelo TCE/PR em fevereiro de 2026.\n"
                    "A área de intervenção abrange as zonas norte e leste conforme Plano Diretor 2022."
                ),
                height=120,
                key="ctx_texto_rapido",
            )

            st.markdown("**URLs de referência** (portais, notícias, estudos, planos diretores):")

            # Até 3 URLs
            ctx_urls_input = []
            for i in range(1, 4):
                col_url, col_btn = st.columns([4, 1])
                url_val = col_url.text_input(
                    f"URL {i}:",
                    placeholder="https://...",
                    key=f"ctx_url_{i}_rapido",
                    label_visibility="collapsed",
                )
                if url_val:
                    ctx_urls_input.append(url_val)
                    cached = st.session_state.ctx_urls_conteudo.get(url_val)
                    if col_btn.button("Buscar", key=f"ctx_fetch_{i}_rapido"):
                        with st.spinner(f"Buscando {url_val[:50]}…"):
                            texto_url, ok, msg = buscar_url_contexto(url_val)
                            st.session_state.ctx_urls_conteudo[url_val] = texto_url if ok else ""
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)
                        cached = st.session_state.ctx_urls_conteudo.get(url_val)

                    if cached:
                        st.caption(f"✅ Conteúdo em cache ({len(cached):,} chars) — será usado na análise.")
                        with st.expander(f"Preview: {url_val[:60]}", expanded=False):
                            st.text(cached[:600] + ("…" if len(cached) > 600 else ""))
                    elif url_val and url_val in st.session_state.ctx_urls_conteudo:
                        st.caption("⚠️ URL buscada mas sem conteúdo recuperável.")

        _aviso_tempo = {
            "ollama":       "⏳ Sem GPU: o processo completo pode levar **15–30 minutos**. Não feche o navegador.",
            "groq":         "⚡ Groq API: o processo completo leva aproximadamente **30–60 segundos**.",
            "mistral":      "☁️ Mistral AI: o processo completo leva aproximadamente **45–90 segundos**.",
            "openai":       "☁️ OpenAI API: o processo completo leva aproximadamente **1–2 minutos**.",
            "azure_openai": "☁️ Azure OpenAI: o processo completo leva aproximadamente **1–2 minutos**.",
            "anthropic":    "☁️ Claude API: o processo completo leva aproximadamente **45–90 segundos**.",
        }
        st.caption(_aviso_tempo.get(llm_config.provider, "Aguarde o processamento completo. Não feche o navegador."))

        if st.button("Analisar e gerar portaria", type="primary", key="rapido_analisar"):
            if not uploads_rapido:
                st.error("Envie pelo menos um arquivo.")
            elif not municipio_rapido:
                st.error("Selecione o município beneficiado.")
            else:
                cod = municipio_rapido["id"]
                nome = municipio_rapido["nome"]

                progress = st.progress(0, text=f"Extraindo texto de {len(uploads_rapido)} arquivo(s)...")
                texto_consolidado, meta = extrair_textos_multiplos(uploads_rapido, llm_config)

                # Exibe resumo da extração
                ok = [a for a in meta["arquivos"] if a["ok"]]
                erros = [a for a in meta["arquivos"] if not a["ok"]]
                if erros:
                    st.warning(f"⚠️ {len(erros)} arquivo(s) não processado(s): {', '.join(a['nome'] for a in erros)}")
                if not texto_consolidado:
                    st.error("Nenhum texto extraído dos arquivos enviados.")
                    st.stop()

                st.session_state.meta_arquivos = meta
                tem_kml = meta["tem_kml_kmz"]

                # Injeta contexto adicional do operador (se fornecido)
                ctx_manual = st.session_state.get("ctx_texto_rapido", "")
                ctx_urls_validas = [
                    u for u in ctx_urls_input
                    if st.session_state.ctx_urls_conteudo.get(u)
                ]
                bloco_ctx = preparar_contexto_adicional(
                    texto_manual=ctx_manual,
                    urls=ctx_urls_validas,
                    conteudos_urls=st.session_state.ctx_urls_conteudo,
                )
                if bloco_ctx:
                    texto_consolidado = bloco_ctx + "\n\n" + texto_consolidado
                    st.info(f"Contexto adicional injetado ({len(bloco_ctx):,} chars).")

                progress.progress(0.08, text=f"Extraindo dados estruturados da proposta ({_ia_label})...")
                dados = chamada1_extracao(texto_consolidado, llm_config)
                if not dados:
                    st.warning("Ollama indisponível. Dados básicos serão usados.")
                    dados = {
                        "proponente": "", "cnpj": "", "natureza": "", "modalidade": "",
                        "objeto": "", "valor_financiamento": "", "valor_contrapartida": "",
                        "valor_total": "", "municipio": nome, "uf": uf_rapido,
                        "processo_sei": "", "numero_proposta": "",
                    }

                progress.progress(0.15, text="Buscando dados IBGE...")
                ibge = ibge_dados_completos(cod, nome, uf_rapido)
                progress.progress(0.28, text="Buscando CAPAG (Tesouro)...")
                capag = capag_buscar_municipio(cod)
                progress.progress(0.40, text=PROGRESS_LEGIS_MCID)
                legis = legislacao_verificar()
                progress.progress(0.50, text="Buscando IDH (Atlas Brasil)...")
                idh = atlas_buscar_idh(cod)
                progress.progress(0.60, text="Buscando indicadores SEBRAE...")
                sebrae = sebrae_buscar_municipio(cod, nome)
                progress.progress(0.65, text="Consultando legislação federal (Planalto)...")
                planalto = planalto_buscar_todas()

                progress.progress(0.68, text="Avaliando conformidade normativa...")
                conf = avaliar_conformidade(dados)
                capag_r = avaliar_capag(capag.capag if capag and capag.encontrado else "")

                progress.progress(0.74, text=f"Gerando Sumário Executivo ({_ia_label})...")
                dados_mun = {
                    "populacao": ibge.populacao_estimada or "",
                    "area": ibge.area_km2 or "",
                    "pib_per_capita": ibge.pib_per_capita or "",
                    "capag": capag.capag if capag and capag.encontrado else "",
                    "municipio": nome,
                    "uf": uf_rapido,
                }
                sumario = chamada2_sumario(dados, dados_mun, llm_config)
                if not sumario:
                    sumario = (
                        f"**1.1.** O presente instrumento apresenta a análise de enquadramento "
                        f"de proposta de {dados.get('objeto', 'investimento')} no Município de {nome}/{uf_rapido}.\n\n"
                        f"**1.2.** Em síntese, o proponente busca captação via **debêntures incentivadas** para "
                        f"{dados.get('objeto', 'a intervenção proposta')}.\n\n"
                        f"**1.3.** Nesse sentido, solicita o enquadramento no arcabouço de **debêntures incentivadas**, "
                        f"nos termos da legislação aplicável (ex.: Lei nº 12.431/2011 e normativos correlatos)."
                    )

                progress.progress(0.82, text=f"Gerando Análise Normativa ({_ia_label})...")
                conf_txt = conformidade_texto(conf, capag_r)
                capag_info = {
                    "capag": capag.capag or "",
                    "nota_endividamento": capag.nota_endividamento or "",
                    "nota_poupanca": capag.nota_poupanca or "",
                    "nota_liquidez": capag.nota_liquidez or "",
                } if capag else {}
                analise = chamada3_analise(dados, conf_txt, capag_info, llm_config,
                                           dados_planalto=planalto)

                progress.progress(0.90, text="Avaliando Checklist...")
                checklist = chamada4_checklist(
                    texto_consolidado, llm_config,
                    tem_kml_kmz=tem_kml,
                )
                for item in CHECKLIST_ITEMS:
                    if str(item["id"]) not in checklist:
                        checklist[str(item["id"])] = "Não disponível"
                if tem_kml:
                    checklist["1"] = "Cumprida"

                progress.progress(0.93, text=f"Contextualizando objeto no município ({_ia_label})...")
                contexto_obj = chamada5_contexto_objeto(
                    texto_pdf=texto_consolidado,
                    objeto=dados.get("objeto", ""),
                    municipio=dados.get("municipio") or dados_mun.get("municipio", ""),
                    uf=dados.get("uf") or dados_mun.get("uf", ""),
                    host_or_config=llm_config,
                )

                progress.progress(0.95, text="Gerando documento final...")
                dados_mun["idhm"] = f"{idh.idhm:.3f}" if idh and idh.idhm else ""
                parecer = gerar_portaria_md(
                    dados=dados,
                    sumario=sumario,
                    analise=analise,
                    checklist=checklist,
                    conformidade_results=conf,
                    capag_result=capag_r,
                    dados_municipio=dados_mun,
                    dados_ibge=ibge,
                    dados_capag=capag,
                    dados_idh=idh,
                    dados_sebrae=sebrae,
                    dados_planalto=planalto,
                    contexto_objeto=contexto_obj,
                )

                st.session_state.texto_pdf = texto_consolidado
                st.session_state.dados_extraidos = dados
                st.session_state.dados_ibge = ibge
                st.session_state.dados_capag = capag
                st.session_state.dados_legis = legis
                st.session_state.dados_idh = idh
                st.session_state.dados_sebrae = sebrae
                st.session_state.dados_planalto = planalto
                st.session_state.conformidade = conf
                st.session_state.capag_result = capag_r
                st.session_state.sumario = sumario
                st.session_state.analise = analise
                st.session_state.checklist = checklist
                st.session_state.portaria_md = parecer
                st.session_state.municipio_selecionado = municipio_rapido
                st.session_state.uf_selecionada = uf_rapido

                progress.progress(1.0, text="Concluído!")
                st.success(
                    f"Análise concluída! {len(ok)} arquivo(s) processado(s) "
                    f"({meta['total_chars']:,} caracteres consolidados). "
                    "Visualize e baixe a portaria abaixo."
                )

                # Badges das fontes consultadas
                _f1, _f2, _f3, _f4, _f5 = st.columns(5)
                _f1.metric("IBGE", "✅ OK" if ibge and ibge.populacao_estimada else "⚠️ Parcial")
                _f2.metric("CAPAG", f"✅ {capag.capag}" if capag and capag.encontrado else "⚠️ N/D")
                _f3.metric("IDH/Atlas", f"✅ {idh.idhm:.3f}" if idh and idh.encontrado else "⚠️ N/D")
                _f4.metric(METRICA_LEGIS_MCID, "✅ Vigente" if legis and legis.acessivel else "⚠️ N/D")
                _f5.metric(
                    "CEMPRE/SEBRAE",
                    f"✅ {sebrae.empresas_ativas:,} emp.".replace(",", ".")
                    if sebrae and sebrae.encontrado and sebrae.empresas_ativas
                    else (f"✅ {sebrae.pessoal_ocupado_pct:.1f}% ocup."
                          if sebrae and sebrae.encontrado and sebrae.pessoal_ocupado_pct
                          else ("✅ OK" if sebrae and sebrae.encontrado else "⚠️ N/D"))
                )

                # Badges Planalto + fontes complementares (1 por norma)
                _pl_items = list(planalto.normas.items())
                if _pl_items:
                    _p_cols = st.columns(len(_pl_items))
                    for _col, (_chave, _norma) in zip(_p_cols, _pl_items):
                        _ok = _norma and _norma.acessivel
                        _cache = " (cache)" if (_norma and _norma.cache_usado) else ""
                        _sig = (_norma.sigla if _norma else _chave)[:24]
                        _col.metric(
                            _sig,
                            f"{'✅' if _ok else '⚠️'} {'OK' + _cache if _ok else 'Indisponível'}",
                        )

        # Painel de arquivos processados (pós-análise)
        if st.session_state.meta_arquivos:
            meta = st.session_state.meta_arquivos
            with st.expander(f"📂 Arquivos processados ({len(meta['arquivos'])})", expanded=False):
                for arq in meta["arquivos"]:
                    ext = arq["nome"].lower().rsplit(".", 1)[-1]
                    icone = {"pdf": "📄", "html": "🌐", "htm": "🌐", "docx": "📝",
                             "doc": "📝", "xlsx": "📊", "xls": "📊", "csv": "📊",
                             "kml": "🗺️", "kmz": "🗺️", "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "tiff": "🖼️", "tif": "🖼️", "bmp": "🖼️", "gif": "🖼️", "webp": "🖼️"}.get(ext, "📎")
                    status = "✅" if arq["ok"] else "❌"
                    chars = f" — {arq['chars']:,} chars" if arq["ok"] else f" — {arq.get('erro', 'erro')}"
                    st.write(f"{status} {icone} **{arq['nome']}** ({arq['formato']}){chars}")
                if meta["tem_kml_kmz"]:
                    st.info("🗺️ Arquivo KML/KMZ incluído — perímetro de intervenção reconhecido.")

        if st.session_state.portaria_md:
            st.subheader("Portaria gerada")
            st.markdown(st.session_state.portaria_md)
            r1, r2 = st.columns(2)
            with r1:
                st.download_button(
                    label="Download Word (.docx)",
                    data=md_para_docx_bytes(st.session_state.portaria_md),
                    file_name=EXPORT_PORTARIA_DOCX_NAME,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="rapido_download_docx_port",
                )
            with r2:
                st.download_button(
                    label="Download Markdown (.md)",
                    data=st.session_state.portaria_md,
                    file_name=EXPORT_PORTARIA_MD_NAME,
                    mime="text/markdown",
                    key="rapido_download_md_port",
                )

    # ===== TAB 1: Upload =====
    with tab1:
        st.header("Upload da Proposta")
        st.info(
            "Envie os documentos da proposta. Formatos aceitos: "
            "**PDF, Word (.docx), HTML, Planilhas (.xlsx/.csv), KML/KMZ**. "
            "Vários arquivos podem ser enviados de uma vez — todos serão consolidados antes da extração."
        )

        uploads_tab1 = st.file_uploader(
            "Arquivo(s) da proposta:",
            type=list(_EXTENSOES_SUPORTADAS.keys()),
            accept_multiple_files=True,
            key="tab1_upload",
        )

        col1, col2 = st.columns(2)

        with col1:
            if uploads_tab1 and st.button("Extrair e consolidar textos", type="primary"):
                with st.spinner(f"Extraindo texto de {len(uploads_tab1)} arquivo(s)..."):
                    texto_consolidado, meta = extrair_textos_multiplos(uploads_tab1, llm_config)
                    if texto_consolidado:
                        st.session_state.texto_pdf = texto_consolidado
                        st.session_state.meta_arquivos = meta
                        ok = [a for a in meta["arquivos"] if a["ok"]]
                        st.success(
                            f"{len(ok)}/{len(meta['arquivos'])} arquivo(s) extraído(s) — "
                            f"{meta['total_chars']:,} caracteres totais."
                        )
                        if meta["tem_kml_kmz"]:
                            st.info("🗺️ KML/KMZ detectado — perímetro será marcado como Cumprida no checklist.")
                    else:
                        st.error("Nenhum texto extraído. Verifique os arquivos enviados.")

        with col2:
            _lbl_ia = DESCRICAO_PRIVACIDADE[llm_config.provider]["label"]
            if st.session_state.texto_pdf and st.button(f"Extrair dados via {_lbl_ia}"):
                with st.spinner(f"{_lbl_ia} analisando proposta..."):
                    dados = chamada1_extracao(
                        st.session_state.texto_pdf, llm_config
                    )
                    if dados:
                        st.session_state.dados_extraidos = dados
                        st.success("Dados extraídos com sucesso!")
                    else:
                        st.error(f"Falha na extração. Verifique a conexão com {_lbl_ia}.")

        if st.session_state.meta_arquivos:
            meta = st.session_state.meta_arquivos
            with st.expander(f"📂 Arquivos carregados ({len(meta['arquivos'])})"):
                for arq in meta["arquivos"]:
                    ext = arq["nome"].lower().rsplit(".", 1)[-1]
                    icone = {"pdf": "📄", "html": "🌐", "htm": "🌐", "docx": "📝",
                             "doc": "📝", "xlsx": "📊", "xls": "📊", "csv": "📊",
                             "kml": "🗺️", "kmz": "🗺️", "jpg": "🖼️", "jpeg": "🖼️", "png": "🖼️", "tiff": "🖼️", "tif": "🖼️", "bmp": "🖼️", "gif": "🖼️", "webp": "🖼️"}.get(ext, "📎")
                    st.write(
                        f"{'✅' if arq['ok'] else '❌'} {icone} **{arq['nome']}** "
                        f"({arq['formato']}) — {arq.get('chars', 0):,} chars"
                    )

        # ---- Contexto Adicional (Tab 1) ----
        with st.expander("➕ Contexto adicional (opcional)", expanded=False):
            st.caption(
                "Informações específicas sobre o município ou projeto que complementam os documentos enviados. "
                "Eletivo — deixe em branco se não necessário."
            )
            ctx_texto_tab1 = st.text_area(
                "Observações do analista:",
                placeholder="Ex: histórico de pendências, decisões do TCE, características urbanas relevantes...",
                height=100,
                key="ctx_texto_tab1",
            )
            st.markdown("**URLs de referência:**")
            ctx_urls_tab1 = []
            for i in range(1, 4):
                col_u, col_b = st.columns([4, 1])
                u = col_u.text_input(
                    f"URL {i}:", placeholder="https://...",
                    key=f"ctx_url_{i}_tab1", label_visibility="collapsed",
                )
                if u:
                    ctx_urls_tab1.append(u)
                    if col_b.button("Buscar", key=f"ctx_fetch_{i}_tab1"):
                        with st.spinner(f"Buscando {u[:50]}…"):
                            txt, ok, msg = buscar_url_contexto(u)
                            st.session_state.ctx_urls_conteudo[u] = txt if ok else ""
                            st.success(msg) if ok else st.error(msg)
                    cached = st.session_state.ctx_urls_conteudo.get(u)
                    if cached:
                        st.caption(f"✅ {len(cached):,} chars em cache.")

            if st.button("Aplicar contexto ao texto consolidado", key="ctx_apply_tab1"):
                bloco = preparar_contexto_adicional(
                    texto_manual=ctx_texto_tab1,
                    urls=[u for u in ctx_urls_tab1 if st.session_state.ctx_urls_conteudo.get(u)],
                    conteudos_urls=st.session_state.ctx_urls_conteudo,
                )
                if bloco and st.session_state.texto_pdf:
                    st.session_state.texto_pdf = bloco + "\n\n" + st.session_state.texto_pdf
                    st.success(f"Contexto adicionado ({len(bloco):,} chars). Texto total: {len(st.session_state.texto_pdf):,} chars.")
                elif bloco:
                    st.session_state.texto_pdf = bloco
                    st.success("Contexto aplicado.")
                else:
                    st.info("Nenhum contexto para aplicar.")

        if st.session_state.texto_pdf:
            with st.expander("Texto consolidado (primeiros 2000 caracteres)"):
                st.text(st.session_state.texto_pdf[:2000])

        if st.session_state.dados_extraidos:
            st.subheader("Dados Extraídos")
            dados = st.session_state.dados_extraidos

            c1, c2 = st.columns(2)
            with c1:
                dados["proponente"] = st.text_input("Proponente:", value=dados.get("proponente", ""))
                dados["cnpj"] = st.text_input("CNPJ:", value=dados.get("cnpj", ""))
                dados["natureza"] = st.text_input("Natureza:", value=dados.get("natureza", ""))
                dados["modalidade"] = st.selectbox(
                    "Modalidade:",
                    ["Modernização tecnológica urbana", "Reabilitação de Áreas Urbanas"],
                    index=0 if "modernização" in dados.get("modalidade", "").lower() else 1,
                )
            with c2:
                dados["objeto"] = st.text_area("Objeto:", value=dados.get("objeto", ""), height=100)
                dados["valor_financiamento"] = st.text_input(
                    "Valor Financiamento:", value=dados.get("valor_financiamento", "")
                )
                dados["valor_contrapartida"] = st.text_input(
                    "Valor Contrapartida:", value=dados.get("valor_contrapartida", "")
                )
                dados["valor_total"] = st.text_input(
                    "Valor Total:", value=dados.get("valor_total", "")
                )

            dados["processo_sei"] = st.text_input(
                "Processo SEI:", value=dados.get("processo_sei", "")
            )
            st.session_state.dados_extraidos = dados

    # ===== TAB 2: Dados do Municipio =====
    with tab2:
        st.header("Dados Públicos do Município")

        col_uf, col_mun = st.columns(2)

        with col_uf:
            estados = ibge_listar_estados()
            uf_opcoes = {e["sigla"]: e for e in estados}
            uf_sel = st.selectbox(
                "UF:",
                options=list(uf_opcoes.keys()),
                index=list(uf_opcoes.keys()).index("MG") if "MG" in uf_opcoes else 0,
            )
            st.session_state.uf_selecionada = uf_sel

        with col_mun:
            if uf_sel:
                uf_obj = uf_opcoes[uf_sel]
                municipios = ibge_listar_municipios(uf_obj["id"])
                mun_map = {m["nome"]: m for m in municipios}
                mun_sel = st.selectbox("Município:", options=list(mun_map.keys()))
                if mun_sel:
                    st.session_state.municipio_selecionado = mun_map[mun_sel]

        if st.button("Buscar dados do município", type="primary"):
            mun = st.session_state.municipio_selecionado
            if not mun:
                st.warning("Selecione um município.")
            else:
                cod = mun["id"]
                nome = mun["nome"]

                prog = st.progress(0, text="Buscando IBGE...")
                ibge = ibge_dados_completos(cod, nome, uf_sel)
                st.session_state.dados_ibge = ibge

                prog.progress(25, text="Buscando CAPAG...")
                capag = capag_buscar_municipio(cod)
                st.session_state.dados_capag = capag

                prog.progress(50, text=PROGRESS_LEGIS_MCID)
                legis = legislacao_verificar()
                st.session_state.dados_legis = legis

                prog.progress(70, text="Buscando IDH (Atlas Brasil)...")
                idh = atlas_buscar_idh(cod)
                st.session_state.dados_idh = idh

                prog.progress(85, text="Buscando indicadores SEBRAE...")
                sebrae = sebrae_buscar_municipio(cod, nome)
                st.session_state.dados_sebrae = sebrae

                prog.progress(93, text="Consultando legislação federal (Planalto)...")
                planalto = planalto_buscar_todas()
                st.session_state.dados_planalto = planalto

                prog.progress(100, text="Concluído!")
                st.success(f"Dados de {nome} – {uf_sel} carregados!")

        if st.session_state.dados_ibge:
            ibge = st.session_state.dados_ibge
            st.subheader(f"IBGE — {ibge.nome} ({ibge.uf})")

            ci1, ci2, ci3, ci4 = st.columns(4)
            ci1.metric("População Estimada", ibge.populacao_estimada or "N/D")
            ci2.metric("Área (km²)", ibge.area_km2 or "N/D")
            ci3.metric("PIB per capita", f"R$ {ibge.pib_per_capita}" if ibge.pib_per_capita else "N/D")

            idh = st.session_state.dados_idh
            ci4.metric("IDHM", f"{idh.idhm:.3f}" if idh and idh.idhm else "N/D")

            with st.expander("Sinopse Municipal completa"):
                for k, v in ibge.sinopse.items():
                    st.write(f"**{k}:** {v['valor']} ({v['ano']})")

            with st.expander("PIB Municipal"):
                for k, v in ibge.pib.items():
                    st.write(f"**{k}:** {v['valor']} ({v['ano']})")

            with st.expander("Frota de Veículos"):
                for k, v in ibge.frota.items():
                    st.write(f"**{k}:** {v['valor']} ({v['ano']})")

        if st.session_state.get("dados_sebrae"):
            sebrae = st.session_state.dados_sebrae
            st.subheader("Emprego & Negócios — CEMPRE / IBGE / SEBRAE")
            if sebrae.encontrado:
                # Linha 1: dados primários do CEMPRE (SIDRA 6449)
                if any([sebrae.empresas_ativas, sebrae.empregos_formais, sebrae.pessoal_total]):
                    st.caption("**IBGE SIDRA — CEMPRE (Cadastro Central de Empresas)**")
                    ca1, ca2, ca3, ca4 = st.columns(4)
                    ca1.metric(
                        "Empresas ativas",
                        f"{sebrae.empresas_ativas:,}".replace(",", ".") if sebrae.empresas_ativas else "N/D",
                        help="Número de empresas e outras organizações (CEMPRE/IBGE SIDRA T6449)",
                    )
                    ca2.metric(
                        "Trabalhadores assalariados",
                        f"{sebrae.empregos_formais:,}".replace(",", ".") if sebrae.empregos_formais else "N/D",
                        help="Pessoal ocupado assalariado — emprego formal (CEMPRE/IBGE SIDRA T6449)",
                    )
                    ca3.metric(
                        "Total de pessoas ocupadas",
                        f"{sebrae.pessoal_total:,}".replace(",", ".") if sebrae.pessoal_total else "N/D",
                        help="Pessoal ocupado total (formal + outros) — CEMPRE/IBGE SIDRA T6449",
                    )
                    _sal_str = (
                        f"R$ {sebrae.salario_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        if sebrae.salario_medio else "N/D"
                    )
                    ca4.metric(
                        "Salário médio mensal",
                        _sal_str,
                        delta=(
                            f"Massa: R$ {sebrae.salarios_anuais_mil/1_000:.1f} bi/ano".replace(".", ",")
                            if sebrae.salarios_anuais_mil and sebrae.salarios_anuais_mil >= 1_000 else None
                        ),
                        help="Calculado: (Salários anuais CEMPRE / assalariados) / 12 meses",
                    )

                # Linha 2: indicadores IBGE complementares
                if any([sebrae.pessoal_ocupado_pct, sebrae.receitas_realizadas_mil]):
                    st.caption("**IBGE — Indicadores Municipais (complemento)**")
                    cb1, cb2 = st.columns(2)
                    if sebrae.pessoal_ocupado_pct:
                        cb1.metric(
                            "Pessoal ocupado / pop. total",
                            f"{sebrae.pessoal_ocupado_pct:.1f}%",
                            help="Proporção da população empregada em empresas (IBGE ind. 60037)",
                        )
                    if sebrae.receitas_realizadas_mil:
                        cb2.metric(
                            "Receitas orçamentárias realizadas",
                            f"R$ {sebrae.receitas_realizadas_mil/1_000:.1f} mi".replace(".", ","),
                            help="Receitas orçamentárias municipais realizadas (IBGE ind. 47001, R$ mil)",
                        )

                st.caption(
                    f"Fonte: {sebrae.fonte}"
                    + (f" — Ano ref.: {sebrae.ano_ref}" if sebrae.ano_ref else "")
                    + f" | [Ver perfil municipal no IBGE Cidades]({sebrae.url_perfil})"
                    + f" | [DataSEBRAE]({SEBRAE_BASE})"
                )
            else:
                st.info(
                    f"Indicadores de emprego/negócios não disponíveis para este município via IBGE. "
                    f"{sebrae.erro or ''} "
                    f"[Ver perfil no IBGE Cidades]({sebrae.url_perfil}) | "
                    f"[DataSEBRAE]({SEBRAE_BASE})"
                )

        if st.session_state.dados_capag:
            capag = st.session_state.dados_capag
            st.subheader("CAPAG — Tesouro Nacional")
            if capag.encontrado:
                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("Nota CAPAG", capag.capag)
                cc2.metric("Endividamento", f"{capag.nota_endividamento}")
                cc3.metric("Poupança Corrente", f"{capag.nota_poupanca}")
                cc4.metric("Liquidez", f"{capag.nota_liquidez}")

                if capag.capag.upper() in ("C", "D"):
                    st.warning(
                        f"CAPAG {capag.capag} — Município com restrições para garantia da União. "
                        "Isso será refletido na análise normativa."
                    )
            else:
                st.warning("Município não encontrado na base CAPAG.")

        if st.session_state.get("dados_planalto"):
            planalto = st.session_state.dados_planalto
            st.subheader("Legislação Federal — Planalto.gov.br")
            for chave, norma in planalto.normas.items():
                _ico = "✅" if norma.acessivel else "⚠️"
                _cache_txt = " *(cache local)*" if norma.cache_usado else " *(web)*"
                with st.expander(
                    f"{_ico} {norma.label} — {norma.descricao}{_cache_txt if norma.acessivel else ''}",
                    expanded=False,
                ):
                    if norma.acessivel and norma.texto:
                        st.caption(f"Fonte: [{norma.url}]({norma.url})")
                        st.text_area(
                            "Texto extraído (primeiros 3.000 caracteres):",
                            value=norma.texto[:3000],
                            height=200,
                            disabled=True,
                            key=f"txt_planalto_{chave}",
                        )
                        st.caption(f"Total: {len(norma.texto):,} caracteres extraídos")
                    elif norma.erro:
                        st.warning(f"Não foi possível acessar: {norma.erro}")
                        st.markdown(f"[Acesse manualmente]({norma.url})")

        if st.session_state.dados_legis:
            legis = st.session_state.dados_legis
            st.subheader(SUBHEADER_LEGIS_MCID)
            if legis.acessivel:
                lc1, lc2 = st.columns(2)
                lc1.metric(
                    "IN MCID nº 18/2025",
                    "Vigente" if legis.in_18_2025_vigente else "Não localizada",
                )
                lc2.metric(
                    "Res. CCFGTS nº 897/2018",
                    "Vigente" if legis.res_897_2018_vigente else "Não localizada",
                )
                with st.expander("Normativos encontrados"):
                    for n in legis.normativos:
                        st.write(f"- {n}")
            else:
                st.warning("Página de legislação indisponível no momento.")

        if st.session_state.dados_idh and st.session_state.dados_idh.encontrado:
            idh = st.session_state.dados_idh
            st.subheader("IDH — Atlas Brasil")
            id1, id2, id3, id4 = st.columns(4)
            id1.metric("IDHM Geral", f"{idh.idhm:.3f}" if idh.idhm else "N/D")
            id2.metric("IDHM Educação", f"{idh.idhm_educacao:.3f}" if idh.idhm_educacao else "N/D")
            id3.metric("IDHM Longevidade", f"{idh.idhm_longevidade:.3f}" if idh.idhm_longevidade else "N/D")
            id4.metric("IDHM Renda", f"{idh.idhm_renda:.3f}" if idh.idhm_renda else "N/D")

    # ===== TAB 3: Crivo Normativo =====
    with tab3:
        st.header("Crivo Normativo Automatizado")
        _llm_tab3 = DESCRICAO_PRIVACIDADE[llm_config.provider]["label"]

        if not st.session_state.dados_extraidos:
            st.warning("Primeiro extraia os dados do PDF na aba 1.")
        elif not st.session_state.dados_ibge:
            st.warning("Primeiro busque os dados do município na aba 2.")
        else:
            dados = st.session_state.dados_extraidos
            ibge = st.session_state.dados_ibge
            capag = st.session_state.dados_capag

            st.subheader("Conformidade Determinística")
            if st.button("Avaliar conformidade"):
                conf = avaliar_conformidade(dados)
                st.session_state.conformidade = conf

                capag_nota = capag.capag if capag and capag.encontrado else ""
                capag_r = avaliar_capag(capag_nota)
                st.session_state.capag_result = capag_r

                for r in conf:
                    if r["conforme"] is True:
                        st.success(f"{r['regra']}: {r['detalhe']}")
                    elif r["conforme"] is False:
                        st.error(f"{r['regra']}: {r['detalhe']}")
                    else:
                        st.warning(f"{r['regra']}: {r['detalhe']}")

                if capag_r["conforme"] is True:
                    st.success(f"CAPAG: {capag_r['detalhe']}")
                elif capag_r["conforme"] is False:
                    st.error(f"CAPAG: {capag_r['detalhe']}")
                else:
                    st.warning(f"CAPAG: {capag_r['detalhe']}")

            st.divider()
            st.subheader(f"Geração via {_llm_tab3} (Sumário + Análise + Checklist)")

            if st.button(f"Gerar seções via {_llm_tab3}", type="primary"):
                if st.session_state.conformidade is None:
                    st.warning("Primeiro avalie a conformidade acima.")
                else:
                    dados_mun = {
                        "populacao": ibge.populacao_estimada or "",
                        "area": ibge.area_km2 or "",
                        "pib_per_capita": ibge.pib_per_capita or "",
                        "capag": capag.capag if capag and capag.encontrado else "",
                    }

                    prog = st.progress(0, text=f"Gerando Sumário Executivo ({_ia_label})...")
                    sumario = chamada2_sumario(dados, dados_mun, llm_config)
                    st.session_state.sumario = sumario

                    prog.progress(33, text=f"Gerando Análise Normativa ({_ia_label})...")
                    conf_txt = conformidade_texto(
                        st.session_state.conformidade, st.session_state.capag_result
                    )
                    capag_info = {}
                    if capag and capag.encontrado:
                        capag_info = {
                            "capag": capag.capag,
                            "nota_endividamento": capag.nota_endividamento,
                            "nota_poupanca": capag.nota_poupanca,
                            "nota_liquidez": capag.nota_liquidez,
                        }
                    analise = chamada3_analise(
                        dados,
                        conf_txt,
                        capag_info,
                        llm_config,
                        dados_planalto=st.session_state.get("dados_planalto"),
                    )
                    st.session_state.analise = analise

                    prog.progress(66, text=f"Avaliando Checklist ({_ia_label})...")
                    checklist = chamada4_checklist(
                        st.session_state.texto_pdf, llm_config
                    )
                    st.session_state.checklist = checklist

                    prog.progress(100, text="Concluído!")
                    st.success("Seções geradas com sucesso!")

            if st.session_state.sumario:
                with st.expander("Preview: Sumário Executivo", expanded=True):
                    st.session_state.sumario = st.text_area(
                        "Editar sumário:",
                        value=st.session_state.sumario,
                        height=200,
                        key="edit_sumario",
                    )

            if st.session_state.analise:
                with st.expander("Preview: Análise Normativa", expanded=True):
                    st.session_state.analise = st.text_area(
                        "Editar análise:",
                        value=st.session_state.analise,
                        height=200,
                        key="edit_analise",
                    )

            if st.session_state.checklist:
                with st.expander("Preview: Checklist", expanded=True):
                    for item in CHECKLIST_ITEMS:
                        status = st.session_state.checklist.get(str(item["id"]), "-")
                        new_status = st.selectbox(
                            f"Item {item['id']}: {item['doc']}",
                            ["Cumprida", "Não disponível", "Não cabível"],
                            index=["Cumprida", "Não disponível", "Não cabível"].index(status)
                            if status in ["Cumprida", "Não disponível", "Não cabível"] else 1,
                            key=f"check_{item['id']}",
                        )
                        st.session_state.checklist[str(item["id"])] = new_status

    # ===== TAB 4: Portaria Final =====
    with tab4:
        st.header("Portaria Final — Geração do Documento")

        can_generate = all([
            st.session_state.dados_extraidos,
            st.session_state.sumario,
            st.session_state.analise,
            st.session_state.checklist,
            st.session_state.conformidade,
            st.session_state.capag_result,
        ])

        if not can_generate:
            st.warning("Complete as abas 1, 2 e 3 antes de gerar a portaria final.")
        else:
            if st.button("Gerar Portaria Final", type="primary"):
                ibge_final = st.session_state.dados_ibge
                capag_final = st.session_state.dados_capag
                idh_final = st.session_state.dados_idh
                dados_mun = {
                    "populacao": ibge_final.populacao_estimada or "" if ibge_final else "",
                    "area": ibge_final.area_km2 or "" if ibge_final else "",
                    "pib_per_capita": ibge_final.pib_per_capita or "" if ibge_final else "",
                    "municipio": ibge_final.nome if ibge_final else "",
                    "uf": ibge_final.uf if ibge_final else "",
                    "capag": capag_final.capag if capag_final and capag_final.encontrado else "",
                }
                if idh_final and idh_final.idhm:
                    dados_mun["idhm"] = f"{idh_final.idhm:.3f}"

                contexto_obj_final = chamada5_contexto_objeto(
                    texto_pdf=st.session_state.texto_pdf or "",
                    objeto=(st.session_state.dados_extraidos or {}).get("objeto", ""),
                    municipio=(st.session_state.dados_extraidos or {}).get("municipio", "")
                              or (ibge_final.nome if ibge_final else ""),
                    uf=(st.session_state.dados_extraidos or {}).get("uf", "")
                       or (ibge_final.uf if ibge_final else ""),
                    host_or_config=llm_config,
                )

                parecer = gerar_portaria_md(
                    dados=st.session_state.dados_extraidos,
                    sumario=st.session_state.sumario,
                    analise=st.session_state.analise,
                    checklist=st.session_state.checklist,
                    conformidade_results=st.session_state.conformidade,
                    capag_result=st.session_state.capag_result,
                    dados_municipio=dados_mun,
                    dados_ibge=ibge_final,
                    dados_capag=capag_final,
                    dados_idh=idh_final,
                    dados_sebrae=st.session_state.get("dados_sebrae"),
                    dados_planalto=st.session_state.get("dados_planalto"),
                    contexto_objeto=contexto_obj_final,
                )
                st.session_state.portaria_md = parecer
                st.success("Portaria gerada com sucesso!")

            if st.session_state.portaria_md:
                st.subheader("Preview da Portaria")
                st.markdown(st.session_state.portaria_md)

                st.divider()

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.download_button(
                        label="Download Word (.docx)",
                        data=md_para_docx_bytes(st.session_state.portaria_md),
                        file_name=EXPORT_PORTARIA_DOCX_NAME,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                with c2:
                    st.download_button(
                        label="Download .md",
                        data=st.session_state.portaria_md,
                        file_name=EXPORT_PORTARIA_MD_NAME,
                        mime="text/markdown",
                    )
                with c3:
                    proponente = st.session_state.dados_extraidos.get("proponente", "proposta")
                    filename = f"portaria_{proponente[:30].replace(' ', '_')}.docx"
                    st.download_button(
                        label="Download Word (nome personalizado)",
                        data=md_para_docx_bytes(st.session_state.portaria_md),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )



    with tab_envio:
        render_aba_enviar_ao_repositorio(
            llm_config, TIPOS_ACEITOS, TIPOS_LABEL, category="portaria"
        )
