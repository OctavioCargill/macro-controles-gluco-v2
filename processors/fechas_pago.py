CONDICIONES_PAGO = {
    "CONTADO CONTRA ENTREGA": 2,
    "A VENCER EM 7 DIAS": 7,
    "A VENCER EM 10 DIAS": 10,
    "A VENCER EM 15 DIAS": 15,
    "A VENCER EM 30 DIAS": 30,
    "A VENCER EM 45 DIAS": 45,
    "A VENCER EM 90 DIAS": 90,
}


def asignar_dias_pago(df):

    df["DIAS_PAGO"] = (
        df["Condicion de Pago"]
        .map(CONDICIONES_PAGO)
    )

    df["RESULTADO_CONDICION"] = "OK"

    df.loc[
        df["DIAS_PAGO"].isna(),
        "RESULTADO_CONDICION"
    ] = "NO ENCONTRADO"

    return df