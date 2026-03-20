"""
Gera um arquivo diagnostico.bat simples para testar o ambiente Windows.
Execute este script no Mac e copie o diagnostico.bat para o Windows.
"""

conteudo = """\
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
"""

with open('diagnostico_windows.bat', 'w', encoding='cp1252', newline='\r\n') as f:
    f.write(conteudo)

print("diagnostico_windows.bat criado com sucesso (CP1252 + CRLF).")
print("Copie este arquivo para o Windows e execute como Administrador.")
