"""
Motor de processamento do Parecer de Merito:
  - Extracao de texto do PDF (pypdf)
  - Pipeline de 4 chamadas Ollama
  - Regras normativas pre-avaliadas
  - Gerador de Markdown final no formato oficial MCID
"""

import io
import json
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import requests
from pypdf import PdfReader

from llm_client import LLMConfig, gerar_texto, gerar_json as _llm_gerar_json, gerar_visao, suporta_visao
from biblioteca import get_exemplos_fewshot, get_exemplos_secao, get_guia_estilo
from fontes_publicas import DadosPlanalto

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = 600  # legado — timeout padrão usado no LLMConfig

# ---------------------------------------------------------------------------
# Secao 2 — COMPETENCIA (boilerplate identico em todos os pareceres)
# ---------------------------------------------------------------------------

TEXTO_COMPETENCIA = """**2.1.** Com base na **Lei nº 14.600, de 19 de junho de 2023**, e no **Decreto nº 12.553, de 14 de julho de 2025**, que aprovou a Estrutura Regimental do MCID, as atribuições de promover inovações tecnológicas, ambientais, sociais e de gestão nas políticas nacionais urbanas e de fomentar o desenvolvimento e a difusão de inovações urbanas integram as competências do Departamento de Adaptação das Cidades à Transição Climática e Transformação Digital (DAC) da SNDUM, como consta dos incisos I e VII do art. 19 do Decreto, *in verbis*:

> *"Art. 19. Ao Departamento de Adaptação das Cidades à Transição Climática e Transformação Digital compete:*
> *I – promover inovações tecnológicas, ambientais, sociais e de gestão nas políticas nacionais urbanas e elaborar estratégia para difundi-las para os Estados, o Distrito Federal e os Municípios;*
> *(…)*
> *VII – firmar parcerias com institutos de pesquisa, universidades, organizações não governamentais e privadas para fomentar o desenvolvimento e a difusão de inovações urbanas nas áreas de competência do Ministério; e"*. (Grifos nossos)

**2.2.** Em circunstâncias semelhantes à presente análise técnica, cabe ao Ministério das Cidades, por meio do DAC, avaliar a priorização por este Ministério Setorial de projetos de modernização da rede de iluminação pública municipal. Tal atribuição tem por amparo o disposto na **Portaria MCID nº 359, de 9 de abril de 2025**, que regulamenta os critérios e as condições complementares para o enquadramento e acompanhamento dos projetos de investimentos considerados como prioritários na área de infraestrutura para o setor de iluminação pública, cabendo ao Ministério aprovar previamente o enquadramento de projetos de investimento em infraestrutura do setor de iluminação pública, como se segue:

> *"Art. 3° Os projetos de investimento em infraestrutura do setor de iluminação pública deverão ser objeto de aprovação prévia do Ministério das Cidades, nos termos do § 2° do art. 3° do Decreto n° 11.964, de 26 de março de 2024.*
> *Art. 4° Os projetos de investimento serão considerados prioritários após a publicação de portaria de aprovação pelo Ministro de Estado das Cidades, nos termos do art. 6º do Decreto nº 11.964, de 26 de março de 2024"*. (Grifos nossos)

**2.3.** Ademais, nos termos do **Decreto nº 12.210 de 3 de outubro de 2024**, compete ao Ministério das Cidades qualificar a política federal de fomento a parcerias em empreendimentos públicos dos Estados, do Distrito Federal e dos Municípios em transformação digital para cidades inteligentes no âmbito do Programa de Parcerias de Investimentos da Presidência da República (PPI). Esta competência reforça a prevista na Lei nº 14.600, de 2023, detalhada nos incisos I e VII do art. 19 do Decreto nº 12.553, de 2025.

**2.4.** As operações do Programa de Desenvolvimento Urbano – Pró-Cidades, nos termos do Anexo da Resolução do Conselho Curador do Fundo de Garantia de Tempo de Serviço – CCFGTS nº 897, de 11 de setembro de 2018, estão subordinadas às normas do Gestor da Aplicação, ou seja, à regulamentação deste Ministério, inclusive a **Instrução Normativa (IN) nº 18, de 25 de abril de 2025, do Ministério das Cidades (MCID)**.

**2.5.** Destarte, por caber à Coordenação-Geral de Modernização Urbana (CGMUR) tanto realizar a análise técnica dos projetos de iluminação pública quanto a de projetos de modernização tecnológica urbana no âmbito do DAC, nas próximas seções serão apresentadas as análises realizadas por esta Unidade."""

# ---------------------------------------------------------------------------
# Few-shot: formato oficial (estilo dos pareceres reais do MCID)
# ---------------------------------------------------------------------------

# Os exemplos hard-coded de Nova Lima foram removidos.
# Os exemplos de referência agora são carregados dinamicamente da biblioteca
# de pareceres validados em automacao/biblioteca/pareceres_validados/
# via get_exemplos_secao(numero_secao) — injeção cirúrgica por seção.

# ---------------------------------------------------------------------------
# Extracao PDF
# ---------------------------------------------------------------------------

def extrair_texto_pdf(arquivo) -> Optional[str]:
    try:
        reader = PdfReader(arquivo)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.error("Falha ao extrair PDF: %s", e)
        return None


# ---------------------------------------------------------------------------
# Extratores multi-formato
# ---------------------------------------------------------------------------

