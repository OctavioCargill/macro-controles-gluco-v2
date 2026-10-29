"""Menú principal de la aplicación, barra de navegación y módulos en desarrollo."""

import customtkinter as ctk

from gui import tema as T
from gui.pantalla_inicio import TarjetaPaso
from services.auditoria import APP_LOGO_PATH, APP_NAME, APP_VERSION


class MenuPrincipal(ctk.CTkFrame):
    """Inicio de la app: los tres módulos del proceso de Glucovil."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.pack(fill="both", expand=True, padx=30, pady=30)

        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=40, pady=(10, 0))

        # --- Cabecera: nombre de la app a la izquierda, versión (info) a la derecha
        cabecera = ctk.CTkFrame(contenido, fg_color="transparent")
        cabecera.pack(fill="x")
        if APP_LOGO_PATH.exists():
            try:
                from PIL import Image

                self._logo = ctk.CTkImage(light_image=Image.open(APP_LOGO_PATH), size=(64, 64))
                ctk.CTkLabel(cabecera, image=self._logo, text="").pack(side="left", padx=(0, 16))
            except Exception:
                pass
        textos = ctk.CTkFrame(cabecera, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        ctk.CTkLabel(textos, text=APP_NAME, font=(T.FUENTE, 30, "bold"), text_color=T.TEXTO).pack(anchor="w")
        ctk.CTkLabel(
            textos, text="Proceso de liquidaciones de Glucovil", font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            cabecera,
            text=f"ⓘ  Versión {APP_VERSION}",
            command=self.master.mostrar_acerca_de,
            width=150,
            height=34,
            corner_radius=T.RADIO_BOTON,
            fg_color="transparent",
            hover_color=T.SUPERFICIE_ELEVADA,
            border_width=1,
            border_color=T.BORDE,
            text_color=T.TEXTO_SECUNDARIO,
            font=T.ETIQUETA_CHICA,
        ).pack(side="right", anchor="n", pady=(4, 0))

        # --- Módulos
        ctk.CTkLabel(contenido, text="Módulos", font=T.SUBTITULO, text_color=T.TEXTO).pack(anchor="w", pady=(36, 12))
        modulos = ctk.CTkFrame(contenido, fg_color="transparent")
        modulos.pack(fill="x")
        for columna in range(3):
            modulos.grid_columnconfigure(columna, weight=1, uniform="modulos")

        self.modulo_controlar = TarjetaPaso(
            modulos, 1, "Controlar", lambda: self.master.mostrar_pantalla("controlar"), etiqueta="Etapa 1"
        )
        self.modulo_netting = TarjetaPaso(
            modulos, 2, "Netting", lambda: self.master.mostrar_pantalla("netting"), etiqueta="Etapa 2"
        )
        self.modulo_liberacion = TarjetaPaso(
            modulos, 3, "Liberación", lambda: self.master.mostrar_pantalla("liberacion"), etiqueta="Etapa 3"
        )
        for columna, tarjeta in enumerate((self.modulo_controlar, self.modulo_netting, self.modulo_liberacion)):
            tarjeta.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 8, 0 if columna == 2 else 8))

        self.modulo_liberacion.mostrar("pronto", "Liberación de liquidaciones.", "En desarrollo")

        # --- Pie: salir
        pie = ctk.CTkFrame(contenido, fg_color="transparent")
        pie.pack(side="bottom", fill="x", pady=(0, 10))
        ctk.CTkFrame(contenido, fg_color=T.BORDE, height=1, corner_radius=0).pack(side="bottom", fill="x", pady=(0, 16))
        ctk.CTkButton(
            pie,
            text="Salir",
            command=self.master.cerrar_aplicacion,
            width=130,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.SECUNDARIO, text_color=T.TEXTO_SOBRE_SECUNDARIO,
            hover_color=T.SECUNDARIO_HOVER,
            font=T.BOTON,
        ).pack(side="right")

        self.actualizar_estado()

    def actualizar_estado(self):
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            self.modulo_netting.mostrar(
                "disponible", "Propuestas de 24 y 48 hs: lo que se paga y lo que se descuenta por beneficiario.", "Abrir →"
            )
        else:
            e = resultado.estadisticas
            self.modulo_netting.mostrar(
                "siguiente",
                f"Armadas a las {resultado.generado:%H:%M}: {e['propuestas_24']} de 24 hs y {e['propuestas_48']} de 48 hs.",
                "Continuar →",
            )

        df = getattr(self.master, "df_procesado", None)
        if df is None:
            self.modulo_controlar.mostrar(
                "siguiente", "Carga de reportes SAP, revisión de liquidaciones y limpieza de controladas.", "Abrir →"
            )
            return
        documentos = df["Numero Doc"].nunique() if "Numero Doc" in df.columns else len(df)
        controlados = 0
        if "CONTROLADO" in df.columns and "Numero Doc" in df.columns:
            controlados = df.loc[df["CONTROLADO"].fillna(False).astype(bool), "Numero Doc"].nunique()
        hora = str(getattr(self.master, "ultima_ejecucion", ""))[-8:-3]
        self.modulo_controlar.mostrar(
            "siguiente",
            f"Procesado a las {hora}: {documentos} documentos, {controlados} marcados como controlados.",
            "Continuar →",
        )


class PantallaEnDesarrollo(ctk.CTkFrame):
    """Lugar reservado para los módulos que todavía no están implementados."""

    def __init__(self, master, titulo):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.42, anchor="center")
        ctk.CTkLabel(centro, text=titulo, font=(T.FUENTE, 26, "bold"), text_color=T.TEXTO).pack()
        ctk.CTkLabel(
            centro,
            text="  En desarrollo  ",
            font=T.ETIQUETA_CHICA,
            text_color=T.AVISO,
            fg_color=T.AVISO_FONDO,
            corner_radius=8,
        ).pack(pady=(8, 10))
        ctk.CTkLabel(
            centro,
            text="Este módulo todavía no está disponible en esta versión de la aplicación.",
            font=T.CUERPO,
            text_color=T.TEXTO_SECUNDARIO,
        ).pack(pady=(0, 20))
        ctk.CTkButton(
            centro,
            text="Volver al menú principal",
            command=lambda: self.master.ir_a("inicio"),
            width=220,
            height=T.ALTO_BOTON,
            corner_radius=T.RADIO_BOTON,
            fg_color=T.SECUNDARIO, text_color=T.TEXTO_SOBRE_SECUNDARIO,
            hover_color=T.SECUNDARIO_HOVER,
            font=T.BOTON,
        ).pack()


class BarraNavegacion(ctk.CTkFrame):
    """Barra superior: botón Volver (pantalla anterior) y ruta clickeable hasta el menú principal."""

    def __init__(self, master):
        super().__init__(master, fg_color=T.FONDO, corner_radius=0, height=52)
        self.master = master
        self.pack_propagate(False)

        self.btn_volver = ctk.CTkButton(
            self,
            text="←  Volver",
            command=self.master.volver,
            width=104,
            height=32,
            corner_radius=T.RADIO_BOTON,
            fg_color="transparent",
            hover_color=T.SUPERFICIE_ELEVADA,
            border_width=1,
            border_color=T.BORDE,
            text_color=T.TEXTO_SECUNDARIO,
            font=T.ETIQUETA_CHICA,
        )
        self.btn_volver.pack(side="left", padx=(30, 16), pady=(14, 0))

        self.ruta = ctk.CTkFrame(self, fg_color="transparent")
        self.ruta.pack(side="left", pady=(14, 0))
        self._bloqueada = False

    def mostrar_ruta(self, pasos):
        """pasos: lista de (clave, título) desde el menú principal hasta la pantalla actual."""
        for widget in self.ruta.winfo_children():
            widget.destroy()
        for indice, (clave, titulo) in enumerate(pasos):
            es_actual = indice == len(pasos) - 1
            if indice:
                ctk.CTkLabel(self.ruta, text="›", font=T.CUERPO, text_color=T.TEXTO_TENUE).pack(side="left", padx=8)
            etiqueta = ctk.CTkLabel(
                self.ruta,
                text=titulo,
                font=T.ETIQUETA_CHICA if es_actual else T.CUERPO_CHICO,
                text_color=T.TEXTO if es_actual else T.ENLACE,
            )
            etiqueta.pack(side="left")
            if not es_actual:
                etiqueta.configure(cursor="hand2")
                etiqueta.bind("<Button-1>", lambda _event, destino=clave: self.master.ir_a(destino))
                etiqueta.bind("<Enter>", lambda _event, e=etiqueta: e.configure(text_color=T.TEXTO))
                etiqueta.bind("<Leave>", lambda _event, e=etiqueta: e.configure(text_color=T.ENLACE))

    def bloquear(self, bloquear):
        self._bloqueada = bloquear
        self.btn_volver.configure(state="disabled" if bloquear else "normal")
