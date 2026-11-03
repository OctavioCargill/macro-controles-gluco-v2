"""Pruebas de Netting con datos inventados (no se usan datos reales)."""

from datetime import date, datetime

import openpyxl
import pytest

from netting import cargas
from netting.calendario import dias_a_pagar
from netting.motor import (
    Avisos, Estado, armar_comisiones, armar_propuestas, clasificar_beneficiario, numerar,
    preparar_077, preparar_historico,
)
from netting.salida import asignar_grupos, datos_para_e1, poner_observaciones, resumen_propuestas
from netting.servicio import (
    _validar_estatus, ejecutar_netting, generar_salida, guardar_datos_paquete, resumen_por_fecha_de_pago,
)

FERIADOS = {date(2026, 11, 23)}


# ---------------------------------------------------------------- días a pagar

@pytest.mark.parametrize("hoy, pago, esperado", [
    (date(2026, 10, 26), datetime(2026, 10, 26), 0),      # hoy
    (date(2026, 10, 26), datetime(2026, 10, 20), 0),      # vencida
    (date(2026, 10, 26), None, 0),                        # sin fecha
    (date(2026, 10, 26), datetime(2026, 10, 27), 1),      # mañana
    (date(2026, 10, 26), datetime(2026, 10, 28), 2),
    (date(2026, 10, 30), datetime(2026, 11, 2), 1),       # viernes → lunes
    (date(2026, 10, 30), datetime(2026, 10, 31), 1),      # viernes → sábado cuenta hasta el lunes
    (date(2026, 11, 20), datetime(2026, 11, 24), 1),      # viernes → martes con lunes feriado
    (date(2026, 10, 26), datetime(2026, 10, 26, 15, 0), 1),  # hoy con hora: la macro cuenta 1
])
def test_dias_a_pagar(hoy, pago, esperado):
    assert dias_a_pagar(pago, hoy, FERIADOS) == esperado


# ---------------------------------------------------------------- tipo de beneficiario

def _h(**kw):
    base = dict(corredor="", vendedor="V", cobrador="V", cesion="", usuario_anulacion="")
    base.update(kw)
    return base


@pytest.mark.parametrize("fila, esperado", [
    (_h(corredor="C", cobrador="C"), "CORREDOR"),
    (_h(corredor="C"), "CORREDOR-DIRECTO"),
    (_h(), "VENDEDOR"),
    (_h(corredor="C", cesion="X"), "CORREDOR-CESION"),
    (_h(cesion="X"), "VENDEDOR-CESION"),
    (_h(usuario_anulacion="CARGILL", corredor="C", cobrador="C"), "CARGILL"),
    (_h(cobrador="OTRO"), ""),
])
def test_clasificar(fila, esperado):
    assert clasificar_beneficiario(fila) == esperado


# ---------------------------------------------------------------- numeración y grupos

def _p(ab, tipo="CORREDOR", tipo_doc="L#", corredor="C", vendedor="V", benef=None):
    return dict(ab_benef=ab, benef=benef or f"B{ab}", tipo_benef=tipo, tipo_doc=tipo_doc,
                corredor=corredor, vendedor=vendedor, n_propuesta="", total=1.0, tipo_pagar="PAGAR")


def test_numerar_24_agrupa_por_ab_y_separa_directos_y_comisiones():
    filas = [
        _p(1), _p(1), _p(1, tipo_doc="C0"), _p(1, tipo_doc="C0"),     # liquidaciones y comisiones del mismo AB
        _p(2, tipo="CORREDOR-DIRECTO", corredor="C", vendedor="V1"),
        _p(2, tipo="CORREDOR-DIRECTO", corredor="C", vendedor="V1"),  # mismo corredor y vendedor: misma propuesta
        _p(2, tipo="CORREDOR-DIRECTO", corredor="C", vendedor="V2"),  # cambia vendedor: otra
        _p(3, tipo="VENDEDOR-CESION"), _p(3, tipo="VENDEDOR-CESION"),  # cesión de vendedor: una por documento
    ]
    estado = Estado([], [], 100, set(), Avisos())
    numerar(filas, estado, "24")
    assert [f["n_propuesta"] for f in filas] == [101, 101, 102, 102, 103, 103, 104, 105, 106]
    assert estado.ultimo_numero == 106


