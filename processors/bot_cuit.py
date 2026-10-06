import pandas as pd


def validar_bot_cuit(df, df_bot):

    df = df.copy()

    df["BOT_ENCONTRADO"] = False

    df["RESULTADO_BOT_CUIT"] = (
        "NO ENCONTRADO EN BOT"
    )

    if "Nro_Contrato" not in df_bot.columns:
        return df

    contratos_bot = (
        df_bot["Nro_Contrato"]
        .astype(str)
        .str.strip()
    )

    for idx in df.index:

        contrato = str(
            df.loc[idx, "Contrato"]
        ).strip()

        match = df_bot[
            contratos_bot == contrato
        ]

        if match.empty:
            continue

        df.loc[
            idx,
            "BOT_ENCONTRADO"
        ] = True

        cuit_vendedor = str(
            df.loc[idx, "Vendedor"]
        ).strip()

        cuit_corredor = str(
            df.loc[idx, "Corredor"]
        ).strip()

        bot_vendedor = str(
            match.iloc[0]
            .get(
                "Vendedor_CUIT",
                ""
            )
        ).strip()

        bot_corredor = str(
            match.iloc[0]
            .get(
                "Corredor_CUIT",
                ""
            )
        ).strip()

        if (
            cuit_vendedor == bot_vendedor
            or
            cuit_corredor == bot_corredor
        ):

            df.loc[
                idx,
                "RESULTADO_BOT_CUIT"
            ] = "OK"

        else:

            df.loc[
                idx,
                "RESULTADO_BOT_CUIT"
            ] = "ERROR-CUIT"

    return df