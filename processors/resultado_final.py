def calcular_resultado_final(df):

    # Estado por defecto
    df["RESULTADO_FINAL"] = "CONTROL MACRO"
    df["MOTIVO_CONTROL"] = ""

    # -------------------------
    # SIN MATCH 090
    # -------------------------

    if "CONTRATO_ENCONTRADO_090" in df.columns:

        mask = (
            df["CONTRATO_ENCONTRADO_090"]
            == False
        )

        df.loc[
            mask,
            "RESULTADO_FINAL"
        ] = "CONTROL MANUAL"

        df.loc[
            mask,
            "MOTIVO_CONTROL"
        ] = "SIN MATCH 090"

    # -------------------------
    # REVISAR HISTORICO
    # -------------------------

    mask = (
        df["REVISAR"] == True
    )

    df.loc[
        mask,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask,
        "MOTIVO_CONTROL"
    ] = "REVISAR"

    # -------------------------
    # YA PAGADO
    # -------------------------

    mask = (
        df["YA_PAGADO"] == True
    )

    df.loc[
        mask,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask,
        "MOTIVO_CONTROL"
    ] = "YA PAGADO"

    # -------------------------
    # BENEFICIARIO
    # -------------------------

    if "RESULTADO_BENEFICIARIO" in df.columns:

        mask = (
            df["RESULTADO_BENEFICIARIO"]
            != "OK"
        )

        df.loc[
            mask,
            "RESULTADO_FINAL"
        ] = "CONTROL MANUAL"

        df.loc[
            mask,
            "MOTIVO_CONTROL"
        ] = "ERROR BENEFICIARIO"

    # -------------------------
    # CESION
    # -------------------------

    if "RESULTADO_CESION" in df.columns:

        mask = (
            df["RESULTADO_CESION"]
            != "OK"
        )

        df.loc[
            mask,
            "RESULTADO_FINAL"
        ] = "CONTROL MANUAL"

        df.loc[
            mask,
            "MOTIVO_CONTROL"
        ] = "ERROR CESION"

    # -------------------------
    # FECHAS
    # -------------------------
    #
    # NO ACTIVAR TODAVIA
    #
    # Cuando validemos que la lógica
    # de fechas coincide con VBA
    # descomentamos este bloque.
    #
    # mask = (
    #     df["RESULTADO_FECHA"]
    #     != "OK"
    # )
    #
    # df.loc[
    #     mask,
    #     "RESULTADO_FINAL"
    # ] = "CONTROL MANUAL"
    #
    # df.loc[
    #     mask,
    #     "MOTIVO_CONTROL"
    # ] = "ERROR FECHA"

    return df