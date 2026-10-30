import importlib.util
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui import tema as T
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


class TarjetaPaso(ctk.CTkFrame):
    """Tarjeta clickeable de un paso del proceso (Cargar, Visualizar, Limpieza)."""

    def __init__(self, master, numero, titulo, comando, etiqueta=None):
        super().__init__(
            master,
            fg_color=T.SUPERFICIE,
            corner_radius=16,
            border_width=1,
            border_color=T.BORDE,
            height=210,
        )
        self.grid_propagate(False)
        self.pack_propagate(False)
        self.comando = comando
        self._color_borde = T.BORDE

        self.lbl_paso = ctk.CTkLabel(self, text=etiqueta or f"Paso {numero}", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE, anchor="w")
        self.lbl_paso.pack(anchor="w", padx=20, pady=(20, 0))
        self.lbl_titulo = ctk.CTkLabel(self, text=titulo, font=(T.FUENTE, 20, "bold"), text_color=T.TEXTO, anchor="w")
        self.lbl_titulo.pack(anchor="w", padx=20, pady=(4, 6))
        self.lbl_detalle = ctk.CTkLabel(
            self, text="", font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, anchor="w", justify="left", wraplength=280
        )
        self.lbl_detalle.pack(anchor="w", padx=20)
        self.lbl_accion = ctk.CTkLabel(self, text="", font=T.ETIQUETA, text_color=T.ENLACE, anchor="w")
        self.lbl_accion.pack(side="bottom", anchor="w", padx=20, pady=(0, 18))

        for widget in (self, self.lbl_paso, self.lbl_titulo, self.lbl_detalle, self.lbl_accion):
            widget.bind("<Button-1>", lambda _event: self.comando())
            widget.bind("<Enter>", lambda _event: self.configure(border_color=T.BORDE_FUERTE if self._color_borde == T.BORDE else self._color_borde, fg_color=T.SUPERFICIE_ELEVADA))
            widget.bind("<Leave>", lambda _event: self.configure(border_color=self._color_borde, fg_color=T.SUPERFICIE))
            widget.configure(cursor="hand2")

    def mostrar(self, estado, detalle, accion):
        """estado: 'siguiente' (resaltado), 'hecho', 'disponible' o 'bloqueado'."""
        colores = {
            "siguiente": (T.PRIMARIO, T.MARCA, T.TEXTO, T.TEXTO_SECUNDARIO, 2),
            "hecho": (T.BORDE, T.OK, T.TEXTO, T.TEXTO_SECUNDARIO, 1),
            "disponible": (T.BORDE, T.TEXTO_TENUE, T.TEXTO, T.TEXTO_SECUNDARIO, 1),
            "bloqueado": (T.BORDE, T.TEXTO_TENUE, T.TEXTO_TENUE, T.TEXTO_TENUE, 1),
            "pronto": (T.BORDE, T.TEXTO_TENUE, T.TEXTO, T.TEXTO_SECUNDARIO, 1),
        }
        borde, color_paso, color_titulo, color_detalle, grosor = colores[estado]
        self._color_borde = borde
        self.configure(border_color=borde, border_width=grosor)
        texto_paso = self.lbl_paso.cget("text").split(" ✓")[0]
        self.lbl_paso.configure(text=texto_paso + (" ✓" if estado == "hecho" else ""), text_color=color_paso)
        self.lbl_titulo.configure(text_color=color_titulo)
        self.lbl_detalle.configure(text=detalle, text_color=color_detalle)
        self.lbl_accion.configure(text=accion, text_color=T.TEXTO_TENUE if estado in ("bloqueado", "pronto") else T.ENLACE)


