"""Pruebas del asistente: contenido consistente y que las preguntas típicas encuentren su respuesta."""

import pytest

from asistente.buscador import UMBRAL_RESPUESTA, Buscador, normalizar
from asistente.contenido import PREGUNTAS, PROCESOS

PANTALLAS = {"inicio", "controlar", "netting", "liberacion", "carga", "visualizacion", "limpieza", "busqueda",
             "metricas", "netting_carga", "netting_revision", "netting_salida", "liberacion_control",
             "liberacion_revision", "liberacion_limpieza"}


def test_contenido_consistente():
    ids = [e["id"] for e in PREGUNTAS]
    assert len(ids) == len(set(ids))
    for entrada in PREGUNTAS:
        assert entrada["proceso"] in PROCESOS
        assert entrada["pregunta"].strip() and entrada["respuesta"].strip()
        assert entrada.get("pantalla") in (None, *PANTALLAS), entrada["id"]
        for relacionada in entrada.get("relacionadas", []):
            assert relacionada in ids and relacionada != entrada["id"]
    for proceso in PROCESOS:
        assert any(e["proceso"] == proceso for e in PREGUNTAS)


def test_normalizar_saca_acentos_y_signos():
    assert normalizar("¿Qué es LIBERACIÓN?") == "que es liberacion"


@pytest.mark.parametrize("consulta, esperado", [
    ("no me sale ninguna propuesta", "net_sin_propuestas"),
    ("como copio el coe", "ctl_copiar"),
    ("donde pongo los feriados", "net_feriados"),
    ("el id de pago lo cargo a mano?", "lib_id"),
    ("no aparece una liquidacion del 044", "ctl_ya_controlada"),
    ("no puedo guardar el archivo", "gen_excel_abierto"),
    ("liberacion manul", "lib_manual"),            # con error de tipeo
    ("que pasa con los pagos en estado P", "lib_ya_liberado"),
    ("saldo en la cuenta K", "lib_controles"),
    ("qué es un corredor directo", "net_tipos_benef"),
    ("como pruebo la app", "gen_prueba"),
    ("que es el output e1", "lib_output"),
])
def test_preguntas_tipicas(consulta, esperado):
    resultados = Buscador().buscar(consulta)
    assert resultados and resultados[0].entrada["id"] == esperado
    assert resultados[0].puntaje >= UMBRAL_RESPUESTA


def test_sin_resultado_y_filtro_por_proceso():
    buscador = Buscador()
    assert buscador.buscar("hola") == []
    assert all(c.entrada["proceso"] in ("netting", "general") for c in buscador.buscar("archivos", proceso="netting"))
