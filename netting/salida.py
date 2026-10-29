"""Salida de Netting: reparto por analista (unificar_24 / unificar_48) y Propuestas_Netting.xlsx."""

from datetime import datetime
from pathlib import Path

from netting.cargas import vacio
from netting.motor import COBRAR, PAGAR, igual

COLUMNAS_SALIDA = [
    ("Tipo de beneficiario", "tipo_benef"),
    ("Tipo", "tipo"),
    ("AB Corredos", "ab_corredor"),
    ("CORREDOR", "corredor"),
    ("AB Vendedor", "ab_vendedor"),
    ("VENDEDOR", "vendedor"),
    ("AB Beneficiario", "ab_benef"),
    ("Beneficiario", "benef"),
    ("N de Docu", "doc"),
    ("TIPO de Docu", "tipo_doc"),
    ("Descripcion de Docu", "desc"),
    ("Total", "total"),
    ("Fecha Emision", "fecha_emision"),
    ("Contrato", "contrato"),
    ("N_PROPUESTA", "n_propuesta"),
    ("Doc Incluidos", None),
    ("COMBOBOX", None),
    ("Observaciones", "observaciones"),
    ("GRUPOS", "grupo"),
]


def _cint_vba(valor):
    """Asignar un Double a un Integer en VBA redondea al par más cercano (0,5 → 0; 1,5 → 2)."""
    return int(round(valor))


def asignar_grupos(propuestas, cantidad_analistas, ventana):
    """unificar_24 / unificar_48: reparte propuestas enteras entre analistas, en el orden de la hoja.

    Devuelve la cantidad de propuestas contadas.
    """
    for fila in propuestas:
        fila["grupo"] = ""
    n = len(propuestas)

    cantidad = 0
    r = 0
    while r < n and not vacio(propuestas[r]["n_propuesta"]):
        actual = propuestas[r]["n_propuesta"]
        while r < n and igual(propuestas[r]["n_propuesta"], actual):
            r += 1
        cantidad += 1

    por_grupo = _cint_vba(cantidad / cantidad_analistas) if cantidad_analistas else 0
    armador, contador, r = 1, 0, 0
    while r < n and not vacio(propuestas[r]["n_propuesta"]):
        actual = propuestas[r]["n_propuesta"]
        while r < n and igual(propuestas[r]["n_propuesta"], actual):
            propuestas[r]["grupo"] = armador
            r += 1
        contador += 1
        if contador == por_grupo:
            armador += 1
            # unificar_24 no deja pasar del último analista; unificar_48 no tiene ese tope.
            if ventana == "24" and armador > cantidad_analistas:
                armador = cantidad_analistas
            contador = 0
    return cantidad


def resumen_propuestas(propuestas):
    """Una entrada por N° de propuesta (en el orden de la hoja) con totales a pagar y a descontar."""
    resumen = []
    indice = {}
    for fila in propuestas:
        clave = fila["n_propuesta"] if not vacio(fila["n_propuesta"]) else ("sin número", id(fila))
        if clave not in indice:
            indice[clave] = len(resumen)
            resumen.append({
                "n_propuesta": fila["n_propuesta"],
                "ventana": fila["ventana"],
                "tipo_benef": fila["tipo_benef"],
                "ab_benef": fila["ab_benef"],
                "benef": fila["benef"],
                "grupo": fila.get("grupo", ""),
                "filas": [],
                "a_pagar": 0.0,
                "a_descontar": 0.0,
            })
        item = resumen[indice[clave]]
        item["filas"].append(fila)
        total = fila["total"] or 0.0
        if fila["tipo"] == PAGAR:
            item["a_pagar"] += total
        elif fila["tipo"] == COBRAR:
            item["a_descontar"] += total
    for item in resumen:
        item["neto"] = item["a_pagar"] + item["a_descontar"]
        item["documentos"] = len(item["filas"])
        item["grupo"] = item["filas"][0].get("grupo", "")
    return resumen


def _valor_excel(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if texto.isdigit() and len(texto) < 15:
            return int(texto)
    return valor


def exportar_propuestas(ruta, propuestas_24, propuestas_48, info):
    """Escribe Propuestas_Netting.xlsx con las hojas Propuestas_24, Propuestas_48 y Control.

    info: lista de (clave, valor) para la hoja Control.
    """
    import xlsxwriter

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        libro = xlsxwriter.Workbook(str(ruta))
    except Exception as exc:  # pragma: no cover
        raise PermissionError(str(exc)) from exc

    encabezado = libro.add_format({"bold": True, "bg_color": "#e6ecdc", "border": 1})
    moneda = libro.add_format({"num_format": "#,##0.00"})
    fecha = libro.add_format({"num_format": "dd/mm/yyyy"})

    for nombre_hoja, filas in (("Propuestas_24", propuestas_24), ("Propuestas_48", propuestas_48)):
        hoja = libro.add_worksheet(nombre_hoja)
        for columna, (titulo, _campo) in enumerate(COLUMNAS_SALIDA):
            hoja.write(0, columna, titulo, encabezado)
        for numero, fila in enumerate(filas, start=1):
            for columna, (_titulo, campo) in enumerate(COLUMNAS_SALIDA):
                if campo is None:
                    continue
                valor = _valor_excel(fila.get(campo))
                if valor is None or valor == "":
                    continue
                if isinstance(valor, datetime):
                    hoja.write_datetime(numero, columna, valor, fecha)
                elif campo == "total" and isinstance(valor, (int, float)):
                    hoja.write_number(numero, columna, valor, moneda)
                else:
                    hoja.write(numero, columna, valor)
        anchos = [20, 8, 12, 32, 12, 32, 14, 32, 12, 8, 28, 16, 12, 14, 13, 12, 12, 24, 9]
        for columna, ancho in enumerate(anchos):
            hoja.set_column(columna, columna, ancho)
        hoja.freeze_panes(1, 0)
        if filas:
            hoja.autofilter(0, 0, len(filas), len(COLUMNAS_SALIDA) - 1)

    control = libro.add_worksheet("Control")
    control.write(0, 0, "Dato", encabezado)
    control.write(0, 1, "Valor", encabezado)
    for numero, (clave, valor) in enumerate(info, start=1):
        control.write(numero, 0, clave)
        control.write(numero, 1, str(valor) if not isinstance(valor, (int, float)) else valor)
    control.set_column(0, 0, 38)
    control.set_column(1, 1, 110)

    try:
        libro.close()
    except Exception as exc:
        raise PermissionError(
            f"No se pudo guardar {ruta.name}. Si está abierto en Excel, cerralo y probá de nuevo."
        ) from exc
    return ruta
