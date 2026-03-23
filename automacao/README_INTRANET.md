# Guia de Implantação — Debêntures Incentivadas (Intranet MCID)

---

## Qual cenário usar?

| | Cenário A — Servidor central ⭐ **Recomendado** | Cenário B — Cada máquina roda o app |
|--|--|--|
| **Como funciona** | Um único Mac Mini roda o app. Os colegas acessam pelo navegador. | Cada colega instala e roda o app localmente. |
| **Pré-requisito por máquina** | Nenhum — só navegador | Python, Ollama, 10 GB livres de RAM |
| **Modelo Ollama baixado** | Uma vez, só no servidor | Uma vez em cada máquina (~5 GB) |
| **Manutenção** | Atualiza em um único lugar | Precisa atualizar em cada máquina |
| **Ideal para** | Times com servidor ou workstation dedicada | Analistas que precisam trabalhar offline |

> **Para o time do Ministério com 6–15 pessoas e máquinas de 16 GB:** use o **Cenário A**. O Mac Mini já está rodando o Ollama — basta deixar o Streamlit ligado e compartilhar o link da rede.

---

## Cenário A — Servidor central (recomendado)

### Visão geral

```
[Mac Mini com Ollama + Streamlit]  ←→  [Navegador dos colegas na rede]
       http://172.20.7.6:8502
```

O endereço `172.20.7.6:8502` já aparece no terminal do Mac Mini quando o Streamlit está rodando (`Network URL`). Qualquer colega na mesma rede pode abrir esse endereço no Chrome/Edge.

### Passo a passo (no Mac Mini — servidor)

**1. Verifique que o Ollama está rodando**
```bash
curl http://localhost:11434/api/tags
# Deve retornar {"models":[...]} com qwen2.5:7b listado
```
Se não estiver: abra o app **Ollama** na barra de menu.

**2. Vá até a pasta do projeto**
```bash
cd ~/MCID/Sistema_Debentures/automacao
```

**3. Ative o ambiente Python**
```bash
source meu_ambiente/bin/activate   # ou o nome do seu ambiente virtual
```

**4. Suba o Streamlit escutando na rede**
```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8502
```

**5. Compartilhe o link com o time**

O terminal vai mostrar:
```
  Local URL:   http://localhost:8502
  Network URL: http://172.20.7.6:8502   ← este é o link para a equipe
```

Envie o **Network URL** por e-mail ou Teams para os colegas.

### O que o colega precisa fazer

Nada além de abrir o navegador e digitar o endereço:
```
http://172.20.7.6:8502
```
Sem instalar Python, sem instalar Ollama, sem configuração alguma.

### Deixar o app sempre disponível (opcional)

Para o Mac Mini não parar o Streamlit ao fechar o terminal, use `nohup`:
```bash
nohup streamlit run app.py --server.address=0.0.0.0 --server.port=8502 > streamlit.log 2>&1 &
echo "App rodando. PID: $!"
```

Para parar depois:
```bash
pkill -f "streamlit run app.py"
```

### Proteger com senha (opcional)

Crie um arquivo `.env` na pasta `automacao/`:
```bash
echo "APP_PASSWORD=senha-do-time" > .env
```
Depois reinicie o Streamlit. Cada colega verá uma tela de login ao acessar.

---

## Cenário B — Instalação individual em cada máquina

Use este cenário se um colega precisar rodar o app **offline** ou em uma rede diferente.

### Pré-requisitos por máquina

