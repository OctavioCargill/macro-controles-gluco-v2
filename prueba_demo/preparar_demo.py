r"""Arma una copia aparte de la app con datos inventados para probar (y grabar) Glucovil de punta a punta.

Uso, desde la carpeta del repo:
    py prueba_demo\preparar_demo.py                  fecha de proceso = hoy (o el próximo día hábil)
    py prueba_demo\preparar_demo.py --fecha 12/11/2026
    py prueba_demo\preparar_demo.py --reemplazar     borra la copia anterior y la arma de nuevo

Crea  ..\<repo>-DEMO  con el código de la app, una carpeta data solo con archivos de prueba y GUION.md
con los pasos y los resultados esperados. Las fechas de pago se calculan contra la fecha de proceso, así
que en Netting alcanza con dejar la fecha que propone la pantalla. Nada de esto toca tu carpeta data.
"""

import argparse
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parent
sys.path.insert(0, str(REPO))

import openpyxl  # noqa: E402
import pandas as pd  # noqa: E402

from netting.config import CONFIG_POR_DEFECTO  # noqa: E402
from processors.ids import generar_id_corto, generar_id_largo, normalizar_nro_legal  # noqa: E402

NO_COPIAR = ("data", "logs", "config", ".git", "build", "dist", "dist_final", "prueba_e2e", "prueba_demo",
             "__pycache__", ".pytest_cache", "*.pyc", "exports")
AVISO = "DATOS DE DEMO INVENTADOS - NO SON DATOS REALES"
COLS_044 = ['Numero Doc', 'Tipo Doc', 'Estatus Documento', 'Contrato', 'BP Comercial', 'Nombre BP Comercial', 'Slip Negociacion', 'Slip', 'Fecha de Slip', 'Numero de Slip Fijacion', 'Fecha de slip Fijacion', 'Fecha Operacion', 'Cantidad Fijada', 'Tipo de Vendedor', 'Descripcion de vendedor', 'Anulacion multa anul Fijac', 'Observacion de Anulacion', 'Usuario anulacion', 'Pago Contra', 'Condicion de Pago', 'Estado de AFIP', 'Desc Estado AFIP', 'Unidades', 'Precio', 'Moneda del Contrato', 'Tipo de Cambio', 'Moneda', 'Usuario Alta', 'Numero de emisor', 'Numero documento fiscal', 'Emision Documento', 'Tipo Documento', 'Emisor Documento', 'Centro Costo', 'Nombre Centro Costo', 'Producto', 'Descripcion de Producto', 'Cosecha', 'Descripcion de Cosecha', 'Corredor', 'Nombre Corredor', 'Vendedor', 'Nombre Vendedor', 'AB Beneficiario del Pago', 'Nombre Beneficiario del Pago', 'AB Beneficiario de Cesion', 'Nombre Beneficiario de Cesion', 'AB Beneficiario Contrato', 'Nombre Beneficiario Contrato', 'Descripcion de la liquidacion', 'Numero de CAE COE Factura', 'Tip Liquidacion', 'Porcentaje de pago', 'Fecha Pago', 'Concepto', 'Condicion de Inscripcion', 'Imponible', 'Importe Fiscal', 'Valor Comprobante', 'Total a Pagar', 'Conforme descripcion', 'Merchant', 'Importe Sellado', 'Importe Registro', 'Porcentaje Sellado', 'Ingreso Sellado', 'Sellado a Cobrar NK', 'Documentacion Presentada', 'Fecha Generacion Liquidacion', 'Total Pactado', 'Total Recibido', 'Total Fijado', 'Borrador Parcial', 'Liquidado Parcial', 'Pagado Parcial', 'Borrador Comision', 'Liquidado Comision', 'Pagado Comision', 'Borrador Final', 'Liquidado Final', 'Pagado Final', 'Volume Cedido', 'Importe Cedido', 'Fecha cierta de pago', 'Firma de boleto', 'Proviene de Canje', 'Lugar de descarga del contrato', 'Observaciones', '% Comision', 'Convenio', 'Descripcion Convenio', 'Documento Fiscal Relacionado', 'Tp Doc. Fiscal Relacionado', 'Desc Tp Doc. Fiscal Rel', 'Numero Documento Relacionado', 'Tipo Documento Relacionado', 'Anticipo/Barter', 'Cod Compania', 'Anulacion - MG', 'Mes Ref', 'Ano Ref']
FERIADOS = {date.fromisoformat(f) for f in CONFIG_POR_DEFECTO.get("feriados", [])}


