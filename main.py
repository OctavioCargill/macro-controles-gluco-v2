import warnings
from datetime import date

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="openpyxl"
)

from processors.fechas_pago import (
    asignar_dias_pago,
    calcular_fecha_pago,
    calcular_fecha_final,
    validar_fecha_pago
)

from utils.fecha_control import (
    obtener_fecha_control
)

from processors.resultado_final import (
    calcular_resultado_final
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
    print("Version 0.5 Stable")
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
    
    df = asignar_dias_pago(df)

    df = calcular_fecha_pago(df)

    df = calcular_fecha_final(df)

    df = validar_fecha_pago(df)

    df = determinar_beneficiario(df)

    df = validar_cesiones(df)

    df = calcular_resultado_final(df)

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

    print(f"Ya controlados   : {eliminados}")
    print(f"A revisar        : {df['REVISAR'].sum()}")
    print(f"Ya pagados       : {df['YA_PAGADO'].sum()}")

    # --------------------------------------------------
    # VALIDACION 090
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

    # --------------------------------------------------
    # BENEFICIARIOS
    # --------------------------------------------------

    print()
    print("=" * 50)
    print("BENEFICIARIOS")
    print("=" * 50)

    conteo = (
        df["TIPO_BENEFICIARIO"]
        .value_counts(dropna=False)
    )

    for tipo, cantidad in conteo.items():
        print(f"{tipo:<12} : {cantidad}")

    print()
    print("VALIDACION")

    resultado = (
        df["RESULTADO_BENEFICIARIO"]
        .value_counts(dropna=False)
    )

    for estado, cantidad in resultado.items():
        print(f"{estado:<20} : {cantidad}")

    # --------------------------------------------------
    # CESIONES
    # --------------------------------------------------

    print()
    print("=" * 50)
    print("CESIONES")
    print("=" * 50)

    conteo_cesiones = (
        df["RESULTADO_CESION"]
        .value_counts(dropna=False)
    )

    for resultado, cantidad in conteo_cesiones.items():
        print(f"{resultado:<30} : {cantidad}")

    # --------------------------------------------------
    # RESULTADO FINAL
    # --------------------------------------------------

    print()
    print("=" * 50)
    print("RESULTADO FINAL")
    print("=" * 50)

    resultado_final = (
        df["RESULTADO_FINAL"]
        .value_counts(dropna=False)
    )

    print()
    print("=" * 50)
    print("VALIDACION FECHAS")
    print("=" * 50)
    
    conteo_fechas = (
        df["RESULTADO_FECHA"]
        .value_counts(dropna=False)
    )
    
    for resultado, cantidad in conteo_fechas.items():
        print(
            f"{resultado:<25} : {cantidad}"
        )

    for estado, cantidad in resultado_final.items():
        print(f"{estado:<20} : {cantidad}")

    manuales = df[
        df["RESULTADO_FINAL"]
        == "CONTROL MANUAL"
    ]

    print()
    print(
        f"Documentos a revisar : "
        f"{len(manuales)}"
    )

    print()
    print("MOTIVOS")
    
    motivos = (
        df["MOTIVO_CONTROL"]
        .replace("", "CONTROL MACRO")
        .value_counts()
    )
    
    for motivo, cantidad in motivos.items():
    
        print(
            f"{motivo:<25} : {cantidad}"
    )

    # ==================================================
    # CONTROL POWERAPP
    # ==================================================

    print()
    print("=" * 80)
    print("CONTROL POWERAPP")
    print("=" * 80)

    control_powerapp = (
        df[
            df["RESULTADO_FINAL"] == "CONTROL MACRO"
        ]
        .copy()
    )

    # Una sola fila por liquidación
    control_powerapp = (
        control_powerapp
        .sort_values(
            [
                "Numero Doc",
                "Fecha Pago"
            ]
        )
        .drop_duplicates(
            subset=["Numero Doc"],
            keep="first"
        )
    )

    # Ordenar para lectura
    control_powerapp = (
        control_powerapp
        .sort_values(
            [
                "Fecha Pago",
                "Numero Doc"
            ]
        )
    )

    columnas = [
        "Numero Doc",
        "Tipo Doc",
        "Contrato",
        "Fecha Pago",
        "FECHA_FINAL",
        "AB Beneficiario del Pago",
        "Total a Pagar"
    ]

    columnas = [
        c
        for c in columnas
        if c in control_powerapp.columns
    ]

    print(
        control_powerapp[
            columnas
        ].to_string(index=False)
    )

    print()
    print(
        f"Liquidaciones únicas : "
        f"{len(control_powerapp)}"
    )

    print()
    print("Distribucion por Fecha Pago")
    print("-" * 40)

    print(
        control_powerapp["Fecha Pago"]
        .value_counts()
        .sort_index()
    )

    # --------------------------------------------------
    # EXPORTACION
    # --------------------------------------------------
    
    exportar_resultado(
        df,
        parciales,
        finales,
        comisiones,
        ajustes
    )
            
    print()
    print("=" * 50)
    print("EXPORTACION")
    print("=" * 50)
    print("Archivo generado: resultado_gluco_v2.xlsx")

    print()
    print("=" * 50)
    print("PROCESO FINALIZADO")
    print("=" * 50)


if __name__ == "__main__":
    main()