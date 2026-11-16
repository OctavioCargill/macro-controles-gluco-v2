"""Validación contra la Power App (captura) y la factura (PDF), con datos inventados."""

import importlib.util
from pathlib import Path

import pytest

from validacion import normalizar as N
from validacion.comparador import COINCIDE, DISTINTO, NO_SE_VE, campo, comparar_captura, comparar_factura
from validacion.lectura import Renglon

DATOS = Path(__file__).parent / "datos_validacion"
HAY_OCR = importlib.util.find_spec("rapidocr") is not None and importlib.util.find_spec("onnxruntime") is not None
HAY_PDF = importlib.util.find_spec("pypdf") is not None


def _r(texto, x0, y0, x1=None, y1=None):
    return Renglon(texto, x0, y0, x1 if x1 is not None else x0 + 8 * len(texto), y1 if y1 is not None else y0 + 20)


def _estados(validacion):
    return {r.titulo: r.estado for r in validacion.resultados}


def test_normalizar():
    assert N.importe("$ 15.020.000,00") == 15020000.0
    assert N.importe("15,020,000.00") == 15020000.0
    assert N.importe("206.334,84") == 206334.84
    assert N.importe("(1.500,00)") == -1500.0
    assert N.codigo("3400-00085001") == "340000085001"
    assert N.codigo(340000085001.0) == "340000085001"
    assert N.codigo("34OOOOO85OO1", ocr=True) == "340000085001"
    assert str(N.fecha("10/11/2026")) == "2026-11-10" and str(N.fecha("2026-11-10")) == "2026-11-10"
    assert N.importes_en("Importe neto a pagar 14.995.000,00") == [14995000.0]


def test_captura_formulario_etiqueta_arriba():
    # Formulario como la Power App: etiqueta arriba, valor abajo, en tres columnas
    renglones = [
        _r("Nro. Doc. Interno", 44, 91), _r("Nro. Legal", 390, 89), _r("Contrato", 738, 90),
        _r("85001", 44, 115), _r("340000085001", 391, 115), _r("904000001A", 738, 115),
        _r("Total a pagar", 391, 157), _r("Kilos", 736, 157),
        _r("$ 15.020.000,00", 391, 181), _r("30.000", 735, 181),
        _r("Fecha de Pago", 736, 221), _r("11/11/2026", 737, 247),
        _r("Conforme", 389, 287), _r("A", 390, 313, 400, 333),
    ]
    campos = [campo("Nro. Doc. Interno", "85001"), campo("Nro. Legal (COE)", "3400085001",
                                                         alternativas=["340000085001"]),
              campo("Contrato", "904000001A"), campo("Total a pagar", "$ 15.200.000,00"), campo("Kilos", "30000.0"),
              campo("Fecha de Pago", "10/11/2026"), campo("Conforme", "A"), campo("Obs. de Pago", "DEMO"),
              campo("Vendedor", "-")]
    validacion = comparar_captura(campos, renglones)
    estados = _estados(validacion)
    assert estados == {"Nro. Doc. Interno": COINCIDE, "Nro. Legal (COE)": COINCIDE, "Contrato": COINCIDE,
                       "Total a pagar": DISTINTO, "Kilos": COINCIDE, "Fecha de Pago": DISTINTO,
                       "Conforme": COINCIDE, "Obs. de Pago": NO_SE_VE}         # «-» no se compara
    total = next(r for r in validacion.resultados if r.titulo == "Total a pagar")
    assert total.leido == "$ 15.020.000,00" and validacion.hay_diferencias
    assert validacion.resumen == "5 coinciden · 2 distintos · 1 no se ven"


