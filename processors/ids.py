import pandas as pd


def limpiar_numero(valor):

    if pd.isna(valor):
        return ""

    try:
        return str(int(float(valor)))
    except:
        return str(valor)


def generar_id_corto(df):

    df["id_corto"] = (
        df["Numero de CAE COE Factura"]
        .apply(limpiar_numero)
        +
        df["Numero documento fiscal"]
        .apply(limpiar_numero)
    )

    return df


def generar_id_largo(df):

    fecha = pd.to_datetime(
        df["Fecha Pago"],
        dayfirst=True,
        errors="coerce"
    ).dt.strftime("%d%m%Y")

    df["id_largo"] = (
        df["Tipo Doc"].astype(str)
        +
        df["Numero Doc"].astype(str)
        +
        df["Numero de CAE COE Factura"]
        .apply(limpiar_numero)
        +
        df["Numero documento fiscal"]
        .apply(limpiar_numero)
        +
        fecha.fillna("")
    )

    return df