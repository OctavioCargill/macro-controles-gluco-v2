def clasificar_documentos(df):

    parciales = df[
        (df["Tipo Doc"] == "L#")
        &
        (
            df["Descripcion de la liquidacion"]
            == "Liquidación Parcial"
        )
    ]

    finales = df[
        (df["Tipo Doc"] == "L#")
        &
        (
            df["Descripcion de la liquidacion"]
            == "Liquidación Final C/Parcial"
        )
    ]

    comisiones = df[
        df["Tipo Doc"] == "C0"
    ]

    ajustes = df[
        df["Tipo Doc"] == "H7"
    ]

    return (
        parciales,
        finales,
        comisiones,
        ajustes
    )