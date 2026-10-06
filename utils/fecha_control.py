from datetime import date, timedelta


def obtener_fecha_control(fecha_base=None):
    """
    Martes  -> controla pagos del Jueves
    Viernes -> controla pagos del Martes siguiente
    """

    if fecha_base is None:
        fecha_base = date.today()

    # Martes
    if fecha_base.weekday() == 1:
        return fecha_base + timedelta(days=2)

    # Viernes
    if fecha_base.weekday() == 4:
        return fecha_base + timedelta(days=4)

    return None
