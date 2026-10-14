from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from services.auditoria import APP_DATA_PATH, APP_ICON_PATH, APP_NAME, APP_VERSION, APP_VERSION_DATE, construir_diagnostico

from .pantalla_inicio import (
    MenuPrincipal,
    PantallaBusqueda,
    PantallaCargaDatos,
    PantallaMetricas,
    PantallaVisualizacion,
    PantallaLimpieza,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1200x800")
        self.minsize(1100, 700)

        self.version = APP_VERSION
        self.icon_path = APP_ICON_PATH
        self._configurar_icono()

        self.ultima_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.diagnostico = construir_diagnostico()
        self.df_procesado = None
        self.resumen = {}
        self.integridad_procesamiento = {
            "encontradas": 0,
            "procesadas": 0,
            "mostradas": 0,
            "descartadas": 0,
            "descartes": [],
        }

        self.frames = {
            "menu": MenuPrincipal(self),
            "metricas": PantallaMetricas(self),
            "busqueda": PantallaBusqueda(self),
            "carga": PantallaCargaDatos(self),
            "visualizacion": PantallaVisualizacion(self),
            "limpieza": PantallaLimpieza(self),
        }

        self.footer = ctk.CTkLabel(
            self,
            text=f"{APP_NAME} • Versión {APP_VERSION}",
            font=("Segoe UI", 10, "bold"),
            text_color="#cbd5e1",
            fg_color="#0f172a",
            corner_radius=0,
        )
        self.footer.pack(side="bottom", fill="x")

        for nombre, frame in self.frames.items():
            frame.pack_forget()

        self.mostrar_pantalla("menu")

    def _configurar_icono(self):
        if not self.icon_path or not self.icon_path.exists():
            return
        try:
            self.iconbitmap(str(self.icon_path))
            self.wm_iconbitmap(str(self.icon_path))
        except Exception:
            pass

    def mostrar_acerca_de(self):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Acerca de - {APP_NAME}")
        ventana.geometry("460x360")
        ventana.minsize(420, 300)
        ventana.transient(self)
        ventana.grab_set()

        if self.icon_path and self.icon_path.exists():
            try:
                ventana.iconbitmap(str(self.icon_path))
            except Exception:
                pass

        contenido = ctk.CTkFrame(ventana, fg_color="#0b1120", corner_radius=18)
        contenido.pack(fill="both", expand=True, padx=20, pady=20)

        titulo = ctk.CTkLabel(
            contenido,
            text=APP_NAME,
            font=("Segoe UI", 26, "bold"),
            text_color="#f8fafc"
        )
        titulo.pack(anchor="w", padx=18, pady=(18, 4))

        version = ctk.CTkLabel(
            contenido,
            text=f"Versión: {APP_VERSION}",
            font=("Segoe UI", 13, "bold"),
            text_color="#93c5fd"
        )
        version.pack(anchor="w", padx=18, pady=(0, 12))

        descripcion = ctk.CTkLabel(
            contenido,
            text="Herramienta para control, validación y seguimiento de liquidaciones, documentos y controles asociados.",
            font=("Segoe UI", 12),
            text_color="#dbeafe",
            justify="left",
            wraplength=400,
        )
        descripcion.pack(anchor="w", padx=18, pady=(0, 14))

        datos = [
            f"Fecha de versión: {APP_VERSION_DATE}",
            f"Estado del sistema: {('OK' if not self.diagnostico.get('faltantes') else 'Requiere revisión')}",
            f"Módulos cargados: {len(self.frames)}",
            f"Ruta de datos: {APP_DATA_PATH}",
        ]

        for linea in datos:
            ctk.CTkLabel(
                contenido,
                text=linea,
                font=("Segoe UI", 11),
                text_color="#cbd5e1",
                justify="left",
                wraplength=390,
            ).pack(anchor="w", padx=18, pady=2)

        btn_cerrar = ctk.CTkButton(
            contenido,
            text="Cerrar",
            command=ventana.destroy,
            width=140,
            height=38,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        btn_cerrar.pack(anchor="e", padx=18, pady=(18, 18))

    def mostrar_pantalla(self, nombre):
        for key, frame in self.frames.items():
            if key == nombre:
                frame.pack(fill="both", expand=True)
                frame.tkraise()
            else:
                frame.pack_forget()

        if nombre == "metricas" and hasattr(self.frames["metricas"], "actualizar_metricas"):
            self.frames["metricas"].actualizar_metricas()

        if nombre == "busqueda" and hasattr(self.frames["busqueda"], "actualizar_resultados"):
            self.frames["busqueda"].actualizar_resultados()

        if nombre == "visualizacion" and self.df_procesado is not None:
            self.frames["visualizacion"].cargar_dataframe(self.df_procesado)

        if nombre == "limpieza" and self.df_procesado is not None:
            self.frames["limpieza"].cargar_documentos(self.df_procesado)

    def mostrar_pantalla_carga(self):
        self.mostrar_pantalla("carga")

    def mostrar_pantalla_metrica(self):
        self.mostrar_pantalla("metricas")

    def mostrar_pantalla_busqueda(self):
        self.mostrar_pantalla("busqueda")

    def mostrar_pantalla_visualizacion(self):
        if self.df_procesado is not None:
            self.frames["visualizacion"].cargar_dataframe(self.df_procesado)
        self.mostrar_pantalla("visualizacion")

    def mostrar_pantalla_limpieza(self):
        if self.df_procesado is not None:
            self.frames["limpieza"].cargar_documentos(self.df_procesado)
        self.mostrar_pantalla("limpieza")

    def cerrar_aplicacion(self):
        self.destroy()


app = App()
app.mainloop()