def test_grupos_redondeo_y_tope():
    filas = [dict(n_propuesta=n) for n in (1, 1, 2, 3, 4, 5)]
    assert asignar_grupos(filas, 2, "24") == 5      # 5/2 = 2,5 → 2 (redondeo al par)
    assert [f["grupo"] for f in filas] == [1, 1, 1, 2, 2, 2]  # tope en el último analista
    filas48 = [dict(n_propuesta=n) for n in (1, 2, 3, 4, 5)]
    asignar_grupos(filas48, 2, "48")
    assert [f["grupo"] for f in filas48] == [1, 1, 2, 2, 3]   # 48 hs no tiene tope (como la macro)


# ---------------------------------------------------------------- corrida completa con archivos inventados

HOY = date(2026, 10, 28)  # miércoles
D0, D1, D2, D5 = datetime(2026, 10, 28), datetime(2026, 10, 29), datetime(2026, 10, 30), datetime(2026, 11, 4)

ENCABEZADO_HIST = [
    "Documento", "Tipo Doc", "Descripcion de la liquidacion", "Contrato", "Numero documento fiscal",
    "Usuario anulacion", "Corredor", "Nombre Corredor", "Vendedor", "Nombre Vendedor",
    "AB Beneficiario del Pago", "Nombre Beneficiario del Pago", "AB Beneficiario de Cesion",
    "Nombre Beneficiario de Cesion", "AB Beneficiario Contrato", "Nombre Beneficiario Contrato",
    "Total a Pagar", "Fecha Generacion Liquidacion", "Fecha Pago", "Condicion de Inscripcion",
    "Usuario Alta", "Anticipo/Barter", "ID CORTO", "ID LARGO", "Pago Contra", "Condicion de Pago",
    "Dias A pagar",
]


def _hist(doc, desc, contrato, ab_corr, corr, ab_vend, vend, ab_cob, cob, total, pago, ab_ces="", ces="", aa=""):
    return [doc, "L#" if "Comisi" not in desc else "C0", desc, contrato, "", "", ab_corr, corr, ab_vend, vend,
            ab_cob, cob, ab_ces, ces, 0, "", total, D0, pago, "", "", "", "", f"ID{doc}", "", "", aa]


FILAS_HIST = [
    # Corredor AGRO SUR (AB 500) cobra dos liquidaciones a 24 hs de dos vendedores distintos
    _hist(1001, "Liquidación Final", "K1", 500, "AGRO SUR SA", 900, "CAMPO UNO", 500, "AGRO SUR SA", 1000.0, D1),
    _hist(1002, "Liquidación Final", "K2", 500, "AGRO SUR SA", 901, "CAMPO DOS", 500, "AGRO SUR SA", 2000.0, D0),
    # Vendedor directo LA ESTANCIA (AB 902) cobra a 24 hs
    _hist(1003, "Liquidación Parcial", "K3", "0", "", 902, "LA ESTANCIA", 902, "LA ESTANCIA", 5000.0, D1),
    # Corredor directo: corredor PAMPA (501) pero cobra el vendedor CAMPO TRES (903), 48 hs
    _hist(1004, "Liquidación Final", "K4", 501, "PAMPA CEREALES", 903, "CAMPO TRES", 903, "CAMPO TRES", 700.0, D2),
    # Vendedor con cesión a 24 hs
    _hist(1005, "Liquidación Final", "K5", "0", "", 904, "CAMPO CUATRO", 904, "CAMPO CUATRO", 300.0, D1, 950, "BANCO X"),
    # Comisión del corredor AGRO SUR a 24 hs
    _hist(1006, "Comisiónes", "K1", 500, "AGRO SUR SA", 900, "CAMPO UNO", 500, "AGRO SUR SA", 50.0, D0),
    # Vence en más de 48 hs: queda afuera
    _hist(1007, "Liquidación Final", "K6", 500, "AGRO SUR SA", 900, "CAMPO UNO", 500, "AGRO SUR SA", 999.0, D5),
    # Marcado X en la macro: se descarta
    _hist(1008, "Liquidación Final", "K1", 500, "AGRO SUR SA", 900, "CAMPO UNO", 500, "AGRO SUR SA", 1.0, D0, aa="X"),
]

