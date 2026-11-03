"""Lectura de las entradas de Liberación.

    Propuestas  del registro de Netting (data/Netting_Propuestos.xlsx) o de un Propuestas_Netting
                (hojas Detalle_24/48 de la app o Propuestas_24/48 de la macro vieja).
    020         Reporte de Pagos y Cobros (SAP BO): un renglón por documento de cada netting, con su
                ID de transacción, importe cancelado, estado del pago y facturas asociadas.
    067         Vouchers pendientes de liberación: líneas de pago de cada ID (cuenta K, importe,
                instrumento, banco y cuenta bancaria).
"""

import re
from pathlib import Path

from netting.cargas import (
    ErrorDeCarga, Lectura, _buscar_encabezado, _mapa_columnas, _valor, a_fecha, a_numero, leer_hoja, normalizar, vacio,
)
from netting.registro import HOJA_REGISTRO, NOMBRE_REGISTRO

ESTADOS_CERRADOS = ("LIBERADO", "ANULADA")


def _texto(valor):
    valor = normalizar(valor)
    return "" if valor is None else str(valor).strip()


# ---------------------------------------------------------------- 020

COLUMNAS_020 = {
    "ab_corredor": (["Corredor"], False),
    "corredor": (["Nombre Corredor"], False),
    "ab_cliente": (["Cliente"], False),
    "cliente": (["Nombre Cliente"], False),
    "id": (["ID Transaccion"], True),                              # F
    "nro": (["Nro de Documento"], True),                           # G
    "concepto": (["Concepto"], True),                              # H
    "desc_tipo": (["Descripcion Tipo de Documento"], False),
    "detalle": (["Detalle del documento"], False),
    "fecha_doc": (["Fecha Documento"], False),                     # K
    "importe": (["Importe Cancelado CON IVA"], True),              # O
    "contrato": (["Contrato"], False),
    "factura_asociada": (["Factura Asociada"], False),             # Z
    "fecha_pago": (["Fecha de pago"], False),
    "estado": (["Estado del pago"], True),                         # AD
    "nombre_estado": (["Nombre Estado del Pago"], False),
    "permuta": (["Permuta"], False),                               # AM
}


def cargar_020(ruta) -> Lectura:
    filas = leer_hoja(ruta)
    nombre = Path(ruta).name
    inicio = _buscar_encabezado(filas, ["ID Transaccion", "Nro de Documento", "Concepto"], f"020 ({nombre})")
    mapa = _mapa_columnas(filas[inicio], COLUMNAS_020, f"020 ({nombre})")
    registros = []
    for numero, fila in enumerate(filas[inicio + 1:], start=inicio + 2):
        registro = {campo: _valor(fila, indice) for campo, indice in mapa.items()}
        if all(vacio(v) for v in registro.values()):
            continue
        if vacio(registro.get("id")) and vacio(registro.get("nro" if "nro" in registro else "letra")):
            continue  # pie del reporte ("Data Refresh Date: …") u otra fila sin ID ni documento
        for campo in COLUMNAS_020:
            registro.setdefault(campo, "")
        registro["fecha_doc"] = a_fecha(registro["fecha_doc"]) if registro["fecha_doc"] != "" else None
        registro["fecha_pago"] = a_fecha(registro["fecha_pago"]) if registro["fecha_pago"] != "" else None
        # Factura Asociada viene como "907-910-913": la macro la separa por "-" (sin espacios).
        asociadas = re.sub(r"\s+", "", _texto(registro["factura_asociada"]))
        registro["asociadas"] = [normalizar(_a_entero(p)) for p in asociadas.split("-") if p != ""]
        registro["fila_origen"] = numero
        registros.append(registro)
    if not registros:
        raise ErrorDeCarga(f"020 ({nombre}): no tiene documentos.")
    return Lectura(registros, [], str(ruta))


def _a_entero(texto):
    return int(texto) if re.fullmatch(r"\d+", texto) else texto


# ---------------------------------------------------------------- 067

COLUMNAS_067 = {
    "fecha_netting": (["Fecha Generacion de Netting"], False),
    "n_x1": (["N° de X1", "Nº de X1", "N de X1"], False),
    "estado_x1": (["Estado del X1"], False),
    "ab_benef": (["Abook del Beneficiario"], False),
    "benef": (["Razon Social Beneficiario"], False),
    "instrumento": (["Instrumento del Pago"], False),
    "nombre_instrumento": (["Nombre Instrumento del Pago"], False),
    "letra": (["Letra del Instrumento de pago"], True),            # U (K = cuenta principal)
    "banco": (["Nombre BANCO"], False),
    "cuenta": (["Cuenta bancaria"], False),
    "importe": (["Importe a Pagar Moneda Local"], True),           # Y
    "validacion": (["Nombre Validaciones Coherentes"], False),
    "id": (["ID Transaction"], True),                              # AD
}


