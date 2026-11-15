import logging
from pathlib import Path

import pandas as pd

from processors.ids import ids_validos, normalizar_columnas_id


def cargar_historico(ruta_archivo):
    """Lee el histórico de controlados y deja id_largo / id_corto listos (acepta el .xlsb de la macro)."""
    return normalizar_columnas_id(_leer_historico(ruta_archivo))


def _leer_historico(ruta_archivo):
    ruta = Path(ruta_archivo)
    if ruta.suffix.lower() == ".xlsb":
        try:
            return pd.read_excel(ruta, engine="pyxlsb")
        except ImportError as exc:
            logger = logging.getLogger(__name__)
            logger.warning(
                "No se pudo importar pyxlsb para %s. Se intentará usar CSV de fallback. Detalle: %s",
                ruta,
                exc,
            )
            rutas_fallback = [
                ruta.with_name(f"{ruta.stem}_fallback.csv"),
                ruta.with_suffix(".csv"),
                ruta.with_name(f"{ruta.stem}.csv"),
            ]
            for fallback in rutas_fallback:
                if fallback.exists() and fallback.is_file():
                    logger.info("Cargando histórico desde fallback CSV: %s", fallback)
                    return pd.read_csv(fallback)
            raise ImportError(
                "No se pudo abrir el histórico .xlsb porque falta pyxlsb y no existe un CSV de fallback válido. "
                "Instale pyxlsb o incluya un archivo de respaldo CSV."
            ) from exc

    return pd.read_excel(ruta)


def filtrar_controlados(
    df,
    df_historico
):

    ids_controlados = ids_validos(df_historico["id_largo"])

    df_filtrado = df[
        ~df["id_largo"]
        .astype(str)
        .isin(ids_controlados)
    ].copy()

    eliminados = (
        len(df)
        - len(df_filtrado)
    )

    return (
        df_filtrado,
        eliminados
    )


def marcar_revisar(
    df,
    df_historico
):

    ids_cortos = ids_validos(df_historico["id_corto"])

    df["REVISAR"] = (
        df["id_corto"]
        .astype(str)
        .isin(ids_cortos)
    )

    return df
