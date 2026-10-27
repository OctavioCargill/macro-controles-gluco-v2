import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def resolver_ruta_base(base_dir=None):
    """Resuelve la ruta base de la aplicación sin depender del cwd ni de rutas locales.

    En desarrollo, la base es la carpeta raíz del proyecto. En ejecutable empaquetado,
    la base debe ser el directorio donde se encuentra el .exe.
    """
    if base_dir is not None:
        return Path(base_dir).expanduser().resolve()

    if getattr(sys, "frozen", False):
        executable = getattr(sys, "executable", None)
        if executable:
            return Path(executable).resolve().parent
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS).resolve()

    return Path(__file__).resolve().parents[1]


def resolver_estructura_runtime(base_dir=None):
    base = resolver_ruta_base(base_dir)
    rutas = {
        "root": base,
        "data": base / "data",
        "logs": base / "logs",
        "config": base / "config",
        "icon": base / "icon",
    }
    for nombre, ruta in rutas.items():
        if nombre in {"data", "logs", "config", "icon"}:
            ruta.mkdir(parents=True, exist_ok=True)
    return rutas


APP_NAME = "Aplicacion - Proceso Glucovil "
APP_VERSION = "2.0.0"
APP_VERSION_DATE = "2026-10-14"
APP_ROOT = resolver_ruta_base()
APP_RUNTIME = resolver_estructura_runtime(APP_ROOT)
APP_DATA_PATH = APP_RUNTIME["data"]
APP_LOGS_PATH = APP_RUNTIME["logs"]
APP_CONFIG_PATH = APP_RUNTIME["config"]
APP_ICON_DIR = APP_RUNTIME["icon"]
APP_ICON_PATH = APP_ICON_DIR / "placeholder.ico"
if not APP_ICON_PATH.exists():
    APP_ICON_PATH = APP_ROOT / "assets" / "icons" / "placeholder.ico"


