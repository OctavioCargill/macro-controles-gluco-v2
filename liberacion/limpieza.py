"""Botón LIMPIAR LIQUIDACIONES PAGADAS: pasa del Histórico de controlados al Histórico de pagados
los documentos que el 020 (bajado de nuevo, desde el netting hasta la liberación) muestra pagados.

Diferencias con la macro, a propósito:
- Se mueven todas las filas del documento (CONTROLAR guarda varias por documento); la macro movía una.
- Por defecto solo se mueven los pagos liberados: estado A (Liberado) o P (Transmitido a A9); la macro
  movía todo lo del 020 y dependía de que el analista revisara antes los estados.
- Antes de tocar los archivos se guarda una copia de cada uno.
"""

import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from liberacion.cargas import cargar_020
from liberacion.motor import ESTADOS_LIBERADOS
from netting.cargas import ErrorDeCarga, a_fecha, normalizar
from netting.registro import actualizar_registro
from services.bloqueo import uso_exclusivo

COLUMNAS_EXTRA_PAGADOS = ("Fecha Netting", "Fecha Acreditación", "ID pago E1")
DESCUENTOS = {"AH", "RI", "RM", "RT", "X@", "X&", "Q4", "QJ"}


def _texto(valor):
    valor = normalizar(valor)
    return "" if valor is None else str(valor).strip()


def _clave(nro, tipo):
    return f"{_texto(nro)}{_texto(tipo)}"


@dataclass
class ResultadoLimpieza:
    documentos: list = field(default_factory=list)       # [(doc, tipo, id_pago)] movidos
    filas_movidas: int = 0
    no_encontrados: list = field(default_factory=list)   # documentos del 020 que no están en el Histórico
    omitidos_estado: list = field(default_factory=list)  # (doc, tipo, estado) que no están en A ni P
    pendientes: list = field(default_factory=list)       # (doc, tipo, fecha pago) que quedaron por pagar
    copias: list = field(default_factory=list)
    simulado: bool = True


