"""Ventana «Carpeta de datos»: elegir la carpeta compartida entre PCs y traer los históricos de la macro."""

import json
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui import tema as T
from services.auditoria import (
    APP_CONFIG_PATH,
    APP_DATA_COMPARTIDA,
    APP_DATA_PATH,
    APP_ROOT,
    carpeta_datos_disponible,
    guardar_carpeta_datos,
)

ARCHIVOS_CLAVE = (
    ("Historico_Documentos_Controlados.xlsx", "Histórico de controlados"),
    ("historico_pagados.xlsx", "Histórico de pagados"),
    ("Netting_Propuestos.xlsx", "Registro de Netting"),
)


def reubicar_rutas_guardadas(vieja, nueva, carpeta_config=APP_CONFIG_PATH):
    """Las rutas recordadas por Netting y Liberación que apuntaban a la carpeta vieja pasan a la nueva."""
    vieja, nueva = Path(vieja).resolve(), Path(nueva)
    for nombre in ("netting.json", "liberacion.json"):
        ruta = Path(carpeta_config) / nombre
        try:
            config = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rutas = config.get("rutas") or {}
        for clave, valor in list(rutas.items()):
            if not valor:
                continue
            actual = Path(valor)
            try:
                if actual.resolve() == vieja:
                    rutas[clave] = str(nueva)
                elif actual.parent.resolve() == vieja:
                    rutas[clave] = str(nueva / actual.name)
            except OSError:
                continue
        ruta.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _boton(master, texto, comando, primario=False, ancho=180):
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho, height=34, corner_radius=T.RADIO_BOTON, font=T.ETIQUETA,
        fg_color=T.PRIMARIO if primario else T.SECUNDARIO, hover_color=T.PRIMARIO_HOVER if primario else T.SECUNDARIO_HOVER,
        text_color=T.TEXTO_SOBRE_COLOR if primario else T.TEXTO_SOBRE_SECUNDARIO,
    )