def habil(dia):
    return dia.weekday() < 5 and dia not in FERIADOS


def sumar_habiles(dia, n):
    paso = 1 if n >= 0 else -1
    for _ in range(abs(n)):
        dia += timedelta(days=paso)
        while not habil(dia):
            dia += timedelta(days=paso)
    return dia


def dt(dia):
    return datetime(dia.year, dia.month, dia.day)


def guardar(ruta, encabezado, filas, hoja, pie=None):
    libro = openpyxl.Workbook()
    h = libro.active
    h.title = hoja
    h.append([f"Compania: 99999 ({AVISO})"])
    h.append([])
    h.append(encabezado)
    for fila in filas:
        h.append(fila)
    if pie:
        h.append([pie])
    libro.save(ruta)


# ---------------------------------------------------------------- actores (inventados)
LITORAL, CENTRO = (36990001, "CEREALES DEL LITORAL DEMO SA"), (36990002, "GRANOS DEL CENTRO DEMO SRL")
ESPERANZA, SANJORGE = (43990021, "LA ESPERANZA DEMO SA"), (43990022, "SAN JORGE DEMO SH")
ALBERTO, ACACIAS = (43990023, "DON ALBERTO DEMO SA"), (43990024, "LAS ACACIAS DEMO SRL")
OMBU, ARROYOS = (43990025, "EL OMBU DEMO SA"), (43990026, "TRES ARROYOS DEMO SA")
NOGALES, BANCO = (43990027, "LOS NOGALES DEMO SA"), (36990090, "BANCO DEMO SA")
OTRO = (43990099, "OTRO BENEFICIARIO DEMO")
SIN = (0, None)
PRODUCTO = ("6318AR", "MAIZ DURO")
P = ("Liquidación Parcial", "LPG-LIQUID PARCIAL-COMPRAS")
F = ("Liquidación Final C/Parcial", "LPG-FINAL-COMPRAS")


def l044(doc, tipo, desc, tip, contrato, corr, vend, benef, total, gen, pago, cond="CONTADO CONTRA ENTREGA",
         cesion=(None, None), coe=None, fiscal=None, cedido=None):
    f = {c: None for c in COLS_044}
    f.update({
        "Numero Doc": doc, "Tipo Doc": tipo, "Estatus Documento": "A", "Contrato": contrato,
        "BP Comercial": "0999999000", "Nombre BP Comercial": "PLANTA DEMO", "Pago Contra": "ENTREGA",
        "Condicion de Pago": cond, "Unidades": 30000, "Precio": round(total / 30000, 2), "Moneda": "ARS",
        "Moneda del Contrato": "ARS", "Usuario Alta": "DEMO", "Numero de emisor": 5100,
        "Numero documento fiscal": fiscal or 3400000000 + doc, "Emision Documento": dt(gen), "Tipo Documento": "LPG",
        "Producto": PRODUCTO[0], "Descripcion de Producto": PRODUCTO[1], "Cosecha": "2526",
        "Descripcion de Cosecha": "2025/2026", "Corredor": corr[0], "Nombre Corredor": corr[1],
        "Vendedor": vend[0], "Nombre Vendedor": vend[1], "AB Beneficiario del Pago": benef[0],
        "Nombre Beneficiario del Pago": benef[1], "AB Beneficiario de Cesion": cesion[0],
        "Nombre Beneficiario de Cesion": cesion[1], "AB Beneficiario Contrato": benef[0],
        "Nombre Beneficiario Contrato": benef[1], "Descripcion de la liquidacion": desc,
        "Numero de CAE COE Factura": coe or 340000000000 + doc, "Tip Liquidacion": tip, "Porcentaje de pago": 100,
        "Fecha Pago": dt(pago), "Concepto": "DEMO", "Imponible": round(total / 1.105, 2), "Importe Fiscal": total,
        "Valor Comprobante": total, "Total a Pagar": total, "Fecha Generacion Liquidacion": dt(gen),
        "Volume Cedido": cedido, "Cod Compania": 99999, "Mes Ref": pago.month, "Ano Ref": pago.year,
        "Observaciones": AVISO,
    })
    return [f[c] for c in COLS_044]


