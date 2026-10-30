import logging
import re
from tkinter import ttk

import customtkinter as ctk

from gui import tema as T
import pandas as pd

from processors.clasificador import (
    es_liquidacion_final,
    es_liquidacion_parcial
)


class Tarjeta(ctk.CTkFrame):

    def __init__(self, master, titulo, valor, color):

        super().__init__(master)

        self.configure(
            width=120,
            height=110,
            corner_radius=18,
            fg_color=T.SUPERFICIE,
            border_width=1,
            border_color=T.BORDE
        )

        self.pack_propagate(False)

        self.lbl_titulo = ctk.CTkLabel(
            self,
            text=titulo,
            font=T.ETIQUETA,
            text_color=T.TEXTO_SECUNDARIO,
            anchor="w",
            justify="left"
        )
        self.lbl_titulo.pack(anchor="w", padx=14, pady=(18, 0))

        self.lbl_valor = ctk.CTkLabel(
            self,
            text=str(valor),
            font=T.VALOR_DESTACADO,
            text_color=color,
            anchor="w",
            justify="left"
        )
        self.lbl_valor.pack(anchor="w", padx=14, pady=(8, 18))

    def actualizar(self, valor):

        self.lbl_valor.configure(
            text=str(valor)
        )


class PantallaControl(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)

        self.master = master
        self.df_original = pd.DataFrame()
        self.df_tabla = pd.DataFrame()
        self.tipo_actual = "TODOS"

        self.configure(fg_color=T.FONDO)

        self.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self._aplicar_estilo_tabla()

        # La pantalla tiene dos vistas en el mismo lugar: la lista de liquidaciones y el
        # detalle de una liquidación (antes el detalle se abría en otra ventana).
        self._doc_detalle = None
        self.vista_lista = ctk.CTkFrame(self, fg_color="transparent")
        self.vista_lista.pack(fill="both", expand=True)
        self.vista_detalle = ctk.CTkFrame(self, fg_color="transparent")

        titulo = ctk.CTkLabel(
            self.vista_lista,
            text="Visualizar liquidaciones",
            font=T.TITULO_PANTALLA,
            text_color=T.TEXTO
        )

        titulo.pack(anchor="w", padx=8, pady=(18, 12))

        self.frame_tarjetas = ctk.CTkFrame(self.vista_lista, fg_color="transparent")
        self.frame_tarjetas.pack(fill="x", pady=(0, 12))

        self.tarjeta_total = Tarjeta(self.frame_tarjetas, "DOCUMENTOS", 0, T.SERIE_TOTAL)

        self.tarjeta_macro = Tarjeta(self.frame_tarjetas, "CONTROL MACRO", 0, T.SERIE_MACRO)

        self.tarjeta_manual = Tarjeta(self.frame_tarjetas, "CONTROL MANUAL", 0, T.SERIE_MANUAL)

        self.tarjeta_parciales = Tarjeta(self.frame_tarjetas, "PARCIALES", 0, T.SERIE_PARCIALES)

        self.tarjeta_finales = Tarjeta(self.frame_tarjetas, "FINALES", 0, T.SERIE_FINALES)

        self.tarjeta_comisiones = Tarjeta(self.frame_tarjetas, "COMISIONES", 0, T.SERIE_COMISIONES)

        self.tarjeta_ajustes = Tarjeta(self.frame_tarjetas, "AJUSTES", 0, T.SERIE_AJUSTES)

        tarjetas = (
            self.tarjeta_total, self.tarjeta_macro, self.tarjeta_manual, self.tarjeta_parciales,
            self.tarjeta_finales, self.tarjeta_comisiones, self.tarjeta_ajustes,
        )
        for columna, tarjeta in enumerate(tarjetas):
            self.frame_tarjetas.grid_columnconfigure(columna, weight=1, uniform="tarjetas")
            tarjeta.grid(row=0, column=columna, sticky="ew", padx=(0, 0 if columna == len(tarjetas) - 1 else 10), pady=8)

        self.frame_filtros = ctk.CTkFrame(
            self.vista_lista,
            corner_radius=18,
            fg_color=T.SUPERFICIE,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_filtros.pack(fill="x", pady=(0, 12))

        self.lbl_estado = ctk.CTkLabel(
            self.frame_filtros,
            text="",
            font=T.ETIQUETA,
            text_color=T.OK,
            anchor="w",
            justify="left"
        )
        self.lbl_estado.grid(row=1, column=0, columnspan=4, padx=(18, 18), pady=(0, 12), sticky="w")

        self.frame_filtros.grid_columnconfigure(0, weight=0)
        self.frame_filtros.grid_columnconfigure(1, weight=0)
        self.frame_filtros.grid_columnconfigure(2, weight=0)
        self.frame_filtros.grid_columnconfigure(3, weight=0)
        self.frame_filtros.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            self.frame_filtros,
            text="Fecha",
            font=T.ETIQUETA,
            text_color=T.TEXTO_SUAVE
        ).grid(row=0, column=0, padx=(18, 8), pady=18, sticky="w")

        self.combo_fecha = ctk.CTkComboBox(
            self.frame_filtros,
            values=["Todas"],
            width=180,
            command=self.filtrar_fecha,
            border_color=T.BORDE_FUERTE,
            fg_color=T.SUPERFICIE_HUNDIDA,
            dropdown_fg_color=T.SUPERFICIE,
            dropdown_text_color=T.TEXTO_SUAVE,
            dropdown_hover_color=T.SUPERFICIE_ELEVADA,
            button_color=T.BORDE_FUERTE,
            button_hover_color=T.TEXTO_TENUE,
            text_color=T.TEXTO
        )
        self.combo_fecha.set("Todas")
        self.combo_fecha.grid(row=0, column=1, padx=(0, 24), pady=18, sticky="w")

        ctk.CTkLabel(
            self.frame_filtros,
            text="Tipo de documento",
            font=T.ETIQUETA,
            text_color=T.TEXTO_SUAVE
        ).grid(row=0, column=2, padx=(0, 8), pady=18, sticky="w")

        self.combo_tipo = ctk.CTkComboBox(
            self.frame_filtros,
            values=["TODOS", "PARCIALES", "FINALES", "COMISIONES", "AJUSTES"],
            width=220,
            command=self.filtrar_tipo,
            border_color=T.BORDE_FUERTE,
            fg_color=T.SUPERFICIE_HUNDIDA,
            dropdown_fg_color=T.SUPERFICIE,
            dropdown_text_color=T.TEXTO_SUAVE,
            dropdown_hover_color=T.SUPERFICIE_ELEVADA,
            button_color=T.BORDE_FUERTE,
            button_hover_color=T.TEXTO_TENUE,
            text_color=T.TEXTO
        )
        self.combo_tipo.set("TODOS")
        self.combo_tipo.grid(row=0, column=3, padx=(0, 18), pady=18, sticky="w")

        self.frame_tabla = ctk.CTkFrame(
            self.vista_lista,
            corner_radius=18,
            fg_color=T.SUPERFICIE,
            border_width=1,
            border_color=T.BORDE
        )
        self.frame_tabla.pack(fill="both", expand=True, pady=(0, 10))

        columnas = ("Nro Doc Interno", "Tipo Doc", "Tipo liquidación", "Contrato", "Fecha Pago", "Forma de pago",
                    "Total", "Controlado")
        self.tabla = ttk.Treeview(
            self.frame_tabla,
            columns=columnas,
            show="headings",
            height=18,
            selectmode="browse"
        )

        for columna in columnas:
            self.tabla.heading(columna, text=columna)
            self.tabla.column(columna, anchor="center", width=160)

        self.tabla.column("Nro Doc Interno", width=128, anchor="center", stretch=False)
        self.tabla.column("Tipo Doc", width=75, anchor="center", stretch=False)
        self.tabla.column("Tipo liquidación", width=210, anchor="w")
        self.tabla.column("Contrato", width=115, anchor="center", stretch=False)
        self.tabla.column("Fecha Pago", width=100, anchor="center", stretch=False)
        self.tabla.column("Forma de pago", width=200, anchor="w")
        self.tabla.column("Total", width=140, anchor="e", stretch=False)
        self.tabla.column("Controlado", width=95, anchor="center", stretch=False)

        self.tabla.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        scroll_y = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tabla.yview)
        scroll_y.pack(side="right", fill="y", pady=12)

        scroll_x = ttk.Scrollbar(self.frame_tabla, orient="horizontal", command=self.tabla.xview)
        scroll_x.pack(side="bottom", fill="x", padx=12)

        self.tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tabla.bind("<Double-1>", lambda event: self.ver_detalle())

        self.frame_acciones = ctk.CTkFrame(self.vista_lista, fg_color="transparent")
        self.frame_acciones.pack(side="bottom", pady=(8, 12), before=self.frame_tabla)

        self.btn_detalle = ctk.CTkButton(
            self.frame_acciones,
            text="Ver detalle",
            command=self.ver_detalle,
            width=190,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.PRIMARIO,
            hover_color=T.PRIMARIO_HOVER,
            text_color=T.TEXTO_SOBRE_COLOR,
            font=T.BOTON
        )
        self.btn_detalle.pack(side="left", padx=8)

        self.btn_marcar = ctk.CTkButton(
            self.frame_acciones,
            text="Marcar controlado",
            command=self.toggle_controlado,
            width=220,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.EXITO,
            hover_color=T.EXITO_HOVER,
            text_color=T.TEXTO_SOBRE_COLOR,
            font=T.BOTON
        )
        self.btn_marcar.pack(side="left", padx=8)

    def _aplicar_estilo_tabla(self):

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            logging.getLogger(__name__).debug("No se pudo aplicar el tema clam de ttk", exc_info=True)

        style.configure(
            "Treeview",
            background=T.SUPERFICIE_HUNDIDA,
            foreground=T.TEXTO_SUAVE,
            rowheight=28,
            fieldbackground=T.SUPERFICIE_HUNDIDA,
            borderwidth=0,
            bordercolor=T.SUPERFICIE_HUNDIDA,
            lightcolor=T.SUPERFICIE_HUNDIDA,
            darkcolor=T.SUPERFICIE_HUNDIDA
        )
        style.map(
            "Treeview",
            background=[("selected", T.PRIMARIO)],
            foreground=[("selected", T.TEXTO_SOBRE_COLOR)]
        )
        style.configure(
            "Treeview.Heading",
            background=T.ENCABEZADO_TABLA,
            foreground=T.TEXTO,
            relief="flat",
            font=(T.FUENTE, 10, "bold")
        )
        style.map(
            "Treeview.Heading",
            background=[("active", T.BORDE)]
        )

        # Barras de desplazamiento al tono de la app (antes eran grises claras).
        for orientacion in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(
                orientacion,
                background=T.BORDE,
                troughcolor=T.SUPERFICIE_HUNDIDA,
                bordercolor=T.SUPERFICIE_HUNDIDA,
                lightcolor=T.BORDE,
                darkcolor=T.BORDE,
                arrowcolor=T.TEXTO_SECUNDARIO,
                relief="flat"
            )
            style.map(orientacion, background=[("active", T.BORDE_FUERTE)])

    def mostrar_estado(self, mensaje, color=T.OK):

        self.lbl_estado.configure(
            text=mensaje,
            text_color=color,
            fg_color=T.FONDO_DE_ESTADO.get(color, T.SUPERFICIE_HUNDIDA),
            corner_radius=10
        )
        self.lbl_estado.update_idletasks()

    def _formatear_numero(self, valor):

        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return "0,00"

        return f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    @staticmethod
    def _texto_columna(fila, columnas):
        """Primer valor no vacío entre varias columnas posibles, como texto limpio."""
        for columna in columnas:
            if columna in fila.index:
                valor = fila.get(columna)
                if valor is not None and not (isinstance(valor, float) and pd.isna(valor)):
                    texto = re.sub(r"\s+", " ", str(valor)).strip()
                    if texto and texto.lower() != "nan":
                        return texto
        return ""

    def toggle_controlado(self):
        seleccion = self.tabla.selection()

        if not seleccion:
            return

        item = self.tabla.item(seleccion[0])
        self._alternar_controlado(item["values"][0])

    def _alternar_controlado(self, numero_doc):
        """Marca o desmarca como controlada una liquidación y refresca la lista sin perder la selección."""
        numero_doc = str(numero_doc).strip()

        if "CONTROLADO" not in self.df_original.columns:
            self.df_original["CONTROLADO"] = False

        mask = self.df_original["Numero Doc"].astype(str).str.strip() == numero_doc
        self.df_original.loc[mask, "CONTROLADO"] = ~self.df_original.loc[mask, "CONTROLADO"].fillna(False).astype(bool)

        if hasattr(self.master, "df_procesado"):
            self.master.df_procesado = self.df_original.copy()

        fecha_actual = self.combo_fecha.get()
        tipo_actual = self.combo_tipo.get()
        self.aplicar_filtros(fecha_actual, tipo_actual)
        self.seleccionar_documento(numero_doc)

    def limpiar_controlados(self):
        if "CONTROLADO" not in self.df_original.columns:
            return

        self.df_original = self.df_original[
            ~self.df_original["CONTROLADO"].fillna(False).astype(bool)
        ].copy()

        fecha_actual = self.combo_fecha.get()
        tipo_actual = self.combo_tipo.get()
        self.aplicar_filtros(fecha_actual, tipo_actual)

    def seleccionar_documento(self, numero_doc):
        """Selecciona y hace visible en la tabla la fila del documento indicado.
        Devuelve True si la fila está en la tabla (puede no estarlo por los filtros)."""
        numero_doc = str(numero_doc).strip()
        for item_id in self.tabla.get_children():
            valores = self.tabla.item(item_id, "values")
            if valores and str(valores[0]).strip() == numero_doc:
                self.tabla.selection_set(item_id)
                self.tabla.focus(item_id)
                self.tabla.see(item_id)
                return True
        return False

    def ver_detalle(self, numero_doc=None):

        if numero_doc is None:
            seleccion = self.tabla.selection()

            if not seleccion:
                children = self.tabla.get_children()
                if not children:
                    return
                self.tabla.selection_set(children[0])
                seleccion = self.tabla.selection()

            if not seleccion:
                return

            item = self.tabla.item(seleccion[0])

            if not item or not item["values"]:
                return

            numero_doc = item["values"][0]

        numero_doc = str(numero_doc).strip()

        detalle = self.df_original[
            self.df_original["Numero Doc"].astype(str).str.strip() == numero_doc
        ].copy()

        if detalle.empty:
            return

        def obtener_valor(fila, columnas, valor_default=""):
            for columna in columnas:
                if columna in fila.index and pd.notna(fila.get(columna, valor_default)):
                    valor = fila.get(columna, valor_default)
                    if isinstance(valor, pd.Timestamp):
                        return valor.strftime("%d/%m/%Y")
                    return str(valor)
            return str(valor_default)

        def formatear_importe(valor):
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                return "$ 0,00"

            abs_numero = abs(numero)
            texto = f"{abs_numero:,.2f}"
            texto = texto.replace(",", "X")
            texto = texto.replace(".", ",")
            texto = texto.replace("X", ".")
            signo = "-" if numero < 0 else ""
            return f"{signo}$ {texto}"

        primer_fila = detalle.iloc[0].copy()

        contrato = obtener_valor(primer_fila, ["Contrato"], "-")
        tipo_doc = obtener_valor(primer_fila, ["Tipo Doc"], "-")
        fecha_pago = obtener_valor(primer_fila, ["Fecha Pago"], "-")
        vendedor = obtener_valor(primer_fila, ["Nombre Vendedor", "Vendedor"], "-")
        corredor = obtener_valor(primer_fila, ["Nombre Corredor", "Corredor"], "-")

        total = primer_fila.get("Total a Pagar", None)
        tipo_liquidacion = self._texto_columna(primer_fila, ("Tip Liquidacion", "Descripcion de la liquidacion")) or "-"
        controlado = (
            bool(detalle["CONTROLADO"].fillna(False).astype(bool).any()) if "CONTROLADO" in detalle.columns else False
        )

        self._doc_detalle = numero_doc
        for hijo in self.vista_detalle.winfo_children():
            hijo.destroy()

        # --- Cabecera: número, estado, total y acciones
        cabecera = ctk.CTkFrame(
            self.vista_detalle, fg_color=T.SUPERFICIE, corner_radius=18, border_width=1, border_color=T.BORDE
        )
        cabecera.pack(fill="x", pady=(8, 10))
        cabecera.grid_columnconfigure(0, weight=1)

        izquierda = ctk.CTkFrame(cabecera, fg_color="transparent")
        izquierda.grid(row=0, column=0, sticky="w", padx=20, pady=(14, 4))
        ctk.CTkLabel(izquierda, text="CONTROL · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        fila_titulo = ctk.CTkFrame(izquierda, fg_color="transparent")
        fila_titulo.pack(anchor="w")
        ctk.CTkLabel(
            fila_titulo, text=f"Liquidación {numero_doc}", font=T.TITULO_PANTALLA, text_color=T.TEXTO
        ).pack(side="left")
        ctk.CTkLabel(
            fila_titulo,
            text="  ✓ Controlada  " if controlado else "  Pendiente de control  ",
            font=T.ETIQUETA_CHICA,
            text_color=T.OK if controlado else T.AVISO,
            fg_color=T.OK_FONDO if controlado else T.AVISO_FONDO,
            corner_radius=8,
        ).pack(side="left", padx=14)
        ctk.CTkLabel(
            izquierda,
            text=f"{tipo_liquidacion}  ·  {tipo_doc}  ·  Pago {fecha_pago}",
            font=T.CUERPO,
            text_color=T.TEXTO_SECUNDARIO,
        ).pack(anchor="w", pady=(2, 0))

        derecha = ctk.CTkFrame(cabecera, fg_color="transparent")
        derecha.grid(row=0, column=1, sticky="e", padx=20, pady=(14, 4))
        ctk.CTkLabel(derecha, text="Total a pagar", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE).pack(anchor="e")
        ctk.CTkLabel(
            derecha, text=formatear_importe(total), font=(T.FUENTE, 28, "bold"), text_color=T.TEXTO
        ).pack(anchor="e")

        acciones = ctk.CTkFrame(cabecera, fg_color="transparent")
        acciones.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 16))
        estilo_secundario = dict(
            height=38, corner_radius=T.RADIO_BOTON, font=T.BOTON,
            fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO,
        )
        ctk.CTkButton(acciones, text="←  Volver a la lista", command=self.cerrar_detalle, width=180,
                      **estilo_secundario).pack(side="left")

        documentos = [
            str(self.tabla.item(item_id, "values")[0]).strip() for item_id in self.tabla.get_children()
        ]
        posicion = documentos.index(numero_doc) if numero_doc in documentos else None
        anterior = documentos[posicion - 1] if posicion not in (None, 0) else None
        siguiente = documentos[posicion + 1] if posicion is not None and posicion + 1 < len(documentos) else None
        ctk.CTkButton(acciones, text="‹  Anterior", width=120, state="normal" if anterior else "disabled",
                      command=lambda: self._abrir_vecino(anterior), **estilo_secundario).pack(side="left", padx=(12, 6))
        ctk.CTkButton(acciones, text="Siguiente  ›", width=120, state="normal" if siguiente else "disabled",
                      command=lambda: self._abrir_vecino(siguiente), **estilo_secundario).pack(side="left")
        if posicion is not None:
            ctk.CTkLabel(
                acciones, text=f"{posicion + 1} de {len(documentos)} en la lista",
                font=T.CUERPO_CHICO, text_color=T.TEXTO_TENUE,
            ).pack(side="left", padx=12)

        if controlado:
            ctk.CTkButton(
                acciones, text="Quitar marca", width=150,
                command=lambda: self._marcar_desde_detalle(numero_doc), **estilo_secundario,
            ).pack(side="right")
        else:
            if siguiente:
                ctk.CTkButton(
                    acciones, text="Controlada y siguiente  ›", width=210, height=38, corner_radius=T.RADIO_BOTON,
                    font=T.BOTON, fg_color="transparent", hover_color=T.SUPERFICIE_ELEVADA, border_width=1,
                    border_color=T.EXITO, text_color=T.EXITO,
                    command=lambda: self._marcar_desde_detalle(numero_doc, abrir=siguiente),
                ).pack(side="right", padx=(8, 0))
            ctk.CTkButton(
                acciones, text="✓  Marcar como controlada", width=230, height=38, corner_radius=T.RADIO_BOTON,
                font=T.BOTON, fg_color=T.EXITO, hover_color=T.EXITO_HOVER, text_color=T.TEXTO_SOBRE_COLOR,
                command=lambda: self._marcar_desde_detalle(numero_doc),
            ).pack(side="right")

        # --- Datos de la liquidación
        contenido = ctk.CTkScrollableFrame(self.vista_detalle, fg_color=T.FONDO)
        contenido.pack(fill="both", expand=True)

        for columna in range(3):
            contenido.grid_columnconfigure(columna, weight=1, uniform="datos")

        contrato = obtener_valor(primer_fila, ["Contrato"], "-")
        kilos = obtener_valor(primer_fila, ["Unidades", "Kilos"], "-")
        conforme = obtener_valor(primer_fila, ["Conforme", "Estatus Documento", "Estado Documento", "Estado Liq."], "-")
        obs_pago = obtener_valor(primer_fila, ["Concepto", "Obs. de Pago", "Observacion de Pago", "Observacion de Anulacion"], "-")
        forma_pago = obtener_valor(primer_fila, ["Condicion de Pago", "Forma de Pago", "Pago Contra"], "-")
        tipo_vendedor = obtener_valor(primer_fila, ["Tipo de Vendedor", "Descripcion de vendedor", "Tipo Vendedor"], "-")
        fecha_pago_efectiva = obtener_valor(primer_fila, ["Fecha Pago", "Fecha de Pago Efectiva"], "-")
        nro_doc_interno = obtener_valor(primer_fila, ["Numero Doc", "Nro. Doc. Interno"], "-")
        nro_legal = obtener_valor(primer_fila, ["Nro_Legal", "Nro. Legal", "Numero documento fiscal", "Numero de CAE COE Factura", "COE"], "-")
        estado_liq = obtener_valor(primer_fila, ["Estatus Documento", "Estado Liq.", "Estado de liquidacion"], "-")
        id_solicitado = obtener_valor(primer_fila, ["id_largo", "ID solicitado", "Id solicitado"], "-")

        info = [
            ("Total a pagar:", formatear_importe(total)),
            ("Tipo liquidación:", tipo_liquidacion),
            ("Forma de Pago:", forma_pago),
            ("Contrato:", contrato),
            ("Kilos:", kilos),
            ("Conforme:", conforme),
            ("Tipo Documento:", tipo_doc),
            ("Nro. Doc. Interno:", nro_doc_interno),
            ("Nro. Legal (COE):", nro_legal),
            ("Estado Liq.:", estado_liq),
            ("Obs. de Pago:", obs_pago),
            ("Fecha de Pago:", fecha_pago),
            ("Vendedor:", vendedor),
            ("Corredor:", corredor),
            ("Tipo Vendedor:", tipo_vendedor),
            ("Fecha de Pago Efectiva:", fecha_pago_efectiva),
            ("ID solicitado:", id_solicitado),
        ]

        for idx, (label, valor) in enumerate(info):
            fila = ctk.CTkFrame(
                contenido,
                fg_color=T.SUPERFICIE,
                corner_radius=12,
                border_width=1,
                border_color=T.BORDE,
                height=78
            )
            fila.grid(row=idx // 3, column=idx % 3, padx=6, pady=6, sticky="nsew")
            fila.grid_propagate(False)
            fila.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                fila,
                text=str(label).rstrip(":"),
                font=T.ETIQUETA_CHICA,
                text_color=T.TEXTO_TENUE,
                anchor="w",
                justify="left"
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))

            ctk.CTkLabel(
                fila,
                text=str(valor),
                font=(T.FUENTE, 14, "bold"),
                text_color=T.TEXTO,
                anchor="w",
                justify="left",
                wraplength=320
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(2, 10))

        def obtener_columna_flexible(fila, columnas):
            for columna in columnas:
                if columna in fila.index:
                    valor = fila.get(columna)
                    if pd.notna(valor):
                        return str(valor)
            return ""

        def limpiar_texto(valor):
            if pd.isna(valor):
                return ""
            texto = str(valor).strip()
            texto = re.sub(r"\s+", " ", texto)
            return texto

        def armar_descripcion_tax(fila):
            producto = limpiar_texto(fila.get("Producto", ""))
            descripcion = limpiar_texto(
                fila.get("Descripcion de Producto", fila.get("Descripcion del Producto", ""))
            )
            concepto = limpiar_texto(fila.get("Concepto", ""))
            descripcion_base = " ".join(part for part in [descripcion, concepto] if part)

            if descripcion_base:
                texto = descripcion_base
            elif producto:
                texto = producto
            else:
                texto = "Sin descripción disponible"

            if re.search(r"(?i)(AJUA|AJU|RIB|PIB|IIBB|IVA)", producto):
                if "RIB" in producto.upper() or "IIBB" in producto.upper() or "IBB" in producto.upper():
                    texto = descripcion_base or concepto or "Retención " + producto
                elif "PIB" in producto.upper() or "IVA" in producto.upper():
                    texto = descripcion_base or concepto or "Percepción " + producto

            return texto

        def detectar_tipo_tax(texto):
            t = texto.upper()
            if "RIB" in t or "IIBB" in t or "IBB" in t:
                return "Retención"
            if "PIB" in t or "IVA" in t:
                return "Percepción"
            return "Retención / Percepción"

        def construir_registros_retenciones_percepciones(df):
            registros = []
            columnas_base = [
                "Base Imponible",
                "Base imponible",
                "Base de cálculo",
                "Base de calculo",
                "Base",
                "Imponible",
                "Importe imponible",
                "Base Imponible Fiscal",
                "Base cálculos"
            ]
            columnas_aliquota = [
                "Alícuota",
                "Aliquota",
                "Alicuota",
                "Tasa",
                "Porcentaje",
                "Aliquota %",
                "Alícuota %",
                "Porcentaje de retencion",
                "Porcentaje de percepcion"
            ]

            for _, fila in df.iterrows():
                producto = limpiar_texto(fila.get("Producto", ""))
                descripcion = limpiar_texto(
                    fila.get("Descripcion de Producto", fila.get("Descripcion del Producto", ""))
                )
                concepto = limpiar_texto(fila.get("Concepto", ""))
                texto_producto = " ".join(part for part in [producto, descripcion, concepto] if part)

                if not texto_producto:
                    continue

                hay_retencion = any(patron in texto_producto.upper() for patron in ("RIB", "IIBB", "IBB", "RETENCION"))
                hay_percepcion = any(patron in texto_producto.upper() for patron in ("PIB", "IVA", "PERCEPCION"))

                if not hay_retencion and not hay_percepcion:
                    continue

                tipo = "Retención" if hay_retencion else "Percepción"
                concepto_final = armar_descripcion_tax(fila)
                base = obtener_columna_flexible(fila, columnas_base)
                aliquota = obtener_columna_flexible(fila, columnas_aliquota)
                importe = fila.get("Importe Fiscal")
                importe_formateado = formatear_importe(importe)
                codigo = producto or "-"

                registros.append({
                    "Tipo": tipo,
                    "Concepto": concepto_final,
                    "Base de cálculo": base or "-",
                    "Alícuota (%)": aliquota or "-",
                    "Importe": importe_formateado,
                    "Código": codigo,
                    "_key": (
                        tipo,
                        concepto_final,
                        base,
                        aliquota,
                        str(importe),
                        codigo
                    )
                })

            if not registros:
                return []

            df_registros = pd.DataFrame(registros)
            df_registros = df_registros.drop_duplicates(subset=["_key"]).copy()
            return df_registros.drop(columns=["_key"]).to_dict("records")

        registros_tax = construir_registros_retenciones_percepciones(detalle)
        logger = logging.getLogger(__name__)
        logger.info(
            "Retenciones/percepciones detectadas en detalle para Numero Doc %s: %s",
            numero_doc,
            registros_tax
        )

        retenciones_panel = ctk.CTkFrame(
            contenido,
            fg_color=T.SUPERFICIE,
            corner_radius=10,
            border_width=1,
            border_color=T.BORDE
        )
        retenciones_panel.grid(row=100, column=0, columnspan=3, sticky="ew", padx=6, pady=(12, 12))

        ctk.CTkLabel(
            retenciones_panel,
            text="Retenciones y percepciones",
            font=T.SUBTITULO,
            text_color=T.TEXTO
        ).pack(anchor="w", padx=14, pady=(12, 8))

        if not registros_tax:
            ctk.CTkLabel(
                retenciones_panel,
                text="La liquidación no posee retenciones ni percepciones.",
                text_color=T.TEXTO_SECUNDARIO,
                font=T.CUERPO
            ).pack(anchor="w", padx=14, pady=(0, 12))
        else:
            tabla_tax = ttk.Treeview(
                retenciones_panel,
                columns=("Tipo", "Concepto", "Base de cálculo", "Alícuota (%)", "Importe", "Código"),
                show="headings",
                height=8,
                selectmode="browse"
            )
            tabla_tax.heading("Tipo", text="Tipo")
            tabla_tax.heading("Concepto", text="Concepto")
            tabla_tax.heading("Base de cálculo", text="Base de cálculo")
            tabla_tax.heading("Alícuota (%)", text="Alícuota (%)")
            tabla_tax.heading("Importe", text="Importe")
            tabla_tax.heading("Código", text="Código")
            tabla_tax.column("Tipo", width=90, anchor="center")
            tabla_tax.column("Concepto", width=320, anchor="w")
            tabla_tax.column("Base de cálculo", width=170, anchor="e")
            tabla_tax.column("Alícuota (%)", width=110, anchor="center")
            tabla_tax.column("Importe", width=150, anchor="e")
            tabla_tax.column("Código", width=170, anchor="center")
            tabla_tax.pack(fill="x", padx=12, pady=(0, 12))

            scroll_tax_y = ttk.Scrollbar(retenciones_panel, orient="vertical", command=tabla_tax.yview)
            scroll_tax_y.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
            tabla_tax.configure(yscrollcommand=scroll_tax_y.set)

            for registro in registros_tax:
                tabla_tax.insert(
                    "",
                    "end",
                    values=(
                        registro["Tipo"],
                        registro["Concepto"],
                        registro["Base de cálculo"],
                        registro["Alícuota (%)"],
                        registro["Importe"],
                        registro["Código"],
                    )
                )

        self.vista_lista.pack_forget()
        self.vista_detalle.pack(fill="both", expand=True)

    def detalle_abierto(self):
        return self._doc_detalle is not None

    def cerrar_detalle(self):
        """Vuelve a la lista dejando seleccionada la liquidación que se estaba viendo."""
        documento = self._doc_detalle
        self._doc_detalle = None
        self.vista_detalle.pack_forget()
        self.vista_lista.pack(fill="both", expand=True)
        if documento:
            self.seleccionar_documento(documento)

    def volver_interno(self):
        """Lo usa el botón Volver de la app: si hay un detalle abierto, primero vuelve a la lista."""
        if self.detalle_abierto():
            self.cerrar_detalle()
            return True
        return False

    def _abrir_vecino(self, numero_doc):
        if numero_doc:
            self.seleccionar_documento(numero_doc)
            self.ver_detalle(numero_doc=numero_doc)

    def _marcar_desde_detalle(self, numero_doc, abrir=None):
        self._alternar_controlado(numero_doc)
        self.ver_detalle(numero_doc=abrir or numero_doc)

    def actualizar(self, total, macro, manual, parciales, finales, comisiones, ajustes):

        self.tarjeta_total.actualizar(total)
        self.tarjeta_macro.actualizar(macro)
        self.tarjeta_manual.actualizar(manual)
        self.tarjeta_parciales.actualizar(parciales)
        self.tarjeta_finales.actualizar(finales)
        self.tarjeta_comisiones.actualizar(comisiones)
        self.tarjeta_ajustes.actualizar(ajustes)

    def cargar_dataframe(self, df):

        if self.detalle_abierto():
            self.cerrar_detalle()

        self.df_original = df.copy()

        if "CONTROLADO" not in self.df_original.columns:
            self.df_original["CONTROLADO"] = False

        self.df_original["CONTROLADO"] = self.df_original["CONTROLADO"].fillna(False).astype(bool)

        if "Fecha Pago" in df.columns:
            self.df_original["Fecha Pago"] = pd.to_datetime(self.df_original["Fecha Pago"], errors="coerce")

            fechas = (
                self.df_original["Fecha Pago"]
                .dropna()
                .dt.strftime("%d/%m/%Y")
                .unique()
                .tolist()
            )
            fechas = sorted(fechas)
            self.combo_fecha.configure(values=["Todas"] + fechas)
        else:
            self.combo_fecha.configure(values=["Todas"])

        self.combo_fecha.set("Todas")
        self.combo_tipo.set("TODOS")
        self.mostrar_estado("Datos cargados correctamente y listos para visualizar.", T.OK)
        self.aplicar_filtros("Todas", "TODOS")

    def cargar_tabla(self, df):

        for item in self.tabla.get_children():
            self.tabla.delete(item)

        self.df_tabla = df.copy()

        if self.df_tabla.empty:
            return

        documentos = self.df_tabla.copy()

        if "RESULTADO_FINAL" in documentos.columns:
            documentos = documentos[
                documentos["RESULTADO_FINAL"] == "CONTROL MACRO"
            ]

        documentos = documentos.sort_values("Numero Doc").drop_duplicates(subset=["Numero Doc"], keep="first")
        self.df_tabla = documentos.copy()

        for idx, _ in enumerate(documentos.iterrows()):
            _, fila = _
            fila = fila.copy()
            fecha_str = ""
            if "Fecha Pago" in fila and pd.notna(fila["Fecha Pago"]):
                fecha_str = pd.to_datetime(fila["Fecha Pago"]).strftime("%d/%m/%Y")

            valor_total = fila.get("Total a Pagar", 0)
            controlado = bool(fila.get("CONTROLADO", False))
            tipo_liquidacion = self._texto_columna(fila, ("Tip Liquidacion", "Descripcion de la liquidacion"))
            forma_pago = self._texto_columna(fila, ("Condicion de Pago", "Forma de Pago", "Pago Contra"))
            tag = "par" if idx % 2 == 0 else "impar"

            self.tabla.insert(
                "",
                "end",
                values=(
                    fila.get("Numero Doc", ""),
                    fila.get("Tipo Doc", ""),
                    tipo_liquidacion,
                    fila.get("Contrato", ""),
                    fecha_str,
                    forma_pago,
                    self._formatear_numero(valor_total),
                    "SI" if controlado else "NO",
                ),
                tags=(tag,)
            )

        self.tabla.tag_configure("par", background=T.SUPERFICIE_HUNDIDA)
        self.tabla.tag_configure("impar", background=T.SUPERFICIE)

    def filtrar_fecha(self, fecha):

        tipo = self.combo_tipo.get()
        self.aplicar_filtros(fecha, tipo)

    def filtrar_tipo(self, tipo):

        self.tipo_actual = tipo
        fecha = self.combo_fecha.get()
        self.aplicar_filtros(fecha, tipo)

    def aplicar_filtros(self, fecha, tipo):

        df = self.df_original.copy()

        if df.empty:
            self.mostrar_estado("No hay resultados para el filtro seleccionado.", T.ERROR)
            self.cargar_tabla(df)
            return

        estado_tipo = tipo if tipo and tipo != "TODOS" else "todos"
        self.mostrar_estado(f"Mostrando {len(df)} documentos para {estado_tipo}.", T.INFO)

        if "Fecha Pago" in df.columns:
            df["Fecha Pago"] = pd.to_datetime(df["Fecha Pago"], errors="coerce")

        if fecha not in (None, "", "Todas") and "Fecha Pago" in df.columns:
            df = df[df["Fecha Pago"].dt.strftime("%d/%m/%Y") == fecha]

        if tipo == "TODOS":
            pass
        elif tipo == "PARCIALES":
            df = df[
                (df["Tipo Doc"].astype(str).str.strip() == "L#")
                &
                df.get("Descripcion de la liquidacion", pd.Series(dtype=str)).map(es_liquidacion_parcial)
            ]
        elif tipo == "FINALES":
            df = df[
                (df["Tipo Doc"].astype(str).str.strip() == "L#")
                &
                df.get("Descripcion de la liquidacion", pd.Series(dtype=str)).map(es_liquidacion_final)
            ]
        elif tipo == "COMISIONES":
            df = df[df["Tipo Doc"].astype(str).str.strip() == "C0"]
        elif tipo == "AJUSTES":
            df = df[df["Tipo Doc"].astype(str).str.strip() == "H7"]

        self.cargar_tabla(df)