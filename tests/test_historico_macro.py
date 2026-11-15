"""Históricos que no vienen de la app: el .xlsb de la macro anterior o archivos editados a mano."""

import pandas as pd

from processors.historico import cargar_historico, filtrar_controlados, marcar_revisar
from processors.historico_pagados import cargar_historico_pagados, marcar_pagados
from processors.ids import normalizar_columnas_id


def _macro_vieja():
    # Como lo lee pandas del .xlsb: «ID LARGO» / «ID CORTO», «Documento», ID corto como número que perdió dígitos
    return pd.DataFrame({
        "Documento": [62533.0, 128.0],
        "Tipo Doc": ["L#", "H7"],
        "Numero documento fiscal": ["331009477565", "331006442467"],
        "Fecha Pago": [46310.0, 45357.0],
        "ID CORTO": [3.31009477565331e23, 3.31006442467331e23],
        "ID LARGO": ["L#6253333100947756533100947756515102026", "H712833100644246733100644246706032024"],
    })


def test_macro_vieja_renombra_y_recupera_id_corto():
    df = normalizar_columnas_id(_macro_vieja())
    assert list(df["id_largo"]) == ["L#6253333100947756533100947756515102026", "H712833100644246733100644246706032024"]
    assert list(df["id_corto"]) == ["331009477565331009477565", "331006442467331006442467"]


def test_sin_ids_los_calcula_como_controlar():
    df = normalizar_columnas_id(pd.DataFrame({
        "Numero Doc": [85001], "Tipo Doc": ["L#"], "Numero de CAE COE Factura": [340000085001],
        "Numero documento fiscal": [3400085001], "Fecha Pago": ["10/11/2026"],
    }))
    assert df.at[0, "id_corto"] == "3400000850013400085001"
    assert df.at[0, "id_largo"] == "L#85001340000085001340008500110112026"


def test_formato_de_la_app_no_cambia():
    original = pd.DataFrame({"id_largo": ["L#1A10112026"], "id_corto": ["A"], "Tipo Doc": ["L#"]})
    df = normalizar_columnas_id(original)
    assert list(df["id_largo"]) == ["L#1A10112026"] and list(df["id_corto"]) == ["A"]


def test_controlar_con_historico_de_la_macro(tmp_path):
    ruta = tmp_path / "Historico_Documentos_Controlados.xlsx"
    _macro_vieja().to_excel(ruta, index=False)
    historico = cargar_historico(ruta)
    df = pd.DataFrame({"id_largo": ["L#6253333100947756533100947756515102026", "OTRO"],
                       "id_corto": ["331009477565331009477565", "X"]})
    filtrado, eliminados = filtrar_controlados(df, historico)
    assert eliminados == 1 and list(filtrado["id_largo"]) == ["OTRO"]
    assert list(marcar_revisar(filtrado, historico)["REVISAR"]) == [False]


def test_pagados_sin_archivo_o_sin_columnas(tmp_path):
    df = pd.DataFrame({"id_largo": ["A"], "id_corto": ["B"]})
    assert not marcar_pagados(df.copy(), cargar_historico_pagados(tmp_path / "no_existe.xlsx"))["YA_PAGADO"].any()
    ruta = tmp_path / "historico_pagados.xlsx"
    pd.DataFrame({"Numero Doc": [1], "ID LARGO": ["A"]}).to_excel(ruta, index=False)
    assert marcar_pagados(df.copy(), cargar_historico_pagados(ruta))["YA_PAGADO"].all()
