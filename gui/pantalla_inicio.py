import customtkinter as ctk
from tkinter import filedialog
from .pantalla_control import PantallaControl

from services.procesar_control import (
    ejecutar_control
)


class PantallaInicio(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(master)

        self.master = master

        self.archivo_044 = ""
        self.archivo_090 = ""
        self.archivo_077 = ""

        self.pack(
            fill="both",
            expand=True
        )

        self.crear_interfaz()

    def crear_interfaz(self):

        titulo = ctk.CTkLabel(
            self,
            text="CONTROLES GLUCO V2",
            font=("Segoe UI", 28, "bold")
        )

        titulo.pack(
            pady=30
        )

        frame = ctk.CTkFrame(self)

        frame.pack(
            padx=30,
            pady=20,
            fill="x"
        )

        # 044

        self.lbl_044 = ctk.CTkLabel(
            frame,
            text="044 no seleccionado"
        )

        self.lbl_044.pack(
            pady=(20, 5)
        )

        btn_044 = ctk.CTkButton(
            frame,
            text="Seleccionar 044",
            command=self.seleccionar_044
        )

        btn_044.pack()

        # 090

        self.lbl_090 = ctk.CTkLabel(
            frame,
            text="090 no seleccionado"
        )

        self.lbl_090.pack(
            pady=(20, 5)
        )

        btn_090 = ctk.CTkButton(
            frame,
            text="Seleccionar 090",
            command=self.seleccionar_090
        )

        btn_090.pack()

        # 077

        self.lbl_077 = ctk.CTkLabel(
            frame,
            text="077 no seleccionado"
        )

        self.lbl_077.pack(
            pady=(20, 5)
        )

        btn_077 = ctk.CTkButton(
            frame,
            text="Seleccionar 077",
            command=self.seleccionar_077
        )

        btn_077.pack()

        # PROCESAR

        btn_procesar = ctk.CTkButton(
            self,
            text="PROCESAR",
            height=50,
            font=("Segoe UI", 18, "bold"),
            command=self.procesar
        )

        btn_procesar.pack(
            pady=30
        )

        self.estado = ctk.CTkLabel(
            self,
            text=""
        )

        self.estado.pack(
            pady=10
        )

    def seleccionar_044(self):

        archivo = filedialog.askopenfilename(
            filetypes=[
                ("Excel", "*.xlsx")
            ]
        )

        if archivo:

            self.archivo_044 = archivo

            self.lbl_044.configure(
                text=archivo
            )

    def seleccionar_090(self):

        archivo = filedialog.askopenfilename(
            filetypes=[
                ("Excel", "*.xlsx")
            ]
        )

        if archivo:

            self.archivo_090 = archivo

            self.lbl_090.configure(
                text=archivo
            )

    def seleccionar_077(self):

        archivo = filedialog.askopenfilename(
            filetypes=[
                ("Excel", "*.xlsx")
            ]
        )

        if archivo:

            self.archivo_077 = archivo

            self.lbl_077.configure(
                text=archivo
            )

    def procesar(self):

        if (
            not self.archivo_044
            or not self.archivo_090
            or not self.archivo_077
        ):

            self.estado.configure(
                text="Debe seleccionar los tres archivos."
            )

            return

        self.estado.configure(
            text="Procesando..."
        )

        resumen = ejecutar_control(
            self.archivo_044,
            self.archivo_090
        )

        self.destroy()

        pantalla = PantallaControl(
            self.master
        )

        pantalla.actualizar(
            total=104,
            macro=100,
            manual=4,
            parciales=11,
            finales=81,
            comisiones=8,
            ajustes=4
        )

        pantalla.cargar_liquidaciones(
    [
        {
            "doc": 63271,
            "tipo": "L#",
            "contrato": "902001245A",
            "fecha": "02/10/2026",
            "importe": "25.024.912"
        },
        {
            "doc": 63268,
            "tipo": "L#",
            "contrato": "902001125A",
            "fecha": "06/10/2026",
            "importe": "115.086.671"
        },
        {
            "doc": 63273,
            "tipo": "L#",
            "contrato": "902001107A",
            "fecha": "06/10/2026",
            "importe": "25.369.470"
        },
        {
            "doc": 63222,
            "tipo": "L#",
            "contrato": "902001135A",
            "fecha": "06/10/2026",
            "importe": "605.850.468"
        }
    ]
)