def cargar_067(ruta) -> Lectura:
    filas = leer_hoja(ruta)
    nombre = Path(ruta).name
    inicio = _buscar_encabezado(filas, ["ID Transaction", "Letra del Instrumento de pago"], f"067 ({nombre})")
    mapa = _mapa_columnas(filas[inicio], COLUMNAS_067, f"067 ({nombre})")
    registros = []
    for fila in filas[inicio + 1:]:
        registro = {campo: _valor(fila, indice) for campo, indice in mapa.items()}
        if all(vacio(v) for v in registro.values()):
            continue
        if vacio(registro.get("id")) and vacio(registro.get("nro" if "nro" in registro else "letra")):
            continue  # pie del reporte ("Data Refresh Date: …") u otra fila sin ID ni documento
        for campo in COLUMNAS_067:
            registro.setdefault(campo, "")
        registros.append(registro)
    return Lectura(registros, [], str(ruta))


# ---------------------------------------------------------------- propuestas

def _fila_propuesta(**datos):
    base = {
        "tipo_benef": "", "tipo": "", "ab_benef": "", "benef": "", "doc": "", "tipo_doc": "", "desc": "",
        "total": None, "n_propuesta": "", "accion": "", "observaciones": "", "grupo": "", "ventana": "",
        "generado": "", "fecha_proceso": "", "clave": "",
    }
    base.update(datos)
    return base


def listar_corridas(ruta_registro):
    """Corridas de netting del registro que todavía tienen documentos sin liberar.

    Devuelve [{"generado", "fecha_proceso", "ventanas": {"24": n, "48": n}}], la más reciente primero.
    """
    ruta = Path(ruta_registro)
    if not ruta.exists():
        return []
    filas = leer_hoja(ruta, HOJA_REGISTRO)
    if not filas:
        return []
    columnas = {_texto(v): i for i, v in enumerate(filas[0]) if _texto(v)}
    corridas = {}
    for fila in filas[1:]:
        estado = _texto(_valor(fila, columnas.get("Estado"))).upper()
        if estado in ESTADOS_CERRADOS:
            continue
        generado = _texto(_valor(fila, columnas.get("Generado")))
        if not generado:
            continue
        dato = corridas.setdefault(generado, {"generado": generado,
                                              "fecha_proceso": _texto(_valor(fila, columnas.get("Fecha proceso"))),
                                              "ventanas": {}})
        ventana = _texto(_valor(fila, columnas.get("Ventana"))).replace(" hs", "")
        propuesta = _texto(_valor(fila, columnas.get("N° propuesta")))
        dato["ventanas"].setdefault(ventana, set()).add(propuesta)

    def orden(item):
        from datetime import datetime
        try:
            return datetime.strptime(item["generado"], "%d/%m/%Y %H:%M")
        except ValueError:
            return datetime.min

    resultado = sorted(corridas.values(), key=orden, reverse=True)
    for dato in resultado:
        dato["ventanas"] = {v: len(p) for v, p in dato["ventanas"].items()}
    return resultado


