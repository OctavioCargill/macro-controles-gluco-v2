"""Aviso de uso simultáneo para cuando dos PCs comparten la misma carpeta de datos.

Mientras una app guarda (pasar al histórico, dar salida, controlar pagos, Output E1, limpiar pagadas) deja en
la carpeta de datos el archivo .glucovil_en_uso.json con usuario, PC y hora. Si la otra PC intenta guardar en
ese momento, recibe un aviso con quién está guardando y no toca nada. Si una app se cerró de golpe y la marca
quedó, pasados unos minutos se ignora sola.
"""

import getpass
import json
import os
import socket
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

NOMBRE_MARCA = ".glucovil_en_uso.json"
VENCIMIENTO = timedelta(minutes=10)


class CarpetaEnUso(PermissionError):
    """Otra PC está guardando en la carpeta de datos. Es PermissionError para que las pantallas lo muestren
    igual que un archivo abierto en Excel."""


def _quien_soy():
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = os.environ.get("USERNAME", "otro usuario")
    return {"usuario": usuario, "pc": socket.gethostname(), "pid": os.getpid()}


def _leer(ruta):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def quien_esta_guardando(carpeta):
    """Datos de la marca vigente de otra PC, o None si no hay nadie guardando."""
    marca = _leer(Path(carpeta) / NOMBRE_MARCA)
    if not marca:
        return None
    try:
        desde = datetime.fromisoformat(marca.get("desde", ""))
    except ValueError:
        return None
    yo = _quien_soy()
    if datetime.now() - desde > VENCIMIENTO or (marca.get("pc") == yo["pc"] and marca.get("pid") == yo["pid"]):
        return None
    return marca


@contextmanager
def uso_exclusivo(accion, carpeta=None):
    """Envuelve una escritura en la carpeta de datos. accion: texto como «dando salida al netting»."""
    if carpeta is None:
        from services.auditoria import APP_DATA_PATH
        carpeta = APP_DATA_PATH
    ruta = Path(carpeta) / NOMBRE_MARCA
    otro = quien_esta_guardando(carpeta)
    if otro:
        raise CarpetaEnUso(
            f"{otro.get('usuario', 'Otro usuario')} está {otro.get('accion', 'guardando')} desde la PC "
            f"{otro.get('pc', '?')} (desde las {otro.get('desde', '')[11:16]}). Esperá a que termine y probá de nuevo."
        )
    mia = {**_quien_soy(), "accion": accion, "desde": datetime.now().isoformat(timespec="seconds")}
    try:
        ruta.write_text(json.dumps(mia, ensure_ascii=False), encoding="utf-8")
    except OSError:
        mia = None          # si no se puede dejar la marca (carpeta de solo lectura), igual se sigue
    try:
        yield
    finally:
        if mia is not None:
            actual = _leer(ruta)
            if actual and actual.get("pc") == mia["pc"] and actual.get("pid") == mia["pid"]:
                try:
                    ruta.unlink()
                except OSError:
                    pass