ENCABEZADO_077 = [
    "Codigo BP Comercial", "BP Comercial", "Cod Cliente", "CLIENTE", "CUIT", "COD TIPO DOC", "TIPO_DOC",
    "NRO DOC", "EMISOR", "NUMERO FACTURA", "NUMERO LEGAL", "DETALLE", "PRODUCTO", "DESC_PRODUCTO", "COSECHA",
    "FECHA_DOC", "VENCIMIENTO_DOC", "DIAS_ATRASO", "VL_LIMITE_CREDITO", "Importe Doc",
    "Saldo pend aplicar Netting", "Intereses", "Intereses COMPENSATORIO", "Reajuste TC", "FECHA_REPORTE",
    "Factura Asociada", "Tipo Factura Asociada", "Contrato", "Corredor", "CUIT Corredor", "AB Corredor",
    "Compania",
]


def _f077(cliente_ab, cliente, tipo, nro, saldo, contrato, corredor="", fecha=datetime(2026, 9, 1)):
    return ["0151195000", "Glucovil", cliente_ab, cliente, "", tipo, "", str(nro), "", "", "", f"Factura {nro}",
            "", "", "", fecha, None, 0, None, saldo, saldo, 0, None, 0, None, "", "", contrato, corredor, "", "", "51511"]


FILAS_077 = [
    _f077(900, "CAMPO UNO", "RI", 7001, 100.0, "K1", "AGRO SUR SA"),       # del corredor, contrato en el 090
    _f077(901, "CAMPO DOS", "AH", 7002, 40.0, "K2", "AGRO SUR SA"),        # del corredor
    _f077(900, "CAMPO UNO", "RI", 7003, 10.0, "K9", "AGRO SUR SA"),        # contrato que no está en el 090: se borra
    _f077(902, "LA ESTANCIA", "RM", 7004, 60.0, "K3"),                     # del vendedor directo
    _f077(902, "LA ESTANCIA", "ZZ", 7005, 60.0, "K3"),                     # tipo fuera de alcance
    _f077(903, "CAMPO TRES", "RI", 7006, 30.0, "K4", "PAMPA CEREALES"),     # corredor directo: no se descuenta
]

ENCABEZADO_090 = ["Contrato"] + [f"c{i}" for i in range(2, 14)] + ["Nombre Vendedor", "c15", "c16", "c17", "Nombre Corredor"]


def _f090(contrato, vendedor, corredor):
    fila = [""] * len(ENCABEZADO_090)
    fila[0], fila[13], fila[17] = contrato, vendedor, corredor
    return fila


FILAS_090 = [
    _f090("K1", "CAMPO UNO", "AGRO SUR SA"),
    _f090("K2", "CAMPO DOS", "AGRO SUR SA"),
    _f090("K3", "LA ESTANCIA", None),
    _f090("K4", "CAMPO TRES", "PAMPA CEREALES"),
    _f090("K5", "CAMPO CUATRO", None),
]

def _xlsx(ruta, encabezado, filas, hoja="Hoja1", filas_titulo=0):
    libro = openpyxl.Workbook()
    hoja_activa = libro.active
    hoja_activa.title = hoja
    for _ in range(filas_titulo):
        hoja_activa.append(["Reporte SAP"])
    hoja_activa.append(encabezado)
    for fila in filas:
        hoja_activa.append(fila)
    libro.save(ruta)
    return str(ruta)


@pytest.fixture
def archivos(tmp_path):
    return {
        "historico": _xlsx(tmp_path / "Historico.xlsx", ENCABEZADO_HIST, FILAS_HIST),
        "077": _xlsx(tmp_path / "077.xlsx", ENCABEZADO_077, FILAS_077 + [["Data Refresh Date: hoy"]], filas_titulo=2),
        "090": _xlsx(tmp_path / "090.xlsx", ENCABEZADO_090, FILAS_090, filas_titulo=2),
    }


CONFIG = {"feriados": ["2026-01-01", "2026-11-23"], "corredores_solo_24": [], "agrupar_por_ab": True, "rutas": {}}


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setattr("netting.servicio.guardar_config", lambda c: None)
    return dict(CONFIG, rutas={"pagados": str(tmp_path / "historico_pagados.xlsx"),
                                "registro": str(tmp_path / "Netting_Propuestos.xlsx")})


