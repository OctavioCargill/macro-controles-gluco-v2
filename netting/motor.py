"""Reglas de Netting replicadas de Macro_Propuesta.xlsm ("modo compatibilidad").

Cada función indica el procedimiento VBA del que sale. La macro trabaja moviendo el cursor de
Excel fila por fila; acá se recorren listas de la misma forma para obtener exactamente las
mismas propuestas, incluidas algunas rarezas de la macro. Cuando una de esas rarezas cambia el
resultado, se deja un aviso para que se pueda revisar (ver `Avisos`).
"""

import unicodedata
from dataclasses import dataclass, field

from netting.calendario import dias_a_pagar
from netting.cargas import a_fecha, a_numero, a_numero_si_se_puede, vacio

TIPOS_077 = ("AH", "RI", "RM", "RT", "X@", "X&")
COMISIONES = ("Comisiónes", "Varios-Comisión")
SALTEAN_COBRAR = ("CORREDOR-CESION", "VENDEDOR-CESION", "CORREDOR-DIRECTO", "CARGILL-AUTOMATICO")

CORREDOR = "CORREDOR"
VENDEDOR = "VENDEDOR"
CORREDOR_DIRECTO = "CORREDOR-DIRECTO"
CORREDOR_CESION = "CORREDOR-CESION"
VENDEDOR_CESION = "VENDEDOR-CESION"
CARGILL = "CARGILL"
TIPOS_BENEFICIARIO = (CARGILL, CORREDOR, CORREDOR_DIRECTO, VENDEDOR, CORREDOR_CESION, VENDEDOR_CESION)

PAGAR = "PAGAR"
COBRAR = "COBRAR"


@dataclass
class Avisos:
    """Mensajes para el usuario, separados por gravedad."""

    info: list = field(default_factory=list)
    revisar: list = field(default_factory=list)

    def agregar(self, mensaje, revisar=False):
        (self.revisar if revisar else self.info).append(mensaje)


# ---------------------------------------------------------------- comparaciones y orden "de Excel"

def igual(a, b) -> bool:
    """`=` de VBA entre dos celdas: número contra texto nunca es igual; vacío es igual a 0 y a ""."""
    if a == "" or b == "":
        return vacio(a) and vacio(b)
    a_num = isinstance(a, (int, float)) and not isinstance(a, bool)
    b_num = isinstance(b, (int, float)) and not isinstance(b, bool)
    if a_num != b_num:
        return False
    return a == b


def _texto_orden(texto: str):
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    ).casefold()
    # Excel ignora guiones y apóstrofos al ordenar texto (si no, empatan y va primero el que no los tiene).
    return sin_acentos.replace("-", "").replace("'", ""), sin_acentos


def clave_excel(valor, texto_como_numero=False):
    """Orden ascendente de Excel: números, después texto (sin distinguir mayúsculas), vacíos al final."""
    if valor is None or valor == "":
        return (2, 0, ("", ""))
    if isinstance(valor, bool):
        return (1, 0, _texto_orden(str(valor)))
    if isinstance(valor, (int, float)):
        return (0, float(valor), ("", ""))
    if hasattr(valor, "toordinal"):
        return (0, valor.toordinal() + getattr(valor, "hour", 0) / 24, ("", ""))
    texto = str(valor)
    if texto_como_numero:
        numero = a_numero_si_se_puede(texto)
        if isinstance(numero, (int, float)):
            return (0, float(numero), ("", ""))
    return (1, 0, _texto_orden(texto))


def ordenar(filas, *campos):
    """Sort de Excel sobre la hoja: estable, por varias claves. campos: (nombre, texto_como_numero)."""
    filas.sort(key=lambda f: tuple(clave_excel(f[c], n) for c, n in campos))


