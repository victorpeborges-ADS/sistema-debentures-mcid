@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Instalacao - Debentures Incentivadas MCID

echo.
echo ============================================================
echo   INSTALACAO - DEBENTURES INCENTIVADAS / MCID
echo   Ministerio das Cidades
echo ============================================================
echo.

:: === PASSO 1: Python ===
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 goto SEM_PYTHON
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VERSION=%%v
echo [OK] Python !PY_VERSION!
goto PASSO2

:SEM_PYTHON
echo.
echo [ERRO] Python nao encontrado.
echo.
echo  Instale em: https://www.python.org/downloads/
echo  OBRIGATORIO: marque Add Python to PATH na instalacao.
echo  Reinicie o computador e execute este script novamente.
echo.
pause
exit /b 1

:: === PASSO 2: Ollama ===
:PASSO2
echo.
echo [2/5] Verificando Ollama...
ollama --version >nul 2>&1
if not errorlevel 1 goto OLLAMA_OK

echo  Ollama nao encontrado. Baixando instalador automaticamente...
set OLLAMA_INST=%TEMP%\OllamaSetup.exe
powershell -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile '%TEMP%\OllamaSetup.exe'" 2>nul
if not exist "%TEMP%\OllamaSetup.exe" goto OLLAMA_FALHOU
echo  Download concluido. Abrindo instalador do Ollama...
echo  Siga as instrucoes na tela e clique em Install.
start /wait "" "%TEMP%\OllamaSetup.exe"
timeout /t 5 /nobreak >nul
ollama --version >nul 2>&1
if errorlevel 1 goto OLLAMA_FALHOU
echo [OK] Ollama instalado.
goto PASSO3

:OLLAMA_FALHOU
echo [ERRO] Nao foi possivel instalar o Ollama automaticamente.
echo  Instale manualmente em: https://ollama.com/download
echo  Reinicie o computador e execute este script novamente.
pause
exit /b 1

:OLLAMA_OK
for /f "tokens=*" %%v in ('ollama --version 2^>^&1') do set OL_VER=%%v
echo [OK] !OL_VER!

:: === PASSO 3: Ambiente virtual ===
:PASSO3
echo.
echo [3/5] Criando ambiente Python...
if exist "meu_ambiente\Scripts\activate.bat" goto VENV_OK
python -m venv meu_ambiente
if errorlevel 1 goto VENV_FALHOU
echo [OK] Ambiente criado.
goto PASSO4

:VENV_FALHOU
echo [ERRO] Falha ao criar ambiente virtual.
pause
exit /b 1

:VENV_OK
echo [OK] Ambiente ja existe.

:: === PASSO 4: Dependencias ===
:PASSO4
echo.
echo [4/5] Instalando dependencias Python (3 a 5 minutos)...
call meu_ambiente\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto DEPS_FALHOU
echo [OK] Dependencias instaladas.
goto PASSO5

:DEPS_FALHOU
echo [ERRO] Falha ao instalar dependencias. Verifique a conexao com a internet.
pause
exit /b 1

:: === PASSO 5: Modelo Ollama ===
:PASSO5
echo.
echo [5/5] Baixando modelo de IA qwen2.5:7b (aprox. 5 GB)...
echo  Tempo estimado: 10 a 30 minutos. Nao feche esta janela.
echo.
start /b "" ollama serve 2>nul
timeout /t 4 /nobreak >nul
ollama pull qwen2.5:7b
if errorlevel 1 goto MODELO_AVISO
echo [OK] Modelo qwen2.5:7b pronto.
goto CONFIG

:MODELO_AVISO
echo [AVISO] Nao foi possivel baixar o modelo agora.
echo  Execute depois pelo Prompt de Comando: ollama pull qwen2.5:7b

:: === Credenciais ===
:CONFIG
echo.
if exist ".streamlit\secrets.toml" goto CONFIG_OK
if not exist ".streamlit\secrets.toml.example" goto CONFIG_OK
copy ".streamlit\secrets.toml.example" ".streamlit\secrets.toml" >nul
echo [OK] Arquivo .streamlit\secrets.toml criado.
echo  ATENCAO: Abra esse arquivo no Bloco de Notas e preencha a senha.
goto ATALHO

:CONFIG_OK
echo [OK] Credenciais ja configuradas.

:: === Atalho na Area de Trabalho ===
:ATALHO
echo.
set SHORTCUT=%USERPROFILE%\Desktop\Debentures Incentivadas MCID.lnk
powershell -Command "$ws=New-Object -ComObject WScript.Shell; $sc=$ws.CreateShortcut('%SHORTCUT%'); $sc.TargetPath='%~dp0iniciar_windows.bat'; $sc.WorkingDirectory='%~dp0'; $sc.Save()"
if exist "%SHORTCUT%" echo [OK] Atalho criado na Area de Trabalho.

:: === GitHub (opcional) ===
echo.
git --version >nul 2>&1
if errorlevel 1 goto SEM_GIT
pushd "%~dp0\..\.."
git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 goto GIT_OK
echo [INFO] Para vincular ao GitHub execute no CMD:
echo   cd /d "%~dp0\..\.."
echo   git remote add origin https://github.com/victorpeborges-ADS/MCID.git
echo   git fetch origin main
popd
goto FIM

:GIT_OK
echo [OK] Repositorio GitHub vinculado. Use atualizar_windows.bat para novidades.
popd
goto FIM

:SEM_GIT
echo [INFO] Git nao instalado. Download em: https://git-scm.com/download/win

:: === FIM ===
:FIM
echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo  Use o atalho na Area de Trabalho ou execute iniciar_windows.bat
echo.
echo  LEMBRE-SE: abra .streamlit\secrets.toml no Bloco de Notas
echo  e preencha a senha da equipe.
echo.
pause
endlocal
