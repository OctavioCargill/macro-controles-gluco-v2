"""Compara los datos de una liquidación con lo que muestra la captura de la Power App y con su factura.

Para cada dato de la app:
- Captura: se busca la etiqueta (por ejemplo «Total a pagar») y se lee el valor que está a su derecha o debajo,
  como se ve en un formulario. Si la etiqueta no aparece, se busca el valor en toda la captura.
- Factura: se busca el importe o el código en todo el texto del PDF; para el total también se lee el renglón
  que dice «total» / «neto a pagar» para poder mostrar cuánto dice la factura cuando no coincide.

Resultado por dato: COINCIDE, DISTINTO (con el valor que se leyó) o NO SE VE (no aparece en la captura o factura).
"""

from dataclasses import dataclass, field

from validacion import normalizar as N

COINCIDE = "coincide"
DISTINTO = "distinto"
NO_SE_VE = "no_se_ve"

TIPO_IMPORTE = "importe"
TIPO_NUMERO = "numero"
TIPO_CODIGO = "codigo"
TIPO_FECHA = "fecha"
TIPO_TEXTO = "texto"

# Otras formas en que la Power App o la factura pueden nombrar el mismo dato
ALIAS = {
    "Total a pagar": ["Total a pagar", "Total", "Importe total", "Neto a pagar", "Importe a pagar"],
    "Nro. Legal (COE)": ["Nro. Legal (COE)", "Nro. Legal", "Nro Legal", "Numero Legal", "COE", "Nro. COE"],
    "Nro. Doc. Interno": ["Nro. Doc. Interno", "Nro Doc Interno", "Doc. Interno", "Numero Doc", "Nro. Documento"],
    "Tipo liquidación": ["Tipo liquidación", "Tipo de liquidación", "Tipo Liquidacion"],
    "Forma de Pago": ["Forma de Pago", "Condición de Pago", "Condicion de pago"],
    "Fecha de Pago": ["Fecha de Pago", "Fecha Pago"],
    "Kilos": ["Kilos", "Kg", "Cantidad", "Unidades"],
    "Tipo Documento": ["Tipo Documento", "Tipo Doc", "Tipo de Documento"],
    "Estado Liq.": ["Estado Liq.", "Estado Liq", "Estado de liquidación", "Estado"],
}
ETIQUETAS_TOTAL_FACTURA = ("neto a pagar", "total a pagar", "importe a pagar", "importe neto", "total neto",
                           "pago segun condiciones", "importe total", "total")


@dataclass
class Campo:
    titulo: str
    valor: str
    tipo: str = TIPO_TEXTO
    alias: list = field(default_factory=list)
    alternativas: list = field(default_factory=list)   # otras formas válidas del mismo valor (ej. descripción)


@dataclass
class Resultado:
    titulo: str
    valor_app: str
    estado: str
    leido: str = ""
    nota: str = ""


@dataclass
class Validacion:
    origen: str                       # "captura" o "factura"
    archivo: str
    resultados: list
    renglones_leidos: int = 0

    def cantidad(self, estado):
        return sum(1 for r in self.resultados if r.estado == estado)

    @property
    def resumen(self):
        partes = [f"{self.cantidad(COINCIDE)} coinciden"]
        if self.cantidad(DISTINTO):
            partes.append(f"{self.cantidad(DISTINTO)} distintos")
        if self.cantidad(NO_SE_VE):
            partes.append(f"{self.cantidad(NO_SE_VE)} no se ven")
        return " · ".join(partes)

    @property
    def hay_diferencias(self):
        return self.cantidad(DISTINTO) > 0


def tipo_por_titulo(titulo):
    clave = N.texto(titulo)
    if "total" in clave or "importe" in clave or clave.startswith(("retencion", "percepcion")):
        return TIPO_IMPORTE
    if clave in ("kilos", "kg", "unidades"):
        return TIPO_NUMERO
    if "fecha" in clave:
        return TIPO_FECHA
    if any(p in clave for p in ("nro", "numero", "contrato", "coe", "id ")) or clave.startswith("id"):
        return TIPO_CODIGO
    return TIPO_TEXTO


def campo(titulo, valor, tipo=None, alternativas=()):
    titulo = str(titulo).rstrip(":").strip()
    alias = ALIAS.get(titulo, [titulo])
    sin_parentesis = titulo.split("(")[0].strip()
    if sin_parentesis and sin_parentesis not in alias:
        alias = alias + [sin_parentesis]
    otras = [str(a).strip() for a in alternativas if not _vacio(a) and str(a).strip() != str(valor).strip()]
    return Campo(titulo, str(valor).strip(), tipo or tipo_por_titulo(titulo), alias, otras)


def _vacio(valor):
    return str(valor).strip() in ("", "-", "$ 0,00", "nan", "None", "N/A")


