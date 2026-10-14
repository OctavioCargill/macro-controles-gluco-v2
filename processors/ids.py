import pandas as pd


def normalizar_nro_legal(df):
    if df is None or df.empty:
        return df

    if "Nro_Legal" not in df.columns:
        df["Nro_Legal"] = ""

    df["Nro_Legal"] = df["Nro_Legal"].replace("", pd.NA)

    if "Numero documento fiscal" in df.columns:
        df["Nro_Legal"] = df["Nro_Legal"].fillna(df["Numero documento fiscal"])
        df["Nro_Legal"] = df["Nro_Legal"].astype(str).str.replace(".0", "", regex=False)

    if "COE" not in df.columns:
        df["COE"] = df["Nro_Legal"]

    if "Nro. Legal" not in df.columns:
        df["Nro. Legal"] = df["Nro_Legal"]

    return df


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