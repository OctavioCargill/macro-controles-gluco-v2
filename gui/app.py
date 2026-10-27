import os
import sys
from datetime import datetime
from pathlib import Path

from services.auditoria import resolver_ruta_base

ROOT_DIR = resolver_ruta_base()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import customtkinter as ctk

from gui import tema as T

from services.auditoria import (
    APP_DATA_PATH,
    APP_ICON_PATH,
    APP_NAME,
    APP_VERSION,
    APP_VERSION_DATE,
    asegurar_estructura_runtime,
    construir_diagnostico,
    evaluar_integridad_liquidaciones,
)

from gui.pantalla_principal import BarraNavegacion, MenuPrincipal, PantallaEnDesarrollo
from gui.pantalla_inicio import (
    MenuControlar,
    PantallaBusqueda,
    PantallaCargaDatos,
    PantallaMetricas,
    PantallaVisualizacion,
    PantallaLimpieza,
)

# Jerarquía de pantallas: de quién cuelga cada una y cómo se llama en la ruta de navegación.
PANTALLA_PADRE = {
    "inicio": None,
    "controlar": "inicio",
    "netting": "inicio",
    "liberacion": "inicio",
    "carga": "controlar",
    "visualizacion": "controlar",
    "limpieza": "controlar",
    "busqueda": "controlar",
    "metricas": "controlar",
}
TITULO_PANTALLA = {
    "inicio": "Menú principal",
    "controlar": "Controlar",
    "netting": "Netting",
    "liberacion": "Liberación",
    "carga": "Carga de datos",
    "visualizacion": "Visualizar liquidaciones",
    "limpieza": "Limpieza de controladas",
    "busqueda": "Buscador global",
    "metricas": "Métricas generales",
}

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.configure(fg_color=T.FONDO)
        self.geometry("1200x800")
        self.minsize(1100, 700)

        asegurar_estructura_runtime()
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
            "historizadas": 0,
            "descartadas": 0,
            "descartes": [],
            "estado": "REQUIERE_REVISION",
            "lista_para_produccion": False,
        }

        self._historial = []
        self._pantalla_actual = None
        self._navegacion_bloqueada = False

        self.frames = {
            "inicio": MenuPrincipal(self),
            "controlar": MenuControlar(self),
            "netting": PantallaEnDesarrollo(self, "Netting"),
            "liberacion": PantallaEnDesarrollo(self, "Liberación"),
            "metricas": PantallaMetricas(self),
            "busqueda": PantallaBusqueda(self),
            "carga": PantallaCargaDatos(self),
            "visualizacion": PantallaVisualizacion(self),
            "limpieza": PantallaLimpieza(self),
        }

        self.footer = ctk.CTkLabel(
            self,
            text=f"{APP_NAME} • Versión {APP_VERSION}",
            font=(T.FUENTE, 10, "bold"),
            text_color=T.TEXTO_TENUE,
            fg_color=T.SUPERFICIE_HUNDIDA,
            corner_radius=0,
        )
        self.footer.pack(side="bottom", fill="x")

        for nombre, frame in self.frames.items():
            frame.pack_forget()

        self.barra_navegacion = BarraNavegacion(self)
        self.bind("<Alt-Left>", lambda _event: self.volver())

        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)
        self.mostrar_pantalla("inicio")

    def _configurar_icono(self):
        if not self.icon_path or not self.icon_path.exists():
            return
        try:
            self.iconbitmap(str(self.icon_path))
            self.wm_iconbitmap(str(self.icon_path))
        except Exception:
            pass

    def mostrar_acerca_de(self):
        # Si ya está abierta, se trae al frente en lugar de abrir otra.
        existente = getattr(self, "_ventana_acerca_de", None)
        if existente is not None and existente.winfo_exists():
            existente.lift()
            existente.focus_force()
            return

        ventana = ctk.CTkToplevel(self)
        self._ventana_acerca_de = ventana
        ventana.title(f"Acerca de {APP_NAME}")
        ventana.configure(fg_color=T.FONDO)
        ventana.resizable(False, False)
        ventana.transient(self)
        ventana.grab_set()
        ventana.bind("<Escape>", lambda _event: ventana.destroy())

        if self.icon_path and self.icon_path.exists():
            try:
                ventana.iconbitmap(str(self.icon_path))
            except Exception:
                pass

        cuerpo = ctk.CTkFrame(ventana, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=28, pady=24)

        # --- Encabezado
        ctk.CTkLabel(
            cuerpo, text="CONTROL · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA
        ).pack(anchor="w")
        ctk.CTkLabel(
            cuerpo, text=APP_NAME, font=T.TITULO_PANTALLA, text_color=T.TEXTO
        ).pack(anchor="w", pady=(2, 8))
        ctk.CTkLabel(
            cuerpo,
            text=f"  Versión {APP_VERSION}  ·  {self._fecha_legible(APP_VERSION_DATE)}  ",
            font=T.ETIQUETA_CHICA,
            text_color=T.INFO,
            fg_color=T.INFO_FONDO,
            corner_radius=8,
        ).pack(anchor="w")

        ctk.CTkLabel(
            cuerpo,
            text=(
                "Control, validación y seguimiento de liquidaciones de granos de Glucovil: "
                "procesa los reportes SAP 044, 090 y 077, clasifica los documentos y "
                "mantiene el histórico de los ya controlados."
            ),
            font=T.CUERPO,
            text_color=T.TEXTO_SECUNDARIO,
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(16, 18))

        # --- Estado del sistema
        faltantes = self.diagnostico.get("faltantes") or []
        estado_ok = not faltantes
        panel_estado = ctk.CTkFrame(
            cuerpo,
            fg_color=T.OK_FONDO if estado_ok else T.AVISO_FONDO,
            corner_radius=12,
        )
        panel_estado.pack(fill="x")
        ctk.CTkLabel(
            panel_estado,
            text="●  Sistema listo para procesar" if estado_ok else "●  Faltan recursos para procesar",
            font=T.ETIQUETA,
            text_color=T.OK if estado_ok else T.AVISO,
        ).pack(anchor="w", padx=14, pady=(10, 2 if faltantes else 10))
        for recurso in faltantes:
            ctk.CTkLabel(
                panel_estado,
                text=f"Falta: {recurso.get('nombre', '')}",
                font=T.CUERPO_CHICO,
                text_color=T.TEXTO_SUAVE,
                justify="left",
                wraplength=420,
            ).pack(anchor="w", padx=30, pady=(0, 2))
        if faltantes:
            ctk.CTkFrame(panel_estado, fg_color="transparent", height=8).pack()

        # --- Datos
        datos = ctk.CTkFrame(cuerpo, fg_color=T.SUPERFICIE, corner_radius=12, border_width=1, border_color=T.BORDE)
        datos.pack(fill="x", pady=(12, 0))
        datos.grid_columnconfigure(1, weight=1)

        if self.df_procesado is not None:
            ultimo = self.ultima_ejecucion
        else:
            ultimo = "Sin procesar en esta sesión"

        filas = [
            ("Último procesamiento", ultimo),
            ("Carpeta de datos", str(APP_DATA_PATH)),
        ]
        for fila, (clave, valor) in enumerate(filas):
            ctk.CTkLabel(
                datos, text=clave, font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE
            ).grid(row=fila, column=0, sticky="nw", padx=(14, 12), pady=(10 if fila == 0 else 4, 4))
            ctk.CTkLabel(
                datos, text=valor, font=T.CUERPO_CHICO, text_color=T.TEXTO_SUAVE,
                justify="left", wraplength=290, anchor="w",
            ).grid(row=fila, column=1, sticky="nw", padx=(0, 14), pady=(10 if fila == 0 else 4, 4))

        acciones_ruta = ctk.CTkFrame(datos, fg_color="transparent")
        acciones_ruta.grid(row=len(filas), column=1, sticky="w", pady=(2, 12))

        aviso_copia = ctk.CTkLabel(acciones_ruta, text="", font=T.NOTA, text_color=T.OK)

        def copiar_ruta():
            self.clipboard_clear()
            self.clipboard_append(str(APP_DATA_PATH))
            aviso_copia.configure(text="Ruta copiada")
            ventana.after(2000, lambda: aviso_copia.winfo_exists() and aviso_copia.configure(text=""))

        estilo_chico = dict(height=30, corner_radius=T.RADIO_BOTON, font=T.ETIQUETA_CHICA,
                            fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER,
                            text_color=T.TEXTO_SOBRE_SECUNDARIO)
        if hasattr(os, "startfile"):
            ctk.CTkButton(
                acciones_ruta, text="Abrir carpeta", width=110,
                command=lambda: os.startfile(str(APP_DATA_PATH)), **estilo_chico
            ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            acciones_ruta, text="Copiar ruta", width=100, command=copiar_ruta, **estilo_chico
        ).pack(side="left")
        aviso_copia.pack(side="left", padx=10)

        # --- Pie
        ctk.CTkButton(
            cuerpo,
            text="Cerrar",
            command=ventana.destroy,
            width=130,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.PRIMARIO,
            hover_color=T.PRIMARIO_HOVER,
            font=T.BOTON,
        ).pack(anchor="e", pady=(20, 0))

        # Centrar sobre la ventana principal.
        ventana.update_idletasks()
        ancho, alto = 520, ventana.winfo_reqheight()
        x = self.winfo_rootx() + (self.winfo_width() - ancho) // 2
        y = self.winfo_rooty() + max(0, (self.winfo_height() - alto) // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

    @staticmethod
    def _fecha_legible(fecha_iso):
        try:
            return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return str(fecha_iso)

    # ------------------------------------------------------------------ navegación
    def _ruta(self, nombre):
        ruta = []
        while nombre:
            ruta.insert(0, nombre)
            nombre = PANTALLA_PADRE.get(nombre)
        return ruta

    def mostrar_pantalla(self, nombre, registrar=True):
        if self._navegacion_bloqueada and nombre != self._pantalla_actual:
            return
        actual = self._pantalla_actual
        if registrar and actual and actual != nombre:
            if nombre in self._ruta(actual):
                # Ir a una pantalla "de arriba" (p. ej. de Carga a Controlar) reinicia el historial,
                # así Volver no rebota entre las mismas dos pantallas.
                self._historial = self._ruta(nombre)[:-1]
            else:
                self._historial.append(actual)
        self._pantalla_actual = nombre
        self._mostrar(nombre)

    def volver(self):
        """Vuelve a la pantalla anterior; si no hay historial, a la pantalla de la que cuelga."""
        if self._navegacion_bloqueada:
            return
        destino = self._historial.pop() if self._historial else PANTALLA_PADRE.get(self._pantalla_actual)
        if destino:
            self._pantalla_actual = destino
            self._mostrar(destino)

    def ir_a(self, nombre):
        """Salto directo desde la ruta de navegación (por ejemplo, al menú principal)."""
        if self._navegacion_bloqueada:
            return
        self._historial = self._ruta(nombre)[:-1]
        self._pantalla_actual = nombre
        self._mostrar(nombre)

    def bloquear_navegacion(self, bloquear):
        self._navegacion_bloqueada = bloquear
        self.barra_navegacion.bloquear(bloquear)

    def _mostrar(self, nombre):
        for menu in ("inicio", "controlar"):
            if nombre == menu:
                self.frames[menu].actualizar_estado()

        for clave in ("visualizacion", "limpieza"):
            if nombre == clave:
                self.frames[clave].mostrar_vacio(self.df_procesado is None)

        for key, frame in self.frames.items():
            if key != nombre:
                frame.pack_forget()

        if nombre == "inicio":
            self.barra_navegacion.pack_forget()
        else:
            self.barra_navegacion.mostrar_ruta([(clave, TITULO_PANTALLA[clave]) for clave in self._ruta(nombre)])
            self.barra_navegacion.pack(side="top", fill="x", before=self.footer)

        self.frames[nombre].pack(fill="both", expand=True)
        self.frames[nombre].tkraise()

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

    def ejecutar_prueba_integridad(self):
        """Ejecuta la validación del estado de integridad general de la app.
        El menú dispara este método, por lo que debe existir en App.
        """
        estado = self.integridad_procesamiento.copy()
        if not estado.get("lista_para_produccion"):
            from tkinter import messagebox
            messagebox.showwarning(
                "Pruebas de integridad",
                "El procesamiento actual requiere revisión antes de declararse listo para producción."
            )
        else:
            from tkinter import messagebox
            messagebox.showinfo(
                "Pruebas de integridad",
                f"Estado: {estado.get('estado', 'OK')}\n"
                f"Detectadas: {estado.get('encontradas', 0)}\n"
                f"Procesadas: {estado.get('procesadas', 0)}\n"
                f"Mostradas: {estado.get('mostradas', 0)}\n"
                f"Historizadas: {estado.get('historizadas', 0)}"
            )
        return estado

    def cerrar_aplicacion(self):
        pendientes = self._controlados_sin_historizar()
        if pendientes:
            from tkinter import messagebox
            salir = messagebox.askyesno(
                "Salir de la aplicación",
                f"Tenés {pendientes} documento(s) marcados como controlados que todavía no pasaste al histórico.\n\n"
                "Si salís ahora, esas marcas se pierden. ¿Querés salir igual?",
                icon="warning",
                default="no",
            )
            if not salir:
                self.mostrar_pantalla("limpieza")
                return
        self.destroy()

    def _controlados_sin_historizar(self):
        df = self.df_procesado
        if df is None or "CONTROLADO" not in df.columns:
            return 0
        marcados = df["CONTROLADO"].fillna(False).astype(bool)
        if "Numero Doc" in df.columns:
            return int(df.loc[marcados, "Numero Doc"].nunique())
        return int(marcados.sum())


if __name__ == "__main__":
    app = App()
    app.mainloop()