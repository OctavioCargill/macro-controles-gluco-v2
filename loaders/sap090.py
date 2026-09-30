import pandas as pd


def cargar_090(ruta_archivo: str) -> pd.DataFrame:

    df = pd.read_excel(
        ruta_archivo,
        header=2
    )

    # eliminar filas vacías
    df = df.dropna(
        subset=["Contrato"]
    )

    # eliminar posibles filas informativas SAP
    df = df[
        ~df["Contrato"]
        .astype(str)
        .str.contains(
            "Data Refresh",
            na=False
        )
    ]

    df = df.reset_index(drop=True)

    print(f"090 cargado: {len(df)} registros")

    return df
