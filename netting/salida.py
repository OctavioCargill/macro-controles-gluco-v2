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
    ("COMBOBOX", "accion"),
    ("Observaciones", "observaciones"),
    ("GRUPOS", "grupo"),
    ("ID pago E1", "id_pago"),
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
        a_pagar = [f for f in item["filas"] if f["tipo"] == PAGAR]
        # El tipo del paquete es el de lo que se le paga (los descuentos heredan el del beneficiario).
        if a_pagar:
            item["tipo_benef"] = a_pagar[0]["tipo_benef"]
            item["benef"] = a_pagar[0]["benef"]
        item["observaciones"] = next((f.get("observaciones") for f in item["filas"] if f.get("observaciones")), "")
        item["accion"] = next((f.get("accion") for f in item["filas"] if f.get("accion")), "")
        item["id_pago"] = next((f.get("id_pago") for f in item["filas"] if f.get("id_pago")), "")
        item["alerta_estatus"] = any(f.get("alerta_estatus") for f in item["filas"])
        item.update(datos_para_e1(a_pagar[0] if a_pagar else item["filas"][0]))
    return resumen


# En E1 (GLUCO Netting > Añadir) el AB se pega en «Cliente» si el pago es al vendedor y en
# «Corredor» si es por corredor. Como en el formulario de la macro, para corredor-directo y
# cesión de corredor se busca por el AB del corredor.
_BUSCAR_POR = {
    "CORREDOR": ("CORREDOR", "Corredor", "ab_corredor"),
    "CORREDOR-DIRECTO": ("CORREDOR", "Corredor", "ab_corredor"),
    "CORREDOR-CESION": ("CORREDOR", "Corredor", "ab_corredor"),
    "VENDEDOR": ("VENDEDOR", "Cliente", "ab_benef"),
    "VENDEDOR-CESION": ("VENDEDOR", "Cliente", "ab_benef"),
}


def datos_para_e1(fila):
    buscar_por, campo, columna_ab = _BUSCAR_POR.get(fila["tipo_benef"], ("VENDEDOR", "Cliente", "ab_benef"))
    ab = fila.get(columna_ab)
    if vacio(ab):
        ab = fila.get("ab_benef")
    return {"buscar_por": buscar_por, "campo_e1": campo, "ab_e1": ab}


def poner_datos_paquete(item, observaciones=None, accion=None, id_pago=None):
    """Guarda observaciones, acción e ID de pago de un paquete en todas sus filas (así salen en el Excel)."""
    for clave, valor in (("observaciones", observaciones), ("accion", accion), ("id_pago", id_pago)):
        if valor is None:
            continue
        for fila in item["filas"]:
            fila[clave] = valor
        item[clave] = valor


def poner_observaciones(item, texto):
    poner_datos_paquete(item, observaciones=texto)


