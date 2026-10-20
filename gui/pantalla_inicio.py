import importlib.util
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from tkinter import ttk

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.auditoria import (
    APP_DATA_PATH,
    APP_NAME,
    APP_ROOT,
    APP_VERSION,
    asegurar_estructura_runtime,
    construir_diagnostico,
    escribir_log_auditoria,
    evaluar_integridad_liquidaciones,
    metricas_generales,
    validar_archivos_requeridos,
)
from services.procesar_control import ejecutar_control

from gui.pantalla_control import PantallaControl


class MenuPrincipal(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)

        titulo = ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=("Segoe UI", 30, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(pady=(30, 12))

        self.lbl_version = ctk.CTkLabel(
            self,
            text=f"Versión {APP_VERSION}",
            font=("Segoe UI", 12, "bold"),
            text_color="#93c5fd"
        )
        self.lbl_version.pack(pady=(0, 18))

        panel = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=22,
            border_width=1,
            border_color="#334155"
        )
        panel.pack(fill="both", expand=True, padx=80, pady=(0, 30))

        opciones = [
            ("MÉTRICAS GENERALES", self.master.mostrar_pantalla_metrica),
            ("BUSCADOR GLOBAL", self.master.mostrar_pantalla_busqueda),
            ("CARGAR BASES", self.master.mostrar_pantalla_carga),
            ("VISUALIZAR LIQUIDACIONES", self.master.mostrar_pantalla_visualizacion),
            ("LIMPIEZA DE LIQUIDACIONES CONTROLADAS", self.master.mostrar_pantalla_limpieza),
            ("PRUEBAS DE INTEGRIDAD", self.master.ejecutar_prueba_integridad),
            ("ACERCA DE", self.master.mostrar_acerca_de),
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

    def actualizar_metrica(self):
        if hasattr(self.master, "df_procesado") and self.master.df_procesado is not None:
            metrics = metricas_generales(self.master.df_procesado, getattr(self.master, "resumen", {}))
        else:
            metrics = {
                "total_liquidaciones_detectadas": 0,
                "total_liquidaciones_procesadas": 0,
                "total_liquidaciones_aprobadas": 0,
                "total_liquidaciones_observadas": 0,
                "total_documentos_controlados": 0,
                "total_documentos_pendientes": 0,
                "total_documentos_historizados": 0,
                "cantidad_errores_detectados": 0,
                "ultima_ejecucion": getattr(self.master, "ultima_ejecucion", "No ejecutado"),
            }

        for clave, label in self.metric_labels.items():
            valor = metrics.get(clave, 0)
            if clave == "ultima_ejecucion":
                texto = str(valor)
            elif isinstance(valor, float):
                texto = f"{valor:,.2f}"
            else:
                texto = str(valor)
            label.configure(text=texto)

        if hasattr(self.master, "diagnostico"):
            estado = self.master.diagnostico.get("hay_errores", False)
            if estado:
                self.lbl_version.configure(text=f"Versión {APP_VERSION} • requiere revisión")
            else:
                self.lbl_version.configure(text=f"Versión {APP_VERSION} • OK")

    def buscar_global(self):
        df = getattr(self.master, "df_procesado", None)
        if df is None or df.empty:
            self.tabla_busqueda.delete(*self.tabla_busqueda.get_children())
            self.tabla_busqueda.insert("", "end", values=("Sin datos", "-", "-", "-", "-", "-"))
            return

        texto = self.buscar_entry.get()
        resultados = df.copy()
        if texto and texto.strip():
            cols = [c for c in ["Numero Doc", "Contrato", "Nro. Legal", "Nro_Legal", "Descripcion de la liquidacion", "Tipo Doc", "Proveedor", "Nombre Beneficiario del Pago", "Numero de CAE COE Factura"] if c in resultados.columns]
            mascara = pd.Series(False, index=resultados.index)
            query = texto.strip().lower()
            for col in cols:
                mascara = mascara | resultados[col].fillna("").astype(str).str.lower().str.contains(query, na=False)
            resultados = resultados.loc[mascara].head(20)

        self.tabla_busqueda.delete(*self.tabla_busqueda.get_children())
        if resultados.empty:
            self.tabla_busqueda.insert("", "end", values=("Sin coincidencias", "-", "-", "-", "-", "-"))
            return

        for _, fila in resultados.iterrows():
            numero_doc = str(fila.get("Numero Doc", ""))
            contrato = str(fila.get("Contrato", ""))
            tipo = str(fila.get("Descripcion de la liquidacion", fila.get("Tipo Doc", "")))
            fecha = ""
            if "Fecha Pago" in fila and pd.notna(fila.get("Fecha Pago")):
                fecha = pd.to_datetime(fila.get("Fecha Pago")).strftime("%d/%m/%Y")
            estado = str(fila.get("RESULTADO_FINAL", "-"))
            self.tabla_busqueda.insert("", "end", values=(numero_doc, contrato, tipo, fecha, estado))

    def abrir_detalle_busqueda(self, event=None):
        seleccion = self.tabla_busqueda.selection()
        if not seleccion:
            return
        item = self.tabla_busqueda.item(seleccion[0], "values")
        documento = item[0]
        if documento in ("Sin datos", "Sin coincidencias"):
            return

        self.master.mostrar_pantalla("visualizacion")
        visual = self.master.frames["visualizacion"]
        if visual.df_original is not None and not visual.df_original.empty:
            filtro = visual.df_original["Numero Doc"].astype(str) == str(documento)
            if filtro.any():
                visual.tabla.selection_set(visual.tabla.get_children()[int(filtro.iloc[:len(visual.tabla.get_children())].sum()) - 1])
                visual.ver_detalle()


class PantallaMetricas(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.metric_labels = {}
        self.crear_interfaz()

    def crear_interfaz(self):
        titulo = ctk.CTkLabel(
            self,
            text="Métricas Generales",
            font=("Segoe UI", 28, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 18))

        self.frame_metricas = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        self.frame_metricas.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.metricas_grid = ctk.CTkFrame(self.frame_metricas, fg_color="transparent")
        self.metricas_grid.pack(fill="both", expand=True, padx=18, pady=18)

        metrics = [
            ("Total liquidaciones detectadas", "total_liquidaciones_detectadas"),
            ("Total liquidaciones procesadas", "total_liquidaciones_procesadas"),
            ("Total liquidaciones aprobadas", "total_liquidaciones_aprobadas"),
            ("Total liquidaciones observadas", "total_liquidaciones_observadas"),
            ("Total docs controlados", "total_documentos_controlados"),
            ("Total docs pendientes", "total_documentos_pendientes"),
            ("Total docs historizados", "total_documentos_historizados"),
            ("Errores detectados", "cantidad_errores_detectados"),
            ("Última ejecución", "ultima_ejecucion"),
        ]

        for idx, (titulo_metric, clave) in enumerate(metrics):
            frame = ctk.CTkFrame(self.metricas_grid, fg_color="#0f172a", corner_radius=12, border_width=1, border_color="#334155")
            frame.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(frame, text=titulo_metric, font=("Segoe UI", 11, "bold"), text_color="#cbd5e1").pack(anchor="w", padx=12, pady=(10, 2))
            label = ctk.CTkLabel(frame, text="0", font=("Segoe UI", 20, "bold"), text_color="#86efac")
            label.pack(anchor="w", padx=12, pady=(0, 10))
            self.metric_labels[clave] = label

        self.metricas_grid.grid_columnconfigure(0, weight=1)
        self.metricas_grid.grid_columnconfigure(1, weight=1)
        self.metricas_grid.grid_columnconfigure(2, weight=1)

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=18, pady=(0, 10))
        btn_volver = ctk.CTkButton(
            acciones,
            text="VOLVER AL MENÚ PRINCIPAL",
            command=self.volver_al_menu,
            width=260,
            height=46,
            fg_color="#334155",
            hover_color="#475569",
            font=("Segoe UI", 12, "bold")
        )
        btn_volver.pack(side="left")

        self.actualizar_metricas()

    def actualizar_metricas(self):
        metrics = metricas_generales(getattr(self.master, "df_procesado", None), getattr(self.master, "resumen", {}))
        for clave, label in self.metric_labels.items():
            valor = metrics.get(clave, 0)
            texto = str(valor)
            if clave == "ultima_ejecucion":
                texto = str(valor)
            elif isinstance(valor, float):
                texto = f"{valor:,.2f}"
            label.configure(text=texto)

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")


class PantallaBusqueda(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color="#0b1120")
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.crear_interfaz()

    def crear_interfaz(self):
        titulo = ctk.CTkLabel(
            self,
            text="Buscador Global",
            font=("Segoe UI", 28, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 18))

        self.frame_busqueda = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        self.frame_busqueda.pack(fill="x", padx=18, pady=(0, 18))

        fila_busqueda = ctk.CTkFrame(self.frame_busqueda, fg_color="transparent")
        fila_busqueda.pack(fill="x", padx=18, pady=18)

        self.buscar_entry = ctk.CTkEntry(
            fila_busqueda,
            placeholder_text="Buscar por número, contrato, proveedor, tipo de liquidación...",
            width=500,
            height=38,
            fg_color="#0f172a",
            border_color="#475569"
        )
        self.buscar_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_buscar = ctk.CTkButton(
            fila_busqueda,
            text="BUSCAR",
            command=self.actualizar_resultados,
            width=150,
            height=38,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=("Segoe UI", 12, "bold")
        )
        btn_buscar.pack(side="left")

        self.frame_resultados = ctk.CTkFrame(self, fg_color="#111827", corner_radius=18, border_width=1, border_color="#334155")
        self.frame_resultados.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        columnas = ("Documento", "Contrato", "Tipo", "Fecha", "Estado", "Acción")
        self.tabla_busqueda = ttk.Treeview(
            self.frame_resultados,
            columns=columnas,
            show="headings",
            height=12,
            selectmode="browse"
        )
        for columna in columnas:
            self.tabla_busqueda.heading(columna, text=columna)
            self.tabla_busqueda.column(columna, anchor="center", width=170)

        self.tabla_busqueda.pack(fill="both", expand=True, padx=12, pady=12)

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=18, pady=(0, 10))
        btn_volver = ctk.CTkButton(
            acciones,
            text="VOLVER AL MENÚ PRINCIPAL",
            command=self.volver_al_menu,
            width=260,
            height=46,
            fg_color="#334155",
            hover_color="#475569",
            font=("Segoe UI", 12, "bold")
        )
        btn_volver.pack(side="left")

        self.actualizar_resultados()

    def actualizar_resultados(self):
        df = getattr(self.master, "df_procesado", None)
        self.tabla_busqueda.delete(*self.tabla_busqueda.get_children())

        if df is None or df.empty:
            self.tabla_busqueda.insert("", "end", values=("Sin datos", "-", "-", "-", "-", "-"))
            return

        texto = self.buscar_entry.get().strip()
        resultados = df.copy()
        if texto:
            cols = [c for c in ["Numero Doc", "Contrato", "Nro. Legal", "Nro_Legal", "Descripcion de la liquidacion", "Tipo Doc", "Proveedor", "Nombre Beneficiario del Pago", "Numero de CAE COE Factura"] if c in resultados.columns]
            mascara = pd.Series(False, index=resultados.index)
            query = texto.lower()
            for col in cols:
                mascara = mascara | resultados[col].fillna("").astype(str).str.lower().str.contains(query, na=False)
            resultados = resultados.loc[mascara].head(20)

        if resultados.empty:
            self.tabla_busqueda.insert("", "end", values=("Sin coincidencias", "-", "-", "-", "-", "-"))
            return

        for _, fila in resultados.iterrows():
            numero_doc = str(fila.get("Numero Doc", ""))
            contrato = str(fila.get("Contrato", ""))
            tipo = str(fila.get("Descripcion de la liquidacion", fila.get("Tipo Doc", "")))
            fecha = ""
            if "Fecha Pago" in fila and pd.notna(fila.get("Fecha Pago")):
                fecha = pd.to_datetime(fila.get("Fecha Pago")).strftime("%d/%m/%Y")
            estado = str(fila.get("RESULTADO_FINAL", "-"))
            self.tabla_busqueda.insert("", "end", values=(numero_doc, contrato, tipo, fecha, estado))

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")


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

        self.frame_validacion = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=18,
            border_width=1,
            border_color="#334155"
        )
        self.frame_validacion.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            self.frame_validacion,
            text="Validación de archivos y recursos",
            font=("Segoe UI", 14, "bold"),
            text_color="#f8fafc"
        ).pack(anchor="w", padx=18, pady=(18, 6))

        self.validacion_grid = ctk.CTkScrollableFrame(self.frame_validacion, fg_color="transparent", height=220)
        self.validacion_grid.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.validacion_rows = {}
        self.actualizar_validacion_archivos()

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
        btn_044 = ctk.CTkButton(panel, text="Cargar manual 044", command=self.seleccionar_044, width=220, height=42)
        btn_044.pack(anchor="w", padx=24, pady=(0, 12))

        self.lbl_090 = ctk.CTkLabel(panel, text="090 no seleccionado", anchor="w", justify="left")
        self.lbl_090.pack(anchor="w", padx=24, pady=(8, 6))
        btn_090 = ctk.CTkButton(panel, text="Cargar manual 090", command=self.seleccionar_090, width=220, height=42)
        btn_090.pack(anchor="w", padx=24, pady=(0, 12))

        self.lbl_077 = ctk.CTkLabel(panel, text="077 no seleccionado", anchor="w", justify="left")
        self.lbl_077.pack(anchor="w", padx=24, pady=(8, 6))
        btn_077 = ctk.CTkButton(panel, text="Cargar manual 077", command=self.seleccionar_077, width=220, height=42)
        btn_077.pack(anchor="w", padx=24, pady=(0, 20))

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(10, 20))

        self.btn_procesar = ctk.CTkButton(
            acciones,
            text="PROCESAR",
            command=self.procesar,
            width=220,
            height=48,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=("Segoe UI", 14, "bold")
        )
        self.btn_procesar.pack(side="left", padx=(0, 12))

        btn_acerca_de = ctk.CTkButton(
            acciones,
            text="ACERCA DE",
            command=self.master.mostrar_acerca_de,
            width=180,
            height=48,
            fg_color="#1d4ed8",
            hover_color="#1e40af",
            font=("Segoe UI", 14, "bold")
        )
        btn_acerca_de.pack(side="left", padx=(0, 12))

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

        self.estado = ctk.CTkLabel(self, text="", text_color="#86efac", font=("Segoe UI", 12, "bold"))
        self.estado.pack(anchor="w", padx=20, pady=(0, 10))

        self.frame_log = ctk.CTkFrame(
            self,
            fg_color="#0f172a",
            corner_radius=14,
            border_width=1,
            border_color="#334155"
        )
        self.frame_log.pack(fill="x", padx=20, pady=(0, 10))

        lbl_log = ctk.CTkLabel(self.frame_log, text="ACTIVIDAD", font=("Segoe UI", 12, "bold"), text_color="#cbd5e1")
        lbl_log.pack(anchor="w", padx=12, pady=(12, 0))

        self.log = ctk.CTkTextbox(self.frame_log, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x", padx=12, pady=(6, 12))

        self._cargar_todas_archivos_automaticos()

    def _icono_estado(self, estado):
        if estado == "OK":
            return "✅"
        if estado == "INVALIDO":
            return "⚠"
        return "❌"

    def actualizar_validacion_archivos(self):
        for widget in self.validacion_grid.winfo_children():
            widget.destroy()

        recursos = validar_archivos_requeridos(APP_ROOT)
        for idx, recurso in enumerate(recursos):
            fila = ctk.CTkFrame(self.validacion_grid, fg_color="#0f172a", corner_radius=10, border_width=1, border_color="#334155")
            fila.grid(row=idx, column=0, sticky="ew", padx=0, pady=6)
            fila.grid_columnconfigure(0, weight=0)
            fila.grid_columnconfigure(1, weight=1)

            estado = self._icono_estado(recurso["estado"])
            ctk.CTkLabel(fila, text=f"{estado} {recurso['nombre']}", font=("Segoe UI", 11, "bold"), text_color="#f8fafc").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(8, 2))
            ctk.CTkLabel(fila, text=recurso["ruta"], font=("Segoe UI", 10), text_color="#cbd5e1", wraplength=900, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))
            ctk.CTkLabel(fila, text=f"Estado: {recurso['estado']} | Tamaño: {recurso['size']} | Modificado: {recurso['modificado']}", font=("Segoe UI", 9), text_color="#93c5fd").grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
            self.validacion_rows[recurso["nombre"]] = fila

        faltantes = [recurso for recurso in recursos if recurso["estado"] == "FALTANTE"]
        if hasattr(self, "estado"):
            if faltantes:
                self.estado.configure(text="Hay recursos requeridos faltantes. El procesamiento queda bloqueado.", text_color="#fca5a5")
            else:
                self.estado.configure(text="Validación OK: todos los recursos requeridos fueron localizados.", text_color="#86efac")

    def _agregar_log(self, mensaje):
        if hasattr(self, "log"):
            self.log.configure(state="normal")
            self.log.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {mensaje}\n")
            self.log.see("end")
            self.log.configure(state="disabled")

    def _ruta_data(self):
        asegurar_estructura_runtime(APP_ROOT)
        return APP_DATA_PATH

    def _mostrar_advertencia(self, titulo, mensaje):
        self.estado.configure(text=mensaje, text_color="#fbbf24")
        self._agregar_log(f"Advertencia: {titulo} - {mensaje}")
        messagebox.showwarning(titulo, mensaje)

    def _mostrar_error(self, titulo, mensaje, exc=None):
        self.estado.configure(text=mensaje, text_color="#fca5a5")
        self._agregar_log(f"Error: {titulo} - {mensaje}")
        if exc is not None:
            logging.getLogger(__name__).exception(mensaje)
        messagebox.showerror(titulo, mensaje)

    def _buscar_archivo_automatico(self, prefijo):
        ruta_data = self._ruta_data()
        logger = logging.getLogger(__name__)

        if not ruta_data.exists():
            logger.error("No existe la carpeta /data para buscar archivos. ruta=%s", ruta_data)
            return ""

        candidatos = []
        for archivo in ruta_data.iterdir():
            if not archivo.is_file():
                continue
            nombre = archivo.name.lower()
            if nombre.startswith(f"{prefijo.lower()}"):
                candidatos.append(archivo)

        if not candidatos:
            logger.warning("No se encontró ningún archivo con prefijo %s en %s", prefijo, ruta_data)
            return ""

        candidatos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        archivo = candidatos[0]
        logger.info("Archivo localizado automáticamente. prefijo=%s ruta=%s", prefijo, archivo)
        return str(archivo)

    def _cargar_archivo_automatico(self, prefijo, atributo, label):
        archivo = self._buscar_archivo_automatico(prefijo)

        if not archivo:
            setattr(self, atributo, "")
            label.configure(text=f"{prefijo} no encontrado en /data")
            self._agregar_log(f"Error: no se encontró la base {prefijo} en {self._ruta_data()}")
            return False

        setattr(self, atributo, archivo)
        label.configure(text=archivo)
        self._agregar_log(f"Base {prefijo} cargada automáticamente: {archivo}")
        self.update_idletasks()
        return True

    def _cargar_archivo_manual(self, prefijo, atributo, label):
        archivo = filedialog.askopenfilename(
            title=f"Seleccionar base {prefijo}",
            initialdir=str(self._ruta_data()),
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls *.xlsb *.csv"),
                ("Todos los archivos", "*.*")
            ]
        )

        if not archivo:
            self._agregar_log(f"Carga manual cancelada para la base {prefijo}.")
            return False

        path = Path(archivo)
        if not path.exists():
            self._mostrar_error(
                "Archivo inexistente",
                f"La base {prefijo} seleccionada no existe en disco. Verifique la ruta y vuelva a intentarlo."
            )
            return False

        if path.suffix.lower() not in {".xlsx", ".xls", ".xlsb", ".csv"}:
            self._mostrar_error(
                "Formato no válido",
                f"La base {prefijo} tiene un formato no soportado: {path.suffix or 'sin extensión'}. Use Excel o CSV."
            )
            return False

        setattr(self, atributo, str(path))
        label.configure(text=str(path))
        self.estado.configure(
            text=f"Base {prefijo} cargada manualmente y lista para procesar.",
            text_color="#86efac"
        )
        self._agregar_log(f"Base {prefijo} cargada manualmente: {path}")
        self.update_idletasks()
        return True

    def _cargar_todas_archivos_automaticos(self):
        archivos = {
            "044": ("archivo_044", self.lbl_044),
            "090": ("archivo_090", self.lbl_090),
            "077": ("archivo_077", self.lbl_077),
        }

        encontrados = []
        faltantes = []
        for prefijo, (atributo, label) in archivos.items():
            ok = self._cargar_archivo_automatico(prefijo, atributo, label)
            if ok:
                encontrados.append(getattr(self, atributo))
            else:
                faltantes.append(prefijo)

        if faltantes:
            self.estado.configure(
                text=f"Faltan bases: {', '.join(faltantes)}. Verifique la carpeta /data.",
                text_color="#fca5a5"
            )
            self._agregar_log(
                f"Estado: faltan bases para continuar: {', '.join(faltantes)}. Deben estar en /data."
            )
        elif encontrados:
            bases = "044, 090, 077"
            self.estado.configure(
                text=f"Bases cargadas correctamente y listas para procesar: {bases}.",
                text_color="#86efac"
            )
            self._agregar_log(
                f"Estado: bases cargadas y listas para procesar: {bases}."
            )

        return not faltantes

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")

    def seleccionar_044(self):
        self._cargar_archivo_manual("044", "archivo_044", self.lbl_044)

    def seleccionar_090(self):
        self._cargar_archivo_manual("090", "archivo_090", self.lbl_090)

    def seleccionar_077(self):
        self._cargar_archivo_manual("077", "archivo_077", self.lbl_077)

    def procesar(self):
        self.actualizar_validacion_archivos()
        recursos = validar_archivos_requeridos(APP_ROOT)
        faltantes = [recurso["nombre"] for recurso in recursos if recurso["estado"] == "FALTANTE"]
        escribir_log_auditoria(f"Inicio de procesamiento. Archivos validados: {', '.join(recurso['nombre'] for recurso in recursos)}")

        if faltantes:
            detalle = "\n".join(f"- {recurso['nombre']}: {recurso['ruta']}" for recurso in recursos if recurso["estado"] == "FALTANTE")
            self._mostrar_error(
                "Recursos requeridos faltantes",
                f"No se puede iniciar el procesamiento porque faltan recursos obligatorios:\n{detalle}\n\nRevise la ruta indicada y vuelva a intentar."
            )
            return

        rutas = {}
        faltantes = []
        for prefijo, atributo in [("044", "archivo_044"), ("090", "archivo_090"), ("077", "archivo_077")]:
            ruta = getattr(self, atributo, "")
            rutas[prefijo] = ruta
            if not ruta or not Path(ruta).exists():
                faltantes.append(prefijo)

        if faltantes:
            mensajes = ", ".join(faltantes)
            self._mostrar_error(
                "Faltan archivos",
                f"No se encontraron o no están cargados los archivos requeridos: {mensajes}. Verifique la carpeta /data o utilice la carga manual."
            )
            return

        self.btn_procesar.configure(
            state="disabled",
            text="PROCESANDO...",
            fg_color="#f59e0b",
            hover_color="#d97706"
        )
        self.estado.configure(
            text="Las bases están cargadas y se está ejecutando la macro...",
            text_color="#f8fafc"
        )
        self._agregar_log("Bases cargadas correctamente. Inicio de procesamiento de la macro.")
        self.update_idletasks()

        try:
            resultado = ejecutar_control(self.archivo_044, self.archivo_090)
            if not isinstance(resultado, dict) or "resumen" not in resultado or "df" not in resultado:
                raise ValueError("La macro devolvió un resultado inválido. Revisar el procesamiento.")

            resumen = resultado["resumen"]
            df = resultado["df"]

            if not isinstance(df, pd.DataFrame):
                raise TypeError("La macro no devolvió un DataFrame válido para continuar.")

            self.master.df_procesado = df
            self.master.ultima_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.master.resumen = dict(resumen)
            self.master.resumen["ultima_ejecucion"] = self.master.ultima_ejecucion
            resumen_integridad = evaluar_integridad_liquidaciones(
                liquidaciones_detectadas=int(resumen.get("total", 0)),
                liquidaciones_procesadas=int(resumen.get("total", 0)),
                liquidaciones_mostradas=int(len(df)),
                liquidaciones_historizadas=int(len(df)),
            )
            self.master.integridad_procesamiento = {
                "encontradas": int(resumen.get("total", 0)),
                "procesadas": int(resumen.get("total", 0)),
                "mostradas": int(len(df)),
                "historizadas": int(len(df)),
                "descartadas": 0,
                "descartes": [],
                "estado": resumen_integridad["estado"],
                "lista_para_produccion": resumen_integridad["lista_para_produccion"],
                "diferencias": resumen_integridad["diferencias"],
                "justificaciones": {},
            }
            self.master.diagnostico = construir_diagnostico(APP_ROOT)
            if not resumen_integridad["lista_para_produccion"]:
                self._mostrar_error(
                    "Pruebas de Integridad",
                    "El procesamiento no está listo para producción: los conteos de liquidaciones no coinciden. Revise y justifique cada diferencia antes de continuar."
                )

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

            self.estado.configure(
                text=f"Bases cargadas correctamente. La macro finalizó con éxito. Total procesado: {resumen.get('total', 0)} registros.",
                text_color="#86efac"
            )
            escribir_log_auditoria(f"Procesamiento finalizado. Registros totales: {resumen.get('total', 0)}; macro: {resumen.get('macro', 0)}; manual: {resumen.get('manual', 0)}")
            self._agregar_log(
                f"Procesamiento finalizado correctamente. Las bases ya estaban cargadas y el total fue de {resumen.get('total', 0)} registros."
            )
            messagebox.showinfo(
                "Macro ejecutada",
                f"Las bases ya estaban cargadas y se procesaron correctamente.\nRegistros totales: {resumen.get('total', 0)}"
            )
            self.master.mostrar_pantalla("visualizacion")
        except FileNotFoundError as exc:
            self._mostrar_error(
                "Archivo no encontrado",
                f"Falta una base del proceso o no se pudo abrir el archivo. Revise la ruta y vuelva a cargar la información.\nDetalle: {exc}",
                exc
            )
        except (pd.errors.EmptyDataError, KeyError, ValueError, TypeError, OSError) as exc:
            self._mostrar_error(
                "Error de datos",
                f"La macro no pudo procesar las bases porque la estructura o el contenido no coincide con lo esperado.\nDetalle: {exc}",
                exc
            )
        except Exception as exc:
            self._mostrar_error(
                "Error en la macro",
                f"Ocurrió un error inesperado durante el procesamiento.\nDetalle: {exc}",
                exc
            )
        finally:
            self.btn_procesar.configure(
                state="normal",
                text="PROCESAR",
                fg_color="#2563eb",
                hover_color="#1d4ed8"
            )


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

        self.estado = ctk.CTkLabel(
            self,
            text="",
            text_color="#86efac",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            justify="left"
        )
        self.estado.pack(anchor="w", padx=18, pady=(0, 10))

        self.frame_log = ctk.CTkFrame(
            self,
            fg_color="#0f172a",
            corner_radius=14,
            border_width=1,
            border_color="#334155"
        )
        self.frame_log.pack(fill="x", padx=18, pady=(0, 10))

        lbl_log = ctk.CTkLabel(self.frame_log, text="ACTIVIDAD", font=("Segoe UI", 12, "bold"), text_color="#cbd5e1")
        lbl_log.pack(anchor="w", padx=12, pady=(12, 0))

        self.log = ctk.CTkTextbox(self.frame_log, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x", padx=12, pady=(6, 12))

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

    def _agregar_log(self, mensaje):
        if not hasattr(self, "log"):
            return
        self.log.configure(state="normal")
        self.log.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {mensaje}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _ruta_historico(self):
        return APP_DATA_PATH / "Historico_Documentos_Controlados.xlsx"

    def _validar_ruta_historico(self, ruta):
        logger = logging.getLogger(__name__)

        if not ruta.parent.exists():
            ruta.parent.mkdir(parents=True, exist_ok=True)

        if not ruta.parent.exists():
            raise OSError(f"No existe el directorio de historial: {ruta.parent}")

        if ruta.exists() and not ruta.is_file():
            raise OSError(f"La ruta histórica no es un archivo válido: {ruta}")

        if ruta.exists() and not os.access(ruta, os.W_OK):
            raise PermissionError(f"El archivo histórico no tiene permisos de escritura: {ruta}")

        if not ruta.exists() and not os.access(ruta.parent, os.W_OK):
            raise PermissionError(f"El directorio histórico no tiene permisos de escritura: {ruta.parent}")

        logger.info("Validación histórica OK. ruta=%s", ruta)
        return True

    def _escribir_historico_xlsx(self, df_hist, ruta):
        logger = logging.getLogger(__name__)

        try:
            from openpyxl import Workbook, load_workbook
        except ImportError as exc:
            logger.info("No se usará openpyxl porque no está instalado. ruta=%s detalle=%s", ruta, exc)
            return False, str(exc)

        try:
            if ruta.exists():
                libro = load_workbook(ruta)
            else:
                libro = Workbook()

            nombres_hojas = libro.sheetnames
            hoja = None
            nombre_hoja_historico = "Historico_Controlados"
            for nombre in [nombre_hoja_historico, "Historico"]:
                if nombre in nombres_hojas:
                    hoja = libro[nombre]
                    break

            if hoja is None:
                hoja = libro.active
                if hoja.title in {"Sheet", "Sheet1"}:
                    hoja.title = nombre_hoja_historico
                else:
                    hoja = libro.create_sheet(title=nombre_hoja_historico)

            if hoja.max_row == 1 and hoja["A1"].value is None:
                columnas = list(df_hist.columns)
                for idx, nombre_col in enumerate(columnas, start=1):
                    hoja.cell(row=1, column=idx, value=nombre_col)
                fila_inicio = 2
            else:
                fila_inicio = hoja.max_row + 1

            for fila_idx, fila in enumerate(df_hist.itertuples(index=False, name=None), start=fila_inicio):
                for col_idx, valor in enumerate(fila, start=1):
                    hoja.cell(row=fila_idx, column=col_idx, value=valor)

            libro.save(ruta)
            libro.close()
            logger.info("Escritura histórica exitosa usando openpyxl. ruta=%s registros=%s", ruta, len(df_hist))
            return True, "openpyxl"
        except Exception as exc:
            logger.exception(
                "Fallo al escribir con openpyxl. ruta=%s registros=%s",
                ruta,
                len(df_hist),
            )
            return False, str(exc)

    def _escribir_historico_win32com(self, df_hist, ruta):
        logger = logging.getLogger(__name__)

        try:
            import win32com.client
        except ImportError as exc:
            logger.info("No se usará win32com porque no está instalado. ruta=%s detalle=%s", ruta, exc)
            return False, str(exc)

        excel = None
        libro = None
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            if ruta.exists():
                libro = excel.Workbooks.Open(str(ruta))
            else:
                libro = excel.Workbooks.Add()

            nombres_hojas = [hoja.Name for hoja in libro.Worksheets]
            hoja = None
            nombre_hoja_historico = "Historico_Controlados"
            for nombre in [nombre_hoja_historico, "Historico", "Sheet1"]:
                if nombre in nombres_hojas:
                    hoja = libro.Worksheets(nombre)
                    break

            if hoja is None:
                hoja = libro.Worksheets.Add()
                hoja.Name = nombre_hoja_historico

            logger.info("Hoja destino validada. nombre=%s archivo=%s", hoja.Name, ruta)

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
            logger.info("Escritura histórica exitosa usando win32com. ruta=%s registros=%s", ruta, len(df_hist))
            return True, "win32com"
        except Exception as exc:
            logger.exception(
                "Fallo al escribir con win32com. ruta=%s registros=%s",
                ruta,
                len(df_hist),
            )
            return False, str(exc)
        finally:
            if libro is not None:
                try:
                    libro.Close(SaveChanges=True)
                except Exception:
                    logger.debug("No se pudo cerrar el libro de Excel de historial.", exc_info=True)
            if excel is not None:
                try:
                    excel.Quit()
                except Exception:
                    logger.debug("No se pudo cerrar la instancia de Excel del historial.", exc_info=True)

    def _guardar_historico_fallback(self, df_hist, ruta):
        logger = logging.getLogger(__name__)
        rastros = []

        try:
            if importlib.util.find_spec("openpyxl") is not None:
                ruta_xlsx = ruta.with_name(f"{ruta.stem}_fallback.xlsx")
                df_hist.to_excel(ruta_xlsx, index=False)
                rastros.append(str(ruta_xlsx))
                logger.info("Fallback local XLSX guardado. ruta=%s registros=%s", ruta_xlsx, len(df_hist))

            ruta_csv = ruta.with_name(f"{ruta.stem}_fallback.csv")
            df_hist.to_csv(ruta_csv, index=False, encoding="utf-8")
            rastros.append(str(ruta_csv))
            logger.info("Fallback local CSV guardado. ruta=%s registros=%s", ruta_csv, len(df_hist))
            return True, rastros
        except Exception as exc:
            logger.exception(
                "Fallo en el fallback local de persistencia. ruta=%s registros=%s",
                ruta,
                len(df_hist),
            )
            return False, [str(exc)]

    def _guardar_historico_controlados(self, df_controlados):
        if df_controlados is None or df_controlados.empty:
            return True

        ruta = self._ruta_historico()
        logger = logging.getLogger(__name__)

        df_hist = df_controlados.copy()
        df_hist["Fecha_Limpieza"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        df_hist["Estado_Limpieza"] = "CONTROLADO_LIMPIADO"

        logger.info(
            "Intento de persistencia de históricos. ruta=%s registros=%s metodo=pendiente",
            ruta,
            len(df_hist),
        )

        try:
            self._validar_ruta_historico(ruta)
        except Exception:
            logger.exception(
                "No se pudo validar la ruta histórica antes de guardar. ruta=%s registros=%s",
                ruta,
                len(df_hist),
            )
            return False

        if ruta.suffix.lower() == ".xlsx":
            ok_xlsx, detalle_xlsx = self._escribir_historico_xlsx(df_hist, ruta)
            if ok_xlsx:
                logger.info(
                    "Persistencia histórica confirmada. ruta=%s registros=%s metodo=%s",
                    ruta,
                    len(df_hist),
                    detalle_xlsx,
                )
                return True

            logger.warning(
                "openpyxl falló para guardar .xlsx; se ejecuta fallback local. ruta=%s registros=%s detalle=%s",
                ruta,
                len(df_hist),
                detalle_xlsx,
            )
        else:
            ok_com, detalle_com = self._escribir_historico_win32com(df_hist, ruta)
            if ok_com:
                logger.info(
                    "Persistencia histórica confirmada. ruta=%s registros=%s metodo=%s",
                    ruta,
                    len(df_hist),
                    detalle_com,
                )
                return True

            logger.warning(
                "win32com falló para guardar .xlsb; se ejecuta fallback local. ruta=%s registros=%s detalle=%s",
                ruta,
                len(df_hist),
                detalle_com,
            )

        ok_fallback, rutas_fallback = self._guardar_historico_fallback(df_hist, ruta)
        if not ok_fallback:
            logger.error(
                "No se pudo persistir la información histórica. No se eliminan los registros de la macro. ruta=%s registros=%s detalle=%s",
                ruta,
                len(df_hist),
                rutas_fallback,
            )
            return False

        logger.warning(
            "Se usó fallback local porque win32com no está disponible o falló. ruta=%s registros=%s rutas=%s",
            ruta,
            len(df_hist),
            rutas_fallback,
        )
        return True

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
            self.estado.configure(text="No hay documentos para limpiar.", text_color="#fbbf24")
            self._agregar_log("No hay documentos para limpiar en la vista actual.")
            messagebox.showinfo("Sin registros", "No existen documentos controlados para limpiar en la vista actual.")
            return

        controlados = self.df_original[self.df_original["CONTROLADO"].fillna(False).astype(bool)].copy()
        if controlados.empty:
            self.estado.configure(text="No hay documentos seleccionados como controlados.", text_color="#fbbf24")
            self._agregar_log("No hay documentos marcados como controlados para guardar en el histórico.")
            messagebox.showinfo("Sin selección", "No hay documentos marcados como controlados para guardar en el histórico.")
            return

        self.estado.configure(text="Generando histórico de documentos controlados...", text_color="#f8fafc")
        self._agregar_log(f"Inicia generación del histórico para {len(controlados)} documentos controlados.")
        self.update_idletasks()

        persistido = self._guardar_historico_controlados(controlados)
        if not persistido:
            logging.getLogger(__name__).error(
                "No se eliminan registros de la macro porque la escritura del histórico falló. registros=%s",
                len(controlados),
            )
            self.estado.configure(text="Error: no se pudo generar el histórico.", text_color="#fca5a5")
            self._agregar_log("Error: la escritura del histórico falló.")
            messagebox.showerror(
                "Error de histórico",
                "No se pudo generar el archivo histórico. Revisa la ruta, permisos y la estructura de los datos."
            )
            return

        self.df_original = self.df_original[
            ~self.df_original["CONTROLADO"].fillna(False).astype(bool)
        ].copy()

        if hasattr(self.master, "df_procesado"):
            self.master.df_procesado = self.df_original.copy()

        if hasattr(self.master, "frames") and "visualizacion" in self.master.frames:
            self.master.frames["visualizacion"].df_original = self.df_original.copy()
            self.master.frames["visualizacion"].cargar_dataframe(self.df_original)

        self.cargar_documentos(self.df_original)
        self.estado.configure(
            text=f"Histórico generado correctamente. Se registraron {len(controlados)} documentos controlados.",
            text_color="#86efac"
        )
        self._agregar_log(f"Histórico generado correctamente para {len(controlados)} documentos controlados.")
        messagebox.showinfo(
            "Histórico generado",
            f"Se registraron correctamente {len(controlados)} documentos en el histórico."
        )

    def volver_al_menu(self):
        self.master.mostrar_pantalla("menu")


PantallaInicio = MenuPrincipal
