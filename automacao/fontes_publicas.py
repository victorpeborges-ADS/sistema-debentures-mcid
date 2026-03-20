"""
Clientes para as 8 fontes publicas consultadas:
  1. IBGE (API Localidades + Pesquisas + SIDRA)
  2. Tesouro Nacional / CAPAG (XLSX)
  3. Ministerio das Cidades / Legislacao (scrape HTML)
  4. Atlas Brasil / IDH (scrape)
  5. SEBRAE / Observatorio Setorial Territorial (API Tesseract)
  6. Planalto — Decreto nº 12.210/2024 (regulamenta Pro-Cidades)
  7. Planalto — Lei nº 13.089/2015 (Estatuto da Metropole)
  8. Planalto — Lei nº 10.257/2001 (Estatuto da Cidade)
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

TIMEOUT = 15

# ---------------------------------------------------------------------------
# 1. IBGE
# ---------------------------------------------------------------------------

IBGE_BASE = "https://servicodados.ibge.gov.br/api"
SIDRA_BASE = "https://apisidra.ibge.gov.br"

SINOPSE_IDS = {
    29166: "populacao_censo",
    29168: "densidade_demografica",
    29167: "area_territorial_km2",
    29171: "populacao_estimada",
    29169: "codigo_ibge",
    29170: "prefeito",
    60409: "gentilico",
    77861: "bioma",
    82270: "amazonia_legal",
    91245: "regiao_intermediaria",
    91247: "regiao_imediata",
    91249: "mesorregiao",
    91251: "microrregiao",
}

PIB_IDS = {
    46996: "pib_precos_correntes_mil",
    47000: "pib_per_capita",
    46997: "pib_precos_correntes_mil_serie_atual",
    47001: "pib_per_capita_serie_atual",
    47003: "vab_total_mil",
    47005: "vab_agropecuaria_mil",
    47006: "vab_industria_mil",
    47007: "vab_servicos_mil",
    47008: "vab_adm_publica_mil",
}

FROTA_NOMES = [
    "frota_total", "automoveis", "bonde", "caminhao", "caminhao_trator",
    "caminhonete", "camioneta", "chassi_plataforma", "ciclomotor",
    "micro_onibus", "motocicleta", "motoneta", "onibus", "quadriciclo",
    "reboque", "semi_reboque", "side_car", "outros", "trator_esteira",
    "trator_rodas", "triciclo", "utilitario",
]


def _get_json(url: str) -> Optional[dict | list]:
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("Falha ao acessar %s: %s", url, e)
        return None


def _latest_value(serie: dict) -> tuple[Optional[str], Optional[str]]:
    for ano, val in sorted(serie.items(), reverse=True):
        if val and val != "-":
            return ano, val
    return None, None


def ibge_listar_estados() -> list[dict]:
    data = _get_json(f"{IBGE_BASE}/v1/localidades/estados")
    if not data:
        return []
    return sorted(data, key=lambda x: x["nome"])


def ibge_listar_municipios(uf_id: int) -> list[dict]:
    data = _get_json(f"{IBGE_BASE}/v1/localidades/estados/{uf_id}/municipios")
    if not data:
        return []
    return sorted(data, key=lambda x: x["nome"])


def _ibge_pesquisa(pesquisa_id: int, cod_municipio: int) -> list[dict]:
    url = f"{IBGE_BASE}/v1/pesquisas/{pesquisa_id}/indicadores/0/resultados/{cod_municipio}"
    data = _get_json(url)
    return data if isinstance(data, list) else []


def ibge_sinopse(cod_municipio: int) -> dict:
    resultado = {}
    for ind in _ibge_pesquisa(33, cod_municipio):
        ind_id = ind.get("id", 0)
        chave = SINOPSE_IDS.get(ind_id)
        if not chave:
            continue
        res = ind.get("res", [])
        if res:
            serie = res[0].get("res", {})
            ano, val = _latest_value(serie)
            if val:
                resultado[chave] = {"valor": val, "ano": ano}
    return resultado


def ibge_pib(cod_municipio: int) -> dict:
    resultado = {}
    for ind in _ibge_pesquisa(38, cod_municipio):
        ind_id = ind.get("id", 0)
        chave = PIB_IDS.get(ind_id)
        if not chave:
            continue
        res = ind.get("res", [])
        if res:
            serie = res[0].get("res", {})
            ano, val = _latest_value(serie)
            if val:
                resultado[chave] = {"valor": val, "ano": ano}
    return resultado


def ibge_frota(cod_municipio: int) -> dict:
    resultado = {}
    for i, ind in enumerate(_ibge_pesquisa(22, cod_municipio)):
        chave = FROTA_NOMES[i] if i < len(FROTA_NOMES) else f"tipo_{i}"
        res = ind.get("res", [])
        if res:
            serie = res[0].get("res", {})
            ano, val = _latest_value(serie)
            if val:
                resultado[chave] = {"valor": val, "ano": ano}
    return resultado


def ibge_populacao_sidra(cod_municipio: int) -> dict:
    url = f"{SIDRA_BASE}/values/t/4709/n6/{cod_municipio}/v/93/p/last"
    data = _get_json(url)
    if data and len(data) > 1:
        row = data[1]
        return {
            "populacao": row.get("V"),
            "ano": row.get("D3N"),
            "municipio": row.get("D1N"),
        }
    return {}


@dataclass
class DadosIBGE:
    """Consolida todos os dados IBGE de um municipio."""
    cod_municipio: int = 0
    nome: str = ""
    uf: str = ""
    sinopse: dict = field(default_factory=dict)
    pib: dict = field(default_factory=dict)
    frota: dict = field(default_factory=dict)
    populacao_sidra: dict = field(default_factory=dict)

    @property
    def populacao_estimada(self) -> Optional[str]:
        s = self.sinopse.get("populacao_estimada", {})
        return s.get("valor") if s else None

    @property
    def area_km2(self) -> Optional[str]:
        s = self.sinopse.get("area_territorial_km2", {})
        return s.get("valor") if s else None

    @property
    def pib_per_capita(self) -> Optional[str]:
        for chave in ("pib_per_capita", "pib_per_capita_serie_atual"):
            p = self.pib.get(chave, {})
            if p.get("valor"):
                return p["valor"]
        return None


def ibge_dados_completos(cod_municipio: int, nome: str = "", uf: str = "") -> DadosIBGE:
    return DadosIBGE(
        cod_municipio=cod_municipio,
        nome=nome,
        uf=uf,
        sinopse=ibge_sinopse(cod_municipio),
        pib=ibge_pib(cod_municipio),
        frota=ibge_frota(cod_municipio),
        populacao_sidra=ibge_populacao_sidra(cod_municipio),
    )


# ---------------------------------------------------------------------------
# 2. CAPAG (Tesouro Nacional)
# ---------------------------------------------------------------------------

CAPAG_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "9ff93162-409e-48b5-91d9-cf645a47fdfc/resource/"
    "046f7fcf-a742-4787-9768-dbb10747d55d/download/"
    "capag-municipios-posicao-2025-nov-09---processamento-2025-nov-10.xlsx"
)
CAPAG_CACHE = CACHE_DIR / "capag_municipios.xlsx"
CAPAG_TTL_DAYS = 30

CAPAG_COL_MAP = {
    "Código Município Completo": "cod_municipio",
    "Nome_Município": "nome",
    "UF": "uf",
    "CAPAG": "capag",
    "Indicador 1": "indicador_endividamento",
    "Nota 1": "nota_endividamento",
    "Indicador 2": "indicador_poupanca",
    "Nota 2": "nota_poupanca",
    "Indicador 3": "indicador_liquidez",
    "Nota 3": "nota_liquidez",
    "ICF": "icf",
    "Origem da Nota Final": "origem",
}


def _capag_download() -> bool:
    if CAPAG_CACHE.exists():
        age_days = (time.time() - CAPAG_CACHE.stat().st_mtime) / 86400
        if age_days < CAPAG_TTL_DAYS:
            logger.info("CAPAG XLSX em cache (%.1f dias)", age_days)
            return True
    logger.info("Baixando CAPAG XLSX (~22 MB)...")
    try:
        r = requests.get(CAPAG_URL, timeout=120, stream=True)
        r.raise_for_status()
        with open(CAPAG_CACHE, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        logger.info("CAPAG XLSX salvo em %s", CAPAG_CACHE)
        return True
    except Exception as e:
        logger.error("Falha ao baixar CAPAG: %s", e)
        return False


_capag_df_cache: Optional[pd.DataFrame] = None


def capag_carregar() -> Optional[pd.DataFrame]:
    global _capag_df_cache
    if _capag_df_cache is not None:
        return _capag_df_cache

    if not _capag_download():
        return None

    try:
        import openpyxl
        wb = openpyxl.load_workbook(CAPAG_CACHE, read_only=True, data_only=True)
        ws = wb["Prévia da CAPAG"]

        header_row = list(ws.iter_rows(min_row=3, max_row=3, values_only=True))[0]
        data_rows = []
        for row in ws.iter_rows(min_row=4, values_only=True):
            data_rows.append(row)
        wb.close()

        df = pd.DataFrame(data_rows, columns=header_row)
        _capag_df_cache = df
        return df
    except Exception as e:
        logger.error("Erro ao processar CAPAG: %s", e)
        return None


@dataclass
class DadosCAPAG:
    cod_municipio: int = 0
    nome: str = ""
    uf: str = ""
    capag: str = ""
    indicador_endividamento: Optional[float] = None
    nota_endividamento: str = ""
    indicador_poupanca: Optional[float] = None
    nota_poupanca: str = ""
    indicador_liquidez: Optional[float] = None
    nota_liquidez: str = ""
    icf: str = ""
    origem: str = ""
    encontrado: bool = False


def capag_buscar_municipio(cod_municipio: int) -> DadosCAPAG:
    df = capag_carregar()
    if df is None:
        return DadosCAPAG(cod_municipio=cod_municipio)

    cod_col = "Código Município Completo"
    mask = df[cod_col].astype(str).str.strip() == str(cod_municipio)
    rows = df[mask]

    if rows.empty:
        return DadosCAPAG(cod_municipio=cod_municipio)

    row = rows.iloc[0]

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    return DadosCAPAG(
        cod_municipio=cod_municipio,
        nome=str(row.get("Nome_Município", "")),
        uf=str(row.get("UF", "")),
        capag=str(row.get("CAPAG", "")),
        indicador_endividamento=safe_float(row.get("Indicador 1")),
        nota_endividamento=str(row.get("Nota 1", "")),
        indicador_poupanca=safe_float(row.get("Indicador 2")),
        nota_poupanca=str(row.get("Nota 2", "")),
        indicador_liquidez=safe_float(row.get("Indicador 3")),
        nota_liquidez=str(row.get("Nota 3", "")),
        icf=str(row.get("ICF", "")),
        origem=str(row.get("Origem da Nota Final", "")),
        encontrado=True,
    )


# ---------------------------------------------------------------------------
# 3. Legislacao MCID
# ---------------------------------------------------------------------------

LEGIS_URL = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/"
    "acoes-e-programas/desenvolvimento-urbano-e-metropolitano/"
    "programa-de-desenvolvimento-urbano-pro-cidades/legislacao"
)


@dataclass
class DadosLegislacao:
    normativos: list = field(default_factory=list)
    url: str = LEGIS_URL
    acessivel: bool = False
    in_18_2025_vigente: bool = False
    res_897_2018_vigente: bool = False


def legislacao_verificar() -> DadosLegislacao:
    result = DadosLegislacao()
    try:
        r = requests.get(LEGIS_URL, timeout=TIMEOUT)
        r.raise_for_status()
        result.acessivel = True

        html = r.text
        normas = re.findall(
            r"(INSTRU[ÇC][AÃ]O\s+NORMATIVA[^<]{5,80}|RESOLU[ÇC][AÃ]O[^<]{5,80})",
            html,
            re.IGNORECASE,
        )
        result.normativos = [n.strip() for n in normas]

        for n in result.normativos:
            if "18" in n and "2025" in n:
                result.in_18_2025_vigente = True
            if "897" in n and "2018" in n:
                result.res_897_2018_vigente = True

    except Exception as e:
        logger.warning("Falha ao acessar legislacao MCID: %s", e)

    return result


# ---------------------------------------------------------------------------
# 4. Atlas Brasil / IDH
# ---------------------------------------------------------------------------

ATLAS_RANKING_URL = "http://www.atlasbrasil.org.br/ranking"


@dataclass
class DadosIDH:
    idhm: Optional[float] = None
    idhm_educacao: Optional[float] = None
    idhm_longevidade: Optional[float] = None
    idhm_renda: Optional[float] = None
    ano: str = "2010"
    encontrado: bool = False


def atlas_buscar_idh(cod_municipio: int) -> DadosIDH:
    """Busca IDH no Atlas Brasil via scrape do perfil municipal.

    O Atlas Brasil usa codigo de 6 digitos (sem digito verificador).
    O endpoint AJAX e /perfil/municipio/idhm/{cod_6d} e retorna HTML com
    objetos JSON embutidos contendo siglas IDHM, IDHM_E, IDHM_L, IDHM_R.
    """
    cod_6d = str(cod_municipio)[:6]

    try:
        s = requests.Session()
        r = s.get(
            f"http://www.atlasbrasil.org.br/perfil/municipio/{cod_municipio}",
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return DadosIDH()

        csrf = re.search(r'csrf-token.*?content="([^"]+)"', r.text)
        if not csrf:
            return DadosIDH()

        headers = {
            "X-CSRF-TOKEN": csrf.group(1),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"http://www.atlasbrasil.org.br/perfil/municipio/{cod_municipio}",
        }

        r2 = s.get(
            f"http://www.atlasbrasil.org.br/perfil/municipio/idhm/{cod_6d}",
            headers=headers,
            timeout=TIMEOUT,
        )
        if r2.status_code != 200 or len(r2.text) < 100:
            return DadosIDH()

        pattern = r'"valor"\s*:\s*"([^"]+)"[^{}]*?"ano"\s*:\s*(\d+)[^{}]*?"sigla"\s*:\s*"(IDHM[^"]*)"'
        matches = re.findall(pattern, r2.text)

        dados_2010 = {}
        for val, ano, sigla in matches:
            if ano == "2010":
                dados_2010[sigla] = _safe_float(val)

        if "IDHM" in dados_2010:
            return DadosIDH(
                idhm=dados_2010.get("IDHM"),
                idhm_educacao=dados_2010.get("IDHM_E"),
                idhm_longevidade=dados_2010.get("IDHM_L"),
                idhm_renda=dados_2010.get("IDHM_R"),
                ano="2010",
                encontrado=True,
            )

    except Exception as e:
        logger.warning("Atlas Brasil indisponivel: %s", e)

    return DadosIDH()


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 5. Indicadores de Emprego e Negócios — IBGE SIDRA (CEMPRE) + Indicadores Municipais
#
#    Fontes confirmadas e testadas por município (código IBGE 7 dígitos):
#
#    PRIMÁRIA — IBGE SIDRA Tabela 6449 (CEMPRE — Cadastro Central de Empresas):
#      Variável 2585: Número de empresas e outras organizações
#      Variável 707:  Pessoal ocupado total
#      Variável 708:  Pessoal ocupado assalariado (emprego formal)
#      Variável 662:  Salários e outras remunerações (R$ mil / ano)
#      → Salário médio mensal calculado = (662 * 1000 / 708) / 12
#
#    SECUNDÁRIA — IBGE Indicadores Municipais (API v1/pesquisas):
#      Indicador 60037: Pessoal ocupado nas empresas (% da pop.)
#      Indicador 60033: Salário médio mensal dos trabalhadores formais (sal. mínimos)
#      Indicador 47001: Receitas orçamentárias realizadas (R$ 1.000)
#
#    O Observatório SEBRAE (observatorio.sebrae.com.br) é SPA React e
#    não permite scraping — disponível apenas como link de consulta manual.
# ---------------------------------------------------------------------------

SEBRAE_BASE       = "https://datasebrae.com.br"
_IBGE_CIDADES_BASE = "https://cidades.ibge.gov.br/brasil"
_SIDRA_BASE        = "https://apisidra.ibge.gov.br/values"
_IBGE_PESQUISAS_BASE = "https://servicodados.ibge.gov.br/api/v1/pesquisas/-/indicadores"

# Variáveis da tabela 6449 (CEMPRE) que nos interessam
_CEMPRE_VARS = {
    "2585": "empresas",           # Número de empresas e outras organizações
    "707":  "pessoal_total",      # Pessoal ocupado total
    "708":  "pessoal_assalariado",# Pessoal ocupado assalariado (emprego formal)
    "662":  "salarios_mil",       # Salários e outras remunerações (R$ mil / ano)
}


@dataclass
class DadosSEBRAE:
    """
    Indicadores socioeconômicos municipais de emprego e negócios.
    Fonte primária: IBGE SIDRA Tabela 6449 (CEMPRE).
    Fonte secundária: IBGE Indicadores Municipais.
    Referência manual: SEBRAE Observatório Setorial Territorial.
    """
    cod_municipio: int = 0
    encontrado: bool = False
    # --- CEMPRE (SIDRA 6449) ---
    empresas_ativas: Optional[int] = None          # total de organizações ativas
    mei_ativos: Optional[int] = None               # MEI (não disponível via SIDRA)
    empregos_formais: Optional[int] = None         # pessoal ocupado assalariado
    pessoal_total: Optional[int] = None            # pessoal ocupado total (formal + informal)
    salarios_anuais_mil: Optional[float] = None    # R$ mil/ano (total massa salarial)
    salario_medio: Optional[float] = None          # R$ médio/mês (calculado)
    # --- Indicadores IBGE (complementares) ---
    pessoal_ocupado_pct: Optional[float] = None    # % da pop. total (ind. 60037)
    salario_medio_sm: Optional[float] = None       # em salários mínimos (ind. 60033)
    receitas_realizadas_mil: Optional[float] = None# R$ mil (ind. 47001)
    pib_total: Optional[float] = None
    pib_per_capita_sebrae: Optional[float] = None
    nota_enem: Optional[float] = None
    ano_ref: str = ""
    url_perfil: str = ""
    fonte: str = "IBGE SIDRA — CEMPRE (Cadastro Central de Empresas)"
    erro: str = ""


# Salário mínimo vigente por ano (para converter SM → R$ quando CEMPRE não disponível)
_SALARIO_MINIMO = {
    "2024": 1412, "2023": 1320, "2022": 1212, "2021": 1100,
    "2020": 1045, "2019": 998,  "2018": 954,  "2017": 937,
    "2016": 880,  "2015": 788,  "2014": 724,  "2013": 678,
    "2012": 622,
}


def _sidra_cempre_municipio(cod_municipio: int) -> dict:
    """
    Busca dados do CEMPRE (IBGE SIDRA Tabela 6449) para um município.
    Retorna dict com chaves 'empresas', 'pessoal_total', 'pessoal_assalariado',
    'salarios_mil', 'ano'; ou dict vazio em caso de falha.

    Tabela 6449 = CEMPRE — Empresas e outras organizações (nível municipal).
    Confirmado funcional para todos os municípios brasileiros.
    """
    # variáveis solicitadas (apenas as 4 de interesse, separadas por vírgula)
    variaveis = ",".join(_CEMPRE_VARS.keys())
    url = (
        f"{_SIDRA_BASE}/t/6449/n6/{cod_municipio}"
        f"/v/{variaveis}/p/last%201/c12762/117897/f/a"
    )
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"Accept": "application/json"})
        r.raise_for_status()
        rows = r.json()
        if not rows or len(rows) < 2:
            return {}
        dados: dict = {}
        ano_ref = ""
        for row in rows[1:]:   # pula o cabeçalho
            cod_var = str(row.get("D2C", ""))
            nome_campo = _CEMPRE_VARS.get(cod_var)
            if not nome_campo:
                continue
            val = _safe_float(row.get("V"))
            if val is None:
                continue
            dados[nome_campo] = val
            if not ano_ref:
                ano_ref = str(row.get("D3N", ""))
        if dados:
            dados["ano"] = ano_ref
        return dados
    except Exception as e:
        logger.debug("SIDRA CEMPRE cod %s: %s", cod_municipio, e)
        return {}


def _ibge_indicador_municipio(ind_id: str, cod_municipio: int) -> tuple:
    """
    Busca um indicador IBGE para um município específico.
    Retorna (valor_float_ou_str, ano_str) ou (None, "").
    """
    url = f"{_IBGE_PESQUISAS_BASE}/{ind_id}/resultados/{cod_municipio}"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if not data or not isinstance(data, list):
            return None, ""
        res_list = data[0].get("res", [])
        if not res_list:
            return None, ""
        res_dict = res_list[0].get("res", {})
        if not res_dict:
            return None, ""
        ano = max(res_dict.keys(), key=lambda k: k.split("-")[0])
        val = res_dict[ano]
        return _safe_float(val), ano
    except Exception as e:
        logger.debug("IBGE ind %s cod %s: %s", ind_id, cod_municipio, e)
        return None, ""


def sebrae_buscar_municipio(cod_municipio: int, nome: str = "") -> DadosSEBRAE:
    """
    Busca indicadores de emprego e negócios para o município.

    Estratégia (em ordem de prioridade):
      1. IBGE SIDRA Tabela 6449 (CEMPRE) — empresas, emprego formal, salários reais
      2. IBGE Indicadores Municipais — percentual ocupado, salário em SM, receitas
      3. Link direto ao SEBRAE Observatório para consulta manual adicional
    """
    resultado = DadosSEBRAE(
        cod_municipio=cod_municipio,
        url_perfil=f"{_IBGE_CIDADES_BASE}/{cod_municipio}/panorama",
    )

    dados_coletados = 0

    # -----------------------------------------------------------------------
    # 1. SIDRA Tabela 6449 — CEMPRE (fonte principal)
    # -----------------------------------------------------------------------
    cempre = _sidra_cempre_municipio(cod_municipio)
    if cempre:
        if "empresas" in cempre:
            resultado.empresas_ativas = int(cempre["empresas"])
            dados_coletados += 1
        if "pessoal_assalariado" in cempre:
            resultado.empregos_formais = int(cempre["pessoal_assalariado"])
            dados_coletados += 1
        if "pessoal_total" in cempre:
            resultado.pessoal_total = int(cempre["pessoal_total"])
        if "salarios_mil" in cempre:
            resultado.salarios_anuais_mil = cempre["salarios_mil"]
            # Salário médio mensal = (total anual em R$) / pessoal assalariado / 12
            if resultado.empregos_formais and resultado.empregos_formais > 0:
                resultado.salario_medio = round(
                    (cempre["salarios_mil"] * 1_000) / resultado.empregos_formais / 12, 2
                )
            dados_coletados += 1
        if cempre.get("ano"):
            resultado.ano_ref = cempre["ano"]
        resultado.fonte = "IBGE SIDRA — CEMPRE (Cadastro Central de Empresas)"
        logger.info("CEMPRE %s: %d empresas, %d empregos formais",
                    nome, resultado.empresas_ativas or 0, resultado.empregos_formais or 0)

    # -----------------------------------------------------------------------
    # 2. IBGE Indicadores Municipais (complemento/fallback)
    # -----------------------------------------------------------------------
    # Pessoal ocupado % (útil para calcular taxa de ocupação)
    val_ocp, ano_ocp = _ibge_indicador_municipio("60037", cod_municipio)
    if val_ocp is not None:
        resultado.pessoal_ocupado_pct = val_ocp
        if not resultado.ano_ref:
            resultado.ano_ref = ano_ocp.split("-")[0]
        dados_coletados += 1

    # Salário médio em SM (fallback caso CEMPRE não retorne salário)
    if resultado.salario_medio is None:
        val_sm, ano_sm = _ibge_indicador_municipio("60033", cod_municipio)
        if val_sm is not None:
            resultado.salario_medio_sm = val_sm
            ano_sm_str = ano_sm.split("-")[0]
            sm_ref = _SALARIO_MINIMO.get(ano_sm_str) or _SALARIO_MINIMO.get("2022", 1212)
            resultado.salario_medio = round(val_sm * sm_ref, 2)
            dados_coletados += 1

    # Receitas orçamentárias realizadas
    val_rec, _ = _ibge_indicador_municipio("47001", cod_municipio)
    if val_rec is not None:
        resultado.receitas_realizadas_mil = val_rec
        dados_coletados += 1

    # -----------------------------------------------------------------------
    # 3. Resultado final
    # -----------------------------------------------------------------------
    if dados_coletados > 0:
        resultado.encontrado = True
    else:
        resultado.erro = (
            "Dados de emprego/negócios não disponíveis via IBGE para este município. "
            f"Consulte: IBGE Cidades ({resultado.url_perfil}) ou DataSEBRAE ({SEBRAE_BASE})"
        )

    return resultado


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", ".")))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 6-8. Legislação federal — Planalto.gov.br
#      Textos são cacheados localmente após primeira consulta (não mudam).
# ---------------------------------------------------------------------------

# Normas relevantes para o programa Pró-Cidades
NORMAS_PLANALTO = {
    "decreto_12210_2024": {
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/decreto/d12210.htm",
        "label": "Decreto nº 12.210/2024",
        "descricao": "Regulamenta o Programa de Desenvolvimento Urbano (Pró-Cidades)",
        "sigla": "D12210/2024",
    },
    "lei_13089_2015": {
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13089.htm",
        "label": "Lei nº 13.089/2015",
        "descricao": "Institui o Estatuto da Metrópole",
        "sigla": "L13089/2015",
    },
    "lei_10257_2001": {
        "url": "https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10257.htm",
        "label": "Lei nº 10.257/2001",
        "descricao": "Estatuto da Cidade — regulamenta os arts. 182 e 183 da Constituição Federal",
        "sigla": "L10257/2001",
    },
}

# Limite de caracteres do texto legal a injetar nos prompts (por norma)
_PLANALTO_MAX_CHARS = 12_000


@dataclass
class DadosNormaPlanalto:
    """Texto e metadados de uma norma federal do Planalto."""
    chave: str = ""
    label: str = ""
    descricao: str = ""
    sigla: str = ""
    url: str = ""
    texto: str = ""          # texto limpo extraído do HTML
    acessivel: bool = False
    cache_usado: bool = False
    erro: str = ""


@dataclass
class DadosPlanalto:
    """Consolida todas as normas Planalto consultadas."""
    normas: dict = field(default_factory=dict)   # chave → DadosNormaPlanalto

    @property
    def todas_acessiveis(self) -> bool:
        return all(n.acessivel for n in self.normas.values())

    @property
    def resumo_citacao(self) -> str:
        """Retorna string de citação para o rodapé do parecer."""
        return "; ".join(
            f"{n.label} ({n.descricao})"
            for n in self.normas.values()
            if n.acessivel
        )

    def texto_consolidado(self, max_chars_por_norma: int = _PLANALTO_MAX_CHARS) -> str:
        """
        Retorna bloco de texto com o conteúdo de todas as normas,
        pronto para injeção no prompt da IA como contexto normativo.
        """
        blocos = []
        for n in self.normas.values():
            if n.texto:
                trecho = n.texto[:max_chars_por_norma]
                if len(n.texto) > max_chars_por_norma:
                    trecho += "\n[...texto truncado por limite de contexto...]"
                blocos.append(
                    f"### {n.label} — {n.descricao}\nURL: {n.url}\n\n{trecho}"
                )
        if not blocos:
            return ""
        return (
            "\n\n---\n## LEGISLAÇÃO FEDERAL DE REFERÊNCIA (Planalto.gov.br)\n\n"
            + "\n\n---\n\n".join(blocos)
            + "\n\n---\n"
        )


def _planalto_cache_path(chave: str) -> Path:
    return CACHE_DIR / f"planalto_{chave}.txt"


def _limpar_html_planalto(html: str) -> str:
    """Extrai texto limpo de páginas do Planalto, removendo scripts, CSS e navegação."""
    # Remove scripts e estilos
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>",  " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove comentários HTML
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    # Converte parágrafos e quebras em newlines
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>",  "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>",      "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<li[^>]*>", "\n• ", html, flags=re.IGNORECASE)
    # Remove todas as tags restantes
    html = re.sub(r"<[^>]+>", " ", html)
    # Decodifica entidades comuns
    html = html.replace("&nbsp;", " ").replace("&amp;", "&")
    html = html.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Normaliza espaços e linhas em branco excessivas
    linhas = [l.strip() for l in html.splitlines()]
    linhas = [l for l in linhas if l]
    texto = "\n".join(linhas)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def planalto_buscar_norma(chave: str, forcar_atualizacao: bool = False) -> DadosNormaPlanalto:
    """
    Busca e cacheia o texto de uma norma do Planalto.
    - Primeiro tenta o cache local (arquivo .txt em data/)
    - Se não existir ou forcar_atualizacao=True, faz o download
    """
    meta = NORMAS_PLANALTO.get(chave)
    if not meta:
        return DadosNormaPlanalto(chave=chave, erro=f"Chave desconhecida: {chave}")

    resultado = DadosNormaPlanalto(
        chave=chave,
        label=meta["label"],
        descricao=meta["descricao"],
        sigla=meta["sigla"],
        url=meta["url"],
    )

    cache_path = _planalto_cache_path(chave)

    # Tenta cache local
    if cache_path.exists() and not forcar_atualizacao:
        try:
            resultado.texto = cache_path.read_text(encoding="utf-8")
            resultado.acessivel = True
            resultado.cache_usado = True
            logger.info("Planalto cache hit: %s", chave)
            return resultado
        except Exception as e:
            logger.warning("Erro ao ler cache %s: %s", chave, e)

    # Download da norma
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        r = requests.get(meta["url"], headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"

        texto = _limpar_html_planalto(r.text)
        if len(texto) < 200:
            resultado.erro = "Texto extraído muito curto — possível bloqueio ou página vazia."
            return resultado

        resultado.texto = texto
        resultado.acessivel = True

        # Salva no cache para próximas execuções
        try:
            cache_path.write_text(texto, encoding="utf-8")
            logger.info("Planalto cache salvo: %s (%d chars)", chave, len(texto))
        except Exception as e:
            logger.warning("Não foi possível salvar cache %s: %s", chave, e)

    except requests.exceptions.Timeout:
        resultado.erro = f"Timeout ao acessar {meta['url']}"
        logger.warning("Planalto timeout: %s", chave)
    except Exception as e:
        resultado.erro = str(e)
        logger.warning("Planalto erro %s: %s", chave, e)

    return resultado


def planalto_buscar_todas(forcar_atualizacao: bool = False) -> DadosPlanalto:
    """
    Busca as 3 normas do Planalto em paralelo (sequencial com timeout individual).
    Retorna DadosPlanalto com todas as normas consultadas.
    """
    resultado = DadosPlanalto()
    for chave in NORMAS_PLANALTO:
        norma = planalto_buscar_norma(chave, forcar_atualizacao=forcar_atualizacao)
        resultado.normas[chave] = norma
        status = "✅ cache" if norma.cache_usado else ("✅ web" if norma.acessivel else f"❌ {norma.erro[:40]}")
        logger.info("Planalto %s: %s", norma.label, status)
    return resultado
