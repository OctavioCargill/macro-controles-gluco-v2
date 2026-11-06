r"""Arma la carpeta para repartir a los usuarios a partir de lo que generó PyInstaller.

Lo llama empaquetado\construir_exe.bat después de PyInstaller. Resultado:

    dist\Glucovil\                     <- esta carpeta se copia al Escritorio de cada usuario
        MacroControlesGlucoV2.exe
        _internal\                     (lo necesita el .exe, no tocar)
        data\                          los usuarios guardan acá los reportes (044, 090, 077, 020, 067)
            Historico_Documentos_Controlados.xlsx   (vacío, con títulos)
            Historico_Documentos_Controlados_fallback.csv
            historico_pagados.xlsx                  (vacío, con títulos)
            LEEME.txt
        config\  logs\
        LEEME.txt
    dist\Glucovil_<versión>_<fecha>.zip  <- lo mismo comprimido, para mandar por mail o Teams
"""

import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ORIGEN = REPO / "dist" / "MacroControlesGlucoV2"
DESTINO = REPO / "dist" / "Glucovil"

LEEME = """GLUCOVIL - Proceso de liquidaciones (versión {version})
=====================================================

CÓMO SE USA
1. Copiá esta carpeta completa (Glucovil) al Escritorio. No muevas el .exe fuera de la carpeta:
   necesita la carpeta _internal que está al lado.
2. Guardá los reportes en la carpeta data, pisando los del día anterior:
   - Controlar:  044, 090 y 077  (el nombre tiene que empezar con 044, 090 o 077)
   - Netting:    usa el Histórico de controlados, el 077 y el 090
   - Liberación: 020 y 067; para limpiar pagadas, el 020 nuevo con "limpiar" en el nombre
3. Abrí MacroControlesGlucoV2.exe.

En la app, el botón "? Ayuda" (arriba a la derecha) y la tarjeta "Asistente" del menú responden las dudas de uso.

SI TRABAJAN DOS PERSONAS (una controla y libera, otra hace el netting)
Las dos apps tienen que usar la misma carpeta de datos en la red. La primera vez, en cada PC:
menú principal -> botón "Datos: carpeta local" -> "Usar una carpeta compartida..." -> elegir la carpeta de red.
La app se cierra; al abrirla de nuevo ya trabaja sobre la carpeta compartida (en ese caso, la carpeta data de
acá queda sin uso). El día que dejan la macro, desde esa misma ventana se traen sus históricos .xlsb.

NO BORRES NI PISES ESTOS ARCHIVOS DE data (son la memoria del proceso):
   Historico_Documentos_Controlados.xlsx   lo controlado (lo escribe Controlar)
   historico_pagados.xlsx                  lo pagado (lo escribe Liberación)
   Netting_Propuestos.xlsx                 lo propuesto en cada netting
Si ya venían usando un Histórico de controlados o de pagados, reemplazá los vacíos que trae esta carpeta
por los suyos ANTES del primer uso.

ACTUALIZAR A UNA VERSIÓN NUEVA
Reemplazá solo MacroControlesGlucoV2.exe y la carpeta _internal. No toques data ni config.

Si Windows muestra "Windows protegió su PC", elegí "Más información" -> "Ejecutar de todos modos"
(el ejecutable no está firmado digitalmente).
"""

LEEME_DATA = """Guardá acá los reportes que bajás de SAP/E1. La app toma solo el más nuevo de cada uno.

  044_...  090_...  077_...    Controlar
  020_...  067_...             Liberación (Controlar pagos)
  020_LIMPIAR_...              Liberación (Limpiar pagadas)

Archivos que escribe la app (no borrar):
  Historico_Documentos_Controlados.xlsx, historico_pagados.xlsx, Netting_Propuestos.xlsx
Salidas: Propuestas_Netting.xlsx (Netting) y Netting_liberar.xlsx (Output E1).
Antes de cambiar los históricos la app guarda copias "_backup_fecha_hora".
"""


def _libro(ruta, hoja, titulos):
    from openpyxl import Workbook

    libro = Workbook()
    libro.active.title = hoja
    libro.active.append(titulos)
    libro.save(ruta)


def main():
    from services.auditoria import APP_VERSION

    if not (ORIGEN / "MacroControlesGlucoV2.exe").exists():
        print(f"No se encontró {ORIGEN / 'MacroControlesGlucoV2.exe'}. Primero corré PyInstaller.")
        return 1
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(ORIGEN, DESTINO)
    # Por si quedó algo de un empaquetado viejo: nunca repartir reportes ni históricos de quien genera el .exe
    for sobrante in ("data", "logs", "config", "_internal/data", "_internal/logs"):
        if (DESTINO / sobrante).exists():
            shutil.rmtree(DESTINO / sobrante)
    data = DESTINO / "data"
    for carpeta in (data, DESTINO / "logs", DESTINO / "config"):
        carpeta.mkdir(parents=True)
    shutil.copy2(REPO / "config" / "app_settings.json", DESTINO / "config" / "app_settings.json")

    # Históricos vacíos: CONTROLAR necesita que existan; las columnas se agregan solas al primer uso.
    _libro(data / "Historico_Documentos_Controlados.xlsx", "Historico_Controlados", ["id_largo", "id_corto"])
    (data / "Historico_Documentos_Controlados_fallback.csv").write_text("id_largo,id_corto\n", encoding="utf-8")
    _libro(data / "historico_pagados.xlsx", "Historico_Pagados",
           ["Numero Doc", "Tipo Doc", "id_largo", "id_corto", "Fecha Netting", "Fecha Acreditación", "ID pago E1"])
    (data / "LEEME.txt").write_text(LEEME_DATA, encoding="utf-8")
    (DESTINO / "LEEME.txt").write_text(LEEME.format(version=APP_VERSION), encoding="utf-8")

    archivo_zip = DESTINO.parent / f"Glucovil_{APP_VERSION}_{date.today():%Y%m%d}.zip"
    with zipfile.ZipFile(archivo_zip, "w", zipfile.ZIP_DEFLATED) as zz:
        for archivo in DESTINO.rglob("*"):
            zz.write(archivo, Path("Glucovil") / archivo.relative_to(DESTINO))
    print(f"Listo: {DESTINO}")
    print(f"       {archivo_zip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
