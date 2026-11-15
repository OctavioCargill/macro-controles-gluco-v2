r"""Arma un juego de datos inventados para probar el .exe de punta a punta (Controlar → Netting → Liberación).

Uso, desde la carpeta del repo:
    py prueba_exe\armar_datos.py                       fecha de proceso = hoy (o el próximo día hábil)
    py prueba_exe\armar_datos.py --fecha 10/11/2026
    py prueba_exe\armar_datos.py --exe dist\Glucovil   además arma dist\Glucovil_PRUEBA lista para abrir

Deja en prueba_exe\:
    data\     044, 090, 077, 020, 067, 020_LIMPIAR e históricos coherentes entre sí (formato de la app)
    config\   netting.json con valores por defecto (último N° de propuesta 54628, sin rutas guardadas)
    GUION.md  pasos y resultados esperados, con las fechas de este juego

Las fechas de pago se calculan contra la fecha de proceso: si lo probás otro día, volvé a correr el script.
"""

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "prueba_demo"))

from netting.config import CONFIG_POR_DEFECTO  # noqa: E402
from preparar_demo import generar, habil  # noqa: E402

LEEME_DATA = "DATOS DE PRUEBA INVENTADOS (fecha de proceso {hoy}). No son datos reales. Ver GUION.md.\n"


def armar(destino, hoy):
    data, config = destino / "data", destino / "config"
    for carpeta in (data, config):
        if carpeta.exists():
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True)
    p24, p48 = generar(data, hoy)
    (data / "LEEME.txt").write_text(LEEME_DATA.format(hoy=f"{hoy:%d/%m/%Y}"), encoding="utf-8")
    ajustes = {k: v for k, v in CONFIG_POR_DEFECTO.items()}
    (config / "netting.json").write_text(json.dumps(ajustes, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(REPO / "config" / "app_settings.json", config / "app_settings.json")

    guion = (REPO / "prueba_demo" / "GUION.md").read_text(encoding="utf-8")
    for clave, valor in {"{HOY}": f"{hoy:%d/%m/%Y}", "{P24}": f"{p24:%d/%m/%Y}", "{P48}": f"{p48:%d/%m/%Y}",
                         "{ACREDITACION}": f"{p48:%d/%m/%Y}"}.items():
        guion = guion.replace(clave, valor)
    (destino / "GUION.md").write_text(guion, encoding="utf-8")
    return p24, p48


def copia_exe(carpeta_exe, datos):
    """dist\\Glucovil → dist\\Glucovil_PRUEBA con estos datos. No toca la carpeta original."""
    carpeta_exe = Path(carpeta_exe).resolve()
    if not (carpeta_exe / "MacroControlesGlucoV2.exe").exists():
        raise SystemExit(f"No encontré MacroControlesGlucoV2.exe en {carpeta_exe}")
    prueba = carpeta_exe.with_name(f"{carpeta_exe.name}_PRUEBA")
    if prueba.exists():
        shutil.rmtree(prueba)
    shutil.copytree(carpeta_exe, prueba, ignore=shutil.ignore_patterns("data", "config", "logs"))
    shutil.copytree(datos / "data", prueba / "data")
    shutil.copytree(datos / "config", prueba / "config")
    (prueba / "logs").mkdir()
    shutil.copy2(datos / "GUION.md", prueba / "GUION.md")
    return prueba


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fecha", help="fecha de proceso dd/mm/aaaa (por defecto hoy, o el próximo día hábil)")
    parser.add_argument("--exe", help="carpeta del ejecutable (ej. dist\\Glucovil) para armar una copia _PRUEBA")
    args = parser.parse_args()
    hoy = datetime.strptime(args.fecha, "%d/%m/%Y").date() if args.fecha else date.today()
    while not habil(hoy):
        hoy += timedelta(days=1)

    p24, p48 = armar(AQUI, hoy)
    print(f"Datos listos en {AQUI / 'data'}")
    print(f"Fecha de proceso {hoy:%d/%m/%Y} · pagos de 24 hs el {p24:%d/%m/%Y} · de 48 hs el {p48:%d/%m/%Y}")
    if args.exe:
        print(f"Copia para probar: {copia_exe(args.exe, AQUI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
