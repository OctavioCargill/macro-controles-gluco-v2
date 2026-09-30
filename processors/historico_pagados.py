import pandas as pd


def cargar_historico_pagados(ruta_archivo):

    df_pagados = pd.read_excel(
        ruta_archivo
    )

    print(
        f"Histórico pagados cargado: "
        f"{len(df_pagados)} registros"
    )

    return df_pagados


def marcar_pagados(
    df,
    df_pagados
):

    ids_largos = set(
        df_pagados["id_largo"]
        .astype(str)
    )

    ids_cortos = set(
        df_pagados["id_corto"]
        .astype(str)
    )

    df["YA_PAGADO"] = (
        df["id_largo"]
        .astype(str)
        .isin(ids_largos)
        |
        df["id_corto"]
        .astype(str)
        .isin(ids_cortos)
    )

    return df