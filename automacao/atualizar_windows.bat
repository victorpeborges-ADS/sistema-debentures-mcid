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

:: Raiz do Git: clone standalone (repo/automacao) ou monorepo (MCID/Sistema_Debentures/automacao)

set "HERE=%~dp0"

cd /d "%HERE%.."

git rev-parse --is-inside-work-tree >nul 2>&1

if not errorlevel 1 if exist "automacao\app.py" goto TEM_REPO

cd /d "%HERE%..\.."

git rev-parse --is-inside-work-tree >nul 2>&1

if not errorlevel 1 if exist "Sistema_Debentures\automacao\app.py" goto TEM_REPO

echo [ERRO] Pasta nao vinculada ao Git ou estrutura desconhecida.

echo  Esperado: clone com pasta automacao/ na raiz OU monorepo MCID com Sistema_Debentures/automacao/

pause

exit /b 1



:TEM_REPO

:: Backup das credenciais Streamlit

if exist "%HERE%.streamlit\secrets.toml" copy "%HERE%.streamlit\secrets.toml" "%HERE%.streamlit\secrets.toml.bak" >nul



for /f "tokens=*" %%i in ('git rev-parse --short HEAD 2^>nul') do set VERSAO_LOCAL=%%i



git fetch origin main >nul 2>&1

if not errorlevel 1 goto FETCH_OK

echo [ERRO] Sem conexao com o GitHub ou remote 'origin/main' indisponivel.

pause

exit /b 1



:FETCH_OK

for /f "tokens=*" %%i in ('git rev-parse --short origin/main 2^>nul') do set VERSAO_REMOTA=%%i



if "!VERSAO_LOCAL!"=="!VERSAO_REMOTA!" goto JA_ATUALIZADO



echo  Nova versao disponivel: !VERSAO_LOCAL! -^> !VERSAO_REMOTA!

echo.

git log --oneline !VERSAO_LOCAL!..origin/main -- . 2>nul

echo.

set /p CONFIRMAR=Instalar atualizacao agora? (S/N): 

if /i not "!CONFIRMAR!"=="S" goto CANCELADO



git merge --ff-only origin/main

if errorlevel 1 (

  echo.

  echo  Primeira tentativa falhou — frequentemente sao ficheiros locais NAO rastreados

  echo  com o mesmo nome que o GitHub vai trazer. A guardar em stash e a tentar de novo...

  echo.

  git stash push -u -m "debentures-pre-update" 2>nul

  git merge --ff-only origin/main

  if errorlevel 1 (

    echo.

    echo [ERRO] Merge fast-forward falhou. Possiveis alteracoes locais ou conflitos.

    echo  Veja: git status

    echo.

    echo  Solucao manual ^(na pasta raiz do projeto, no Git Bash ou CMD^):

    echo    1^) Apagar ou renomear os ficheiros que o Git diz que bloqueiam, OU

    echo    2^) git stash push -u -m backup

    echo       git merge --ff-only origin/main

    echo.

    pause

    exit /b 1

  )

  echo.

  echo [INFO] Copias antigas podem estar em stash — ver: git stash list

  echo       Se nao precisar da copia: git stash drop

  echo.

)

echo [OK] Repositorio atualizado para !VERSAO_REMOTA!

goto RESTAURA



:JA_ATUALIZADO

echo  Sistema ja esta na versao mais recente: !VERSAO_LOCAL!

goto RESTAURA



:CANCELADO

echo  Atualizacao cancelada.



:RESTAURA

cd /d "%HERE%"

if exist ".streamlit\secrets.toml.bak" copy ".streamlit\secrets.toml.bak" ".streamlit\secrets.toml" >nul

if exist ".streamlit\secrets.toml.bak" del ".streamlit\secrets.toml.bak" >nul



if not exist "meu_ambiente\Scripts\activate.bat" goto FIM

echo.

echo  Instalando dependencias Python (requirements.txt)...

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