class MenuControlar(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)

        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=40, pady=(10, 0))

        # --- Cabecera
        ctk.CTkLabel(contenido, text="CONTROL · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        ctk.CTkLabel(contenido, text="Controlar liquidaciones", font=(T.FUENTE, 30, "bold"), text_color=T.TEXTO).pack(anchor="w")

        # --- Proceso: los tres pasos principales
        ctk.CTkLabel(contenido, text="Proceso de control", font=T.SUBTITULO, text_color=T.TEXTO).pack(anchor="w", pady=(32, 12))

        pasos = ctk.CTkFrame(contenido, fg_color="transparent")
        pasos.pack(fill="x")
        for columna in range(3):
            pasos.grid_columnconfigure(columna, weight=1, uniform="pasos")

        self.paso_carga = TarjetaPaso(pasos, 1, "Cargar bases", self.master.mostrar_pantalla_carga)
        self.paso_visualizar = TarjetaPaso(pasos, 2, "Visualizar liquidaciones", self.master.mostrar_pantalla_visualizacion)
        self.paso_limpieza = TarjetaPaso(pasos, 3, "Limpieza de controladas", self.master.mostrar_pantalla_limpieza)
        for columna, tarjeta in enumerate((self.paso_carga, self.paso_visualizar, self.paso_limpieza)):
            tarjeta.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 8, 0 if columna == 2 else 8))

        # --- Pie anclado abajo: herramientas (segunda prioridad) y salir
        pie = ctk.CTkFrame(contenido, fg_color="transparent")
        pie.pack(side="bottom", fill="x", pady=(0, 10))
        tk.Frame(contenido, bg=T.BORDE, height=1).pack(side="bottom", fill="x", pady=(0, 16))

        ctk.CTkLabel(pie, text="Herramientas", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE).pack(side="left", padx=(0, 12))
        for texto, comando in (
            ("Buscador global", self.master.mostrar_pantalla_busqueda),
            ("Métricas generales", self.master.mostrar_pantalla_metrica),
            ("Pruebas de integridad", self.master.ejecutar_prueba_integridad),
        ):
            ctk.CTkButton(
                pie,
                text=texto,
                command=comando,
                width=150,
                height=34,
                corner_radius=T.RADIO_BOTON,
                fg_color="transparent",
                hover_color=T.SUPERFICIE_ELEVADA,
                border_width=1,
                border_color=T.BORDE,
                text_color=T.TEXTO_SECUNDARIO,
                font=T.ETIQUETA_CHICA,
            ).pack(side="left", padx=(0, 8))

        self.actualizar_estado()

    def actualizar_estado(self):
        """Refleja en las tarjetas en qué punto del proceso está el usuario."""
        df = getattr(self.master, "df_procesado", None)
        if df is None:
            self.paso_carga.mostrar("siguiente", "Reportes SAP 044, 090 y 077. Se buscan en la carpeta data o se cargan a mano.", "Empezar →")
            self.paso_visualizar.mostrar("bloqueado", "Revisá cada liquidación y marcá las que ya controlaste.", "Primero procesá las bases")
            self.paso_limpieza.mostrar("bloqueado", "Pasá las liquidaciones controladas al histórico.", "Primero procesá las bases")
            return

        total = int(getattr(self.master, "resumen", {}).get("total", 0) or 0)
        documentos = df["Numero Doc"].nunique() if "Numero Doc" in df.columns else len(df)
        if "CONTROLADO" in df.columns and "Numero Doc" in df.columns:
            controlados = df.loc[df["CONTROLADO"].fillna(False).astype(bool), "Numero Doc"].nunique()
        else:
            controlados = 0

        hora = str(getattr(self.master, "ultima_ejecucion", ""))[-8:-3]
        self.paso_carga.mostrar("hecho", f"Procesado a las {hora}: {total} registros.", "Volver a procesar")
        if controlados:
            self.paso_visualizar.mostrar("disponible", f"{documentos} documentos · {controlados} marcados como controlados.", "Seguir revisando →")
            self.paso_limpieza.mostrar("siguiente", f"{controlados} documentos listos para pasar al histórico.", "Pasar al histórico →")
        else:
            self.paso_visualizar.mostrar("siguiente", f"{documentos} documentos para revisar.", "Revisar →")
            self.paso_limpieza.mostrar("disponible", "Todavía no marcaste documentos como controlados.", "Abrir")


