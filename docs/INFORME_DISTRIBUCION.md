# Informe de distribución y empaquetado

## 1. Dependencias utilizadas

- Python 3.14.6 (entorno asociado al proyecto)
- pandas >= 2.0
- customtkinter >= 5.2
- openpyxl >= 3.1
- pywin32 >= 306 (solo cuando se use Excel COM en Windows)
- PyInstaller para el empaquetado final del ejecutable

## 2. Archivos requeridos

La aplicación valida en runtime:

- data/044.xlsx
- data/077.xlsx
- data/090.xlsx
- data/Historico_Documentos_Controlados.xlsb
- data/Historico_Documentos_Controlados_fallback.csv
- requirements.txt
- assets/icons/placeholder.ico

## 3. Carpetas requeridas

- data/
- logs/
- config/
- icon/
- exports/
- gui/
- loaders/
- processors/
- services/
- utils/

La implementación actual crea estas carpetas automáticamente si faltan.

## 4. Recursos visuales requeridos

- assets/icons/placeholder.ico
- icon/placeholder.ico (copia creada por runtime)

## 5. Riesgos identificados

- Dependencias locales o rutas absolutas no portables.
- Archivos de datos inexistentes en una instalación limpia.
- Faltantes de permisos de escritura en logs o data.
- Versionado de la aplicación y cambios de ruta con el empaquetado de PyInstaller.

## 6. Recomendaciones para release

- Mantener la estructura de directorios junto al ejecutable.
- No hardcodear rutas personales.
- Usar rutas relativas al directorio base de la aplicación.
- Validar permisos y diagnósticos al iniciar.
- Registrar logs en logs/auditoria.log.

## 7. Validación final recomendada

- Carga automática de 044
- Carga automática de 077
- Carga automática de 090
- Procesamiento completo
- Visualización de detalles
- Retenciones y percepciones
- Historización de controlados
- Métricas
- Buscador global
- Diagnóstico
- Logs
- Validaciones de integridad

## 8. Release candidate

La versión actual queda preparada para compilar con PyInstaller manteniendo la lógica de negocio intacta.
