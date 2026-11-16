"""Lectura de capturas de pantalla (OCR) y de facturas en PDF. Todo local, sin internet."""

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class LecturaNoDisponible(RuntimeError):
    """Falta una librería (OCR o PDF) o el archivo no se pudo leer."""


@dataclass
class Renglon:
    texto: str
    x0: float = 0
    y0: float = 0
    x1: float = 0
    y1: float = 0
    confianza: float = 1.0
    pagina: int = 1

    @property
    def alto(self):
        return max(1.0, self.y1 - self.y0)

    @property
    def centro_y(self):
        return (self.y0 + self.y1) / 2


_motor = None
_candado = threading.Lock()


def _motor_ocr():
    """El motor se carga una sola vez (la primera lectura tarda un poco más)."""
    global _motor
    with _candado:
        if _motor is None:
            try:
                from rapidocr import RapidOCR
            except Exception as exc:  # pragma: no cover - depende de la instalación
                raise LecturaNoDisponible(
                    "No está instalado el lector de imágenes (rapidocr). Instalalo con: "
                    "py -m pip install rapidocr onnxruntime"
                ) from exc
            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            _motor = RapidOCR()
        return _motor


def leer_imagen(imagen, pagina=1):
    """Renglones de una imagen: ruta, bytes o imagen PIL. Cada renglón trae su texto y su posición."""
    try:
        import numpy as np
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise LecturaNoDisponible("Faltan las librerías numpy / Pillow.") from exc
    if isinstance(imagen, (str, Path)):
        try:
            imagen = Image.open(imagen)
        except Exception as exc:
            raise LecturaNoDisponible(f"No se pudo abrir la imagen: {exc}") from exc
    elif isinstance(imagen, (bytes, bytearray)):
        import io
        imagen = Image.open(io.BytesIO(imagen))
    imagen = imagen.convert("RGB")
    # Capturas chicas se leen mejor ampliadas
    if imagen.width < 1000:
        factor = 1000 / imagen.width
        imagen = imagen.resize((int(imagen.width * factor), int(imagen.height * factor)))
    else:
        factor = 1.0
    resultado = _motor_ocr()(np.array(imagen)[:, :, ::-1])
    renglones = []
    if resultado is None or getattr(resultado, "boxes", None) is None:
        return renglones
    for caja, txt, confianza in zip(resultado.boxes, resultado.txts, resultado.scores):
        xs = [p[0] for p in caja]
        ys = [p[1] for p in caja]
        renglones.append(Renglon(str(txt).strip(), min(xs) / factor, min(ys) / factor, max(xs) / factor,
                                 max(ys) / factor, float(confianza), pagina))
    renglones.sort(key=lambda r: (round(r.centro_y / max(r.alto, 1)), r.x0))
    return renglones


def leer_pdf(ruta):
    """Renglones de texto de un PDF. Si el PDF es escaneado (sin texto), se leen sus imágenes con OCR."""
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        raise LecturaNoDisponible("No está instalada la librería para leer PDFs (pypdf).") from exc
    try:
        lector = PdfReader(str(ruta))
    except Exception as exc:
        raise LecturaNoDisponible(f"No se pudo abrir el PDF: {exc}") from exc
    renglones = []
    for numero, pagina in enumerate(lector.pages, start=1):
        try:
            texto = pagina.extract_text(extraction_mode="layout") or ""
        except Exception:
            texto = pagina.extract_text() or ""
        lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
        for posicion, linea in enumerate(lineas):
            renglones.append(Renglon(" ".join(linea.split()), 0, posicion * 10, 1000, posicion * 10 + 8, 1.0, numero))
        if not lineas:
            for imagen in getattr(pagina, "images", []):
                try:
                    renglones.extend(leer_imagen(imagen.data, pagina=numero))
                except LecturaNoDisponible:
                    raise
                except Exception:
                    logger.exception("No se pudo leer una imagen del PDF %s", ruta)
    return renglones


def imagen_del_portapapeles():
    """La imagen copiada (Win + Shift + S o Impr Pant). None si no hay una imagen."""
    try:
        from PIL import Image, ImageGrab
    except Exception:  # pragma: no cover
        return None
    try:
        contenido = ImageGrab.grabclipboard()
    except Exception:
        return None
    if isinstance(contenido, Image.Image):
        return contenido
    if isinstance(contenido, list):          # archivo de imagen copiado desde el Explorador
        for ruta in contenido:
            if str(ruta).lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                try:
                    return Image.open(ruta)
                except Exception:
                    return None
    return None