def test_captura_etiqueta_a_la_izquierda_y_tabla():
    renglones = [
        _r("Contrato:", 20, 10, 100, 30), _r("904000001A", 120, 10, 220, 30),
        _r("Total a pagar: $ 15.200.000,00", 20, 50, 320, 70),
        _r("Concepto", 20, 100, 100, 120), _r("Base", 300, 100, 340, 120), _r("Importe", 420, 100, 500, 120),
        _r("Retención IIBB Buenos Aires", 20, 130, 220, 150), _r("13.755.656,11", 240, 130, 330, 150),
        _r("1,50", 360, 130, 400, 150), _r("206.334,84", 420, 130, 500, 150),
    ]
    campos = [campo("Contrato", "904000001A"), campo("Total a pagar", "$ 15.200.000,00"),
              campo("Retención: Retención IIBB Buenos Aires", "$ 206.334,84", tipo="importe"),
              campo("Vendedor", "LA ESPERANZA DEMO SA")]
    campos[2].alias = ["Retención IIBB Buenos Aires"]
    estados = _estados(comparar_captura(campos, renglones))
    assert estados["Contrato"] == COINCIDE and estados["Total a pagar"] == COINCIDE
    assert estados["Retención: Retención IIBB Buenos Aires"] == COINCIDE      # la celda «Importe», no la «Base»
    assert estados["Vendedor"] == NO_SE_VE


def test_texto_corto_no_se_busca_suelto():
    # «DEMO» aparece dentro de un nombre: no cuenta como el dato «Obs. de Pago»
    renglones = [_r("CEREALES DEL LITORAL DEMO SA", 10, 10)]
    assert _estados(comparar_captura([campo("Obs. de Pago", "DEMO")], renglones))["Obs. de Pago"] == NO_SE_VE


def test_factura_texto():
    renglones = [Renglon(t) for t in ["C.O.E.: 3400-00085001", "Contrato: 904000001A", "Kilos: 30.000",
                                      "Subtotal 13.735.656,11", "Retencion IIBB Buenos Aires 1,50% 206.334,84",
                                      "Importe neto a pagar 14.995.000,00"]]
    campos = [campo("Total a pagar", "$ 15.200.000,00"), campo("Nro. Legal (COE)", "340000085001"),
              campo("Contrato", "904000001A"), campo("Kilos", "30000"), campo("Retención: IIBB", "$ 206.334,84", "importe"),
              campo("Importe imponible (subtotal)", "13.000.000", "importe")]
    validacion = comparar_factura(campos, renglones)
    estados = _estados(validacion)
    assert estados == {"Total a pagar": DISTINTO, "Nro. Legal (COE)": COINCIDE, "Contrato": COINCIDE, "Kilos": COINCIDE,
                       "Retención: IIBB": COINCIDE, "Importe imponible (subtotal)": NO_SE_VE}
    total = next(r for r in validacion.resultados if r.titulo == "Total a pagar")
    assert total.leido == "$ 14.995.000,00" and "neto a pagar" in total.nota


@pytest.mark.skipif(not HAY_PDF, reason="falta pypdf")
def test_leer_pdf_con_texto():
    from validacion.lectura import leer_pdf

    textos = " ".join(r.texto for r in leer_pdf(DATOS / "factura_mal.pdf"))
    assert "904000001A" in textos and "14.995.000,00" in textos


@pytest.mark.skipif(not (HAY_OCR and HAY_PDF), reason="falta el OCR (rapidocr / onnxruntime)")
def test_ocr_captura_y_factura_escaneada():
    from validacion.lectura import leer_imagen, leer_pdf

    campos = [campo("Total a pagar", "$ 15.200.000,00"), campo("Contrato", "904000001A"),
              campo("Fecha de Pago", "10/11/2026"), campo("Nro. Doc. Interno", "85001")]
    estados = _estados(comparar_captura(campos, leer_imagen(DATOS / "captura_mal.png")))
    assert estados == {"Total a pagar": DISTINTO, "Contrato": COINCIDE, "Fecha de Pago": DISTINTO,
                       "Nro. Doc. Interno": COINCIDE}
    escaneada = comparar_factura(campos[:2], leer_pdf(DATOS / "factura_escaneada.pdf"))
    assert _estados(escaneada) == {"Total a pagar": DISTINTO, "Contrato": COINCIDE}
