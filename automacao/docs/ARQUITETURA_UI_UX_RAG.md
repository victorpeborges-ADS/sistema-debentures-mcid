# Arquitetura — UI/UX e assistente RAG

Este documento fixa a **nomenclatura** e a **separação de responsabilidades** para evitar ambiguidade entre interface, persistência e prompts de LLM.

## Camadas

| Camada | O que é | O que não é |
|--------|---------|-------------|
| **Repositório de Pareceres** | Leitura: listagem, busca, filtros, pré-visualização de pareceres já gravados (ficheiros em `biblioteca/pareceres_validados/`). | Não é “aba de banco de dados”: o utilizador não acede a SQL; acede a um **repositório de ficheiros** com semântica de arquivo. |
| **Gerador de Pareceres** | Escrita e orquestração: upload de proposta, extração, crivo, geração do parecer, exportação, envio para o repositório, feedback. | |
| **Repositório de Portarias** | Leitura: histórico de portarias (`portarias/historico/`). | Idem: repositório, não “tabela exposta ao utilizador”. |
| **Gerador de Portarias** | Escrita: redação assistida (evolução futura); mesmo padrão de separação. | |

Persistência atual: **ficheiros + JSONL** (feedback). Evolução possível: SQLite/Postgres **sem** mudar os nomes das áreas na UI (“repositório” mantém-se).

## Assistente de documento (RAG restrito)

- **Contexto:** apenas o texto do documento **carregado ou gerado** na área do gerador (parecer em Markdown ou texto consolidado da proposta).
- **System prompt:** obriga a:
  - não inventar conteúdo fora do contexto;
  - indicar ausência explícita quando não houver suporte no texto;
  - **citar** com formato fixo: documento, localização (página/seção se existir no texto), trecho literal entre aspas.

Implementação: `assistente_rag.py` + painel de chat na coluna lateral dos **geradores**.

## Identidade visual

Tema **escuro** orientado a leitura prolongada: ver `.streamlit/config.toml` (`base = "dark"`).
