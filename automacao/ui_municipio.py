"""Seleção de município (API IBGE) com entrada manual se a lista não carregar."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from fontes_publicas import ibge_listar_municipios


def selecionar_municipio_ibge(
    uf_obj: dict,
    *,
    label: str = "Município:",
    key_prefix: str = "mun",
) -> Optional[dict]:
    """
    Retorna {"id": int, "nome": str} ou None.
    Se a API de municípios falhar, exibe nome + código IBGE (7 dígitos).
    """
    municipios = ibge_listar_municipios(uf_obj["id"])
    mun_map = {m["nome"]: m for m in municipios}
    if mun_map:
        mun_sel = st.selectbox(
            label,
            options=sorted(mun_map.keys()),
            key=f"{key_prefix}_sb",
        )
        return mun_map.get(mun_sel) if mun_sel else None

    st.warning(
        "Não foi possível carregar a lista de municípios (API IBGE indisponível ou rede bloqueada). "
        "Informe o nome e o **código IBGE** do município (7 dígitos, ex.: [cidades.ibge.gov.br](https://cidades.ibge.gov.br))."
    )
    mn = st.text_input("Nome do município:", key=f"{key_prefix}_nome_manual")
    cod_s = st.text_input(
        "Código IBGE (7 dígitos):",
        key=f"{key_prefix}_cod_manual",
        placeholder="ex.: 3550308",
        help="Código do município na base do IBGE.",
    )
    cod_s = (cod_s or "").strip()
    mn = (mn or "").strip()
    if mn and cod_s.isdigit() and len(cod_s) == 7:
        return {"id": int(cod_s), "nome": mn}
    return None
