import warnings

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="openpyxl"
)

from processors.beneficiarios import (
determinar_beneficiario
)

from exports.excel_export import (
exportar_resultado
)

from processors.cesiones import (
validar_cesiones
)

from processors.historico_pagados import (
    cargar_historico_pagados,
    marcar_pagados
)

from processors.historico import (
cargar_historico,
filtrar_controlados,
marcar_revisar
)

from loaders.sap044 import cargar_044
from loaders.sap090 import cargar_090

from processors.ids import (
    generar_id_corto,
    generar_id_largo
)

from processors.clasificador import (
    clasificar_documentos
)

from processors.cruce_090 import (
    enriquecer_con_090
)


def main():

    print()
    print("=" * 50)
    print("CONTROLES GLUCO V2")
    print("=" * 50)
    print()

    # --------------------------------------------------
    # CARGA ARCHIVOS
    # --------------------------------------------------

    archivo_044 = "data/044.xlsx"
    archivo_090 = "data/090.xlsx"

    df = cargar_044(archivo_044)

    # --------------------------------------------------
    # IDS
    # --------------------------------------------------

    df = generar_id_corto(df)
    df = generar_id_largo(df)
    df_historico = cargar_historico(
    "data/historico_controlados.xlsx"
    )

    df_pagados = cargar_historico_pagados(
    "data/historico_pagados.xlsx"
    )

    df = marcar_pagados(
        df,
        df_pagados
    )

    df, eliminados = filtrar_controlados(
        df,
        df_historico
    )

    df = marcar_revisar(
        df,
        df_historico
    )

    # --------------------------------------------------
    # CARGA 090
    # --------------------------------------------------

    df_090 = cargar_090(archivo_090)

    # --------------------------------------------------
    # CRUCE 090
    # --------------------------------------------------

    df = enriquecer_con_090(
        df,
        df_090
    )

    df = validar_cesiones(df)

    # --------------------------------------------------
    # DETERMINAR BENEFICIARIO
    # --------------------------------------------------

    df = determinar_beneficiario(df)

    # --------------------------------------------------
    # CLASIFICACION
    # --------------------------------------------------

    parciales, finales, comisiones, ajustes = (
        clasificar_documentos(df)
    )

    # --------------------------------------------------
    # RESUMEN
    # --------------------------------------------------

    print()
    print("=" * 50)
    print("RESUMEN")
    print("=" * 50)

    print(f"Total documentos : {len(df)}")
    print(f"Parciales        : {len(parciales)}")
    print(f"Finales          : {len(finales)}")
    print(f"Comisiones       : {len(comisiones)}")
    print(f"Ajustes          : {len(ajustes)}")

    clasificados = (
        len(parciales)
        + len(finales)
        + len(comisiones)
        + len(ajustes)
    )

    print(f"Ya controlados  : "f"{eliminados}"
    )

    print(
        f"A revisar       : "
        f"{df['REVISAR'].sum()}"
    )

    print(
    f"Ya pagados      : "
    f"{df['YA_PAGADO'].sum()}"
    )

    # --------------------------------------------------
    # CONTRATOS SIN MATCH EN 090
    # --------------------------------------------------

    contratos_sin_match = (
        df["UNIDADES_ORIGINALES_090"]
        .isna()
        .sum()
    )

    print()
    print("=" * 50)
    print("VALIDACION 090")
    print("=" * 50)

    print(
        f"Contratos sin match 090 : "
        f"{contratos_sin_match}"
    )

    print()
    print("=" * 50)
    print("BENEFICIARIOS")
    print("=" * 50)

    print(
        df["TIPO_BENEFICIARIO"]
        .value_counts(dropna=False)
    )

    print()
    print("=" * 50)
    print("CESIONES")
    print("=" * 50)

    print(
        df["RESULTADO_CESION"]
        .value_counts(dropna=False)
    )

    # exportar_resultado(df)
    exportar_resultado(
    df,
    parciales,
    finales,
    comisiones,
    ajustes
    )
    print()
    print("=" * 50)
    print("PROCESO FINALIZADO")
    print("=" * 50)


if __name__ == "__main__":
    main()