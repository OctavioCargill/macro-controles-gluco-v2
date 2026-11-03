"""Controles de liberación replicados de Macro_Controles_Netting_y_Compensa.xlsb.

Cada función indica el procedimiento VBA del que sale (módulos abrir_bases, Module1, Module2,
output_e1). Igual que en Netting, se recorren las filas como lo hace la macro para llegar al mismo
resultado; los resultados de cada control se guardan con los mismos textos que escribe la macro
en las columnas T a AA de la hoja Propuestas.
"""

from dataclasses import dataclass, field

from netting.cargas import a_numero, vacio
from netting.motor import Avisos, igual, ordenar

NO_SE_ENCONTRO = "NO SE ENCONTRO"
OK = "OK"

# Columna Z (CONTROL)
LIBERAR = "LIBERAR"
MANUAL = "MANUAL"
COMPENSA_LIBERAR = "COMPENSA-LIBERAR"
COMPENSA_MANUAL = "COMPENSA-MANUAL"
LIBERACION_MANUAL = "LIBERACION MANUAL"
A_LIBERAR_EN_E1 = (LIBERAR, LIBERACION_MANUAL)
# Estados del pago en E1 que ya están liberados: A (Liberado) y P (Transmitido a A9)
ESTADOS_LIBERADOS = ("A", "P")

CONTROLES = (
    ("control_montos", "Control montos"),        # T
    ("control_tipo", "Control tipo doc"),        # U
    ("cronologia", "Cronología de pago"),        # V
    ("monto_liberar", "Monto por liberar"),      # W
    ("devengados", "Documentos devengados"),     # X
    ("permuta", "Permuta"),                      # Y
)


def _texto(valor):
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return "" if valor is None else str(valor).strip()


def _num(valor):
    numero = a_numero(valor)
    return 0.0 if numero is None else numero


# ---------------------------------------------------------------- 020 (abrir_bases: después de pegar el 020)

def preparar_020(filas, config):
    """Ordena por ID / concepto / documento, junta las compensas Q4/QJ repetidas e invierte el signo
    de los documentos de cobro. Devuelve una lista nueva."""
    t020 = [dict(f) for f in filas]
    ordenar(t020, ("id", False), ("concepto", False), ("nro", False))

    # Q4 / QJ: si el siguiente renglón es el mismo ID, documento y concepto, se suman y se borra uno.
    # (Como en la macro, con tres o más repetidos solo quedan sumados los dos últimos.)
    monto = 0.0
    i = 0
    while i < len(t020) and not vacio(t020[i]["concepto"]):
        fila = t020[i]
        if fila["concepto"] in ("Q4", "QJ"):
            siguiente = t020[i + 1] if i + 1 < len(t020) else None
            if siguiente is not None and igual(fila["id"], siguiente["id"]) and igual(fila["nro"], siguiente["nro"]) \
                    and igual(fila["concepto"], siguiente["concepto"]):
                monto = _num(fila["importe"]) + _num(siguiente["importe"])
                del t020[i]
                continue
            if monto != 0:
                fila["importe"] = monto
                monto = 0.0
        i += 1

    ordenar(t020, ("id", False), ("fecha_doc", False))
    negativos = set(config.get("tipos_signo_negativo", []))
    for fila in t020:
        if vacio(fila["concepto"]):
            break
        if fila["concepto"] in negativos:
            fila["importe"] = -_num(fila["importe"])
    return t020


# ---------------------------------------------------------------- CONTROL (Module1.control)

@dataclass
class ResultadoControl:
    propuestas: list
    avisos: Avisos = field(default_factory=Avisos)


def _buscar_doc_020(t020, n_doc, tipo_doc):
    """Find + FindNext de la macro sobre la columna G (desde arriba) hasta que coinciden documento y tipo."""
    orden = range(len(t020))
    buscado = _texto(n_doc).casefold()
    if not buscado:
        return None
    for indice in orden:
        fila = t020[indice]
        if buscado in _texto(fila["nro"]).casefold() and igual(fila["nro"], n_doc) and igual(fila["concepto"], tipo_doc):
            return indice
    return None


