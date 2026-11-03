"""Pruebas de Liberación con datos inventados."""

from datetime import date, datetime

import openpyxl
import pytest

from liberacion import cargas
from liberacion.config import CONFIG_POR_DEFECTO
from liberacion.limpieza import limpiar_pagadas
from liberacion.motor import controlar, filas_output_e1, liberar_manual, preparar_020, resumen_paquetes
from liberacion.salida import exportar_output_e1
from liberacion.servicio import ejecutar_control

CONFIG = CONFIG_POR_DEFECTO

ENC_020 = ["Corredor", "Nombre Corredor", "Cliente", "Nombre Cliente", "CUIT Cliente", "ID Transaccion",
           "Nro de Documento", "Concepto", "Descripcion Tipo de Documento", "Detalle del documento", "Fecha Documento",
           "Unidades", "Importe Total del doc CON IVA", "Importe Fiscal", "Importe Cancelado CON IVA", "Vencimiento",
           "Contrato", "Slip de Fijacion", "Descripcion del producto", "Cosecha", "Descripcion de retencion",
           "Provincia", "Alicuota", "BP Comercial", "Numero de COE/FACTURA", "Factura Asociada",
           "Tipo Factura Asociada", "Fecha de pago", "Fecha de Operacion", "Estado del pago",
           "Nombre Estado del Pago", "Usuario X1", "Nombre de aprobador", "Numero de PK", "Compania",
           "Interes En Cuenta", "Tipo Cambio En Cuenta", "Neteo", "Permuta", "Retenciones"]


def f020(id_, nro, concepto, importe, estado="H", corredor=35990001, asociada="", permuta="N", fecha=datetime(2026, 11, 1)):
    fila = [None] * len(ENC_020)
    valores = {"Corredor": corredor, "Nombre Corredor": "CORREDOR X", "ID Transaccion": id_, "Nro de Documento": nro,
               "Concepto": concepto, "Fecha Documento": fecha, "Importe Cancelado CON IVA": importe,
               "Factura Asociada": asociada, "Estado del pago": estado, "Permuta": permuta}
    for clave, valor in valores.items():
        fila[ENC_020.index(clave)] = valor
    return fila


ENC_067 = ["Fecha Generacion de Netting", "Fecha De Transmision de Netting Emision", "Hora Transm Netting Emision",
           "Fecha Anulacion de Netting", "Tipo de Documento X1", "N° de X1", "Estado del X1", "Id Interface",
           "ID Permuta", "Abook del Vendedor Productor", "Codigo tributario del Vendedor", "Razon Social Vendedor",
           "Abook del Beneficiario", "CUIT Beneficiario", "Razon Social Beneficiario", "Abook del Benef Alterna",
           "Codigo tributario del Benef Alter", "Razon Social Benef Alter", "Instrumento del Pago",
           "Nombre Instrumento del Pago", "Letra del Instrumento de pago", "Codigo BANCO", "Nombre BANCO",
           "Cuenta bancaria", "Importe a Pagar Moneda Local", "Usuario Generador de Netting",
           "Usuario Liberacion de Netting", "Validaciones Coherentes", "Nombre Validaciones Coherentes",
           "ID Transaction", "Usuario de Aprobacion del Pago"]


def f067(id_, letra, importe):
    fila = [None] * len(ENC_067)
    for clave, valor in {"ID Transaction": id_, "Letra del Instrumento de pago": letra,
                         "Importe a Pagar Moneda Local": importe, "Instrumento del Pago": "D",
                         "Nombre Instrumento del Pago": "Transferencias E1", "Nombre BANCO": "BANCO PRUEBA",
                         "Cuenta bancaria": "0001"}.items():
        fila[ENC_067.index(clave)] = valor
    return fila


def prop(n, doc, tipo_doc, total, tipo="PAGAR", benef="CLIENTE", accion=""):
    return dict(tipo_benef="VENDEDOR", tipo=tipo, ab_benef=1, benef=benef, doc=doc, tipo_doc=tipo_doc, desc="",
                total=total, n_propuesta=n, accion=accion, observaciones="", grupo=1, ventana="24", generado="",
                fecha_proceso="", clave="")


