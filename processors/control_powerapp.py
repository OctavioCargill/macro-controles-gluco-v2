import pandas as pd


def construir_control_powerapp(df):

    filas = []

    for numero_doc, grupo in (
        df.groupby("Numero Doc")
    ):

        if (
            grupo["RESULTADO_FINAL"]
            .iloc[0]
            != "CONTROL MACRO"
        ):
            continue

        retenciones = []

        percepciones = []

        for _, fila in grupo.iterrows():

            producto = str(
                fila["Producto"]
            )

            importe = fila[
                "Importe Fiscal"
            ]

            if "RIB" in producto:

                retenciones.append(
                    f"{producto}: "
                    f"{importe:,.2f}"
                )

            if "PIB" in producto:

                percepciones.append(
                    f"{producto}: "
                    f"{importe:,.2f}"
                )

        filas.append(
            {
                "Numero Doc":
                    numero_doc,

                "Tipo Doc":
                    grupo["Tipo Doc"]
                    .iloc[0],

                "Contrato":
                    grupo["Contrato"]
                    .iloc[0],

                "Fecha Pago":
                    grupo["Fecha Pago"]
                    .iloc[0],

                "AB Beneficiario del Pago":
                    grupo[
                        "AB Beneficiario del Pago"
                    ].iloc[0],

                "Total a Pagar":
                    grupo[
                        "Total a Pagar"
                    ].iloc[0],

                "RETENCIONES_IIBB":
                    (
                        " | ".join(
                            retenciones
                        )
                        if retenciones
                        else "N/A"
                    ),

                "PERCEPCIONES_IIBB":
                    (
                        " | ".join(
                            percepciones
                        )
                        if percepciones
                        else "N/A"
                    )
            }
        )

    return pd.DataFrame(
        filas
    )