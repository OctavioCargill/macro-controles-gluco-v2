"""Salidas del control: Output E1 (Netting_liberar.xlsx) y actualización del registro de Netting."""

from pathlib import Path

from liberacion.motor import NO_SE_ENCONTRO, filas_output_e1
from netting.registro import actualizar_registro

NOMBRE_OUTPUT_E1 = "Netting_liberar.xlsx"
HOJA_E1 = "E1"
ENCABEZADO_E1 = ("ID Transacción", "Estado", "Proceso")


def exportar_output_e1(ruta, paquetes):
    """Agrega al final de la hoja E1 los IDs a liberar (como el botón OUTPUT LIBERACIÓN E1).

    Si el archivo no existe se crea con encabezado. Devuelve la cantidad de IDs agregados.
    """
    from openpyxl import Workbook, load_workbook

    filas = filas_output_e1(paquetes)
    if not filas:
        raise ValueError("No se encontraron netting para liberar (ningún paquete en LIBERAR o LIBERACIÓN MANUAL).")
    ruta = Path(ruta)
    if ruta.exists():
        libro = load_workbook(ruta)
        hoja = libro[HOJA_E1] if HOJA_E1 in libro.sheetnames else libro.create_sheet(HOJA_E1)
    else:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        libro = Workbook()
        hoja = libro.active
        hoja.title = HOJA_E1
    if hoja.max_row == 1 and hoja["A1"].value is None:
        for columna, titulo in enumerate(ENCABEZADO_E1, start=1):
            hoja.cell(row=1, column=columna, value=titulo)
    # Última fila con dato en la columna A (como End(xlUp) en la macro)
    ultima = hoja.max_row
    while ultima > 1 and hoja.cell(ultima, 1).value in (None, ""):
        ultima -= 1
    for desplazamiento, valores in enumerate(filas, start=1):
        for columna, valor in enumerate(valores, start=1):
            hoja.cell(row=ultima + desplazamiento, column=columna, value=valor)
    try:
        libro.save(ruta)
    except PermissionError as exc:
        raise PermissionError(f"No se pudo guardar {ruta.name}. Si está abierto en Excel, cerralo y probá de nuevo.") from exc
    finally:
        libro.close()
    return len(filas)


def actualizar_registro_con_control(ruta_registro, propuestas):
    """Guarda en el registro de Netting el ID de pago (del 020), el control y el estado en E1."""
    por_paquete = {}
    for fila in propuestas:
        if not fila.get("generado"):
            continue
        clave = (fila["generado"], f"{fila['ventana']} hs", str(fila["n_propuesta"]))
        por_paquete[clave] = fila

    def cambios(fila_registro):
        clave = (str(fila_registro.get("Generado")), str(fila_registro.get("Ventana")),
                 str(fila_registro.get("N° propuesta")))
        dato = por_paquete.get(clave)
        if dato is None or str(fila_registro.get("Estado", "")).upper() in ("LIBERADO", "ANULADA"):
            return None
        encontrado = dato["id"] not in (NO_SE_ENCONTRO, "")
        return {
            "ID pago E1": dato["id"] if encontrado else fila_registro.get("ID pago E1"),
            "Control liberación": dato["control"],
            "Estado E1": dato["estado_ne"],
            "Estado": "CON ID DE PAGO" if encontrado else fila_registro.get("Estado"),
        }

    if not por_paquete or not Path(ruta_registro).exists():
        return 0
    return actualizar_registro(ruta_registro, cambios)
