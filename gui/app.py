import customtkinter as ctk

from .pantalla_inicio import (
    MenuPrincipal,
    PantallaCargaDatos,
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

        self.df_procesado = None
        self.resumen = {}

        self.frames = {
            "menu": MenuPrincipal(self),
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

        if nombre == "visualizacion" and self.df_procesado is not None:
            self.frames["visualizacion"].cargar_dataframe(self.df_procesado)

        if nombre == "limpieza" and self.df_procesado is not None:
            self.frames["limpieza"].cargar_documentos(self.df_procesado)

    def mostrar_pantalla_carga(self):
        self.mostrar_pantalla("carga")

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