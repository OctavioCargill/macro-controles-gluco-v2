def marcar_contrato_no_encontrado(df):

    df["CONTRATO_ENCONTRADO_090"] = (
        ~df["UNIDADES_ORIGINALES_090"].isna()
    )

    return df
