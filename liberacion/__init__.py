"""Etapa 3 del proceso Glucovil: liberación de pagos.

Reemplaza a la macro Macro_Controles_Netting_y_Compensa.xlsb:

    cargas.py    propuestas (registro de Netting o Propuestas_Netting), reportes 020 y 067
    motor.py     botón CONTROL: ID de netting, montos, tipo, cronología, cuenta K, devengados, permuta
    salida.py    botón OUTPUT LIBERACIÓN E1 (Netting_liberar.xlsx) y actualización del registro
    limpieza.py  botón LIMPIAR LIQUIDACIONES PAGADAS: Histórico de controlados → Histórico de pagados
    servicio.py  orquesta los pasos

Los IDs de pago no se cargan a mano: salen del reporte 020, como en la macro.
"""
