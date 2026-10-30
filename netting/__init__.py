"""Etapa 2 del proceso Glucovil: armado de propuestas de netting.

Reemplaza a la macro Macro_Propuesta.xlsm (solo el camino de propuestas automáticas;
las propuestas manuales de Cargill quedaron fuera de alcance).

Organización:
    config.py      parámetros editables (feriados, corredores solo 24 hs, contador de propuestas)
    calendario.py  días hábiles a pagar, igual que calcula_dias de la macro
    cargas.py      lectura del Histórico, 077 y 090 (.xlsb / .xlsx / .csv)
    motor.py       reglas de la macro, replicadas en "modo compatibilidad"
    salida.py      reparto por analista y exportación de Propuestas_Netting.xlsx
    servicio.py    orquesta los pasos y devuelve un ResultadoNetting

No depende de Excel ni de CONTROLAR: solo lee el Histórico que CONTROLAR (o la macro vieja) genera.
"""
