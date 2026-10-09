import pandas as pd
import customtkinter as ctk
from gui.pantalla_control import PantallaControl

root = ctk.CTk()
root.withdraw()

pantalla = PantallaControl(root)

df = pd.DataFrame({
    'Numero Doc': [101, 101, 102],
    'Tipo Doc': ['L#', 'L#', 'C0'],
    'Contrato': ['A', 'A', 'B'],
    'Fecha Pago': pd.to_datetime(['2024-01-01', '2024-01-01', '2024-01-02']),
    'Total a Pagar': [1000.0, 1100.0, 2000.0],
    'RESULTADO_FINAL': ['CONTROL MACRO', 'CONTROL MACRO', 'CONTROL MACRO'],
    'Producto': ['RIB1', 'PIB1', 'RIB2'],
    'Importe Fiscal': [10.0, 12.0, 15.0],
    'Descripcion de la liquidacion': ['Liquidación Parcial', 'Liquidación Parcial', 'Liquidación Final C/Parcial']
})

pantalla.cargar_dataframe(df)
print('combo exists:', hasattr(pantalla, 'combo_fecha'), hasattr(pantalla, 'combo_tipo'))
print('rows:', len(pantalla.tabla.get_children()))
print('first item:', pantalla.tabla.item(pantalla.tabla.get_children()[0])['values'])
root.destroy()