def _buscar_parcial(filas, campo, objetivo):
    """Range(col).Find(valor): primera fila (desde arriba) cuyo texto CONTIENE el buscado.

    Ojo, como en la macro: el documento 907 también encuentra al 9070.
    """
    buscado = _texto(objetivo).casefold()
    if not buscado:
        return None
    for indice, fila in enumerate(filas):
        if buscado in _texto(fila[campo]).casefold():
            return indice
    return None


def _grupo(propuestas, inicio, clave):
    fin = inicio
    while fin < len(propuestas) and igual(propuestas[fin][clave], propuestas[inicio][clave]):
        fin += 1
    return fin


def _poner(filas, campo, valor):
    for fila in filas:
        fila[campo] = valor


def controlar(propuestas, t020, t067, config) -> ResultadoControl:
    for fila in propuestas:
        fila.update({"id": "", "estado_e1": "", "control": "", "estado_ne": ""})
        for campo, _ in CONTROLES:
            fila[campo] = ""
    avisos = Avisos()

    _asignar_ids(propuestas, t020)
    _verificar_documentos(propuestas, t020, t067, config)
    _revisar_permuta(propuestas, t020)
    _control_errores(propuestas)
    _estados(propuestas, config)

    sin_id = {f["n_propuesta"] for f in propuestas if f["id"] == NO_SE_ENCONTRO}
    if sin_id:
        avisos.agregar(
            f"{len(sin_id)} propuesta(s) sin ID de netting en el 020 (no se netearon en E1 o el 020 no cubre "
            f"esa fecha): N° {', '.join(map(str, sorted(sin_id, key=str)[:10]))}.",
            revisar=True,
        )
    return ResultadoControl(propuestas, avisos)


def _asignar_ids(propuestas, t020):
    """El ID sale del primer documento de cada propuesta encontrado en el 020 (mismo N° y tipo)."""
    i, n = 0, len(propuestas)
    while i < n and not vacio(propuestas[i]["doc"]):
        indice = _buscar_doc_020(t020, propuestas[i]["doc"], propuestas[i]["tipo_doc"])
        id_netting = t020[indice]["id"] if indice is not None else NO_SE_ENCONTRO
        estado = t020[indice]["estado"] if indice is not None else NO_SE_ENCONTRO
        fin = _grupo(propuestas, i, "n_propuesta")
        for fila in propuestas[i:fin]:
            fila["id"] = id_netting
            fila["estado_e1"] = estado
        i = fin


