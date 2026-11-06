"""Pasa los históricos de la macro (.xlsb) al formato de la app (.xlsx), una sola vez.

La app lee y escribe los históricos en .xlsx (sin Excel no se puede modificar un .xlsb). Este módulo:
- busca la hoja y la fila de títulos (la que tiene «Tipo Doc»),
- copia todas las filas tal cual, con los títulos en la fila 1,
- convierte a fecha las columnas de fechas (en un .xlsb vienen como números),
- deja los IDs (id_largo, id_corto) como texto y, si el histórico no los tiene, los calcula como CONTROLAR,
- verifica releyendo el .xlsx que estén todas las filas y los mismos IDs.
Antes de reemplazar un .xlsx existente guarda una copia.
"""

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from netting.cargas import ErrorDeCarga

_EPOCA = datetime(1899, 12, 30)
DESTINOS = {
    "controlados": ("Historico_Documentos_Controlados.xlsx", "Historico_Controlados"),
    "pagados": ("historico_pagados.xlsx", "Historico_Pagados"),
}
COLUMNAS_ID = ("id_largo", "id_corto")
PALABRAS_FECHA = ("fecha", "vencim", "emision")


def _clave(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("_", " ").split())


@dataclass
class InformeMigracion:
    origen: Path
    tipo: str
    hoja: str = ""
    fila_titulos: int = 0
    columnas: list = field(default_factory=list)
    filas: int = 0
    columnas_fecha: list = field(default_factory=list)
    ids_calculados: bool = False
    avisos: list = field(default_factory=list)
    destino: Path = None
    copia: Path = None
    verificado: bool = False

    def texto(self):
        lineas = [
            f"Archivo: {self.origen.name}",
            f"Hoja: {self.hoja}  ·  títulos en la fila {self.fila_titulos}",
            f"Filas de datos: {self.filas:,}".replace(",", "."),
            f"Columnas ({len(self.columnas)}): {', '.join(self.columnas)}",
            f"Columnas de fecha que se convierten: {', '.join(self.columnas_fecha) or 'ninguna'}",
        ]
        if self.ids_calculados:
            lineas.append("No tenía id_largo / id_corto: se calculan como en CONTROLAR.")
        for aviso in self.avisos:
            lineas.append(f"⚠ {aviso}")
        if self.destino:
            lineas.append(f"Guardado en: {self.destino}")
        if self.copia:
            lineas.append(f"Copia del anterior: {self.copia.name}")
        if self.verificado:
            lineas.append("✓ Verificado: el .xlsx tiene todas las filas y los mismos IDs.")
        return "\n".join(lineas)


def _leer_hojas(ruta):
    try:
        from pyxlsb import open_workbook
    except ImportError as exc:  # pragma: no cover
        raise ErrorDeCarga("Falta la librería pyxlsb para leer archivos .xlsb.") from exc
    hojas = {}
    with open_workbook(str(ruta)) as libro:
        for nombre in libro.sheets:
            with libro.get_sheet(nombre) as hoja:
                hojas[nombre] = [[celda.v for celda in fila] for fila in hoja.rows(sparse=False)]
    return hojas


def _leer_hojas_xlsx(ruta):
    import openpyxl

    libro = openpyxl.load_workbook(str(ruta), read_only=True, data_only=True)
    try:
        return {h.title: [list(f) for f in h.iter_rows(values_only=True)] for h in libro.worksheets}
    finally:
        libro.close()


def _elegir_hoja(hojas, nombre_archivo):
    """La hoja con «Tipo Doc» en los títulos y más filas de datos."""
    mejor = None
    for nombre, filas in hojas.items():
        for indice, fila in enumerate(filas[:20]):
            claves = [_clave(v) for v in fila]
            if "tipo doc" in claves and ("numero doc" in claves or "documento" in claves or "id largo" in claves):
                datos = [f for f in filas[indice + 1:] if any(v not in (None, "") for v in f)]
                if mejor is None or len(datos) > len(mejor[3]):
                    mejor = (nombre, indice, fila, datos)
                break
    if mejor is None:
        raise ErrorDeCarga(f"{nombre_archivo}: no encontré ninguna hoja con la columna «Tipo Doc».")
    return mejor


