import logging
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import pandas as pd

from .pantalla_control import PantallaControl

from services.procesar_control import (
    ejecutar_control
)


class MenuPrincipal(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)

        titulo = ctk.CTkLabel(
            self,
            text="CONTROLES GLUCO V2",
            font=("Segoe UI", 30, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(pady=(30, 25))

        panel = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=22,
            border_width=1,
            border_color="#334155"
        )
        panel.pack(fill="both", expand=True, padx=80, pady=(0, 30))

        opciones = [
            ("CARGAR BASES", self.master.mostrar_pantalla_carga),
            ("VISUALIZAR LIQUIDACIONES", self.master.mostrar_pantalla_visualizacion),
            ("LIMPIEZA DE LIQUIDACIONES CONTROLADAS", self.master.mostrar_pantalla_limpieza),
            ("SALIR", self.master.cerrar_aplicacion),
        ]

        for texto, comando in opciones:
            btn = ctk.CTkButton(
                panel,
                text=texto,
                command=comando,
                height=56,
                width=420,
                corner_radius=12,
                fg_color="#1f2937",
                hover_color="#334155",
                text_color="#f8fafc",
                font=("Segoe UI", 16, "bold")
            )
            btn.pack(pady=12)


class PantallaCargaDatos(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.archivo_044 = ""
        self.archivo_090 = ""
        self.archivo_077 = ""

        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)

        self.crear_interfaz()

    def crear_interfaz(self):

        titulo = ctk.CTkLabel(
            self,
            text="CARGA DE DATOS",
            font=("Segoe UI", 28, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(anchor="w", padx=18, pady=(20, 20))

        panel = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        panel.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.lbl_044 = ctk.CTkLabel(panel, text="044 no seleccionado", anchor="w", justify="left")
        self.lbl_044.pack(anchor="w", padx=24, pady=(24, 6))
        btn_044 = ctk.CTkButton(panel, text="Seleccionar 044", command=self.seleccionar_044, width=220, height=42)
        btn_044.pack(anchor="w", padx=24, pady=(0, 12))

        self.lbl_090 = ctk.CTkLabel(panel, text="090 no seleccionado", anchor="w", justify="left")
        self.lbl_090.pack(anchor="w", padx=24, pady=(8, 6))
        btn_090 = ctk.CTkButton(panel, text="Seleccionar 090", command=self.seleccionar_090, width=220, height=42)
        btn_090.pack(anchor="w", padx=24, pady=(0, 12))

        self.lbl_077 = ctk.CTkLabel(panel, text="077 no seleccionado", anchor="w", justify="left")
        self.lbl_077.pack(anchor="w", padx=24, pady=(8, 6))
        btn_077 = ctk.CTkButton(panel, text="Seleccionar 077", command=self.seleccionar_077, width=220, height=42)
        btn_077.pack(anchor="w", padx=24, pady=(0, 20))

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(10, 20))

        btn_procesar = ctk.CTkButton(
            acciones,
            text="PROCESAR",
            command=self.procesar,
            width=220,
            height=48,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=("Segoe UI", 14, "bold")
        )
        btn_procesar.pack(side="left", padx=(0, 12))

        btn_volver = ctk.CTkButton(
            acciones,
            text="VOLVER AL MENÚ PRINCIPAL",
            command=self.volver_al_menu,
            width=260,
            height=48,
            fg_color="#334155",
            hover_color="#475569",
            font=("Segoe UI", 14, "bold")
        )
        btn_volver.pack(side="left")

        self.estado = ctk.CTkLabel(self, text="", text_color="#86efac")
        self.estado.pack(anchor="w", padx=20, pady=(0, 10))

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")

    def seleccionar_044(self):
        archivo = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if archivo:
            self.archivo_044 = archivo
            self.lbl_044.configure(text=archivo)

    def seleccionar_090(self):
        archivo = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if archivo:
            self.archivo_090 = archivo
            self.lbl_090.configure(text=archivo)

    def seleccionar_077(self):
        archivo = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if archivo:
            self.archivo_077 = archivo
            self.lbl_077.configure(text=archivo)

    def procesar(self):
        if not self.archivo_044 or not self.archivo_090 or not self.archivo_077:
            self.estado.configure(text="Debe seleccionar los tres archivos.")
            return

        self.estado.configure(text="Procesando...")
        self.update_idletasks()

        resultado = ejecutar_control(self.archivo_044, self.archivo_090)
        resumen = resultado["resumen"]
        df = resultado["df"]

        self.master.df_procesado = df
        self.master.resumen = resumen

        pantalla = self.master.frames["visualizacion"]
        pantalla.actualizar(
            total=resumen["total"],
            macro=resumen["macro"],
            manual=resumen["manual"],
            parciales=resumen["parciales"],
            finales=resumen["finales"],
            comisiones=resumen["comisiones"],
            ajustes=resumen["ajustes"]
        )
        pantalla.cargar_dataframe(df)
        self.master.mostrar_pantalla("visualizacion")


class PantallaVisualizacion(PantallaControl):

    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.btn_volver = ctk.CTkButton(
            self.frame_acciones,
            text="VOLVER AL MENÚ PRINCIPAL",
            command=self.volver_al_menu,
            width=260,
            height=42,
            corner_radius=12,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_volver.pack(side="left", padx=8)

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")


class PantallaLimpieza(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.df_original = pd.DataFrame()
        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.crear_interfaz()

    def crear_interfaz(self):
        titulo = ctk.CTkLabel(
            self,
            text="LIMPIEZA DE DOCUMENTOS CONTROLADOS",
            font=("Segoe UI", 28, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 12))

        self.frame_tabla = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        self.frame_tabla.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.tabla = ctk.CTkTextbox(self.frame_tabla, height=16)
        self.tabla.pack(fill="both", expand=True, padx=12, pady=12)

        self.tabla.insert("0.0", "No hay documentos controlados para mostrar.")

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(0, 20))

        btn_eliminar = ctk.CTkButton(
            acciones,
            text="Limpiar controlados",
            command=self.eliminar_seleccionados,
            width=250,
            height=46,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=("Segoe UI", 14, "bold")
        )
        btn_eliminar.pack(side="left", padx=(0, 12))

        btn_volver = ctk.CTkButton(
            acciones,
            text="VOLVER AL MENÚ PRINCIPAL",
            command=self.volver_al_menu,
            width=260,
            height=46,
            fg_color="#334155",
            hover_color="#475569",
            font=("Segoe UI", 14, "bold")
        )
        btn_volver.pack(side="left")

    def _ruta_historico(self):
        return Path(__file__).resolve().parents[1] / "data" / "Historico_Documentos_Controlados.xlsb"

    def _guardar_historico_controlados(self, df_controlados):
        if df_controlados is None or df_controlados.empty:
            return

        ruta = self._ruta_historico()
        ruta.parent.mkdir(parents=True, exist_ok=True)

        df_hist = df_controlados.copy()
        df_hist["Fecha_Limpieza"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        df_hist["Estado_Limpieza"] = "CONTROLADO_LIMPIADO"

        try:
            import win32com.client

            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            if ruta.exists():
                libro = excel.Workbooks.Open(str(ruta))
            else:
                libro = excel.Workbooks.Add()

            hoja = None
            for nombre in ["Historico_Documentos_Controlados", "Historico", "Sheet1"]:
                try:
                    hoja = libro.Worksheets(nombre)
                    break
                except Exception as exc:  # pragma: no cover - fallback de compatibilidad
                    logging.getLogger(__name__).debug("Hoja no disponible en historial: %s", exc)
                    continue

            if hoja is None:
                hoja = libro.Worksheets.Add()
                hoja.Name = "Historico_Documentos_Controlados"

            if hoja.Cells(1, 1).Value is None:
                columnas = list(df_hist.columns)
                for idx, nombre_col in enumerate(columnas, start=1):
                    hoja.Cells(1, idx).Value = nombre_col
                fila_inicio = 2
            else:
                fila_inicio = hoja.UsedRange.Rows.Count + 1

            for fila_idx, fila in enumerate(df_hist.itertuples(index=False), start=fila_inicio):
                for col_idx, valor in enumerate(fila, start=1):
                    hoja.Cells(fila_idx, col_idx).Value = valor

            libro.SaveAs(str(ruta), 50)
            libro.Close(SaveChanges=True)
            excel.Quit()

        except Exception as exc:  # pragma: no cover - fallback local si Excel no está disponible
            logging.getLogger(__name__).warning("No se pudo escribir en XLSB; se usa fallback local: %s", exc)
            df_hist.to_excel(ruta.with_suffix(".xlsx"), index=False)

    def cargar_documentos(self, df):
        if df is None or df.empty:
            self.df_original = pd.DataFrame()
            self.tabla.delete("0.0", "end")
            self.tabla.insert("0.0", "No hay documentos controlados para mostrar.")
            return

        self.df_original = df.copy()
        if "CONTROLADO" not in self.df_original.columns:
            self.df_original["CONTROLADO"] = False
        self.df_original["CONTROLADO"] = self.df_original["CONTROLADO"].fillna(False).astype(bool)

        if hasattr(self.master, "df_procesado") and self.master.df_procesado is not None:
            self.master.df_procesado = self.df_original.copy()

        controlados = self.df_original[self.df_original["CONTROLADO"] == True].copy()

        self.tabla.delete("0.0", "end")
        if controlados.empty:
            self.tabla.insert("0.0", "No hay documentos controlados para mostrar.")
            return

        lineas = []
        for _, fila in controlados.iterrows():
            numero_doc = str(fila.get("Numero Doc", ""))
            contrato = str(fila.get("Contrato", ""))
            fecha_pago = ""
            if "Fecha Pago" in fila and pd.notna(fila.get("Fecha Pago")):
                fecha_pago = pd.to_datetime(fila.get("Fecha Pago")).strftime("%d/%m/%Y")
            beneficiario = str(fila.get("AB Beneficiario del Pago", fila.get("Nombre Beneficiario del Pago", "")))
            estado = "CONTROLADO" if bool(fila.get("CONTROLADO", False)) else "NO CONTROLADO"
            lineas.append(f"{numero_doc} | {contrato} | {fecha_pago} | {beneficiario} | {estado}\n")

        self.tabla.insert("0.0", "".join(lineas))

    def eliminar_seleccionados(self):
        if self.df_original.empty:
            return

        controlados = self.df_original[self.df_original["CONTROLADO"].fillna(False).astype(bool)].copy()
        if controlados.empty:
            return

        self._guardar_historico_controlados(controlados)

        self.df_original = self.df_original[
            ~self.df_original["CONTROLADO"].fillna(False).astype(bool)
        ].copy()

        if hasattr(self.master, "df_procesado"):
            self.master.df_procesado = self.df_original.copy()

        if hasattr(self.master, "frames") and "visualizacion" in self.master.frames:
            self.master.frames["visualizacion"].df_original = self.df_original.copy()
            self.master.frames["visualizacion"].cargar_dataframe(self.df_original)

        self.cargar_documentos(self.df_original)

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")


PantallaInicio = MenuPrincipal