def cargar_desde_registro(ruta_registro, generado, ventana) -> Lectura:
    """Documentos pendientes de liberar de una corrida (Generado) y ventana (24/48) del registro."""
    ruta = Path(ruta_registro)
    if not ruta.exists():
        raise ErrorDeCarga(f"No existe el registro de Netting ({ruta.name}). Primero hay que dar salida al netting.")
    filas = leer_hoja(ruta, HOJA_REGISTRO)
    columnas = {_texto(v): i for i, v in enumerate(filas[0]) if _texto(v)}
    faltan = [c for c in ("Generado", "Ventana", "N° propuesta", "N° documento", "Tipo doc", "Total") if c not in columnas]
    if faltan:
        raise ErrorDeCarga(f"{ruta.name}: faltan columnas {', '.join(faltan)}.")

    def valor(fila, nombre):
        return _valor(fila, columnas.get(nombre))

    registros = []
    for fila in filas[1:]:
        if _texto(valor(fila, "Generado")) != generado:
            continue
        if _texto(valor(fila, "Ventana")).replace(" hs", "") != str(ventana):
            continue
        if _texto(valor(fila, "Estado")).upper() in ESTADOS_CERRADOS:
            continue
        movimiento = _texto(valor(fila, "Movimiento"))
        registros.append(_fila_propuesta(
            tipo_benef=_texto(valor(fila, "Tipo beneficiario")),
            tipo="PAGAR" if movimiento.lower().startswith("a pagar") else "COBRAR",
            ab_benef=normalizar(valor(fila, "AB")),
            benef=_texto(valor(fila, "Beneficiario")),
            doc=normalizar(valor(fila, "N° documento")),
            tipo_doc=_texto(valor(fila, "Tipo doc")),
            desc=_texto(valor(fila, "Descripción")),
            total=a_numero(valor(fila, "Total")),
            n_propuesta=normalizar(valor(fila, "N° propuesta")),
            accion=_texto(valor(fila, "Acción")).upper(),
            observaciones=_texto(valor(fila, "Observaciones")),
            grupo=normalizar(valor(fila, "Grupo")),
            ventana=str(ventana),
            generado=generado,
            fecha_proceso=_texto(valor(fila, "Fecha proceso")),
            clave=_texto(valor(fila, "Clave")),
        ))
    if not registros:
        raise ErrorDeCarga(f"El registro no tiene documentos pendientes de la corrida {generado} ({ventana} hs).")
    return Lectura(registros, [], str(ruta))


COLUMNAS_PROPUESTAS = {
    "tipo_benef": (["Tipo de beneficiario"], False),
    "tipo": (["Tipo"], False),
    "ab_benef": (["AB Beneficiario"], False),
    "benef": (["Beneficiario"], False),
    "doc": (["N de Docu"], True),                       # I
    "tipo_doc": (["TIPO de Docu"], True),               # J
    "desc": (["Descripcion de Docu"], False),
    "total": (["Total"], True),                         # L
    "n_propuesta": (["N_PROPUESTA"], True),             # O
    "accion": (["COMBOBOX"], False),                    # Q
    "observaciones": (["Observaciones"], False),
    "grupo": (["GRUPOS"], False),
}


def cargar_desde_propuestas(ruta, ventana) -> Lectura:
    """Propuestas_Netting.xlsx de la app (hoja Detalle_24/48) o .xlsb de la macro (Propuestas_24/48)."""
    ruta = Path(ruta)
    ultimo_error = None
    for hoja in (f"Detalle_{ventana}", f"Propuestas_{ventana}"):
        try:
            filas = leer_hoja(ruta, hoja)
            inicio = _buscar_encabezado(filas, ["N de Docu", "N_PROPUESTA"], f"{ruta.name} ({hoja})")
        except ErrorDeCarga as exc:
            ultimo_error = exc
            continue
        mapa = _mapa_columnas(filas[inicio], COLUMNAS_PROPUESTAS, f"{ruta.name} ({hoja})")
        registros = []
        for fila in filas[inicio + 1:]:
            datos = {campo: _valor(fila, indice) for campo, indice in mapa.items()}
            if vacio(datos["doc"]) and vacio(datos["n_propuesta"]):
                break
            registros.append(_fila_propuesta(
                tipo_benef=_texto(datos.get("tipo_benef")), tipo=_texto(datos.get("tipo")),
                ab_benef=normalizar(datos.get("ab_benef")), benef=_texto(datos.get("benef")),
                doc=normalizar(datos["doc"]), tipo_doc=_texto(datos["tipo_doc"]), desc=_texto(datos.get("desc")),
                total=a_numero(datos["total"]), n_propuesta=normalizar(datos["n_propuesta"]),
                accion=_texto(datos.get("accion")).upper(), observaciones=_texto(datos.get("observaciones")),
                grupo=normalizar(datos.get("grupo")), ventana=str(ventana),
            ))
        if registros:
            return Lectura(registros, [], str(ruta))
    raise ErrorDeCarga(
        f"{ruta.name}: no se encontraron propuestas de {ventana} hs (se buscaron las hojas Detalle_{ventana} y "
        f"Propuestas_{ventana} con columnas N de Docu y N_PROPUESTA)."
        + (f" Detalle: {ultimo_error}" if ultimo_error else "")
    )


def ruta_registro_por_defecto():
    from services.auditoria import APP_DATA_PATH

    return Path(APP_DATA_PATH) / NOMBRE_REGISTRO