def _normalizar_valor(valor, es_fecha, es_id):
    if isinstance(valor, float) and valor.is_integer() and not es_fecha:
        valor = int(valor)
    if es_fecha and isinstance(valor, (int, float)) and not isinstance(valor, bool) and 1 <= valor < 2958466:
        return _EPOCA + timedelta(days=float(valor))
    if es_id and valor not in (None, ""):
        return str(valor).strip()
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def preparar(ruta_xlsb, tipo):
    """Lee el histórico de la macro y devuelve (informe, títulos, filas) listos para guardar."""
    ruta = Path(ruta_xlsb)
    if tipo not in DESTINOS:
        raise ValueError(f"Tipo de histórico desconocido: {tipo}")
    if not ruta.exists():
        raise ErrorDeCarga(f"No existe {ruta}.")
    hojas = _leer_hojas(ruta) if ruta.suffix.lower() == ".xlsb" else _leer_hojas_xlsx(ruta)
    nombre_hoja, indice, encabezado, datos = _elegir_hoja(hojas, ruta.name)

    ancho = max([len(encabezado)] + [len(f) for f in datos])
    titulos = [str(v).strip() if v not in (None, "") else "" for v in encabezado] + [""] * (ancho - len(encabezado))
    while titulos and titulos[-1] == "" and all(len(f) < len(titulos) or f[len(titulos) - 1] in (None, "") for f in datos):
        titulos.pop()
    informe = InformeMigracion(origen=ruta, tipo=tipo, hoja=nombre_hoja, fila_titulos=indice + 1)
    vistos = {}
    for posicion, titulo in enumerate(titulos):
        if not titulo:
            titulos[posicion] = f"Columna_{posicion + 1}"
            informe.avisos.append(f"La columna {posicion + 1} no tiene título: se llama «{titulos[posicion]}».")
        if titulos[posicion] in vistos:
            nuevo = f"{titulos[posicion]}_{posicion + 1}"
            informe.avisos.append(f"Título repetido «{titulos[posicion]}»: la segunda se llama «{nuevo}».")
            titulos[posicion] = nuevo
        vistos[titulos[posicion]] = posicion

    es_fecha = [any(p in _clave(t) for p in PALABRAS_FECHA) for t in titulos]
    es_id = [_clave(t).replace(" ", "_") in COLUMNAS_ID for t in titulos]
    informe.columnas_fecha = [t for t, f in zip(titulos, es_fecha) if f]
    filas = []
    for fila in datos:
        fila = list(fila[:len(titulos)]) + [None] * (len(titulos) - len(fila))
        filas.append([_normalizar_valor(v, f, i) for v, f, i in zip(fila, es_fecha, es_id)])

    claves = [_clave(t) for t in titulos]
    if not all(c in claves for c in ("id largo", "id corto")):
        titulos, filas = _calcular_ids(titulos, filas, informe)
    informe.columnas = titulos
    informe.filas = len(filas)
    return informe, titulos, filas


def _calcular_ids(titulos, filas, informe):
    import pandas as pd

    from processors.ids import generar_id_corto, generar_id_largo, normalizar_nro_legal

    necesarias = ["Tipo Doc", "Numero Doc", "Numero de CAE COE Factura", "Numero documento fiscal", "Fecha Pago"]
    faltan = [c for c in necesarias if c not in titulos]
    if faltan:
        informe.avisos.append(
            "No tiene id_largo / id_corto y no se pueden calcular (faltan: " + ", ".join(faltan) + "). "
            "CONTROLAR no va a poder reconocer lo ya controlado: avisale al desarrollador antes de usarlo."
        )
        return titulos, filas
    df = pd.DataFrame(filas, columns=titulos)
    df = generar_id_largo(generar_id_corto(normalizar_nro_legal(df)))
    informe.ids_calculados = True
    nuevos = [c for c in df.columns if c not in titulos]
    titulos = titulos + nuevos
    filas = [fila + [df.iloc[i][c] for c in nuevos] for i, fila in enumerate(filas)]
    return titulos, filas


def migrar(ruta_xlsb, tipo, carpeta_destino):
    """Convierte y guarda en la carpeta de datos. Si ya había un .xlsx, guarda una copia antes."""
    from openpyxl import Workbook

    informe, titulos, filas = preparar(ruta_xlsb, tipo)
    nombre, hoja = DESTINOS[tipo]
    destino = Path(carpeta_destino) / nombre
    temporal = destino.with_name(f"{destino.stem}_migrando.xlsx")
    libro = Workbook(write_only=True)
    h = libro.create_sheet(hoja)
    h.append(titulos)
    for fila in filas:
        h.append(fila)
    libro.save(temporal)

    # Verificación: mismas filas y mismos IDs
    releido = _leer_hojas_xlsx(temporal)[hoja]
    columnas_id = [i for i, t in enumerate(titulos) if _clave(t) in ("id largo", "id corto")]
    originales = {tuple(str(f[i]) for i in columnas_id) for f in filas}
    copiados = {tuple(str(f[i]) for i in columnas_id) for f in releido[1:]}
    if len(releido) - 1 != len(filas) or originales != copiados:
        temporal.unlink(missing_ok=True)
        raise ErrorDeCarga(f"La verificación falló: se leyeron {len(filas)} filas y se escribieron {len(releido) - 1}. "
                           "No se cambió nada.")
    if destino.exists():
        informe.copia = destino.with_name(f"{destino.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}{destino.suffix}")
        destino.rename(informe.copia)
    temporal.rename(destino)
    informe.destino = destino
    informe.verificado = True
    return informe
