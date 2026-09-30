import pandas as pd


def determinar_beneficiario(df):

    df["TIPO_BENEFICIARIO"] = "NO_IDENTIFICADO"

    mask_vendedor = (
        df["AB Beneficiario del Pago"]
        ==
        df["Vendedor"]
    )

    df.loc[
        mask_vendedor,
        "TIPO_BENEFICIARIO"
    ] = "VENDEDOR"

    mask_corredor = (
        df["AB Beneficiario del Pago"]
        ==
        df["Corredor"]
    )

    df.loc[
        mask_corredor,
        "TIPO_BENEFICIARIO"
    ] = "CORREDOR"

    mask_cesion = (
        df["AB Beneficiario de Cesion"]
        .notna()
    )

    df.loc[
        mask_cesion,
        "TIPO_BENEFICIARIO"
    ] = "CESION"

    # NUEVO

    df["RESULTADO_BENEFICIARIO"] = "OK"

    df.loc[
        df["TIPO_BENEFICIARIO"]
        == "NO_IDENTIFICADO",
        "RESULTADO_BENEFICIARIO"
    ] = "ERROR-BENEFICIARIO"

    return df