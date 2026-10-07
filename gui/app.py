import customtkinter as ctk
from .pantalla_inicio import PantallaInicio

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()

app.title("Controles Gluco V2")
app.geometry("1200x800")

PantallaInicio(app)

app.mainloop()