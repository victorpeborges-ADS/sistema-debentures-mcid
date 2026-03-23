"""
Gerencia a biblioteca de pareceres validados e o registro de feedbacks.

- pareceres_validados/  : pareceres .md aprovados, usados como few-shot dinâmico
- feedbacks/feedbacks.jsonl : sugestões e avaliações da equipe

Few-shot e guia de estilo ignoram ficheiros cujo texto indique parecer de **Pro-Cidades**
(ruído para o produto Debêntures). Coloque apenas exemplos alinhados à Lei 12.431/2011.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

BIBLIOTECA_DIR = Path(__file__).parent / "biblioteca"
PARECERES_DIR = BIBLIOTECA_DIR / "pareceres_validados"
FEEDBACKS_DIR = BIBLIOTECA_DIR / "feedbacks"
FEEDBACKS_FILE = FEEDBACKS_DIR / "feedbacks.jsonl"

# Garante que as pastas existem na inicialização do módulo
PARECERES_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACKS_DIR.mkdir(parents=True, exist_ok=True)

# Quando não há .md elegíveis, o motor ainda recebe orientação mínima (sem ruído Pro-Cidades).
GUIA_ESTILO_PADRAO_DEBENTURES = """
## GUIA DE ESTILO (padrão — biblioteca sem exemplos .md elegíveis)