# --------------------------------------------------------------------------- comparar un valor
def _iguales(campo_app, leido):
    """True si el texto leído representa el mismo valor que el de la app (o alguna de sus alternativas)."""
    if leido is None or str(leido).strip() == "":
        return False
    if campo_app.alternativas:
        for valor in [campo_app.valor] + campo_app.alternativas:
            if _iguales(Campo(campo_app.titulo, valor, campo_app.tipo), leido):
                return True
        return False
    tipo = campo_app.tipo
    if tipo in (TIPO_IMPORTE, TIPO_NUMERO):
        a, b = N.importe(campo_app.valor), N.importe(leido)
        if a is None or b is None:
            return False
        return abs(abs(a) - abs(b)) < (0.011 if tipo == TIPO_IMPORTE else 0.5)
    if tipo == TIPO_FECHA:
        a, b = N.fecha(campo_app.valor), N.fecha(leido)
        return a is not None and a == b
    if tipo == TIPO_CODIGO:
        a = N.codigo(campo_app.valor)
        if not a:
            return False
        if N.codigo(leido) == a:
            return True
        numerico = a.isdigit()
        return numerico and N.codigo(leido, ocr=True) == a
    a, b = N.texto(campo_app.valor), N.texto(leido)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 4 and (a in b or b in a) and min(len(a), len(b)) / max(len(a), len(b)) > 0.6:
        return True
    return N.parecido(a, b) >= 0.88


def _aparece(campo_app, renglones):
    """Busca el valor en cualquier renglón (o parte de renglón)."""
    if campo_app.tipo == TIPO_TEXTO and len(N.texto(campo_app.valor)) < 4:
        return None                         # «A», «SI»: aparecen en cualquier lado, no sirve buscarlos sueltos
    for renglon in renglones:
        if _iguales(campo_app, renglon.texto):
            return renglon
        # Un texto (nombre, descripción) tiene que estar entero; un número o código puede estar dentro de un renglón
        partes = _partes(renglon.texto) if campo_app.tipo != TIPO_TEXTO else _despues_de_dos_puntos(renglon.texto)
        for parte in partes:
            if _iguales(campo_app, parte):
                return renglon
    return None


def _despues_de_dos_puntos(texto_renglon):
    return [texto_renglon.split(":", 1)[1].strip()] if ":" in str(texto_renglon) else []


def _partes(texto_renglon):
    """Pedazos de un renglón donde puede estar un valor: palabras sueltas y lo que sigue a «:»."""
    texto_renglon = str(texto_renglon)
    partes = [p.strip() for p in texto_renglon.replace("|", " ").split(":") if p.strip()]
    for palabra in texto_renglon.replace(":", " ").split():
        partes.append(palabra)
    return partes


# --------------------------------------------------------------------------- captura de pantalla
def _es_etiqueta(renglon, campo_app):
    texto_renglon = N.texto(renglon.texto)
    for alias in campo_app.alias:
        etiqueta = N.texto(alias)
        if not etiqueta:
            continue
        if texto_renglon == etiqueta or N.parecido(texto_renglon, etiqueta) >= 0.88:
            return True, ""
        if texto_renglon.startswith(etiqueta + " ") and ":" in renglon.texto:
            return True, renglon.texto.split(":", 1)[1].strip()
    return False, ""


def _candidatos(etiqueta, renglones):
    """Lo que está a la derecha de la etiqueta (mismo renglón) y lo que está debajo (misma columna)."""
    derecha, debajo = [], []
    for otro in renglones:
        if otro is etiqueta:
            continue
        misma_linea = abs(otro.centro_y - etiqueta.centro_y) <= etiqueta.alto * 0.6
        if misma_linea and otro.x0 >= etiqueta.x1 - 5 and otro.x0 - etiqueta.x1 < 450:
            derecha.append((otro.x0 - etiqueta.x1, otro))
        separacion = otro.y0 - etiqueta.y1
        se_superpone = otro.x0 < etiqueta.x1 + 30 and otro.x1 > etiqueta.x0 - 30
        if -etiqueta.alto * 0.4 <= separacion < etiqueta.alto * 2.6 and se_superpone and not misma_linea:
            debajo.append((separacion + abs(otro.x0 - etiqueta.x0) * 0.1, otro))
    derecha.sort(key=lambda par: par[0])
    debajo.sort(key=lambda par: par[0])
    # En una tabla el valor puede estar en cualquier celda del renglón: se devuelven todas las de la derecha
    return [r for _, r in derecha[:8]] + [r for _, r in debajo[:1]]


def _mas_probable(campo_app, candidatos):
    """Cuando no coincide: el valor que más probablemente sea el de ese dato, para mostrarlo."""
    if campo_app.tipo in (TIPO_IMPORTE, TIPO_NUMERO):
        numericos = [c for c in candidatos if N.importe(c) is not None]
        if numericos:
            # En una tabla de retenciones el importe es la última columna
            return numericos[-1] if len(numericos) > 1 else numericos[0]
    if campo_app.tipo == TIPO_FECHA:
        fechas = [c for c in candidatos if N.fecha(c) is not None]
        if fechas:
            return fechas[0]
    return candidatos[0]