def _hoja_y_encabezado(libro, nombre_archivo):
    hojas = [libro[n] for n in ("Historico_Controlados", "Historico") if n in libro.sheetnames] + [libro.active]
    for hoja in hojas:
        for numero, fila in enumerate(hoja.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
            titulos = [_texto(v) for v in fila]
            if "Tipo Doc" in titulos and ("Numero Doc" in titulos or "Documento" in titulos):
                return hoja, numero, titulos
    raise ErrorDeCarga(f"{nombre_archivo}: no se encontró la fila de títulos (Numero Doc / Tipo Doc).")


def _copia_de_seguridad(ruta):
    destino = ruta.with_name(f"{ruta.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}{ruta.suffix}")
    shutil.copy2(ruta, destino)
    return destino


def limpiar_pagadas(ruta_020, ruta_historico, ruta_pagados, fecha_netting: date, fecha_acreditacion: date,
                    solo_estado_a=True, ruta_registro=None, simular=False) -> ResultadoLimpieza:
    argumentos = (ruta_020, ruta_historico, ruta_pagados, fecha_netting, fecha_acreditacion, solo_estado_a,
                  ruta_registro, simular)
    if simular:
        return _limpiar_pagadas(*argumentos)
    with uso_exclusivo("limpiando liquidaciones pagadas", Path(ruta_historico).parent):
        return _limpiar_pagadas(*argumentos)


def _limpiar_pagadas(ruta_020, ruta_historico, ruta_pagados, fecha_netting, fecha_acreditacion, solo_estado_a,
                     ruta_registro, simular):
    from openpyxl import Workbook, load_workbook

    ruta_historico, ruta_pagados = Path(ruta_historico), Path(ruta_pagados)
    if ruta_historico.suffix.lower() not in (".xlsx", ".xlsm"):
        raise ErrorDeCarga(
            f"{ruta_historico.name}: sin Excel no se puede modificar un {ruta_historico.suffix}. Usá el Histórico "
            ".xlsx que genera CONTROLAR."
        )
    if ruta_pagados.exists() and ruta_pagados.suffix.lower() not in (".xlsx", ".xlsm"):
        raise ErrorDeCarga(f"{ruta_pagados.name}: el Histórico de pagados tiene que ser .xlsx.")

    resultado = ResultadoLimpieza(simulado=simular)

    # 1) Documentos pagados según el 020
    pagados_020 = {}
    for fila in cargar_020(ruta_020).filas:
        clave = _clave(fila["nro"], fila["concepto"])
        if solo_estado_a and _texto(fila["estado"]).upper() not in ESTADOS_LIBERADOS:
            resultado.omitidos_estado.append((fila["nro"], fila["concepto"], fila["estado"]))
            continue
        pagados_020.setdefault(clave, fila)

    # 2) Filas del Histórico de controlados que corresponden a esos documentos
    libro_hist = load_workbook(ruta_historico)
    hoja_hist, fila_titulos, titulos_hist = _hoja_y_encabezado(libro_hist, ruta_historico.name)
    col_doc = titulos_hist.index("Numero Doc") if "Numero Doc" in titulos_hist else titulos_hist.index("Documento")
    col_tipo = titulos_hist.index("Tipo Doc")
    col_fecha = titulos_hist.index("Fecha Pago") if "Fecha Pago" in titulos_hist else None

    a_mover, encontrados = [], set()
    for numero in range(fila_titulos + 1, hoja_hist.max_row + 1):
        valores = [hoja_hist.cell(numero, c + 1).value for c in range(len(titulos_hist))]
        if all(v in (None, "") for v in valores):
            continue
        clave = _clave(valores[col_doc], valores[col_tipo])
        if clave in pagados_020:
            a_mover.append((numero, valores, pagados_020[clave]))
            if clave not in encontrados:
                encontrados.add(clave)
                resultado.documentos.append((normalizar(valores[col_doc]), _texto(valores[col_tipo]),
                                             pagados_020[clave]["id"]))
        elif col_fecha is not None:
            fecha = a_fecha(valores[col_fecha])
            if fecha is not None and fecha.date() <= fecha_acreditacion:
                resultado.pendientes.append((normalizar(valores[col_doc]), _texto(valores[col_tipo]), fecha))
    resultado.filas_movidas = len(a_mover)
    resultado.no_encontrados = [
        (f["nro"], f["concepto"]) for clave, f in pagados_020.items()
        if clave not in encontrados and _texto(f["concepto"]) not in ("", "$B") and _texto(f["nro"]) not in ("", "0")
        and _texto(f["concepto"]) not in DESCUENTOS  # los descuentos salen del 077, no del Histórico
    ]
    if simular or not a_mover:
        libro_hist.close()
        return resultado

    # 3) Copias de seguridad
    resultado.copias.append(_copia_de_seguridad(ruta_historico))
    if ruta_pagados.exists():
        resultado.copias.append(_copia_de_seguridad(ruta_pagados))

    # 4) Agregar al Histórico de pagados (por nombre de columna)
    if ruta_pagados.exists():
        libro_pag = load_workbook(ruta_pagados)
        hoja_pag = libro_pag.active
        titulos_pag = [_texto(c.value) for c in hoja_pag[1]]
        while titulos_pag and titulos_pag[-1] == "":
            titulos_pag.pop()
    else:
        ruta_pagados.parent.mkdir(parents=True, exist_ok=True)
        libro_pag = Workbook()
        hoja_pag = libro_pag.active
        hoja_pag.title = "Historico_Pagados"
        titulos_pag = []
    for titulo in [t for t in titulos_hist if t] + list(COLUMNAS_EXTRA_PAGADOS):
        if titulo not in titulos_pag:
            titulos_pag.append(titulo)
            hoja_pag.cell(row=1, column=len(titulos_pag), value=titulo)
    posicion = {titulo: indice for indice, titulo in enumerate(titulos_pag, start=1)}
    siguiente = hoja_pag.max_row + 1
    for _numero, valores, linea_020 in a_mover:
        for titulo, valor in zip(titulos_hist, valores):
            if titulo:
                hoja_pag.cell(row=siguiente, column=posicion[titulo], value=valor)
        hoja_pag.cell(row=siguiente, column=posicion["Fecha Netting"], value=datetime.combine(fecha_netting, datetime.min.time()))
        hoja_pag.cell(row=siguiente, column=posicion["Fecha Acreditación"],
                      value=datetime.combine(fecha_acreditacion, datetime.min.time()))
        hoja_pag.cell(row=siguiente, column=posicion["ID pago E1"], value=linea_020["id"])
        siguiente += 1

    # 5) Sacar del Histórico de controlados (de abajo hacia arriba)
    for numero in sorted((n for n, _, _ in a_mover), reverse=True):
        hoja_hist.delete_rows(numero, 1)

    try:
        libro_pag.save(ruta_pagados)
        libro_hist.save(ruta_historico)
    except PermissionError as exc:
        raise PermissionError(
            "No se pudieron guardar los históricos. Si alguno está abierto en Excel, cerralo y probá de nuevo "
            f"(quedaron copias de seguridad: {', '.join(p.name for p in resultado.copias)})."
        ) from exc
    finally:
        libro_pag.close()
        libro_hist.close()

    # 6) Registro de Netting: los documentos liberados terminan el proceso
    if ruta_registro and Path(ruta_registro).exists():
        # Todo lo pagado según el 020: lo que se pagó y también los descuentos (RI, AH…) del paquete.
        movidos = set(pagados_020)

        def cambios(fila):
            if _clave(fila.get("N° documento"), fila.get("Tipo doc")) in movidos:
                return {"Estado": "LIBERADO", "Fecha liberación": fecha_acreditacion.strftime("%d/%m/%Y")}
            return None

        actualizar_registro(ruta_registro, cambios)
    resultado.simulado = False
    return resultado