• Fundamentação: **Lei nº 12.431/2011** e normas CVM aplicáveis a debêntures incentivadas; não use IN MCID 18/2025 como base do enquadramento.
• Parágrafos numerados (**1.1.**, **6.3.**, etc.) e registo jurídico-administrativo.
• Normas em **negrito**; dados municipais com indicação de fonte (IBGE, CAPAG, etc.).
• Terceira pessoa, sem copiar dados de outros municípios.
"""


def _texto_indica_conteudo_procidades(amostra: str) -> bool:
    """Heurística: texto de parecer claramente do programa Pro-Cidades (excluir do few-shot)."""
    if not amostra or not amostra.strip():
        return False
    t = amostra.lower()
    if "pró-cidades" in t or "pro-cidades" in t:
        return True
    if "programa pró-cidades" in t or "programa pro-cidades" in t:
        return True
    if re.search(r"\b8\.6\.6\.3\.4\b", amostra):
        return True
    return False


def _parecer_elegivel_fewshot(path: Path) -> bool:
    """True se o ficheiro pode ser usado como referência de estilo para Debêntures."""
    try:
        amostra = path.read_text(encoding="utf-8")[:20000]
    except OSError as e:
        logger.warning("Não foi possível ler %s: %s", path.name, e)
        return False
    if _texto_indica_conteudo_procidades(amostra):
        logger.info(
            "Biblioteca: ignorado para few-shot (conteúdo Pro-Cidades / IN 18 típico): %s",
            path.name,
        )
        return False
    return True


def listar_pareceres_para_fewshot() -> List[Path]:
    """Lista .md aptos a few-shot (exclui ruído Pro-Cidades)."""
    return [p for p in listar_pareceres() if _parecer_elegivel_fewshot(p)]


# ---------------------------------------------------------------------------
# Pareceres validados
# ---------------------------------------------------------------------------

def listar_pareceres() -> List[Path]:
    """Retorna lista de arquivos .md na pasta de pareceres validados, mais recentes primeiro."""
    arquivos = sorted(
        PARECERES_DIR.glob("*.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return arquivos


def get_exemplos_fewshot(max_exemplos: int = 3, max_chars_por_exemplo: int = 6000) -> str:
    """
    LEGADO — mantido para compatibilidade. Prefira get_exemplos_secao().
    Retorna pareceres completos truncados. Não usar para novas chamadas LLM.
    """
    arquivos = listar_pareceres_para_fewshot()
    if not arquivos:
        return ""
    blocos = []
    for arq in arquivos[:max_exemplos]:
        try:
            conteudo = arq.read_text(encoding="utf-8").strip()
            if len(conteudo) > max_chars_por_exemplo:
                metade = max_chars_por_exemplo // 2
                conteudo = (
                    conteudo[:metade]
                    + "\n\n[...trecho omitido...]\n\n"
                    + conteudo[-metade:]
                )
            blocos.append(f"### Exemplo: {arq.stem}\n\n{conteudo}")
        except Exception as e:
            logger.warning("Não foi possível ler %s: %s", arq.name, e)
    if not blocos:
        return ""
    return (
        "\n\n---\n## PARECERES DE REFERÊNCIA\n\n"
        + "\n\n---\n\n".join(blocos)
        + "\n\n---\n"
    )


# ---------------------------------------------------------------------------
# Injeção cirúrgica por seção — o modo correto de usar a biblioteca
#
# Cada chamada LLM deve receber APENAS os trechos relevantes para a seção
# que está sendo gerada. Isso evita que o modelo copie dados de municípios
# errados e garante que os exemplos tenham impacto real no texto gerado.
# ---------------------------------------------------------------------------

# Mapeamento de seções do parecer para as palavras-chave que as delimitam.
# Cada entrada: (lista de keywords de início, lista de keywords de seções seguintes)
#
# Os pareceres na biblioteca podem vir de duas fontes:
#   a) PDFs extraídos (texto fragmentado, sem `#` Markdown)
#   b) Markdown gerado pelo sistema (com `## N. NOME`)
# O extrator abaixo lida com ambos.
_SECAO_KEYWORDS = {
    1: {
        "nome": "Sumário Executivo",
        "inicio": ["SUMÁRIO EXECUTIVO", "O presente Parecer de Mérito"],
        "fim_proximo": ["COMPETÊNCIA", "IDENTIF", "2.\nCOM", "## 2."],
    },
    2: {
        "nome": "Competência",
        "inicio": ["COMPETÊNCIA", "Com base na Lei"],
        "fim_proximo": ["PROPOSTA", "3.\nPRO", "## 3.", "IDENTIFICAÇÃO"],
    },
    3: {
        "nome": "Identificação da Proposta",
        "inicio": [
            "PROPOSTA\n",
            "IDENTIFICAÇÃO DA PROPOSTA",
            "3.\nPRO",
            "QUADRO 1",
        ],
        "fim_proximo": ["O MUNICÍPIO", "4.\nO M", "## 4.", "DADOS DO MUNICÍPIO"],
    },
    4: {
        "nome": "O Município",
        # Usa apenas formas MAIÚSCULAS para não confundir com menções no corpo do texto
        "inicio": [
            "O MUNICÍPIO DE ",
            "DADOS DO MUNICÍPIO",
            "## 4. O MUN",
            "## 4. MUN",
            "4. O MUNICÍPIO",
        ],
        "fim_proximo": ["ANÁLISE DE ENQUADRAMENTO", "DESCRIÇÃO DA PROPOSTA", "PROJETO E DOCUMENTAÇÃO",
                        "5.\nANÁL", "5.\nDESC", "## 5."],
    },
    5: {
        "nome": "Descrição da Proposta",
        "inicio": ["DESCRIÇÃO DA PROPOSTA", "5.\nDESC", "## 5. DESCRI"],
        "fim_proximo": ["ANÁLISE DE ENQUADRAMENTO", "6.\nANÁ", "## 6."],
    },
    6: {
        "nome": "Análise de Enquadramento",
        "inicio": ["ANÁLISE DE ENQUADRAMENTO", "5.\nANÁL", "6.\nANÁL",
                   "## 5. ANÁL", "## 6. ANÁL",
                   "debêntures incentivadas", "Lei nº 12.431"],
        "fim_proximo": ["ATENDIMENTO AOS CRITÉRIOS", "ATENDIMENTO À DOCUMENTAÇÃO",
                        "CHECKLIST", "CONCLUSÃO",
                        "6.\nATE", "7.\nCHE", "7.\nCON", "## 7."],
    },
    7: {
        "nome": "Atendimento à documentação da operação",
        "inicio": [
            "ATENDIMENTO À DOCUMENTAÇÃO",
            "CHECKLIST",
            "ATENDIMENTO AOS CRITÉRIOS",
            "6.\nATE",
            "## 7.",
        ],
        "fim_proximo": ["CONCLUSÃO", "PARECER CONCLUSIVO", "7.\nCON", "8.\nPAR", "## 8."],
    },
    8: {
        "nome": "Parecer Conclusivo",
        "inicio": ["CONCLUSÃO", "PARECER CONCLUSIVO", "7.\nCON", "8.\nPAR",
                   "## 7. CON", "## 8. PAR",
                   "Com base no exposto"],
        "fim_proximo": [],
    },
}

_SECAO_NOMES = {k: v["nome"] for k, v in _SECAO_KEYWORDS.items()}


def _extrair_secao(texto: str, numero: int) -> str:
    """
    Extrai o texto de uma seção específica de um parecer.

    Compatível com dois formatos:
      - Markdown com `## N. NOME` (pareceres gerados pelo sistema)
      - Texto plano de PDF extraído (números fragmentados, sem `#`)
    """
    import re
    info = _SECAO_KEYWORDS.get(numero)
    if not info:
        return ""

    # Tenta cada palavra-chave de início na ordem de prioridade
    pos_inicio = -1
    for kw in info["inicio"]:
        idx = texto.find(kw)
        if idx != -1:
            pos_inicio = idx
            break

    if pos_inicio == -1:
        return ""

    trecho = texto[pos_inicio:]

    # Encontra o fim: primeira keyword da seção seguinte
    pos_fim = len(trecho)
    for kw_fim in info["fim_proximo"]:
        idx_fim = trecho.find(kw_fim)
        # Garante que não corta antes de 200 chars (mínimo útil)
        if idx_fim != -1 and idx_fim > 200:
            pos_fim = min(pos_fim, idx_fim)

    return trecho[:pos_fim].strip()


def get_exemplos_secao(
    numero_secao: int,
    max_exemplos: int = 2,
    max_chars: int = 2500,
) -> str:
    """
    Retorna exemplos da seção N extraídos dos pareceres validados da biblioteca.

    Esta é a função correta para injeção few-shot. Cada chamada LLM deve
    receber apenas a seção que está sendo gerada, não o parecer inteiro.

    - Elimina o risco do modelo copiar dados (população, CAPAG) de outros municípios
    - Mantém o contexto pequeno → menor latência e menor custo
    - O modelo aprende o PADRÃO da seção, não o conteúdo de outro caso

    Args:
        numero_secao: número da seção (1–8)
        max_exemplos: quantos pareceres da biblioteca usar
        max_chars: limite de chars por exemplo extraído
    """
    arquivos = listar_pareceres_para_fewshot()
    if not arquivos:
        return ""

    nome_secao = _SECAO_NOMES.get(numero_secao, f"Seção {numero_secao}")
    blocos = []

    # Percorre TODOS os arquivos até ter max_exemplos com a seção encontrada
    for arq in arquivos:
        if len(blocos) >= max_exemplos:
            break
        try:
            conteudo = arq.read_text(encoding="utf-8")
            secao = _extrair_secao(conteudo, numero_secao)
            if not secao:
                continue
            if len(secao) > max_chars:
                secao = secao[:max_chars] + "\n[...trecho completo disponível no documento original...]"
            blocos.append(
                f"EXEMPLO DE {nome_secao.upper()} (parecer: {arq.stem}):\n"
                f"{'─'*60}\n"
                f"{secao}\n"
                f"{'─'*60}"
            )
        except Exception as e:
            logger.warning("Erro ao extrair seção %d de %s: %s", numero_secao, arq.name, e)

    if not blocos:
        return ""

    instrucao = (
        f"\n\n## REFERÊNCIA DE ESTILO — {nome_secao.upper()}\n"
        f"Os trechos abaixo são exemplos de pareceres **debêntures incentivadas** na biblioteca.\n"
        f"Use-os EXCLUSIVAMENTE como modelo de:\n"
        f"  • Estrutura e numeração dos parágrafos\n"
        f"  • Tom e linguagem jurídico-administrativa\n"
        f"  • Nível de detalhe técnico esperado\n"
        f"  • Padrão de citação de normas e fontes\n"
        f"NÃO copie nomes de municípios, valores, datas ou dados técnicos destes exemplos.\n"
        f"Substitua TODO o conteúdo factual pelos dados do projeto atual.\n"
        f"NÃO reproduza linguagem do Programa Pró-Cidades ou IN MCID 18/2025 como fundamento.\n\n"
    )
    return instrucao + "\n\n".join(blocos) + "\n\n"


def get_guia_estilo() -> str:
    """
    Gera um guia de estilo compacto extraído dos pareceres validados da biblioteca.
    Ideal para injetar no system prompt.

    Detecta padrões de escrita nos textos reais, incluindo o formato de PDF
    extraído (parágrafos numerados como "1.\n2.") e Markdown gerado pelo sistema.
    """
    arquivos = listar_pareceres_para_fewshot()
    if not arquivos:
        return GUIA_ESTILO_PADRAO_DEBENTURES.strip() + "\n"

    total = len(arquivos)

    # Indicadores de padrões de escrita
    usa_negrito_normas = 0       # **Lei nº**, **CVM**
    usa_numeracao_ponto = 0      # 4.1. ou **4.1.**
    usa_citacao_inline = 0       # (Fonte: IBGE)
    usa_linguagem_formal = 0     # "nos termos do", "in verbis", "destarte"
    usa_terceira_pessoa = 0      # "o município", "o proponente", "a prefeitura"
    usa_valores_reais = 0        # R$ X.XXX.XXX,XX

    for arq in arquivos[:5]:
        try:
            txt = arq.read_text(encoding="utf-8")
            if re.search(
                r"(?:Lei n[oº°]\s*12\.431|Lei n[oº°]|Decreto n[oº°]|Resolução|CVM)",
                txt,
                re.IGNORECASE,
            ):
                usa_negrito_normas += 1
            if re.search(r"\d+\s*\.\s*\d+\s*\.", txt):
                usa_numeracao_ponto += 1
            if re.search(r"\(Fonte:", txt, re.IGNORECASE):
                usa_citacao_inline += 1
            if re.search(r"(?:nos termos|in verbis|destarte|consoante|doravante)", txt, re.IGNORECASE):
                usa_linguagem_formal += 1
            if re.search(r"(?:o município|o proponente|a prefeitura|o projeto)", txt, re.IGNORECASE):
                usa_terceira_pessoa += 1
            if re.search(r"R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}", txt):
                usa_valores_reais += 1
        except Exception:
            pass

    padroes = [
        "parágrafos numerados sequencialmente: 1.1., 1.2., 4.1., 4.2., etc.",
    ]
    if usa_negrito_normas > 0:
        padroes.append("normas citadas na íntegra: 'Lei nº 12.431, de 3 de junho de 2011'")
    if usa_linguagem_formal > 0:
        padroes.append("expressões jurídico-formais: 'nos termos de', 'destarte', 'consoante'")
    if usa_terceira_pessoa > 0:
        padroes.append("3ª pessoa: 'o Município', 'o Proponente', 'a Concessionária'")
    if usa_valores_reais > 0:
        padroes.append("valores monetários: R$ 35.000.000,00 (dois decimais, ponto milhar, vírgula decimal)")
    if usa_citacao_inline > 0:
        padroes.append("citações de fonte: (Fonte: IBGE, 2024) ou (IBGE — SIDRA, 2022)")

    return (
        f"\n## GUIA DE ESTILO (baseado em {total} parecer(es) validado(s) na biblioteca)\n"
        + "\n".join(f"• {p}" for p in padroes)
        + "\n"
    )


def salvar_parecer_na_biblioteca(nome_arquivo: str, conteudo_md: str) -> Path:
    """
    Salva um parecer gerado na biblioteca de validados.
    Retorna o path do arquivo salvo.
    """
    if not nome_arquivo.endswith(".md"):
        nome_arquivo += ".md"
    destino = PARECERES_DIR / nome_arquivo
    destino.write_text(conteudo_md, encoding="utf-8")
    if _texto_indica_conteudo_procidades(conteudo_md[:20000]):
        logger.warning(
            "Parecer salvo contém marcas de Pro-Cidades / IN 18 típico — será ignorado no few-shot: %s",
            destino.name,
        )
    logger.info("Parecer salvo na biblioteca: %s", destino)
    return destino


def remover_parecer(nome_arquivo: str) -> bool:
    """Remove um parecer da biblioteca. Retorna True se bem-sucedido."""
    alvo = PARECERES_DIR / nome_arquivo
    if alvo.exists():
        alvo.unlink()
        return True
    return False


def info_biblioteca() -> dict:
    """Retorna estatísticas resumidas da biblioteca."""
    arquivos = listar_pareceres()
    elegiveis = listar_pareceres_para_fewshot()
    total_chars = 0
    for arq in arquivos:
        try:
            total_chars += len(arq.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_pareceres": len(arquivos),
        "pareceres_elegiveis_fewshot": len(elegiveis),
        "pareceres_excluidos_ruido": max(0, len(arquivos) - len(elegiveis)),
        "total_chars": total_chars,
        "arquivos": [
            {
                "nome": arq.name,
                "tamanho_kb": round(arq.stat().st_size / 1024, 1),
                "modificado": datetime.fromtimestamp(arq.stat().st_mtime).strftime(
                    "%d/%m/%Y %H:%M"
                ),
            }
            for arq in arquivos
        ],
    }


# ---------------------------------------------------------------------------
# Feedbacks
# ---------------------------------------------------------------------------

SECOES_OPCOES = [
    "Geral — qualidade geral do parecer",
    "1 — Sumário Executivo",
    "3 — Identificação da Proposta (Quadro 1)",
    "4 — O Município",
    "5 — Descrição da Proposta",
    "6 — Análise de Enquadramento",
    "7 — Atendimento à documentação da operação",
    "8 — Conclusão",
    "Dados externos (IBGE / CAPAG / IDH)",
    "Outro",
]

AVALIACOES = {
    1: "⭐ Muito ruim",
    2: "⭐⭐ Ruim",
    3: "⭐⭐⭐ Regular",
    4: "⭐⭐⭐⭐ Bom",
    5: "⭐⭐⭐⭐⭐ Excelente",
}


def salvar_feedback(
    municipio: str,
    secao: str,
    avaliacao: int,
    comentario: str,
    autor: str = "",
    provedor_ia: str = "",
) -> bool:
    """
    Registra um feedback no arquivo JSONL (uma entrada JSON por linha).
    Retorna True se salvo com sucesso.
    """
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "municipio": municipio.strip(),
        "secao": secao,
        "avaliacao": avaliacao,
        "comentario": comentario.strip(),
        "autor": autor.strip(),
        "provedor_ia": provedor_ia,
    }
    try:
        with open(FEEDBACKS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        logger.error("Erro ao salvar feedback: %s", e)
        return False


def listar_feedbacks(limite: int = 200) -> List[dict]:
    """Retorna os feedbacks mais recentes (mais novo primeiro)."""
    if not FEEDBACKS_FILE.exists():
        return []
    try:
        linhas = FEEDBACKS_FILE.read_text(encoding="utf-8").strip().splitlines()
        entradas = []
        for linha in linhas:
            try:
                entradas.append(json.loads(linha))
            except json.JSONDecodeError:
                pass
        return list(reversed(entradas))[:limite]
    except Exception as e:
        logger.error("Erro ao ler feedbacks: %s", e)
        return []


def resumo_feedbacks() -> dict:
    """Retorna estatísticas dos feedbacks para exibição no app."""
    todos = listar_feedbacks(limite=9999)
    if not todos:
        return {"total": 0, "media": None, "por_secao": {}, "recentes": []}

    avaliacoes = [f["avaliacao"] for f in todos if isinstance(f.get("avaliacao"), int)]
    media = round(sum(avaliacoes) / len(avaliacoes), 1) if avaliacoes else None

    por_secao: dict = {}
    for fb in todos:
        secao = fb.get("secao", "Geral")
        if secao not in por_secao:
            por_secao[secao] = []
        if isinstance(fb.get("avaliacao"), int):
            por_secao[secao].append(fb["avaliacao"])

    media_por_secao = {
        s: round(sum(vals) / len(vals), 1)
        for s, vals in por_secao.items()
        if vals
    }

    return {
        "total": len(todos),
        "media": media,
        "por_secao": media_por_secao,
        "recentes": todos[:5],
    }
