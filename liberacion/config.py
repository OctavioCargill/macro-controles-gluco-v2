"""Parámetros de Liberación (hoja Tablas de la macro y rutas de los archivos)."""

import json
import logging
from pathlib import Path

from services.auditoria import APP_CONFIG_PATH

logger = logging.getLogger(__name__)

RUTA_CONFIG = Path(APP_CONFIG_PATH) / "liberacion.json"

CONFIG_POR_DEFECTO = {
    # Tablas!A:B — estado del pago en E1
    "estados": {
        "2": "Split o cambio de benficiario",
        "F": "Validación Coherente",
        "H": "Pendiente de liberar",
        "A": "Liberado",
        "P": "Transmitido a A9",
        "M": "Anulado",
        "Y": "Proximo a estado A",
        "X": "ERROR - LEVANTAR INC",
    },
    # Tablas!D — documentos de cobro que pueden quedar devengados en el netting
    "documentos_cobro": ["RI", "RT", "RM", "X&", "X@", "Q4", "QJ"],
    # Tipos del 020 a los que la macro les invierte el signo del importe cancelado
    "tipos_signo_negativo": ["AH", "RI", "RM", "RT", "X@", "X&", "Q4", "QJ"],
    "rutas": {"020": "", "067": "", "propuestas": "", "output_e1": "", "historico": "", "pagados": "", "020_limpiar": ""},
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
