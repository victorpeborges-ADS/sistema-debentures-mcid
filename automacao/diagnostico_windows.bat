@echo off
chcp 65001 >nul
echo.
echo === DIAGNOSTICO DO SISTEMA ===
echo.

echo [1] Sistema operacional:
ver

echo.
echo [2] Python instalado?
python --version 2>&1
if errorlevel 1 (
    echo RESULTADO: Python NAO encontrado.
    echo Baixe em: https://www.python.org/downloads/
) else (
    echo RESULTADO: Python encontrado.
)

echo.
echo [3] pip disponivel?
pip --version 2>&1
if errorlevel 1 (
    echo RESULTADO: pip NAO encontrado.
) else (
    echo RESULTADO: pip encontrado.
)

echo.
echo [4] Ollama instalado?
ollama --version 2>&1
if errorlevel 1 (
    echo RESULTADO: Ollama NAO encontrado.
) else (
    echo RESULTADO: Ollama encontrado.
)

echo.
echo [5] Git instalado?
git --version 2>&1
if errorlevel 1 (
    echo RESULTADO: Git NAO encontrado.
) else (
    echo RESULTADO: Git encontrado.
)

echo.
echo [6] Arquivos presentes nesta pasta:
dir /b

echo.
echo === FIM DO DIAGNOSTICO ===
echo.
pause
