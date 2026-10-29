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
from netting.servicio import NOMBRE_SALIDA, ejecutar_netting, generar_salida
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
            self.paso_armar.mostrar("siguiente", "Histórico, 077, 090 y compensas de ventas. Elegís la fecha de proceso.", "Empezar →")
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
    ("ventas", "Compensas de ventas (opcional)", "Copia local en data: Compensas*.xlsx, hoja «Compensas Pendientes»"),
)
PATRON_VENTAS = "Compensas*"


def buscar_compensas_en_data():
    """Archivo de compensas más reciente en la carpeta data (Compensas*.xlsx / .xlsm / .xlsb / .xls)."""
    carpeta = Path(APP_DATA_PATH)
    if not carpeta.exists():
        return ""
    candidatos = [
        p for p in carpeta.glob(PATRON_VENTAS)
        if p.is_file() and p.suffix.lower() in (".xlsx", ".xlsm", ".xlsb", ".xls") and not p.name.startswith("~$")
    ]
    if not candidatos:
        return ""
    return str(max(candidatos, key=lambda p: p.stat().st_mtime))


class PantallaNettingCarga(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.config = cargar_config()
        self.rutas = {clave: self.config.get("rutas", {}).get(clave, "") for clave, *_ in ARCHIVOS}
        self.rutas = {k: (v if v and Path(v).exists() else "") for k, v in self.rutas.items()}
        # Compensas de ventas: siempre se toma la copia local de data (la del día), no la de OneDrive.
        self.rutas["ventas"] = buscar_compensas_en_data()
        self._sin_ventas = False  # el usuario eligió correr sin compensas
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
            if clave == "ventas":
                _boton(botones, "Quitar", self.quitar_ventas, tipo="borde", ancho=70, alto=32).pack(side="left", padx=(0, 6))
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

    def al_mostrar(self):
        # Después de dar salida, el último N° guardado pasa a ser el punto de partida de la próxima corrida.
        if not self._procesando and not self._sin_ventas and not self.rutas.get("ventas"):
            self.rutas["ventas"] = buscar_compensas_en_data()
            self._refrescar_rutas()
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
            elif clave == "ventas" and self._sin_ventas:
                etiqueta.configure(text="Sin compensas de ventas (quitado a mano).", text_color=T.AVISO)
            elif clave == "ventas":
                etiqueta.configure(
                    text=f"No hay ningún Compensas*.xlsx en {APP_DATA_PATH}. Se arma sin compensas de ventas.",
                    text_color=T.AVISO,
                )
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
            if clave == "ventas":
                self._sin_ventas = False
            self._refrescar_rutas()

    def quitar_ventas(self):
        self.rutas["ventas"] = ""
        self._sin_ventas = True
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
        faltan = [titulo for clave, titulo, _ in ARCHIVOS if clave != "ventas" and not self.rutas.get(clave)]
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

        self.config["rutas"].update({k: v for k, v in self.rutas.items() if k != "ventas"})
        self.config["ultimo_numero_propuesta"] = numero
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

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.ventana = "24"
        self._resumen = []
        self._crear()

    def _crear(self):
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=0, pady=0)
        izquierda = ctk.CTkFrame(cabecera, fg_color="transparent")
        izquierda.pack(side="left")
        _encabezado(izquierda, "Revisar propuestas", "")

        controles = ctk.CTkFrame(cabecera, fg_color="transparent")
        controles.pack(side="right", padx=20, pady=(24, 0))
        self.btn_avisos = _boton(controles, "Avisos", self.ver_avisos, tipo="borde", ancho=120, alto=34)
        self.btn_avisos.pack(side="right", padx=(8, 0))
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
        self.ent_buscar = ctk.CTkEntry(controles, width=240, placeholder_text="Buscar beneficiario, AB o N°…",
                                       fg_color=T.SUPERFICIE, border_color=T.BORDE_FUERTE)
        self.ent_buscar.pack(side="right")
        self.ent_buscar.bind("<KeyRelease>", lambda _e: self._llenar_lista())

        self.lbl_totales = ctk.CTkLabel(self, text="", font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_totales.pack(anchor="w", padx=20, pady=(0, 6))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(0, weight=5)
        cuerpo.grid_rowconfigure(1, weight=6)

        # --- Lista de propuestas
        lista = _panel(cuerpo)
        lista.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        columnas = ("N°", "Tipo de beneficiario", "AB", "Beneficiario", "Docs", "A pagar", "A descontar", "Neto", "Grupo")
        anchos = {"N°": 70, "Tipo de beneficiario": 170, "AB": 90, "Beneficiario": 240, "Docs": 50,
                  "A pagar": 130, "A descontar": 130, "Neto": 130, "Grupo": 60}
        marco, self.tabla = _tabla(lista, columnas, anchos, alto=7,
                                   derecha=("A pagar", "A descontar", "Neto", "Docs"), estirar=("Beneficiario",))
        marco.pack(fill="both", expand=True, padx=12, pady=12)
        self.tabla.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalle())

        # --- Detalle de la propuesta seleccionada
        detalle = _panel(cuerpo)
        detalle.grid(row=1, column=0, sticky="nsew")
        self.lbl_detalle = ctk.CTkLabel(detalle, text="Elegí una propuesta para ver el detalle.", font=T.SUBTITULO,
                                        text_color=T.TEXTO, anchor="w", justify="left")
        self.lbl_detalle.pack(anchor="w", padx=16, pady=(12, 2))
        self.lbl_sub = ctk.CTkLabel(detalle, text="", font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_sub.pack(anchor="w", padx=16, pady=(0, 6))

        tablas = ctk.CTkFrame(detalle, fg_color="transparent")
        tablas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        tablas.grid_columnconfigure(0, weight=1, uniform="det")
        tablas.grid_columnconfigure(1, weight=1, uniform="det")
        tablas.grid_rowconfigure(1, weight=1)

        self.lbl_pagar = ctk.CTkLabel(tablas, text="Se paga", font=T.ETIQUETA, text_color=T.OK, anchor="w")
        self.lbl_pagar.grid(row=0, column=0, sticky="w", padx=4)
        self.lbl_descontar = ctk.CTkLabel(tablas, text="Se descuenta", font=T.ETIQUETA, text_color=T.ERROR, anchor="w")
        self.lbl_descontar.grid(row=0, column=1, sticky="w", padx=(12, 4))

        col_pagar = ("Documento", "Tipo", "Descripción", "Vendedor", "Total")
        marco_p, self.tabla_pagar = _tabla(
            tablas, col_pagar, {"Documento": 92, "Tipo": 45, "Descripción": 140, "Vendedor": 125, "Total": 115},
            alto=5, derecha=("Total",), estirar=("Descripción", "Vendedor"))
        marco_p.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        col_desc = ("Documento", "Tipo", "Detalle", "Fecha", "Total")
        marco_d, self.tabla_descontar = _tabla(
            tablas, col_desc, {"Documento": 92, "Tipo": 45, "Detalle": 160, "Fecha": 90, "Total": 115},
            alto=5, derecha=("Total",), estirar=("Detalle",))
        marco_d.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        self.vacio = crear_estado_vacio(
            self, "Todavía no hay propuestas armadas", "Armá las propuestas en el paso 1 para revisarlas acá.")

    def al_mostrar(self):
        resultado = getattr(self.master, "netting_resultado", None)
        alternar_estado_vacio(self.vacio, resultado is None)
        if resultado is None:
            return
        cantidad = len(resultado.avisos.revisar)
        self.btn_avisos.configure(text=f"⚠  Avisos ({cantidad})" if cantidad else "Avisos",
                                  text_color=T.AVISO if cantidad else T.TEXTO_SECUNDARIO)
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
            text=(f"{len(self._resumen)} propuestas · A pagar {_moneda(pagar)} · A descontar {_moneda(descontar)} · "
                  f"Neto {_moneda(pagar + descontar)}   ·   Fecha de proceso {resultado.fecha_proceso:%d/%m/%Y}")
        )
        self._llenar_lista()

    def _llenar_lista(self):
        self.tabla.delete(*self.tabla.get_children())
        filtro = self.ent_buscar.get().strip().casefold()
        for indice, item in enumerate(self._resumen):
            texto = f"{item['n_propuesta']} {item['ab_benef']} {item['benef']} {item['tipo_benef']}".casefold()
            if filtro and filtro not in texto:
                continue
            etiqueta = "negativo" if item["neto"] < 0 else ("par" if indice % 2 == 0 else "impar")
            self.tabla.insert("", "end", iid=str(indice), tags=(etiqueta,), values=(
                item["n_propuesta"], item["tipo_benef"], item["ab_benef"], item["benef"], item["documentos"],
                _moneda(item["a_pagar"]), _moneda(item["a_descontar"]), _moneda(item["neto"]), item["grupo"],
            ))
        hijos = self.tabla.get_children()
        if hijos:
            self.tabla.selection_set(hijos[0])
            self.tabla.focus(hijos[0])
        else:
            self._limpiar_detalle()

    def _limpiar_detalle(self):
        self.lbl_detalle.configure(text="Elegí una propuesta para ver el detalle.")
        self.lbl_sub.configure(text="")
        self.tabla_pagar.delete(*self.tabla_pagar.get_children())
        self.tabla_descontar.delete(*self.tabla_descontar.get_children())

    def _mostrar_detalle(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        item = self._resumen[int(seleccion[0])]
        self.lbl_detalle.configure(text=f"Propuesta {item['n_propuesta']} · {item['benef']}")
        primera = item["filas"][0]
        corredor = primera["corredor"] if primera["corredor"] not in ("", None) else "directo"
        self.lbl_sub.configure(
            text=(f"{item['tipo_benef']} · AB {item['ab_benef']} · Corredor: {corredor} · "
                  f"Neto {_moneda(item['neto'])}" + (f" · Grupo {item['grupo']}" if item["grupo"] != "" else ""))
        )
        self.tabla_pagar.delete(*self.tabla_pagar.get_children())
        self.tabla_descontar.delete(*self.tabla_descontar.get_children())
        n_pagar = n_desc = 0
        for fila in item["filas"]:
            if fila["tipo"] == "PAGAR":
                self.tabla_pagar.insert("", "end", tags=("par" if n_pagar % 2 == 0 else "impar",), values=(
                    fila["doc"], fila["tipo_doc"], fila["desc"], fila["vendedor"], _moneda(fila["total"])))
                n_pagar += 1
            else:
                self.tabla_descontar.insert("", "end", tags=("par" if n_desc % 2 == 0 else "impar",), values=(
                    fila["doc"], fila["tipo_doc"], fila["desc"] or fila.get("origen", ""), _fecha(fila["fecha_emision"]),
                    _moneda(fila["total"])))
                n_desc += 1
        self.lbl_pagar.configure(text=f"Se paga · {n_pagar} doc. · {_moneda(item['a_pagar'])}")
        self.lbl_descontar.configure(text=f"Se descuenta · {n_desc} doc. · {_moneda(item['a_descontar'])}")

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
        asignar_grupos(resultado.propuestas_24, cantidad, "24")
        asignar_grupos(resultado.propuestas_48, cantidad, "48")
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
        self.estado.configure(text=f"Listo: {ruta}", text_color=T.OK)
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
