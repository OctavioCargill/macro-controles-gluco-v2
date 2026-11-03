"""Arma una copia aparte de la app para la prueba de punta a punta, sin tocar tu carpeta data.

Uso (desde la carpeta del repo):   py prueba_e2e\\preparar_copia.py

Crea la carpeta  ..\\macro-controles-gluco-v2-PRUEBA  con el código de la app y, en su carpeta data,
solo los archivos de prueba. Si la carpeta ya existe, no hace nada (borrala a mano para empezar de cero).
"""

import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
DESTINO = REPO.parent / f"{REPO.name}-PRUEBA"
NO_COPIAR = ("data", "logs", "config", ".git", "build", "dist", "dist_final", "prueba_e2e", "__pycache__",
             ".pytest_cache", "*.pyc")


def main():
    if DESTINO.exists():
        print(f"Ya existe {DESTINO}. Borrala si querés empezar la prueba de cero.")
        return 1
    shutil.copytree(REPO, DESTINO, ignore=shutil.ignore_patterns(*NO_COPIAR))
    (DESTINO / "data").mkdir()
    (DESTINO / "config").mkdir()
    ajustes = REPO / "config" / "app_settings.json"
    if ajustes.exists():
        shutil.copy2(ajustes, DESTINO / "config" / ajustes.name)
    for archivo in (AQUI / "data_inicial").iterdir():
        shutil.copy2(archivo, DESTINO / "data" / archivo.name)
    print(f"Listo: {DESTINO}")
    print(f'Para abrir la app de prueba:  cd "{DESTINO}"  y después  py -m gui.app')
    return 0


if __name__ == "__main__":
    sys.exit(main())