def _valor_excel(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if texto.isdigit() and len(texto) < 15:
            return int(texto)
    return valor


COLUMNAS_PAQUETES = [
    ("N° Propuesta", 12), ("AB", 12), ("Tipo beneficiario", 18), ("Cliente", 34), ("Movimiento", 13),
    ("Vendedor", 30), ("Corredor", 26), ("Beneficiario", 30), ("N° Documento", 13), ("Tipo Doc", 9),
    ("Fecha Emisión", 12), ("Descripción", 30), ("Total", 16), ("Grupo", 7), ("Observaciones", 36),
    ("Buscar en netting por", 14), ("AB para E1", 12), ("Campo en E1", 11), ("Acción", 11), ("ID pago E1", 14),
]


def _escribir(hoja, fila, columna, valor, formato=None, fmt_fecha=None, fmt_moneda=None):
    valor = _valor_excel(valor)
    if valor is None or valor == "":
        if formato is not None:
            hoja.write_blank(fila, columna, None, formato)
        return
    if isinstance(valor, datetime):
        hoja.write_datetime(fila, columna, valor, fmt_fecha if formato is None else formato)
    elif isinstance(valor, (int, float)) and fmt_moneda is not None:
        hoja.write_number(fila, columna, valor, fmt_moneda)
    else:
        hoja.write(fila, columna, valor, formato)


def _hoja_paquetes(libro, nombre, propuestas, formatos):
    """Un bloque por AB: cabecera del paquete y, plegables debajo, cuentas por cobrar y por pagar."""
    hoja = libro.add_worksheet(nombre)
    hoja.outline_settings(True, False, False, False)  # el "+/-" arriba de cada bloque
    for columna, (titulo, ancho) in enumerate(COLUMNAS_PAQUETES):
        hoja.write(0, columna, titulo, formatos["encabezado"])
        hoja.set_column(columna, columna, ancho)
    hoja.freeze_panes(1, 0)
    ultima = len(COLUMNAS_PAQUETES) - 1
    fila = 1
    for item in resumen_propuestas(propuestas):
        n, ab = item["n_propuesta"], item["ab_benef"]
        # Cabecera del paquete
        hoja.set_row(fila, 20)
        for columna in range(ultima + 1):
            hoja.write_blank(fila, columna, None, formatos["paquete"])
        _escribir(hoja, fila, 0, n, formatos["paquete"])
        _escribir(hoja, fila, 1, ab, formatos["paquete"])
        _escribir(hoja, fila, 2, item["tipo_benef"], formatos["paquete"])
        _escribir(hoja, fila, 3, item["benef"], formatos["paquete"])
        hoja.write(fila, 4, "PAQUETE", formatos["paquete"])
        hoja.write(fila, 11, "Neto a pagar", formatos["paquete_derecha"])
        hoja.write_number(fila, 12, item["neto"], formatos["paquete_moneda"])
        _escribir(hoja, fila, 13, item["grupo"], formatos["paquete"])
        _escribir(hoja, fila, 14, item.get("observaciones"), formatos["paquete"])
        _escribir(hoja, fila, 15, item.get("buscar_por"), formatos["paquete"])
        _escribir(hoja, fila, 16, item.get("ab_e1"), formatos["paquete"])
        _escribir(hoja, fila, 17, item.get("campo_e1"), formatos["paquete"])
        _escribir(hoja, fila, 18, item.get("accion"), formatos["paquete"])
        _escribir(hoja, fila, 19, item.get("id_pago"), formatos["paquete"])
        fila += 1

        secciones = (
            ("CUENTAS POR COBRAR", "A descontar", [f for f in item["filas"] if f["tipo"] == COBRAR],
             "Total a descontar", item["a_descontar"], formatos["cobrar"]),
            ("CUENTA POR PAGAR", "A pagar", [f for f in item["filas"] if f["tipo"] == PAGAR],
             "Total a pagar", item["a_pagar"], formatos["pagar"]),
        )
        for titulo, movimiento, filas, rotulo_total, total, formato_titulo in secciones:
            if not filas:
                continue
            hoja.set_row(fila, None, None, {"level": 1})
            for columna in range(ultima + 1):
                hoja.write_blank(fila, columna, None, formato_titulo)
            hoja.write(fila, 4, titulo, formato_titulo)
            fila += 1
            for f in filas:
                hoja.set_row(fila, None, None, {"level": 1})
                corredor = f["corredor"] if not vacio(f["corredor"]) else "DIRECTO"
                valores = [n, ab, f["tipo_benef"], item["benef"], movimiento, f["vendedor"], corredor, f["benef"],
                           f["doc"], f["tipo_doc"], f["fecha_emision"], f["desc"]]
                for columna, valor in enumerate(valores):
                    _escribir(hoja, fila, columna, valor, fmt_fecha=formatos["fecha"])
                _escribir(hoja, fila, 12, f["total"], fmt_moneda=formatos["moneda"])
                fila += 1
            hoja.set_row(fila, None, None, {"level": 1})
            hoja.write(fila, 11, rotulo_total, formatos["total_rotulo"])
            hoja.write_number(fila, 12, total, formatos["total_moneda"])
            fila += 1
        fila += 1  # renglón en blanco entre paquetes
    return hoja


def _hoja_detalle(libro, nombre, filas, formatos):
    """Mismas columnas que la hoja de la macro (una fila por documento), para filtrar o copiar."""
    hoja = libro.add_worksheet(nombre)
    for columna, (titulo, _campo) in enumerate(COLUMNAS_SALIDA):
        hoja.write(0, columna, titulo, formatos["encabezado"])
    for numero, fila in enumerate(filas, start=1):
        for columna, (_titulo, campo) in enumerate(COLUMNAS_SALIDA):
            if campo is None:
                continue
            _escribir(hoja, numero, columna, fila.get(campo), fmt_fecha=formatos["fecha"],
                      fmt_moneda=formatos["moneda"] if campo == "total" else None)
    anchos = [20, 8, 12, 32, 12, 32, 14, 32, 12, 8, 28, 16, 12, 14, 13, 12, 12, 24, 9, 14]
    for columna, ancho in enumerate(anchos):
        hoja.set_column(columna, columna, ancho)
    hoja.freeze_panes(1, 0)
    if filas:
        hoja.autofilter(0, 0, len(filas), len(COLUMNAS_SALIDA) - 1)


def exportar_propuestas(ruta, propuestas_24, propuestas_48, info):
    """Escribe Propuestas_Netting.xlsx.

    Hojas:
        Propuestas_24 / Propuestas_48   un bloque por AB (paquete), con lo que se descuenta y lo que se paga
        Detalle_24 / Detalle_48         una fila por documento, columnas de la macro
        Control                         fecha, archivos usados, números y avisos
    """
    import xlsxwriter

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro = xlsxwriter.Workbook(str(ruta))

    verde, rojo, azul = "#e6ecdc", "#c62828", "#1f4f9a"
    formatos = {
        "encabezado": libro.add_format({"bold": True, "bg_color": verde, "border": 1}),
        "moneda": libro.add_format({"num_format": "#,##0.00"}),
        "fecha": libro.add_format({"num_format": "dd/mm/yyyy"}),
        "paquete": libro.add_format({"bold": True, "bg_color": "#f1f4ec", "top": 2, "top_color": "#4f7a2b"}),
        "paquete_derecha": libro.add_format({"bold": True, "bg_color": "#f1f4ec", "top": 2, "top_color": "#4f7a2b",
                                             "align": "right"}),
        "paquete_moneda": libro.add_format({"bold": True, "bg_color": "#f1f4ec", "top": 2, "top_color": "#4f7a2b",
                                            "num_format": "#,##0.00"}),
        "cobrar": libro.add_format({"bold": True, "font_color": "#ffffff", "bg_color": rojo}),
        "pagar": libro.add_format({"bold": True, "font_color": "#ffffff", "bg_color": azul}),
        "total_rotulo": libro.add_format({"bold": True, "align": "right"}),
        "total_moneda": libro.add_format({"bold": True, "num_format": "#,##0.00", "top": 1}),
    }

    _hoja_paquetes(libro, "Propuestas_24", propuestas_24, formatos)
    _hoja_paquetes(libro, "Propuestas_48", propuestas_48, formatos)
    _hoja_detalle(libro, "Detalle_24", propuestas_24, formatos)
    _hoja_detalle(libro, "Detalle_48", propuestas_48, formatos)

    control = libro.add_worksheet("Control")
    control.write(0, 0, "Dato", formatos["encabezado"])
    control.write(0, 1, "Valor", formatos["encabezado"])
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
