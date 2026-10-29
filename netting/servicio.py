"""Orquesta Netting: carga de archivos → propuestas 24 y 48 hs → salida."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from netting import cargas
from netting.config import anios_sin_feriados, feriados_como_fechas, guardar_config
from netting.motor import Avisos, Estado, TIPOS_BENEFICIARIO, armar_propuestas, preparar_077, preparar_historico
from netting.salida import asignar_grupos, exportar_propuestas, resumen_propuestas

logger = logging.getLogger(__name__)

NOMBRE_SALIDA = "Propuestas_Netting.xlsx"


@dataclass
class ResultadoNetting:
    fecha_proceso: date
    rutas: dict
    propuestas_24: list
    propuestas_48: list
    numero_inicial: int
    numero_final: int
    avisos: Avisos
    estadisticas: dict = field(default_factory=dict)
    generado: datetime = field(default_factory=datetime.now)

    def resumen(self, ventana):
        return resumen_propuestas(self.propuestas_24 if ventana == "24" else self.propuestas_48)


def ejecutar_netting(rutas, fecha_proceso: date, ultimo_numero: int, config, progreso=None) -> ResultadoNetting:
    """rutas: {"historico", "077", "090", "ventas"} → ResultadoNetting. Lanza cargas.ErrorDeCarga."""

    def avanzar(texto):
        logger.info(texto)
        if progreso:
            progreso(texto)

    avisos = Avisos()
    faltantes = [nombre for nombre in ("historico", "077", "090") if not rutas.get(nombre)]
    if faltantes:
        raise cargas.ErrorDeCarga("Faltan archivos: " + ", ".join(faltantes) + ".")

    avanzar("Leyendo el Histórico…")
    historico = cargas.cargar_historico(rutas["historico"])
    avanzar(f"Histórico: {len(historico.filas)} documentos.")
    avanzar("Leyendo el 077…")
    reporte_077 = cargas.cargar_077(rutas["077"])
    avanzar(f"077: {len(reporte_077.filas)} documentos.")
    avanzar("Leyendo el 090…")
    reporte_090 = cargas.cargar_090(rutas["090"])
    avanzar(f"090: {len(reporte_090.filas)} contratos.")
    if rutas.get("ventas"):
        avanzar("Leyendo compensas de ventas…")
        ventas = cargas.cargar_ventas(rutas["ventas"])
        avanzar(f"Ventas: {len(ventas.filas)} compensas pendientes.")
    else:
        ventas = cargas.Lectura([], [], "")
        avisos.agregar(
            "Se armó SIN compensas de ventas: las propuestas de corredores no incluyen esos descuentos "
            "(la macro sí los incluye).",
            revisar=True,
        )
    _avisar_archivos_viejos(rutas, fecha_proceso, avisos)
    for lectura in (historico, reporte_077, reporte_090, ventas):
        for aviso in lectura.avisos:
            avisos.agregar(aviso, revisar=True)

    feriados = feriados_como_fechas(config)
    sin_feriados = anios_sin_feriados(config, fecha_proceso)
    if sin_feriados:
        avisos.agregar(
            f"No hay feriados cargados para {', '.join(map(str, sin_feriados))}: los días a pagar pueden dar mal.",
            revisar=True,
        )

    avanzar("Calculando días a pagar y tipo de beneficiario…")
    hist = preparar_historico(historico.filas, fecha_proceso, feriados, avisos)

    avanzar("Preparando el 077 (cruce con 090 y ventas)…")
    t077 = preparar_077(reporte_077.filas, reporte_090.filas, ventas.filas, avisos)

    solo_24 = {str(c.get("ab", "")).strip() for c in config.get("corredores_solo_24", []) if c.get("ab")}
    estado = Estado(t077=t077, t090=[dict(f) for f in reporte_090.filas],
                    ultimo_numero=int(ultimo_numero), solo_24=solo_24, avisos=avisos)

    avanzar("Armando propuestas de 24 hs…")
    propuestas_24, _ = armar_propuestas(hist, estado, "24")
    avanzar("Armando propuestas de 48 hs…")
    propuestas_48, _ = armar_propuestas(hist, estado, "48")

    resumenes = {v: resumen_propuestas(p) for v, p in (("24", propuestas_24), ("48", propuestas_48))}
    for ventana, resumen in resumenes.items():
        negativas = [r for r in resumen if r["neto"] < 0]
        if negativas:
            avisos.agregar(
                f"{ventana} hs: {len(negativas)} propuesta(s) con más a descontar que a pagar "
                f"(N° {', '.join(str(r['n_propuesta']) for r in negativas[:8])}{'…' if len(negativas) > 8 else ''}).",
                revisar=True,
            )

    por_tipo = {}
    for fila in hist:
        por_tipo[fila["tipo_benef"] or "(sin tipo)"] = por_tipo.get(fila["tipo_benef"] or "(sin tipo)", 0) + 1
    otros_tipos = {t: c for t, c in por_tipo.items() if t not in TIPOS_BENEFICIARIO}
    if otros_tipos:
        avisos.agregar(
            "Histórico: documentos que no encajan en ningún tipo de beneficiario: "
            + ", ".join(f"{t} ({c})" for t, c in otros_tipos.items()),
            revisar=True,
        )

    estadisticas = {
        "historico": len(hist),
        "en_24": sum(1 for f in hist if f["dias"] <= 1),
        "en_48": sum(1 for f in hist if f["dias"] == 2),
        "mas_48": sum(1 for f in hist if f["dias"] > 2),
        "por_tipo": por_tipo,
        "docs_077": len(t077),
        "docs_077_usados": sum(1 for f in t077 if f["ag"] == "YA USADA"),
        "propuestas_24": len(resumenes["24"]),
        "propuestas_48": len(resumenes["48"]),
        "filas_24": len(propuestas_24),
        "filas_48": len(propuestas_48),
    }
    avanzar(
        f"Listo: {estadisticas['propuestas_24']} propuestas de 24 hs y {estadisticas['propuestas_48']} de 48 hs."
    )
    return ResultadoNetting(
        fecha_proceso=fecha_proceso,
        rutas=dict(rutas),
        propuestas_24=propuestas_24,
        propuestas_48=propuestas_48,
        numero_inicial=int(ultimo_numero),
        numero_final=estado.ultimo_numero,
        avisos=avisos,
        estadisticas=estadisticas,
    )


def _avisar_archivos_viejos(rutas, fecha_proceso, avisos):
    """Avisa si algún archivo se modificó por última vez antes de la fecha de proceso."""
    nombres = {"historico": "Histórico", "077": "077", "090": "090", "ventas": "Compensas de ventas"}
    for clave, nombre in nombres.items():
        ruta = rutas.get(clave)
        if not ruta:
            continue
        try:
            modificado = datetime.fromtimestamp(Path(ruta).stat().st_mtime)
        except OSError:
            continue
        if modificado.date() < fecha_proceso:
            avisos.agregar(
                f"{nombre}: el archivo es del {modificado:%d/%m/%Y %H:%M}, anterior a la fecha de proceso "
                f"({fecha_proceso:%d/%m/%Y}). ¿Es la versión del día?",
                revisar=(clave == "ventas"),
            )


def generar_salida(resultado: ResultadoNetting, cantidad_analistas: int, carpeta, config) -> Path:
    """Reparte por analista, escribe Propuestas_Netting.xlsx y guarda el último N° de propuesta."""
    if cantidad_analistas < 1:
        raise ValueError("La cantidad de analistas tiene que ser 1 o más.")
    asignar_grupos(resultado.propuestas_24, cantidad_analistas, "24")
    asignar_grupos(resultado.propuestas_48, cantidad_analistas, "48")

    info = [
        ("Generado", resultado.generado.strftime("%d/%m/%Y %H:%M")),
        ("Fecha de proceso (hoy para los días a pagar)", resultado.fecha_proceso.strftime("%d/%m/%Y")),
        ("Histórico", resultado.rutas.get("historico", "")),
        ("077", resultado.rutas.get("077", "")),
        ("090", resultado.rutas.get("090", "")),
        ("Compensas de ventas", resultado.rutas.get("ventas", "") or "(sin compensas de ventas)"),
        ("Primer N° de propuesta", resultado.numero_inicial + 1),
        ("Último N° de propuesta", resultado.numero_final),
        ("Cantidad de analistas", cantidad_analistas),
        ("Propuestas 24 hs", resultado.estadisticas.get("propuestas_24", 0)),
        ("Propuestas 48 hs", resultado.estadisticas.get("propuestas_48", 0)),
    ]
    for aviso in resultado.avisos.revisar:
        info.append(("Revisar", aviso))
    for aviso in resultado.avisos.info:
        info.append(("Info", aviso))

    ruta = Path(carpeta) / NOMBRE_SALIDA
    exportar_propuestas(ruta, resultado.propuestas_24, resultado.propuestas_48, info)

    config["ultimo_numero_propuesta"] = resultado.numero_final
    config["cantidad_analistas"] = cantidad_analistas
    config.setdefault("rutas", {})["salida"] = str(Path(carpeta))
    try:
        guardar_config(config)
    except Exception:
        logger.exception("No se pudo guardar la configuración de Netting.")
    return ruta
