import pandas as pd


def limpiar_cuit(valor):

    if pd.isna(valor):
        return ""

    try:
        return str(int(float(valor)))
    except:
        return str(valor)