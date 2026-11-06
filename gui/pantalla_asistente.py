"""Asistente: guía de usuario con preguntas precargadas sobre Controlar, Netting y Liberación.

Funciona sin internet: busca la respuesta en asistente/contenido.py.
"""

import customtkinter as ctk

from asistente.buscador import UMBRAL_RESPUESTA, Buscador
from asistente.contenido import PROCESOS
from gui import tema as T

FILTROS = [("todos", "Todas")] + list(PROCESOS.items())
SUGERENCIAS_INICIO = {
    "todos": ["gen_orden", "ctl_macro_manual", "net_fecha", "lib_controles"],
    "general": ["gen_que_es", "gen_orden", "gen_archivos_data", "gen_prueba"],
    "controlar": ["ctl_cargar", "ctl_motivos", "ctl_marcar", "ctl_limpieza"],
    "netting": ["net_que_toma", "net_fecha", "net_sin_propuestas", "net_salida"],
    "liberacion": ["lib_que_hace", "lib_controles", "lib_manual", "lib_limpiar"],
}
COLOR_PROCESO = {
    "general": (T.TEXTO_SECUNDARIO, T.SUPERFICIE_ELEVADA),
    "controlar": (T.INFO, T.INFO_FONDO),
    "netting": (T.MARCA, T.AVISO_FONDO),
    "liberacion": (T.OK, T.OK_FONDO),
}


