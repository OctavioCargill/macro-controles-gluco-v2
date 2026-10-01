import pandas as pd


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


def calcular_fecha_pago(df):

    df["FECHA_CALCULADA"] = pd.NaT

    fecha_base = pd.to_datetime(
        df["Fecha Generacion Liquidacion"],
        errors="coerce"
    )

    for idx in df.index:

        fecha = fecha_base.loc[idx]

        dias = df.loc[idx, "DIAS_PAGO"]

        if pd.isna(fecha):
            continue

        if pd.isna(dias):
            continue

        dias = int(dias)

        # VBA:
        # dias < 7 = habiles
        # dias >= 7 = corridos

        if dias < 7:

            fecha_calc = fecha

            contador = 0

            while contador < dias:

                fecha_calc += pd.Timedelta(days=1)

                if fecha_calc.weekday() < 5:
                    contador += 1

        else:

            fecha_calc = (
                fecha
                + pd.Timedelta(days=dias)
            )

        df.loc[
            idx,
            "FECHA_CALCULADA"
        ] = fecha_calc

    return df


def calcular_fecha_final(df):

    df["FECHA_FINAL"] = df[
        "FECHA_CALCULADA"
    ]

    fecha_cierta = pd.to_datetime(
        df["Fecha cierta de pago"],
        errors="coerce"
    )

    mask = (
        fecha_cierta.notna()
        &
        (
            fecha_cierta >
            df["FECHA_CALCULADA"]
        )
    )

    df.loc[
        mask,
        "FECHA_FINAL"
    ] = fecha_cierta

    return df

def validar_fecha_pago(df):

    df["RESULTADO_FECHA"] = "SIN FECHA"

    fecha_final = pd.to_datetime(
        df["FECHA_FINAL"],
        errors="coerce"
    )

    fecha_pago = pd.to_datetime(
        df["Fecha Pago"],
        errors="coerce"
    )

    mask_ok = (
        fecha_final.notna()
        &
        fecha_pago.notna()
        &
        (fecha_final == fecha_pago)
    )

    mask_mayor = (
        fecha_final.notna()
        &
        fecha_pago.notna()
        &
        (fecha_final < fecha_pago)
    )

    mask_menor = (
        fecha_final.notna()
        &
        fecha_pago.notna()
        &
        (fecha_final > fecha_pago)
    )

    df.loc[
        mask_ok,
        "RESULTADO_FECHA"
    ] = "OK"

    df.loc[
        mask_mayor,
        "RESULTADO_FECHA"
    ] = "ERROR-FECHA-MAYOR"

    df.loc[
        mask_menor,
        "RESULTADO_FECHA"
    ] = "ERROR-FECHA-MENOR"

    return df