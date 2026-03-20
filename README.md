# Sistema Debêntures (MCID)

Cópia independente do automatizador de **Parecer de Mérito**, configurada para o contexto **Debêntures Incentivadas**. A lógica de APIs (IBGE, CAPAG, Atlas, SEBRAE, Planalto, portal MCID) e o fluxo de IA são os mesmos do projeto original.

**Repositório GitHub:** [github.com/victorpeborges-ADS/sistema-debentures-mcid](https://github.com/victorpeborges-ADS/sistema-debentures-mcid)

```bash
git clone https://github.com/victorpeborges-ADS/sistema-debentures-mcid.git
cd sistema-debentures-mcid/automacao
```

## Diferença em relação ao Pro-Cidades

- Interface, títulos, nomes de ficheiros exportados e porta do Streamlit (**8502**) são específicos deste sistema.
- O **Pro-Cidades** continua a usar a pasta e a porta próprias (por exemplo **8501**), podendo os dois correr em paralelo na mesma máquina.

## Como executar (Mac)

```bash
cd /caminho/para/Sistema_Debentures/automacao
source meu_ambiente/bin/activate   # ou .venv, conforme a sua instalação
streamlit run app.py --server.port=8502 --server.address=127.0.0.1
```

Ou use o duplo clique em `automacao/iniciar_mac.command` (após `instalar_mac.command`).

Abra no navegador: **http://127.0.0.1:8502**

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
