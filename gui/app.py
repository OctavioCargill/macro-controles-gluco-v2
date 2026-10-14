from datetime import datetime

import customtkinter as ctk

from services.auditoria import APP_VERSION, construir_diagnostico

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

        self.title("Controles Gluco V2")
        self.geometry("1200x800")
        self.minsize(1100, 700)

        self.version = APP_VERSION
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

        for nombre, frame in self.frames.items():
            frame.pack_forget()

        self.mostrar_pantalla("menu")

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