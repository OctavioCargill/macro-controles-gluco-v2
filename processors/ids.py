import pandas as pd


def normalizar_nro_legal(df):
    if df is None or df.empty:
        return df

    if "Nro_Legal" not in df.columns:
        df["Nro_Legal"] = ""

    df["Nro_Legal"] = df["Nro_Legal"].replace("", pd.NA)

    if "Numero documento fiscal" in df.columns:
        df["Nro_Legal"] = df["Nro_Legal"].fillna(df["Numero documento fiscal"])
        df["Nro_Legal"] = df["Nro_Legal"].astype(str).str.replace(".0", "", regex=False)

    if "COE" not in df.columns:
        df["COE"] = df["Nro_Legal"]

    if "Nro. Legal" not in df.columns:
        df["Nro. Legal"] = df["Nro_Legal"]

    return df


def limpiar_numero(valor):

    if pd.isna(valor):
        return ""

    try:
        return str(int(float(valor)))
    except:
        return str(valor)


def generar_id_corto(df):

    df["id_corto"] = (
        df["Numero de CAE COE Factura"]
        .apply(limpiar_numero)
        +
        df["Numero documento fiscal"]
        .apply(limpiar_numero)
    )

    return df


def generar_id_largo(df):

    fecha = pd.to_datetime(
        df["Fecha Pago"],
        dayfirst=True,
        errors="coerce"
    ).dt.strftime("%d%m%Y")

    df["id_largo"] = (
        df["Tipo Doc"].astype(str)
        +
        df["Numero Doc"].astype(str)
        +
        df["Numero de CAE COE Factura"]
        .apply(limpiar_numero)
        +
        df["Numero documento fiscal"]
        .apply(limpiar_numero)
        +
        fecha.fillna("")
    )

    return df

# ---------------------------------------------------------------------------------------------------------
# Históricos que no vienen de la app (macro vieja en .xlsb, archivos editados a mano, etc.)
# ---------------------------------------------------------------------------------------------------------

_COLUMNAS_NUMERO_DOC = ("Numero Doc", "Documento")


def _clave_columna(texto):
    import unicodedata

    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("_", " ").split())


def _id_como_texto(valor):
    """Un ID guardado como texto. Si Excel lo guardó como número y perdió dígitos, devuelve "" (se recalcula)."""
    if valor is None or valor is pd.NA or valor is pd.NaT:
        return ""
    if isinstance(valor, float):
        if pd.isna(valor) or not valor.is_integer() or abs(valor) >= 1e15:
            return ""
        return str(int(valor))
    if isinstance(valor, int):
        return str(valor)
    texto = str(valor).strip()
    if texto.lower() in ("nan", "none", "nat"):
        return ""
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    if "e+" in texto.lower():
        return ""
    return texto


def _fecha_ddmmaaaa(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)) or valor is pd.NaT:
        return ""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 1 <= valor < 2958466:  # número de serie de Excel (así vienen las fechas en un .xlsb)
            return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(valor))).strftime("%d%m%Y")
        return ""
    fecha = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    return "" if pd.isna(fecha) else fecha.strftime("%d%m%Y")


def normalizar_columnas_id(df):
    """Deja las columnas id_largo / id_corto como texto, con el mismo formato que genera CONTROLAR.

    Acepta los históricos de la macro anterior: títulos «ID LARGO» / «ID CORTO», número de documento en la
    columna «Documento», fechas como número de serie de Excel e ID corto guardado como número (Excel le
    recorta dígitos: en ese caso se toma del ID largo o se recalcula). Si no hay datos para armar un ID,
    queda vacío y no coincide con nada.
    """
    if df is None:
        return df
    df = df.copy()

    renombres = {}
    for columna in df.columns:
        clave = _clave_columna(columna)
        for destino in ("id_largo", "id_corto"):
            if clave == destino.replace("_", " ") and columna != destino and destino not in df.columns \
                    and destino not in renombres.values():
                renombres[columna] = destino
    df = df.rename(columns=renombres)

    for columna in ("id_largo", "id_corto"):
        df[columna] = df[columna].map(_id_como_texto) if columna in df.columns else ""
    if df.empty:
        return df

    col_doc = next((c for c in _COLUMNAS_NUMERO_DOC if c in df.columns), None)
    prefijo = None
    if col_doc and "Tipo Doc" in df.columns:
        prefijo = df["Tipo Doc"].map(lambda v: "" if pd.isna(v) else str(v).strip()) + df[col_doc].apply(limpiar_numero)

    # ID corto que Excel guardó como número: se recupera del ID largo (tipo + doc + ID corto + ddmmaaaa)
    if prefijo is not None:
        def _corto_desde_largo(i):
            largo, pre = df.at[i, "id_largo"], prefijo.at[i]
            if pre and largo.startswith(pre) and len(largo) > len(pre) + 8:
                return largo[len(pre):-8]
            return ""
        faltan = df["id_corto"].eq("")
        for i in df.index[faltan]:
            df.at[i, "id_corto"] = _corto_desde_largo(i)

    # Lo que siga vacío se calcula como en CONTROLAR, si están los datos
    columnas_calculo = ("Numero de CAE COE Factura", "Numero documento fiscal")
    if all(c in df.columns for c in columnas_calculo):
        corto = df["Numero de CAE COE Factura"].apply(limpiar_numero) + df["Numero documento fiscal"].apply(limpiar_numero)
        faltan = df["id_corto"].eq("")
        df.loc[faltan, "id_corto"] = corto[faltan]
        if prefijo is not None and "Fecha Pago" in df.columns:
            largo = prefijo + corto + df["Fecha Pago"].map(_fecha_ddmmaaaa)
            faltan = df["id_largo"].eq("")
            df.loc[faltan, "id_largo"] = largo[faltan]
    return df


def ids_validos(serie):
    """Conjunto de IDs como texto, sin vacíos."""
    return {v for v in serie.map(_id_como_texto) if v}