def _t020(filas):
    claves = {"Corredor": "ab_corredor", "ID Transaccion": "id", "Nro de Documento": "nro", "Concepto": "concepto",
              "Fecha Documento": "fecha_doc", "Importe Cancelado CON IVA": "importe", "Factura Asociada": "factura_asociada",
              "Estado del pago": "estado", "Permuta": "permuta"}
    registros = []
    for fila in filas:
        r = {campo: fila[ENC_020.index(col)] for col, campo in claves.items()}
        r["asociadas"] = [int(x) for x in str(r["factura_asociada"] or "").split("-") if x]
        registros.append(r)
    return preparar_020(registros, CONFIG)


def _t067(filas):
    return [{"id": f[ENC_067.index("ID Transaction")], "letra": f[ENC_067.index("Letra del Instrumento de pago")],
             "importe": f[ENC_067.index("Importe a Pagar Moneda Local")]} for f in filas]


def _control(propuestas, filas_020, filas_067=()):
    control = controlar(propuestas, _t020(filas_020), _t067(filas_067), CONFIG)
    return {p["n_propuesta"]: p for p in resumen_paquetes(control.propuestas)}


def test_paquete_ok_se_libera():
    paquetes = _control(
        [prop(1, 63001, "L#", 1000.0), prop(1, 907, "RI", -100.0, tipo="COBRAR")],
        [f020(2147001, 63001, "L#", 1000.0), f020(2147001, 907, "RI", 100.0)],  # RI viene positivo: se invierte
    )
    p = paquetes[1]
    assert p["id"] == 2147001 and p["control"] == "LIBERAR" and p["estado_ne"] == "H - Pendiente de liberar"
    assert all(f["control_montos"] == "OK" and f["devengados"] == "OK" for f in p["filas"])


def test_sin_id_monto_menor_y_falta_l():
    paquetes = _control(
        [prop(1, 70001, "L#", 1.0),                                # no está en el 020
         prop(2, 63002, "L#", 900.0), prop(2, 63003, "L#", 500.0)],
        [f020(2147002, 63002, "L#", 1000.0)],
        [f067(2147002, "K", 0)],
    )
    assert paquetes[1]["id"] == "NO SE ENCONTRO" and paquetes[1]["control"] == "NO SE ENCONTRO"
    filas = paquetes[2]["filas"]
    assert filas[0]["control_montos"] == "MONTO - MENOR"
    assert filas[1]["control_tipo"] == "ERROR- FALTA DOC L#"
    assert filas[0]["monto_liberar"] == "OK-S/PARA LIBERAR"         # cuenta K en 0
    assert paquetes[2]["control"] == "MANUAL"


def test_cronologia_y_monto_por_liberar():
    paquetes = _control(
        [prop(1, 63010, "L#", 5.0), prop(1, 63011, "L#", 7.0),
         prop(2, 63020, "L#", 3.0), prop(2, 63021, "L#", 4.0)],
        [f020(10, 63011, "L#", 7.0), f020(11, 63020, "L#", 3.0)],
        [f067(11, "K", 1500.0)],
    )
    # El ID 10 sale del segundo documento? No: el ID se toma del primer documento de la propuesta.
    assert paquetes[1]["id"] == "NO SE ENCONTRO"
    assert paquetes[2]["filas"][0]["monto_liberar"] == "ERROR-MONTO POR LIBERAR"
    assert paquetes[2]["control"] == "MANUAL"

    cronologia = _control(
        [prop(3, 63030, "L#", 5.0), prop(3, 63031, "L#", 8.0), prop(3, 63032, "L#", 2.0)],
        [f020(12, 63030, "L#", 5.0), f020(12, 63032, "L#", 2.0)],
    )
    assert cronologia[3]["filas"][0]["cronologia"] == "ERROR CRONOLOGIA" and cronologia[3]["control"] == "MANUAL"