def _verificar_documentos(propuestas, t020, t067, config):
    """verifica_Doc_pagar + verifica_pagos_cronologicos + verifica_cuenta_K_0 + revisar_doc_devengados."""
    r, n = 0, len(propuestas)
    while r < n and not vacio(propuestas[r]["id"]):
        if propuestas[r]["id"] == NO_SE_ENCONTRO:
            r += 1
            continue
        id_netting = propuestas[r]["id"]
        fin = _grupo(propuestas, r, "id")
        grupo = propuestas[r:fin]
        temp = [dict(fila, ok=False) for fila in t020 if igual(fila["id"], id_netting)]

        for fila in grupo:
            indice = _buscar_parcial(temp, "nro", fila["doc"])
            if indice is not None:
                temp[indice]["ok"] = True
                monto, importe = round(_num(fila["total"]), 2), round(_num(temp[indice]["importe"]), 2)
                if monto == importe:
                    fila["control_montos"] = OK
                elif monto < importe:
                    fila["control_montos"] = "MONTO - MENOR"
                else:
                    fila["control_montos"] = "MONTO - MAYOR"
                fila["control_tipo"] = OK if igual(fila["tipo_doc"], temp[indice]["concepto"]) else "ERROR TIPO DE DOCUMENTO"
            else:
                fila["control_montos"] = fila["control_tipo"] = "NO SE ENCONTRO DOCUMENTO"
                if fila["tipo_doc"] == "L#":
                    fila["control_tipo"] = "ERROR- FALTA DOC L#"

        # Cronología: si un documento no se pagó, los que siguen tampoco tienen que estar pagados.
        k = 0
        while k < len(grupo):
            if grupo[k]["control_montos"] == OK:
                k += 1
            elif k + 1 < len(grupo) and grupo[k + 1]["control_montos"] == OK:
                _poner(grupo, "cronologia", "ERROR CRONOLOGIA")
                break
            else:
                k += 1

        if grupo[0]["cronologia"] == "ERROR CRONOLOGIA":
            r = fin
            continue
        _poner(grupo, "cronologia", OK)
        _poner(grupo, "monto_liberar", OK)
        revisar = sum(1 for fila in grupo if fila["control_montos"] != OK)

        if revisar:
            # Quedaron documentos sin pagar: la cuenta K del 067 no tiene que tener plata por liberar.
            for linea in (f for f in t067 if igual(f["id"], id_netting)):
                if _texto(linea["letra"]) == "K":
                    valor = "OK-S/PARA LIBERAR" if _num(linea["importe"]) == 0 else "ERROR-MONTO POR LIBERAR"
                    _poner(grupo, "monto_liberar", valor)
                    break
        if grupo[0]["monto_liberar"] == "ERROR-MONTO POR LIBERAR":
            r = fin
            continue

        _revisar_devengados(grupo, temp, config)
        if grupo[0]["devengados"] == "":
            _poner(grupo, "devengados", OK)
        r = fin


def _revisar_devengados(grupo, temp, config):
    """Documentos de cobro del netting en E1 que no estaban en la propuesta: sus facturas asociadas
    tienen que ser descuentos de la propuesta."""
    docs_no_l = [_texto(f["doc"]) for f in grupo if f["tipo_doc"] != "L#"]
    cobros = set(config.get("documentos_cobro", []))
    for fila in temp:
        marca = OK if fila["ok"] else fila.get("ab_corredor")
        if vacio(marca):
            break  # la macro recorre la columna A del 020 (Corredor) hasta la primera vacía
        if fila["ok"] or fila["concepto"] not in cobros:
            continue
        if not docs_no_l:
            grupo[0]["devengados"] = "ERROR-DOC NO ASIG/PROPUESTA"
            continue
        for asociada in fila.get("asociadas", []):
            if _texto(asociada) not in docs_no_l:
                _poner(grupo, "devengados", "ERROR DOC DEVENGADOS")
                return


def _revisar_permuta(propuestas, t020):
    vistos = set()
    for fila in propuestas:
        id_netting = fila["id"]
        if fila["accion"] != "PERMUTA" or id_netting in (NO_SE_ENCONTRO, "") or id_netting in vistos:
            continue
        vistos.add(id_netting)
        linea = next((f for f in t020 if igual(f["id"], id_netting)), None)
        if linea is None:
            continue
        valor = OK if _texto(linea["permuta"]).upper() == "S" else "ERROR PERMUTA"
        _poner([f for f in propuestas if igual(f["id"], id_netting)], "permuta", valor)


def _control_errores(propuestas):
    r, n = 0, len(propuestas)
    while r < n and not vacio(propuestas[r]["id"]):
        if propuestas[r]["id"] == NO_SE_ENCONTRO:
            propuestas[r]["control"] = NO_SE_ENCONTRO
            r += 1
            continue
        fin = _grupo(propuestas, r, "id")
        grupo = propuestas[r:fin]
        errores, compensa = 0, False
        for fila in grupo:
            if fila["control_montos"] != OK and fila["monto_liberar"] == "ERROR-MONTO POR LIBERAR":
                errores += 1
            if fila["control_tipo"] != OK:
                errores += 1
            if fila["cronologia"] != OK:
                errores += 1
            if fila["devengados"] != OK:
                errores += 1
            if fila["permuta"] != OK and fila["accion"] == "PERMUTA":
                errores += 1
            if _texto(fila["tipo_doc"]).upper() in ("Q4", "QJ"):
                compensa = True
                break  # la macro deja de contar al encontrar la compensa
        if errores:
            valor = COMPENSA_MANUAL if compensa else MANUAL
        else:
            valor = COMPENSA_LIBERAR if compensa else LIBERAR
        _poner(grupo, "control", valor)
        r = fin