def generar(data, hoy):
    p24, p48 = sumar_habiles(hoy, 1), sumar_habiles(hoy, 2)          # pagan mañana y pasado (hábiles)
    g24, g48 = sumar_habiles(hoy, -1), hoy                            # generadas ayer y hoy (contado: 2 hábiles)
    lejos, viejo = sumar_habiles(hoy, 8), sumar_habiles(hoy, -10)
    filas_044 = [
        # --- 24 hs
        l044(85001, "L#", *P, "904000001A", LITORAL, ESPERANZA, LITORAL, 15200000.00, g24, p24),
        l044(85002, "L#", *F, "904000002A", LITORAL, SANJORGE, LITORAL, 9800000.00, g24, p24),
        l044(85003, "L#", *P, "904000003A", SIN, ALBERTO, ALBERTO, 7400000.00, g24, p24),
        l044(85004, "H7", None, "LSG-AJUSTE", "904000003A", SIN, ALBERTO, ALBERTO, -120000.00, g24, p24),
        l044(85005, "L#", *P, "904000004A", CENTRO, ACACIAS, CENTRO, 5600000.00, g24, p24),
        l044(85006, "L#", *F, "904000005A", SIN, OMBU, OMBU, 3900000.00, g24, p24),
        l044(85007, "L#", *P, "904000006A", SIN, ARROYOS, ARROYOS, 4500000.00, g24, p24, cesion=BANCO, cedido=10000),
        l044(85008, "L#", *P, "904000007A", SIN, NOGALES, NOGALES, 2300000.00, g24, p24),
        # --- 48 hs
        l044(85009, "L#", *F, "904000008A", CENTRO, ESPERANZA, ESPERANZA, 6100000.00, g48, p48),
        l044(85010, "L#", *P, "904000002A", LITORAL, SANJORGE, LITORAL, 2700000.00, g48, p48),
        # --- controlada pero todavía no vence
        l044(85011, "L#", *P, "904000001A", LITORAL, ESPERANZA, LITORAL, 3300000.00, sumar_habiles(lejos, -2), lejos),
        # --- casos de CONTROL
        l044(85012, "L#", *P, "904999999A", LITORAL, ESPERANZA, LITORAL, 1000000.00, g24, p24),
        l044(85013, "L#", *F, "904000003A", SIN, ALBERTO, ALBERTO, 1500000.00, g24, p24, coe=340000078013, fiscal=3400078013),
        l044(85014, "L#", *P, "904000005A", SIN, OMBU, OMBU, 900000.00, g24, p24),
        l044(85015, "L#", *P, "904000006A", SIN, ARROYOS, ARROYOS, 800000.00, g24, p24, cesion=BANCO, cedido=99999),
        l044(85016, "L#", *P, "904000004A", CENTRO, ACACIAS, OTRO, 600000.00, g24, p24),
        l044(85017, "L#", *P, "904000002A", LITORAL, SANJORGE, LITORAL, 2000000.00, sumar_habiles(lejos, -1), sumar_habiles(lejos, 1)),
    ]
    guardar(data / "044_DEMO.xlsx", COLS_044, filas_044, "044", pie=f"Data Refresh Date: {hoy:%d/%m/%Y} (DEMO)")

    enc_090 = ["Contrato", "Estado", "Tipo Contrato", "Info", "Fecha de Emision", "Fecha de Operacion",
               "Fecha Vencim. Intencion Hasta", "IV Especial", "BP Comercial Origen", "Nombre BP Comercial Origen",
               "BP comercial reasignada", "Nombre BP comercial reasignada", "Vendedor", "Nombre Vendedor",
               "CUIT Vendedor", "Rol Vendedor", "Corredor", "Nombre Corredor", "CUIT Corredor", "Unid. Originales"]
    inicio = dt(hoy - timedelta(days=120))

    def f090(contrato, vend, corr, unid=30000):
        return [contrato, "E - Executada", "Precio Fijo", "Compra Precio Fij", inicio, inicio, None, None, "0999999000",
                "PLANTA DEMO", None, None, vend[0], vend[1], 30999000000 + vend[0] % 1000, "VENDEDOR (PRODUCTOR)",
                corr[0], corr[1], 30999000000 + corr[0] % 1000 if corr[0] else None, unid]
    guardar(data / "090_DEMO.xlsx", enc_090, [
        f090("904000001A", ESPERANZA, LITORAL), f090("904000002A", SANJORGE, LITORAL),
        f090("904000003A", ALBERTO, SIN), f090("904000004A", ACACIAS, CENTRO),
        f090("904000005A", OMBU, SIN), f090("904000006A", ARROYOS, SIN, unid=50000),
        f090("904000007A", NOGALES, SIN), f090("904000008A", ESPERANZA, CENTRO),
    ], "090")

    enc_077 = ["Codigo BP Comercial", "BP Comercial", "Cod Cliente", "CLIENTE", "CUIT", "COD TIPO DOC", "TIPO_DOC",
               "NRO DOC", "EMISOR", "NUMERO FACTURA", "NUMERO LEGAL", "DETALLE", "PRODUCTO", "DESC_PRODUCTO",
               "COSECHA", "FECHA_DOC", "VENCIMIENTO_DOC", "DIAS_ATRASO", "VL_LIMITE_CREDITO", "Importe Doc",
               "Saldo pend aplicar Netting", "Intereses", "Intereses COMPENSATORIO", "Reajuste TC", "FECHA_REPORTE",
               "Factura Asociada", "Tipo Factura Asociada", "Contrato", "Corredor", "CUIT Corredor", "AB Corredor",
               "Compania"]

    def f077(cli, tipo, nro, detalle, dias, saldo, contrato, corr=SIN):
        fecha = dt(hoy - timedelta(days=dias))
        return ["0999999000", "PLANTA DEMO", cli[0], cli[1], "30999000000", tipo, "Invoice", str(nro), "5100", "", "",
                detalle, *PRODUCTO, "2025/2026", fecha, fecha, 0, None, saldo, saldo, 0, None, 0, None, "", "",
                contrato, corr[1], None, corr[0], "99999"]
    guardar(data / "077_DEMO.xlsx", enc_077, [
        f077(ESPERANZA, "RI", 62001, "FACTURA - SECADO", 50, 1100000.00, "904000001A", LITORAL),
        f077(SANJORGE, "AH", 62002, "FACTURA - FLETE", 45, 400000.00, "904000002A", LITORAL),
        f077(ALBERTO, "RI", 62003, "FACTURA - SERVICIOS", 70, 600000.00, "904000003A"),
        f077(ACACIAS, "RT", 62004, "FACTURA - ZARANDEO", 30, 300000.00, "904000004A", CENTRO),
        f077(ESPERANZA, "RM", 62005, "NC - CONTRATO QUE NO ESTA EN EL 090", 90, 50000.00, "904999998A", LITORAL),
        f077(OMBU, "ZZ", 62006, "DOCUMENTO FUERA DE ALCANCE", 20, 15000.00, "904000005A"),
    ], "077", pie=f"Data Refresh Date: {hoy:%d/%m/%Y} (DEMO)")

    # Histórico con lo controlado antes (la 85017 ya está; la 78013 comparte COE con la 85013) y pagados (85014)
    anterior = l044(78013, "L#", *P, "904000003A", SIN, ALBERTO, ALBERTO, 1500000.00, sumar_habiles(lejos, -1),
                    lejos, coe=340000078013, fiscal=3400078013)
    controlada = next(f for f in filas_044 if f[0] == 85017)
    df = pd.DataFrame([anterior, controlada], columns=COLS_044)
    df = generar_id_largo(generar_id_corto(normalizar_nro_legal(df)))
    df["CONTROLADO"] = True
    df["Fecha_Limpieza"] = f"{viejo:%Y-%m-%d} 12:00:00"
    df["Estado_Limpieza"] = "CONTROLADO_LIMPIADO"
    libro = openpyxl.Workbook()
    h = libro.active
    h.title = "Historico_Controlados"
    h.append(list(df.columns))
    for fila in df.itertuples(index=False, name=None):
        h.append([None if v is pd.NaT or (isinstance(v, float) and pd.isna(v)) else v for v in fila])
    libro.save(data / "Historico_Documentos_Controlados.xlsx")
    pd.DataFrame(columns=list(df.columns)).to_csv(data / "Historico_Documentos_Controlados_fallback.csv", index=False)

    pagada = generar_id_largo(generar_id_corto(normalizar_nro_legal(
        pd.DataFrame([next(f for f in filas_044 if f[0] == 85014)], columns=COLS_044)))).iloc[0]
    libro = openpyxl.Workbook()
    h = libro.active
    h.title = "Historico_Pagados"
    h.append(["Numero Doc", "Tipo Doc", "Contrato", "Total a Pagar", "Fecha Pago", "id_largo", "id_corto",
              "Fecha Netting", "Fecha Acreditación", "ID pago E1"])
    h.append([85014, "L#", pagada["Contrato"], pagada["Total a Pagar"], pagada["Fecha Pago"], pagada["id_largo"],
              pagada["id_corto"], dt(viejo), dt(viejo), 2147299914])
    libro.save(data / "historico_pagados.xlsx")

    # ------------------------------------------------------------ 020 y 067 "bajados de E1" después del netting
    enc_020 = ["Corredor", "Nombre Corredor", "Cliente", "Nombre Cliente", "CUIT Cliente", "ID Transaccion",
               "Nro de Documento", "Concepto", "Descripcion Tipo de Documento", "Detalle del documento",
               "Fecha Documento", "Unidades", "Importe Total del doc CON IVA", "Importe Fiscal",
               "Importe Cancelado CON IVA", "Vencimiento", "Contrato", "Slip de Fijacion", "Descripcion del producto",
               "Cosecha", "Descripcion de retencion", "Provincia", "Alicuota", "BP Comercial", "Numero de COE/FACTURA",
               "Factura Asociada", "Tipo Factura Asociada", "Fecha de pago", "Fecha de Operacion", "Estado del pago",
               "Nombre Estado del Pago", "Usuario X1", "Nombre de aprobador", "Numero de PK", "Compania",
               "Interes En Cuenta", "Tipo Cambio En Cuenta", "Neteo", "Permuta", "Retenciones"]
    nombres = {"H": "Pendiente de liberar", "A": "Liberado", "P": "Transmitido a A9"}

    def f020(id_, corr, cli, nro, concepto, importe, estado, contrato, fecha_doc, total=None, asociada=None, pago=p24):
        v = {"Corredor": corr[0] or 0, "Nombre Corredor": corr[1], "Cliente": cli[0], "Nombre Cliente": cli[1],
             "CUIT Cliente": "30999000000", "ID Transaccion": id_, "Nro de Documento": nro, "Concepto": concepto,
             "Descripcion Tipo de Documento": "Liquidacion" if concepto in ("L#", "C0", "H7") else "Factura",
             "Fecha Documento": dt(fecha_doc), "Importe Total del doc CON IVA": importe if total is None else total,
             "Importe Cancelado CON IVA": importe, "Contrato": contrato, "Descripcion del producto": PRODUCTO[1],
             "Cosecha": "2025/2026", "BP Comercial": "0999999000", "Factura Asociada": asociada,
             "Fecha de pago": dt(pago), "Fecha de Operacion": dt(hoy), "Estado del pago": estado,
             "Nombre Estado del Pago": nombres[estado], "Usuario X1": "DEMO", "Compania": 99999, "Neteo": "S",
             "Permuta": "N"}
        return [v.get(c) for c in enc_020]

    hace = lambda dias: hoy - timedelta(days=dias)  # noqa: E731

    def armar_020(e):
        return [
            # CEREALES DEL LITORAL: todo coincide → LIBERAR
            f020(2147200001, LITORAL, ESPERANZA, 85001, "L#", 15200000.00, e[1], "904000001A", g24),
            f020(2147200001, LITORAL, SANJORGE, 85002, "L#", 9800000.00, e[1], "904000002A", g24),
            f020(2147200001, LITORAL, ESPERANZA, 62001, "RI", 1100000.00, e[1], "904000001A", hace(50)),
            f020(2147200001, LITORAL, SANJORGE, 62002, "AH", 400000.00, e[1], "904000002A", hace(45)),
            # DON ALBERTO: todo coincide → LIBERAR
            f020(2147200002, SIN, ALBERTO, 85003, "L#", 7400000.00, e[2], "904000003A", g24),
            f020(2147200002, SIN, ALBERTO, 85004, "H7", -120000.00, e[2], "904000003A", g24),
            f020(2147200002, SIN, ALBERTO, 62003, "RI", 600000.00, e[2], "904000003A", hace(70)),
            # GRANOS DEL CENTRO: E1 tomó además una RT que no está en la propuesta → MANUAL (devengados)
            f020(2147200003, CENTRO, ACACIAS, 85005, "L#", 5600000.00, e[3], "904000004A", g24),
            f020(2147200003, CENTRO, ACACIAS, 62004, "RT", 300000.00, e[3], "904000004A", hace(30)),
            f020(2147200003, CENTRO, ACACIAS, 62099, "RT", 150000.00, e[3], "904000004A", hace(25), asociada="99999"),
            # EL OMBU: E1 tomó 3.500.000 de 3.900.000 y quedan 400.000 en la cuenta K → MANUAL (montos)
            f020(2147200004, SIN, OMBU, 85006, "L#", 3500000.00, e[4], "904000005A", g24, total=3900000.00),
            # TRES ARROYOS (cesión a BANCO DEMO): no se generó en E1 → NO SE ENCONTRO
            # LOS NOGALES: ya liberado en E1 → no entra al Output
            f020(2147200006, SIN, NOGALES, 85008, "L#", 2300000.00, e[6], "904000007A", g24),
            # 48 hs
            f020(2147200007, CENTRO, ESPERANZA, 85009, "L#", 6100000.00, e[7], "904000008A", g48, pago=p48),
            f020(2147200008, LITORAL, SANJORGE, 85010, "L#", 2700000.00, e[8], "904000002A", g48, pago=p48),
        ]
    pie = f"Data Refresh Date: {hoy:%d/%m/%Y} (DEMO)"
    guardar(data / "020_DEMO.xlsx", enc_020,
            armar_020({1: "H", 2: "H", 3: "H", 4: "H", 6: "A", 7: "H", 8: "H"}), "020", pie=pie)
    # Después de subir el Output E1: lo liberado (incluida la liberación manual de EL OMBU) pasa a A;
    # GRANOS DEL CENTRO quedó en MANUAL y sigue en H.
    guardar(data / "020_LIMPIAR_DEMO.xlsx", enc_020,
            armar_020({1: "A", 2: "A", 3: "H", 4: "A", 6: "A", 7: "A", 8: "A"}), "020", pie=pie)

    enc_067 = ["Fecha Generacion de Netting", "Fecha De Transmision de Netting Emision", "Hora Transm Netting Emision",
               "Fecha Anulacion de Netting", "Tipo de Documento X1", "N° de X1", "Estado del X1", "Id Interface",
               "ID Permuta", "Abook del Vendedor Productor", "Codigo tributario del Vendedor", "Razon Social Vendedor",
               "Abook del Beneficiario", "CUIT Beneficiario", "Razon Social Beneficiario", "Abook del Benef Alterna",
               "Codigo tributario del Benef Alter", "Razon Social Benef Alter", "Instrumento del Pago",
               "Nombre Instrumento del Pago", "Letra del Instrumento de pago", "Codigo BANCO", "Nombre BANCO",
               "Cuenta bancaria", "Importe a Pagar Moneda Local", "Usuario Generador de Netting",
               "Usuario Liberacion de Netting", "Validaciones Coherentes", "Nombre Validaciones Coherentes",
               "ID Transaction", "Usuario de Aprobacion del Pago"]

    def f067(id_, benef, letra, importe, x1):
        nombre = "Cuenta corriente" if letra == "K" else "Transferencia E1"
        v = {"Fecha Generacion de Netting": dt(hoy), "Tipo de Documento X1": "X1", "N° de X1": x1, "Estado del X1": "H",
             "Abook del Beneficiario": benef[0], "Razon Social Beneficiario": benef[1], "Instrumento del Pago": letra,
             "Nombre Instrumento del Pago": nombre, "Letra del Instrumento de pago": letra, "Codigo BANCO": "999",
             "Nombre BANCO": "BANCO DEMO SA", "Cuenta bancaria": f"0999000{benef[0]}",
             "Importe a Pagar Moneda Local": importe, "Usuario Generador de Netting": "DEMO",
             "Validaciones Coherentes": "F", "Nombre Validaciones Coherentes": "Validación Coherente", "ID Transaction": id_}
        return [v.get(c) for c in enc_067]
    guardar(data / "067_DEMO.xlsx", enc_067, [
        f067(2147200001, LITORAL, "K", 0.00, 6001), f067(2147200001, LITORAL, "T", 23500000.00, 6001),
        f067(2147200002, ALBERTO, "K", 0.00, 6002), f067(2147200002, ALBERTO, "T", 6680000.00, 6002),
        f067(2147200003, CENTRO, "K", 0.00, 6003), f067(2147200003, CENTRO, "T", 5150000.00, 6003),
        f067(2147200004, OMBU, "K", 400000.00, 6004), f067(2147200004, OMBU, "T", 3500000.00, 6004),
        f067(2147200006, NOGALES, "K", 0.00, 6006), f067(2147200006, NOGALES, "T", 2300000.00, 6006),
        f067(2147200007, ESPERANZA, "K", 0.00, 6007), f067(2147200007, ESPERANZA, "T", 6100000.00, 6007),
        f067(2147200008, LITORAL, "K", 0.00, 6008), f067(2147200008, LITORAL, "T", 2700000.00, 6008),
    ], "067", pie=pie)
    return p24, p48


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fecha", help="fecha de proceso dd/mm/aaaa (por defecto hoy, o el próximo día hábil)")
    parser.add_argument("--reemplazar", action="store_true", help="borra la copia DEMO anterior")
    parser.add_argument("--destino", help="carpeta de la copia (por defecto ..\\<repo>-DEMO)")
    args = parser.parse_args()
    if args.fecha:
        hoy = datetime.strptime(args.fecha, "%d/%m/%Y").date()
    else:
        hoy = date.today()
    while not habil(hoy):
        hoy += timedelta(days=1)

    destino = Path(args.destino) if args.destino else REPO.parent / f"{REPO.name}-DEMO"
    if destino.exists():
        if not args.reemplazar:
            print(f"Ya existe {destino}. Usá --reemplazar para armarla de nuevo.")
            return 1
        shutil.rmtree(destino)
    shutil.copytree(REPO, destino, ignore=shutil.ignore_patterns(*NO_COPIAR))
    for carpeta in ("data", "config", "logs"):
        (destino / carpeta).mkdir(exist_ok=True)
    ajustes = REPO / "config" / "app_settings.json"
    if ajustes.exists():
        shutil.copy2(ajustes, destino / "config" / ajustes.name)

    p24, p48 = generar(destino / "data", hoy)
    acreditacion = p48
    guion = (AQUI / "GUION.md").read_text(encoding="utf-8")
    for clave, valor in {"{HOY}": f"{hoy:%d/%m/%Y}", "{P24}": f"{p24:%d/%m/%Y}", "{P48}": f"{p48:%d/%m/%Y}",
                         "{ACREDITACION}": f"{acreditacion:%d/%m/%Y}"}.items():
        guion = guion.replace(clave, valor)
    (destino / "GUION.md").write_text(guion, encoding="utf-8")

    print(f"Listo: {destino}")
    print(f"Fecha de proceso de la demo: {hoy:%d/%m/%Y} (pagos de 24 hs el {p24:%d/%m/%Y}, de 48 hs el {p48:%d/%m/%Y}).")
    print(f'Para abrir la app:  cd "{destino}"  y después  py -m gui.app')
    print("Los pasos y los resultados esperados están en GUION.md dentro de esa carpeta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
