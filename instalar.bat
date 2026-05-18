@echo off
echo ============================================
echo           Maquinado - Instalacao
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Baixe em: https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b
)

echo [1/2] Python encontrado. Instalando dependencias...
echo.
python -m pip install -r requirements.txt
echo.

if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b
)

echo [2/2] Instalacao concluida com sucesso!
echo.
echo Para iniciar o script, execute: iniciar.bat
pause
