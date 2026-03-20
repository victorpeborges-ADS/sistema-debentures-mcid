#!/bin/bash
# Instalação — Sistema Debêntures Incentivadas MCID
# Duplo clique para executar no Mac.

# Vai para a pasta do script (necessário para duplo clique no Finder)
cd "$(dirname "$0")"

clear
echo ""
echo "============================================================"
echo "  INSTALAÇÃO — DEBÊNTURES INCENTIVADAS / MCID"
echo "============================================================"
echo ""

# ---- Verificar Python ----
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python 3 não encontrado."
    echo ""
    echo "Instale o Python 3.11 ou superior em:"
    echo "  https://www.python.org/downloads/"
    echo ""
    read -p "Pressione Enter para sair."
    exit 1
fi

PY_VERSION=$(python3 --version 2>&1)
echo "[OK] $PY_VERSION encontrado."

# ---- Verificar Ollama ----
if ! command -v ollama &>/dev/null; then
    echo ""
    echo "[AVISO] Ollama não encontrado."
    echo ""
    echo "Baixe e instale o Ollama em:"
    echo "  https://ollama.com/download"
    echo ""
    echo "Após instalar, abra o Ollama (aparecerá na barra de menu)"
    echo "e execute este script novamente."
    echo ""
    read -p "Pressione Enter para sair."
    exit 1
fi
echo "[OK] Ollama encontrado."

# ---- Criar ambiente virtual ----
echo ""
echo "[1/4] Criando ambiente virtual Python..."
if [ -d "meu_ambiente" ]; then
    echo "      Ambiente já existe — pulando criação."
else
    python3 -m venv meu_ambiente
    echo "      Ambiente criado."
fi

# ---- Instalar dependências ----
echo ""
echo "[2/4] Instalando dependências (pode levar alguns minutos)..."
source meu_ambiente/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "      Dependências instaladas."

# ---- Baixar modelo Ollama ----
echo ""
echo "[3/4] Verificando modelo de linguagem (qwen2.5:7b)..."
echo "      Esta etapa pode levar 10-20 min no primeiro download (~5 GB)."
ollama pull qwen2.5:7b
echo "      Modelo pronto."

# ---- Criar app lançador no Dock/Desktop ----
echo ""
echo "[4/4] Criando lançador no Desktop..."

LAUNCHER="$HOME/Desktop/Debêntures Incentivadas MCID.command"
SCRIPT_DIR="$(pwd)"

cat > "$LAUNCHER" << LAUNCHER_CONTENT
#!/bin/bash
cd "$SCRIPT_DIR"
source meu_ambiente/bin/activate
exec bash iniciar_mac.command
LAUNCHER_CONTENT

chmod +x "$LAUNCHER"

if [ -f "$LAUNCHER" ]; then
    echo "      Lançador criado no Desktop."
else
    echo "      [AVISO] Não foi possível criar lançador. Use iniciar_mac.command diretamente."
fi

# ---- Concluído ----
echo ""
echo "============================================================"
echo "  INSTALAÇÃO CONCLUÍDA!"
echo "============================================================"
echo ""
echo "Para usar o sistema:"
echo "  - Clique duas vezes em 'Debêntures Incentivadas MCID' no Desktop"
echo "  - OU execute iniciar_mac.command nesta pasta"
echo ""
echo "O app usa a porta 8502 (Pro-Cidades usa 8501, se estiver instalado)."
echo ""
echo "Requisito: o Ollama precisa estar aberto (ícone na barra de"
echo "menu do Mac) antes de usar o app."
echo ""
read -p "Pressione Enter para sair."
