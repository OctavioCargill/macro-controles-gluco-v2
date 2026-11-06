"""Buscador del asistente: encuentra la pregunta precargada que mejor responde lo que escribió el usuario.

Sin internet ni librerías externas: normaliza el texto (minúsculas, sin acentos), saca palabras vacías,
tolera errores de tipeo (difflib) y pondera las palabras raras más que las comunes.
"""

import math
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from asistente.contenido import PREGUNTAS

PALABRAS_VACIAS = set("""
a al algo como con cual cuales cuando de del desde donde e el ella en entre es esa ese eso esta este esto hay
la las le lo los me mi no o para pero por puedo puede que se si sin sobre su sus te tengo tiene un una uno unos
y ya yo hago hacer hace sale dice qué cómo cuál quiero necesito ver tenes tenés debo deberia debería
""".split())

SINONIMOS = {
    "liberacion": "liberar", "liberado": "liberar", "liberados": "liberar", "libero": "liberar",
    "controlada": "controlar", "controladas": "controlar", "control": "controlar", "controlo": "controlar",
    "controles": "controlar", "propuesta": "propuestas", "neteo": "netting", "netear": "netting",
    "pago": "pagos", "pagadas": "pagos", "pagada": "pagos", "pagado": "pagos", "pagar": "pagos",
    "historico": "historico", "historicos": "historico", "hs": "horas", "archivo": "archivos",
    "id": "id", "ids": "id", "descuento": "descuentos", "descontar": "descuentos", "copio": "copiar",
    "copia": "copiar", "error": "error", "errores": "error", "falla": "error", "anda": "funciona",
    "feriado": "feriados", "fecha": "fecha", "fechas": "fecha", "beneficiarios": "beneficiario",
    "corredores": "corredor", "cuentas": "cuenta", "vendedores": "vendedor", "limpieza": "limpiar", "limpio": "limpiar",
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9#@&]+", " ", texto).strip()


def palabras(texto):
    resultado = []
    for palabra in normalizar(texto).split():
        if palabra in PALABRAS_VACIAS:
            continue
        resultado.append(SINONIMOS.get(palabra, palabra))
    return resultado


@dataclass
class Coincidencia:
    entrada: dict
    puntaje: float


class Buscador:
    def __init__(self, preguntas=PREGUNTAS):
        self.preguntas = list(preguntas)
        self._indice = []
        for entrada in self.preguntas:
            titulo = set(palabras(entrada["pregunta"]))
            claves = set(palabras(entrada.get("claves", "")))
            cuerpo = set(palabras(entrada["respuesta"]))
            lista = palabras(entrada["pregunta"])
            pares = set(zip(lista, lista[1:]))
            self._indice.append((entrada, titulo, claves, cuerpo, normalizar(entrada["pregunta"]), pares))
        documentos = len(self._indice)
        frecuencia = {}
        for _e, titulo, claves, cuerpo, _t, _p in self._indice:
            for palabra in titulo | claves | cuerpo:
                frecuencia[palabra] = frecuencia.get(palabra, 0) + 1
        self._idf = {p: math.log(1 + documentos / f) for p, f in frecuencia.items()}
        self._vocabulario = list(frecuencia)

    def _equivalente(self, palabra):
        """La palabra tal cual, o la del vocabulario más parecida (errores de tipeo)."""
        if palabra in self._idf:
            return palabra, 1.0
        if len(palabra) < 4:
            return None, 0
        mejor, parecido = None, 0
        for candidata in self._vocabulario:
            if abs(len(candidata) - len(palabra)) > 2:
                continue
            ratio = SequenceMatcher(None, palabra, candidata).ratio()
            if ratio > parecido:
                mejor, parecido = candidata, ratio
        return (mejor, parecido) if parecido >= 0.82 else (None, 0)

    def buscar(self, consulta, proceso=None, cantidad=5):
        terminos = []
        for palabra in palabras(consulta):
            equivalente, peso = self._equivalente(palabra)
            if equivalente:
                terminos.append((equivalente, peso))
        frase = normalizar(consulta)
        pares_consulta = set(zip([t for t, _ in terminos], [t for t, _ in terminos][1:]))
        resultados = []
        for entrada, titulo, claves, cuerpo, titulo_normal, pares in self._indice:
            if proceso and entrada["proceso"] not in (proceso, "general"):
                continue
            puntaje = 0.0
            for termino, peso in terminos:
                idf = self._idf.get(termino, 0)
                if termino in titulo:
                    puntaje += 3.0 * idf * peso
                elif termino in claves:
                    puntaje += 2.2 * idf * peso
                elif termino in cuerpo:
                    puntaje += 0.6 * idf * peso
            puntaje += 3.0 * len(pares_consulta & pares)      # palabras seguidas como en la pregunta
            if frase and len(frase) > 6 and frase in titulo_normal:
                puntaje += 6
            if proceso and entrada["proceso"] == proceso:
                puntaje *= 1.15
            if puntaje > 0:
                resultados.append(Coincidencia(entrada, puntaje))
        resultados.sort(key=lambda c: c.puntaje, reverse=True)
        return resultados[:cantidad]

    def por_id(self, identificador):
        return next((e for e in self.preguntas if e["id"] == identificador), None)

    def del_proceso(self, proceso):
        return [e for e in self.preguntas if proceso in (None, "todos") or e["proceso"] == proceso]


UMBRAL_RESPUESTA = 7.0   # por debajo de esto se ofrecen sugerencias en lugar de responder directo