def _texto_celda(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def buscar(filas, campo, objetivo):
    """Range(col).Find(objetivo): primera fila cuyo texto CONTIENE el buscado, sin distinguir mayúsculas.

    Devuelve el índice o None. Ojo: puede devolver una fila que solo contiene el texto
    (p. ej. busca "AGRO SA" y encuentra "NUEVA AGRO SA"); la macro después recorre mientras la
    celda sea exactamente igual, así que en ese caso no toma ninguna fila.
    """
    buscado = _texto_celda(objetivo).casefold()
    if buscado == "":
        return None
    for indice, fila in enumerate(filas):
        if buscado in _texto_celda(fila[campo]).casefold():
            return indice
    return None


def _contrato_texto(valor):
    return _texto_celda(valor)


# ---------------------------------------------------------------- Histórico (abrir_bases)

def preparar_historico(registros, hoy, feriados, avisos: Avisos):
    """Abrir_Historico: eliminar_pendientes → calcula_dias → calcular_beneficiarios."""
    filas = []
    pendientes = 0
    sin_fecha = 0
    for registro in registros:
        if registro.get("dias_origen") in ("PENDIENTE", "X"):
            pendientes += 1
            continue
        fila = dict(registro)
        if fila.get("fecha_pago") is None:
            sin_fecha += 1
        fila["dias"] = dias_a_pagar(fila.get("fecha_pago"), hoy, feriados)
        fila["tipo_benef"] = clasificar_beneficiario(fila)
        filas.append(fila)
    if pendientes:
        avisos.agregar(f"Histórico: se descartaron {pendientes} documentos marcados PENDIENTE o X.")
    if sin_fecha:
        avisos.agregar(
            f"Histórico: {sin_fecha} documentos sin fecha de pago; como en la macro cuentan como 0 días "
            "(entran en 24 hs).",
            revisar=True,
        )
    return filas


def clasificar_beneficiario(fila):
    """calcular_beneficiarios: compara NOMBRES (no códigos AB). Gana la primera condición que se cumple."""
    corredor, vendedor = fila["corredor"], fila["vendedor"]
    cobrador, cesion = fila["cobrador"], fila["cesion"]
    if fila.get("usuario_anulacion") == CARGILL:
        return CARGILL
    if igual(corredor, cobrador) and vacio(cesion):
        return CORREDOR
    if igual(vendedor, cobrador) and vacio(cesion) and not vacio(corredor):
        return CORREDOR_DIRECTO
    if igual(vendedor, cobrador) and vacio(cesion) and vacio(corredor):
        return VENDEDOR
    if igual(vendedor, cobrador) and not vacio(cesion) and not vacio(corredor):
        return CORREDOR_CESION
    if igual(vendedor, cobrador) and not vacio(cesion) and vacio(corredor):
        return VENDEDOR_CESION
    # Ninguna condición: la macro deja lo que ya había en la columna F ("Usuario anulacion").
    return fila.get("usuario_anulacion", "")


# ---------------------------------------------------------------- 077 (abrir_bases + reordenar_077 + REPORTE_VENTAS)

def preparar_077(registros_077, registros_090, ventas, avisos: Avisos):
    filas = []
    descartados_tipo = 0
    for registro in registros_077:
        if registro["tipo"] not in TIPOS_077:
            descartados_tipo += 1
            continue
        fila = dict(registro)
        saldo = a_numero(fila["saldo"])
        fila["saldo"] = -saldo if saldo is not None else (0.0 if fila["saldo"] == "" else fila["saldo"])
        fila["nro"] = a_numero_si_se_puede(fila["nro"])
        fila["fecha"] = a_fecha(fila["fecha"]) if fila["fecha"] != "" else None
        fila["ag"] = ""
        filas.append(fila)

    # Cruce con el 090: BUSCARV(Contrato; '090'!A:A; 0). Si no está, se borra.
    contratos_090 = {}
    for registro in registros_090:
        clave = _clave_buscarv(registro["contrato"])
        if clave is not None and clave not in contratos_090:
            contratos_090[clave] = registro["contrato"]
    cruzadas, sin_contrato = [], 0
    for fila in filas:
        clave = _clave_buscarv(fila["contrato"])
        if clave is None or clave not in contratos_090:
            sin_contrato += 1
            continue
        fila["ag"] = contratos_090[clave]
        cruzadas.append(fila)

    # Se agregan las compensas de ventas al final (no pasan por el cruce con el 090).
    for venta in ventas:
        cruzadas.append({
            "cod_bp": "VENTA", "cod_cliente": venta["ab_cliente"], "cliente": venta["cliente"],
            "tipo": venta["tipo"], "nro": venta["nro"], "detalle": "", "fecha": None,
            "saldo": venta["importe"], "contrato": "", "corredor": venta["corredor"],
            "ab_corredor": venta["ab_corredor"], "ag": "", "fila_origen": venta["fila_origen"],
        })

    avisos.agregar(
        f"077: {len(registros_077)} documentos leídos; {descartados_tipo} de otros tipos, "
        f"{sin_contrato} sin contrato en el 090; quedan {len(cruzadas) - len(ventas)} + {len(ventas)} ventas."
    )
    return cruzadas


def _clave_buscarv(valor):
    """BUSCARV exacto: sin distinguir mayúsculas; número y texto no coinciden entre sí."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return ("n", float(valor))
    return ("t", str(valor).casefold())


# ---------------------------------------------------------------- propuestas (propuesta_24 / propuesta_48)

@dataclass
class Estado:
    """Lo que en la macro queda guardado en las hojas entre botones."""

    t077: list
    t090: list
    ultimo_numero: int
    solo_24: set
    avisos: Avisos


def _fila_pagar(origen, primera, ventana, vendedor_de_primera=False):
    total = a_numero(origen["total"])
    fila = {
        "tipo_benef": origen["tipo_benef"],
        "tipo": PAGAR,
        "ab_corredor": primera["ab_corredor"],
        "corredor": primera["corredor"],
        "ab_vendedor": primera["ab_vendedor"] if vendedor_de_primera else origen["ab_vendedor"],
        "vendedor": primera["vendedor"] if vendedor_de_primera else origen["vendedor"],
        "ab_benef": origen["ab_cesion"] if not vacio(origen["cesion"]) else primera["ab_cobrador"],
        "benef": origen["cesion"] if not vacio(origen["cesion"]) else primera["cobrador"],
        "doc": origen["doc"],
        "tipo_doc": origen["tipo_doc"],
        "desc": origen["desc"],
        "total": total,
        "fecha_emision": None,
        "contrato": origen["contrato"],
        "n_propuesta": "",
        "ventana": ventana,
        "id_largo": origen.get("id_largo", ""),
        "origen": "Histórico",
    }
    if total is None:
        fila["total"] = None
    return fila


def _fila_cobrar(doc077, tipo_benef, ab_corredor, corredor, ab_vendedor, vendedor, ab_benef, benef, contrato, ventana):
    return {
        "tipo_benef": tipo_benef,
        "tipo": COBRAR,
        "ab_corredor": ab_corredor,
        "corredor": corredor,
        "ab_vendedor": ab_vendedor,
        "vendedor": vendedor,
        "ab_benef": ab_benef,
        "benef": benef,
        "doc": doc077["nro"],
        "tipo_doc": doc077["tipo"],
        "desc": doc077["detalle"],
        "total": a_numero(doc077["saldo"]),
        "fecha_emision": doc077["fecha"],
        "contrato": contrato,
        "n_propuesta": "",
        "ventana": ventana,
        "id_largo": "",
        "origen": "Venta" if doc077.get("cod_bp") == "VENTA" else "077",
    }


def _contratos_090(estado: Estado, campo, nombre, ctto, ventana, es_vendedor):
    """Arma ctto_090 con los contratos del 090 de ese corredor/vendedor. Devuelve (x, reales)."""
    ordenar(estado.t090, (campo, False))
    inicio = buscar(estado.t090, campo, nombre)
    x = 0
    reales = []
    if inicio is not None:
        indice = inicio
        while indice < len(estado.t090) and igual(estado.t090[indice][campo], nombre):
            ctto[x] = _contrato_texto(estado.t090[indice]["contrato"])
            reales.append(ctto[x])
            x += 1
            indice += 1
        if not reales:
            _aviso_busqueda_parcial(estado, estado.t090, campo, nombre, "090")
        # En 24 hs la macro no resta 1 al terminar la búsqueda del vendedor: compara un lugar de más.
        if not (es_vendedor and ventana == "24"):
            x -= 1
    return x, reales


def _aviso_busqueda_parcial(estado, filas, campo, nombre, donde):
    if any(igual(f[campo], nombre) for f in filas):
        estado.avisos.agregar(
            f"{donde}: «{nombre}» no se encontró porque antes aparece otro nombre que lo contiene "
            "(la macro busca por coincidencia parcial). Esos documentos quedan afuera, igual que en la macro.",
            revisar=True,
        )


def _contrato_coincide(ctto, x, reales, contrato, estado, beneficiario, doc):
    objetivo = _contrato_texto(contrato)
    for indice in range(0, x + 1):
        if ctto[indice] == objetivo:
            if objetivo not in reales:
                motivo = (
                    "no tiene contrato y coincidió con un lugar vacío de la lista de contratos"
                    if objetivo == ""
                    else f"su contrato {objetivo} quedó en la lista de un beneficiario anterior"
                )
                estado.avisos.agregar(
                    f"{beneficiario}: la macro toma el documento {doc} aunque {motivo} "
                    "(rareza de la macro, se replica). Revisarlo.",
                    revisar=True,
                )
            return True
    return False


def armar_liquidaciones(hist, estado: Estado, ventana):
    """liquidaciones_24 / liquidaciones_48: documentos a pagar y, por beneficiario, los del 077 a cobrar."""
    temp = list(hist)
    if ventana == "48":
        antes = len(temp)
        temp = [f for f in temp if _texto_celda(f["ab_cobrador"]) not in estado.solo_24]
        if antes != len(temp):
            estado.avisos.agregar(f"48 hs: {antes - len(temp)} documentos de corredores que solo cobran a 24 hs quedan afuera.")
        temp = [f for f in temp if _dias(f) == 2 and f["desc"] not in COMISIONES]
        ordenar(temp, ("tipo_benef", False), ("ab_corredor", True))
    else:
        temp = [f for f in temp if not (_dias(f) > 1) and f["desc"] not in COMISIONES]
        ordenar(temp, ("tipo_benef", False), ("ab_cobrador", True))

    salida = []
    ctto = [""] * 1001   # Dim ctto_090(1000) As String: vive durante todo el procedimiento
    x = 0
    i, n = 0, len(temp)
    while i < n and not vacio(temp[i]["tipo_benef"]):
        primera = temp[i]
        cobrador, vendedor, corredor = primera["cobrador"], primera["vendedor"], primera["corredor"]

        while i < n and igual(temp[i]["cobrador"], cobrador) and (
            ventana == "48" or (igual(temp[i]["vendedor"], vendedor) and igual(temp[i]["corredor"], corredor))
        ):
            salida.append(_fila_pagar(temp[i], primera, ventana))
            i += 1

        ultima = temp[i - 1]
        tipo = ultima["tipo_benef"]
        if tipo in SALTEAN_COBRAR:
            continue

        reales = []
        if tipo == CORREDOR:
            x, reales = _contratos_090(estado, "corredor", corredor, ctto, ventana, es_vendedor=False)
        elif tipo == VENDEDOR:
            x, reales = _contratos_090(estado, "vendedor", vendedor, ctto, ventana, es_vendedor=True)

        if tipo == CORREDOR:
            ordenar(estado.t077, ("corredor", False), ("fecha", False))
            inicio = buscar(estado.t077, "corredor", corredor)
            if inicio is not None:
                j = inicio
                if not igual(estado.t077[j]["corredor"], corredor):
                    _aviso_busqueda_parcial(estado, estado.t077, "corredor", corredor, "077")
                while j < len(estado.t077) and igual(estado.t077[j]["corredor"], corredor):
                    doc = estado.t077[j]
                    if doc["cod_bp"] == "VENTA" and ventana == "24":
                        encontrado = True
                    else:
                        encontrado = _contrato_coincide(ctto, x, reales, doc["contrato"], estado, corredor, doc["nro"])
                    if encontrado and doc["ag"] != "YA USADA":
                        salida.append(_fila_cobrar(
                            doc, CORREDOR, primera["ab_corredor"], corredor, doc["cod_cliente"], doc["cliente"],
                            primera["ab_corredor"], corredor, "", ventana,
                        ))
                        doc["ag"] = "YA USADA"
                    j += 1
        elif tipo == VENDEDOR:
            ordenar(estado.t077, ("cliente", False), ("fecha", False))
            inicio = buscar(estado.t077, "cliente", vendedor)
            if inicio is not None:
                j = inicio
                if not igual(estado.t077[j]["cliente"], vendedor):
                    _aviso_busqueda_parcial(estado, estado.t077, "cliente", vendedor, "077")
                while j < len(estado.t077) and igual(estado.t077[j]["cliente"], vendedor):
                    doc = estado.t077[j]
                    if vacio(doc["corredor"]):
                        encontrado = _contrato_coincide(ctto, x, reales, doc["contrato"], estado, vendedor, doc["nro"])
                        # En 24 hs la macro no mira si el documento ya se usó; en 48 hs sí.
                        if encontrado and (ventana == "24" or doc["ag"] != "YA USADA"):
                            if doc["ag"] == "YA USADA":
                                estado.avisos.agregar(
                                    f"{vendedor}: el documento {doc['nro']} ya estaba usado en otra propuesta y la "
                                    "macro lo vuelve a tomar (24 hs no lo controla).",
                                    revisar=True,
                                )
                            salida.append(_fila_cobrar(
                                doc, VENDEDOR, primera["ab_corredor"], corredor, primera["ab_vendedor"], vendedor,
                                primera["ab_cobrador"], cobrador, doc["cliente"], ventana,
                            ))
                            doc["ag"] = "YA USADA"
                    j += 1
                ctto[:] = [""] * 1001  # Erase ctto_090
    if i < n and vacio(temp[i]["tipo_benef"]):
        resto = n - i
        estado.avisos.agregar(
            f"{ventana} hs: {resto} documentos sin tipo de beneficiario (no coinciden los nombres) quedan afuera.",
            revisar=True,
        )
    return salida


def armar_comisiones(hist, estado: Estado, ventana):
    """Comisiones_24 / Comisiones_48: comisiones a pagar, agrupadas por beneficiario del pago."""
    if ventana == "48":
        temp = [f for f in hist if _dias(f) == 2 and f["desc"] in COMISIONES]
    else:
        temp = [f for f in hist if not (_dias(f) > 1) and f["desc"] in COMISIONES]
    ordenar(temp, ("tipo_benef", False), ("ab_corredor", True))

    salida, salteados = [], []
    i, n = 0, len(temp)
    while i < n and not vacio(temp[i]["tipo_benef"]):
        primera = temp[i]
        while i < n and igual(temp[i]["cobrador"], primera["cobrador"]):
            salida.append(_fila_pagar(temp[i], primera, ventana, vendedor_de_primera=(ventana == "24")))
            i += 1
        if ventana == "48":
            # La macro de 48 hs avanza una fila de más al terminar cada beneficiario.
            if i < n and not vacio(temp[i]["tipo_benef"]):
                salteados.append(temp[i])
            i += 1
    if salteados:
        docs = ", ".join(str(f["doc"]) for f in salteados[:10])
        estado.avisos.agregar(
            f"Comisiones 48 hs: la macro saltea {len(salteados)} comisión(es) (la primera de cada beneficiario "
            f"desde el segundo): {docs}{'…' if len(salteados) > 10 else ''}. Se replica para comparar.",
            revisar=True,
        )
    return salida


def _dias(fila):
    valor = fila.get("dias", 0)
    return valor if isinstance(valor, (int, float)) else 0


def numerar(propuestas, estado: Estado, ventana):
    """Bloque CONTAR CANTIDAD de propuesta_24_hs / propuesta_48_hs: asigna N_PROPUESTA."""
    campo = "ab_benef" if ventana == "24" else "benef"
    n = len(propuestas)

    def valor(r, clave):
        return propuestas[r][clave] if 0 <= r < n else ""

    cont = estado.ultimo_numero + 1
    r = 0
    while r < n and not vacio(propuestas[r][campo]):
        cliente = propuestas[r][campo]
        while r < n and igual(propuestas[r][campo], cliente):
            tipo = propuestas[r]["tipo_benef"]
            if tipo in (CORREDOR, VENDEDOR):
                anterior = valor(r - 1, "tipo_doc") if r > 0 else "TIPO de Docu"
                if (ventana == "24" and anterior != "C0" and propuestas[r]["tipo_doc"] == "C0"
                        and igual(cliente, valor(r + 1, campo))):
                    propuestas[r]["n_propuesta"] = cont + 1
                    r += 1
                    break
                propuestas[r]["n_propuesta"] = cont
                r += 1
            else:
                mismo_siguiente = (
                    igual(valor(r + 1, "corredor"), propuestas[r]["corredor"])
                    and igual(valor(r + 1, "vendedor"), propuestas[r]["vendedor"])
                )
                propuestas[r]["n_propuesta"] = cont
                r += 1
                if not (tipo in (CORREDOR_DIRECTO, CORREDOR_CESION) and mismo_siguiente):
                    break
        cont += 1
    sin_numero = n - r
    if sin_numero:
        estado.avisos.agregar(
            f"{ventana} hs: {sin_numero} filas quedaron sin número de propuesta porque falta el beneficiario "
            "en una fila (la macro corta ahí).",
            revisar=True,
        )
    estado.ultimo_numero = cont - 1


def armar_propuestas(hist, estado: Estado, ventana):
    """Botón PROPUESTA 24/48 HS completo: liquidaciones + comisiones + numeración."""
    propuestas = armar_liquidaciones(hist, estado, ventana)
    propuestas += armar_comisiones(hist, estado, ventana)
    desde = estado.ultimo_numero + 1
    numerar(propuestas, estado, ventana)
    sin_total = [p for p in propuestas if p["total"] is None]
    if sin_total:
        estado.avisos.agregar(
            f"{ventana} hs: {len(sin_total)} documentos con importe vacío o no numérico.", revisar=True
        )
    return propuestas, desde
