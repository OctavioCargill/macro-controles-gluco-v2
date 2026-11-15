import pandas as pd

from processors.ids import ids_validos, normalizar_columnas_id


def cargar_historico_pagados(ruta_archivo):

    """Lee el histórico de pagados. Si no existe, devuelve uno vacío (no hay nada pagado todavía)."""
    from pathlib import Path

    if not Path(ruta_archivo).exists():
        return pd.DataFrame(columns=["id_largo", "id_corto"])
    return normalizar_columnas_id(pd.read_excel(ruta_archivo))


def marcar_pagados(
    df,
    df_pagados
):

    ids_largos = ids_validos(df_pagados["id_largo"])
    ids_cortos = ids_validos(df_pagados["id_corto"])

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