from services.auditoria import evaluar_integridad_liquidaciones


def test_integridad_ok():
    resultado = evaluar_integridad_liquidaciones(10, 10, 10, 10)
    assert resultado["estado"] == "OK"
    assert resultado["lista_para_produccion"] is True


def test_integridad_requiere_revision():
    resultado = evaluar_integridad_liquidaciones(10, 10, 8, 9)
    assert resultado["estado"] == "REQUIERE_REVISION"
    assert resultado["lista_para_produccion"] is False


def test_integridad_justificada():
    resultado = evaluar_integridad_liquidaciones(10, 10, 8, 9, justificaciones={"mostradas": "Ajuste de filtro"})
    assert resultado["estado"] == "OK_CON_JUSTIFICACION"
    assert resultado["lista_para_produccion"] is True