def test_devengados_permuta_y_compensa():
    paquetes = _control(
        [prop(1, 63040, "L#", 100.0, accion="PERMUTA"), prop(1, 910, "RI", -10.0, tipo="COBRAR")],
        [f020(20, 63040, "L#", 100.0, permuta="S"), f020(20, 910, "RI", 10.0),
         f020(20, 999, "RT", 5.0, asociada="910")],               # RT devengado asociado a un descuento de la propuesta
    )
    assert paquetes[1]["filas"][0]["permuta"] == "OK" and paquetes[1]["control"] == "LIBERAR"

    mal = _control(
        [prop(2, 63041, "L#", 100.0, accion="PERMUTA"), prop(2, 911, "RI", -10.0, tipo="COBRAR")],
        [f020(21, 63041, "L#", 100.0, permuta="N"), f020(21, 911, "RI", 10.0), f020(21, 998, "RT", 5.0, asociada="12345")],
    )
    filas = mal[2]["filas"]
    assert filas[0]["permuta"] == "ERROR PERMUTA" and filas[0]["devengados"] == "ERROR DOC DEVENGADOS"
    assert mal[2]["control"] == "MANUAL"

    compensa = _control(
        [prop(3, 63042, "L#", 100.0), prop(3, 1802, "QJ", -30.0, tipo="COBRAR")],
        [f020(22, 63042, "L#", 100.0), f020(22, 1802, "QJ", 10.0), f020(22, 1802, "QJ", 20.0)],  # QJ repetido: se suma
    )
    assert compensa[3]["filas"][1]["control_montos"] == "OK" and compensa[3]["control"] == "COMPENSA-LIBERAR"


def test_output_e1_y_liberacion_manual(tmp_path):
    paquetes = list(_control(
        [prop(1, 63050, "L#", 1.0), prop(2, 63051, "L#", 9.0), prop(3, 63052, "L#", 1.0)],
        [f020(30, 63050, "L#", 1.0), f020(31, 63051, "L#", 2.0), f020(32, 63052, "L#", 1.0, estado="A")],
        [f067(31, "K", 7.0)],                                            # quedó plata por liberar en la K
    ).values())
    assert [p["control"] for p in paquetes] == ["LIBERAR", "MANUAL", "LIBERAR"]
    liberar_manual(paquetes[1])
    assert filas_output_e1(paquetes) == [(30, "H", "SECUNDARIA"), (31, "H", "SECUNDARIA")]  # el 32 ya está en A
    ruta = tmp_path / "Netting_liberar.xlsx"
    assert exportar_output_e1(ruta, paquetes) == 2
    assert exportar_output_e1(ruta, paquetes) == 2                     # se agrega al final, como la macro
    hoja = openpyxl.load_workbook(ruta)["E1"]
    assert [c.value for c in hoja[1]] == ["ID Transacción", "Estado", "Proceso"] and hoja.max_row == 5


def _xlsx(ruta, encabezado, filas, hoja="Hoja1"):
    libro = openpyxl.Workbook()
    h = libro.active
    h.title = hoja
    h.append(encabezado)
    for fila in filas:
        h.append(fila)
    libro.save(ruta)
    return str(ruta)


