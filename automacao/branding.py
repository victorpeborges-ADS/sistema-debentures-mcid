"""
Identidade do Sistema Debêntures Incentivadas (MCID).

Centraliza textos da interface, nomes de exportação e porta do Streamlit.
A lógica de APIs, motor e prompts permanece nos demais módulos.
"""

APP_STREAMLIT_PORT = 8502
APP_PUBLIC_URL = f"http://127.0.0.1:{APP_STREAMLIT_PORT}"

APP_PAGE_TITLE = "Parecer — Debêntures Incentivadas"
APP_PAGE_ICON = "📊"
APP_ACCESS_TITLE = "Debêntures Incentivadas — Acesso Restrito"
APP_VERSION_CAPTION = "v1.0 — Debêntures Incentivadas / MCID"

EXPORT_DOCX_NAME = "parecer_merito_debentures.docx"
EXPORT_MD_NAME = "parecer_merito_debentures.md"
EXPORT_PORTARIA_DOCX_NAME = "portaria_debentures.docx"
EXPORT_PORTARIA_MD_NAME = "portaria_debentures.md"

# Mensagens de progresso (UI)
PROGRESS_LEGIS_MCID = "Verificando legislação no portal MCID..."

# Métricas / subheaders
METRICA_LEGIS_MCID = "Legislação MCID (portal)"
SUBHEADER_LEGIS_MCID = "Legislação MCID (portal gov.br)"

# Texto da aba rápida (markdown simples para st.info)
RAPIDO_HEADER = "Submissão para análise — Debêntures Incentivadas"

PORTARIA_RAPIDO_HEADER = "Submissão para análise — Portarias (Debêntures Incentivadas)"

def texto_info_submissao_rapida(tipos_label: str) -> str:
    """Bloco explicativo da submissão rápida; mantém as mesmas fontes de dados do motor."""
    return (
        f"Envie **até 8 arquivos** da documentação da operação ({tipos_label}) e selecione o município. "
        "O sistema consolida os documentos, executa as análises com as seguintes fontes públicas: "
        "**IBGE** (população, área, PIB) · "
        "**Tesouro Nacional — CAPAG** (capacidade de pagamento) · "
        "**Atlas Brasil / PNUD** (IDHM) · "
        "**SEBRAE — Observatório Setorial Territorial** (empresas, emprego) · "
        "**Ministério das Cidades** (página de legislação de referência no MCID) · "
        "**Planalto.gov.br** (Decreto nº 12.210/2024 · Lei nº 13.089/2015 · Lei nº 10.257/2001) "
        "— e gera o parecer. "
        "Arquivos KML/KMZ são reconhecidos automaticamente como o perímetro de intervenção, quando aplicável. "
        "Imagens (.jpg/.png/.tiff) são processadas por **OCR** (documentos escaneados) "
        "e/ou **visão por IA** (fotos, mapas, plantas técnicas)."
    )


def texto_info_submissao_portaria(tipos_label: str) -> str:
    """Texto da submissão rápida no fluxo de portarias (mesmas fontes públicas)."""
    return (
        texto_info_submissao_rapida(tipos_label).replace("gera o parecer", "gera a portaria")
        .replace("o parecer", "a portaria")
    )