class PantallaMetricas(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.metric_labels = {}
        self.crear_interfaz()

    def crear_interfaz(self):
        titulo = ctk.CTkLabel(
            self,
            text="Métricas generales",
            font=T.TITULO_PANTALLA,
            text_color=T.TEXTO
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 18))

        self.frame_metricas = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE,
            corner_radius=18,
            border_width=1,
            border_color=T.BORDE
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
            frame = ctk.CTkFrame(self.metricas_grid, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=12, border_width=1, border_color=T.BORDE)
            frame.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(frame, text=titulo_metric, font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(anchor="w", padx=12, pady=(10, 2))
            label = ctk.CTkLabel(frame, text="0", font=T.VALOR_DESTACADO, text_color=T.OK)
            label.pack(anchor="w", padx=12, pady=(0, 10))
            self.metric_labels[clave] = label

        self.metricas_grid.grid_columnconfigure(0, weight=1)
        self.metricas_grid.grid_columnconfigure(1, weight=1)
        self.metricas_grid.grid_columnconfigure(2, weight=1)


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
        self.master.volver()


class PantallaBusqueda(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.crear_interfaz()

    def crear_interfaz(self):
        titulo = ctk.CTkLabel(
            self,
            text="Buscador global",
            font=T.TITULO_PANTALLA,
            text_color=T.TEXTO
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 18))

        self.frame_busqueda = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE,
            corner_radius=18,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_busqueda.pack(fill="x", padx=18, pady=(0, 18))

        fila_busqueda = ctk.CTkFrame(self.frame_busqueda, fg_color="transparent")
        fila_busqueda.pack(fill="x", padx=18, pady=18)

        self.buscar_entry = ctk.CTkEntry(
            fila_busqueda,
            placeholder_text="Buscar por número, contrato, proveedor, tipo de liquidación...",
            width=500,
            height=38,
            fg_color=T.SUPERFICIE_HUNDIDA,
            border_color=T.BORDE_FUERTE
        )
        self.buscar_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.buscar_entry.bind("<Return>", lambda _event: self.actualizar_resultados())

        btn_buscar = ctk.CTkButton(
            fila_busqueda,
            text="Buscar",
            command=self.actualizar_resultados,
            width=150,
            height=38,
            fg_color=T.PRIMARIO,
            hover_color=T.PRIMARIO_HOVER,
            font=T.BOTON
        )
        btn_buscar.pack(side="left")

        self.frame_resultados = ctk.CTkFrame(self, fg_color=T.SUPERFICIE, corner_radius=18, border_width=1, border_color=T.BORDE)
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
        self.tabla_busqueda.bind("<Double-1>", self.abrir_detalle)
        self.tabla_busqueda.bind("<Return>", self.abrir_detalle)


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
            self.tabla_busqueda.insert("", "end", values=(numero_doc, contrato, tipo, fecha, estado, "Doble clic para ver ›"))

    def abrir_detalle(self, event=None):
        seleccion = self.tabla_busqueda.selection()
        if not seleccion:
            return
        valores = self.tabla_busqueda.item(seleccion[0], "values")
        if not valores:
            return
        documento = str(valores[0]).strip()
        if documento in ("Sin datos", "Sin coincidencias", ""):
            return

        # Al entrar a Visualizar se restablecen los filtros, así el documento queda a la vista.
        self.master.mostrar_pantalla("visualizacion")
        visual = self.master.frames["visualizacion"]
        visual.seleccionar_documento(documento)
        visual.ver_detalle(numero_doc=documento)

    def volver_al_menu(self):
        self.master.volver()


class PantallaCargaDatos(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)
        self.master = master
        self.archivo_044 = ""
        self.archivo_090 = ""
        self.archivo_077 = ""

        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)

        self.crear_interfaz()

    def crear_interfaz(self):

        titulo = ctk.CTkLabel(
            self,
            text="Carga de datos",
            font=T.TITULO_PANTALLA,
            text_color=T.TEXTO
        )
        titulo.pack(anchor="w", padx=18, pady=(20, 20))

        self.frame_validacion = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE,
            corner_radius=18,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_validacion.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        ctk.CTkLabel(
            self.frame_validacion,
            text="Validación de archivos y recursos",
            font=T.SUBTITULO,
            text_color=T.TEXTO
        ).pack(anchor="w", padx=18, pady=(18, 6))

        self.validacion_grid = ctk.CTkScrollableFrame(self.frame_validacion, fg_color="transparent", height=220)
        self.validacion_grid.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.validacion_rows = {}
        self.actualizar_validacion_archivos()

        panel = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE,
            corner_radius=18,
            border_width=1,
            border_color=T.BORDE
        )
        panel.pack(fill="x", padx=20, pady=(0, 10))

        # Los tres reportes van lado a lado (antes estaban apilados y no entraban en 800 px de alto).
        for columna in range(3):
            panel.grid_columnconfigure(columna, weight=1, uniform="reportes")

        for columna, (prefijo, comando) in enumerate((
            ("044", self.seleccionar_044),
            ("090", self.seleccionar_090),
            ("077", self.seleccionar_077),
        )):
            etiqueta = ctk.CTkLabel(
                panel, text=f"{prefijo} no seleccionado", anchor="w", justify="left", wraplength=320
            )
            etiqueta.grid(row=0, column=columna, sticky="nw", padx=24, pady=(20, 6))
            boton = ctk.CTkButton(panel, text=f"Cargar manual {prefijo}", command=comando, width=220, height=T.ALTO_BOTON,
                                  corner_radius=T.RADIO_BOTON, font=T.BOTON,
                                  fg_color=T.SECUNDARIO, text_color=T.TEXTO_SOBRE_SECUNDARIO, hover_color=T.SECUNDARIO_HOVER)
            boton.grid(row=1, column=columna, sticky="w", padx=24, pady=(0, 20))
            setattr(self, f"lbl_{prefijo}", etiqueta)
            setattr(self, f"btn_{prefijo}", boton)

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(10, 20))

        self.btn_procesar = ctk.CTkButton(
            acciones,
            text="Procesar",
            command=self.procesar,
            width=220,
            height=T.ALTO_BOTON,
            fg_color=T.PRIMARIO,
            hover_color=T.PRIMARIO_HOVER,
            font=T.BOTON
        )
        self.btn_procesar.pack(side="left", padx=(0, 12))


        self.estado = ctk.CTkLabel(self, text="", text_color=T.OK, font=T.ETIQUETA)
        self.estado.pack(anchor="w", padx=20, pady=(0, 10))

        # Barra de progreso: solo visible mientras se procesa.
        self.barra_progreso = ctk.CTkProgressBar(self, mode="indeterminate", height=8, progress_color=T.EN_CURSO)
        self._procesando = False

        self.frame_log = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE_HUNDIDA,
            corner_radius=14,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_log.pack(fill="x", padx=20, pady=(0, 10))

        lbl_log = ctk.CTkLabel(self.frame_log, text="Actividad", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO)
        lbl_log.pack(anchor="w", padx=12, pady=(12, 0))

        self.log = ctk.CTkTextbox(self.frame_log, height=6, state="disabled", wrap="word", fg_color=T.SUPERFICIE_HUNDIDA, text_color=T.TEXTO_SUAVE)
        self.log.pack(fill="x", padx=12, pady=(6, 12))

        # Los botones, el mensaje de estado y la actividad se anclan abajo y se reservan
        # primero su lugar: si la ventana es baja, se achica el panel de archivos en vez
        # de quedar estos elementos fuera de la vista (pasaba en 1200x800 y notebooks).
        self.frame_log.pack_configure(side="bottom", before=self.frame_validacion)
        self.estado.pack_configure(side="bottom", before=self.frame_validacion)
        acciones.pack_configure(side="bottom", before=self.frame_validacion)

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
            fila = ctk.CTkFrame(self.validacion_grid, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=10, border_width=1, border_color=T.BORDE)
            fila.grid(row=idx, column=0, sticky="ew", padx=0, pady=6)
            fila.grid_columnconfigure(0, weight=0)
            fila.grid_columnconfigure(1, weight=1)

            estado = self._icono_estado(recurso["estado"])
            ctk.CTkLabel(fila, text=f"{estado} {recurso['nombre']}", font=T.ETIQUETA_CHICA, text_color=T.TEXTO).grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(8, 2))
            ctk.CTkLabel(fila, text=recurso["ruta"], font=T.NOTA, text_color=T.TEXTO_SECUNDARIO, wraplength=900, justify="left").grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))
            ctk.CTkLabel(fila, text=f"Estado: {recurso['estado']} | Tamaño: {recurso['size']} | Modificado: {recurso['modificado']}", font=T.NOTA, text_color=T.INFO).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
            self.validacion_rows[recurso["nombre"]] = fila

        faltantes = [recurso for recurso in recursos if recurso["estado"] == "FALTANTE"]
        if hasattr(self, "estado"):
            if faltantes:
                self.estado.configure(text="Hay recursos requeridos faltantes. El procesamiento queda bloqueado.", text_color=T.ERROR)
            else:
                self.estado.configure(text="Validación OK: todos los recursos requeridos fueron localizados.", text_color=T.OK)

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
        self.estado.configure(text=mensaje, text_color=T.AVISO)
        self._agregar_log(f"Advertencia: {titulo} - {mensaje}")
        messagebox.showwarning(titulo, mensaje)

    def _mostrar_error(self, titulo, mensaje, exc=None):
        self.estado.configure(text=mensaje, text_color=T.ERROR)
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
            text_color=T.OK
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
                text_color=T.ERROR
            )
            self._agregar_log(
                f"Estado: faltan bases para continuar: {', '.join(faltantes)}. Deben estar en /data."
            )
        elif encontrados:
            bases = "044, 090, 077"
            self.estado.configure(
                text=f"Bases cargadas correctamente y listas para procesar: {bases}.",
                text_color=T.OK
            )
            self._agregar_log(
                f"Estado: bases cargadas y listas para procesar: {bases}."
            )

        return not faltantes

    def volver_al_menu(self):
        self.master.volver()

    def seleccionar_044(self):
        self._cargar_archivo_manual("044", "archivo_044", self.lbl_044)

    def seleccionar_090(self):
        self._cargar_archivo_manual("090", "archivo_090", self.lbl_090)

    def seleccionar_077(self):
        self._cargar_archivo_manual("077", "archivo_077", self.lbl_077)

    def procesar(self):
        if self._procesando:
            return

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

        self._set_procesando(True)
        self._agregar_log("Bases cargadas correctamente. Inicio de procesamiento de la macro.")

        # El cálculo corre en un hilo aparte para que la ventana siga respondiendo.
        # El hilo NO toca la interfaz: solo deja el resultado en self._resultado_hilo,
        # y _revisar_proceso (que corre en el hilo de la ventana) lo levanta.
        self._resultado_hilo = None
        self._inicio_proceso = time.monotonic()
        archivo_044, archivo_090 = self.archivo_044, self.archivo_090

        def tarea():
            try:
                self._resultado_hilo = ("ok", ejecutar_control(archivo_044, archivo_090))
            except Exception as exc:  # se reporta en el hilo principal
                self._resultado_hilo = ("error", exc)

        threading.Thread(target=tarea, daemon=True).start()
        self.after(200, self._revisar_proceso)

    def _set_procesando(self, activo):
        self._procesando = activo
        estado_botones = "disabled" if activo else "normal"
        for boton in (self.btn_044, self.btn_090, self.btn_077):
            boton.configure(state=estado_botones)
        # Mientras procesa no se puede salir de la pantalla (no se cambia de base a mitad del proceso).
        self.master.bloquear_navegacion(activo)

        if activo:
            self.btn_procesar.configure(
                state="disabled",
                text="Procesando…",
                fg_color=T.EN_CURSO,
                hover_color=T.EN_CURSO_HOVER
            )
            self.estado.configure(
                text="Ejecutando la macro… la ventana sigue disponible mientras tanto.",
                text_color=T.TEXTO
            )
            self.barra_progreso.pack(side="bottom", fill="x", padx=20, pady=(0, 10), before=self.estado)
            self.barra_progreso.start()
        else:
            self.barra_progreso.stop()
            self.barra_progreso.pack_forget()
            self.btn_procesar.configure(
                state="normal",
                text="Procesar",
                fg_color=T.PRIMARIO,
                hover_color=T.PRIMARIO_HOVER
            )

    def _revisar_proceso(self):
        if self._resultado_hilo is None:
            segundos = int(time.monotonic() - self._inicio_proceso)
            self.estado.configure(
                text=f"Ejecutando la macro… {segundos} s transcurridos. La ventana sigue disponible mientras tanto."
            )
            self.after(200, self._revisar_proceso)
            return

        tipo, valor = self._resultado_hilo
        self._resultado_hilo = None
        self._set_procesando(False)
        self._finalizar_proceso(tipo, valor)

    def _finalizar_proceso(self, tipo, valor):
        try:
            if tipo == "error":
                raise valor
            resultado = valor
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

            segundos = int(time.monotonic() - self._inicio_proceso)
            self.estado.configure(
                text=f"La macro finalizó con éxito en {segundos} s. Total procesado: {resumen.get('total', 0)} registros.",
                text_color=T.OK
            )
            escribir_log_auditoria(f"Procesamiento finalizado. Registros totales: {resumen.get('total', 0)}; macro: {resumen.get('macro', 0)}; manual: {resumen.get('manual', 0)}")
            self._agregar_log(
                f"Procesamiento finalizado correctamente en {segundos} s. Total: {resumen.get('total', 0)} registros."
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


def crear_estado_vacio(pantalla, titulo, descripcion):
    """Panel que tapa la pantalla cuando todavía no hay datos procesados."""
    vacio = ctk.CTkFrame(pantalla, fg_color=T.FONDO, corner_radius=0)
    centro = ctk.CTkFrame(vacio, fg_color="transparent")
    centro.place(relx=0.5, rely=0.45, anchor="center")
    ctk.CTkLabel(centro, text=titulo, font=(T.FUENTE, 22, "bold"), text_color=T.TEXTO).pack()
    ctk.CTkLabel(
        centro, text=descripcion, font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, wraplength=460, justify="center"
    ).pack(pady=(8, 20))
    botones = ctk.CTkFrame(centro, fg_color="transparent")
    botones.pack()
    ctk.CTkButton(
        botones, text="Ir a carga de datos", command=pantalla.master.mostrar_pantalla_carga,
        width=190, height=T.ALTO_BOTON, corner_radius=T.RADIO_BOTON,
        fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, font=T.BOTON,
    ).pack(side="left", padx=6)
    ctk.CTkButton(
        botones, text="Volver", command=pantalla.master.volver,
        width=160, height=T.ALTO_BOTON, corner_radius=T.RADIO_BOTON,
        fg_color=T.SECUNDARIO, text_color=T.TEXTO_SOBRE_SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, font=T.BOTON,
    ).pack(side="left", padx=6)
    return vacio


def alternar_estado_vacio(vacio, mostrar):
    if mostrar:
        vacio.place(relx=0, rely=0, relwidth=1, relheight=1)
        vacio.lift()
    else:
        vacio.place_forget()


class PantallaVisualizacion(PantallaControl):

    def __init__(self, master):
        super().__init__(master)
        self.master = master


        self.vacio = crear_estado_vacio(
            self,
            "Todavía no hay liquidaciones procesadas",
            "Cargá los reportes 044, 090 y 077 y procesalos para revisar las liquidaciones acá.",
        )

    def mostrar_vacio(self, mostrar):
        alternar_estado_vacio(self.vacio, mostrar)

    def volver_al_menu(self):
        self.master.volver()


class PantallaLimpieza(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.df_original = pd.DataFrame()
        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)
        self.crear_interfaz()

    def crear_interfaz(self):
        ctk.CTkLabel(
            self,
            text="Limpieza de liquidaciones controladas",
            font=T.TITULO_PANTALLA,
            text_color=T.TEXTO
        ).pack(anchor="w", padx=18, pady=(18, 2))
        ctk.CTkLabel(
            self,
            text=(
                "Estas son las liquidaciones que marcaste como controladas en Visualizar. "
                "Al pasarlas al histórico quedan registradas y salen de la vista actual."
            ),
            font=T.CUERPO,
            text_color=T.TEXTO_SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=900,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        # --- Pie anclado abajo: acciones y registro de actividad (se reservan su lugar primero)
        self.frame_log = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE_HUNDIDA,
            corner_radius=14,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_log.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(self.frame_log, text="Actividad", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO).pack(
            anchor="w", padx=12, pady=(10, 0)
        )
        self.log = ctk.CTkTextbox(
            self.frame_log, height=64, state="disabled", wrap="word",
            fg_color=T.SUPERFICIE_HUNDIDA, text_color=T.TEXTO_SUAVE
        )
        self.log.pack(fill="x", padx=12, pady=(4, 10))

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(side="bottom", fill="x", padx=20, pady=(0, 12))

        self.btn_historico = ctk.CTkButton(
            acciones,
            text="Pasar al histórico",
            command=self.eliminar_seleccionados,
            width=240,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.PRIMARIO,
            hover_color=T.PRIMARIO_HOVER,
            font=T.BOTON
        )
        self.btn_historico.pack(side="right")

        self.btn_quitar = ctk.CTkButton(
            acciones,
            text="Quitar marca",
            command=self.quitar_marca,
            width=160,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.SECUNDARIO,
            hover_color=T.SECUNDARIO_HOVER,
            text_color=T.TEXTO_SOBRE_SECUNDARIO,
            font=T.BOTON
        )
        self.btn_quitar.pack(side="right", padx=(0, 10))

        self.estado = ctk.CTkLabel(acciones, text="", text_color=T.OK, font=T.ETIQUETA, anchor="w", justify="left")
        self.estado.pack(side="left")

        # --- Resumen y tabla
        self.lbl_resumen = ctk.CTkLabel(self, text="", font=T.SUBTITULO, text_color=T.TEXTO, anchor="w")
        self.lbl_resumen.pack(anchor="w", padx=20, pady=(0, 8))

        self.frame_tabla = ctk.CTkFrame(
            self,
            fg_color=T.SUPERFICIE,
            corner_radius=18,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_tabla.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        columnas = ("Documento", "Tipo", "Contrato", "Fecha de pago", "Beneficiario", "Total", "Líneas")
        self.tabla = ttk.Treeview(self.frame_tabla, columns=columnas, show="headings", selectmode="browse")
        anchos = {"Documento": 110, "Tipo": 70, "Contrato": 140, "Fecha de pago": 120,
                  "Beneficiario": 300, "Total": 150, "Líneas": 70}
        for columna in columnas:
            self.tabla.heading(columna, text=columna)
            self.tabla.column(
                columna,
                width=anchos[columna],
                anchor="w" if columna == "Beneficiario" else ("e" if columna == "Total" else "center"),
                stretch=columna == "Beneficiario",
            )
        scroll_y = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y", pady=12, padx=(0, 8))
        self.tabla.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=12)
        self.tabla.tag_configure("par", background=T.SUPERFICIE)
        self.tabla.tag_configure("impar", background=T.SUPERFICIE_HUNDIDA)
        self.tabla.bind("<Double-1>", self.ver_detalle)
        self.tabla.bind("<Return>", self.ver_detalle)
        self.tabla.bind("<Delete>", lambda _event: self.quitar_marca())

        # Mensaje cuando hay datos procesados pero ninguna liquidación marcada
        self.sin_marcadas = ctk.CTkFrame(self.frame_tabla, fg_color=T.SUPERFICIE, corner_radius=18)
        centro = ctk.CTkFrame(self.sin_marcadas, fg_color="transparent")
        centro.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(
            centro, text="Todavía no marcaste liquidaciones como controladas",
            font=(T.FUENTE, 18, "bold"), text_color=T.TEXTO
        ).pack()
        ctk.CTkLabel(
            centro,
            text="Revisalas en Visualizar y usá «Marcar controlado» en las que ya estén OK.",
            font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO
        ).pack(pady=(6, 16))
        ctk.CTkButton(
            centro, text="Ir a Visualizar", command=self.master.mostrar_pantalla_visualizacion,
            width=180, height=T.ALTO_BOTON, corner_radius=T.RADIO_BOTON,
            fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, font=T.BOTON
        ).pack()

        self.vacio = crear_estado_vacio(
            self,
            "Todavía no hay liquidaciones procesadas",
            "Procesá las bases y marcá las liquidaciones controladas en Visualizar para pasarlas al histórico desde acá.",
        )

    def mostrar_vacio(self, mostrar):
        alternar_estado_vacio(self.vacio, mostrar)

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

    @staticmethod
    def _titulos_historico(hoja):
        """Títulos de la fila 1, sin las celdas vacías del final."""
        titulos = [celda.value for celda in hoja[1]]
        while titulos and titulos[-1] in (None, ""):
            titulos.pop()
        return [str(titulo) if titulo is not None else "" for titulo in titulos]

    @classmethod
    def _encabezado_historico_valido(cls, hoja):
        """True si la fila 1 tiene un título por columna y ninguna fila de datos es más ancha."""
        titulos = cls._titulos_historico(hoja)
        if not titulos or any(titulo == "" for titulo in titulos):
            return False
        for fila in hoja.iter_rows(min_row=2, values_only=True):
            ancho = 0
            for indice, valor in enumerate(fila, start=1):
                if valor is not None:
                    ancho = indice
            if ancho > len(titulos):
                return False
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

            columnas = [str(columna) for columna in df_hist.columns]
            vacia = hoja.max_row == 1 and hoja["A1"].value is None

            if not vacia and not self._encabezado_historico_valido(hoja):
                # Versiones anteriores agregaban filas debajo de títulos que no coincidían, y el
                # histórico quedaba ilegible para Netting. Se guarda una copia del archivo y se
                # arranca uno nuevo con todos los títulos.
                libro.close()
                respaldo = ruta.with_name(f"{ruta.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}{ruta.suffix}")
                ruta.rename(respaldo)
                logger.warning(
                    "El histórico no tenía títulos válidos; se guardó una copia y se crea uno nuevo. ruta=%s copia=%s",
                    ruta,
                    respaldo,
                )
                libro = Workbook()
                hoja = libro.active
                hoja.title = nombre_hoja_historico
                vacia = True

            if vacia:
                encabezado = list(columnas)
                for idx, nombre_col in enumerate(encabezado, start=1):
                    hoja.cell(row=1, column=idx, value=nombre_col)
                fila_inicio = 2
            else:
                encabezado = self._titulos_historico(hoja)
                # Columnas nuevas (por ejemplo, si cambia el 044) se agregan al final de los títulos.
                for nombre_col in columnas:
                    if nombre_col not in encabezado:
                        encabezado.append(nombre_col)
                        hoja.cell(row=1, column=len(encabezado), value=nombre_col)
                fila_inicio = hoja.max_row + 1

            # Cada dato va a la columna con su mismo título, no a la misma posición.
            posicion = {}
            for idx, nombre_col in enumerate(encabezado, start=1):
                posicion.setdefault(nombre_col, idx)
            for fila_idx, fila in enumerate(df_hist.itertuples(index=False, name=None), start=fila_inicio):
                for nombre_col, valor in zip(columnas, fila):
                    hoja.cell(row=fila_idx, column=posicion[nombre_col], value=valor)

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

    @staticmethod
    def _formatear_importe(valor):
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return "-"
        texto = f"{abs(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{'-' if numero < 0 else ''}$ {texto}"

    def cargar_documentos(self, df):
        self.tabla.delete(*self.tabla.get_children())

        if df is None or df.empty:
            self.df_original = pd.DataFrame()
            self._actualizar_resumen(0)
            return

        self.df_original = df.copy()
        if "CONTROLADO" not in self.df_original.columns:
            self.df_original["CONTROLADO"] = False
        self.df_original["CONTROLADO"] = self.df_original["CONTROLADO"].fillna(False).astype(bool)

        if hasattr(self.master, "df_procesado") and self.master.df_procesado is not None:
            self.master.df_procesado = self.df_original.copy()

        controlados = self.df_original[self.df_original["CONTROLADO"]].copy()
        if controlados.empty or "Numero Doc" not in controlados.columns:
            self._actualizar_resumen(0)
            return

        # Una liquidación puede tener varias líneas (grano, retenciones, percepciones):
        # se muestra una sola fila por documento, con la cantidad de líneas que agrupa.
        controlados["_doc"] = controlados["Numero Doc"].astype(str).str.strip()
        lineas_por_doc = controlados.groupby("_doc", sort=False).size()
        documentos = controlados.drop_duplicates(subset=["_doc"], keep="first").sort_values("_doc")

        for indice, (_, fila) in enumerate(documentos.iterrows()):
            fecha_pago = ""
            if pd.notna(fila.get("Fecha Pago")):
                fecha_pago = pd.to_datetime(fila.get("Fecha Pago")).strftime("%d/%m/%Y")
            beneficiario = fila.get("AB Beneficiario del Pago", fila.get("Nombre Beneficiario del Pago", ""))
            beneficiario = "" if pd.isna(beneficiario) else str(beneficiario)
            self.tabla.insert(
                "",
                "end",
                values=(
                    fila["_doc"],
                    "" if pd.isna(fila.get("Tipo Doc")) else str(fila.get("Tipo Doc", "")),
                    "" if pd.isna(fila.get("Contrato")) else str(fila.get("Contrato", "")),
                    fecha_pago,
                    beneficiario or "-",
                    self._formatear_importe(fila.get("Total a Pagar")),
                    int(lineas_por_doc[fila["_doc"]]),
                ),
                tags=("par" if indice % 2 == 0 else "impar",),
            )

        self._actualizar_resumen(len(documentos))

    def _actualizar_resumen(self, cantidad):
        if cantidad:
            plural = "liquidación lista" if cantidad == 1 else "liquidaciones listas"
            self.lbl_resumen.configure(text=f"{cantidad} {plural} para pasar al histórico")
            self.btn_historico.configure(text=f"Pasar al histórico ({cantidad})")
            self.sin_marcadas.place_forget()
        else:
            self.lbl_resumen.configure(text="Sin liquidaciones marcadas")
            self.btn_historico.configure(text="Pasar al histórico")
            self.sin_marcadas.place(relx=0.5, rely=0.5, relwidth=0.99, relheight=0.97, anchor="center")
            self.sin_marcadas.lift()

    def _documento_seleccionado(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            return None
        valores = self.tabla.item(seleccion[0], "values")
        return str(valores[0]).strip() if valores else None

    def ver_detalle(self, _event=None):
        documento = self._documento_seleccionado()
        if documento:
            self.master.mostrar_pantalla("visualizacion")
            visual = self.master.frames["visualizacion"]
            visual.seleccionar_documento(documento)
            visual.ver_detalle(numero_doc=documento)

    def quitar_marca(self):
        documento = self._documento_seleccionado()
        if not documento:
            self.estado.configure(text="Seleccioná una liquidación de la tabla.", text_color=T.AVISO)
            return
        mascara = self.df_original["Numero Doc"].astype(str).str.strip() == documento
        self.df_original.loc[mascara, "CONTROLADO"] = False
        self.cargar_documentos(self.df_original)
        self.estado.configure(text=f"Se quitó la marca de la liquidación {documento}.", text_color=T.INFO)
        self._agregar_log(f"Liquidación {documento} desmarcada: vuelve a quedar pendiente de control.")

    def eliminar_seleccionados(self):
        if self.df_original.empty:
            self.estado.configure(text="No hay documentos para limpiar.", text_color=T.AVISO)
            self._agregar_log("No hay documentos para limpiar en la vista actual.")
            messagebox.showinfo("Sin registros", "No existen documentos controlados para limpiar en la vista actual.")
            return

        controlados = self.df_original[self.df_original["CONTROLADO"].fillna(False).astype(bool)].copy()
        if controlados.empty:
            self.estado.configure(text="No hay documentos seleccionados como controlados.", text_color=T.AVISO)
            self._agregar_log("No hay documentos marcados como controlados para guardar en el histórico.")
            messagebox.showinfo("Sin selección", "No hay documentos marcados como controlados para guardar en el histórico.")
            return

        cantidad_docs = (
            controlados["Numero Doc"].astype(str).str.strip().nunique()
            if "Numero Doc" in controlados.columns else len(controlados)
        )
        confirmar = messagebox.askyesno(
            "Pasar al histórico",
            f"Se van a registrar {cantidad_docs} liquidación(es) en el histórico de documentos controlados "
            "y van a salir de la vista actual.\n\n¿Continuar?",
            default="no",
        )
        if not confirmar:
            self.estado.configure(text="No se modificó el histórico.", text_color=T.TEXTO_SECUNDARIO)
            return

        self.estado.configure(text="Generando histórico de documentos controlados…", text_color=T.TEXTO)
        self._agregar_log(
            f"Inicia el pase al histórico de {cantidad_docs} liquidación(es) ({len(controlados)} líneas)."
        )
        self.update_idletasks()

        persistido = self._guardar_historico_controlados(controlados)
        if not persistido:
            logging.getLogger(__name__).error(
                "No se eliminan registros de la macro porque la escritura del histórico falló. registros=%s",
                len(controlados),
            )
            self.estado.configure(text="Error: no se pudo generar el histórico.", text_color=T.ERROR)
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
            text=f"Listo: {cantidad_docs} liquidación(es) pasaron al histórico.",
            text_color=T.OK
        )
        self._agregar_log(f"{cantidad_docs} liquidación(es) registradas en el histórico.")
        messagebox.showinfo(
            "Histórico generado",
            f"Se registraron {cantidad_docs} liquidación(es) en el histórico."
        )

    def volver_al_menu(self):
        self.master.volver()


PantallaInicio = MenuControlar