def _docs(filas, tipo):
    return sorted(f["doc"] for f in filas if f["tipo"] == tipo)


def test_corrida_completa_un_paquete_por_ab(archivos, tmp_path, config):
    resultado = ejecutar_netting(archivos, HOY, 1000, config)
    p24, p48 = resultado.propuestas_24, resultado.propuestas_48

    # 24 hs: liquidaciones 1001, 1002, 1003, 1005 y la comisión 1006; no entran 1004 (48), 1007 (>48), 1008 (X)
    assert _docs(p24, "PAGAR") == [1001, 1002, 1003, 1005, 1006]
    # Descuentos: 7001 y 7002 del corredor (con contrato en el 090) y 7004 del vendedor directo
    assert _docs(p24, "COBRAR") == [7001, 7002, 7004]
    cobrar = {f["doc"]: f for f in p24 if f["tipo"] == "COBRAR"}
    assert cobrar[7001]["total"] == -100.0          # el 077 se descuenta con signo negativo

    # Un paquete por AB: AGRO SUR (liquidaciones + comisión + descuentos), LA ESTANCIA y la cesión a BANCO X
    resumen = resultado.resumen("24")
    paquetes = {r["ab_benef"]: r for r in resumen}
    assert set(paquetes) == {500, 902, 950}
    agro = paquetes[500]
    assert sorted(f["doc"] for f in agro["filas"]) == [1001, 1002, 1006, 7001, 7002]
    assert agro["a_pagar"] == 3050.0 and agro["a_descontar"] == -140.0 and agro["neto"] == 2910.0
    assert paquetes[902]["neto"] == 5000.0 - 60.0
    assert [r["n_propuesta"] for r in resumen] == [1001, 1002, 1003]
    # Dentro de cada paquete: primero lo que se paga y después los descuentos
    assert [f["tipo"] for f in agro["filas"]] == ["PAGAR", "PAGAR", "PAGAR", "COBRAR", "COBRAR"]

    assert _docs(p48, "PAGAR") == [1004] and _docs(p48, "COBRAR") == []
    assert resultado.numero_final == 1004

    # Salida: paquetes por AB, detalle plano y control
    poner_observaciones(agro, "Revisar retención")
    ruta = generar_salida(resultado, 2, tmp_path, config)
    libro = openpyxl.load_workbook(ruta)
    assert libro.sheetnames == ["Propuestas_24", "Propuestas_48", "Detalle_24", "Detalle_48", "Control"]
    hoja = libro["Propuestas_24"]
    filas = [[c.value for c in fila] for fila in hoja.iter_rows()]
    cabeceras = [f for f in filas if f[4] == "PAQUETE"]
    assert [(f[0], f[1], f[12]) for f in cabeceras] == [(1001, 500, 2910), (1002, 902, 4940), (1003, 950, 300)]
    assert cabeceras[0][14] == "Revisar retención"
    assert any(f[4] == "CUENTAS POR COBRAR" for f in filas) and any(f[4] == "CUENTA POR PAGAR" for f in filas)
    assert libro["Detalle_24"].max_row == len(p24) + 1


def test_lo_propuesto_no_vuelve_a_entrar_hasta_liberarse(archivos, tmp_path, config):
    primera = ejecutar_netting(archivos, HOY, 1000, config)
    generar_salida(primera, 1, tmp_path, config)
    generar_salida(primera, 1, tmp_path, config)  # regenerar el archivo no duplica el registro
    registro = openpyxl.load_workbook(config["rutas"]["registro"])["Propuestos"]
    assert registro.max_row - 1 == len(primera.propuestas_24) + len(primera.propuestas_48)

    segunda = ejecutar_netting(archivos, HOY, primera.numero_final, config)
    assert segunda.propuestas_24 == [] and segunda.propuestas_48 == []
    assert segunda.estadisticas["excluidos_propuestos_hist"] == 6
    assert segunda.estadisticas["excluidos_propuestos_077"] == 3

    sin_bloqueo = ejecutar_netting(archivos, HOY, primera.numero_final, dict(config, bloquear_propuestos=False))
    assert _docs(sin_bloqueo.propuestas_24, "PAGAR") == [1001, 1002, 1003, 1005, 1006]


