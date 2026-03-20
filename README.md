# Sistema Debêntures (MCID)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![CI](https://github.com/victorpeborges-ADS/sistema-debentures-mcid/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/victorpeborges-ADS/sistema-debentures-mcid/actions/workflows/ci.yml)

Cópia independente do automatizador de **Parecer de Mérito**, configurada para o contexto **Debêntures Incentivadas**. A lógica de APIs (IBGE, CAPAG, Atlas, SEBRAE, Planalto, portal MCID) e o fluxo de IA são os mesmos do projeto original.

> **Aviso:** ferramenta de apoio à análise. O conteúdo gerado deve ser **revisto** por analista competente; não substitui parecer jurídico ou decisão administrativa oficial.

**Repositório GitHub:** [github.com/victorpeborges-ADS/sistema-debentures-mcid](https://github.com/victorpeborges-ADS/sistema-debentures-mcid)

```bash
git clone https://github.com/victorpeborges-ADS/sistema-debentures-mcid.git
cd sistema-debentures-mcid/automacao
```

## Navegação (repositório vs gerador)

O sistema separa **leitura** (repositórios com filtros e pré-visualização) de **escrita** (geradores com assistente RAG restrito ao documento em contexto). Não há “aba de base de dados” para o utilizador final — apenas repositórios de ficheiros. Detalhes: `automacao/docs/ARQUITETURA_UI_UX_RAG.md`.

## Diferença em relação ao Pro-Cidades

- Interface, títulos, nomes de ficheiros exportados e porta do Streamlit (**8502**) são específicos deste sistema.
- O **Pro-Cidades** continua a usar a pasta e a porta próprias (por exemplo **8501**), podendo os dois correr em paralelo na mesma máquina.
- Tema **escuro** por defeito (produtividade / leitura prolongada), configurável em `automacao/.streamlit/config.toml`.

## Como executar (terminal)

> **Importante:** `/caminho/para/...` nos exemplos abaixo é **só um marcador**. No Mac/Linux use o caminho **real** até à pasta `automacao` (ex.: `cd ~/MCID/Sistema_Debentures/automacao`). O ficheiro `requirements.txt` e o `app.py` estão **dentro** de `automacao/`, não na pasta pai `Sistema_Debentures`.

Na **primeira vez**, crie o ambiente e instale dependências **já dentro de `automacao`**:

```bash
cd ~/MCID/Sistema_Debentures/automacao    # ajuste ao seu disco (ou: cd sistema-debentures-mcid/automacao)
python3 -m venv meu_ambiente              # ou: python3 -m venv .venv
source meu_ambiente/bin/activate          # Windows: meu_ambiente\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Sempre que for usar** o sistema (com o venv ativo):

```bash
cd ~/MCID/Sistema_Debentures/automacao
source meu_ambiente/bin/activate
streamlit run app.py --server.port=8502 --server.address=127.0.0.1
```

Abra no navegador: **http://127.0.0.1:8502**

Opcional (PostgreSQL): defina `DATABASE_URL` no ambiente ou em `automacao/.env` (ver `.env.example`).

**Se aparecer `No module named 'sqlalchemy'`** depois de `pip install -r requirements.txt`, o executável `pip` pode estar a apontar para outro projeto. Reinstale com o Python deste ambiente:

```bash
cd ~/MCID/Sistema_Debentures/automacao   # ajuste o caminho
source meu_ambiente/bin/activate
python -m pip install -r requirements.txt
```

Ou recrie o venv: `rm -rf meu_ambiente` e volte a correr `instalar_mac.command`.

### macOS (atalhos)

Duplo clique em `automacao/instalar_mac.command` (primeira vez), depois `iniciar_mac.command` ou os comandos acima.

## Instalação em outras máquinas

Sim. O procedimento é **copiar a pasta `Sistema_Debentures`** (ou só `Sistema_Debentures/automacao`) e executar o instalador do sistema operativo.

| Plataforma | O que fazer |
|------------|-------------|
| **macOS** | Duplo clique em `automacao/instalar_mac.command` (primeira vez). Depois: `iniciar_mac.command` ou o comando `streamlit` abaixo. |
| **Windows** | Duplo clique em `automacao/instalar_windows.bat` (primeira vez). Depois: atalho na área de trabalho ou `iniciar_windows.bat`. |
| **Docker / servidor** | Ver `automacao/README_INTRANET.md` e `automacao/docker-compose.yml` (app na porta **8502**). |

Requisitos típicos: Python 3.11+, ambiente virtual criado pelo script, dependências em `requirements.txt`, e opcionalmente Ollama + modelo `qwen2.5:7b` para IA local (ou usar Groq/Mistral/OpenAI na barra lateral).

> **Git:** `atualizar_windows.bat` só funciona depois que a pasta `Sistema_Debentures` estiver versionada no repositório Git (commit + push). Até lá, use cópia por pen drive/rede.

## Documentação adicional

- `automacao/COMO_INSTALAR_WINDOWS.md` — instalação detalhada em Windows
- `automacao/README_INTRANET.md` — implantação em intranet / Docker
- `SECURITY.md` — reporte de vulnerabilidades e boas práticas

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
