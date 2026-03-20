#!/bin/sh
# Deploy intranet — APP_PASSWORD e OLLAMA_HOST via variáveis de ambiente
exec streamlit run app.py --server.address=0.0.0.0 --server.port=8502
