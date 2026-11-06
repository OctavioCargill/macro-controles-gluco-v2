@echo off
REM Genera el ejecutable de Glucovil y arma la carpeta para repartir (dist\Glucovil y un .zip).
REM Uso: doble clic, o desde la carpeta del repo:  empaquetado\construir_exe.bat
setlocal
cd /d "%~dp0.."

echo === 1/4 Dependencias
py -m pip install --quiet -r requirements.txt pyinstaller || goto :error

echo === 2/4 Tests
py -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo pytest no esta instalado: se saltean los tests.
) else (
    py -m pytest -q tests || goto :error
)

echo === 3/4 PyInstaller
py -m PyInstaller --noconfirm --clean MacroControlesGlucoV2.spec || goto :error

echo === 4/4 Carpeta para los usuarios
py empaquetado\armar_carpeta.py || goto :error

echo.
echo Listo. Copia la carpeta dist\Glucovil al Escritorio de cada usuario (o manda el .zip).
pause
exit /b 0

:error
echo.
echo *** Fallo el paso anterior. Revisa el mensaje de arriba. ***
pause
exit /b 1
