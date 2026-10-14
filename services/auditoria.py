import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

APP_VERSION = "v0.5.1"


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def validar_archivos_requeridos(base_dir=None):
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]

    carpeta_data = Path(base_dir) / "data"
    carpeta_exports = Path(base_dir) / "exports"
    carpeta_gui = Path(base_dir) / "gui"
    carpeta_loaders = Path(base_dir) / "loaders"
    carpeta_processors = Path(base_dir) / "processors"
    carpeta_services = Path(base_dir) / "services"
    carpeta_utils = Path(base_dir) / "utils"

    item_requerido = [
        ("044", carpeta_data / "044.xlsx", "archivo"),
        ("077", carpeta_data / "077.xlsx", "archivo"),
        ("090", carpeta_data / "090.xlsx", "archivo"),
        ("Historico_Documentos_Controlados", carpeta_data / "Historico_Documentos_Controlados.xlsb", "archivo"),
        ("Historico_Documentos_Controlados_fallback", carpeta_data / "Historico_Documentos_Controlados_fallback.csv", "archivo"),
        ("data", carpeta_data, "directorio"),
        ("exports", carpeta_exports, "directorio"),
        ("gui", carpeta_gui, "directorio"),
        ("loaders", carpeta_loaders, "directorio"),
        ("processors", carpeta_processors, "directorio"),
        ("services", carpeta_services, "directorio"),
        ("utils", carpeta_utils, "directorio"),
        ("requirements", Path(base_dir) / "requirements.txt", "archivo"),
    ]

    resultado = []
    for nombre, path, tipo in item_requerido:
        if tipo == "directorio":
            existe = path.exists() and path.is_dir()
            estado = "OK" if existe else "FALTANTE"
            size = "-" if not existe else "directorio"
            modificado = "-" if not existe else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        else:
            existe = path.exists() and path.is_file()
            estado = "OK" if existe else "FALTANTE"
            size = "-" if not existe else f"{path.stat().st_size} bytes"
            modificado = "-" if not existe else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        resultado.append({
            "nombre": nombre,
            "ruta": str(path),
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

    if df is not None and not df.empty:
        controlados = _serie_segura(df, "CONTROLADO", False)
        resultado_final = df["RESULTADO_FINAL"] if "RESULTADO_FINAL" in df.columns else pd.Series(["" for _ in range(len(df))], index=df.index)
        base["total_documentos_controlados"] = _to_int(controlados.sum())
        base["total_documentos_pendientes"] = _to_int((resultado_final.astype(str).str.strip().eq("CONTROL MACRO")).sum())
        base["cantidad_errores_detectados"] = _to_int((resultado_final.astype(str).str.strip().eq("CONTROL MANUAL")).sum())
        if "Total a Pagar" in df.columns:
            base["monto_total_procesado"] = float(pd.to_numeric(df["Total a Pagar"], errors="coerce").fillna(0).sum())

    return base


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
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)
    ruta_log = log_dir / "auditoria.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ruta_log, "a", encoding="utf-8") as archivo:
        archivo.write(f"[{timestamp}] {mensaje}\n")

    logger = logging.getLogger("macro_auditoria")
    logger.info(mensaje)


def construir_diagnostico(base_dir=None):
    recursos = validar_archivos_requeridos(base_dir)
    faltantes = [recurso for recurso in recursos if recurso["estado"] == "FALTANTE"]
    return {
        "version": APP_VERSION,
        "ultima_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado_archivos": recursos,
        "faltantes": faltantes,
        "hay_errores": bool(faltantes),
    }
