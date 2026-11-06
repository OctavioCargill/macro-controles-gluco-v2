"""Orquesta Liberación: propuestas + 020 + 067 → controles → visor → Output E1 → limpieza."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from liberacion import cargas
from liberacion.motor import (
    A_LIBERAR_EN_E1, NO_SE_ENCONTRO, Avisos, controlar, liberar_manual, preparar_020, resumen_paquetes, ya_liberado,
)
from liberacion.salida import actualizar_registro_con_control, exportar_output_e1
from services.bloqueo import uso_exclusivo

logger = logging.getLogger(__name__)


@dataclass
class ResultadoLiberacion:
    fuente: dict
    propuestas: list
    paquetes: list
    t067: list
    avisos: Avisos
    rutas: dict
    generado: datetime = field(default_factory=datetime.now)

    def estadisticas(self):
        visibles = [p for p in self.paquetes if not ya_liberado(p["filas"][0])]
        por_control = {}
        for paquete in visibles:
            por_control[paquete["control"]] = por_control.get(paquete["control"], 0) + 1
        return {
            "paquetes": len(self.paquetes),
            "visibles": len(visibles),
            "ya_liberados": len(self.paquetes) - len(visibles),
            "a_liberar": sum(1 for p in visibles if p["control"] in A_LIBERAR_EN_E1),
            "por_control": por_control,
        }


def ejecutar_control(fuente, ruta_020, ruta_067, config, progreso=None) -> ResultadoLiberacion:
    """fuente: {"tipo": "registro", "ruta", "generado", "ventana"} o {"tipo": "archivo", "ruta", "ventana"}."""

    def avanzar(texto):
        logger.info(texto)
        if progreso:
            progreso(texto)

    if not ruta_020 or not ruta_067:
        raise cargas.ErrorDeCarga("Faltan los reportes 020 y/o 067.")
    avanzar("Leyendo las propuestas…")
    if fuente["tipo"] == "registro":
        lectura = cargas.cargar_desde_registro(fuente["ruta"], fuente["generado"], fuente["ventana"])
    else:
        lectura = cargas.cargar_desde_propuestas(fuente["ruta"], fuente["ventana"])
    propuestas = lectura.filas
    avanzar(f"Propuestas: {len(propuestas)} documentos.")
    avanzar("Leyendo el 020…")
    t020 = preparar_020(cargas.cargar_020(ruta_020).filas, config)
    avanzar(f"020: {len(t020)} renglones.")
    avanzar("Leyendo el 067…")
    t067 = cargas.cargar_067(ruta_067).filas
    avanzar(f"067: {len(t067)} renglones.")

    avanzar("Controlando (ID de netting, montos, cronología, cuenta K, devengados, permuta)…")
    control = controlar(propuestas, t020, t067, config)
    paquetes = resumen_paquetes(propuestas, t067)

    negativos = [p for p in paquetes if p["neto"] < 0]
    if negativos:
        control.avisos.agregar(
            f"{len(negativos)} paquete(s) con neto negativo (no se liberan): "
            f"N° {', '.join(str(p['n_propuesta']) for p in negativos[:8])}.",
            revisar=True,
        )
    manuales = [p for p in paquetes if p["control"] in ("MANUAL", "COMPENSA-MANUAL")]
    if manuales:
        control.avisos.agregar(
            f"{len(manuales)} paquete(s) en MANUAL. No debería haber: si hay, probablemente al netteador le faltó "
            "tildar alguna RI en E1.",
            revisar=True,
        )

    resultado = ResultadoLiberacion(
        fuente=dict(fuente), propuestas=propuestas, paquetes=paquetes, t067=t067, avisos=control.avisos,
        rutas={"020": str(ruta_020), "067": str(ruta_067)},
    )
    if fuente["tipo"] == "registro":
        try:
            with uso_exclusivo("guardando los IDs de pago", Path(fuente["ruta"]).parent):
                cambiadas = actualizar_registro_con_control(fuente["ruta"], propuestas)
            avanzar(f"Registro de Netting actualizado con los IDs de pago ({cambiadas} filas).")
        except PermissionError as exc:
            resultado.avisos.agregar(str(exc), revisar=True)
    e = resultado.estadisticas()
    avanzar(f"Listo: {e['visibles']} paquetes para revisar, {e['a_liberar']} para liberar.")
    return resultado


def liberacion_manual(resultado: ResultadoLiberacion, paquete):
    if resultado.fuente["tipo"] != "registro":
        liberar_manual(paquete)
        return
    with uso_exclusivo("liberando un paquete a mano", Path(resultado.fuente["ruta"]).parent):
        liberar_manual(paquete)
        actualizar_registro_con_control(resultado.fuente["ruta"], paquete["filas"])


def generar_output_e1(resultado: ResultadoLiberacion, ruta):
    with uso_exclusivo("generando el Output E1", Path(ruta).parent):
        return exportar_output_e1(ruta, resultado.paquetes)


def sin_id(resultado):
    return [p for p in resultado.paquetes if p["id"] == NO_SE_ENCONTRO]
