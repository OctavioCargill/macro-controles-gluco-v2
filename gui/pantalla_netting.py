"""Pantallas de Netting: menú, armado de propuestas, revisión y salida."""

import logging
import os
import queue
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from gui import tema as T
from gui.pantalla_inicio import TarjetaPaso, alternar_estado_vacio, crear_estado_vacio
from netting.cargas import ErrorDeCarga
from netting.config import cargar_config, guardar_config
from netting.salida import asignar_grupos, resumen_propuestas
from netting.servicio import (
    NOMBRE_SALIDA, ejecutar_netting, generar_salida, guardar_datos_paquete, repartir_grupos,
    resumen_por_fecha_de_pago,
)
from services.auditoria import APP_DATA_PATH

logger = logging.getLogger(__name__)


def _moneda(valor):
    if valor is None or valor == "":
        return ""
    try:
        texto = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return str(valor)
    return "$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _fecha(valor):
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    return "" if valor in (None, "") else str(valor)


def _boton(master, texto, comando, tipo="primario", ancho=200, alto=None):
    colores = {
        "primario": dict(fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, text_color=T.TEXTO_SOBRE_COLOR),
        "secundario": dict(fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO),
        "borde": dict(fg_color="transparent", hover_color=T.SUPERFICIE_ELEVADA, text_color=T.TEXTO_SECUNDARIO,
                      border_width=1, border_color=T.BORDE),
    }[tipo]
    return ctk.CTkButton(
        master, text=texto, command=comando, width=ancho, height=alto or T.ALTO_BOTON,
        corner_radius=T.RADIO_BOTON, font=T.BOTON if tipo != "borde" else T.ETIQUETA_CHICA, **colores
    )


def _panel(master):
    return ctk.CTkFrame(master, fg_color=T.SUPERFICIE, corner_radius=T.RADIO_PANEL, border_width=1, border_color=T.BORDE)


def _tabla(master, columnas, anchos, alto=8, derecha=(), estirar=()):
    marco = ctk.CTkFrame(master, fg_color="transparent")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", selectmode="browse", height=alto)
    for columna in columnas:
        tabla.heading(columna, text=columna)
        tabla.column(
            columna, width=anchos.get(columna, 100), stretch=columna in estirar,
            anchor="e" if columna in derecha else "w",
        )
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    tabla.pack(side="left", fill="both", expand=True)
    tabla.tag_configure("par", background=T.SUPERFICIE)
    tabla.tag_configure("impar", background=T.SUPERFICIE_HUNDIDA)
    tabla.tag_configure("negativo", background=T.AVISO_FONDO, foreground=T.AVISO)
    return marco, tabla


def _encabezado(master, titulo, descripcion, compacto=False):
    ctk.CTkLabel(master, text="NETTING · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(
        anchor="w", padx=18, pady=(6 if compacto else 14, 0))
    ctk.CTkLabel(master, text=titulo, font=T.TITULO_PANTALLA, text_color=T.TEXTO).pack(anchor="w", padx=18)
    if descripcion:
        ctk.CTkLabel(
            master, text=descripcion, font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO,
            anchor="w", justify="left", wraplength=1000,
        ).pack(anchor="w", padx=18, pady=(0, 6 if compacto else 10))


# ====================================================================== menú

