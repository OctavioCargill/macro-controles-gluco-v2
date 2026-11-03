"""Orquesta Netting: carga de archivos → propuestas 24 y 48 hs → salida."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from netting import cargas, registro
from netting.config import anios_sin_feriados, feriados_como_fechas, guardar_config
from netting.motor import Avisos, Estado, TIPOS_BENEFICIARIO, armar_propuestas, preparar_077, preparar_historico
from netting.salida import asignar_grupos, exportar_propuestas, poner_datos_paquete, resumen_propuestas
from services.auditoria import APP_DATA_PATH

logger = logging.getLogger(__name__)

NOMBRE_SALIDA = "Propuestas_Netting.xlsx"


def ruta_pagados(config):
    return Path(config.get("rutas", {}).get("pagados") or Path(APP_DATA_PATH) / registro.NOMBRE_PAGADOS)


def ruta_registro(config):
    return Path(config.get("rutas", {}).get("registro") or Path(APP_DATA_PATH) / registro.NOMBRE_REGISTRO)


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
    salida_registrada: bool = False
    cantidad_analistas: int = 1

    def resumen(self, ventana):
        return resumen_propuestas(self.propuestas_24 if ventana == "24" else self.propuestas_48)


def _excluir_ya_procesados(historico, reporte_077, config, avisos, avanzar):
    """Saca del Histórico lo ya pagado (Liberación) y, de ambos, lo que ya está en una propuesta."""
    ids_pagados, hay_pagados = registro.cargar_pagados(ruta_pagados(config))
    antes = len(historico.filas)
    historico.filas = [
        f for f in historico.filas
        if registro._texto(f.get("id_largo")) not in ids_pagados and registro._texto(f.get("id_corto")) not in ids_pagados
    ]
    pagados = antes - len(historico.filas)
    if not hay_pagados:
        avisos.agregar(f"No se encontró {ruta_pagados(config).name}: no se excluyen documentos ya pagados.", revisar=True)
    elif pagados:
        avisos.agregar(f"Histórico: {pagados} documentos ya pagados (histórico de pagados) quedan afuera.")

    propuestos_hist = propuestos_077 = 0
    if config.get("bloquear_propuestos", True):
        claves = registro.cargar_propuestos(ruta_registro(config))
        if claves:
            antes = len(historico.filas)
            historico.filas = [f for f in historico.filas if registro.clave_historico(f) not in claves]
            propuestos_hist = antes - len(historico.filas)
            antes = len(reporte_077.filas)
            reporte_077.filas = [f for f in reporte_077.filas if registro.clave_077(f) not in claves]
            propuestos_077 = antes - len(reporte_077.filas)
        if propuestos_hist or propuestos_077:
            avisos.agregar(
                f"Ya estaban en una propuesta anterior y todavía no se liberaron: {propuestos_hist} del Histórico "
                f"y {propuestos_077} del 077. Quedan afuera."
            )
    avanzar(f"Excluidos: {pagados} ya pagados, {propuestos_hist + propuestos_077} ya propuestos.")
    return {"excluidos_pagados": pagados, "excluidos_propuestos_hist": propuestos_hist,
            "excluidos_propuestos_077": propuestos_077}


def _avisar_sin_propuestas(hist, fecha_proceso, avisos):
    """Si no sale ninguna propuesta casi siempre es la fecha de proceso: se muestran las próximas fechas de pago."""
    futuras = sorted({f["fecha_pago"].date() for f in hist
                      if f.get("fecha_pago") is not None and f["fecha_pago"].date() > fecha_proceso})
    texto = f"No salió ninguna propuesta con fecha de proceso {fecha_proceso:%d/%m/%Y}: ningún documento del histórico vence en 24 o 48 hs."
    if futuras:
        texto += " Próximas fechas de pago en el histórico: " + ", ".join(f"{d:%d/%m/%Y}" for d in futuras[:5]) + "."
    avisos.agregar(texto, revisar=True)


def ejecutar_netting(rutas, fecha_proceso: date, ultimo_numero: int, config, progreso=None) -> ResultadoNetting:
    """rutas: {"historico", "077", "090"} → ResultadoNetting. Lanza cargas.ErrorDeCarga."""

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
    _avisar_archivos_viejos(rutas, fecha_proceso, avisos)
    excluidos = _excluir_ya_procesados(historico, reporte_077, config, avisos, avanzar)
    for lectura in (historico, reporte_077, reporte_090):
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

    avanzar("Preparando el 077 (cruce con el 090)…")
    t077 = preparar_077(reporte_077.filas, reporte_090.filas, avisos)

    solo_24 = {str(c.get("ab", "")).strip() for c in config.get("corredores_solo_24", []) if c.get("ab")}
    estado = Estado(t077=t077, t090=[dict(f) for f in reporte_090.filas],
                    ultimo_numero=int(ultimo_numero), solo_24=solo_24, avisos=avisos,
                    agrupar_por_ab=config.get("agrupar_por_ab", True))

    avanzar("Armando propuestas de 24 hs…")
    propuestas_24, _ = armar_propuestas(hist, estado, "24")
    avanzar("Armando propuestas de 48 hs…")
    propuestas_48, _ = armar_propuestas(hist, estado, "48")

    _validar_estatus(hist, propuestas_24 + propuestas_48, avisos)

    # Los grupos (uno por analista) se reparten desde el armado, así cada uno revisa los suyos.
    cantidad_analistas = max(1, int(config.get("cantidad_analistas", 1) or 1))
    asignar_grupos(propuestas_24, cantidad_analistas, "24")
    asignar_grupos(propuestas_48, cantidad_analistas, "48")

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
        **excluidos,
    }
    if not propuestas_24 and not propuestas_48:
        _avisar_sin_propuestas(hist, fecha_proceso, avisos)
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
        cantidad_analistas=cantidad_analistas,
    )


ESTATUS_VALIDOS = ("A", "P")


def _validar_estatus(hist, propuestas, avisos):
    """«Todas las parciales del contrato deben estar en A o P para generar los IDs de pago»."""
    malos = {}
    for fila in hist:
        estatus = str(fila.get("estatus") or "").strip().upper()
        if estatus and estatus not in ESTATUS_VALIDOS:
            malos.setdefault(cargas.normalizar(fila.get("contrato")), set()).add(f"{fila['doc']} ({estatus})")
    if not malos:
        return
    contratos = set()
    for fila in propuestas:
        clave = cargas.normalizar(fila.get("contrato"))
        if fila["tipo"] == "PAGAR" and clave in malos:
            fila["alerta_estatus"] = True
            contratos.add(clave)
    if contratos:
        detalle = "; ".join(f"{c}: {', '.join(sorted(malos[c]))}" for c in sorted(map(str, contratos))[:6])
        avisos.agregar(
            f"{len(contratos)} contrato(s) con documentos que no están en estatus A o P; E1 no va a generar el ID "
            f"de pago hasta que estén todas en A o P: {detalle}{'…' if len(contratos) > 6 else ''}",
            revisar=True,
        )


def repartir_grupos(resultado: ResultadoNetting, cantidad_analistas: int):
    cantidad_analistas = max(1, int(cantidad_analistas))
    asignar_grupos(resultado.propuestas_24, cantidad_analistas, "24")
    asignar_grupos(resultado.propuestas_48, cantidad_analistas, "48")
    resultado.cantidad_analistas = cantidad_analistas


def guardar_datos_paquete(resultado: ResultadoNetting, item, config, observaciones, accion, id_pago):
    """Guarda acción, observaciones e ID de pago; si ya se dio salida, también en el registro."""
    poner_datos_paquete(item, observaciones=observaciones, accion=accion, id_pago=id_pago)
    if resultado.salida_registrada:
        registro.actualizar_paquete(
            ruta_registro(config), resultado, item["ventana"], item["n_propuesta"],
            {"Acción": accion, "Observaciones": observaciones, "ID pago E1": id_pago},
        )
        return True
    return False


def resumen_por_fecha_de_pago(resultado: ResultadoNetting):
    """Documentos a pagar por fecha de pago, para comparar con la PowerApp filtrada por fecha."""
    filas = {}
    for ventana, propuestas in (("24", resultado.propuestas_24), ("48", resultado.propuestas_48)):
        for fila in propuestas:
            if fila["tipo"] != "PAGAR":
                continue
            fecha = fila.get("fecha_pago")
            clave = fecha.date() if hasattr(fecha, "date") else None
            dato = filas.setdefault(clave, {"24": 0, "48": 0, "total": 0.0, "paquetes": set()})
            dato[ventana] += 1
            dato["total"] += fila["total"] or 0.0
            dato["paquetes"].add((ventana, fila["n_propuesta"]))
    return [
        {"fecha": fecha, "docs_24": d["24"], "docs_48": d["48"], "total": d["total"], "paquetes": len(d["paquetes"])}
        for fecha, d in sorted(filas.items(), key=lambda kv: (kv[0] is None, kv[0] or datetime.min.date()))
    ]


def _avisar_archivos_viejos(rutas, fecha_proceso, avisos):
    """Avisa si algún archivo se modificó por última vez antes de la fecha de proceso."""
    nombres = {"historico": "Histórico", "077": "077", "090": "090"}
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
            )


def _verificar_que_se_pueda_escribir(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return
    try:
        with open(ruta, "r+b"):
            pass
    except PermissionError as exc:
        raise PermissionError(
            f"{ruta.name} está abierto en otro programa (¿Excel?). Cerralo y probá de nuevo."
        ) from exc


def generar_salida(resultado: ResultadoNetting, cantidad_analistas: int, carpeta, config) -> Path:
    """Reparte por analista, escribe Propuestas_Netting.xlsx y guarda el último N° de propuesta."""
    if cantidad_analistas < 1:
        raise ValueError("La cantidad de analistas tiene que ser 1 o más.")
    repartir_grupos(resultado, cantidad_analistas)

    info = [
        ("Generado", resultado.generado.strftime("%d/%m/%Y %H:%M")),
        ("Fecha de proceso (hoy para los días a pagar)", resultado.fecha_proceso.strftime("%d/%m/%Y")),
        ("Histórico", resultado.rutas.get("historico", "")),
        ("077", resultado.rutas.get("077", "")),
        ("090", resultado.rutas.get("090", "")),
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
    destino_registro = ruta_registro(config)
    _verificar_que_se_pueda_escribir(destino_registro)
    _verificar_que_se_pueda_escribir(ruta)
    exportar_propuestas(ruta, resultado.propuestas_24, resultado.propuestas_48, info)
    # Los documentos propuestos quedan registrados: no vuelven a entrar hasta que se liberen.
    # Si se vuelve a generar el archivo de la misma corrida, no se duplica el registro.
    if not resultado.salida_registrada:
        registro.registrar_salida(
            destino_registro, resultado, (("24", resultado.propuestas_24), ("48", resultado.propuestas_48))
        )
        resultado.salida_registrada = True

    config["ultimo_numero_propuesta"] = resultado.numero_final
    config["cantidad_analistas"] = cantidad_analistas
    config.setdefault("rutas", {})["salida"] = str(Path(carpeta))
    try:
        guardar_config(config)
    except Exception:
        logger.exception("No se pudo guardar la configuración de Netting.")
    return ruta
