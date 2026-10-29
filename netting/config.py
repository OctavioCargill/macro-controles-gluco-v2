"""Parámetros de Netting que en la macro vivían en la hoja Tablas.

Se guardan en config/netting.json para poder editarlos sin tocar código:
    feriados                 Tablas!A  (se agregaron los de 2026, que la macro no tenía)
    corredores_solo_24       Tablas!I:J (AB y nombre de corredores que solo cobran a 24 hs)
    ultimo_numero_propuesta  Tablas!G2 (último N° de propuesta usado)
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

from services.auditoria import APP_CONFIG_PATH

logger = logging.getLogger(__name__)

RUTA_CONFIG = Path(APP_CONFIG_PATH) / "netting.json"

# Feriados tal como estaban en Tablas!A de Macro_Propuesta.xlsm ...
_FERIADOS_MACRO = [
    "2021-01-01", "2021-02-15", "2021-02-16", "2021-03-24", "2021-04-01", "2021-04-02", "2021-05-24",
    "2021-05-25", "2021-06-21", "2021-07-09", "2021-08-16", "2021-10-08", "2021-10-11", "2021-11-22",
    "2021-12-08", "2021-12-24", "2021-12-31",
    "2022-02-28", "2022-03-01", "2022-03-24", "2022-04-14", "2022-04-15", "2022-05-18", "2022-05-25",
    "2022-06-17", "2022-06-20", "2022-08-15", "2022-10-07", "2022-10-10", "2022-11-21", "2022-12-08",
    "2022-12-09",
    "2023-08-21", "2023-10-13", "2023-10-16", "2023-11-20", "2023-12-08", "2023-12-25",
    "2024-06-17", "2024-06-20", "2024-06-21", "2024-11-18", "2024-12-24", "2024-12-25", "2024-12-31",
    "2025-01-01", "2025-03-03", "2025-03-04", "2025-03-24", "2025-04-02", "2025-04-17", "2025-04-18",
    "2025-05-01", "2025-05-02", "2025-06-16", "2025-06-20", "2025-07-09", "2025-08-15", "2025-11-21",
    "2025-11-24", "2025-12-08", "2025-12-24", "2025-12-25", "2025-12-31",
    "2026-01-01",
]
# ... más los feriados nacionales y días no laborables de 2026 (la macro solo tenía el 1/1/2026).
# Mismo criterio que usó la macro en 2025: feriados, días no laborables, 24 y 31 de diciembre.
_FERIADOS_2026 = [
    "2026-02-16", "2026-02-17", "2026-03-23", "2026-03-24", "2026-04-02", "2026-04-03", "2026-05-01",
    "2026-05-25", "2026-06-15", "2026-06-20", "2026-07-09", "2026-07-10", "2026-08-17", "2026-10-12",
    "2026-11-23", "2026-12-07", "2026-12-08", "2026-12-24", "2026-12-25", "2026-12-31",
]

CONFIG_POR_DEFECTO = {
    "feriados": _FERIADOS_MACRO + _FERIADOS_2026,
    "corredores_solo_24": [
        {"ab": "35106665", "nombre": "BARRILLI S.A."},
        {"ab": "35106864", "nombre": "DIAZ RIGANTI CEREALES SRL"},
        {"ab": "35230789", "nombre": "GRANAR SAC Y F"},
        {"ab": "35131580", "nombre": "FUTUROS Y OPCIONES.COM.SA"},
        {"ab": "35230725", "nombre": "ENRIQUE R ZENI Y CIA SACIAFEI"},
    ],
    # Valor de Tablas!G2 en la copia de la macro analizada. Antes de la primera corrida real
    # hay que poner el número que tenga la macro en producción ese día.
    "ultimo_numero_propuesta": 54628,
    "cantidad_analistas": 1,
    "rutas": {"historico": "", "077": "", "090": "", "ventas": "", "salida": ""},
}


def cargar_config():
    config = json.loads(json.dumps(CONFIG_POR_DEFECTO))
    if RUTA_CONFIG.exists():
        try:
            guardado = json.loads(RUTA_CONFIG.read_text(encoding="utf-8"))
            for clave, valor in guardado.items():
                if clave == "rutas" and isinstance(valor, dict):
                    config["rutas"].update(valor)
                else:
                    config[clave] = valor
        except Exception:
            logger.exception("No se pudo leer %s; se usan los valores por defecto.", RUTA_CONFIG)
    return config


def guardar_config(config):
    RUTA_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    RUTA_CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def feriados_como_fechas(config):
    fechas = set()
    for valor in config.get("feriados", []):
        try:
            fechas.add(datetime.strptime(str(valor)[:10], "%Y-%m-%d").date())
        except ValueError:
            logger.warning("Feriado con formato inválido en la configuración: %r", valor)
    return fechas


def anios_sin_feriados(config, *fechas: date):
    """Años de las fechas dadas que no tienen ningún feriado cargado (para avisar)."""
    anios = {f.year for f in feriados_como_fechas(config)}
    return sorted({f.year for f in fechas if f is not None and f.year not in anios})