class PantallaAsistente(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.buscador = Buscador()
        self.filtro = "todos"
        self._ancho_texto = 560
        self._crear()
        self.reiniciar()

    # ------------------------------------------------------------------ interfaz
    def _crear(self):
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=20, pady=(6, 8))
        ctk.CTkLabel(cabecera, text="ASISTENTE · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        ctk.CTkLabel(cabecera, text="¿En qué te ayudo?", font=T.TITULO_PANTALLA, text_color=T.TEXTO).pack(anchor="w")
        ctk.CTkLabel(
            cabecera, text="Elegí una pregunta o escribí la tuya. Las respuestas están en la app: funciona sin internet.",
            font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO,
        ).pack(anchor="w")

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        cuerpo.grid_columnconfigure(0, weight=0, minsize=380)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        # --- Izquierda: filtros y preguntas
        izquierda = ctk.CTkFrame(cuerpo, fg_color=T.SUPERFICIE, corner_radius=T.RADIO_PANEL, border_width=1,
                                 border_color=T.BORDE, width=380)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        izquierda.grid_propagate(False)
        izquierda.grid_columnconfigure(0, weight=1)
        izquierda.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(izquierda, text="Preguntas frecuentes", font=T.SUBTITULO, text_color=T.TEXTO).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        filtros = ctk.CTkFrame(izquierda, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.botones_filtro = {}
        for indice, (clave, texto) in enumerate(FILTROS):
            boton = ctk.CTkButton(filtros, text=texto, height=28, width=10, corner_radius=14, font=T.ETIQUETA_CHICA,
                                  command=lambda c=clave: self.elegir_filtro(c))
            boton.grid(row=indice // 3, column=indice % 3, sticky="ew", padx=3, pady=3)
            self.botones_filtro[clave] = boton
        for columna in range(3):
            filtros.grid_columnconfigure(columna, weight=1)
        self.lista = ctk.CTkScrollableFrame(izquierda, fg_color="transparent")
        self.lista.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 10))

        # --- Derecha: conversación y caja de pregunta
        derecha = ctk.CTkFrame(cuerpo, fg_color=T.SUPERFICIE, corner_radius=T.RADIO_PANEL, border_width=1,
                               border_color=T.BORDE)
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.grid_columnconfigure(0, weight=1)
        derecha.grid_rowconfigure(0, weight=1)
        self.chat = ctk.CTkScrollableFrame(derecha, fg_color="transparent")
        self.chat.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        self.chat.bind("<Configure>", self._ajustar_ancho)

        entrada = ctk.CTkFrame(derecha, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=14)
        entrada.grid(row=1, column=0, sticky="ew", padx=14, pady=14)
        entrada.grid_columnconfigure(0, weight=1)
        self.ent_pregunta = ctk.CTkEntry(
            entrada, placeholder_text="Escribí tu pregunta. Ej.: ¿por qué un paquete queda en MANUAL?",
            height=40, border_width=0, fg_color=T.SUPERFICIE_HUNDIDA, font=T.CUERPO, text_color=T.TEXTO,
        )
        self.ent_pregunta.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=6)
        self.ent_pregunta.bind("<Return>", lambda _e: self.preguntar())
        ctk.CTkButton(entrada, text="Preguntar", width=110, height=36, corner_radius=T.RADIO_BOTON, font=T.BOTON,
                      fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, text_color=T.TEXTO_SOBRE_COLOR,
                      command=self.preguntar).grid(row=0, column=1, padx=(0, 6), pady=6)
        ctk.CTkButton(entrada, text="Limpiar", width=80, height=36, corner_radius=T.RADIO_BOTON, font=T.ETIQUETA_CHICA,
                      fg_color="transparent", hover_color=T.SUPERFICIE_ELEVADA, text_color=T.TEXTO_SECUNDARIO,
                      command=self.reiniciar).grid(row=0, column=2, padx=(0, 6), pady=6)

    def _ajustar_ancho(self, evento):
        ancho = max(320, evento.width - 120)
        if abs(ancho - self._ancho_texto) > 20:
            self._ancho_texto = ancho
            for etiqueta in getattr(self, "_textos", []):
                try:
                    etiqueta.configure(wraplength=ancho)
                except Exception:
                    pass

    # ------------------------------------------------------------------ uso desde la app
    def abrir(self, proceso=None):
        """Abre el asistente filtrado por el proceso de la pantalla desde la que se llamó."""
        self.elegir_filtro(proceso if proceso in PROCESOS else "todos")
        if not self._hay_conversacion:
            self.reiniciar()
        self.after(50, self.ent_pregunta.focus_set)

    def elegir_filtro(self, clave):
        self.filtro = clave
        for c, boton in self.botones_filtro.items():
            if c == clave:
                boton.configure(fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, text_color=T.TEXTO_SOBRE_COLOR)
            else:
                boton.configure(fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO)
        self._llenar_lista()

    def _llenar_lista(self):
        for widget in self.lista.winfo_children():
            widget.destroy()
        procesos = list(PROCESOS) if self.filtro == "todos" else [self.filtro]
        for proceso in procesos:
            entradas = self.buscador.del_proceso(proceso)
            if not entradas:
                continue
            texto, _fondo = COLOR_PROCESO[proceso]
            ctk.CTkLabel(self.lista, text=PROCESOS[proceso].upper(), font=T.ETIQUETA_CHICA, text_color=texto,
                         anchor="w").pack(fill="x", padx=8, pady=(10, 2))
            for entrada in entradas:
                fila = ctk.CTkFrame(self.lista, fg_color="transparent", corner_radius=10, cursor="hand2")
                fila.pack(fill="x", padx=2, pady=1)
                etiqueta = ctk.CTkLabel(fila, text=entrada["pregunta"], font=T.CUERPO_CHICO, text_color=T.TEXTO_SUAVE,
                                        anchor="w", justify="left", wraplength=320, cursor="hand2")
                etiqueta.pack(fill="x", padx=8, pady=5)
                for widget in (fila, etiqueta):
                    widget.bind("<Button-1>", lambda _e, i=entrada["id"]: self.responder_id(i))
                    widget.bind("<Enter>", lambda _e, f=fila: f.configure(fg_color=T.SUPERFICIE_ELEVADA))
                    widget.bind("<Leave>", lambda _e, f=fila: f.configure(fg_color="transparent"))

    # ------------------------------------------------------------------ conversación
    def reiniciar(self):
        for widget in self.chat.winfo_children():
            widget.destroy()
        self._textos = []
        self._hay_conversacion = False
        burbuja = self._burbuja_asistente()
        self._texto(burbuja, "¡Hola! Soy el asistente de Glucovil.", fuente=T.ETIQUETA)
        self._texto(burbuja, "Te puedo explicar cómo usar cada etapa de la app (Controlar, Netting y Liberación), qué "
                             "significa cada control y qué hacer cuando algo no sale. Probá con alguna de estas:")
        self._chips(burbuja, SUGERENCIAS_INICIO.get(self.filtro, SUGERENCIAS_INICIO["todos"]))

    def preguntar(self):
        consulta = self.ent_pregunta.get().strip()
        if not consulta:
            return
        self.ent_pregunta.delete(0, "end")
        self._burbuja_usuario(consulta)
        proceso = None if self.filtro == "todos" else self.filtro
        resultados = self.buscador.buscar(consulta, proceso=proceso)
        if proceso and (not resultados or resultados[0].puntaje < UMBRAL_RESPUESTA):
            resultados = self.buscador.buscar(consulta) or resultados    # probar en todos los procesos
        if resultados and resultados[0].puntaje >= UMBRAL_RESPUESTA:
            otras = [r.entrada["id"] for r in resultados[1:3] if r.puntaje >= resultados[0].puntaje * 0.6]
            self._respuesta(resultados[0].entrada, extra=otras)
        elif resultados:
            burbuja = self._burbuja_asistente()
            self._texto(burbuja, "No estoy seguro de haber entendido. ¿Es alguna de estas?")
            self._chips(burbuja, [r.entrada["id"] for r in resultados[:4]])
        else:
            burbuja = self._burbuja_asistente()
            self._texto(burbuja, "No tengo una respuesta para eso todavía. Probá con otras palabras (por ejemplo "
                                 "«fecha de proceso», «MANUAL», «Output E1») o elegí una pregunta de la lista.")
            self._chips(burbuja, SUGERENCIAS_INICIO["todos"][:3])
        self._bajar()

    def responder_id(self, identificador):
        entrada = self.buscador.por_id(identificador)
        if entrada is None:
            return
        self._burbuja_usuario(entrada["pregunta"])
        self._respuesta(entrada)
        self._bajar()

    def _respuesta(self, entrada, extra=()):
        self._hay_conversacion = True
        burbuja = self._burbuja_asistente()
        color, fondo = COLOR_PROCESO.get(entrada["proceso"], COLOR_PROCESO["general"])
        cabeza = ctk.CTkFrame(burbuja, fg_color="transparent", height=1)
        cabeza.pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(cabeza, text=f"  {PROCESOS[entrada['proceso']]}  ", font=T.ETIQUETA_CHICA, text_color=color,
                     fg_color=fondo, corner_radius=8).pack(side="left")
        self._texto(burbuja, entrada["pregunta"], fuente=T.ETIQUETA, arriba=6)
        for parrafo in entrada["respuesta"].split("\n"):
            if parrafo.strip():
                vineta = parrafo.startswith("• ")
                self._texto(burbuja, parrafo, sangria=16 if vineta else 0, arriba=2)
        pantalla = entrada.get("pantalla")
        if pantalla and pantalla in getattr(self.master, "frames", {}):
            from gui.app import TITULO_PANTALLA

            acciones = ctk.CTkFrame(burbuja, fg_color="transparent", height=1)
            acciones.pack(fill="x", padx=14, pady=(8, 0))

            ctk.CTkButton(
                acciones, text=f"Ir a «{TITULO_PANTALLA.get(pantalla, pantalla)}»  →", height=30,
                corner_radius=T.RADIO_BOTON, font=T.ETIQUETA_CHICA, fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER,
                text_color=T.TEXTO_SOBRE_COLOR, command=lambda p=pantalla: self._ir(p),
            ).pack(side="left")
        relacionadas = list(dict.fromkeys(list(entrada.get("relacionadas", [])) + list(extra)))
        relacionadas = [r for r in relacionadas if r != entrada["id"]][:3]
        if relacionadas:
            self._texto(burbuja, "También te puede servir:", fuente=T.NOTA, color=T.TEXTO_TENUE, arriba=8)
            self._chips(burbuja, relacionadas)
        else:
            ctk.CTkFrame(burbuja, fg_color="transparent", height=10, width=1).pack()

    def _ir(self, pantalla):
        if pantalla == "visualizacion":
            self.master.mostrar_pantalla_visualizacion()
        elif pantalla == "limpieza":
            self.master.mostrar_pantalla_limpieza()
        else:
            self.master.mostrar_pantalla(pantalla)

    # ------------------------------------------------------------------ piezas
    def _burbuja_usuario(self, texto):
        fila = ctk.CTkFrame(self.chat, fg_color="transparent")
        fila.pack(fill="x", pady=(10, 0), padx=6)
        burbuja = ctk.CTkFrame(fila, fg_color=T.PRIMARIO, corner_radius=14)
        burbuja.pack(side="right")
        etiqueta = ctk.CTkLabel(burbuja, text=texto, font=T.CUERPO, text_color=T.TEXTO_SOBRE_COLOR, justify="left",
                                wraplength=int(self._ancho_texto * 0.8))
        etiqueta.pack(padx=14, pady=8)

    def _burbuja_asistente(self):
        fila = ctk.CTkFrame(self.chat, fg_color="transparent")
        fila.pack(fill="x", pady=(10, 0), padx=6)
        ctk.CTkLabel(fila, text="G", width=30, height=30, corner_radius=15, fg_color=T.MARCA,
                     text_color=T.TEXTO_SOBRE_COLOR, font=T.ETIQUETA).pack(side="left", anchor="n", padx=(0, 8))
        burbuja = ctk.CTkFrame(fila, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=14, border_width=1,
                               border_color=T.BORDE)
        burbuja.pack(side="left", fill="x", expand=True)
        return burbuja

    def _texto(self, burbuja, texto, fuente=None, color=None, sangria=0, arriba=10):
        etiqueta = ctk.CTkLabel(burbuja, text=texto, font=fuente or T.CUERPO, text_color=color or T.TEXTO_SUAVE,
                                anchor="w", justify="left", wraplength=self._ancho_texto - sangria, height=1)
        etiqueta.pack(fill="x", padx=(14 + sangria, 14), pady=(arriba, 0))
        self._textos.append(etiqueta)
        return etiqueta

    def _chips(self, burbuja, ids):
        contenedor = ctk.CTkFrame(burbuja, fg_color="transparent", height=1)
        contenedor.pack(fill="x", padx=12, pady=(6, 12))
        for identificador in ids:
            entrada = self.buscador.por_id(identificador)
            if entrada is None:
                continue
            ctk.CTkButton(
                contenedor, text=entrada["pregunta"], anchor="w", height=28, corner_radius=14, font=T.CUERPO_CHICO,
                fg_color=T.SUPERFICIE, hover_color=T.SUPERFICIE_ELEVADA, text_color=T.ENLACE, border_width=1,
                border_color=T.BORDE, command=lambda i=identificador: self.responder_id(i),
            ).pack(anchor="w", pady=2)

    def _bajar(self):
        """Lleva la conversación al final (después de que se acomodan los widgets nuevos)."""
        def mover():
            try:
                self.chat._parent_canvas.configure(scrollregion=self.chat._parent_canvas.bbox("all"))
                self.chat._parent_canvas.yview_moveto(1.0)
            except Exception:
                pass
        self.update_idletasks()
        self.after(60, mover)