- macOS 12+ ou Windows 10+ ou Ubuntu 20+
- Python 3.11 ou superior → [python.org/downloads](https://www.python.org/downloads/)
- ~10 GB de RAM livres (5 GB para o modelo + 2 GB para o app)
- ~6 GB de espaço em disco (para o modelo do Ollama)
- Ollama → [ollama.com/download](https://ollama.com/download)

### Passo a passo

**1. Instalar o Ollama**

Baixe e instale em [ollama.com/download](https://ollama.com/download).  
No Mac: abra o `.dmg` e arraste para Aplicativos. O ícone aparece na barra de menu.

**2. Baixar o modelo de linguagem**
```bash
ollama pull qwen2.5:7b
# Aguarde o download de ~5 GB (só precisa fazer uma vez)
```

**3. Copiar a pasta do projeto**

Copie a pasta `automacao/` do Mac Mini para a máquina do colega via:
- Pen drive / HD externo
- Compartilhamento de rede do próprio Mac Mini
- E-mail / Teams (zipar a pasta antes)

**4. Criar ambiente Python e instalar dependências**
```bash
cd ~/Downloads/automacao   # ou onde copiou a pasta

python3 -m venv meu_ambiente
source meu_ambiente/bin/activate          # Mac/Linux
# meu_ambiente\Scripts\activate.bat       # Windows

pip install -r requirements.txt
```

**PDF “print” ou digitalizado (sem texto selecionável):** o sistema usa **PyMuPDF** para renderizar cada página, **Tesseract** (`pytesseract`) com vários modos de OCR e, se ainda faltar texto, **visão por IA** (Pixtral na **Mistral**, Groq, OpenAI, etc.). Instale o binário [Tesseract](https://github.com/tesseract-ocr/tesseract) no sistema (no macOS: `brew install tesseract tesseract-lang`). Com **Mistral** e API key configurada, o Pixtral lê páginas mesmo sem Tesseract local (envia a imagem à API).

**5. Rodar o app**
```bash
streamlit run app.py
# Abre automaticamente em http://localhost:8502
```

---

## Atualizar o app (quando houver novidades)

No **Cenário A**, basta atualizar a pasta `automacao/` no Mac Mini e reiniciar o Streamlit:
```bash
# Parar
pkill -f "streamlit run app.py"

# Atualizar (copiar novos arquivos)
# ...

# Iniciar novamente
streamlit run app.py --server.address=0.0.0.0 --server.port=8502
```

No **Cenário B**, repita o passo 3 (copiar a pasta) em cada máquina.

---

## Fontes consultadas automaticamente

| Fonte | O que busca |
|-------|-------------|
| IBGE | População, área, PIB, densidade, prefeito, bioma |
| CAPAG (Tesouro Nacional) | Nota CAPAG, indicadores de endividamento/poupança/liquidez |
| Ministério das Cidades | Vigência da IN MCID nº 18/2025 e Res. CCFGTS nº 897/2018 |
| Atlas Brasil | IDHM geral, Educação, Longevidade, Renda |

> O app precisa de **acesso à internet** para consultar essas fontes. Dentro da rede do Ministério, verifique se o proxy não bloqueia os domínios `ibge.gov.br`, `tesourotransparente.gov.br` e `atlasbrasil.org.br`.

---

## Formatos de arquivo aceitos

| Formato | Extensão |
|---------|----------|
| PDF | `.pdf` |
| Word | `.docx` |
| HTML | `.html`, `.htm` |
| Planilha | `.xlsx`, `.xls`, `.csv` |
| Georeferenciamento | `.kml`, `.kmz` |

Até **8 arquivos simultâneos** por análise. Arquivos KML/KMZ detectam automaticamente o perímetro de intervenção.

---

## Solução de problemas

| Problema | Causa provável | Solução |
|----------|---------------|---------|
| "Ollama indisponível" | Ollama não está rodando | Abra o app Ollama (ícone na barra de menu) |
| Processamento muito lento | CPU sem GPU | Normal: leva 15–30 min. Não feche o navegador. |
| Colegas não conseguem acessar | Firewall ou rede diferente | Confirme que estão na mesma rede Wi-Fi/cabeada |
| "Network URL" não aparece | Streamlit sem `--server.address=0.0.0.0` | Use o comando completo do Passo 4 |
| CAPAG não encontrado | Município não está na base | Informação não disponível; preencher manualmente |
| Erro ao extrair PDF | PDF protegido por senha | Remova a proteção antes de enviar |
| Timeout nas fontes públicas | Proxy ou lentidão da rede | Tente novamente ou verifique configuração de proxy |