def test_corrida_desde_registro_y_limpieza(tmp_path):
    # Registro de Netting con dos paquetes de una corrida
    enc_reg = ["Clave", "Estado", "Fecha proceso", "Generado", "Ventana", "N° propuesta", "AB", "Beneficiario",
               "Tipo beneficiario", "Movimiento", "Origen", "N° documento", "Tipo doc", "ID largo", "Total", "Acción",
               "Observaciones", "ID pago E1", "Descripción", "Grupo"]
    gen = "02/11/2026 10:00"
    filas_reg = [
        ["L#63060X", "EN PROPUESTA", "02/11/2026", gen, "24 hs", 54701, 1, "CLIENTE UNO", "VENDEDOR", "A pagar",
         "Histórico", 63060, "L#", "L#63060X", 1000.0, "", "", "", "Liquidación Parcial", 1],
        ["077|RI|920", "EN PROPUESTA", "02/11/2026", gen, "24 hs", 54701, 1, "CLIENTE UNO", "VENDEDOR", "A descontar",
         "077", 920, "RI", "", -50.0, "", "", "", "FACTURA", 1],
        ["L#63061X", "EN PROPUESTA", "02/11/2026", gen, "24 hs", 54702, 2, "CLIENTE DOS", "VENDEDOR", "A pagar",
         "Histórico", 63061, "L#", "L#63061X", 700.0, "", "", "", "Liquidación Final", 1],
    ]
    ruta_reg = _xlsx(tmp_path / "Netting_Propuestos.xlsx", enc_reg, filas_reg, hoja="Propuestos")
    corridas = cargas.listar_corridas(ruta_reg)
    assert corridas[0]["generado"] == gen and corridas[0]["ventanas"] == {"24": 2}

    ruta_020 = _xlsx(tmp_path / "020.xlsx", ENC_020, [f020(40, 63060, "L#", 1000.0), f020(40, 920, "RI", 50.0)])
    ruta_067 = _xlsx(tmp_path / "067.xlsx", ENC_067, [f067(40, "K", 950.0)])
    fuente = {"tipo": "registro", "ruta": ruta_reg, "generado": gen, "ventana": "24"}
    resultado = ejecutar_control(fuente, ruta_020, ruta_067, CONFIG)
    controles = {p["n_propuesta"]: p["control"] for p in resultado.paquetes}
    assert controles == {54701: "LIBERAR", 54702: "NO SE ENCONTRO"}
    hoja = openpyxl.load_workbook(ruta_reg)["Propuestos"]
    titulos = [c.value for c in hoja[1]]
    fila = [c.value for c in hoja[2]]
    assert fila[titulos.index("ID pago E1")] == 40 and fila[titulos.index("Estado")] == "CON ID DE PAGO"

    # Limpieza: el 020 nuevo muestra el pago en A
    enc_hist = ["Numero Doc", "Tipo Doc", "Contrato", "Total a Pagar", "Fecha Pago", "id_largo", "id_corto"]
    ruta_hist = _xlsx(tmp_path / "Historico.xlsx", enc_hist, [
        [63060, "L#", "K1", 1000.0, datetime(2026, 11, 3), "L#63060X", "C60"],
        [63060, "L#", "K1", 0.0, datetime(2026, 11, 3), "L#63060X", "C60"],   # segunda línea del mismo documento
        [63061, "L#", "K2", 700.0, datetime(2026, 11, 3), "L#63061X", "C61"],
        [63099, "L#", "K3", 10.0, datetime(2026, 12, 1), "L#63099X", "C99"],
    ], hoja="Historico_Controlados")
    ruta_020b = _xlsx(tmp_path / "020_nuevo.xlsx", ENC_020, [
        f020(40, 63060, "L#", 1000.0, estado="A"), f020(40, 920, "RI", 50.0, estado="A"),
        f020(41, 63070, "L#", 5.0, estado="H")])
    ruta_pag = tmp_path / "historico_pagados.xlsx"
    previa = limpiar_pagadas(ruta_020b, ruta_hist, ruta_pag, date(2026, 11, 2), date(2026, 11, 4), simular=True)
    assert previa.filas_movidas == 2 and not ruta_pag.exists()
    hecho = limpiar_pagadas(ruta_020b, ruta_hist, ruta_pag, date(2026, 11, 2), date(2026, 11, 4),
                            ruta_registro=ruta_reg)
    assert hecho.documentos == [(63060, "L#", 40)] and hecho.filas_movidas == 2
    assert [d[0] for d in hecho.pendientes] == [63061]                 # quedó por pagar con fecha vencida
    assert len(hecho.omitidos_estado) == 1 and len(hecho.copias) == 1
    restantes = [r[0] for r in openpyxl.load_workbook(ruta_hist).active.iter_rows(min_row=2, values_only=True)]
    assert restantes == [63061, 63099]
    pagados = openpyxl.load_workbook(ruta_pag).active
    tit = [c.value for c in pagados[1]]
    assert "id_largo" in tit and "Fecha Acreditación" in tit and pagados.max_row == 3
    reg = openpyxl.load_workbook(ruta_reg)["Propuestos"]
    tit_reg = [c.value for c in reg[1]]
    estados = [r[tit_reg.index("Estado")] for r in reg.iter_rows(min_row=2, values_only=True)]
    assert estados == ["LIBERADO", "LIBERADO", "EN PROPUESTA"]


