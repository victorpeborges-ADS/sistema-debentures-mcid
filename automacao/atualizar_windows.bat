@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Atualizar Sistema - Debentures Incentivadas MCID

echo.
echo ============================================================
echo   ATUALIZAR SISTEMA - DEBENTURES INCENTIVADAS / MCID
echo ============================================================
echo.

git --version >nul 2>&1
if not errorlevel 1 goto TEM_GIT
echo [ERRO] Git nao instalado.
echo  Instale em: https://git-scm.com/download/win
pause
exit /b 1

:TEM_GIT
pushd "%~dp0\..\.."
git rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 goto TEM_REPO
echo [ERRO] Pasta nao vinculada ao GitHub.
echo  Execute instalar_windows.bat e vincule ao repositorio.
popd
pause
exit /b 1

:TEM_REPO
popd

:: Backup das credenciais
if exist ".streamlit\secrets.toml" copy ".streamlit\secrets.toml" ".streamlit\secrets.toml.bak" >nul

pushd "%~dp0\..\.."
for /f "tokens=*" %%i in ('git rev-parse --short HEAD 2^>nul') do set VERSAO_LOCAL=%%i

git fetch origin main >nul 2>&1
if not errorlevel 1 goto FETCH_OK
echo [ERRO] Sem conexao com o GitHub.
popd
pause
exit /b 1

:FETCH_OK
for /f "tokens=*" %%i in ('git rev-parse --short origin/main 2^>nul') do set VERSAO_REMOTA=%%i

if "!VERSAO_LOCAL!"=="!VERSAO_REMOTA!" goto JA_ATUALIZADO

echo  Nova versao disponivel: !VERSAO_LOCAL! para !VERSAO_REMOTA!
echo.
git log --oneline !VERSAO_LOCAL!..origin/main -- Sistema_Debentures/automacao/ 2>nul
echo.
set /p CONFIRMAR=Instalar atualizacao agora? (S/N): 
if /i not "!CONFIRMAR!"=="S" goto CANCELADO

git checkout origin/main -- Sistema_Debentures/automacao/app.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/branding.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/motor.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/biblioteca.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/llm_client.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/fontes_publicas.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/md_para_docx.py 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/requirements.txt 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/iniciar_windows.bat 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/instalar_windows.bat 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/atualizar_windows.bat 2>nul
git checkout origin/main -- Sistema_Debentures/automacao/COMO_INSTALAR_WINDOWS.md 2>nul
git checkout origin/main -- "Sistema_Debentures/automacao/biblioteca/pareceres_validados/" 2>nul
git merge --ff-only origin/main >nul 2>&1
echo [OK] Sistema atualizado para versao !VERSAO_REMOTA!
goto RESTAURA

:JA_ATUALIZADO
echo  Sistema ja esta na versao mais recente: !VERSAO_LOCAL!
goto RESTAURA

:CANCELADO
echo  Atualizacao cancelada.

:RESTAURA
popd
cd /d "%~dp0"
if exist ".streamlit\secrets.toml.bak" copy ".streamlit\secrets.toml.bak" ".streamlit\secrets.toml" >nul
if exist ".streamlit\secrets.toml.bak" del ".streamlit\secrets.toml.bak" >nul

if not exist "meu_ambiente\Scripts\activate.bat" goto FIM
echo.
echo  Verificando dependencias Python...
call meu_ambiente\Scripts\activate.bat
python -m pip install --quiet -r requirements.txt
echo [OK] Dependencias verificadas.

:FIM
echo.
echo ============================================================
echo   PRONTO! Inicie com iniciar_windows.bat
echo ============================================================
echo.
pause
endlocal
