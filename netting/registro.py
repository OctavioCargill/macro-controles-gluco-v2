"""Qué documentos ya no tienen que entrar al netting.

- Histórico de pagados (data/historico_pagados.xlsx): lo escribe Liberación cuando libera un
  pago. Los documentos que figuran ahí ya terminaron el proceso.
- Registro de propuestos (data/Netting_Propuestos.xlsx): lo escribe Netting en cada salida.
  Un documento que ya está en una propuesta no vuelve a entrar mientras no se libere
  (Liberación lo saca del Histórico de controlados y lo pasa a pagados). También es lo que
  Liberación va a leer para saber qué se propuso, en qué paquete y por cuánto.
"""

import logging
from datetime import datetime
from pathlib import Path

from netting.cargas import ErrorDeCarga, leer_hoja, vacio

logger = logging.getLogger(__name__)

NOMBRE_REGISTRO = "Netting_Propuestos.xlsx"
NOMBRE_PAGADOS = "historico_pagados.xlsx"
HOJA_REGISTRO = "Propuestos"

COLUMNAS_REGISTRO = [
    "Clave", "Estado", "Fecha proceso", "Generado", "Ventana", "N° propuesta", "AB", "Beneficiario",
    "Tipo beneficiario", "Movimiento", "Origen", "N° documento", "Tipo doc", "ID largo", "Total",
    "Acción", "Observaciones", "ID pago E1",
]


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def clave_historico(fila):
    """Identifica un documento del Histórico: id_largo si lo tiene, si no número + tipo."""
    id_largo = _texto(fila.get("id_largo"))
    if id_largo:
        return id_largo
    return f"H|{_texto(fila.get('tipo_doc'))}|{_texto(fila.get('doc'))}"


def clave_077(fila):
    return f"077|{_texto(fila.get('tipo'))}|{_texto(fila.get('nro'))}"


def clave_propuesta(fila):
    """Clave de una fila de propuesta (a pagar sale del Histórico; a descontar, del 077)."""
    if fila.get("origen") == "Histórico":
        return clave_historico({"id_largo": fila.get("id_largo"), "tipo_doc": fila.get("tipo_doc"), "doc": fila.get("doc")})
    return f"077|{_texto(fila.get('tipo_doc'))}|{_texto(fila.get('doc'))}"


def _columnas(encabezado, nombres):
    posiciones = {}
    for indice, valor in enumerate(encabezado):
        clave = _texto(valor).casefold()
        if clave in nombres and clave not in posiciones:
            posiciones[clave] = indice
    return posiciones


def cargar_pagados(ruta):
    """IDs (largos y cortos) del Histórico de pagados. Si el archivo no existe, conjunto vacío."""
    ruta = Path(ruta)
    if not ruta.exists():
        return set(), False
    try:
        filas = leer_hoja(ruta)
    except ErrorDeCarga:
        logger.exception("No se pudo leer el histórico de pagados %s", ruta)
        raise
    if not filas:
        return set(), True
    posiciones = _columnas(filas[0], {"id_largo", "id largo", "id_corto", "id corto"})
    ids = set()
    for fila in filas[1:]:
        for indice in posiciones.values():
            if indice < len(fila) and not vacio(fila[indice]):
                ids.add(_texto(fila[indice]))
    return ids, True


def cargar_propuestos(ruta):
    """Claves de documentos que ya salieron en una propuesta de netting."""
    ruta = Path(ruta)
    if not ruta.exists():
        return set()
    filas = leer_hoja(ruta, HOJA_REGISTRO)
    if not filas:
        return set()
    posiciones = _columnas(filas[0], {"clave", "estado"})
    if "clave" not in posiciones:
        return set()
    claves = set()
    for fila in filas[1:]:
        clave = _texto(fila[posiciones["clave"]]) if posiciones["clave"] < len(fila) else ""
        estado = ""
        if "estado" in posiciones and posiciones["estado"] < len(fila):
            estado = _texto(fila[posiciones["estado"]]).upper()
        # Si en el futuro se anula una propuesta (Estado = ANULADA), sus documentos vuelven a entrar.
        if clave and estado != "ANULADA":
            claves.add(clave)
    return claves


