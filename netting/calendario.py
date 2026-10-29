"""Días hábiles a pagar, con la misma lógica que calcula_dias (abrir_bases) de la macro."""

from datetime import date, datetime, timedelta


def _es_habil(dia: date, feriados) -> bool:
    return dia.weekday() < 5 and dia not in feriados


def dias_a_pagar(fecha_pago, hoy: date, feriados) -> int:
    """Días hábiles desde `hoy` hasta la fecha de pago.

    - Fecha de pago vacía, de hoy o pasada: 0.
    - Se avanza día por día desde hoy; cada paso suma 1 y, si cae en sábado, domingo o
      feriado, se sigue avanzando hasta el próximo hábil sin sumar. Así una fecha de pago
      en fin de semana cuenta hasta el lunes siguiente (viernes → sábado = 1).
    - Como en la macro, la comparación usa fecha y hora: una fecha de pago de hoy con hora
      distinta de 00:00 cuenta como 1.
    """
    if fecha_pago is None:
        return 0
    if isinstance(fecha_pago, datetime):
        pago = fecha_pago
    elif isinstance(fecha_pago, date):
        pago = datetime(fecha_pago.year, fecha_pago.month, fecha_pago.day)
    else:
        return 0

    actual = datetime(hoy.year, hoy.month, hoy.day)
    if pago <= actual:
        return 0

    contador = 0
    while actual < pago:
        contador += 1
        actual += timedelta(days=1)
        while not _es_habil(actual.date(), feriados):
            actual += timedelta(days=1)
    return contador
