Macro Controles Gluco V2
=======================

Producto: Macro Controles Gluco V2
Versión: 2.0.0
Descripción: Herramienta de control y validación de liquidaciones.

Estructura recomendada de distribución:

Macro Controles Gluco V2/
├── MacroControlesGlucoV2.exe
├── data/
├── logs/
├── config/
├── icon/
├── README.txt
└── app_settings.json

Requisitos de ejecución:
- Windows 10 o Windows 11
- Permisos de lectura/escritura para la carpeta de instalación
- Carpetas data, logs y config creadas automáticamente si faltan

Arquivos requeridos por la aplicación:
- data/044.xlsx
- data/077.xlsx
- data/090.xlsx
- data/Historico_Documentos_Controlados.xlsb
- data/Historico_Documentos_Controlados_fallback.csv

Si faltan archivos o carpetas, la aplicación mostrará un diagnóstico y no permitirá continuar con el procesamiento.

Logs:
- Se guardan automáticamente en logs/auditoria.log
- Se registran inicio, procesamiento, errores y diagnóstico.

Generación de ejecutable:
- pyinstaller MacroControlesGlucoV2.spec --noconfirm

Para nuevas versiones:
- actualizar APP_VERSION en services/auditoria.py
- actualizar el archivo de versión usado por PyInstaller si se emplea un recurso de Windows
- reconstruir el ejecutable
