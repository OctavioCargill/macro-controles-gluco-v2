import pandas as pd


def validar_cesiones(df):

    df["RESULTADO_CESION"] = "OK"

    volumen_cedido = pd.to_numeric(
        df["Volume Cedido"],
        errors="coerce"
    ).fillna(0)

    volumen_original = pd.to_numeric(
        df["UNIDADES_ORIGINALES_090"],
        errors="coerce"
    ).fillna(0)

    mask_error = (
        volumen_cedido >
        volumen_original
    )

    df.loc[
        mask_error,
        "RESULTADO_CESION"
    ] = (
        "ERROR-EXCEDE KG CEDIDOS"
    )

    return df