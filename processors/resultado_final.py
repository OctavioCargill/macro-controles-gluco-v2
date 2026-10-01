def calcular_resultado_final(df):

    df["RESULTADO_FINAL"] = "CONTROL MACRO"

    df["MOTIVO_CONTROL"] = ""

    # -------------------------
    # REVISAR
    # -------------------------

    mask_revisar = (
        df["REVISAR"] == True
    )

    df.loc[
        mask_revisar,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask_revisar,
        "MOTIVO_CONTROL"
    ] = "REVISAR"

    # -------------------------
    # YA PAGADO
    # -------------------------

    mask_pagado = (
        df["YA_PAGADO"] == True
    )

    df.loc[
        mask_pagado,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask_pagado,
        "MOTIVO_CONTROL"
    ] = "YA PAGADO"

    # -------------------------
    # BENEFICIARIO
    # -------------------------

    mask_beneficiario = (
        df["RESULTADO_BENEFICIARIO"]
        != "OK"
    )

    df.loc[
        mask_beneficiario,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask_beneficiario,
        "MOTIVO_CONTROL"
    ] = "ERROR BENEFICIARIO"

    # -------------------------
    # CESION
    # -------------------------

    mask_cesion = (
        df["RESULTADO_CESION"]
        != "OK"
    )

    df.loc[
        mask_cesion,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask_cesion,
        "MOTIVO_CONTROL"
    ] = "ERROR CESION"
    
    # -------------------------
    # MATCH 090
    # -------------------------

    if "CONTRATO_ENCONTRADO_090" in df.columns:

        mask_match = (
            df["CONTRATO_ENCONTRADO_090"]
            == False
        )

        df.loc[
            mask_match,
            "RESULTADO_FINAL"
        ] = "CONTROL MANUAL"

        df.loc[
            mask_match,
            "MOTIVO_CONTROL"
        ] = "SIN MATCH 090"

    mask_fecha = (
        df["RESULTADO_FECHA"]
        != "OK"
    )

    df.loc[
        mask_fecha,
        "RESULTADO_FINAL"
    ] = "CONTROL MANUAL"

    df.loc[
        mask_fecha,
        "MOTIVO_CONTROL"
    ] = "ERROR FECHA"

    return df