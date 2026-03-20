#!/bin/bash
# Iniciador — Sistema Debêntures Incentivadas MCID
# Duplo clique para abrir o app no navegador.
# Porta 8502 — não conflita com Pro-Cidades (8501).

cd "$(dirname "$0")"

clear
echo ""
echo "============================================================"
echo "  DEBÊNTURES INCENTIVADAS — MCID"
echo "============================================================"
echo ""

# ---- Verificar ambiente virtual ----
if [ ! -f "meu_ambiente/bin/activate" ]; then
    echo "[ERRO] Ambiente virtual não encontrado."
    echo "Execute instalar_mac.command primeiro."
    echo ""
    read -p "Pressione Enter para sair."
    exit 1
fi

# ---- Verificar/iniciar Ollama ----
echo "Verificando Ollama..."
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "Ollama não está respondendo. Tentando iniciar..."
    open -a Ollama 2>/dev/null || true
    echo "Aguardando Ollama iniciar (15 segundos)..."
    sleep 15
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo ""
        echo "[ERRO] Ollama ainda não está disponível."
        echo "Abra o Ollama manualmente (ícone na barra de menu) e tente novamente."
        echo ""
        read -p "Pressione Enter para sair."
        exit 1
    fi
fi
echo "[OK] Ollama está rodando."

# ---- Ativar ambiente e iniciar app ----
echo ""
echo "Iniciando aplicação..."
source meu_ambiente/bin/activate

# Inicia Streamlit em background
streamlit run app.py \
    --server.port=8502 \
    --server.headless=true \
    --server.address=127.0.0.1 &
STREAMLIT_PID=$!

# Aguarda e abre navegador
echo "Aguardando o app iniciar..."
sleep 4
open http://localhost:8502

echo ""
echo "============================================================"
echo "  App aberto em: http://localhost:8502"
echo "============================================================"
echo ""
echo "Não feche esta janela enquanto estiver usando o sistema."
echo "Para encerrar: feche esta janela ou pressione Ctrl+C."
echo ""

# Aguarda o Streamlit (mantém terminal aberto)
wait $STREAMLIT_PID