def test_propuestas_desde_archivo_de_la_macro(tmp_path):
    enc = ["Tipo de beneficiario", "Tipo", "AB Corredos", "CORREDOR", "AB Vendedor", "VENDEDOR", "AB Beneficiario",
           "Beneficiario", "N de Docu", "TIPO de Docu", "Descripcion de Docu", "Total", "Fecha Emision", "Contrato",
           "N_PROPUESTA", "Doc Incluidos", "COMBOBOX", "Observaciones", "GRUPOS"]
    ruta = _xlsx(tmp_path / "Propuestas_Netting.xlsx", enc, [
        ["VENDEDOR", "PAGAR", 0, None, 1, "V", 1, "V", 63080, "L#", "Liq", 10.0, None, "K1", 100, None, "PERMUTA", "", 2]],
        hoja="Propuestas_24")
    filas = cargas.cargar_desde_propuestas(ruta, "24").filas
    assert filas[0]["doc"] == 63080 and filas[0]["accion"] == "PERMUTA" and filas[0]["grupo"] == 2
    with pytest.raises(cargas.ErrorDeCarga):
        cargas.cargar_desde_propuestas(ruta, "48")


def test_estado_p_cuenta_como_liberado(tmp_path):
    paquetes = list(_control(
        [prop(1, 63090, "L#", 1.0), prop(2, 63091, "L#", 1.0), prop(3, 63092, "L#", 1.0)],
        [f020(50, 63090, "L#", 1.0, estado="P"), f020(51, 63091, "L#", 1.0, estado="A"),
         f020(52, 63092, "L#", 1.0, estado="H")],
    ).values())
    assert filas_output_e1(paquetes) == [(52, "H", "SECUNDARIA")]   # A y P ya están liberados

    ruta_hist = _xlsx(tmp_path / "Historico.xlsx", ["Numero Doc", "Tipo Doc", "Fecha Pago"],
                      [[63090, "L#", None], [63091, "L#", None], [63092, "L#", None]])
    ruta_020 = _xlsx(tmp_path / "020.xlsx", ENC_020, [f020(50, 63090, "L#", 1.0, estado="P"),
                                                      f020(51, 63091, "L#", 1.0, estado="A"),
                                                      f020(52, 63092, "L#", 1.0, estado="H")])
    previa = limpiar_pagadas(ruta_020, ruta_hist, tmp_path / "pag.xlsx", date(2026, 11, 2), date(2026, 11, 3),
                             simular=True)
    assert sorted(d[0] for d in previa.documentos) == [63090, 63091]
    assert [o[0] for o in previa.omitidos_estado] == [63092]


def test_pie_data_refresh_no_es_un_documento(tmp_path):
    ruta = _xlsx(tmp_path / "020.xlsx", ENC_020, [f020(60, 63100, "L#", 1.0), ["Data Refresh Date: 09/11/2026"]])
    assert [f["nro"] for f in cargas.cargar_020(ruta).filas] == [63100]
    ruta = _xlsx(tmp_path / "067.xlsx", ENC_067, [f067(60, "K", 0), ["Data Refresh Date: 09/11/2026"]])
    assert [f["id"] for f in cargas.cargar_067(ruta).filas] == [60]
