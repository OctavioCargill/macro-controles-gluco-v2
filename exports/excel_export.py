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


def preparar_exportacion(df):

    columnas_principales = [
        "Numero Doc",
        "Tipo Doc",
        "Contrato",
        "Vendedor",
        "Corredor",
        "Numero de CAE COE Factura",
        "Numero documento fiscal",
        "id_corto",
        "id_largo",
        "TIPO_BENEFICIARIO",
        "RESULTADO_BENEFICIARIO",
        "RESULTADO_CESION",
        "REVISAR",
        "YA_PAGADO",
        "CUIT_VENDEDOR_090",
        "CUIT_CORREDOR_090",
        "UNIDADES_ORIGINALES_090",
        "RESULTADO_FINAL",
        "MOTIVO CONTROL",
        "DIAS_PAGO",
        "FECHA_CALCULADA",
        "FECHA_FINAL",
        "RESULTADO_FECHA",
    ]

    columnas_existentes = [
        c
        for c in columnas_principales
        if c in df.columns
    ]

    return df[columnas_existentes].copy()


def ajustar_columnas(writer, sheet_name, df):

    worksheet = writer.sheets[sheet_name]

    for idx, col in enumerate(df.columns):

        try:

            largo = max(
                len(str(col)),
                df[col]
                .astype(str)
                .str.len()
                .max()
            )

        except Exception:

            largo = 20

        worksheet.set_column(
            idx,
            idx,
            min(largo + 3, 40)
        )


def crear_control_powerapp(df):

    columnas = [
        "Numero Doc",
        "Tipo Doc",
        "Contrato",
        "Producto",
        "Cosecha",
        "AB Beneficiario del Pago",
        "Fecha Pago",
        "Total a Pagar",
        "Imponible",
        "Importe Fiscal",
        "Valor Comprobante",
        "RESULTADO_FINAL",
        "MOTIVO_CONTROL"
    ]

    columnas = [
        c
        for c in columnas
        if c in df.columns
    ]

    return df[columnas].copy()

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

    resultado_export = preparar_exportacion(df)

    parciales_export = preparar_exportacion(parciales)

    finales_export = preparar_exportacion(finales)

    comisiones_export = preparar_exportacion(comisiones)

    ajustes_export = preparar_exportacion(ajustes)

    sin_match = preparar_exportacion(
        df[
            df["UNIDADES_ORIGINALES_090"].isna()
        ]
    )

    ya_pagados = preparar_exportacion(
        df[
            df["YA_PAGADO"] == "SI"
        ]
    )

    revisar = preparar_exportacion(
        df[
            df["REVISAR"] == "SI"
        ]
    )

    resumen = pd.DataFrame(
        {
            "Concepto": [
                "Total Documentos",
                "Parciales",
                "Finales",
                "Comisiones",
                "Ajustes",
                "Ya Pagados",
                "A Revisar",
                "Sin Match 090"
            ],
            "Cantidad": [
                len(df),
                len(parciales),
                len(finales),
                len(comisiones),
                len(ajustes),
                len(ya_pagados),
                len(revisar),
                len(sin_match)
            ]
        }
    )

    a_controlar = crear_a_controlar(df)
    
    control_powerapp = (
        crear_control_powerapp(df)
    )
    
    with pd.ExcelWriter(
        archivo_salida,
        engine="xlsxwriter"
    ) as writer:

        control_powerapp.to_excel(
            writer,
            sheet_name="CONTROL_POWERAPP",
            index=False
        )
        
        a_controlar.to_excel(
            writer,
            sheet_name="A_CONTROLAR",
            index=False
        )
        
        resumen.to_excel(
            writer,
            sheet_name="Resumen",
            index=False
        )

        resultado_export.to_excel(
            writer,
            sheet_name="Resultado",
            index=False)

def crear_a_controlar(df):

    columnas = [
        "Numero Doc",
        "Tipo Doc",
        "Contrato",
        "Producto",
        "Cosecha",
        "Vendedor",
        "Corredor",
        "AB Beneficiario del Pago",
        "Fecha Pago",
        "Total a Pagar",
        "Importe Fiscal",
        "Valor Comprobante",
        "RESULTADO_FINAL",
        "MOTIVO_CONTROL"
    ]

    columnas = [
        c
        for c in columnas
        if c in df.columns
    ]

    return df[columnas].copy()