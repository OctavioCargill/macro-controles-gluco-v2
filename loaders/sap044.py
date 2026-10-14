import pandas as pd


def cargar_044(ruta_archivo: str) -> pd.DataFrame:

    df = pd.read_excel(
        ruta_archivo,
        header=2
    )

    # Eliminar filas vacías
    df = df.dropna(
        subset=["Numero Doc"]
    )

    # Eliminar fila Data Refresh Date
    df = df[
        ~df["Numero Doc"]
        .astype(str)
        .str.contains(
            "Data Refresh",
            na=False
        )
    ]

    # Reiniciar índice
    df = df.reset_index(drop=True)

    return df