class MenuNetting(ctk.CTkFrame):
    """Los tres pasos de Netting."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)

        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=70, pady=(40, 0))

        ctk.CTkLabel(contenido, text="NETTING · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        ctk.CTkLabel(contenido, text="Netting de liquidaciones", font=(T.FUENTE, 30, "bold"), text_color=T.TEXTO).pack(anchor="w")
        ctk.CTkLabel(
            contenido,
            text="Arma las propuestas de 24 y 48 hs: por beneficiario, lo que se le paga y lo que se le descuenta.",
            font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO,
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(contenido, text="Proceso de netting", font=T.SUBTITULO, text_color=T.TEXTO).pack(anchor="w", pady=(32, 12))
        pasos = ctk.CTkFrame(contenido, fg_color="transparent")
        pasos.pack(fill="x")
        for columna in range(3):
            pasos.grid_columnconfigure(columna, weight=1, uniform="pasos")

        self.paso_armar = TarjetaPaso(pasos, 1, "Armar propuestas", lambda: master.mostrar_pantalla("netting_carga"))
        self.paso_revisar = TarjetaPaso(pasos, 2, "Revisar propuestas", lambda: master.mostrar_pantalla("netting_revision"))
        self.paso_salida = TarjetaPaso(pasos, 3, "Dar salida", lambda: master.mostrar_pantalla("netting_salida"))
        for columna, tarjeta in enumerate((self.paso_armar, self.paso_revisar, self.paso_salida)):
            tarjeta.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 8, 0 if columna == 2 else 8))

        ctk.CTkLabel(
            contenido,
            text=(
                "Esta versión replica la macro Macro_Propuesta.xlsm (solo propuestas automáticas). "
                "Para validarla, corré la macro y la app con los mismos archivos y la misma fecha y compará "
                "Propuestas_Netting."
            ),
            font=T.NOTA, text_color=T.TEXTO_TENUE, wraplength=900, justify="left",
        ).pack(anchor="w", pady=(24, 0))

        self.actualizar_estado()

    def actualizar_estado(self):
        resultado = getattr(self.master, "netting_resultado", None)
        salida = getattr(self.master, "netting_salida", None)
        if resultado is None:
            self.paso_armar.mostrar("siguiente", "Histórico de controlados, 077 y 090. Elegís la fecha de proceso.", "Empezar →")
            self.paso_revisar.mostrar("bloqueado", "Propuestas por beneficiario con lo que se paga y lo que se descuenta.", "Primero armá las propuestas")
            self.paso_salida.mostrar("bloqueado", "Reparto por analista y archivo Propuestas_Netting.", "Primero armá las propuestas")
            return
        e = resultado.estadisticas
        hora = resultado.generado.strftime("%H:%M")
        self.paso_armar.mostrar(
            "hecho", f"Armadas a las {hora} con fecha {resultado.fecha_proceso:%d/%m/%Y}.", "Volver a armar"
        )
        avisos = len(resultado.avisos.revisar)
        detalle = f"{e['propuestas_24']} de 24 hs y {e['propuestas_48']} de 48 hs."
        if avisos:
            detalle += f" {avisos} aviso(s) para revisar."
        if salida:
            self.paso_revisar.mostrar("disponible", detalle, "Ver →")
            self.paso_salida.mostrar("hecho", f"Generado: {Path(salida).name}", "Volver a generar")
        else:
            self.paso_revisar.mostrar("siguiente", detalle, "Revisar →")
            self.paso_salida.mostrar("disponible", "Repartí entre analistas y generá el archivo.", "Dar salida →")


# ====================================================================== armar propuestas

ARCHIVOS = (
    ("historico", "Histórico de documentos controlados", "Historico_Documentos_Controlados (.xlsb / .xlsx)"),
    ("077", "Reporte 077", "Documentos pendientes de cobro"),
    ("090", "Reporte 090", "Contratos de compra"),
)


class PantallaNettingCarga(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.config = cargar_config()
        self.rutas = {clave: self.config.get("rutas", {}).get(clave, "") for clave, *_ in ARCHIVOS}
        self.rutas = {k: (v if v and Path(v).exists() else "") for k, v in self.rutas.items()}
        self._cola = queue.Queue()
        self._procesando = False
        self._crear()

    def _crear(self):
        _encabezado(self, "Armar propuestas", "Elegí los archivos del día y la fecha de proceso (la que la macro toma como «hoy»).", compacto=True)

        # --- Pie anclado abajo: actividad, estado y botones
        self.frame_log = ctk.CTkFrame(self, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=14, border_width=1, border_color=T.BORDE)
        self.frame_log.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(self.frame_log, text="Actividad", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO).pack(anchor="w", padx=12, pady=(8, 0))
        self.log = ctk.CTkTextbox(self.frame_log, height=64, state="disabled", wrap="word",
                                  fg_color=T.SUPERFICIE_HUNDIDA, text_color=T.TEXTO_SUAVE)
        self.log.pack(fill="x", padx=12, pady=(4, 10))

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        self.btn_armar = _boton(acciones, "Armar propuestas", self.armar, ancho=220)
        self.btn_armar.pack(side="left")
        self.btn_revisar = _boton(acciones, "Revisar propuestas →", lambda: self.master.mostrar_pantalla("netting_revision"),
                                  tipo="secundario", ancho=210)
        self.estado = ctk.CTkLabel(acciones, text="", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO, anchor="w",
                                   justify="left", wraplength=640)
        self.estado.pack(side="left", padx=16)
        self.barra = ctk.CTkProgressBar(self, mode="indeterminate", height=8, progress_color=T.EN_CURSO)

        # --- Archivos
        panel = _panel(self)
        panel.pack(fill="x", padx=20, pady=(0, 12))
        panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="Archivos de entrada", font=T.SUBTITULO, text_color=T.TEXTO).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(10, 2))
        self.lbl_rutas = {}
        for fila, (clave, titulo, ayuda) in enumerate(ARCHIVOS, start=1):
            textos = ctk.CTkFrame(panel, fg_color="transparent")
            textos.grid(row=fila, column=0, sticky="nw", padx=(18, 12), pady=2)
            ctk.CTkLabel(textos, text=titulo, font=T.ETIQUETA, text_color=T.TEXTO, anchor="w", height=20).pack(anchor="w")
            ctk.CTkLabel(textos, text=ayuda, font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w", height=16).pack(anchor="w")
            etiqueta = ctk.CTkLabel(panel, text="", font=T.CUERPO_CHICO, anchor="w", justify="left", wraplength=620)
            etiqueta.grid(row=fila, column=1, sticky="w", pady=2)
            botones = ctk.CTkFrame(panel, fg_color="transparent")
            botones.grid(row=fila, column=2, sticky="e", padx=18, pady=2)
            _boton(botones, "Elegir…", lambda c=clave: self.elegir(c), tipo="secundario", ancho=110, alto=32).pack(side="left")
            self.lbl_rutas[clave] = etiqueta
        ctk.CTkFrame(panel, fg_color="transparent", height=6).grid(row=len(ARCHIVOS) + 1, column=0)
        self._refrescar_rutas()

        # --- Parámetros
        parametros = _panel(self)
        parametros.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(parametros, text="Parámetros", font=T.SUBTITULO, text_color=T.TEXTO).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(10, 2))

        ctk.CTkLabel(parametros, text="Fecha de proceso", font=T.ETIQUETA, text_color=T.TEXTO).grid(row=1, column=0, sticky="w", padx=(18, 10))
        fila_fecha = ctk.CTkFrame(parametros, fg_color="transparent")
        fila_fecha.grid(row=1, column=1, sticky="w")
        self.ent_fecha = ctk.CTkEntry(fila_fecha, width=120, fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
        self.ent_fecha.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fecha.pack(side="left")
        _boton(fila_fecha, "Hoy", lambda: self._poner_fecha(0), tipo="borde", ancho=56, alto=30).pack(side="left", padx=(8, 4))
        _boton(fila_fecha, "Día hábil anterior", lambda: self._poner_fecha(-1), tipo="borde", ancho=130, alto=30).pack(side="left")
        ctk.CTkLabel(
            parametros, text="Para probar con los archivos de ayer, poné la fecha de ayer.",
            font=T.NOTA, text_color=T.TEXTO_TENUE,
        ).grid(row=2, column=1, sticky="w", pady=(2, 8))

        ctk.CTkLabel(parametros, text="Último N° de propuesta", font=T.ETIQUETA, text_color=T.TEXTO).grid(row=1, column=2, sticky="w", padx=(40, 10))
        self.ent_numero = ctk.CTkEntry(parametros, width=120, fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
        self.ent_numero.insert(0, str(self.config.get("ultimo_numero_propuesta", 0)))
        self.ent_numero.grid(row=1, column=3, sticky="w", padx=(0, 18))
        ctk.CTkLabel(
            parametros, text="El de la macro (hoja Tablas, celda G2) antes de correrla.",
            font=T.NOTA, text_color=T.TEXTO_TENUE,
        ).grid(row=2, column=3, sticky="w", padx=(0, 18), pady=(2, 8))

        self.var_bloquear = ctk.BooleanVar(value=bool(self.config.get("bloquear_propuestos", True)))
        ctk.CTkCheckBox(
            parametros,
            text="No volver a proponer documentos que ya salieron en una propuesta (hasta que Liberación los libere)",
            variable=self.var_bloquear, font=T.CUERPO_CHICO, text_color=T.TEXTO_SUAVE,
            fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, border_color=T.BORDE_FUERTE,
            checkbox_width=18, checkbox_height=18,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=18, pady=(0, 10))

    def al_mostrar(self):
        # Después de dar salida, el último N° guardado pasa a ser el punto de partida de la próxima corrida.
        if getattr(self.master, "netting_salida", None) and not self._procesando:
            self.config = cargar_config()
            self.ent_numero.delete(0, "end")
            self.ent_numero.insert(0, str(self.config.get("ultimo_numero_propuesta", 0)))

    # ------------------------------------------------------------------ archivos y parámetros
    def _refrescar_rutas(self):
        for clave, etiqueta in self.lbl_rutas.items():
            ruta = self.rutas.get(clave)
            if ruta:
                try:
                    modificado = datetime.fromtimestamp(Path(ruta).stat().st_mtime)
                    cuando = f"   ·   modificado {modificado:%d/%m/%Y %H:%M}"
                    viejo = modificado.date() < date.today()
                except OSError:
                    cuando, viejo = "", False
                etiqueta.configure(text=f"✓  {ruta}{cuando}", text_color=T.AVISO if viejo else T.OK)
            else:
                etiqueta.configure(text="Sin elegir", text_color=T.TEXTO_TENUE)

    def elegir(self, clave):
        actual = self.rutas.get(clave) or self.config.get("rutas", {}).get(clave) or ""
        carpeta = str(Path(actual).parent) if actual else str(APP_DATA_PATH)
        ruta = filedialog.askopenfilename(
            title=f"Elegir {dict((c, t) for c, t, _ in ARCHIVOS)[clave]}",
            initialdir=carpeta if Path(carpeta).exists() else None,
            filetypes=[("Excel", "*.xlsb *.xlsx *.xlsm *.xls"), ("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if ruta:
            self.rutas[clave] = ruta
            self._refrescar_rutas()

    def _poner_fecha(self, desplazamiento):
        dia = date.today()
        if desplazamiento < 0:
            dia -= timedelta(days=1)
            while dia.weekday() >= 5:
                dia -= timedelta(days=1)
        self.ent_fecha.delete(0, "end")
        self.ent_fecha.insert(0, dia.strftime("%d/%m/%Y"))

    def _leer_parametros(self):
        try:
            fecha = datetime.strptime(self.ent_fecha.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            raise ValueError("La fecha de proceso tiene que tener el formato dd/mm/aaaa.")
        try:
            numero = int(self.ent_numero.get().strip().replace(".", ""))
        except ValueError:
            raise ValueError("El último N° de propuesta tiene que ser un número entero.")
        return fecha, numero

    # ------------------------------------------------------------------ proceso
    def _agregar_log(self, mensaje):
        self.log.configure(state="normal")
        self.log.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {mensaje}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def armar(self):
        if self._procesando:
            return
        faltan = [titulo for clave, titulo, _ in ARCHIVOS if not self.rutas.get(clave)]
        if faltan:
            messagebox.showwarning("Faltan archivos", "Elegí: " + ", ".join(faltan) + ".")
            return
        try:
            fecha, numero = self._leer_parametros()
        except ValueError as exc:
            messagebox.showwarning("Revisá los parámetros", str(exc))
            return
        if fecha != date.today() and not messagebox.askyesno(
            "Fecha de proceso",
            f"La fecha de proceso es {fecha:%d/%m/%Y} (no es hoy). Los días a pagar se calculan contra esa fecha.\n\n¿Seguir?",
        ):
            return
        if getattr(self.master, "netting_resultado", None) is not None and not messagebox.askyesno(
            "Volver a armar", "Ya hay propuestas armadas en esta sesión. Se van a reemplazar. ¿Seguir?"
        ):
            return

        self.config["rutas"].update(self.rutas)
        self.config["ultimo_numero_propuesta"] = numero
        self.config["bloquear_propuestos"] = bool(self.var_bloquear.get())
        try:
            guardar_config(self.config)
        except Exception:
            logger.exception("No se pudo guardar la configuración de Netting")

        self._set_procesando(True)
        self._agregar_log(f"Armando propuestas con fecha {fecha:%d/%m/%Y}, desde el N° {numero + 1}.")
        rutas = dict(self.rutas)
        config = dict(self.config)

        def tarea():
            try:
                resultado = ejecutar_netting(rutas, fecha, numero, config, progreso=lambda t: self._cola.put(("log", t)))
                self._cola.put(("ok", resultado))
            except ErrorDeCarga as exc:
                self._cola.put(("error", str(exc)))
            except Exception as exc:  # pragma: no cover - errores inesperados
                logger.exception("Error armando propuestas de netting")
                self._cola.put(("error", f"Error inesperado: {exc}"))

        threading.Thread(target=tarea, daemon=True).start()
        self.after(100, self._revisar_cola)

    def _revisar_cola(self):
        try:
            while True:
                tipo, valor = self._cola.get_nowait()
                if tipo == "log":
                    self._agregar_log(valor)
                elif tipo == "ok":
                    self._terminar(valor)
                    return
                elif tipo == "error":
                    self._set_procesando(False)
                    self.estado.configure(text=valor, text_color=T.ERROR)
                    self._agregar_log(f"Error: {valor}")
                    messagebox.showerror("No se pudieron armar las propuestas", valor)
                    return
        except queue.Empty:
            pass
        self.after(150, self._revisar_cola)

    def _terminar(self, resultado):
        self._set_procesando(False)
        self.master.netting_resultado = resultado
        self.master.netting_salida = None
        e = resultado.estadisticas
        for aviso in resultado.avisos.info:
            self._agregar_log(aviso)
        for aviso in resultado.avisos.revisar:
            self._agregar_log(f"REVISAR: {aviso}")
        texto = (
            f"{e['propuestas_24']} propuestas de 24 hs ({e['filas_24']} documentos) y {e['propuestas_48']} de 48 hs "
            f"({e['filas_48']} documentos). N° {resultado.numero_inicial + 1} a {resultado.numero_final}."
        )
        avisos = len(resultado.avisos.revisar)
        if avisos:
            texto += f"  {avisos} aviso(s) para revisar."
        self.estado.configure(text=texto, text_color=T.AVISO if avisos else T.OK)
        self.btn_revisar.pack(side="left", padx=(12, 0), after=self.btn_armar)

    def _set_procesando(self, activo):
        self._procesando = activo
        self.master.bloquear_navegacion(activo)
        self.btn_armar.configure(state="disabled" if activo else "normal",
                                 text="Armando…" if activo else "Armar propuestas")
        if activo:
            self.estado.configure(text="Procesando…", text_color=T.EN_CURSO)
            self.btn_revisar.pack_forget()
            self.barra.pack(side="bottom", fill="x", padx=20, pady=(0, 8), before=self.frame_log)
            self.barra.start()
        else:
            self.barra.stop()
            self.barra.pack_forget()


# ====================================================================== revisar

class PantallaNettingRevision(ctk.CTkFrame):
    """Un paquete por AB, como el formulario de la macro: lo que se descuenta y lo que se paga."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.ventana = "24"
        self._resumen = []
        self._visibles = []
        self._actual = None
        self._crear()

    def _crear(self):
        # --- Cabecera: título, 24/48, buscador y avisos
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x")
        izquierda = ctk.CTkFrame(cabecera, fg_color="transparent")
        izquierda.pack(side="left")
        _encabezado(izquierda, "Revisar propuestas", "", compacto=True)

        controles = ctk.CTkFrame(cabecera, fg_color="transparent")
        controles.pack(side="right", padx=20, pady=(18, 0))
        self.btn_avisos = _boton(controles, "Avisos", self.ver_avisos, tipo="borde", ancho=110, alto=34)
        self.btn_avisos.pack(side="right", padx=(8, 0))
        _boton(controles, "Por fecha de pago", self.ver_por_fecha, tipo="borde", ancho=140, alto=34).pack(
            side="right", padx=(8, 0))
        selector = ctk.CTkFrame(controles, fg_color="transparent")
        selector.pack(side="right", padx=(8, 0))
        self.botones_ventana = {}
        for ventana in ("24", "48"):
            boton = ctk.CTkButton(
                selector, text=f"{ventana} hs", width=70, height=34, corner_radius=T.RADIO_BOTON, font=T.ETIQUETA,
                command=lambda v=ventana: self._cambiar_ventana(v),
            )
            boton.pack(side="left", padx=(0, 4))
            self.botones_ventana[ventana] = boton
        self._marcar_ventana()

        fila_grupo = ctk.CTkFrame(self, fg_color="transparent")
        fila_grupo.pack(fill="x", padx=20, pady=(0, 6))
        self.lbl_totales = ctk.CTkLabel(fila_grupo, text="", font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_totales.pack(side="left")
        _boton(fila_grupo, "Repartir", self._repartir, tipo="borde", ancho=80, alto=28).pack(side="right")
        self.ent_analistas = ctk.CTkEntry(fila_grupo, width=44, height=28, fg_color=T.SUPERFICIE_HUNDIDA,
                                          border_color=T.BORDE_FUERTE, justify="center")
        self.ent_analistas.pack(side="right", padx=(6, 6))
        ctk.CTkLabel(fila_grupo, text="Analistas", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="right")
        self.combo_grupo = ctk.CTkOptionMenu(
            fila_grupo, values=["Todos"], width=90, height=28, command=lambda _v: self._llenar_lista(),
            fg_color=T.SECUNDARIO, button_color=T.SECUNDARIO_HOVER, button_hover_color=T.BORDE_FUERTE,
            text_color=T.TEXTO_SOBRE_SECUNDARIO, dropdown_fg_color=T.SUPERFICIE, dropdown_text_color=T.TEXTO,
            dropdown_hover_color=T.SUPERFICIE_ELEVADA, font=T.ETIQUETA_CHICA,
        )
        self.combo_grupo.pack(side="right", padx=(6, 16))
        ctk.CTkLabel(fila_grupo, text="Mi grupo", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="right")

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        cuerpo.grid_columnconfigure(0, weight=0, minsize=330)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        # --- Izquierda: lista de paquetes
        lista = _panel(cuerpo)
        lista.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.ent_buscar = ctk.CTkEntry(lista, placeholder_text="Buscar cliente, AB o N°…",
                                       fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
        self.ent_buscar.pack(fill="x", padx=12, pady=(12, 8))
        self.ent_buscar.bind("<KeyRelease>", lambda _e: self._llenar_lista())
        marco, self.tabla = _tabla(lista, ("N°", "Cliente", "Neto"), {"N°": 60, "Cliente": 150, "Neto": 100},
                                   alto=10, derecha=("Neto",), estirar=("Cliente",))
        marco.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tabla.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_seleccion())

        # --- Derecha: el paquete seleccionado
        detalle = _panel(cuerpo)
        detalle.grid(row=0, column=1, sticky="nsew")
        detalle.grid_columnconfigure(0, weight=1)
        detalle.grid_rowconfigure(2, weight=1)
        detalle.grid_rowconfigure(3, weight=1)

        encabezado = ctk.CTkFrame(detalle, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        encabezado.grid_columnconfigure(1, weight=1)
        self.lbl_tipo = ctk.CTkLabel(encabezado, text="", font=T.ETIQUETA_CHICA, text_color=T.MARCA, anchor="w")
        self.lbl_tipo.grid(row=0, column=0, columnspan=2, sticky="w")
        self.lbl_cliente = ctk.CTkLabel(encabezado, text="", font=(T.FUENTE, 20, "bold"), text_color=T.TEXTO, anchor="w")
        self.lbl_cliente.grid(row=1, column=0, columnspan=2, sticky="w")
        self.lbl_ab = ctk.CTkLabel(encabezado, text="", font=T.ETIQUETA, text_color=T.INFO, anchor="w",
                                   fg_color=T.INFO_FONDO, corner_radius=8)
        self.lbl_ab.grid(row=2, column=0, sticky="w", pady=(2, 0))
        self.lbl_ab.bind("<Button-1>", lambda _e: self._copiar_ab())
        self.lbl_ab.configure(cursor="hand2")
        neto = ctk.CTkFrame(encabezado, fg_color="transparent")
        neto.grid(row=0, column=2, rowspan=3, sticky="e")
        ctk.CTkLabel(neto, text="Neto a pagar", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE).pack(anchor="e")
        self.lbl_neto = ctk.CTkLabel(neto, text="", font=(T.FUENTE, 22, "bold"), text_color=T.TEXTO)
        self.lbl_neto.pack(anchor="e")

        ctk.CTkFrame(detalle, fg_color=T.BORDE, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        self.seccion_cobrar, self.tabla_cobrar, self.lbl_total_cobrar = self._seccion(
            detalle, 2, "CUENTAS POR COBRAR", T.PELIGRO,
            ("Vendedor", "Corredor", "N° Doc", "Tipo", "Emisión", "Descripción", "Total"),
            {"Vendedor": 150, "Corredor": 110, "N° Doc": 80, "Tipo": 45, "Emisión": 90,
             "Descripción": 150, "Total": 115},
        )
        self.seccion_pagar, self.tabla_pagar, self.lbl_total_pagar = self._seccion(
            detalle, 3, "CUENTA POR PAGAR", T.INFO,
            ("Vendedor", "Corredor", "Beneficiario", "N° Doc", "Tipo", "Descripción", "Total"),
            {"Vendedor": 130, "Corredor": 110, "Beneficiario": 130, "N° Doc": 80, "Tipo": 45,
             "Descripción": 130, "Total": 115},
        )

        # --- Pie: observaciones y navegación
        pie = ctk.CTkFrame(detalle, fg_color="transparent")
        pie.grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 12))
        pie.grid_columnconfigure(1, weight=1)
        datos = ctk.CTkFrame(pie, fg_color="transparent")
        datos.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ctk.CTkLabel(datos, text="Acción", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="left")
        self.combo_accion = ctk.CTkOptionMenu(
            datos, values=["—", "PERMUTA", "COMPENSA"], width=120, height=28,
            fg_color=T.SECUNDARIO, button_color=T.SECUNDARIO_HOVER, button_hover_color=T.BORDE_FUERTE,
            text_color=T.TEXTO_SOBRE_SECUNDARIO, dropdown_fg_color=T.SUPERFICIE, dropdown_text_color=T.TEXTO,
            dropdown_hover_color=T.SUPERFICIE_ELEVADA, font=T.ETIQUETA_CHICA,
        )
        self.combo_accion.pack(side="left", padx=(6, 18))
        ctk.CTkLabel(datos, text="ID de pago E1", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="left")
        self.ent_id_pago = ctk.CTkEntry(datos, width=150, height=28, fg_color=T.SUPERFICIE_HUNDIDA,
                                        border_color=T.BORDE_FUERTE, placeholder_text="Después de E1")
        self.ent_id_pago.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(pie, text="Observaciones", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).grid(
            row=1, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))
        self.txt_obs = ctk.CTkTextbox(pie, height=44, wrap="word", fg_color=T.SUPERFICIE_HUNDIDA,
                                      border_color=T.BORDE_FUERTE, border_width=1, text_color=T.TEXTO)
        self.txt_obs.grid(row=1, column=1, sticky="ew")
        acciones = ctk.CTkFrame(pie, fg_color="transparent")
        acciones.grid(row=0, column=2, rowspan=2, sticky="e", padx=(10, 0))
        self.btn_obs = _boton(acciones, "Guardar", self._guardar_observacion, tipo="primario", ancho=150, alto=34)
        self.btn_obs.pack(anchor="e")
        navegacion = ctk.CTkFrame(acciones, fg_color="transparent")
        navegacion.pack(anchor="e", pady=(6, 0))
        _boton(navegacion, "«", lambda: self._mover(-1), tipo="secundario", ancho=44, alto=30).pack(side="left")
        self.lbl_posicion = ctk.CTkLabel(navegacion, text="", font=T.ETIQUETA, text_color=T.TEXTO, width=80)
        self.lbl_posicion.pack(side="left")
        _boton(navegacion, "»", lambda: self._mover(1), tipo="secundario", ancho=44, alto=30).pack(side="left")

        self.vacio = crear_estado_vacio(
            self, "Todavía no hay propuestas armadas", "Armá las propuestas en el paso 1 para revisarlas acá.")

    def _seccion(self, master, fila, titulo, color, columnas, anchos):
        marco = ctk.CTkFrame(master, fg_color="transparent")
        marco.grid(row=fila, column=0, sticky="nsew", padx=16, pady=(0, 8))
        barra = ctk.CTkFrame(marco, fg_color=color, corner_radius=8, height=28)
        barra.pack(fill="x")
        ctk.CTkLabel(barra, text=titulo, font=T.ETIQUETA, text_color=T.TEXTO_SOBRE_COLOR).pack(pady=3)
        total = ctk.CTkLabel(marco, text="", font=T.ETIQUETA, text_color=color, anchor="e", height=24)
        total.pack(side="bottom", anchor="e")
        contenedor, tabla = _tabla(marco, columnas, anchos, alto=3, derecha=("Total",),
                                   estirar=("Descripción", "Vendedor"))
        contenedor.pack(fill="both", expand=True, pady=(4, 2))
        return marco, tabla, total

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        resultado = getattr(self.master, "netting_resultado", None)
        alternar_estado_vacio(self.vacio, resultado is None)
        if resultado is None:
            return
        cantidad = len(resultado.avisos.revisar)
        self.btn_avisos.configure(text=f"⚠  Avisos ({cantidad})" if cantidad else "Avisos",
                                  text_color=T.AVISO if cantidad else T.TEXTO_SECUNDARIO)
        self.ent_analistas.delete(0, "end")
        self.ent_analistas.insert(0, str(resultado.cantidad_analistas))
        self._actualizar_grupos()
        self._cambiar_ventana(self.ventana)

    def _actualizar_grupos(self):
        resultado = getattr(self.master, "netting_resultado", None)
        cantidad = resultado.cantidad_analistas if resultado else 1
        valores = ["Todos"] + [str(g) for g in range(1, cantidad + 2)]
        actual = self.combo_grupo.get()
        self.combo_grupo.configure(values=valores)
        self.combo_grupo.set(actual if actual in valores else "Todos")

    def _repartir(self):
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            return
        try:
            cantidad = int(self.ent_analistas.get().strip())
            if cantidad < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Analistas", "Ingresá un número entero mayor que 0.")
            return
        repartir_grupos(resultado, cantidad)
        self._actualizar_grupos()
        self._cambiar_ventana(self.ventana)

    def _marcar_ventana(self):
        for ventana, boton in self.botones_ventana.items():
            if ventana == self.ventana:
                boton.configure(fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, text_color=T.TEXTO_SOBRE_COLOR)
            else:
                boton.configure(fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO)

    def _cambiar_ventana(self, valor):
        self.ventana = "48" if str(valor).startswith("48") else "24"
        self._marcar_ventana()
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            return
        self._resumen = resultado.resumen(self.ventana)
        pagar = sum(r["a_pagar"] for r in self._resumen)
        descontar = sum(r["a_descontar"] for r in self._resumen)
        self.lbl_totales.configure(
            text=(f"{len(self._resumen)} paquetes (uno por AB)  ·  A pagar {_moneda(pagar)}  ·  "
                  f"A descontar {_moneda(descontar)}  ·  Neto {_moneda(pagar + descontar)}  ·  "
                  f"Fecha de proceso {resultado.fecha_proceso:%d/%m/%Y}")
        )
        self._llenar_lista()

    def _llenar_lista(self):
        self.tabla.delete(*self.tabla.get_children())
        filtro = self.ent_buscar.get().strip().casefold()
        grupo = self.combo_grupo.get()
        self._visibles = []
        for indice, item in enumerate(self._resumen):
            texto = f"{item['n_propuesta']} {item['ab_benef']} {item['ab_e1']} {item['benef']} {item['tipo_benef']}".casefold()
            if filtro and filtro not in texto:
                continue
            if grupo != "Todos" and str(item["grupo"]) != grupo:
                continue
            self._visibles.append(indice)
            etiqueta = "negativo" if item["neto"] < 0 or item["alerta_estatus"] else (
                "par" if len(self._visibles) % 2 else "impar")
            cliente = ("⚠ " if item["alerta_estatus"] else "") + str(item["benef"])
            self.tabla.insert("", "end", iid=str(indice), tags=(etiqueta,),
                              values=(item["n_propuesta"], cliente, _moneda(item["neto"])))
        if self._visibles:
            self._seleccionar(self._visibles[0])
        else:
            self._actual = None
            self._limpiar_detalle()

    def _seleccionar(self, indice):
        self.tabla.selection_set(str(indice))
        self.tabla.focus(str(indice))
        self.tabla.see(str(indice))

    def _mostrar_seleccion(self):
        seleccion = self.tabla.selection()
        if seleccion:
            self._mostrar_paquete(int(seleccion[0]))

    def _mover(self, paso):
        if not self._visibles or self._actual not in self._visibles:
            return
        posicion = (self._visibles.index(self._actual) + paso) % len(self._visibles)
        self._seleccionar(self._visibles[posicion])

    def _limpiar_detalle(self):
        for etiqueta in (self.lbl_tipo, self.lbl_cliente, self.lbl_ab, self.lbl_neto, self.lbl_posicion,
                         self.lbl_total_cobrar, self.lbl_total_pagar):
            etiqueta.configure(text="")
        self.tabla_cobrar.delete(*self.tabla_cobrar.get_children())
        self.tabla_pagar.delete(*self.tabla_pagar.get_children())
        self.txt_obs.delete("1.0", "end")

    def _mostrar_paquete(self, indice):
        self._actual = indice
        item = self._resumen[indice]
        self.lbl_tipo.configure(
            text=f"PROPUESTA {self.ventana} HS  ·  N° {item['n_propuesta']}  ·  GRUPO {item['grupo']}  ·  "
                 f"{item['tipo_benef']}  ·  AB beneficiario {item['ab_benef']}"
                 + ("  ·  ⚠ HAY PARCIALES QUE NO ESTÁN EN A o P" if item["alerta_estatus"] else ""))
        self.lbl_cliente.configure(text=item["benef"])
        self.lbl_ab.configure(
            text=f"  Buscar en netting por {item['buscar_por']}: pegar AB {item['ab_e1']} en «{item['campo_e1']}»   ⧉  ")
        self.lbl_neto.configure(text=_moneda(item["neto"]), text_color=T.ERROR if item["neto"] < 0 else T.TEXTO)

        self.tabla_cobrar.delete(*self.tabla_cobrar.get_children())
        self.tabla_pagar.delete(*self.tabla_pagar.get_children())
        n_cobrar = n_pagar = 0
        for fila in item["filas"]:
            corredor = fila["corredor"] if fila["corredor"] not in ("", None) else "DIRECTO"
            if fila["tipo"] == "PAGAR":
                self.tabla_pagar.insert("", "end", tags=("par" if n_pagar % 2 == 0 else "impar",), values=(
                    fila["vendedor"], corredor, fila["benef"], fila["doc"], fila["tipo_doc"], fila["desc"],
                    _moneda(fila["total"])))
                n_pagar += 1
            else:
                self.tabla_cobrar.insert("", "end", tags=("par" if n_cobrar % 2 == 0 else "impar",), values=(
                    fila["vendedor"], corredor, fila["doc"], fila["tipo_doc"], _fecha(fila["fecha_emision"]),
                    fila["desc"] or fila.get("origen", ""), _moneda(fila["total"])))
                n_cobrar += 1
        self.lbl_total_cobrar.configure(text=f"Total a descontar: {_moneda(item['a_descontar'])}")
        self.lbl_total_pagar.configure(text=f"Total a pagar: {_moneda(item['a_pagar'])}")
        self.txt_obs.delete("1.0", "end")
        if item.get("observaciones"):
            self.txt_obs.insert("1.0", item["observaciones"])
        self.combo_accion.set(item.get("accion") or "—")
        self.ent_id_pago.delete(0, "end")
        if item.get("id_pago"):
            self.ent_id_pago.insert(0, str(item["id_pago"]))
        self.btn_obs.configure(text="Guardar")
        posicion = self._visibles.index(indice) + 1 if indice in self._visibles else 0
        self.lbl_posicion.configure(text=f"{posicion} / {len(self._visibles)}")

    def _guardar_observacion(self):
        if self._actual is None:
            return
        texto = self.txt_obs.get("1.0", "end").strip()
        accion = "" if self.combo_accion.get() == "—" else self.combo_accion.get()
        id_pago = self.ent_id_pago.get().strip()
        resultado = self.master.netting_resultado
        try:
            en_registro = guardar_datos_paquete(resultado, self._resumen[self._actual], cargar_config(), texto, accion, id_pago)
        except PermissionError as exc:
            messagebox.showerror("No se pudo guardar", str(exc))
            return
        self.btn_obs.configure(text="✓ Guardado" + (" y registrado" if en_registro else ""))
        self.after(1800, lambda: self.btn_obs.winfo_exists() and self.btn_obs.configure(text="Guardar"))

    def _copiar_ab(self):
        if self._actual is None:
            return
        self.clipboard_clear()
        self.clipboard_append(str(self._resumen[self._actual]["ab_e1"]))
        self.lbl_ab.configure(text=self.lbl_ab.cget("text").replace("⧉", "✓ copiado"))
        self.after(1500, lambda: self._actual is not None and self._mostrar_paquete(self._actual))

    def ver_por_fecha(self):
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            return
        ventana = ctk.CTkToplevel(self)
        ventana.title("Documentos por fecha de pago")
        ventana.configure(fg_color=T.FONDO)
        ventana.geometry("640x420")
        ventana.transient(self.winfo_toplevel())
        ctk.CTkLabel(
            ventana, text="Para comparar con la PowerApp filtrada por fecha de pago (cantidad de liquidaciones a pagar).",
            font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, wraplength=600, justify="left",
        ).pack(anchor="w", padx=16, pady=(14, 6))
        marco, tabla = _tabla(ventana, ("Fecha de pago", "Docs 24 hs", "Docs 48 hs", "Paquetes", "A pagar"),
                              {"Fecha de pago": 120, "Docs 24 hs": 90, "Docs 48 hs": 90, "Paquetes": 80, "A pagar": 160},
                              alto=9, derecha=("Docs 24 hs", "Docs 48 hs", "Paquetes", "A pagar"))
        marco.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        total_24 = total_48 = 0
        for indice, dato in enumerate(resumen_por_fecha_de_pago(resultado)):
            total_24 += dato["docs_24"]
            total_48 += dato["docs_48"]
            tabla.insert("", "end", tags=("par" if indice % 2 == 0 else "impar",), values=(
                dato["fecha"].strftime("%d/%m/%Y") if dato["fecha"] else "Sin fecha",
                dato["docs_24"], dato["docs_48"], dato["paquetes"], _moneda(dato["total"])))
        ctk.CTkLabel(ventana, text=f"Total: {total_24} documentos en 24 hs y {total_48} en 48 hs.",
                     font=T.ETIQUETA, text_color=T.TEXTO).pack(anchor="w", padx=16)
        _boton(ventana, "Cerrar", ventana.destroy, tipo="secundario", ancho=120).pack(anchor="e", padx=16, pady=(4, 14))

    def ver_avisos(self):
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            return
        ventana = ctk.CTkToplevel(self)
        ventana.title("Avisos de la corrida")
        ventana.configure(fg_color=T.FONDO)
        ventana.geometry("820x520")
        ventana.transient(self.winfo_toplevel())
        caja = ctk.CTkTextbox(ventana, wrap="word", fg_color=T.SUPERFICIE, text_color=T.TEXTO_SUAVE, font=T.CUERPO)
        caja.pack(fill="both", expand=True, padx=16, pady=16)
        texto = []
        if resultado.avisos.revisar:
            texto.append("PARA REVISAR\n")
            texto += [f"•  {a}\n" for a in resultado.avisos.revisar]
            texto.append("\n")
        texto.append("INFORMACIÓN\n")
        texto += [f"•  {a}\n" for a in resultado.avisos.info] or ["•  Sin novedades.\n"]
        caja.insert("end", "".join(texto))
        caja.configure(state="disabled")
        _boton(ventana, "Cerrar", ventana.destroy, tipo="secundario", ancho=120).pack(anchor="e", padx=16, pady=(0, 16))


