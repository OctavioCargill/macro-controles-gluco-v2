from services.auditoria import APP_DATA_PATH, APP_ROOT, resolver_ruta_recurso
from loaders.sap044 import cargar_044
from loaders.sap090 import cargar_090

from processors.ids import (
    generar_id_corto,
    generar_id_largo,
    normalizar_nro_legal
)

from processors.historico import (
    cargar_historico,
    filtrar_controlados,
    marcar_revisar
)

from processors.historico_pagados import (
    cargar_historico_pagados,
    marcar_pagados
)

from processors.cruce_090 import (
    enriquecer_con_090
)

from processors.beneficiarios import (
    determinar_beneficiario
)

from processors.cesiones import (
    validar_cesiones
)

from processors.fechas_pago import (
    asignar_dias_pago,
    calcular_fecha_pago,
    calcular_fecha_final,
    validar_fecha_pago
)

from processors.resultado_final import (
    calcular_resultado_final
)

from processors.clasificador import (
    clasificar_documentos
)


def ejecutar_control(
    archivo_044,
    archivo_090
):

    df = cargar_044(archivo_044)

    df = normalizar_nro_legal(df)
    df = generar_id_corto(df)
    df = generar_id_largo(df)

    # Primero el .xlsx, que es el que escribe la app al pasar al histórico: si en la carpeta quedó también
    # un .xlsb de la macro, leerlo haría controlar contra un histórico distinto del que se actualiza.
    ruta_historico = APP_DATA_PATH / "Historico_Documentos_Controlados.xlsx"
    if not ruta_historico.exists():
        ruta_historico = resolver_ruta_recurso(
            "Historico_Documentos_Controlados",
            base_dir=APP_ROOT,
            subdir="data",
            extensiones=[".xlsb", ".xlsx", ".xls", ".csv"],
        )
    if ruta_historico is None:
        ruta_historico = APP_DATA_PATH / "Historico_Documentos_Controlados.xlsb"

    df_historico = cargar_historico(ruta_historico)

    df_pagados = cargar_historico_pagados(
        APP_DATA_PATH / "historico_pagados.xlsx"
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

    df_090 = cargar_090(
        archivo_090
    )

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

    resumen = {

        "total":
            len(df),

        "parciales":
            len(parciales),

        "finales":
            len(finales),

        "comisiones":
            len(comisiones),

        "ajustes":
            len(ajustes),

        "macro":
            (
                df["RESULTADO_FINAL"]
                == "CONTROL MACRO"
            ).sum(),

        "manual":
            (
                df["RESULTADO_FINAL"]
                == "CONTROL MANUAL"
            ).sum()
    }

    return {
        "resumen": resumen,
        "df": df
    }