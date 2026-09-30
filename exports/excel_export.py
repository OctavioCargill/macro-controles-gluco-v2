import pandas as pd
from pathlib import Path


def convertir_booleanos(df):

    df = df.copy()

    columnas = [
        "REVISAR",
        "YA_PAGADO",
        "CONTRATO_ENCONTRADO_090"
    ]

    for col in columnas:

        if col in df.columns:

            df[col] = df[col].map(
                {
                    True: "SI",
                    False: "NO"
                }
            )

    return df


def exportar_resultado(
    df,
    parciales,
    finales,
    comisiones,
    ajustes
):

    carpeta_salida = Path("output")

    carpeta_salida.mkdir(
        exist_ok=True
    )

    archivo_salida = (
        carpeta_salida /
        "resultado_gluco_v2.xlsx"
    )

    df = convertir_booleanos(df)

    resumen = pd.DataFrame(
        {
            "Concepto": [
                "Total",
                "Parciales",
                "Finales",
                "Comisiones",
                "Ajustes"
            ],
            "Cantidad": [
                len(df),
                len(parciales),
                len(finales),
                len(comisiones),
                len(ajustes)
            ]
        }
    )

    sin_match = df[
        df["UNIDADES_ORIGINALES_090"].isna()
    ]

    ya_pagados = df[
        df["YA_PAGADO"] == "SI"
    ]

    revisar = df[
        df["REVISAR"] == "SI"
    ]

    with pd.ExcelWriter(
        archivo_salida,
        engine="xlsxwriter"
    ) as writer:

        resumen.to_excel(
            writer,
            sheet_name="Resumen",
            index=False
        )

        df.to_excel(
            writer,
            sheet_name="Resultado",
            index=False
        )

        parciales.to_excel(
            writer,
            sheet_name="Parciales",
            index=False
        )

        finales.to_excel(
            writer,
            sheet_name="Finales",
            index=False
        )

        comisiones.to_excel(
            writer,
            sheet_name="Comisiones",
            index=False
        )

        ajustes.to_excel(
            writer,
            sheet_name="Ajustes",
            index=False
        )

        sin_match.to_excel(
            writer,
            sheet_name="Sin Match 090",
            index=False
        )

        ya_pagados.to_excel(
            writer,
            sheet_name="Ya Pagados",
            index=False
        )

        revisar.to_excel(
            writer,
            sheet_name="Revisar",
            index=False
        )

        workbook = writer.book

        formato_header = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#D9EAD3",
                "border": 1
            }
        )

        for sheet in writer.sheets.values():

            sheet.autofilter(
                0,
                0,
                10000,
                100
            )

    print()
    print("=" * 50)
    print("EXPORTACION")
    print("=" * 50)
    print(
        f"Archivo generado: {archivo_salida}"
    )

    return archivo_salida