import pandas as pd


def cargar_historico(ruta_archivo):

    df_historico = pd.read_excel(
        ruta_archivo
    )

    return df_historico


def filtrar_controlados(
    df,
    df_historico
):

    ids_controlados = set(
        df_historico["id_largo"]
        .astype(str)
    )

    df_filtrado = df[
        ~df["id_largo"]
        .astype(str)
        .isin(ids_controlados)
    ].copy()

    eliminados = (
        len(df)
        - len(df_filtrado)
    )

    return (
        df_filtrado,
        eliminados
    )


def marcar_revisar(
    df,
    df_historico
):

    ids_cortos = set(
        df_historico["id_corto"]
        .astype(str)
    )

    df["REVISAR"] = (
        df["id_corto"]
        .astype(str)
        .isin(ids_cortos)
    )

    return df
