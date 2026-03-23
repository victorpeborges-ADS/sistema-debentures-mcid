"""
Títulos e metadados da estrutura de Parecer de Mérito — debêntures incentivadas,
alinhados aos pareceres reais SEI (Portaria MCID nº 359/2025, Decreto 11.964/2024,
Lei 12.431/2011, Lei 14.801/2024).

Ver documentação: docs/ESTRUTURA_PARECER_DEBENTURES_SEI.md
"""

from __future__ import annotations

# Ordem e nomes usados em gerar_parecer_md (motor.py)
SEC_SUMARIO = "SUMÁRIO EXECUTIVO"
SEC_COMPETENCIA = "COMPETÊNCIA"
SEC_IDENTIFICACAO = "IDENTIFICAÇÃO DA PROPOSTA"
SEC_MUNICIPIO_PREFIX = "DADOS DO MUNICÍPIO"
SEC_PROJETO_DOC = "PROJETO E DOCUMENTAÇÃO APRESENTADA"
SEC_ANALISE = (
    "ANÁLISE DE ENQUADRAMENTO (Decreto nº 11.964/2024, Portaria MCID nº 359/2025 e Lei nº 12.431/2011)"
)
SEC_CHECKLIST = "ATENDIMENTO À DOCUMENTAÇÃO DA OPERAÇÃO"
SEC_CONCLUSAO = "CONCLUSÃO"


def titulo_secao_municipio(municipio: str, uf: str) -> str:
    mun = (municipio or "___").strip()
    u = (uf or "").strip()
    if u:
        return f"{SEC_MUNICIPIO_PREFIX} — {mun.upper()} ({u})"
    return f"{SEC_MUNICIPIO_PREFIX} — {mun.upper()}"


NORMATIVA_RESUMO_RODAPE = (
    "Portaria MCID nº 359/2025 (quando iluminação pública) | Lei nº 12.431/2011 | Lei nº 14.801/2024 | "
    "Decreto nº 11.964/2024 | normas CVM"
)
