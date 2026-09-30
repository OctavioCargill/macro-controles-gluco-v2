import pandas as pd


def enriquecer_con_090(df_044, df_090):

    df_090_aux = df_090[
        [
            "Contrato",
            "CUIT Vendedor",
            "CUIT Corredor",
            "Unid. Originales"
        ]
    ].copy()

    df_090_aux = df_090_aux.rename(
        columns={
            "CUIT Vendedor": "CUIT_VENDEDOR_090",
            "CUIT Corredor": "CUIT_CORREDOR_090",
            "Unid. Originales": "UNIDADES_ORIGINALES_090"
        }
    )

    df_resultado = df_044.merge(
        df_090_aux,
        on="Contrato",
        how="left"
    )

    from processors.limpieza import limpiar_cuit
    df_resultado["CUIT_VENDEDOR_090"] = (
    df_resultado["CUIT_VENDEDOR_090"]
    .apply(limpiar_cuit)
    )

    df_resultado["CUIT_CORREDOR_090"] = (
        df_resultado["CUIT_CORREDOR_090"]
        .apply(limpiar_cuit)
    )

    df_resultado[
    "CONTRATO_ENCONTRADO_090"
    ] = (
    ~df_resultado[
    "UNIDADES_ORIGINALES_090"
    ].isna()
    )
    
    return df_resultado