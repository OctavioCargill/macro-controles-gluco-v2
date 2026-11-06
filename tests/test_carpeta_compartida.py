"""Carpeta de datos compartida, aviso de uso simultáneo y migración de los históricos de la macro."""

import json
import os
from datetime import datetime

import openpyxl
import pytest

from services import auditoria, bloqueo, migracion
from netting.cargas import ErrorDeCarga


# --------------------------------------------------------------------------- carpeta de datos
def test_carpeta_de_datos_configurable(tmp_path):
    base = tmp_path / "app"
    (base / "config").mkdir(parents=True)
    assert auditoria.resolver_carpeta_datos(base) == base / "data"           # sin configurar: la local
    compartida = tmp_path / "red" / "Glucovil"
    compartida.mkdir(parents=True)
    auditoria.guardar_carpeta_datos(compartida, base)
    assert auditoria.carpeta_datos_configurada(base) == compartida
    assert auditoria.resolver_estructura_runtime(base)["data"] == compartida
    assert auditoria.carpeta_datos_disponible(compartida)
    (compartida / "044_hoy.xlsx").write_text("x")
    assert auditoria.resolver_ruta_recurso("044", base_dir=base, extensiones=[".xlsx"]) == (compartida / "044_hoy.xlsx").resolve()
    auditoria.guardar_carpeta_datos(None, base)                                # volver a la local
    assert auditoria.carpeta_datos_configurada(base) is None


def test_carpeta_compartida_sin_red_no_se_crea(tmp_path):
    base = tmp_path / "app"
    (base / "config").mkdir(parents=True)
    sin_red = tmp_path / "disco_que_no_esta" / "Glucovil"
    auditoria.guardar_carpeta_datos(sin_red, base)
    rutas = auditoria.resolver_estructura_runtime(base)
    assert rutas["data"] == sin_red and not sin_red.exists()
    assert not auditoria.carpeta_datos_disponible(sin_red)
    ajustes = json.loads((base / "config" / "app_settings.json").read_text(encoding="utf-8"))
    assert ajustes["carpeta_datos"] == str(sin_red)


# --------------------------------------------------------------------------- uso simultáneo
def test_uso_exclusivo_avisa_a_la_otra_pc(tmp_path, monkeypatch):
    marca = tmp_path / bloqueo.NOMBRE_MARCA
    with bloqueo.uso_exclusivo("dando salida al netting", tmp_path):
        assert marca.exists()
        # La misma app puede seguir guardando (no se bloquea a sí misma)
        with bloqueo.uso_exclusivo("otra cosa", tmp_path):
            pass
    assert not marca.exists()

    marca.write_text(json.dumps({"usuario": "ana", "pc": "PC-NETTING", "pid": 1, "accion": "dando salida al netting",
                                 "desde": datetime.now().isoformat(timespec="seconds")}), encoding="utf-8")
    with pytest.raises(bloqueo.CarpetaEnUso, match="ana está dando salida al netting desde la PC PC-NETTING"):
        with bloqueo.uso_exclusivo("pasando al histórico", tmp_path):
            pass
    assert isinstance(bloqueo.CarpetaEnUso("x"), PermissionError)               # las pantallas ya lo muestran


def test_marca_vieja_se_ignora(tmp_path):
    marca = tmp_path / bloqueo.NOMBRE_MARCA
    marca.write_text(json.dumps({"usuario": "ana", "pc": "PC-NETTING", "pid": 1, "accion": "x",
                                 "desde": "2026-01-01T10:00:00"}), encoding="utf-8")
    with bloqueo.uso_exclusivo("pasando al histórico", tmp_path):
        assert json.loads(marca.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert not marca.exists()


# --------------------------------------------------------------------------- migración
def _como_pyxlsb():
    """Lo que devuelve pyxlsb: números, fechas e IDs numéricos vienen como float."""
    return {
        "Resumen": [["Hoja de resumen"], [None]],
        "Historico": [
            ["HISTÓRICO DE CONTROLADOS (macro)"], [None],
            ["Numero Doc", "Tipo Doc", "Contrato", "Fecha Pago", "Total a Pagar", "id_largo", "id_corto", None],
            [63001.0, "L#", "903000001A", 46336.0, 1500000.5, "L#630013300000000001", 330000000001.0, None],
            [63001.0, "L#", "903000001A", 46336.0, 0.0, "L#630013300000000001", 330000000001.0, None],
            [63002.0, "C0", "903000002A", 46337.0, 250000.0, "C0630023300000000002", 330000000002.0, None],
            [None, None, None, None, None, None, None, None],
        ],
    }


def test_migrar_historico_de_la_macro(tmp_path, monkeypatch):
    monkeypatch.setattr(migracion, "_leer_hojas", lambda ruta: _como_pyxlsb())
    origen = tmp_path / "Historico_Controlados_MACRO.xlsb"
    origen.write_bytes(b"simulado")
    informe, titulos, filas = migracion.preparar(origen, "controlados")
    assert informe.hoja == "Historico" and informe.fila_titulos == 3 and informe.filas == 3
    assert titulos == ["Numero Doc", "Tipo Doc", "Contrato", "Fecha Pago", "Total a Pagar", "id_largo", "id_corto"]
    assert filas[0][0] == 63001 and filas[0][3] == datetime(2026, 11, 10) and filas[0][6] == "330000000001"

    destino = tmp_path / "data"
    destino.mkdir()
    (destino / "Historico_Documentos_Controlados.xlsx").write_text("viejo")
    hecho = migracion.migrar(origen, "controlados", destino)
    assert hecho.verificado and hecho.copia.exists()
    hoja = openpyxl.load_workbook(destino / "Historico_Documentos_Controlados.xlsx")["Historico_Controlados"]
    valores = list(hoja.iter_rows(values_only=True))
    assert valores[0][5:] == ("id_largo", "id_corto") and len(valores) == 4
    assert valores[1][3] == datetime(2026, 11, 10) and valores[3][6] == "330000000002"


def test_migrar_calcula_ids_si_faltan(tmp_path, monkeypatch):
    monkeypatch.setattr(migracion, "_leer_hojas", lambda ruta: {"H": [
        ["Numero Doc", "Tipo Doc", "Numero de CAE COE Factura", "Numero documento fiscal", "Fecha Pago"],
        [63001.0, "L#", 330000000001.0, 3300000001.0, 46336.0],
    ]})
    origen = tmp_path / "pagados.xlsb"
    origen.write_bytes(b"simulado")
    informe, titulos, filas = migracion.preparar(origen, "pagados")
    assert informe.ids_calculados and "id_largo" in titulos and "id_corto" in titulos
    assert filas[0][titulos.index("id_largo")] == "L#63001330000000001330000000110112026"


def test_migrar_sin_tipo_doc_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(migracion, "_leer_hojas", lambda ruta: {"H": [["a", "b"], [1, 2]]})
    origen = tmp_path / "x.xlsb"
    origen.write_bytes(b"simulado")
    with pytest.raises(ErrorDeCarga, match="Tipo Doc"):
        migracion.preparar(origen, "controlados")