def _estados(propuestas, config):
    tabla = {str(k): v for k, v in config.get("estados", {}).items()}
    for fila in propuestas:
        estado = fila["estado_e1"]
        if estado == NO_SE_ENCONTRO or vacio(estado):
            fila["estado_ne"] = NO_SE_ENCONTRO
        else:
            clave = _texto(estado)
            fila["estado_ne"] = f"{clave} - {tabla.get(clave, '?')}"


# ---------------------------------------------------------------- resumen por paquete

def letra_estado(fila):
    return _texto(fila.get("estado_ne", "")).split("-")[0].strip()


def ya_liberado(fila):
    """Pagos ya liberados en E1 (estado A o P): no se vuelven a mandar en el Output E1.

    La macro solo sacaba del visor el estado A; P (Transmitido a A9) también está liberado."""
    return letra_estado(fila) in ESTADOS_LIBERADOS


def resumen_paquetes(propuestas, t067=None):
    paquetes, indice = [], {}
    for fila in propuestas:
        clave = (fila["ventana"], fila["n_propuesta"])
        if clave not in indice:
            indice[clave] = len(paquetes)
            paquetes.append({
                "n_propuesta": fila["n_propuesta"], "ventana": fila["ventana"], "id": fila["id"],
                "control": fila["control"], "estado_ne": fila["estado_ne"], "grupo": fila.get("grupo", ""),
                "benef": fila["benef"], "ab_benef": fila["ab_benef"], "tipo_benef": fila["tipo_benef"],
                "filas": [], "a_pagar": 0.0, "a_descontar": 0.0, "accion": fila.get("accion", ""),
            })
        paquete = paquetes[indice[clave]]
        paquete["filas"].append(fila)
        if fila.get("tipo") == "PAGAR":
            paquete["a_pagar"] += _num(fila["total"])
            if not paquete["benef"]:
                paquete["benef"] = fila["benef"]
        else:
            paquete["a_descontar"] += _num(fila["total"])
    for paquete in paquetes:
        paquete["neto"] = paquete["a_pagar"] + paquete["a_descontar"]
        paquete["control"] = paquete["filas"][0]["control"]
        paquete["errores"] = [
            (fila["doc"], fila["tipo_doc"], titulo, fila[campo])
            for fila in paquete["filas"] for campo, titulo in CONTROLES
            if fila[campo] not in (OK, "", "OK-S/PARA LIBERAR")
        ]
        paquete["lineas_067"] = [l for l in (t067 or []) if igual(l["id"], paquete["id"])]
    return paquetes


def liberar_manual(paquete):
    """Botón «Aprobar» del visor: el analista revisó y lo libera igual (no aplica sin ID)."""
    if paquete["id"] in (NO_SE_ENCONTRO, ""):
        raise ValueError("No se puede liberar un ID no encontrado.")
    _poner(paquete["filas"], "control", LIBERACION_MANUAL)
    paquete["control"] = LIBERACION_MANUAL


def filas_output_e1(paquetes):
    """output_e1: ID, letra del estado y «SECUNDARIA», sin repetir, para LIBERAR y LIBERACIÓN MANUAL."""
    vistas, filas = set(), []
    for paquete in paquetes:
        if paquete["control"] not in A_LIBERAR_EN_E1 or ya_liberado(paquete["filas"][0]):
            continue
        clave = (_texto(paquete["id"]), letra_estado(paquete["filas"][0]))
        if clave in vistas:
            continue
        vistas.add(clave)
        filas.append((paquete["id"], clave[1], "SECUNDARIA"))
    return filas