def test_lo_pagado_queda_afuera(archivos, tmp_path, config):
    _xlsx(config["rutas"]["pagados"], ["id_largo", "id_corto"], [["ID1001", None], [None, "X"]])
    resultado = ejecutar_netting(archivos, HOY, 1000, config)
    assert 1001 not in _docs(resultado.propuestas_24, "PAGAR")
    assert resultado.estadisticas["excluidos_pagados"] == 1


def test_datos_para_buscar_en_e1():
    corredor = dict(tipo_benef="CORREDOR-DIRECTO", ab_corredor=501, ab_benef=903)
    assert datos_para_e1(corredor) == {"buscar_por": "CORREDOR", "campo_e1": "Corredor", "ab_e1": 501}
    vendedor = dict(tipo_benef="VENDEDOR", ab_corredor=0, ab_benef=902)
    assert datos_para_e1(vendedor) == {"buscar_por": "VENDEDOR", "campo_e1": "Cliente", "ab_e1": 902}


def test_id_de_pago_y_accion_quedan_en_el_registro(archivos, tmp_path, config):
    resultado = ejecutar_netting(archivos, HOY, 1000, config)
    assert {f["grupo"] for f in resultado.propuestas_24} == {1}   # grupos asignados desde el armado
    generar_salida(resultado, 1, tmp_path, config)
    paquete = resultado.resumen("24")[0]
    assert guardar_datos_paquete(resultado, paquete, config, "ok", "PERMUTA", "1777769") is True
    hoja = openpyxl.load_workbook(config["rutas"]["registro"])["Propuestos"]
    titulos = [c.value for c in hoja[1]]
    filas = [[c.value for c in f] for f in hoja.iter_rows(min_row=2)]
    del_paquete = [f for f in filas if f[titulos.index("N° propuesta")] == paquete["n_propuesta"]
                   and f[titulos.index("Ventana")] == "24 hs"]
    assert del_paquete and all(f[titulos.index("ID pago E1")] == "1777769" for f in del_paquete)
    assert all(f[titulos.index("Acción")] == "PERMUTA" for f in del_paquete)


def test_aviso_parciales_que_no_estan_en_a_o_p():
    hist = [dict(doc=1, contrato="K1", estatus="A"), dict(doc=2, contrato="K1", estatus="R"),
            dict(doc=3, contrato="K2", estatus="P")]
    propuestas = [dict(tipo="PAGAR", contrato="K1"), dict(tipo="PAGAR", contrato="K2")]
    avisos = Avisos()
    _validar_estatus(hist, propuestas, avisos)
    assert propuestas[0].get("alerta_estatus") and not propuestas[1].get("alerta_estatus")
    assert "K1: 2 (R)" in avisos.revisar[0]


def test_resumen_por_fecha_de_pago(archivos, config):
    resultado = ejecutar_netting(archivos, HOY, 1000, config)
    por_fecha = {d["fecha"]: d for d in resumen_por_fecha_de_pago(resultado)}
    assert por_fecha[D0.date()]["docs_24"] == 2 and por_fecha[D1.date()]["docs_24"] == 3
    assert por_fecha[D2.date()]["docs_48"] == 1


def test_errores_de_carga_claros(archivos, tmp_path):
    with pytest.raises(cargas.ErrorDeCarga, match="faltan columnas obligatorias"):
        cargas.cargar_historico(_xlsx(tmp_path / "malo.xlsx", ["Documento", "Tipo Doc", "Total a Pagar", "Fecha Pago"], [[1, "L#", 1, D0]]))
    with pytest.raises(cargas.ErrorDeCarga, match="no se encontró la fila de encabezados"):
        cargas.cargar_090(archivos["077"])


def test_sin_propuestas_avisa_proximas_fechas():
    from netting.servicio import _avisar_sin_propuestas
    avisos = Avisos()
    hist = [{"fecha_pago": datetime(2026, 11, 10)}, {"fecha_pago": datetime(2026, 11, 11)}, {"fecha_pago": None}]
    _avisar_sin_propuestas(hist, date(2026, 11, 3), avisos)
    assert "03/11/2026" in avisos.revisar[0] and "10/11/2026, 11/11/2026" in avisos.revisar[0]