def comparar_captura(campos, renglones, archivo=""):
    """Dato por dato contra los renglones leídos de una captura de la Power App."""
    resultados = []
    etiquetas_de_otros = set()
    for campo_app in campos:
        for renglon in renglones:
            if _es_etiqueta(renglon, campo_app)[0]:
                etiquetas_de_otros.add(id(renglon))
    for campo_app in campos:
        if _vacio(campo_app.valor):
            continue
        leido, nota, estado = "", "", None
        for renglon in renglones:
            es, en_el_mismo = _es_etiqueta(renglon, campo_app)
            if not es:
                continue
            candidatos = [en_el_mismo] if en_el_mismo else []
            candidatos += [c.texto for c in _candidatos(renglon, renglones) if id(c) not in etiquetas_de_otros]
            if not candidatos:
                continue
            coincidente = next((c for c in candidatos if _iguales(campo_app, c)), None)
            if coincidente is not None:
                estado, leido = COINCIDE, coincidente
            else:
                leido = _mas_probable(campo_app, candidatos)
                estado, nota = DISTINTO, f"La Power App muestra «{leido}»"
            break
        if estado is None:
            encontrado = _aparece(campo_app, renglones)
            if encontrado is not None:
                estado, leido, nota = COINCIDE, encontrado.texto, "Encontrado en la captura (sin su etiqueta)"
            else:
                estado, nota = NO_SE_VE, "No aparece en la captura"
        resultados.append(Resultado(campo_app.titulo, campo_app.valor, estado, leido, nota))
    return Validacion("captura", archivo, resultados, len(renglones))


# --------------------------------------------------------------------------- factura PDF
def _total_de_la_factura(renglones):
    """El importe del renglón «neto a pagar» / «total» (el último que aparece, que suele ser el final)."""
    mejor = None
    for etiqueta in ETIQUETAS_TOTAL_FACTURA:
        for indice, renglon in enumerate(renglones):
            if f" {etiqueta} " not in f" {N.texto(renglon.texto)} ":     # palabra entera: «subtotal» no es «total»
                continue
            importes = [i for i in N.importes_en(renglon.texto) if abs(i) >= 1]
            texto_total = renglon.texto
            if not importes:
                # PDF escaneado: el importe es otro renglón a la derecha (o el de abajo)
                vecinos = [c for c in _candidatos(renglon, renglones) if N.importes_en(c.texto)]
                if not vecinos and indice + 1 < len(renglones):
                    vecinos = [renglones[indice + 1]]
                for vecino in vecinos:
                    importes = [i for i in N.importes_en(vecino.texto) if abs(i) >= 1]
                    if importes:
                        texto_total = f"{renglon.texto} {vecino.texto}"
                        break
            if importes:
                mejor = (texto_total, importes[-1])
        if mejor:
            return mejor
    return None


def comparar_factura(campos, renglones, archivo=""):
    """Importes y códigos de la liquidación contra el texto de la factura en PDF."""
    importes = []
    for renglon in renglones:
        importes.extend(N.importes_en(renglon.texto))
    resultados = []
    for campo_app in campos:
        if _vacio(campo_app.valor):
            continue
        if campo_app.tipo in (TIPO_IMPORTE, TIPO_NUMERO):
            buscado = N.importe(campo_app.valor)
            if buscado is None:
                continue
            tolerancia = 0.011 if campo_app.tipo == TIPO_IMPORTE else 0.5
            if any(abs(abs(i) - abs(buscado)) < tolerancia for i in importes):
                resultados.append(Resultado(campo_app.titulo, campo_app.valor, COINCIDE, campo_app.valor,
                                            "El importe figura en la factura"))
                continue
            total = _total_de_la_factura(renglones) if N.texto(campo_app.titulo).startswith("total") else None
            if total:
                resultados.append(Resultado(campo_app.titulo, campo_app.valor, DISTINTO, _formato(total[1]),
                                            f"La factura dice «{total[0]}»"))
            else:
                resultados.append(Resultado(campo_app.titulo, campo_app.valor, NO_SE_VE, "",
                                            "Ese importe no figura en la factura"))
            continue
        encontrado = _aparece(campo_app, renglones)
        if encontrado is not None:
            resultados.append(Resultado(campo_app.titulo, campo_app.valor, COINCIDE, encontrado.texto,
                                        "Figura en la factura"))
        else:
            resultados.append(Resultado(campo_app.titulo, campo_app.valor, NO_SE_VE, "", "No figura en la factura"))
    return Validacion("factura", archivo, resultados, len(renglones))


def _formato(numero):
    texto = f"{abs(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if numero < 0 else ''}$ {texto}"