def asegurar_estructura_runtime(base_dir=None):
    rutas = resolver_estructura_runtime(base_dir)
    base = rutas["root"]

    icon_dir = rutas["icon"]
    icon_source = base / "assets" / "icons" / "placeholder.ico"
    if not icon_dir.joinpath("placeholder.ico").exists() and icon_source.exists():
        icon_dir.joinpath("placeholder.ico").write_bytes(icon_source.read_bytes())

    config_dir = rutas["config"]
    settings_path = config_dir / "app_settings.json"
    if not settings_path.exists():
        settings_path.write_text(json.dumps({
            "product_name": APP_NAME,
            "version": APP_VERSION,
            "author": "Configurable",
            "description": "Herramienta de control y validación de liquidaciones.",
            "default_data_dir": "data",
            "default_logs_dir": "logs",
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    return rutas


asegurar_estructura_runtime(APP_ROOT)


def localizar_archivos_por_patron(carpeta, patron, extensiones=None, max_resultados=10):
    """Busca archivos por tokens dentro del nombre y acepta sufijos de fecha/tiempo.

    Ejemplos:
    - 044 -> 044.xlsx, 044_2024_01_01.xlsx, 044_20240101.xlsb
    - Historico_Documentos_Controlados -> Historico_Documentos_Controlados_2024_01_01.xlsb
    """
    carpeta = Path(carpeta).expanduser().resolve()
    patron = str(patron or "").strip()
    if not patron or not carpeta.exists() or not carpeta.is_dir():
        return []

    extensiones = {ext.lower() for ext in (extensiones or [])}
    tokens = [token for token in re.split(r"[^a-z0-9]+", patron.lower()) if token]
    if not tokens:
        return []

    archivos = []
    for path in sorted(carpeta.iterdir()):
        if not path.is_file():
            continue
        nombre = path.name.lower()
        if extensiones and path.suffix.lower() not in extensiones:
            continue
        if all(token in nombre for token in tokens):
            archivos.append(path)

    if not archivos:
        nombre_normalizado = "".join(re.split(r"[^a-z0-9]+", patron.lower()))
        for path in sorted(carpeta.iterdir()):
            if not path.is_file():
                continue
            stem = "".join(re.split(r"[^a-z0-9]+", path.stem.lower()))
            if stem.startswith(nombre_normalizado) or nombre_normalizado in stem:
                archivos.append(path)

    return archivos[:max_resultados]


def resolver_ruta_recurso(nombre, base_dir=None, subdir="data", extensiones=None):
    base = resolver_ruta_base(base_dir)
    carpeta = (base / subdir).resolve()
    candidatos = localizar_archivos_por_patron(carpeta, nombre, extensiones=extensiones)
    if candidatos:
        return candidatos[0]
    return None


def _ruta_esperada(nombre, base_dir=None):
    base = resolver_ruta_base(base_dir)
    normalizados = {
        "044": "044.xlsx",
        "077": "077.xlsx",
        "090": "090.xlsx",
        "Historico_Documentos_Controlados": "Historico_Documentos_Controlados.xlsb",
        "Historico_Documentos_Controlados_fallback": "Historico_Documentos_Controlados_fallback.csv",
    }
    nombre_base = normalizados.get(nombre, nombre)
    return (base / "data" / nombre_base).resolve()


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def validar_archivos_requeridos(base_dir=None):
    """Valida archivos de negocio en la carpeta data usando patrones tolerantes.

    No exige nombres exactos, admite sufijos de fecha y extensiones equivalentes.
    """
    if base_dir is None:
        base_dir = APP_ROOT

    base = resolver_ruta_base(base_dir)
    rutas_runtime = asegurar_estructura_runtime(base)
    carpeta_data = rutas_runtime["data"]
    logger = logging.getLogger(__name__)

    item_requerido = [
        ("base", base, "directorio"),
        ("data", carpeta_data, "directorio"),
        ("logs", rutas_runtime["logs"], "directorio"),
        ("config", rutas_runtime["config"], "directorio"),
        ("icon", rutas_runtime["icon"], "directorio"),
        ("044", "044", "archivo", [".xlsx", ".xls", ".xlsb", ".csv"]),
        ("077", "077", "archivo", [".xlsx", ".xls", ".xlsb", ".csv"]),
        ("090", "090", "archivo", [".xlsx", ".xls", ".xlsb", ".csv"]),
        ("Historico_Documentos_Controlados", "Historico_Documentos_Controlados", "archivo", [".xlsb", ".xlsx", ".xls", ".csv"]),
        ("Historico_Documentos_Controlados_fallback", "Historico_Documentos_Controlados_fallback", "archivo", [".csv", ".xlsx", ".xls", ".xlsb"]),
    ]

    resultado = []
    for item in item_requerido:
        if len(item) == 3:
            nombre, path, tipo = item
            ruta_obj = Path(path)
            ruta_busqueda = ruta_obj
        else:
            nombre, patron, tipo, extensiones = item
            ruta_obj = resolver_ruta_recurso(patron, base_dir=base, subdir="data", extensiones=extensiones)
            ruta_busqueda = ruta_obj or _ruta_esperada(nombre, base_dir=base)
            logger.info("Validando recurso '%s': base=%s data=%s ruta_esperada=%s ruta_real=%s", nombre, base, carpeta_data, ruta_busqueda, ruta_obj)

        if tipo == "directorio":
            existe = ruta_obj.exists() and ruta_obj.is_dir()
            estado = "OK" if existe else "FALTANTE"
            size = "-" if not existe else "directorio"
            modificado = "-" if not existe else datetime.fromtimestamp(ruta_obj.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        else:
            existe = ruta_obj.exists() and ruta_obj.is_file() if ruta_obj is not None else ruta_busqueda.exists() and ruta_busqueda.is_file()
            estado = "OK" if existe else "FALTANTE"
            size = "-" if not existe else f"{ruta_busqueda.stat().st_size} bytes"
            modificado = "-" if not existe else datetime.fromtimestamp(ruta_busqueda.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        resultado.append({
            "nombre": nombre,
            "ruta": str(ruta_busqueda),
            "ruta_real": str(ruta_obj) if ruta_obj is not None else str(ruta_busqueda),
            "estado": estado,
            "tipo": tipo,
            "size": size,
            "modificado": modificado,
        })

    return resultado


def diagnostico_recurso(path, nombre):
    ruta = Path(path)
    if not ruta.exists():
        return {
            "nombre": nombre,
            "ruta": str(ruta),
            "estado": "FALTANTE",
            "size": "-",
            "modificado": "-",
            "detalle": "No encontrado en la ruta esperada.",
        }

    if ruta.is_file():
        size = ruta.stat().st_size
        modificado = datetime.fromtimestamp(ruta.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "nombre": nombre,
            "ruta": str(ruta),
            "estado": "OK",
            "size": f"{size} bytes",
            "modificado": modificado,
            "detalle": "Archivo encontrado y válido.",
        }

    return {
        "nombre": nombre,
        "ruta": str(ruta),
        "estado": "INVALIDO",
        "size": "-",
        "modificado": "-",
        "detalle": "La ruta existe pero no corresponde al tipo esperado.",
    }


def _serie_segura(df, nombre, valor_default=False):
    if df is None or not hasattr(df, "columns"):
        return pd.Series([valor_default], dtype=bool)

    if nombre not in df.columns:
        return pd.Series([valor_default] * len(df), index=df.index, dtype=bool)

    serie = df[nombre].fillna(False)
    if pd.api.types.is_bool_dtype(serie):
        return serie.astype(bool)
    return serie.astype(str).str.lower().eq("true").fillna(False)


def metricas_generales(df=None, resumen=None):
    base = {
        "total_liquidaciones_detectadas": 0,
        "total_liquidaciones_procesadas": 0,
        "total_liquidaciones_aprobadas": 0,
        "total_liquidaciones_observadas": 0,
        "total_documentos_controlados": 0,
        "total_documentos_pendientes": 0,
        "total_documentos_historizados": 0,
        "cantidad_errores_detectados": 0,
        "ultima_ejecucion": "No ejecutado",
        "monto_total_procesado": 0.0,
        "liquidaciones_finales": 0,
        "liquidaciones_parciales": 0,
        "liquidaciones_comision": 0,
        "liquidaciones_otros_tipos": 0,
    }

    if resumen:
        for clave, valor in resumen.items():
            if clave == "total":
                base["total_liquidaciones_procesadas"] = _to_int(valor)
                base["total_liquidaciones_detectadas"] = _to_int(valor)
            elif clave == "macro":
                base["total_liquidaciones_aprobadas"] = _to_int(valor)
            elif clave == "manual":
                base["total_liquidaciones_observadas"] = _to_int(valor)
            elif clave == "finales":
                base["liquidaciones_finales"] = _to_int(valor)
            elif clave == "parciales":
                base["liquidaciones_parciales"] = _to_int(valor)
            elif clave == "comisiones":
                base["liquidaciones_comision"] = _to_int(valor)
            elif clave == "ultima_ejecucion":
                base["ultima_ejecucion"] = str(valor) if valor is not None else "No ejecutado"

    if df is not None and not df.empty:
        controlados = _serie_segura(df, "CONTROLADO", False)
        resultado_final = df["RESULTADO_FINAL"] if "RESULTADO_FINAL" in df.columns else pd.Series(["" for _ in range(len(df))], index=df.index)
        base["total_documentos_controlados"] = _to_int(controlados.sum())
        base["total_documentos_pendientes"] = _to_int((resultado_final.astype(str).str.strip().eq("CONTROL MACRO")).sum())
        base["cantidad_errores_detectados"] = _to_int((resultado_final.astype(str).str.strip().eq("CONTROL MANUAL")).sum())
        if "Total a Pagar" in df.columns:
            base["monto_total_procesado"] = float(pd.to_numeric(df["Total a Pagar"], errors="coerce").fillna(0).sum())

    return base


def construir_diagnostico(base_dir=None):
    base = resolver_ruta_base(base_dir)
    data = (base / "data").resolve()
    recursos = validar_archivos_requeridos(base)
    encontrados = [recurso for recurso in recursos if recurso["estado"] == "OK"]
    faltantes = [recurso for recurso in recursos if recurso["estado"] == "FALTANTE"]
    logging.getLogger(__name__).info(
        "Diagnostico de rutas: base=%s data=%s encontrados=%s faltantes=%s",
        base,
        data,
        [recurso["nombre"] for recurso in encontrados],
        [recurso["nombre"] for recurso in faltantes],
    )
    return {
        "version": APP_VERSION,
        "base_detectada": str(base),
        "data_detectada": str(data),
        "ultima_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado_archivos": recursos,
        "archivos_encontrados": [recurso["ruta_real"] for recurso in encontrados],
        "archivos_faltantes": [recurso["ruta"] for recurso in faltantes],
        "faltantes": faltantes,
        "hay_errores": bool(faltantes),
    }


def buscar_global(df, texto_busqueda):
    if df is None or df.empty:
        return pd.DataFrame()

    texto = str(texto_busqueda or "").strip()
    if not texto:
        return df.head(25).copy()

    columnas = [
        "Numero Doc",
        "Contrato",
        "Numero de CAE COE Factura",
        "Nro. Legal",
        "Nro_Legal",
        "Proveedor",
        "Nombre Beneficiario del Pago",
        "Descripcion de la liquidacion",
        "Tipo Doc",
        "Producto",
        "Descripcion de Producto",
    ]

    hay_columna = [col for col in columnas if col in df.columns]
    if not hay_columna:
        return df.head(25).copy()

    mascara = pd.Series(False, index=df.index)
    texto_norm = texto.lower()
    for col in hay_columna:
        serie = df[col].fillna("").astype(str).str.lower()
        mascara = mascara | serie.str.contains(texto_norm, case=False, na=False)

    return df.loc[mascara].head(50).copy()


def escribir_log_auditoria(mensaje):
    log_dir = APP_LOGS_PATH
    log_dir.mkdir(exist_ok=True)
    ruta_log = log_dir / "auditoria.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ruta_log, "a", encoding="utf-8") as archivo:
        archivo.write(f"[{timestamp}] {mensaje}\n")

    logger = logging.getLogger("macro_auditoria")
    logger.info(mensaje)


def evaluar_integridad_liquidaciones(
    liquidaciones_detectadas,
    liquidaciones_procesadas,
    liquidaciones_mostradas,
    liquidaciones_historizadas,
    justificaciones=None,
):
    """Valida la consistencia entre los cuatro conteos de liquidaciones.

    Regla de negocio:
    - si todos coinciden -> OK
    - si no coinciden y no hay justificación -> REQUIERE_REVISION
    - si no coinciden pero se documenta justificación -> OK_CON_JUSTIFICACION
    """
    justificaciones = justificaciones or {}
    conteos = {
        "detectadas": int(liquidaciones_detectadas or 0),
        "procesadas": int(liquidaciones_procesadas or 0),
        "mostradas": int(liquidaciones_mostradas or 0),
        "historizadas": int(liquidaciones_historizadas or 0),
    }

    valores = list(conteos.values())
    diffs = {
        clave: valor
        for clave, valor in {
            "detectadas": conteos["detectadas"] - conteos["procesadas"],
            "procesadas": conteos["procesadas"] - conteos["mostradas"],
            "mostradas": conteos["mostradas"] - conteos["historizadas"],
            "historizadas": conteos["historizadas"] - conteos["detectadas"],
        }.items()
        if valor != 0
    }

    if len(set(valores)) == 1:
        estado = "OK"
        lista_para_produccion = True
    elif any(str(valor).strip() for valor in justificaciones.values()):
        estado = "OK_CON_JUSTIFICACION"
        lista_para_produccion = True
    else:
        estado = "REQUIERE_REVISION"
        lista_para_produccion = False

    return {
        "estado": estado,
        "lista_para_produccion": lista_para_produccion,
        "diferencias": diffs,
        "justificaciones": justificaciones,
    }