class VentanaCarpetaDatos(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Carpeta de datos")
        self.configure(fg_color=T.FONDO)
        self.transient(master)
        self.resizable(False, False)
        self._migraciones = {}
        self._crear()
        self.update_idletasks()
        ancho, alto = 720, self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - ancho) // 2
        y = master.winfo_rooty() + max(0, (master.winfo_height() - alto) // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{max(0, y)}")
        self.after(100, self.grab_set)

    def _crear(self):
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(cuerpo, text="Carpeta de datos", font=T.TITULO_PANTALLA, text_color=T.TEXTO).pack(anchor="w")
        ctk.CTkLabel(
            cuerpo, wraplength=660, justify="left", font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO,
            text=("Si dos personas usan la app en PCs distintas (por ejemplo, una controla y libera y otra hace el "
                  "netting), las dos tienen que usar la misma carpeta de datos en la red. Así comparten el Histórico "
                  "de controlados, el de pagados y el registro de Netting."),
        ).pack(anchor="w", pady=(2, 12))

        # --- Carpeta actual
        panel = ctk.CTkFrame(cuerpo, fg_color=T.SUPERFICIE, corner_radius=14, border_width=1, border_color=T.BORDE)
        panel.pack(fill="x")
        disponible = carpeta_datos_disponible(APP_DATA_PATH)
        tipo = "Compartida" if APP_DATA_COMPARTIDA else "Local (al lado del .exe)"
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(fila, text=f"  {tipo}  ", font=T.ETIQUETA_CHICA, corner_radius=8,
                     text_color=T.INFO if APP_DATA_COMPARTIDA else T.TEXTO_SECUNDARIO,
                     fg_color=T.INFO_FONDO if APP_DATA_COMPARTIDA else T.SUPERFICIE_ELEVADA).pack(side="left")
        ctk.CTkLabel(fila, text="  ✓ Disponible  " if disponible else "  ✗ No se puede acceder  ",
                     font=T.ETIQUETA_CHICA, corner_radius=8, text_color=T.OK if disponible else T.ERROR,
                     fg_color=T.OK_FONDO if disponible else T.ERROR_FONDO).pack(side="left", padx=8)
        ctk.CTkLabel(panel, text=str(APP_DATA_PATH), font=T.ETIQUETA, text_color=T.TEXTO, anchor="w",
                     wraplength=660, justify="left").pack(fill="x", padx=16, pady=(8, 2))
        estado = []
        for archivo, nombre in ARCHIVOS_CLAVE:
            existe = disponible and (Path(APP_DATA_PATH) / archivo).exists()
            estado.append(f"{'✓' if existe else '—'} {nombre}")
        ctk.CTkLabel(panel, text="    ".join(estado), font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO,
                     anchor="w").pack(fill="x", padx=16)
        botones = ctk.CTkFrame(panel, fg_color="transparent")
        botones.pack(fill="x", padx=16, pady=12)
        _boton(botones, "Usar una carpeta compartida…", self.elegir_compartida, primario=True, ancho=230).pack(side="left")
        if APP_DATA_COMPARTIDA:
            _boton(botones, "Volver a la carpeta local", self.volver_a_local, ancho=200).pack(side="left", padx=8)

        # --- Migración
        migrar = ctk.CTkFrame(cuerpo, fg_color=T.SUPERFICIE, corner_radius=14, border_width=1, border_color=T.BORDE)
        migrar.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(migrar, text="Traer los históricos de la macro (.xlsb)", font=T.SUBTITULO,
                     text_color=T.TEXTO).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(
            migrar, wraplength=660, justify="left", font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO,
            text=("Se hace una sola vez, el día que dejan de usar la macro. Convierte cada histórico a .xlsx dentro de "
                  "la carpeta de datos de arriba y verifica que no falte ninguna fila. Si ya había uno, guarda una copia."),
        ).pack(anchor="w", padx=16, pady=(2, 8))
        self.lbl_migracion = {}
        for tipo_hist, titulo in (("controlados", "Histórico de controlados"), ("pagados", "Histórico de pagados")):
            fila = ctk.CTkFrame(migrar, fg_color="transparent")
            fila.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(fila, text=titulo, font=T.ETIQUETA, text_color=T.TEXTO, width=180, anchor="w").pack(side="left")
            etiqueta = ctk.CTkLabel(fila, text="Sin elegir", font=T.CUERPO_CHICO, text_color=T.TEXTO_TENUE, anchor="w",
                                    width=330)
            etiqueta.pack(side="left", padx=8)
            _boton(fila, "Elegir .xlsb…", lambda t=tipo_hist: self.elegir_xlsb(t), ancho=120).pack(side="right")
            self.lbl_migracion[tipo_hist] = etiqueta
        acciones = ctk.CTkFrame(migrar, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(8, 4))
        self.btn_revisar = _boton(acciones, "Revisar", lambda: self.migrar(simular=True), ancho=120)
        self.btn_revisar.pack(side="left")
        self.btn_migrar = _boton(acciones, "Convertir y guardar", lambda: self.migrar(simular=False), primario=True)
        self.btn_migrar.pack(side="left", padx=8)
        self.informe = ctk.CTkTextbox(migrar, height=150, wrap="word", fg_color=T.SUPERFICIE_HUNDIDA,
                                      text_color=T.TEXTO_SUAVE, font=T.CUERPO_CHICO)
        self.informe.pack(fill="x", padx=16, pady=(4, 14))
        self.informe.insert("end", "Elegí los .xlsb y tocá «Revisar» para ver qué se va a convertir.")
        self.informe.configure(state="disabled")

        _boton(cuerpo, "Cerrar", self.destroy, ancho=120).pack(anchor="e", pady=(14, 0))

    # ------------------------------------------------------------------ carpeta
    def elegir_compartida(self):
        carpeta = filedialog.askdirectory(parent=self, title="Carpeta de datos compartida (en la red)")
        if not carpeta:
            return
        carpeta = Path(carpeta)
        if not carpeta_datos_disponible(carpeta):
            messagebox.showerror("Carpeta de datos", f"No se puede escribir en {carpeta}.\n\nRevisá la conexión y los "
                                                     "permisos de la carpeta.", parent=self)
            return
        encontrados = [nombre for archivo, nombre in ARCHIVOS_CLAVE if (carpeta / archivo).exists()]
        detalle = ("Ya tiene: " + ", ".join(encontrados) + ".") if encontrados else \
            "Está vacía de históricos: después traé los de la macro con la sección de abajo."
        if not messagebox.askyesno(
                "Usar carpeta compartida",
                f"La app va a leer y guardar todo en:\n{carpeta}\n\n{detalle}\n\nLos archivos de la carpeta actual no se "
                "mueven ni se borran. La app se va a cerrar para aplicar el cambio. ¿Seguir?", parent=self):
            return
        self._aplicar(carpeta)

    def volver_a_local(self):
        if not messagebox.askyesno(
                "Carpeta local", "La app va a volver a usar la carpeta data que está al lado del .exe (no compartida). "
                                 "La app se va a cerrar para aplicar el cambio. ¿Seguir?", parent=self):
            return
        self._aplicar(None)

    def _aplicar(self, carpeta):
        nueva = carpeta or Path(APP_ROOT) / "data"
        guardar_carpeta_datos(carpeta)
        try:
            reubicar_rutas_guardadas(APP_DATA_PATH, nueva)
        except OSError:
            pass
        messagebox.showinfo("Carpeta de datos", "Listo. Abrí la app de nuevo para empezar a usar la carpeta nueva.",
                            parent=self)
        self.master_app.destroy()

    # ------------------------------------------------------------------ migración
    def elegir_xlsb(self, tipo):
        ruta = filedialog.askopenfilename(parent=self, title="Histórico de la macro",
                                          filetypes=[("Excel binario", "*.xlsb"), ("Excel", "*.xlsx *.xlsm")])
        if ruta:
            self._migraciones[tipo] = ruta
            self.lbl_migracion[tipo].configure(text=Path(ruta).name, text_color=T.OK)

    def _mostrar(self, texto):
        self.informe.configure(state="normal")
        self.informe.delete("1.0", "end")
        self.informe.insert("end", texto)
        self.informe.configure(state="disabled")

    def migrar(self, simular):
        if not self._migraciones:
            messagebox.showwarning("Históricos de la macro", "Elegí al menos un .xlsb.", parent=self)
            return
        if not carpeta_datos_disponible(APP_DATA_PATH):
            messagebox.showerror("Históricos de la macro", f"No se puede acceder a {APP_DATA_PATH}.", parent=self)
            return
        if not simular and not messagebox.askyesno(
                "Convertir históricos", f"Se van a guardar los históricos convertidos en:\n{APP_DATA_PATH}\n\n"
                                        "Si ya existen, antes se guarda una copia. ¿Seguir?", parent=self):
            return
        self.btn_revisar.configure(state="disabled")
        self.btn_migrar.configure(state="disabled")
        self._mostrar("Leyendo… (un histórico grande puede tardar un par de minutos)")
        trabajos = dict(self._migraciones)

        def tarea():
            from services import migracion
            from services.bloqueo import uso_exclusivo

            partes = []
            for tipo, ruta in trabajos.items():
                try:
                    if simular:
                        informe, _t, _f = migracion.preparar(ruta, tipo)
                    else:
                        with uso_exclusivo("trayendo los históricos de la macro", APP_DATA_PATH):
                            informe = migracion.migrar(ruta, tipo, APP_DATA_PATH)
                    partes.append(informe.texto())
                except Exception as exc:
                    partes.append(f"{Path(ruta).name}: ERROR - {exc}")
            self.after(0, lambda: self._terminar("\n\n".join(partes)))

        threading.Thread(target=tarea, daemon=True).start()

    def _terminar(self, texto):
        self._mostrar(texto)
        self.btn_revisar.configure(state="normal")
        self.btn_migrar.configure(state="normal")


def revisar_carpeta_al_iniciar(app):
    """Si la carpeta compartida no está disponible (sin red o sin VPN), se avisa antes de trabajar."""
    if not APP_DATA_COMPARTIDA or carpeta_datos_disponible(APP_DATA_PATH):
        return
    ventana = ctk.CTkToplevel(app)
    ventana.title("Carpeta de datos no disponible")
    ventana.configure(fg_color=T.FONDO)
    ventana.transient(app)
    cuerpo = ctk.CTkFrame(ventana, fg_color="transparent")
    cuerpo.pack(fill="both", expand=True, padx=24, pady=20)
    ctk.CTkLabel(cuerpo, text="No se puede acceder a la carpeta de datos", font=T.SUBTITULO, text_color=T.ERROR).pack(anchor="w")
    ctk.CTkLabel(cuerpo, text=str(APP_DATA_PATH), font=T.ETIQUETA, text_color=T.TEXTO, wraplength=520,
                 justify="left").pack(anchor="w", pady=(6, 4))
    ctk.CTkLabel(
        cuerpo, wraplength=520, justify="left", font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO,
        text="Revisá que estés conectado a la red de la empresa (o a la VPN) y que el disco esté disponible. "
             "Hasta que se pueda acceder, la app no va a encontrar los históricos ni los reportes.",
    ).pack(anchor="w")
    estado = ctk.CTkLabel(cuerpo, text="", font=T.CUERPO_CHICO, text_color=T.AVISO)
    estado.pack(anchor="w", pady=(6, 0))
    botones = ctk.CTkFrame(cuerpo, fg_color="transparent")
    botones.pack(fill="x", pady=(14, 0))

    def reintentar():
        if carpeta_datos_disponible(APP_DATA_PATH):
            ventana.destroy()
        else:
            estado.configure(text="Todavía no se puede acceder.")

    def cambiar():
        ventana.destroy()
        VentanaCarpetaDatos(app)

    _boton(botones, "Reintentar", reintentar, primario=True, ancho=130).pack(side="left")
    _boton(botones, "Cambiar carpeta…", cambiar, ancho=150).pack(side="left", padx=8)
    _boton(botones, "Salir", app.destroy, ancho=100).pack(side="right")
    ventana.update_idletasks()
    ventana.geometry(f"580x{ventana.winfo_reqheight()}+{app.winfo_rootx() + 200}+{app.winfo_rooty() + 150}")
    ventana.after(100, ventana.grab_set)
