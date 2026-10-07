import customtkinter as ctk
from tkinter import ttk


class Tarjeta(ctk.CTkFrame):

    def __init__(self, master, titulo, valor):

        super().__init__(master)

        self.configure(
            width=220,
            height=120
        )

        self.pack_propagate(False)

        self.lbl_titulo = ctk.CTkLabel(
            self,
            text=titulo,
            font=("Segoe UI", 16, "bold")
        )

        self.lbl_titulo.pack(
            pady=(20, 5)
        )

        self.lbl_valor = ctk.CTkLabel(
            self,
            text=str(valor),
            font=("Segoe UI", 28, "bold")
        )

        self.lbl_valor.pack()

    def actualizar(self, valor):

        self.lbl_valor.configure(
            text=str(valor)
        )


class PantallaControl(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)

        self.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        titulo = ctk.CTkLabel(
            self,
            text="RESUMEN CONTROL",
            font=("Segoe UI", 28, "bold")
        )

        titulo.pack(pady=20)

        self.frame_tarjetas = ctk.CTkFrame(
            self
        )

        self.frame_tarjetas.pack(
            fill="x",
            pady=20
        )

        # =====================================
        # TABLA LIQUIDACIONES
        # =====================================
        frame_tabla = ctk.CTkFrame(self)

        frame_tabla.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=20
        )

        columnas = (
        "doc",
        "tipo",
        "contrato",
        "fecha",
        "importe"
        )

        self.tabla = ttk.Treeview(
        frame_tabla,
        columns=columnas,
        show="headings"
        )

        self.tabla.heading(
        "doc",
        text="Numero Doc"
        )

        self.tabla.heading(
        "tipo",
        text="Tipo"
        )

        self.tabla.heading(
        "contrato",
        text="Contrato"
        )

        self.tabla.heading(
        "fecha",
        text="Fecha Pago"
        )

        self.tabla.heading(
        "importe",
        text="Total a Pagar"
        )

        self.tabla.column(
        "doc",
        width=100
        )

        self.tabla.column(
        "tipo",
        width=80
        )

        self.tabla.column(
        "contrato",
        width=150
        )

        self.tabla.column(
        "fecha",
        width=120
        )

        self.tabla.column(
        "importe",
        width=150
        )

        self.tabla.pack(
        fill="both",
        expand=True
        )

        self.tarjeta_total = Tarjeta(
            self.frame_tarjetas,
            "DOCUMENTOS",
            0
        )

        self.tarjeta_total.pack(
            side="left",
            padx=10
        )

        self.tarjeta_macro = Tarjeta(
            self.frame_tarjetas,
            "CONTROL MACRO",
            0
        )

        self.tarjeta_macro.pack(
            side="left",
            padx=10
        )

        self.tarjeta_manual = Tarjeta(
            self.frame_tarjetas,
            "CONTROL MANUAL",
            0
        )

        self.tarjeta_manual.pack(
            side="left",
            padx=10
        )

        self.tarjeta_parciales = Tarjeta(
            self.frame_tarjetas,
            "PARCIALES",
            0
        )

        self.tarjeta_parciales.pack(
            side="left",
            padx=10
        )

        self.tarjeta_finales = Tarjeta(
            self.frame_tarjetas,
            "FINALES",
            0
        )

        self.tarjeta_finales.pack(
            side="left",
            padx=10
        )

        self.tarjeta_comisiones = Tarjeta(
            self.frame_tarjetas,
            "COMISIONES",
            0
        )

        self.tarjeta_comisiones.pack(
            side="left",
            padx=10
        )

        self.tarjeta_ajustes = Tarjeta(
            self.frame_tarjetas,
            "AJUSTES",
            0
        )

        self.tarjeta_ajustes.pack(
            side="left",
            padx=10
        )

    def actualizar(
        self,
        total,
        macro,
        manual,
        parciales,
        finales,
        comisiones,
        ajustes
    ):
    

        self.tarjeta_total.actualizar(
            total
        )

        self.tarjeta_macro.actualizar(
            macro
        )

        self.tarjeta_manual.actualizar(
            manual
        )

        self.tarjeta_parciales.actualizar(
            parciales
        )

        self.tarjeta_finales.actualizar(
            finales
        )

        self.tarjeta_comisiones.actualizar(
            comisiones
        )

        self.tarjeta_ajustes.actualizar(
            ajustes
        )
    def cargar_liquidaciones(
        self,
        liquidaciones
    ):

        for fila in self.tabla.get_children():

            self.tabla.delete(fila)

        for liq in liquidaciones:

            self.tabla.insert(
                "",
                "end",
                values=(
                    liq["doc"],
                    liq["tipo"],
                    liq["contrato"],
                    liq["fecha"],
                    liq["importe"]
                )
            )