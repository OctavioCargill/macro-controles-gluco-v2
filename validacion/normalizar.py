"""Normalización de textos, códigos, importes y fechas leídos por OCR o desde un PDF."""

import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher

# Confusiones típicas del OCR en números (solo se aplican cuando el dato de la app es numérico)
_CONFUSIONES = str.maketrans({"o": "0", "O": "0", "i": "1", "I": "1", "l": "1", "|": "1", "s": "5", "S": "5",
                              "b": "8", "B": "8", "z": "2", "Z": "2"})
_IMPORTE = re.compile(r"-?\$?\s?(?:\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+,\d{1,2}|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{2}|\d+)")


def texto(valor):
    """Minúsculas, sin acentos, sin signos y con un solo espacio."""
    valor = unicodedata.normalize("NFKD", str(valor or ""))
    valor = "".join(c for c in valor if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9#&@]+", " ", valor).split())


def codigo(valor, ocr=False):
    """Letras y números juntos, sin ceros adelante. Con ocr=True corrige O→0, I→1, etc."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    valor = str(valor or "").strip()
    if re.fullmatch(r"\d+\.0+", valor):          # número que vino de Excel como 340000085001.0
        valor = valor.split(".")[0]
    if ocr:
        valor = valor.translate(_CONFUSIONES)
    valor = re.sub(r"[^0-9A-Za-z]", "", valor).upper()
    return valor.lstrip("0") or valor


def importe(valor):
    """'$ 15.020.000,00', '15,020,000.00', '15020000' → 15020000.0 (None si no es un importe)."""
    if isinstance(valor, (int, float)):
        return float(valor)
    crudo = re.sub(r"[\s$]", "", str(valor or ""))
    negativo = crudo.startswith("-") or (crudo.startswith("(") and crudo.endswith(")"))
    crudo = crudo.strip("-()")
    if not re.fullmatch(r"[\d.,]+", crudo or "x"):
        return None
    if "," in crudo and "." in crudo:
        decimal = "," if crudo.rfind(",") > crudo.rfind(".") else "."
        crudo = crudo.replace("." if decimal == "," else ",", "").replace(decimal, ".")
    elif "," in crudo:
        crudo = crudo.replace(",", ".") if re.search(r",\d{1,2}$", crudo) else crudo.replace(",", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", crudo):
        crudo = crudo.replace(".", "")
    try:
        numero = float(crudo)
    except ValueError:
        return None
    return -numero if negativo else numero


def importes_en(texto_libre):
    """Todos los importes que aparecen en un texto (para buscar en una factura)."""
    encontrados = []
    for coincidencia in _IMPORTE.finditer(str(texto_libre or "")):
        numero = importe(coincidencia.group(0).replace(" ", "") if "." in coincidencia.group(0) else coincidencia.group(0))
        if numero is not None:
            encontrados.append(numero)
    return encontrados


def fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    crudo = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S",
                    "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(crudo, formato).date()
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", crudo)
    if m:
        dia, mes, anio = (int(x) for x in m.groups())
        anio += 2000 if anio < 100 else 0
        try:
            return date(anio, mes, dia)
        except ValueError:
            return None
    return None


def parecido(a, b):
    return SequenceMatcher(None, texto(a), texto(b)).ratio()