def actualizar_paquete(ruta, resultado, ventana, n_propuesta, datos):
    """Después de dar salida: guarda en el registro la acción, observaciones e ID de pago de un paquete."""
    from openpyxl import load_workbook

    ruta = Path(ruta)
    if not ruta.exists():
        return 0
    libro = load_workbook(ruta)
    try:
        hoja = libro[HOJA_REGISTRO]
        titulos = [celda.value for celda in hoja[1]]
        posicion = {titulo: indice for indice, titulo in enumerate(titulos, start=1) if titulo}
        for titulo in ("Acción", "Observaciones", "ID pago E1"):
            if titulo not in posicion:
                posicion[titulo] = len(titulos) + 1
                titulos.append(titulo)
                hoja.cell(row=1, column=posicion[titulo], value=titulo)
        generado = resultado.generado.strftime("%d/%m/%Y %H:%M")
        cambiadas = 0
        for numero in range(2, hoja.max_row + 1):
            if (str(hoja.cell(numero, posicion["Generado"]).value) == generado
                    and str(hoja.cell(numero, posicion["Ventana"]).value) == f"{ventana} hs"
                    and str(hoja.cell(numero, posicion["N° propuesta"]).value) == str(n_propuesta)):
                for titulo, valor in datos.items():
                    hoja.cell(numero, posicion[titulo], value=valor)
                cambiadas += 1
        libro.save(ruta)
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo actualizar {ruta.name}. Si está abierto en Excel, cerralo y probá de nuevo."
        ) from exc
    finally:
        libro.close()
    return cambiadas


def registrar_salida(ruta, resultado, propuestas_por_ventana):
    """Agrega al registro una fila por documento de cada propuesta generada."""
    from openpyxl import Workbook, load_workbook

    ruta = Path(ruta)
    if ruta.exists():
        libro = load_workbook(ruta)
        hoja = libro[HOJA_REGISTRO] if HOJA_REGISTRO in libro.sheetnames else libro.create_sheet(HOJA_REGISTRO)
    else:
        libro = Workbook()
        hoja = libro.active
        hoja.title = HOJA_REGISTRO

    if hoja.max_row == 1 and hoja["A1"].value is None:
        for columna, titulo in enumerate(COLUMNAS_REGISTRO, start=1):
            hoja.cell(row=1, column=columna, value=titulo)
    titulos = [celda.value for celda in hoja[1]]
    posicion = {titulo: indice for indice, titulo in enumerate(titulos, start=1) if titulo}
    for titulo in COLUMNAS_REGISTRO:
        if titulo not in posicion:
            posicion[titulo] = len(posicion) + 1
            hoja.cell(row=1, column=posicion[titulo], value=titulo)

    generado = resultado.generado.strftime("%d/%m/%Y %H:%M")
    fila_excel = hoja.max_row + 1
    cantidad = 0
    for ventana, propuestas in propuestas_por_ventana:
        for fila in propuestas:
            valores = {
                "Clave": clave_propuesta(fila),
                "Estado": "EN PROPUESTA",
                "Fecha proceso": resultado.fecha_proceso.strftime("%d/%m/%Y"),
                "Generado": generado,
                "Ventana": f"{ventana} hs",
                "N° propuesta": fila.get("n_propuesta"),
                "AB": fila.get("ab_benef"),
                "Beneficiario": fila.get("benef"),
                "Tipo beneficiario": fila.get("tipo_benef"),
                "Movimiento": "A pagar" if fila.get("tipo") == "PAGAR" else "A descontar",
                "Origen": fila.get("origen", ""),
                "N° documento": fila.get("doc"),
                "Tipo doc": fila.get("tipo_doc"),
                "ID largo": fila.get("id_largo", ""),
                "Total": fila.get("total"),
                "Acción": fila.get("accion", ""),
                "Observaciones": fila.get("observaciones", ""),
                "ID pago E1": fila.get("id_pago", ""),
            }
            for titulo, valor in valores.items():
                hoja.cell(row=fila_excel, column=posicion[titulo], value=valor)
            fila_excel += 1
            cantidad += 1
    try:
        libro.save(ruta)
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo actualizar {ruta.name}. Si está abierto en Excel, cerralo y probá de nuevo."
        ) from exc
    finally:
        libro.close()
    logger.info("Registro de propuestos actualizado: %s filas en %s (%s)", cantidad, ruta, datetime.now())
    return cantidad