# ====================================================================== salida

class PantallaNettingSalida(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.config = cargar_config()
        guardada = self.config.get("rutas", {}).get("salida") or ""
        self.carpeta = guardada if guardada and Path(guardada).exists() else str(APP_DATA_PATH)
        self._crear()

    def _crear(self):
        _encabezado(self, "Dar salida", "Reparte las propuestas entre los analistas y genera Propuestas_Netting.xlsx "
                                        "con las hojas Propuestas_24 y Propuestas_48 (mismas columnas que la macro).")

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(side="bottom", fill="x", padx=20, pady=(0, 16))
        self.btn_generar = _boton(acciones, "Generar archivo", self.generar, ancho=220)
        self.btn_generar.pack(side="left")
        self.btn_abrir = _boton(acciones, "Abrir archivo", self.abrir_archivo, tipo="secundario", ancho=150)
        self.btn_carpeta = _boton(acciones, "Abrir carpeta", lambda: self._abrir(self.carpeta), tipo="secundario", ancho=150)
        self.estado = ctk.CTkLabel(acciones, text="", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO, anchor="w",
                                   justify="left", wraplength=560)
        self.estado.pack(side="left", padx=16)

        panel = _panel(self)
        panel.pack(fill="x", padx=20, pady=(0, 12))
        panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="Cantidad de analistas", font=T.ETIQUETA, text_color=T.TEXTO).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        self.ent_analistas = ctk.CTkEntry(panel, width=80, fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
        self.ent_analistas.insert(0, str(self.config.get("cantidad_analistas", 1)))
        self.ent_analistas.grid(row=0, column=1, sticky="w", pady=(18, 6))
        self.ent_analistas.bind("<KeyRelease>", lambda _e: self._previsualizar())

        ctk.CTkLabel(panel, text="Carpeta de destino", font=T.ETIQUETA, text_color=T.TEXTO).grid(
            row=1, column=0, sticky="w", padx=18, pady=(6, 18))
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.grid(row=1, column=1, sticky="ew", pady=(6, 18), padx=(0, 18))
        self.lbl_carpeta = ctk.CTkLabel(fila, text=self.carpeta, font=T.CUERPO_CHICO, text_color=T.TEXTO_SUAVE, anchor="w")
        self.lbl_carpeta.pack(side="left")
        _boton(fila, "Cambiar…", self.elegir_carpeta, tipo="secundario", ancho=110, alto=34).pack(side="left", padx=12)

        previa = _panel(self)
        previa.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        ctk.CTkLabel(previa, text="Reparto por analista", font=T.SUBTITULO, text_color=T.TEXTO).pack(anchor="w", padx=18, pady=(14, 0))
        ctk.CTkLabel(
            previa, text="Igual que la macro: propuestas enteras, en orden, en bloques de (propuestas ÷ analistas).",
            font=T.NOTA, text_color=T.TEXTO_TENUE,
        ).pack(anchor="w", padx=18, pady=(0, 8))
        marco, self.tabla = _tabla(previa, ("Grupo", "Propuestas 24 hs", "Propuestas 48 hs", "Total a pagar"),
                                   {"Grupo": 100, "Propuestas 24 hs": 160, "Propuestas 48 hs": 160, "Total a pagar": 200},
                                   alto=6, derecha=("Propuestas 24 hs", "Propuestas 48 hs", "Total a pagar"))
        marco.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.vacio = crear_estado_vacio(
            self, "Todavía no hay propuestas armadas", "Armá las propuestas en el paso 1 para generar la salida.")

    def al_mostrar(self):
        resultado = getattr(self.master, "netting_resultado", None)
        alternar_estado_vacio(self.vacio, resultado is None)
        if resultado is None:
            return
        salida = getattr(self.master, "netting_salida", None)
        if not salida:
            self.estado.configure(
                text=f"Al generar se guarda {resultado.numero_final} como último N° de propuesta.",
                text_color=T.TEXTO_SECUNDARIO)
            self.btn_abrir.pack_forget()
            self.btn_carpeta.pack_forget()
        self.ent_analistas.delete(0, "end")
        self.ent_analistas.insert(0, str(resultado.cantidad_analistas))
        self._previsualizar()

    def _cantidad(self):
        try:
            cantidad = int(self.ent_analistas.get().strip())
        except ValueError:
            return None
        return cantidad if cantidad >= 1 else None

    def _previsualizar(self):
        resultado = getattr(self.master, "netting_resultado", None)
        self.tabla.delete(*self.tabla.get_children())
        cantidad = self._cantidad()
        if resultado is None or cantidad is None:
            return
        repartir_grupos(resultado, cantidad)
        grupos = {}
        for ventana, filas in (("24", resultado.propuestas_24), ("48", resultado.propuestas_48)):
            for item in resumen_propuestas(filas):
                g = grupos.setdefault(item["grupo"] if item["grupo"] != "" else "Sin grupo", {"24": 0, "48": 0, "pagar": 0.0})
                g[ventana] += 1
                g["pagar"] += item["a_pagar"]
        for indice, (grupo, datos) in enumerate(sorted(grupos.items(), key=lambda kv: (isinstance(kv[0], str), kv[0]))):
            self.tabla.insert("", "end", tags=("par" if indice % 2 == 0 else "impar",),
                              values=(grupo, datos["24"], datos["48"], _moneda(datos["pagar"])))

    def elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Carpeta para Propuestas_Netting", initialdir=self.carpeta)
        if carpeta:
            self.carpeta = carpeta
            self.lbl_carpeta.configure(text=carpeta)

    def generar(self):
        resultado = getattr(self.master, "netting_resultado", None)
        if resultado is None:
            return
        cantidad = self._cantidad()
        if cantidad is None:
            messagebox.showwarning("Cantidad de analistas", "Ingresá un número entero mayor que 0.")
            return
        destino = Path(self.carpeta) / NOMBRE_SALIDA
        if destino.exists() and not messagebox.askyesno(
            "Reemplazar archivo", f"Ya existe {destino}.\n¿Querés reemplazarlo?"
        ):
            return
        config = cargar_config()
        try:
            ruta = generar_salida(resultado, cantidad, self.carpeta, config)
        except PermissionError as exc:
            messagebox.showerror("No se pudo guardar", str(exc))
            return
        except Exception as exc:
            logger.exception("Error generando la salida de netting")
            messagebox.showerror("No se pudo generar la salida", str(exc))
            return
        self.master.netting_salida = str(ruta)
        self.estado.configure(
            text=f"Listo: {ruta}. Los documentos quedaron registrados en Netting_Propuestos.xlsx (data).",
            text_color=T.OK,
        )
        self.btn_abrir.pack(side="left", padx=(12, 0), after=self.btn_generar)
        self.btn_carpeta.pack(side="left", padx=(8, 0), after=self.btn_abrir)
        self._previsualizar()

    def abrir_archivo(self):
        salida = getattr(self.master, "netting_salida", None)
        if salida:
            self._abrir(salida)

    @staticmethod
    def _abrir(ruta):
        if hasattr(os, "startfile"):
            try:
                os.startfile(str(ruta))
            except OSError as exc:
                messagebox.showerror("No se pudo abrir", str(exc))
