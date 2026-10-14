import re
import unicodedata

import pandas as pd


def normalizar_descripcion_liquidacion(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        ch for ch in texto
        if not unicodedata.combining(ch)
    )
    texto = texto.replace("/", " ")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def es_liquidacion_parcial(valor):

    texto = normalizar_descripcion_liquidacion(valor)

    return (
        texto == "liquidacion parcial"
        or (
            "liquidacion" in texto
            and "parcial" in texto
            and "final" not in texto
        )
    )


def es_liquidacion_final(valor):

    texto = normalizar_descripcion_liquidacion(valor)

    return (
        "liquidacion" in texto
        and "final" in texto
        and "parcial" in texto
    )


def clasificar_documentos(df):

    parciales = df[
        (df["Tipo Doc"].astype(str).str.strip() == "L#")
        &
        df["Descripcion de la liquidacion"].map(es_liquidacion_parcial)
    ]

    finales = df[
        (df["Tipo Doc"].astype(str).str.strip() == "L#")
        &
        df["Descripcion de la liquidacion"].map(es_liquidacion_final)
    ]

    comisiones = df[
        df["Tipo Doc"].astype(str).str.strip() == "C0"
    ]

    ajustes = df[
        df["Tipo Doc"].astype(str).str.strip() == "H7"
    ]

    return (
        parciales,
        finales,
        comisiones,
        ajustes
    )