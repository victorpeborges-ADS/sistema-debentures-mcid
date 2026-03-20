@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Debentures Incentivadas - MCID

echo.
echo ============================================================
echo   DEBENTURES INCENTIVADAS - MCID  (porta 8502)
echo ============================================================
echo.

if not exist "meu_ambiente\Scripts\activate.bat" goto SEM_INSTALL
goto VERIFICA_OLLAMA

:SEM_INSTALL
echo [ERRO] Sistema nao instalado.
echo  Execute instalar_windows.bat primeiro.
echo.
pause
exit /b 1

:VERIFICA_OLLAMA
echo Verificando Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if not errorlevel 1 goto OLLAMA_PRONTO
echo  Iniciando Ollama...
set OLLAMA_APP=%LOCALAPPDATA%\Programs\Ollama\ollama app.exe
if exist "!OLLAMA_APP!" goto INICIA_OLLAMA_APP
start /b "" ollama serve 2>nul
goto AGUARDA_OLLAMA

:INICIA_OLLAMA_APP
start "" "!OLLAMA_APP!"

:AGUARDA_OLLAMA
set /a TENTATIVAS=0
:LOOP_OLLAMA
timeout /t 2 /nobreak >nul
curl -s http://localhost:11434/api/tags >nul 2>&1
if not errorlevel 1 goto OLLAMA_PRONTO
set /a TENTATIVAS+=1
if !TENTATIVAS! lss 10 goto LOOP_OLLAMA
echo [AVISO] Ollama nao respondeu. Use Groq ou Mistral AI.
goto INICIA_APP

:OLLAMA_PRONTO
echo [OK] Ollama pronto.

:INICIA_APP
netstat -ano 2>nul | find "8502" | find "LISTENING" >nul 2>&1
if not errorlevel 1 goto JA_RODANDO

call meu_ambiente\Scripts\activate.bat
echo.
echo Iniciando sistema...
start /b streamlit run app.py --server.port=8502 --server.headless=true --server.address=localhost
timeout /t 5 /nobreak >nul
start "" http://localhost:8502
echo.
echo ============================================================
echo   Sistema disponivel em: http://localhost:8502
echo ============================================================
echo.
echo  NAO feche esta janela enquanto estiver usando.
echo.
streamlit run app.py --server.port=8502 --server.headless=true --server.address=localhost
goto FIM

:JA_RODANDO
echo  Sistema ja esta rodando. Abrindo navegador...
start "" http://localhost:8502

:FIM
endlocal