def _extrair_html(arquivo) -> Optional[str]:
    try:
        from html.parser import HTMLParser

        class _Stripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts = []
                self._skip_tags = {"script", "style", "head"}
                self._in_skip = 0

            def handle_starttag(self, tag, attrs):
                if tag in self._skip_tags:
                    self._in_skip += 1

            def handle_endtag(self, tag):
                if tag in self._skip_tags and self._in_skip:
                    self._in_skip -= 1

            def handle_data(self, data):
                if not self._in_skip:
                    self._parts.append(data)

        raw = arquivo.read() if hasattr(arquivo, "read") else arquivo
        if isinstance(raw, str):
            html = raw
        else:
            html = raw.decode("utf-8", errors="replace")
        parser = _Stripper()
        parser.feed(html)
        text = " ".join(parser._parts)
        # Colapsa espaços múltiplos e linhas em branco
        text = re.sub(r"\s{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        logger.error("Falha ao extrair HTML: %s", e)
        return None


def _extrair_docx(arquivo) -> Optional[str]:
    try:
        from docx import Document
        raw = arquivo.read() if hasattr(arquivo, "read") else arquivo
        doc = Document(io.BytesIO(raw) if isinstance(raw, bytes) else arquivo)
        partes = []
        for para in doc.paragraphs:
            if para.text.strip():
                partes.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                linha = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if linha:
                    partes.append(linha)
        return "\n".join(partes)
    except Exception as e:
        logger.error("Falha ao extrair DOCX: %s", e)
        return None


def _extrair_planilha(arquivo, nome: str) -> Optional[str]:
    """Extrai conteúdo de XLSX, XLS ou CSV como texto tabular."""
    try:
        import pandas as pd
        # Normaliza para BytesIO para garantir compatibilidade com qualquer file-like
        raw = arquivo.read() if hasattr(arquivo, "read") else arquivo
        buf = io.BytesIO(raw) if isinstance(raw, bytes) else io.StringIO(raw)
        ext = nome.lower().rsplit(".", 1)[-1]
        if ext == "csv":
            df = pd.read_csv(buf, dtype=str, na_filter=False)
        else:
            df = pd.read_excel(buf, dtype=str, na_filter=False)
        linhas = []
        linhas.append(" | ".join(str(c) for c in df.columns))
        linhas.append("-" * 80)
        for _, row in df.iterrows():
            linhas.append(" | ".join(str(v) for v in row))
        return "\n".join(linhas)
    except Exception as e:
        logger.error("Falha ao extrair planilha %s: %s", nome, e)
        return None


def _extrair_kml_bytes(kml_bytes: bytes, nome_origem: str) -> str:
    """Parseia KML e retorna texto estruturado com nomes, descrições e resumo de coordenadas."""
    NS = {
        "kml": "http://www.opengis.net/kml/2.2",
        "kml21": "http://earth.google.com/kml/2.1",
    }
    try:
        root = ET.fromstring(kml_bytes)
        # Detecta namespace automaticamente
        tag = root.tag
        ns = ""
        if "{" in tag:
            ns = tag.split("}")[0] + "}"

        placemarks = root.iter(f"{ns}Placemark")
        linhas = [f"[KML/KMZ: {nome_origem}]"]
        total = 0
        coords_all = []
        for pm in placemarks:
            total += 1
            nome_el = pm.find(f"{ns}name")
            desc_el = pm.find(f"{ns}description")
            nome_pm = nome_el.text.strip() if nome_el is not None and nome_el.text else f"Ponto {total}"
            desc_pm = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            if total <= 20:  # Limita saída para o LLM
                linha = f"  - {nome_pm}"
                if desc_pm:
                    linha += f": {desc_pm[:120]}"
                linhas.append(linha)

            # Coleta coordenadas para bounding box
            for coords_el in pm.iter(f"{ns}coordinates"):
                if coords_el.text:
                    for pt in coords_el.text.strip().split():
                        parts = pt.split(",")
                        if len(parts) >= 2:
                            try:
                                coords_all.append((float(parts[0]), float(parts[1])))
                            except ValueError:
                                pass

        if total > 20:
            linhas.append(f"  ... (e mais {total - 20} pontos)")
        linhas.append(f"Total de placemarks/pontos: {total}")

        if coords_all:
            lons = [c[0] for c in coords_all]
            lats = [c[1] for c in coords_all]
            linhas.append(
                f"Bounding box: lon [{min(lons):.5f} a {max(lons):.5f}], "
                f"lat [{min(lats):.5f} a {max(lats):.5f}]"
            )

        return "\n".join(linhas)
    except Exception as e:
        logger.error("Falha ao parsear KML %s: %s", nome_origem, e)
        return f"[KML inválido ou não parseável: {nome_origem}]"


def _extrair_kml(arquivo, nome: str) -> Optional[str]:
    try:
        raw = arquivo.read() if hasattr(arquivo, "read") else arquivo
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        return _extrair_kml_bytes(raw, nome)
    except Exception as e:
        logger.error("Falha ao extrair KML: %s", e)
        return None


def _extrair_kmz(arquivo, nome: str) -> Optional[str]:
    try:
        data = arquivo.read() if hasattr(arquivo, "read") else arquivo
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # KMZ é um zip: encontra o primeiro .kml dentro
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                return f"[KMZ sem arquivo .kml interno: {nome}]"
            kml_bytes = zf.read(kml_names[0])
            return _extrair_kml_bytes(kml_bytes, nome)
    except Exception as e:
        logger.error("Falha ao extrair KMZ: %s", e)
        return None


# Mapeamento de extensões para extratores
_EXTENSOES_SUPORTADAS = {
    "pdf":  "PDF",
    "html": "HTML",
    "htm":  "HTML",
    "docx": "Word",
    "doc":  "Word",
    "xlsx": "Planilha",
    "xls":  "Planilha",
    "csv":  "Planilha",
    "kml":  "KML (Georeferenciamento)",
    "kmz":  "KMZ (Georeferenciamento)",
    # Imagens — extração via OCR e/ou visão por IA
    "jpg":  "Imagem",
    "jpeg": "Imagem",
    "png":  "Imagem",
    "gif":  "Imagem",
    "bmp":  "Imagem",
    "tiff": "Imagem",
    "tif":  "Imagem",
    "webp": "Imagem",
}

_EXTENSOES_IMAGEM = {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp"}

_MEDIA_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png",  "gif": "image/gif",
    "bmp": "image/bmp",  "tiff": "image/tiff", "tif": "image/tiff",
    "webp": "image/webp",
}


def detectar_formato(nome_arquivo: str) -> str:
    ext = nome_arquivo.lower().rsplit(".", 1)[-1] if "." in nome_arquivo else ""
    return _EXTENSOES_SUPORTADAS.get(ext, "Desconhecido")


def _extrair_imagem_ocr(arquivo) -> str:
    """
    Extrai texto de uma imagem usando OCR (pytesseract).
    Requer: pip install pytesseract Pillow
    E o binário Tesseract instalado no sistema.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.debug("pytesseract/Pillow não instalado — OCR indisponível.")
        return ""

    try:
        buf = io.BytesIO(arquivo if isinstance(arquivo, bytes) else arquivo.read())
        img = Image.open(buf)
        # Tenta português primeiro, depois inglês como fallback
        try:
            texto = pytesseract.image_to_string(img, lang="por+eng", config="--psm 3")
        except pytesseract.TesseractError:
            texto = pytesseract.image_to_string(img, config="--psm 3")
        return texto.strip()
    except Exception as e:
        logger.warning("OCR falhou: %s", e)
        return ""


def _extrair_imagem_visao(imagem_bytes: bytes, nome: str,
                           llm_config: Optional["LLMConfig"] = None) -> str:
    """
    Envia a imagem para análise pelo modelo de visão do provedor configurado.
    Retorna descrição/texto extraído pelo modelo.
    """
    if not llm_config or not suporta_visao(llm_config):
        return ""

    ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else "jpeg"
    media_type = _MEDIA_TYPES.get(ext, "image/jpeg")

    try:
        import base64 as _b64
        b64 = _b64.b64encode(imagem_bytes).decode()
        resultado = gerar_visao(b64, media_type, llm_config)
        return resultado or ""
    except Exception as e:
        logger.warning("Visão por IA falhou para %s: %s", nome, e)
        return ""


def extrair_texto_imagem(arquivo, nome: str,
                          llm_config: Optional["LLMConfig"] = None) -> str:
    """
    Estratégia de extração de imagens em 3 camadas:
      1. OCR (pytesseract) — ideal para documentos escaneados com texto
      2. Visão por IA (cloud) — ideal para fotos, mapas, plantas técnicas
      3. Fallback informativo — registra a imagem sem texto extraído

    Se o OCR extrair >= 80 caracteres, usa o resultado do OCR.
    Caso contrário, tenta visão por IA (se o provedor suportar).
    Se ambos falharem e o OCR extraiu algo, usa o OCR parcial.
    """
    OCR_MIN_CHARS = 80

    # Normaliza para bytes (pode chegar como Streamlit UploadedFile ou bytes)
    if hasattr(arquivo, "read"):
        imagem_bytes = arquivo.read()
    elif isinstance(arquivo, (bytes, bytearray)):
        imagem_bytes = bytes(arquivo)
    else:
        imagem_bytes = b""

    # Camada 1: OCR
    texto_ocr = _extrair_imagem_ocr(io.BytesIO(imagem_bytes))

    if len(texto_ocr) >= OCR_MIN_CHARS:
        logger.info("Imagem %s: OCR bem-sucedido (%d chars)", nome, len(texto_ocr))
        return f"[Texto extraído por OCR — {nome}]\n{texto_ocr}"

    # Camada 2: Visão por IA
    if llm_config and suporta_visao(llm_config):
        texto_visao = _extrair_imagem_visao(imagem_bytes, nome, llm_config)
        if texto_visao:
            logger.info("Imagem %s: visão por IA bem-sucedida (%d chars)", nome, len(texto_visao))
            return f"[Descrição por IA — {nome}]\n{texto_visao}"

    # Camada 3: OCR parcial ou fallback
    if texto_ocr:
        logger.info("Imagem %s: OCR parcial (%d chars)", nome, len(texto_ocr))
        return f"[Texto parcial por OCR — {nome}]\n{texto_ocr}"

    _motivo = (
        "OCR indisponível (instale: pip install pytesseract Pillow + Tesseract) e "
        "provedor de IA sem suporte a visão."
        if not llm_config or not suporta_visao(llm_config)
        else "Nem OCR nem visão retornaram texto."
    )
    logger.warning("Imagem %s sem extração: %s", nome, _motivo)
    return f"[Imagem anexada sem extração de texto — {nome}. {_motivo}]"


def extrair_texto_arquivo(arquivo, nome: str,
                           llm_config: Optional["LLMConfig"] = None) -> Optional[str]:
    """Extrai texto de um único arquivo com base na extensão."""
    ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""
    if ext == "pdf":
        return extrair_texto_pdf(arquivo)
    elif ext in ("html", "htm"):
        return _extrair_html(arquivo)
    elif ext in ("docx", "doc"):
        return _extrair_docx(arquivo)
    elif ext in ("xlsx", "xls", "csv"):
        return _extrair_planilha(arquivo, nome)
    elif ext == "kml":
        return _extrair_kml(arquivo, nome)
    elif ext == "kmz":
        return _extrair_kmz(arquivo, nome)
    elif ext in _EXTENSOES_IMAGEM:
        return extrair_texto_imagem(arquivo, nome, llm_config)
    else:
        logger.warning("Formato não suportado: %s", nome)
        return None


def extrair_textos_multiplos(arquivos: list,
                              llm_config: Optional["LLMConfig"] = None) -> tuple:
    """
    Extrai e consolida texto de múltiplos arquivos.
    Passa llm_config para extração de imagens (OCR + visão por IA).

    Returns:
        texto_consolidado (str): texto de todos os arquivos com separadores
        metadados (dict): lista de arquivos processados e flags especiais
    """
    partes = []
    metadados = {
        "arquivos": [],
        "tem_kml_kmz": False,
        "tem_imagens": False,
        "total_chars": 0,
    }

    for arq in arquivos:
        nome = getattr(arq, "name", str(arq))
        fmt = detectar_formato(nome)
        texto = extrair_texto_arquivo(arq, nome, llm_config)

        info = {"nome": nome, "formato": fmt, "chars": 0, "ok": False}

        if texto:
            info["chars"] = len(texto)
            info["ok"] = True
            separador = f"\n{'='*60}\n[ARQUIVO: {nome} | Formato: {fmt}]\n{'='*60}\n"
            partes.append(separador + texto)
            metadados["total_chars"] += len(texto)

            ext = nome.lower().rsplit(".", 1)[-1]
            if ext in ("kml", "kmz"):
                metadados["tem_kml_kmz"] = True
            if ext in _EXTENSOES_IMAGEM:
                metadados["tem_imagens"] = True
                # Identifica método de extração usado
                if texto.startswith("[Descrição por IA"):
                    info["metodo_imagem"] = "visao_ia"
                elif texto.startswith("[Texto extraído por OCR"):
                    info["metodo_imagem"] = "ocr"
                elif texto.startswith("[Texto parcial por OCR"):
                    info["metodo_imagem"] = "ocr_parcial"
                else:
                    info["metodo_imagem"] = "sem_extracao"
        else:
            info["erro"] = "Não foi possível extrair texto"

        metadados["arquivos"].append(info)

    texto_consolidado = "\n".join(partes)
    return texto_consolidado, metadados


# ---------------------------------------------------------------------------
# Contexto adicional do operador (texto livre + URL)
# ---------------------------------------------------------------------------

def buscar_url_contexto(url: str, timeout: int = 15) -> tuple:
    """
    Faz fetch de uma URL e retorna (texto_limpo, sucesso, mensagem).
    Usa o mesmo HTML stripper interno — não depende de beautifulsoup4.
    """
    if not url or not url.strip():
        return "", False, "URL vazia."
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; DebenturesMCIDBot/1.0; "
                    "+https://www.gov.br/cidades)"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type or "text" in content_type:
            texto = _extrair_html_str(resp.text)
        else:
            return "", False, f"Tipo de conteúdo não suportado: {content_type}"

        # Limita tamanho para não sobrecarregar o contexto do LLM
        if len(texto) > 8000:
            texto = texto[:8000] + "\n[... conteúdo truncado em 8.000 caracteres ...]"

        return texto, True, f"OK — {len(texto)} caracteres extraídos de {url}"
    except requests.exceptions.ConnectionError:
        return "", False, "Falha de conexão. Verifique a URL e a rede."
    except requests.exceptions.Timeout:
        return "", False, f"Timeout após {timeout}s. O site demorou para responder."
    except requests.exceptions.HTTPError as e:
        return "", False, f"Erro HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return "", False, f"Erro inesperado: {e}"


def _extrair_html_str(html: str) -> str:
    """Extrai texto limpo de uma string HTML (sem dependência externa)."""
    from html.parser import HTMLParser

    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts = []
            self._skip = {"script", "style", "head", "nav", "footer", "aside"}
            self._depth = 0

        def handle_starttag(self, tag, attrs):
            if tag in self._skip:
                self._depth += 1

        def handle_endtag(self, tag):
            if tag in self._skip and self._depth:
                self._depth -= 1

        def handle_data(self, data):
            if not self._depth and data.strip():
                self._parts.append(data.strip())

    p = _Stripper()
    p.feed(html)
    texto = " ".join(p._parts)
    texto = re.sub(r"\s{3,}", "\n\n", texto)
    return texto.strip()


def preparar_contexto_adicional(
    texto_manual: str = "",
    urls: list = None,
    conteudos_urls: dict = None,
) -> str:
    """
    Formata o bloco de contexto adicional do operador para ser injetado
    no texto consolidado antes do pipeline Ollama.

    Args:
        texto_manual: observações livres do operador
        urls: lista de URLs fornecidas
        conteudos_urls: dict {url: texto_extraído}

    Returns:
        bloco de texto formatado, ou "" se nenhum contexto foi fornecido
    """
    partes = []

    if texto_manual and texto_manual.strip():
        partes.append(
            "=== OBSERVAÇÕES DO ANALISTA ===\n"
            + texto_manual.strip()
        )

    urls = urls or []
    conteudos_urls = conteudos_urls or {}
    for url in urls:
        conteudo = conteudos_urls.get(url, "")
        if conteudo and conteudo.strip():
            partes.append(
                f"=== FONTE ADICIONAL: {url} ===\n"
                + conteudo.strip()
            )

    if not partes:
        return ""

    bloco = (
        "\n" + "=" * 60 + "\n"
        "[CONTEXTO ADICIONAL FORNECIDO PELO OPERADOR]\n"
        + "=" * 60 + "\n"
        + "\n\n".join(partes)
        + "\n" + "=" * 60 + "\n"
    )
    return bloco


# ---------------------------------------------------------------------------
# Adaptadores: assinaturas legadas (host, model) → LLMConfig
# ---------------------------------------------------------------------------

def _config_from_args(host_or_config, model: str = "") -> LLMConfig:
    """Aceita tanto LLMConfig quanto (host_str, model_str) para retrocompatibilidade."""
    if isinstance(host_or_config, LLMConfig):
        return host_or_config
    # Legado: host string + model string → Ollama
    return LLMConfig(
        provider="ollama",
        ollama_host=host_or_config or "http://localhost:11434",
        ollama_model=model or "qwen2.5:7b",
        timeout=OLLAMA_TIMEOUT,
    )


def _gerar(prompt: str, system: str, cfg: LLMConfig,
           as_json: bool = False) -> Optional[str]:
    try:
        if as_json:
            return _llm_gerar_json(prompt, system, cfg)
        return gerar_texto(prompt, system, cfg)
    except Exception as e:
        logger.error("LLM falhou (%s): %s", cfg.provider, e)
        return None


# ---------------------------------------------------------------------------
# Chamada 1: Extracao estruturada
# ---------------------------------------------------------------------------

SYSTEM_EXTRACAO = """Você é um extrator de dados de documentos técnicos do governo brasileiro.
Extraia os campos solicitados do texto fornecido e retorne APENAS um JSON válido.
Se um campo não for encontrado, use string vazia.
Não invente dados. Extraia apenas o que está explícito no texto."""

PROMPT_EXTRACAO = """Extraia os seguintes campos do texto abaixo e retorne como JSON:

Campos:
- proponente: nome completo do proponente/concessionária
- cnpj: CNPJ no formato XX.XXX.XXX/XXXX-XX
- natureza: natureza jurídica (ex: "Pessoa jurídica de direito privado" ou "Órgão Público do Poder Executivo Municipal")
- modalidade: "Modernização tecnológica urbana" ou "Reabilitação de Áreas Urbanas"
- objeto: descrição do objeto da proposta (completa, 1-3 frases)
- valor_financiamento: valor em R$ do financiamento (ex: "R$ 25.000.000,00")
- valor_contrapartida: valor em R$ da contrapartida
- valor_total: valor total do investimento
- municipio: nome do município beneficiado
- uf: sigla da UF (ex: "PR")
- processo_sei: número do processo SEI (ex: "80000.XXXXXX/YYYY-ZZ")
- numero_proposta: número da proposta técnica (ex: "180")
- agente_financeiro: nome do agente financeiro (ex: "BRDE" ou "CAIXA")
- populacao_beneficiada: população estimada beneficiada (apenas número)
- contrato_concessao: número do contrato de concessão/PPP mencionado
- responsavel_tecnico: nome do profissional responsável técnico e seu CREA
- componentes_tecnicos: lista dos principais componentes técnicos do projeto com quantitativos
  (ex: "substituição de 40.806 pontos LED, telegestão em 13.787 pontos, CCO, iluminação especial em 18 monumentos")
  Inclua: quantidades de pontos/unidades, equipamentos específicos (CCO, telegestão, sensores), áreas especiais
- reducao_consumo_pct: percentual de redução no consumo de energia (ex: "46,64")
- reducao_co2_ton: redução estimada de emissões de CO2 em toneladas (apenas número, ex: "969")
- economia_energia_kwh: economia anual de energia em kWh ou MWh (ex: "2.500.000 kWh/ano")
- prazo_execucao: prazo de execução do projeto (ex: "36 meses")

TEXTO:
{texto}

Retorne APENAS o JSON, sem explicações."""


def chamada1_extracao(texto_pdf: str, host_or_config, model: str = "") -> dict:
    cfg = _config_from_args(host_or_config, model)
    prompt = PROMPT_EXTRACAO.format(texto=texto_pdf[:8000])
    resposta = _gerar(prompt, SYSTEM_EXTRACAO, cfg, as_json=True)
    if not resposta:
        return {}
    try:
        return json.loads(resposta)
    except json.JSONDecodeError:
        logger.warning("Resposta da chamada 1 nao e JSON valido")
        return {}


# ---------------------------------------------------------------------------
# Chamada 2: Sumario Executivo (secao 1)
# ---------------------------------------------------------------------------

_SYSTEM_SUMARIO_BASE = """Você é um analista técnico sênior da Coordenação-Geral de Modernização Urbana do Ministério das Cidades (CGMUR/DAC/SNDUM-MCID).
Redija o Sumário Executivo (Seção 1) de um Parecer de Mérito do Programa Pró-Cidades.
Use linguagem técnica e jurídico-administrativa formal. Escreva em português.

REGRAS OBRIGATÓRIAS:
- Escreva EXATAMENTE 3 parágrafos numerados: **1.1.**, **1.2.**, **1.3.**
- Parágrafo **1.1.**: "O presente Parecer de Mérito apresenta a análise de enquadramento, para investimentos com recursos do Programa de Desenvolvimento Urbano (Pró-Cidades), destinados à [modalidade] do Município de [município/UF], nos termos pleiteados pelo [proponente] (CNPJ [cnpj])..."
  → Se houver contrato de concessão ou PPP, mencione-o na frase final do 1.1.
- Parágrafo **1.2.**: "Em síntese, [proponente] busca financiamento junto ao Pró-Cidades para [objeto detalhado]."
  → OBRIGATÓRIO em 1.2.: (a) componentes técnicos específicos COM quantitativos numéricos (ex: "40.806 pontos LED, telegestão em 13.787 pontos, CCO, 18 monumentos"); (b) valor total do investimento; (c) percentual dos recursos FGTS e percentual da contrapartida (ex: "sendo R$ X (71,4%) em recursos do FGTS e R$ Y (28,6%) de contrapartida")
- Parágrafo **1.3.**: "Nesse sentido, solicita o enquadramento do Projeto no Programa Pró-Cidades, [modalidade], com base no subitem 8.6.6.3.4 da IN MCID nº 18, de 25 de abril de 2025."
- Use negrito (**texto**) para destacar: nome do proponente, modalidade, componentes técnicos principais, valor total, percentuais, subitem normativo
- PROIBIDO: histórico do município, topografia, dados sociodemográficos genéricos, texto em primeira pessoa
{guia_estilo}"""

PROMPT_SUMARIO = """Redija o Sumário Executivo (parágrafos 1.1, 1.2 e 1.3) para o seguinte projeto:

DADOS EXTRAÍDOS DA PROPOSTA:
{dados_json}

DADOS COMPLEMENTARES DO MUNICÍPIO (IBGE):
- Município: {municipio} – {uf}
- População estimada (2025): {populacao}
- CAPAG (Tesouro Nacional): {capag}

PERCENTUAIS CALCULADOS (use obrigatoriamente em 1.2):
- Financiamento FGTS: {pct_financiamento:.1f}% do investimento total
- Contrapartida: {pct_contrapartida:.1f}% do investimento total

{exemplos_secao}

Redija os 3 parágrafos numerados (**1.1.**, **1.2.**, **1.3.**) para ESTE projeto específico.
ATENÇÃO: Os exemplos acima são de OUTROS municípios. Use apenas o estilo, NÃO o conteúdo factual."""


def chamada2_sumario(dados: dict, dados_municipio: dict, host_or_config, model: str = "") -> str:
    cfg = _config_from_args(host_or_config, model)
    exemplos_sec1 = get_exemplos_secao(numero_secao=1, max_exemplos=2, max_chars=2000)
    guia = get_guia_estilo()
    system = _SYSTEM_SUMARIO_BASE.format(guia_estilo=guia)

    # Calcula percentuais de financiamento e contrapartida para injeção no prompt
    try:
        vf = _parse_valor(dados.get("valor_financiamento", ""))
        vc = _parse_valor(dados.get("valor_contrapartida", ""))
        vt = vf + vc
        pct_financiamento = (vf / vt * 100) if vt > 0 else 0.0
        pct_contrapartida = (vc / vt * 100) if vt > 0 else 0.0
    except Exception:
        pct_financiamento = 0.0
        pct_contrapartida = 0.0

    prompt = PROMPT_SUMARIO.format(
        dados_json=json.dumps(dados, ensure_ascii=False, indent=2),
        municipio=dados.get("municipio") or dados_municipio.get("municipio", ""),
        uf=dados.get("uf") or dados_municipio.get("uf", ""),
        populacao=dados_municipio.get("populacao", "N/D"),
        capag=dados_municipio.get("capag", "N/D"),
        pct_financiamento=pct_financiamento,
        pct_contrapartida=pct_contrapartida,
        exemplos_secao=exemplos_sec1,
    )
    return _gerar(prompt, system, cfg) or ""


# ---------------------------------------------------------------------------
# Chamada 3: Analise de Enquadramento (secao 6)
# ---------------------------------------------------------------------------

_SYSTEM_ANALISE_BASE = """Você é um analista técnico sênior da Coordenação-Geral de Modernização Urbana do Ministério das Cidades (CGMUR/DAC/SNDUM-MCID).
Redija a Análise de Enquadramento do Projeto Pró-Cidades (Seção 6 do parecer).
Use linguagem jurídico-administrativa formal, com parágrafos numerados. Escreva em português.

ESTRUTURA OBRIGATÓRIA (7 parágrafos numerados de 6.1 a 6.7):
- **6.1.** Objetivos gerais do Pró-Cidades com menção ao Estatuto da Cidade (Lei nº 10.257/2001) e Estatuto da Metrópole (Lei nº 13.089/2015)
- **6.2.** Definição da Modalidade 2 — Modernização tecnológica urbana: duas iniciativas: (i) soluções IoT/cidades inteligentes; (ii) apoio à gestão urbana. Mencione o Decreto nº 12.210/2024.
- **6.3.** Enquadramento no subitem 8.6.6.3.4 da IN MCID nº 18/2025. Use EXCLUSIVAMENTE a fórmula: "São exemplos de intervenção passíveis de financiamento aqueles previstos no **subitem 8.6.6.3.4 da IN MCID nº 18, de 25 de abril de 2025**: *"iluminação pública inteligente, com o uso de tecnologias mais eficientes para fins de iluminação pública para todas as pessoas, sistema de telegestão para monitoramento em tempo real; ..."*."
  ⚠️ PROIBIDO: inventar ou reescrever o texto do subitem — use exatamente essa citação.
- **6.4.** Análise de por que ESTE projeto se enquadra nesse subitem (relacione o objeto concreto da proposta com o subitem 8.6.6.3.4)
- **6.5.** Análise do mutuário (natureza jurídica, SPE, PPP, item 8.1 da Res. CCFGTS nº 897/2018)
- **6.6.** Análise da contrapartida: percentual calculado, comparação com mínimo de 5% (subitem 3.2 da Res. CCFGTS 897/2018 e art. 22 da Res. CCFGTS 702/2012)
- **6.7.** Conclusão parcial + alinhamento com Carta Brasileira de Cidades Inteligentes

REGRAS:
- Use negrito (**texto**) para realçar normas e modalidade
- Cite apenas os dispositivos exatos: IN MCID nº 18/2025, Res. CCFGTS 897/2018, Res. CCFGTS 702/2012, Lei 8.036/1990, Lei 10.257/2001, Lei 13.089/2015, Decreto 12.210/2024
- ⚠️ NUNCA invente artigos, subitens ou transcrições além das explicitamente indicadas acima
{guia_estilo}"""

PROMPT_ANALISE = """Redija a Análise de Enquadramento (parágrafos 6.1 a 6.7) com base nos dados abaixo.

DADOS DA PROPOSTA:
{dados_json}

CONFORMIDADE PRÉ-AVALIADA (use estes resultados para os parágrafos 6.5 e 6.6):
{conformidade}

DADOS CAPAG DO MUNICÍPIO:
- Nota CAPAG: {capag} | Endividamento: Nota {nota_end} | Poupança Corrente: Nota {nota_poup} | Liquidez: Nota {nota_liq}

{exemplos_secao}

Redija os 7 parágrafos numerados (**6.1.** a **6.7.**) para ESTE projeto específico.
ATENÇÃO: Os exemplos acima são de OUTROS municípios. Use apenas o estilo e a estrutura, NÃO os valores, normas ou dados factuais deles."""


def chamada3_analise(dados: dict, conformidade: str, capag_info: dict,
                     host_or_config, model: str = "",
                     dados_planalto: "DadosPlanalto | None" = None) -> str:
    cfg = _config_from_args(host_or_config, model)
    exemplos_sec6 = get_exemplos_secao(numero_secao=6, max_exemplos=2, max_chars=2500)
    guia = get_guia_estilo()
    system = _SYSTEM_ANALISE_BASE.format(guia_estilo=guia)

    # Contexto normativo do Planalto (limitado a 4000 chars)
    ctx_planalto = ""
    if dados_planalto:
        ctx_planalto = dados_planalto.texto_consolidado(max_chars_por_norma=2000)

    prompt = PROMPT_ANALISE.format(
        dados_json=json.dumps(dados, ensure_ascii=False, indent=2),
        conformidade=conformidade,
        capag=capag_info.get("capag", "N/D"),
        nota_end=capag_info.get("nota_endividamento", "N/D"),
        nota_poup=capag_info.get("nota_poupanca", "N/D"),
        nota_liq=capag_info.get("nota_liquidez", "N/D"),
        exemplos_secao=exemplos_sec6,
    )
    if ctx_planalto:
        prompt = ctx_planalto + "\n\n" + prompt
    return _gerar(prompt, system, cfg) or ""


# ---------------------------------------------------------------------------
# Chamada 4: Checklist (secao 7)
# ---------------------------------------------------------------------------

SYSTEM_CHECKLIST = """Você é um analista documental do Ministério das Cidades.
Analise o texto do PDF e determine o status de cada item do checklist do Anexo II da IN MCID nº 18/2025.
Retorne APENAS JSON válido, sem explicações."""

CHECKLIST_ITEMS = [
    {"id": 1, "doc": "Definição do perímetro da área de intervenção (.kml/.kmz ou imagem satélite/foto aérea)"},
    {"id": 2, "doc": "Declaração de disponibilidade orçamentária/financeira para a contrapartida"},
    {"id": 3, "doc": "Declaração de capacidade técnica e gerencial (profissional responsável indicado)"},
    {"id": 4, "doc": "Declaração de atendimento à legislação urbanística (Plano Diretor)"},
    {"id": 5, "doc": "Declaração de acessibilidade"},
    {"id": 6, "doc": "Comprovação de titularidade da área"},
    {"id": 7, "doc": "Anuência do Município / Contrato de concessão ou PPP (setor privado)"},
    {"id": 8, "doc": "Outros (especificar se solicitados)"},
]

PROMPT_CHECKLIST = """Analise o texto do PDF abaixo e determine, para cada item do Anexo II da IN MCID nº 18/2025, se o documento correspondente está presente ou mencionado.

ITENS DO CHECKLIST:
{itens}

REGRAS para determinação do status:
- "Cumprida" = documento está presente, mencionado como entregue, ou há declaração assinada no texto
- "Atendido parcialmente" = documento mencionado mas incompleto (ex: foto em vez de .kml para o perímetro)
- "Não disponível" = documento não encontrado no texto e seria aplicável
- "Não cabível" = item não se aplica ao tipo de proposta (ex: Plano Diretor para setor privado/SPE; titularidade para vias públicas)

DICAS DE INTERPRETAÇÃO:
- Item 1 (perímetro): "Cumprida" apenas se .kml/.kmz ou imagem satélite delimitada; foto genérica = "Atendido parcialmente"; seção XI vazia = "Não disponível"
- Item 4 (Plano Diretor): para SPE/concessionária privada = "Não cabível"
- Item 5 (acessibilidade): para projetos de iluminação = "Não cabível"
- Item 6 (titularidade): para vias públicas concedidas = "Não cabível"
- Item 7 (anuência/PPP): "Cumprida" se há contrato de concessão ou PPP mencionado

TEXTO DO PDF:
{texto}

Retorne JSON no formato: {{"1": "Cumprida", "2": "Não disponível", "3": "Cumprida", "4": "Não cabível", "5": "Não cabível", "6": "Não cabível", "7": "Cumprida", "8": "-"}}"""


def chamada4_checklist(texto_pdf: str, host_or_config, model: str = "",
                        tem_kml_kmz: bool = False) -> dict:
    cfg = _config_from_args(host_or_config, model)
    itens_str = "\n".join(f"  {i['id']}. {i['doc']}" for i in CHECKLIST_ITEMS)
    prompt = PROMPT_CHECKLIST.format(
        itens=itens_str,
        texto=texto_pdf[:6000],
    )
    resposta = _gerar(prompt, SYSTEM_CHECKLIST, cfg, as_json=True)
    resultado = {}
    if resposta:
        try:
            resultado = json.loads(resposta)
        except json.JSONDecodeError:
            resultado = {}

    if tem_kml_kmz:
        resultado["1"] = "Cumprida"

    return resultado


# ---------------------------------------------------------------------------
# Chamada 5 — Contexto do objeto no município (parágrafo específico seção 4)
# ---------------------------------------------------------------------------

_SYSTEM_CONTEXTO_OBJETO_BASE = (
    "Você é um Analista de Infraestrutura Urbana do Ministério das Cidades. "
    "Sua tarefa é redigir UM ÚNICO PARÁGRAFO técnico, objetivo e formal, "
    "que descreva a situação atual do município especificamente em relação ao OBJETO do projeto. "
    "Use exclusivamente dados quantitativos e fatos extraídos do texto da proposta fornecida. "
    "NUNCA use frases genéricas. NUNCA invente dados. "
    "Se os documentos contiverem números específicos (quantidade de pontos, percentuais, "
    "capacidade instalada, extensão de rede, etc.), CITE-OS com precisão. "
    "O parágrafo deve ter entre 3 e 6 sentenças, no estilo formal de pareceres do MCID."
    "{guia_estilo}"
)

PROMPT_CONTEXTO_OBJETO = """\
Município: {municipio} / {uf}
Objeto do projeto: {objeto}

Texto consolidado da proposta (extraia daqui os dados específicos do município sobre o objeto):
{texto}

{exemplos_secao4}

---

Redija UM ÚNICO parágrafo técnico que descreva a situação atual de {municipio} \
especificamente em relação a "{objeto}".

Requisitos OBRIGATÓRIOS:
1. Use dados numéricos concretos do texto acima (quantidades, percentuais, extensões, capacidades)
2. Contextualize por que esses dados justificam ou dão urgência ao projeto proposto
3. Mencione características específicas do município que impactam o objeto (topografia, densidade, \
área especial, etc.) SE mencionadas nos documentos
4. Linguagem formal, terceira pessoa, tempo presente
5. NÃO repita informações já cobertas por população ou PIB — foque no objeto técnico
6. NÃO copie dados dos exemplos de referência — eles são de outros municípios

Parágrafo (apenas o texto, sem numeração):
"""


def chamada5_contexto_objeto(
    texto_pdf: str,
    objeto: str,
    municipio: str,
    uf: str,
    host_or_config,
    model: str = "",
) -> str:
    """
    Gera o parágrafo final da seção 4 conectando os dados específicos do município
    diretamente ao objeto da proposta (ex: iluminação pública, mobilidade, saneamento).

    Este parágrafo DEVE conter dados numéricos extraídos da proposta — não é genérico.
    """
    if not objeto or not texto_pdf:
        return ""

    cfg = _config_from_args(host_or_config, model)
    exemplos_sec4 = get_exemplos_secao(numero_secao=4, max_exemplos=2, max_chars=2000)
    guia = get_guia_estilo()
    system = _SYSTEM_CONTEXTO_OBJETO_BASE.format(
        guia_estilo=f"\n{guia}" if guia else ""
    )
    prompt = PROMPT_CONTEXTO_OBJETO.format(
        municipio=municipio,
        uf=uf,
        objeto=objeto,
        texto=texto_pdf[:7000],
        exemplos_secao4=exemplos_sec4,
    )
    resultado = _gerar(prompt, system, cfg)
    return (resultado or "").strip()


# ---------------------------------------------------------------------------
# Regras normativas (avaliacao deterministica)
# ---------------------------------------------------------------------------

def avaliar_conformidade(dados: dict) -> list[dict]:
    resultados = []

    modalidade = dados.get("modalidade", "")
    modalidades_elegiveis = [
        "modernização tecnológica urbana",
        "reabilitação de áreas urbanas",
    ]
    resultados.append({
        "regra": "Modalidade elegível (IN MCID nº 18/2025)",
        "conforme": any(m in modalidade.lower() for m in modalidades_elegiveis) if modalidade else None,
        "detalhe": f"Modalidade: {modalidade}" if modalidade else "Não informada",
    })

    try:
        vf = _parse_valor(dados.get("valor_financiamento", ""))
        vc = _parse_valor(dados.get("valor_contrapartida", ""))
        vt = vf + vc
        pct = (vc / vt * 100) if vt > 0 else 0
        resultados.append({
            "regra": "Contrapartida >= 5% (Res. CCFGTS nº 897/2018, subitem 3.2)",
            "conforme": pct >= 5.0,
            "detalhe": f"Contrapartida: {pct:.1f}%",
        })
    except Exception:
        resultados.append({
            "regra": "Contrapartida >= 5% (Res. CCFGTS nº 897/2018, subitem 3.2)",
            "conforme": None,
            "detalhe": "Valores financeiros insuficientes para cálculo",
        })

    natureza = dados.get("natureza", "")
    resultados.append({
        "regra": "Proponente elegível (Res. CCFGTS nº 897/2018, item 8.1)",
        "conforme": bool(natureza),
        "detalhe": f"Natureza: {natureza}" if natureza else "Não informada",
    })

    resultados.append({
        "regra": "Aplicação restrita à zona urbana (Lei nº 8.036/1990, art. 5°)",
        "conforme": None,
        "detalhe": "Verificar perímetro da área de intervenção no Checklist (item 1)",
    })

    return resultados


def avaliar_capag(nota_capag: str) -> dict:
    if not nota_capag:
        return {"conforme": None, "detalhe": "CAPAG não disponível"}
    nota = nota_capag.upper().strip()
    if nota in ("A", "B"):
        return {"conforme": True, "detalhe": f"CAPAG {nota} — sem restrições para garantia da União"}
    elif nota == "C":
        return {"conforme": False, "detalhe": f"CAPAG {nota} — restrições parciais para garantia da União"}
    elif nota == "D":
        return {"conforme": False, "detalhe": f"CAPAG {nota} — município com restrições severas"}
    return {"conforme": None, "detalhe": f"CAPAG {nota} — classificação não reconhecida"}


def conformidade_texto(resultados: list[dict], capag_result: dict) -> str:
    linhas = []
    for r in resultados:
        status = "CONFORME" if r["conforme"] else ("NÃO CONFORME" if r["conforme"] is False else "VERIFICAR")
        linhas.append(f"- {r['regra']}: {status} — {r['detalhe']}")
    status_capag = "CONFORME" if capag_result["conforme"] else (
        "NÃO CONFORME" if capag_result["conforme"] is False else "VERIFICAR")
    linhas.append(f"- CAPAG compatível (Tesouro Nacional): {status_capag} — {capag_result['detalhe']}")
    return "\n".join(linhas)


def _parse_valor(texto: str) -> float:
    if not texto:
        return 0.0
    limpo = texto.replace("R$", "").replace(" ", "").strip()
    partes = limpo.split("(")[0].strip()
    partes = partes.replace(".", "").replace(",", ".")
    return float(partes)


# ---------------------------------------------------------------------------
# Secao 4 — O MUNICÍPIO (gerada a partir dos dados publicos estruturados)
# ---------------------------------------------------------------------------

def _gerar_secao_municipio(
    nome: str,
    uf: str,
    dados_ibge=None,
    dados_capag=None,
    dados_idh=None,
    dados_sebrae=None,
    contexto_objeto: str = "",
) -> str:
    """
    Monta a seção 4 (O MUNICÍPIO) com dados reais do IBGE, CAPAG, Atlas Brasil e SEBRAE.

    Regra de conflito entre fontes: prevalece SEMPRE o dado com ano de referência
    mais recente. Cada valor exibido é acompanhado de citação (Fonte, Ano).

    `contexto_objeto`: parágrafo final gerado por LLM descrevendo especificamente
    a situação do município em relação ao objeto do projeto (iluminação, mobilidade, etc.).
    """
    paragrafos = []
    idx = 1

    def p(texto: str) -> str:
        nonlocal idx
        out = f"**4.{idx}.** {texto}"
        idx += 1
        return out

    ib = dados_ibge
    sin = (ib.sinopse or {}) if ib else {}
    seb = dados_sebrae if (dados_sebrae and dados_sebrae.encontrado) else None

    # ---- 4.1 — Localização e contexto geográfico ----
    if ib or not dados_ibge:
        mesoreg  = sin.get("mesorregiao", {}).get("valor", "")
        microreg = sin.get("microrregiao", {}).get("valor", "")
        reg_int  = sin.get("regiao_intermediaria", {}).get("valor", "")
        bioma    = sin.get("bioma", {}).get("valor", "")
        amazonia = sin.get("amazonia_legal", {}).get("valor", "Não pertence")

        localizacao = f"O Município de **{nome}**, localizado no Estado de {_nome_estado(uf)}"
        if reg_int:
            localizacao += f", integra a Região Intermediária de {reg_int}"
        if mesoreg:
            localizacao += f", na Mesorregião {mesoreg}"
        if microreg:
            localizacao += f" e na Microrregião de {microreg}"
        if bioma:
            localizacao += f". O município pertence ao bioma **{bioma}**"
        if amazonia and "pertence" in amazonia.lower() and "não" not in amazonia.lower():
            localizacao += " e está inserido na Amazônia Legal"
        localizacao += "."
        paragrafos.append(p(localizacao))

    # ---- 4.2 — Área, população e densidade ----
    # Para cada indicador, coleta candidatos de todas as fontes com seus anos,
    # usa _resolver_dado para escolher o mais recente e cita a origem.
    if ib:
        area_ibge  = sin.get("area_territorial_km2", {})
        area_val, area_ano, area_src = _resolver_dado([
            (ib.area_km2 or area_ibge.get("valor"), int(area_ibge.get("ano", 0) or 0), "IBGE"),
        ])

        pop_censo_entry = sin.get("populacao_censo", {})
        pop_est_entry   = sin.get("populacao_estimada", {})
        pop_seb = str(seb.empregos_formais) if seb and seb.empregos_formais else None  # não é pop, ignorar

        pop_val, pop_ano, pop_src = _resolver_dado([
            (pop_est_entry.get("valor"),   int(pop_est_entry.get("ano",   0) or 0), "IBGE — estimativa"),
            (pop_censo_entry.get("valor"), int(pop_censo_entry.get("ano", 0) or 0), "IBGE — Censo"),
        ])

        dens_entry = sin.get("densidade_demografica", {})
        dens_val, dens_ano, dens_src = _resolver_dado([
            (dens_entry.get("valor"), int(dens_entry.get("ano", 0) or 0), "IBGE"),
        ])

        prefeito  = sin.get("prefeito", {}).get("valor", "")
        gentilico = sin.get("gentilico", {}).get("valor", "")

        demo = []
        if area_val:
            demo.append(f"área territorial de **{_fmt_numero(area_val)} km²** {_citar(area_src, area_ano)}")
        if pop_val:
            demo.append(
                f"**{_fmt_numero(pop_val)} habitantes** {_citar(pop_src, pop_ano)}"
            )
        if dens_val:
            demo.append(f"densidade demográfica de **{_fmt_numero(dens_val)} hab/km²** {_citar(dens_src, dens_ano)}")

        txt_demo = f"O município ocupa uma {', '.join(demo)}." if demo else ""
        if prefeito:
            prefeito_fmt = " ".join(
                w.capitalize() if w.upper() not in ("DE", "DA", "DO", "DAS", "DOS", "E") else w.lower()
                for w in prefeito.split()
            )
            txt_demo += f" O atual Prefeito Municipal é **{prefeito_fmt}**."
        if gentilico:
            txt_demo += f" Os habitantes são denominados {gentilico}s."
        if txt_demo:
            paragrafos.append(p(txt_demo))

    # ---- 4.3 — IDH e indicadores sociais (Atlas Brasil 2010 — dado único, sem conflito) ----
    if dados_idh and dados_idh.idhm:
        idh  = dados_idh
        nivel = _nivel_idhm(idh.idhm)
        txt_idh = (
            f"A população de {nome} apresenta **Índice de Desenvolvimento Humano Municipal "
            f"(IDHM) de {idh.idhm:.3f}**, classificado como {nivel} "
            f"{_citar('Atlas Brasil / PNUD', idh.ano)}"
        )
        subindices = []
        if idh.idhm_longevidade:
            subindices.append(f"IDHM Longevidade {idh.idhm_longevidade:.3f}")
        if idh.idhm_renda:
            subindices.append(f"IDHM Renda {idh.idhm_renda:.3f}")
        if idh.idhm_educacao:
            subindices.append(f"IDHM Educação {idh.idhm_educacao:.3f}")
        if subindices:
            txt_idh += f", composto pelos subíndices: {', '.join(subindices)}"
        txt_idh += "."
        paragrafos.append(p(txt_idh))

    # ---- 4.4 — Economia: PIB resolve conflito IBGE × SEBRAE ----
    if ib:
        pib_total_ibge = None
        pib_pc_ibge    = ib.pib_per_capita
        pib_ano_ibge   = 0
        vab_serv = vab_ind = vab_adm = None

        if ib.pib:
            _pt = ib.pib.get("pib_precos_correntes_mil_serie_atual", {})
            pib_total_ibge = _pt.get("valor")
            pib_ano_ibge   = int(_pt.get("ano", 0) or 0)
            pib_pc_ibge    = pib_pc_ibge or ib.pib.get("pib_per_capita_serie_atual", {}).get("valor")
            vab_serv = ib.pib.get("vab_servicos_mil", {}).get("valor")
            vab_ind  = ib.pib.get("vab_industria_mil", {}).get("valor")
            vab_adm  = ib.pib.get("vab_adm_publica_mil", {}).get("valor")

        # PIB total: candidatos IBGE e SEBRAE
        pib_total_seb_val = str(seb.pib_total * 1000) if (seb and seb.pib_total) else None
        pib_ano_seb       = int(seb.ano_ref) if (seb and seb.ano_ref and seb.ano_ref.isdigit()) else 0

        pib_val, pib_ano, pib_src = _resolver_dado([
            (pib_total_ibge, pib_ano_ibge, "IBGE"),
            (pib_total_seb_val, pib_ano_seb, "SEBRAE/Observatório"),
        ])

        # PIB per capita: candidatos IBGE e SEBRAE
        pib_pc_seb_val = str(seb.pib_per_capita_sebrae) if (seb and seb.pib_per_capita_sebrae) else None
        pib_pc_val, pib_pc_ano, pib_pc_src = _resolver_dado([
            (pib_pc_ibge, pib_ano_ibge, "IBGE"),
            (pib_pc_seb_val, pib_ano_seb, "SEBRAE/Observatório"),
        ])

        if pib_val or pib_pc_val:
            partes_econ = []
            if pib_val:
                pib_bi = float(pib_val) / 1_000_000
                partes_econ.append(
                    f"**PIB municipal de R$ {_fmt_bi(pib_bi)} bilhões** {_citar(pib_src, pib_ano)}"
                )
            if pib_pc_val:
                partes_econ.append(
                    f"**PIB per capita de R$ {_fmt_numero(pib_pc_val, decimais=2)}** {_citar(pib_pc_src, pib_pc_ano)}"
                )
            txt_pib = "A economia de " + nome + " registrou " + ", com ".join(partes_econ) + "."
            if vab_serv or vab_ind or vab_adm:
                vabt = []
                if vab_serv:
                    vabt.append(f"Serviços: R$ {_fmt_bi(float(vab_serv)/1_000_000)} bilhões")
                if vab_ind:
                    vabt.append(f"Indústria: R$ {_fmt_bi(float(vab_ind)/1_000_000)} bilhões")
                if vab_adm:
                    vabt.append(f"Administração Pública: R$ {_fmt_bi(float(vab_adm)/1_000_000)} bilhões")
                vab_ano = ib.pib.get("vab_servicos_mil", {}).get("ano", "") if ib.pib else ""
                txt_pib += (
                    f" O Valor Adicionado Bruto (VAB) distribui-se entre: "
                    + "; ".join(vabt)
                    + f" {_citar('IBGE', vab_ano)}."
                )
            paragrafos.append(p(txt_pib))

    # ---- 4.5 — Situação fiscal (CAPAG — fonte única Tesouro Nacional) ----
    if dados_capag and dados_capag.encontrado:
        cap = dados_capag
        status_geral = (
            "sem restrições para a prestação de garantia pela União"
            if cap.capag.upper() in ("A", "B")
            else "com restrições para garantia da União"
        )
        txt_cap = (
            f"Quanto à situação fiscal, o Município apresenta **nota CAPAG {cap.capag}** "
            f"(Capacidade de Pagamento) junto ao Tesouro Nacional, {status_geral} "
            f"(Fonte: Tesouro Nacional / STN). "
            f"Os indicadores componentes são: "
            f"Endividamento {float(cap.indicador_endividamento):.4f} (Nota {cap.nota_endividamento}), "
            f"Poupança Corrente {float(cap.indicador_poupanca):.4f} (Nota {cap.nota_poupanca}) e "
            f"Liquidez {float(cap.indicador_liquidez):.4f} (Nota {cap.nota_liquidez})."
        )
        paragrafos.append(p(txt_cap))

    # ---- 4.6 — Estrutura empresarial e emprego (IBGE CEMPRE / SEBRAE) ----
    if seb:
        partes_seb = []
        if seb.empresas_ativas:
            partes_seb.append(f"**{_fmt_numero(str(seb.empresas_ativas))} empresas e outras organizações ativas**")
        if seb.mei_ativos:
            partes_seb.append(f"**{_fmt_numero(str(seb.mei_ativos))} MEI**")
        if seb.empregos_formais:
            partes_seb.append(f"**{_fmt_numero(str(seb.empregos_formais))} trabalhadores assalariados** (emprego formal)")
        if seb.pessoal_total and seb.pessoal_total != seb.empregos_formais:
            partes_seb.append(f"**{_fmt_numero(str(seb.pessoal_total))} pessoas ocupadas** (total)")
        if seb.salario_medio:
            sal_fmt = f"R$ {seb.salario_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            partes_seb.append(f"salário médio mensal de **{sal_fmt}**")
        if partes_seb:
            ref_seb = _citar(seb.fonte or "IBGE SIDRA — CEMPRE", seb.ano_ref or None)
            txt_seb = (
                f"O tecido produtivo de {nome} registra: {'; '.join(partes_seb)} {ref_seb}. "
            )
            # Complemento com massa salarial, se disponível
            if seb.salarios_anuais_mil:
                massa_bi = seb.salarios_anuais_mil / 1_000_000
                txt_seb += (
                    f"A massa salarial anual totaliza **R$ {_fmt_bi(massa_bi)} bilhões** "
                    f"{_citar(seb.fonte or 'IBGE', seb.ano_ref or None)}. "
                )
            if seb.pessoal_ocupado_pct:
                txt_seb += (
                    f"O percentual de pessoal ocupado nas empresas em relação à população total é de "
                    f"**{seb.pessoal_ocupado_pct:.1f}%** {_citar('IBGE — Indicadores Municipais', seb.ano_ref or None)}. "
                )
            if seb.nota_enem:
                txt_seb += (
                    f"O município registrou nota média de **{seb.nota_enem:.1f} pontos no ENEM**, "
                    f"indicador relevante para o capital humano local {_citar('SEBRAE/INEP', seb.ano_ref or None)}. "
                )
            paragrafos.append(p(txt_seb))

    if not paragrafos:
        paragrafos.append(p(
            f"Dados municipais de {nome} – {uf}. "
            "*(Dados das fontes públicas não disponíveis para este município neste processamento.)*"
        ))

    # ---- Último parágrafo — contexto específico do objeto no município ----
    # Gerado por LLM (chamada5_contexto_objeto) com dados extraídos da proposta.
    if contexto_objeto:
        paragrafos.append(p(contexto_objeto))

    return "\n\n".join(paragrafos)


def _nome_estado(uf: str) -> str:
    estados = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
        "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
        "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
        "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
        "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
    }
    return estados.get(uf.upper(), uf)


def _nivel_idhm(valor: float) -> str:
    if valor >= 0.8:
        return "muito alto"
    elif valor >= 0.7:
        return "alto"
    elif valor >= 0.6:
        return "médio"
    elif valor >= 0.5:
        return "baixo"
    return "muito baixo"


def _fmt_numero(valor, decimais: int = 0) -> str:
    try:
        n = float(str(valor).replace(",", "."))
        if decimais:
            return f"{n:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{n:,.0f}".replace(",", ".")
    except Exception:
        return str(valor)


def _fmt_bi(valor: float) -> str:
    """Formata bilhões em padrão BR: 16,97 bilhões."""
    return f"{valor:.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Resolução de conflitos entre fontes — prioriza dado mais recente
# ---------------------------------------------------------------------------

def _resolver_dado(candidatos: list) -> tuple:
    """
    Recebe lista de (valor, ano, fonte_label) e retorna o dado mais recente
    com valor válido (não nulo, não vazio).

    Retorna: (valor, ano_int, fonte_label) ou (None, None, None)

    Exemplo:
        candidatos = [
            ("100", 2019, "Dados municipais"),
            ("200", 2021, "Atlas Brasil"),
            ("2000", 2025, "IBGE"),
        ]
        → ("2000", 2025, "IBGE")
    """
    validos = []
    for v, a, f in candidatos:
        if v is None or v == "" or v == "N/D":
            continue
        try:
            ano_int = int(str(a)) if a else 0
        except (TypeError, ValueError):
            ano_int = 0
        validos.append((v, ano_int, f))

    if not validos:
        return None, None, None

    validos.sort(key=lambda x: x[1], reverse=True)
    return validos[0]


def _citar(fonte: str, ano) -> str:
    """Formata inline citation: '(Fonte: IBGE, 2025)'."""
    if not fonte:
        return ""
    partes = [fonte]
    if ano:
        partes.append(str(ano))
    return f"({', '.join(partes)})"


# ---------------------------------------------------------------------------
# Limpeza pós-geração: remove cabeçalhos duplicados gerados pelo LLM
# ---------------------------------------------------------------------------

def _limpar_cabecalhos_duplicados(md: str) -> str:
    """
    Remove cabeçalhos de seção que o LLM repete acidentalmente dentro do
    corpo de texto logo após o cabeçalho oficial já inserido pelo template.

    Exemplo de problema:
        ## 6. ANÁLISE DE ENQUADRAMENTO DO PROJETO PRÓ-CIDADES   ← template
        *6. ANÁLISE DE ENQUADRAMENTO DO PROJETO PRÓ-CIDADES*    ← LLM repetiu
        6.1. ...

    A função detecta linhas que repetem o padrão de cabeçalho de seção (n. TÍTULO)
    imediatamente após um cabeçalho ## já presente e as remove.
    """
    # Padrões que o LLM costuma repetir como primeira linha do bloco gerado
    _PADROES_DUPLICADOS = [
        # "*6. ANÁLISE DE ENQUADRAMENTO...*" ou "**6. ANÁLISE...**"
        re.compile(r"^\*{1,2}\d+\.\s+[A-ZÁÉÍÓÚÃÕ\s]+\*{1,2}$", re.MULTILINE),
        # "6. ANÁLISE DE ENQUADRAMENTO..." sem markdown, linha sozinha maiúscula
        re.compile(r"^\d+\.\s+[A-ZÁÉÍÓÚÃÕ]{4,}[A-ZÁÉÍÓÚÃÕ\s]+$", re.MULTILINE),
    ]

    linhas = md.split("\n")
    resultado = []
    ultimo_cabecalho_n = None

    for i, linha in enumerate(linhas):
        # Detecta cabeçalho ## oficial do template
        m = re.match(r"^#{1,3}\s+(\d+)\.", linha)
        if m:
            ultimo_cabecalho_n = int(m.group(1))
            resultado.append(linha)
            continue

        # Verifica se esta linha é uma repetição do cabeçalho recém-definido
        if ultimo_cabecalho_n is not None:
            # Testa se a linha começa com o mesmo número de seção e é somente título
            duplicado = False
            for pat in _PADROES_DUPLICADOS:
                if pat.match(linha.strip()):
                    # Confirma que o número bate com o último cabeçalho
                    m2 = re.match(r"\*{0,2}(\d+)\.", linha.strip())
                    if m2 and int(m2.group(1)) == ultimo_cabecalho_n:
                        duplicado = True
                        break
            if duplicado:
                logger.debug("Cabeçalho duplicado removido: %r", linha[:80])
                continue  # pula a linha duplicada

        resultado.append(linha)

    return "\n".join(resultado)


# ---------------------------------------------------------------------------
# Gerador de Markdown — formato oficial MCID (8 secoes)
# ---------------------------------------------------------------------------

def gerar_parecer_md(
    dados: dict,
    sumario: str,
    analise: str,
    checklist: dict,
    conformidade_results: list[dict],
    capag_result: dict,
    dados_municipio: dict,
    dados_ibge=None,
    dados_capag=None,
    dados_idh=None,
    dados_sebrae=None,
    dados_planalto=None,
    contexto_objeto: str = "",
) -> str:

    municipio = dados.get("municipio") or dados_municipio.get("municipio", "___")
    uf = dados.get("uf") or dados_municipio.get("uf", "")
    num_proposta = dados.get("numero_proposta", "___")
    proponente = dados.get("proponente", "___")
    objeto = dados.get("objeto", "")

    # ---- Cabeçalho ----
    cabecalho = f"""\
MINISTÉRIO DAS CIDADES  
Secretaria Nacional de Desenvolvimento Urbano e Metropolitano  
Departamento de Adaptação das Cidades à Transição Climática e Transformação Digital  
Coordenação-Geral de Modernização Urbana

---

# Parecer de Mérito — Proposta Técnica nº {num_proposta}/CGMUR/DAC/SNDUM-MCID

**Referência:** Proposta Técnica nº {num_proposta} — Programa Pró-Cidades  
**Processo SEI:** {dados.get("processo_sei", "___")}  
**Assunto:** Parecer de Mérito sobre a proposta de enquadramento na Modalidade 2 do Programa de Desenvolvimento Urbano de projeto para {objeto[:180] + "..." if len(objeto) > 180 else objeto}, apresentado por {proponente}.

---"""

    # ---- Seção 1: Sumário Executivo ----
    sec1 = f"## 1. SUMÁRIO EXECUTIVO\n\n{sumario}"

    # ---- Seção 2: Competência (boilerplate) ----
    sec2 = f"## 2. COMPETÊNCIA\n\n{TEXTO_COMPETENCIA}"

    # ---- Seção 3: Proposta (Quadro 1) ----
    pop = dados_municipio.get("populacao") or (str(dados_ibge.populacao_estimada) if dados_ibge else "")
    pop_ben = dados.get("populacao_beneficiada", pop)
    agente = dados.get("agente_financeiro", "")
    cnpj_agente = ""
    if "BRDE" in agente.upper():
        cnpj_agente = " (CNPJ 92.816.560/0001-37)"
    elif "CAIXA" in agente.upper():
        cnpj_agente = " (CNPJ 00.360.305/0001-04)"

    sec3 = f"""\
## 3. PROPOSTA

**3.1.** Os dados da Proposta Técnica nº {num_proposta} encontram-se apontados abaixo (Quadro 1).

**Quadro 1** – Dados da Proposta de modernização tecnológica urbana apresentada por {proponente}

| Campo | Valor |
|-------|-------|
| Natureza do Proponente | {dados.get("natureza", "")} |
| Identificação do Proponente | {proponente} |
| CNPJ | {dados.get("cnpj", "")} |
| Modalidade | {dados.get("modalidade", "")} |
| Objeto | {objeto} |
| Valor de Financiamento (A) | {dados.get("valor_financiamento", "")} |
| Valor de Contrapartida (B) | {dados.get("valor_contrapartida", "")} |
| Valor Investimento (A) + (B) | {dados.get("valor_total", "")} |
| Município beneficiado | {municipio} – {uf} |
| Agente Financeiro | {agente}{cnpj_agente} |
| Contrato de Concessão/PPP | {dados.get("contrato_concessao", "—")} |
| Responsável Técnico | {dados.get("responsavel_tecnico", "—")} |
| População Municipal Estimada (IBGE 2025) | {pop} |
| População Beneficiada Estimada pelo Proponente | {pop_ben} |"""

    # ---- Seção 4: O Município ----
    sec4_corpo = _gerar_secao_municipio(
        municipio, uf, dados_ibge, dados_capag, dados_idh, dados_sebrae,
        contexto_objeto=contexto_objeto,
    )
    sec4 = f"## 4. O MUNICÍPIO DE {municipio.upper()}\n\n{sec4_corpo}"

    # ---- Seção 5: Descrição da Proposta ----
    resp_tec = dados.get("responsavel_tecnico", "")
    contrato = dados.get("contrato_concessao", "")
    sec5 = f"""\
## 5. DESCRIÇÃO DA PROPOSTA

**5.1.** {proponente} submeteu ao Ministério das Cidades, por intermédio do Programa de Desenvolvimento das Cidades (Pró-Cidades), a **Proposta Técnica nº {num_proposta}**, solicitando financiamento de {dados.get("valor_financiamento", "___")} para {objeto}.{"" if not contrato else f" O Projeto decorre do **{contrato}** celebrado com o poder público municipal."}{"" if not resp_tec else f" O responsável técnico designado é **{resp_tec}**."}

**5.2.** O montante total do investimento é de **{dados.get("valor_total", "___")}**, sendo **{dados.get("valor_financiamento", "___")}** financiados com recursos do Fundo de Garantia por Tempo de Serviço (FGTS) via Pró-Cidades e **{dados.get("valor_contrapartida", "___")}** correspondentes à contrapartida do proponente.

**5.3.** O projeto encontra-se alinhado às diretrizes da Carta Brasileira de Cidades Inteligentes e à Política Nacional de Desenvolvimento Urbano, objetivando a melhoria da qualidade dos serviços públicos prestados à população, a otimização do consumo energético e a ampliação da segurança e do conforto nos espaços urbanos."""

    # ---- Seção 6: Análise de Enquadramento ----
    sec6 = f"## 6. ANÁLISE DE ENQUADRAMENTO DO PROJETO PRÓ-CIDADES\n\n{analise}"

    # ---- Seção 7: Atendimento Normativo (Checklist) ----
    checklist_rows = ""
    for item in CHECKLIST_ITEMS:
        status = checklist.get(str(item["id"]), "—")
        checklist_rows += f"| {item['id']} | {item['doc']} | **{status}** |\n"

    # Gerar análise por item com pendências
    pendencias = [
        CHECKLIST_ITEMS[i] for i in range(len(CHECKLIST_ITEMS))
        if checklist.get(str(CHECKLIST_ITEMS[i]["id"])) in ("Não disponível", "Atendido parcialmente")
    ]

    analise_checklist = (
        "\n\n**7.2.** Uma vez que a aplicação dos recursos financeiros do Pró-Cidades encontra-se "
        "territorialmente restrita à zona urbana dos municípios, conforme especificado no **art. 5° "
        "da Lei nº 8.036, de 11 de maio de 1990**, que dispõe sobre o FGTS, a comprovação da "
        "aplicação dos recursos na área urbana assume importância central, razão pela qual torna-se "
        "necessário avaliar o cumprimento do especificado no item 1 do Quadro 3.\n"
    )
    if pendencias:
        itens_pend = ", ".join(f"item {p['id']}" for p in pendencias)
        analise_checklist += (
            f"\n**7.3.** Da análise documental realizada, verificou-se que os seguintes itens do "
            f"Quadro 3 apresentam pendências ou atendimento parcial: **{itens_pend}**. "
            f"Recomenda-se que o Proponente adote as providências necessárias para o saneamento "
            f"das exigências antes do deferimento final.\n"
            f"\n**7.4.** Por tudo, entende-se que a Proponente cumpriu os requisitos de mérito "
            f"examinados no presente Parecer para fazer jus ao financiamento do Pró-Cidades, "
            f"restando, contudo, a necessidade de adotar as providências mencionadas nos itens "
            f"pendentes deste Quadro 3."
        )
    else:
        analise_checklist += (
            "\n**7.3.** Da análise documental realizada, todos os itens aplicáveis do Quadro 3 "
            "encontram-se cumpridos ou devidamente justificados como não cabíveis, evidenciando "
            "que a Proponente atendeu integralmente às exigências do Anexo II da IN MCID nº 18/2025.\n"
            "\n**7.4.** Por tudo, entende-se que a Proponente cumpriu integralmente os requisitos "
            "de mérito examinados no presente Parecer para fazer jus ao financiamento do Pró-Cidades."
        )

    sec7 = f"""\
## 7. ATENDIMENTO AOS CRITÉRIOS E ÀS CONDIÇÕES NORMATIVAS

**7.1.** Com relação aos requisitos normativos a serem cumpridos pela Proponente, previstos no **Anexo II da IN MCID nº 18, de 2025**, ao analisar a documentação constante da Proposta Técnica nº {num_proposta}, identificou-se a situação descrita no Quadro 3.

*Observação: A definição do perímetro da área de intervenção deve ser devidamente identificada e caracterizada, sendo obrigatória a sua delimitação em arquivo com extensão .kml ou .kmz, ou, alternativamente, sobre imagem de satélite ou fotografia aérea de alta resolução.*

**Quadro 3** – Documentação analisada para enquadramento da Proposta de {proponente}

| Item | Documento | Situação |
|------|-----------|----------|
{checklist_rows}{analise_checklist}"""

    # ---- Seção 8: Conclusão ----
    normas_alinhamento = (
        "**Instrução Normativa MCID nº 18, de 25 de abril de 2025**, à "
        "**Resolução CCFGTS nº 897, de 11 de setembro de 2018** e à "
        "**Portaria MCID nº 359, de 9 de abril de 2025**"
    )

    if pendencias:
        _itens_pend_str = "; ".join(f"({p['id']}) {p['doc']}" for p in pendencias)
        conclusao_txt = (
            f"**PENDÊNCIAS DOCUMENTAIS.** A proposta reúne os elementos técnicos suficientes "
            f"para aprovação de mérito e está em conformidade normativa com a IN MCID nº 18/2025 e "
            f"Resolução CCFGTS nº 897/2018. Contudo, recomenda-se **diligência** para apresentação "
            f"dos seguintes itens: {_itens_pend_str}. "
            f"Após o atendimento dessas exigências, a viabilidade técnica poderá ser deferida."
        )
    else:
        conclusao_txt = (
            "**VIABILIDADE TÉCNICA DEFERIDA.** A proposta reúne todos os elementos técnicos e "
            "documentais exigidos, em plena conformidade com a IN MCID nº 18/2025 e Resolução "
            "CCFGTS nº 897/2018. Recomenda-se o deferimento e encaminhamento ao Departamento de "
            "Desenvolvimento Urbano."
        )

    capag_status = capag_result.get("detalhe", "N/D")

    # Monta benefícios quantitativos da Seção 8.2 a partir dos dados extraídos
    # Usa campos de eficiência presentes na extração (chamada1) quando disponíveis
    _benef_quant = []
    _red_consumo = dados.get("reducao_consumo_pct", "")
    _red_co2     = dados.get("reducao_co2_ton", "")
    _econ_kwh    = dados.get("economia_energia_kwh", "")
    if _red_consumo:
        _benef_quant.append(f"a **redução de {_red_consumo}% no consumo de energia elétrica**")
    if _red_co2:
        _benef_quant.append(f"a **mitigação de {_red_co2} toneladas de emissões de CO₂**")
    if _econ_kwh:
        _benef_quant.append(f"a **economia de {_econ_kwh}**")

    if _benef_quant:
        _beneficios_str = (
            "a melhoria da qualidade de vida da população urbana, a democratização do acesso "
            "a espaços públicos iluminados, " + ", ".join(_benef_quant) +
            f" e a ampliação dos ganhos de eficientização por meio de investimentos na "
            f"modernização tecnológica urbana, com a substituição integral dos pontos de "
            f"iluminação pública por tecnologia LED e implantação de telegestão no Município de {municipio}"
        )
    else:
        _beneficios_str = (
            "a melhoria da qualidade de vida da população urbana, a democratização do acesso "
            "a espaços públicos, infraestrutura, equipamentos e mobiliários urbanos, a otimização "
            "do consumo de energia elétrica e a ampliação dos ganhos de eficientização por meio de "
            f"investimentos na modernização tecnológica urbana do Município de {municipio}"
        )

    sec8 = f"""\
## 8. CONCLUSÃO

**8.1.** Com base no exposto, o Projeto encontra-se alinhado aos princípios e diretrizes da **Carta Brasileira de Cidades Inteligentes**, da {normas_alinhamento}.

**8.2.** O material apresentado informa que o projeto promove {_beneficios_str}.

**8.3.** Destarte, identifica-se que a proposta reúne os elementos técnicos {"suficientes" if pendencias else "integrais"} para sua {"aprovação condicionada ao saneamento das pendências documentais apontadas" if pendencias else "aprovação"}, uma vez que a intervenção proposta é fundamental para garantir maior eficiência energética, segurança pública e qualidade de vida para a população de {municipio}. {"Não obstante, cabe assinalar a necessidade de observar o elencado nos itens 7.3 e 7.4 deste Parecer." if pendencias else ""}

**8.4.** Situação CAPAG do Município: {capag_status}.

**8.5.** {conclusao_txt}

Nesse sentido, recomenda-se encaminhar o presente Parecer de Mérito para atender ao solicitado pelo Departamento de Desenvolvimento Urbano.

---

*(assinatura eletrônica)*  
**[ANALISTA DE INFRAESTRUTURA]**  
Analista de Infraestrutura — CGMUR/DAC/SNDUM-MCID

De acordo. Encaminhe-se o entendimento desta Unidade ao Departamento de Adaptação das Cidades à Transição Climática e Transformação Digital.

*(assinatura eletrônica)*  
**[COORDENADOR-GERAL DE MODERNIZAÇÃO URBANA]**  
Coordenador-Geral de Modernização Urbana — CGMUR/DAC/SNDUM-MCID"""

    # ---- Rodapé ----
    idhm_str = ""
    if dados_idh and dados_idh.idhm:
        idhm_str = f" | Atlas Brasil/PNUD (IDHM {dados_idh.idhm:.3f}, {dados_idh.ano})"

    sebrae_str = ""
    if dados_sebrae and dados_sebrae.encontrado:
        sebrae_str = " | SEBRAE — Observatório Setorial Territorial"

    # Normas Planalto consultadas
    planalto_str = ""
    if dados_planalto and dados_planalto.normas:
        normas_ok = [
            f"{n.label} ({n.sigla})"
            for n in dados_planalto.normas.values()
            if n.acessivel
        ]
        if normas_ok:
            planalto_str = " | Planalto.gov.br: " + " | ".join(normas_ok)

    rodape = (
        f"\n---\n\n"
        f"*Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M')}.*  \n"
        f"*Fontes consultadas: IBGE (servicodados.ibge.gov.br) | Tesouro Nacional — CAPAG | "
        f"Ministério das Cidades — Legislação Pró-Cidades{idhm_str}{sebrae_str}{planalto_str}.*  \n"
        f"*Base normativa: IN MCID nº 18/2025 | Res. CCFGTS nº 897/2018 | Lei nº 8.036/1990 | "
        f"Portaria MCID nº 359/2025 | Decreto nº 12.210/2024 | Lei nº 13.089/2015 (Estatuto da Metrópole) | "
        f"Lei nº 10.257/2001 (Estatuto da Cidade).*"
    )

    md_bruto = "\n\n".join([cabecalho, sec1, sec2, sec3, sec4, sec5, sec6, sec7, sec8]) + rodape
    return _limpar_cabecalhos_duplicados(md_bruto)
