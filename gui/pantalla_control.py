import logging
from tkinter import ttk

import customtkinter as ctk
import pandas as pd


class Tarjeta(ctk.CTkFrame):

    def __init__(self, master, titulo, valor, color):

        super().__init__(master)

        self.configure(
            width=180,
            height=110,
            corner_radius=18,
            fg_color="#111827",
            border_width=1,
            border_color="#334155"
        )

        self.pack_propagate(False)

        self.lbl_titulo = ctk.CTkLabel(
            self,
            text=titulo,
            font=("Segoe UI", 12, "bold"),
            text_color="#cbd5e1",
            anchor="w",
            justify="left"
        )
        self.lbl_titulo.pack(anchor="w", padx=14, pady=(18, 0))

        self.lbl_valor = ctk.CTkLabel(
            self,
            text=str(valor),
            font=("Segoe UI", 26, "bold"),
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

        self.configure(fg_color="#0b1120")

        self.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self._aplicar_estilo_tabla()

        titulo = ctk.CTkLabel(
            self,
            text="RESUMEN CONTROL",
            font=("Segoe UI", 30, "bold"),
            text_color="#f8fafc"
        )

        titulo.pack(anchor="w", padx=8, pady=(18, 12))

        self.frame_tarjetas = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tarjetas.pack(fill="x", pady=(0, 12))

        self.tarjeta_total = Tarjeta(self.frame_tarjetas, "DOCUMENTOS", 0, "#60a5fa")
        self.tarjeta_total.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_macro = Tarjeta(self.frame_tarjetas, "CONTROL MACRO", 0, "#34d399")
        self.tarjeta_macro.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_manual = Tarjeta(self.frame_tarjetas, "CONTROL MANUAL", 0, "#fbbf24")
        self.tarjeta_manual.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_parciales = Tarjeta(self.frame_tarjetas, "PARCIALES", 0, "#a78bfa")
        self.tarjeta_parciales.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_finales = Tarjeta(self.frame_tarjetas, "FINALES", 0, "#38bdf8")
        self.tarjeta_finales.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_comisiones = Tarjeta(self.frame_tarjetas, "COMISIONES", 0, "#f472b6")
        self.tarjeta_comisiones.pack(side="left", padx=(0, 10), pady=8)

        self.tarjeta_ajustes = Tarjeta(self.frame_tarjetas, "AJUSTES", 0, "#fb7185")
        self.tarjeta_ajustes.pack(side="left", pady=8)

        self.frame_filtros = ctk.CTkFrame(
            self,
            corner_radius=18,
            fg_color="#111827",
            border_width=1,
            border_color="#334155"
        )
        self.frame_filtros.pack(fill="x", pady=(0, 12))

        self.frame_filtros.grid_columnconfigure(0, weight=0)
        self.frame_filtros.grid_columnconfigure(1, weight=0)
        self.frame_filtros.grid_columnconfigure(2, weight=0)
        self.frame_filtros.grid_columnconfigure(3, weight=0)
        self.frame_filtros.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            self.frame_filtros,
            text="Fecha",
            font=("Segoe UI", 12, "bold"),
            text_color="#e2e8f0"
        ).grid(row=0, column=0, padx=(18, 8), pady=18, sticky="w")

        self.combo_fecha = ctk.CTkComboBox(
            self.frame_filtros,
            values=["Todas"],
            width=180,
            command=self.filtrar_fecha,
            border_color="#475569",
            fg_color="#0f172a",
            dropdown_fg_color="#0f172a",
            dropdown_text_color="#e2e8f0"
        )
        self.combo_fecha.set("Todas")
        self.combo_fecha.grid(row=0, column=1, padx=(0, 24), pady=18, sticky="w")

        ctk.CTkLabel(
            self.frame_filtros,
            text="Tipo Documento",
            font=("Segoe UI", 12, "bold"),
            text_color="#e2e8f0"
        ).grid(row=0, column=2, padx=(0, 8), pady=18, sticky="w")

        self.combo_tipo = ctk.CTkComboBox(
            self.frame_filtros,
            values=["TODOS", "PARCIALES", "FINALES", "COMISIONES", "AJUSTES"],
            width=220,
            command=self.filtrar_tipo,
            border_color="#475569",
            fg_color="#0f172a",
            dropdown_fg_color="#0f172a",
            dropdown_text_color="#e2e8f0"
        )
        self.combo_tipo.set("TODOS")
        self.combo_tipo.grid(row=0, column=3, padx=(0, 18), pady=18, sticky="w")

        self.frame_tabla = ctk.CTkFrame(
            self,
            corner_radius=18,
            fg_color="#111827",
            border_width=1,
            border_color="#334155"
        )
        self.frame_tabla.pack(fill="both", expand=True, pady=(0, 10))

        columnas = ("Numero Doc", "Tipo Doc", "Contrato", "Fecha Pago", "Total", "Controlado")
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

        self.tabla.column("Numero Doc", width=130, anchor="center")
        self.tabla.column("Tipo Doc", width=110, anchor="center")
        self.tabla.column("Contrato", width=180, anchor="center")
        self.tabla.column("Fecha Pago", width=130, anchor="center")
        self.tabla.column("Total", width=180, anchor="e")
        self.tabla.column("Controlado", width=120, anchor="center")

        self.tabla.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        scroll_y = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tabla.yview)
        scroll_y.pack(side="right", fill="y", pady=12)

        scroll_x = ttk.Scrollbar(self.frame_tabla, orient="horizontal", command=self.tabla.xview)
        scroll_x.pack(side="bottom", fill="x", padx=12)

        self.tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tabla.bind("<Double-1>", lambda event: self.ver_detalle())

        self.frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acciones.pack(pady=(8, 12))

        self.btn_detalle = ctk.CTkButton(
            self.frame_acciones,
            text="VER DETALLE",
            command=self.ver_detalle,
            width=190,
            height=42,
            corner_radius=12,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_detalle.pack(side="left", padx=8)

        self.btn_marcar = ctk.CTkButton(
            self.frame_acciones,
            text="MARCAR CONTROLADO",
            command=self.toggle_controlado,
            width=220,
            height=42,
            corner_radius=12,
            fg_color="#16a34a",
            hover_color="#15803d",
            text_color="#ffffff",
            font=("Segoe UI", 12, "bold")
        )
        self.btn_marcar.pack(side="left", padx=8)

        self.lbl_estado = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color="#86efac"
        )
        self.lbl_estado.pack(pady=(0, 6))

    def _aplicar_estilo_tabla(self):

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            logging.getLogger(__name__).debug("No se pudo aplicar el tema clam de ttk", exc_info=True)

        style.configure(
            "Treeview",
            background="#0f172a",
            foreground="#e2e8f0",
            rowheight=28,
            fieldbackground="#0f172a",
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", "#2563eb")],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground="#f8fafc",
            relief="flat",
            font=("Segoe UI", 10, "bold")
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#334155")]
        )

    def mostrar_estado(self, mensaje, color="#86efac"):

        self.lbl_estado.configure(text=mensaje, text_color=color)
        self.lbl_estado.update_idletasks()

    def _formatear_numero(self, valor):

        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return "0,00"

        return f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    def toggle_controlado(self):
        seleccion = self.tabla.selection()

        if not seleccion:
            return

        item = self.tabla.item(seleccion[0])
        numero_doc = item["values"][0]

        if "CONTROLADO" not in self.df_original.columns:
            self.df_original["CONTROLADO"] = False

        mask = self.df_original["Numero Doc"].astype(str) == str(numero_doc)
        self.df_original.loc[mask, "CONTROLADO"] = ~self.df_original.loc[mask, "CONTROLADO"].fillna(False).astype(bool)

        fecha_actual = self.combo_fecha.get()
        tipo_actual = self.combo_tipo.get()
        self.aplicar_filtros(fecha_actual, tipo_actual)

    def limpiar_controlados(self):
        if "CONTROLADO" not in self.df_original.columns:
            return

        self.df_original = self.df_original[
            ~self.df_original["CONTROLADO"].fillna(False).astype(bool)
        ].copy()

        fecha_actual = self.combo_fecha.get()
        tipo_actual = self.combo_tipo.get()
        self.aplicar_filtros(fecha_actual, tipo_actual)

    def ver_detalle(self):

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

        numero_doc = str(item["values"][0]).strip()

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

        ventana = ctk.CTkToplevel(self)
        ventana.title("CONTROL - GLUCOVIL")
        ventana.geometry("1180x720")
        ventana.minsize(1000, 620)
        ventana.configure(fg_color="#e2e8f0")
        ventana.grab_set()

        cabecera = ctk.CTkFrame(ventana, fg_color="#0b1120", height=80)
        cabecera.pack(fill="x")
        cabecera.pack_propagate(False)

        ctk.CTkLabel(
            cabecera,
            text="CONTROL - GLUCOVIL",
            font=("Segoe UI", 32, "bold"),
            text_color="#2bbf9a"
        ).place(x=18, y=18)

        contenido = ctk.CTkScrollableFrame(ventana, width=1140, height=640, fg_color="#e2e8f0")
        contenido.pack(fill="both", expand=True, padx=18, pady=18)

        contenido.grid_columnconfigure(0, weight=1)
        contenido.grid_columnconfigure(1, weight=1)

        contrato = obtener_valor(primer_fila, ["Contrato"], "-")
        kilos = obtener_valor(primer_fila, ["Unidades", "Kilos"], "-")
        conforme = obtener_valor(primer_fila, ["Conforme", "Estatus Documento", "Estado Documento", "Estado Liq."], "-")
        obs_pago = obtener_valor(primer_fila, ["Concepto", "Obs. de Pago", "Observacion de Pago", "Observacion de Anulacion"], "-")
        forma_pago = obtener_valor(primer_fila, ["Condicion de Pago", "Forma de Pago", "Pago Contra"], "-")
        tipo_vendedor = obtener_valor(primer_fila, ["Tipo de Vendedor", "Descripcion de vendedor", "Tipo Vendedor"], "-")
        fecha_pago_efectiva = obtener_valor(primer_fila, ["Fecha Pago", "Fecha de Pago Efectiva"], "-")
        nro_doc_interno = obtener_valor(primer_fila, ["Numero Doc", "Nro. Doc. Interno"], "-")
        estado_liq = obtener_valor(primer_fila, ["Estatus Documento", "Estado Liq.", "Estado de liquidacion"], "-")
        id_solicitado = obtener_valor(primer_fila, ["id_largo", "ID solicitado", "Id solicitado"], "-")

        info = [
            ("Contrato:", contrato),
            ("Kilos:", kilos),
            ("Conforme:", conforme),
            ("Tipo Documento:", tipo_doc),
            ("Nro. Doc. Interno:", nro_doc_interno),
            ("Estado Liq.:", estado_liq),
            ("Obs. de Pago:", obs_pago),
            ("Forma de Pago:", forma_pago),
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
                fg_color="#f8fafc",
                corner_radius=12,
                border_width=1,
                border_color="#cbd5e1",
                height=96
            )
            fila.grid(row=idx // 2, column=idx % 2, padx=12, pady=8, sticky="nsew")
            fila.grid_propagate(False)
            fila.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                fila,
                text=str(label),
                font=("Segoe UI", 12, "bold"),
                text_color="#475569",
                anchor="w",
                justify="left"
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))

            ctk.CTkLabel(
                fila,
                text=str(valor),
                font=("Segoe UI", 17, "bold"),
                text_color="#0f172a",
                anchor="w",
                justify="left",
                wraplength=440
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(4, 12))

        retenciones = detalle.loc[
            detalle.get("Producto", pd.Series(dtype=str)).astype(str).str.contains("RIB", case=False, na=False)
        ].copy()

        retenciones_panel = ctk.CTkFrame(contenido, fg_color="#111827", corner_radius=10, border_width=1, border_color="#334155")
        retenciones_panel.grid(row=100, column=0, columnspan=2, sticky="ew", padx=12, pady=(18, 10))
        ctk.CTkLabel(retenciones_panel, text="RETENCIONES", font=("Segoe UI", 15, "bold"), text_color="#f8fafc").pack(anchor="w", padx=14, pady=(12, 8))

        if retenciones.empty:
            ctk.CTkLabel(retenciones_panel, text="No posee retenciones.", text_color="#cbd5e1").pack(anchor="w", padx=14, pady=(0, 12))
        else:
            tabla_ret = ttk.Treeview(
                retenciones_panel,
                columns=("Producto", "Descripcion", "Importe Fiscal"),
                show="headings",
                height=6,
                selectmode="browse"
            )
            tabla_ret.heading("Producto", text="Producto")
            tabla_ret.heading("Descripcion", text="Descripcion")
            tabla_ret.heading("Importe Fiscal", text="Importe Fiscal")
            tabla_ret.column("Producto", width=180, anchor="center")
            tabla_ret.column("Descripcion", width=420, anchor="w")
            tabla_ret.column("Importe Fiscal", width=180, anchor="e")
            tabla_ret.pack(fill="x", padx=12, pady=(0, 12))

            scroll_ret_y = ttk.Scrollbar(retenciones_panel, orient="vertical", command=tabla_ret.yview)
            scroll_ret_y.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
            tabla_ret.configure(yscrollcommand=scroll_ret_y.set)

            for _, fila in retenciones.iterrows():
                producto = str(fila.get("Producto", "-"))
                descripcion = str(fila.get("Descripcion de Producto", fila.get("Descripcion del Producto", "-")))
                importe = formatear_importe(fila.get("Importe Fiscal", 0))
                tabla_ret.insert("", "end", values=(producto, descripcion, importe))

        percepciones = detalle.loc[
            detalle.get("Producto", pd.Series(dtype=str)).astype(str).str.contains("PIB", case=False, na=False)
        ].copy()

        percepciones_panel = ctk.CTkFrame(contenido, fg_color="#111827", corner_radius=10, border_width=1, border_color="#334155")
        percepciones_panel.grid(row=101, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkLabel(percepciones_panel, text="PERCEPCIONES", font=("Segoe UI", 15, "bold"), text_color="#f8fafc").pack(anchor="w", padx=14, pady=(12, 8))

        if percepciones.empty:
            ctk.CTkLabel(percepciones_panel, text="No posee percepciones.", text_color="#cbd5e1").pack(anchor="w", padx=14, pady=(0, 12))
        else:
            tabla_perc = ttk.Treeview(
                percepciones_panel,
                columns=("Producto", "Descripcion", "Importe Fiscal"),
                show="headings",
                height=6,
                selectmode="browse"
            )
            tabla_perc.heading("Producto", text="Producto")
            tabla_perc.heading("Descripcion", text="Descripcion")
            tabla_perc.heading("Importe Fiscal", text="Importe Fiscal")
            tabla_perc.column("Producto", width=180, anchor="center")
            tabla_perc.column("Descripcion", width=420, anchor="w")
            tabla_perc.column("Importe Fiscal", width=180, anchor="e")
            tabla_perc.pack(fill="x", padx=12, pady=(0, 12))

            scroll_perc_y = ttk.Scrollbar(percepciones_panel, orient="vertical", command=tabla_perc.yview)
            scroll_perc_y.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
            tabla_perc.configure(yscrollcommand=scroll_perc_y.set)

            for _, fila in percepciones.iterrows():
                producto = str(fila.get("Producto", "-"))
                descripcion = str(fila.get("Descripcion de Producto", fila.get("Descripcion del Producto", "-")))
                importe = formatear_importe(fila.get("Importe Fiscal", 0))
                tabla_perc.insert("", "end", values=(producto, descripcion, importe))

        ventana.protocol("WM_DELETE_WINDOW", ventana.destroy)

    def actualizar(self, total, macro, manual, parciales, finales, comisiones, ajustes):

        self.tarjeta_total.actualizar(total)
        self.tarjeta_macro.actualizar(macro)
        self.tarjeta_manual.actualizar(manual)
        self.tarjeta_parciales.actualizar(parciales)
        self.tarjeta_finales.actualizar(finales)
        self.tarjeta_comisiones.actualizar(comisiones)
        self.tarjeta_ajustes.actualizar(ajustes)

    def cargar_dataframe(self, df):

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
            tag = "par" if idx % 2 == 0 else "impar"

            self.tabla.insert(
                "",
                "end",
                values=(
                    fila.get("Numero Doc", ""),
                    fila.get("Tipo Doc", ""),
                    fila.get("Contrato", ""),
                    fecha_str,
                    self._formatear_numero(valor_total),
                    "SI" if controlado else "NO",
                ),
                tags=(tag,)
            )

        self.tabla.tag_configure("par", background="#0f172a")
        self.tabla.tag_configure("impar", background="#111827")

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
            self.cargar_tabla(df)
            return

        if "Fecha Pago" in df.columns:
            df["Fecha Pago"] = pd.to_datetime(df["Fecha Pago"], errors="coerce")

        if fecha not in (None, "", "Todas") and "Fecha Pago" in df.columns:
            df = df[df["Fecha Pago"].dt.strftime("%d/%m/%Y") == fecha]

        if tipo == "TODOS":
            pass
        elif tipo == "PARCIALES":
            df = df[
                (df["Tipo Doc"].astype(str) == "L#")
                &
                (df.get("Descripcion de la liquidacion", pd.Series(dtype=str)).astype(str) == "Liquidación Parcial")
            ]
        elif tipo == "FINALES":
            df = df[
                (df["Tipo Doc"].astype(str) == "L#")
                &
                (df.get("Descripcion de la liquidacion", pd.Series(dtype=str)).astype(str) == "Liquidación Final C/Parcial")
            ]
        elif tipo == "COMISIONES":
            df = df[df["Tipo Doc"].astype(str) == "C0"]
        elif tipo == "AJUSTES":
            df = df[df["Tipo Doc"].astype(str) == "H7"]

        self.cargar_tabla(df)