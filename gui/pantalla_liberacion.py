"""Pantallas de Liberación: menú, control de pagos, revisión con Output E1 y limpieza de pagadas."""

import logging
import queue
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui import tema as T
from gui.pantalla_inicio import TarjetaPaso, alternar_estado_vacio, crear_estado_vacio
from gui.pantalla_netting import _boton, _fecha, _moneda, _panel, _tabla
from liberacion import cargas
from liberacion.config import cargar_config, guardar_config
from liberacion.limpieza import limpiar_pagadas
from liberacion.motor import (
    A_LIBERAR_EN_E1, COMPENSA_LIBERAR, COMPENSA_MANUAL, CONTROLES, LIBERACION_MANUAL, LIBERAR, MANUAL,
    NO_SE_ENCONTRO, ya_liberado,
)
from liberacion.salida import NOMBRE_OUTPUT_E1
from liberacion.servicio import ejecutar_control, generar_output_e1, liberacion_manual
from services.auditoria import APP_DATA_PATH

logger = logging.getLogger(__name__)

COLOR_CONTROL = {
    LIBERAR: (T.OK, T.OK_FONDO),
    LIBERACION_MANUAL: (T.OK, T.OK_FONDO),
    COMPENSA_LIBERAR: (T.INFO, T.INFO_FONDO),
    MANUAL: (T.ERROR, T.ERROR_FONDO),
    COMPENSA_MANUAL: (T.ERROR, T.ERROR_FONDO),
    NO_SE_ENCONTRO: (T.AVISO, T.AVISO_FONDO),
}
FILTROS = ["Todos", LIBERAR, MANUAL, COMPENSA_LIBERAR, COMPENSA_MANUAL, LIBERACION_MANUAL, NO_SE_ENCONTRO,
           "Ya liberados"]
# Títulos cortos para la tabla (el detalle completo de cada error se muestra abajo)
COLUMNAS_CONTROL = ("Montos", "Tipo doc", "Cronología", "Por liberar", "Devengados", "Permuta")
TEXTO_CORTO = {
    "OK": "OK", "OK-S/PARA LIBERAR": "OK (K en 0)", "": "—",
    "MONTO - MENOR": "✕ Menor", "MONTO - MAYOR": "✕ Mayor", "NO SE ENCONTRO DOCUMENTO": "✕ No está",
    "ERROR- FALTA DOC L#": "✕ Falta L#", "ERROR TIPO DE DOCUMENTO": "✕ Tipo", "ERROR CRONOLOGIA": "✕ Error",
    "ERROR-MONTO POR LIBERAR": "✕ K con saldo", "ERROR DOC DEVENGADOS": "✕ Devengado",
    "ERROR-DOC NO ASIG/PROPUESTA": "✕ No asignado", "ERROR PERMUTA": "✕ Sin permuta",
}
HISTORICO_POR_DEFECTO = Path(APP_DATA_PATH) / "Historico_Documentos_Controlados.xlsx"
PAGADOS_POR_DEFECTO = Path(APP_DATA_PATH) / "historico_pagados.xlsx"


def _encabezado(master, titulo, descripcion):
    ctk.CTkLabel(master, text="LIBERACIÓN · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(
        anchor="w", padx=18, pady=(6, 0))
    ctk.CTkLabel(master, text=titulo, font=T.TITULO_PANTALLA, text_color=T.TEXTO).pack(anchor="w", padx=18)
    if descripcion:
        ctk.CTkLabel(master, text=descripcion, font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, anchor="w",
                     justify="left", wraplength=1000).pack(anchor="w", padx=18, pady=(0, 6))


def _combo(master, valores, comando=None, ancho=140):
    return ctk.CTkOptionMenu(
        master, values=valores, width=ancho, height=30, command=comando,
        fg_color=T.SECUNDARIO, button_color=T.SECUNDARIO_HOVER, button_hover_color=T.BORDE_FUERTE,
        text_color=T.TEXTO_SOBRE_SECUNDARIO, dropdown_fg_color=T.SUPERFICIE, dropdown_text_color=T.TEXTO,
        dropdown_hover_color=T.SUPERFICIE_ELEVADA, font=T.ETIQUETA_CHICA,
    )


def _entrada(master, ancho=120, texto=""):
    entrada = ctk.CTkEntry(master, width=ancho, fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
    if texto:
        entrada.insert(0, texto)
    return entrada


def _leer_fecha(texto, nombre):
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{nombre}: tiene que tener el formato dd/mm/aaaa.")


EXTENSIONES_REPORTE = (".xlsx", ".xlsb", ".xlsm", ".xls", ".csv")


def buscar_en_data(prefijo, con=None, sin=()):
    """El archivo más nuevo de la carpeta data que empieza con el prefijo (como CONTROLAR con el 044/090/077).

    con: texto que el nombre tiene que tener; sin: textos que no tiene que tener (en minúsculas)."""
    carpeta = Path(APP_DATA_PATH)
    if not carpeta.exists():
        return ""
    candidatos = []
    for archivo in carpeta.iterdir():
        nombre = archivo.name.lower()
        if (not archivo.is_file() or nombre.startswith("~$") or archivo.suffix.lower() not in EXTENSIONES_REPORTE
                or not nombre.startswith(prefijo) or (con and con not in nombre) or any(t in nombre for t in sin)):
            continue
        candidatos.append(archivo)
    if not candidatos:
        return ""
    return str(max(candidatos, key=lambda a: a.stat().st_mtime))


def _texto_ruta(etiqueta, ruta, ayuda_vacia="Sin elegir"):
    if ruta and Path(ruta).exists():
        try:
            modificado = datetime.fromtimestamp(Path(ruta).stat().st_mtime)
            cuando = f"   ·   modificado {modificado:%d/%m/%Y %H:%M}"
        except OSError:
            cuando = ""
        etiqueta.configure(text=f"✓  {ruta}{cuando}", text_color=T.OK)
    elif ruta:
        etiqueta.configure(text=f"No existe todavía: {ruta}", text_color=T.AVISO)
    else:
        etiqueta.configure(text=ayuda_vacia, text_color=T.TEXTO_TENUE)


class _ConTarea:
    """Corre una función en un hilo y trae los mensajes a la interfaz por una cola."""

    def _iniciar_tarea(self, funcion, al_terminar, al_fallar):
        self._cola = queue.Queue()

        def tarea():
            try:
                self._cola.put(("ok", funcion(lambda t: self._cola.put(("log", t)))))
            except (cargas.ErrorDeCarga, ValueError, PermissionError) as exc:
                self._cola.put(("error", str(exc)))
            except Exception as exc:  # pragma: no cover - errores inesperados
                logger.exception("Error en Liberación")
                self._cola.put(("error", f"Error inesperado: {exc}"))

        threading.Thread(target=tarea, daemon=True).start()
        self.after(100, lambda: self._revisar_cola(al_terminar, al_fallar))

    def _revisar_cola(self, al_terminar, al_fallar):
        try:
            while True:
                tipo, valor = self._cola.get_nowait()
                if tipo == "log":
                    self._agregar_log(valor)
                elif tipo == "ok":
                    al_terminar(valor)
                    return
                else:
                    al_fallar(valor)
                    return
        except queue.Empty:
            pass
        self.after(150, lambda: self._revisar_cola(al_terminar, al_fallar))

    def _crear_log(self, alto=64):
        self.frame_log = ctk.CTkFrame(self, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=14, border_width=1,
                                      border_color=T.BORDE)
        self.frame_log.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(self.frame_log, text="Actividad", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO).pack(
            anchor="w", padx=12, pady=(8, 0))
        self.log = ctk.CTkTextbox(self.frame_log, height=alto, state="disabled", wrap="word",
                                  fg_color=T.SUPERFICIE_HUNDIDA, text_color=T.TEXTO_SUAVE)
        self.log.pack(fill="x", padx=12, pady=(4, 10))
        self.barra = ctk.CTkProgressBar(self, mode="indeterminate", height=8, progress_color=T.EN_CURSO)

    def _agregar_log(self, mensaje):
        self.log.configure(state="normal")
        self.log.insert("end", f"{datetime.now():%H:%M:%S} - {mensaje}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _barra(self, activa):
        if activa:
            self.barra.pack(side="bottom", fill="x", padx=20, pady=(0, 8), before=self.frame_log)
            self.barra.start()
        else:
            self.barra.stop()
            self.barra.pack_forget()


# ====================================================================== menú

class MenuLiberacion(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=70, pady=(40, 0))
        ctk.CTkLabel(contenido, text="LIBERACIÓN · GLUCOVIL", font=T.ETIQUETA_CHICA, text_color=T.MARCA).pack(anchor="w")
        ctk.CTkLabel(contenido, text="Liberación de pagos", font=(T.FUENTE, 30, "bold"), text_color=T.TEXTO).pack(anchor="w")
        ctk.CTkLabel(
            contenido, text="Controla los netting generados en E1 contra las propuestas, arma el Output E1 y pasa "
                            "las liquidaciones pagadas al Histórico de pagados.",
            font=T.CUERPO, text_color=T.TEXTO_SECUNDARIO, wraplength=900, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(contenido, text="Proceso de liberación", font=T.SUBTITULO, text_color=T.TEXTO).pack(
            anchor="w", pady=(32, 12))
        pasos = ctk.CTkFrame(contenido, fg_color="transparent")
        pasos.pack(fill="x")
        for columna in range(3):
            pasos.grid_columnconfigure(columna, weight=1, uniform="pasos")
        self.paso_control = TarjetaPaso(pasos, 1, "Controlar pagos", lambda: master.mostrar_pantalla("liberacion_control"))
        self.paso_revisar = TarjetaPaso(pasos, 2, "Revisar y liberar", lambda: master.mostrar_pantalla("liberacion_revision"))
        self.paso_limpiar = TarjetaPaso(pasos, 3, "Limpiar pagadas", lambda: master.mostrar_pantalla("liberacion_limpieza"))
        for columna, tarjeta in enumerate((self.paso_control, self.paso_revisar, self.paso_limpiar)):
            tarjeta.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 8, 0 if columna == 2 else 8))
        ctk.CTkLabel(
            contenido,
            text=("Replica Macro_Controles_Netting_y_Compensa.xlsb. Los IDs de pago no se cargan a mano: se buscan "
                  "en el 020 a partir de los documentos de cada propuesta y quedan guardados en el registro de Netting."),
            font=T.NOTA, text_color=T.TEXTO_TENUE, wraplength=900, justify="left",
        ).pack(anchor="w", pady=(24, 0))
        self.actualizar_estado()

    def actualizar_estado(self):
        resultado = getattr(self.master, "liberacion_resultado", None)
        self.paso_limpiar.mostrar(
            "disponible", "Con el 020 bajado de nuevo: mueve lo pagado del Histórico de controlados a pagados.", "Abrir →")
        if resultado is None:
            self.paso_control.mostrar("siguiente", "Propuestas de netting, reportes 020 y 067.", "Empezar →")
            self.paso_revisar.mostrar("bloqueado", "Paquete por paquete: controles, liberación manual y Output E1.",
                                      "Primero controlá los pagos")
            return
        e = resultado.estadisticas()
        self.paso_control.mostrar("hecho", f"Controlado a las {resultado.generado:%H:%M}.", "Volver a controlar")
        salida = getattr(self.master, "liberacion_output", None)
        detalle = f"{e['visibles']} paquetes, {e['a_liberar']} para liberar."
        if salida:
            self.paso_revisar.mostrar("hecho", detalle + f" Output: {Path(salida).name}", "Ver →")
        else:
            self.paso_revisar.mostrar("siguiente", detalle, "Revisar →")


# ====================================================================== controlar pagos

class PantallaLiberacionControl(_ConTarea, ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.config = cargar_config()
        rutas = self.config.get("rutas", {})
        self.rutas = {clave: (rutas.get(clave) if rutas.get(clave) and Path(rutas.get(clave)).exists() else "")
                      for clave in ("020", "067", "propuestas")}
        self._elegidos = set()       # los que el usuario eligió a mano en esta sesión no se pisan
        self._buscar_reportes()
        self.ventana = "24"
        self._corridas = []
        self._procesando = False
        self._crear()

    def _crear(self):
        _encabezado(self, "Controlar pagos", "Elegí qué propuestas controlar y los reportes 020 y 067 bajados después "
                                             "de generar los netting en E1.")
        self._crear_log()
        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        self.btn_controlar = _boton(acciones, "Controlar pagos", self.controlar, ancho=220)
        self.btn_controlar.pack(side="left")
        self.btn_revisar = _boton(acciones, "Revisar y liberar →", lambda: self.master.mostrar_pantalla("liberacion_revision"),
                                  tipo="secundario", ancho=200)
        self.estado = ctk.CTkLabel(acciones, text="", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO, anchor="w",
                                   justify="left", wraplength=640)
        self.estado.pack(side="left", padx=16)

        # --- Propuestas
        fuente = _panel(self)
        fuente.pack(fill="x", padx=20, pady=(0, 12))
        fuente.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(fuente, text="Propuestas", font=T.SUBTITULO, text_color=T.TEXTO).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(10, 4))
        self.var_fuente = ctk.StringVar(value="registro")
        opciones = dict(variable=self.var_fuente, command=self._cambiar_fuente, font=T.ETIQUETA, text_color=T.TEXTO,
                        fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, border_color=T.BORDE_FUERTE)
        ctk.CTkRadioButton(fuente, text="Corrida de netting de la app", value="registro", **opciones).grid(
            row=1, column=0, sticky="w", padx=18, pady=4)
        self.combo_corrida = _combo(fuente, ["—"], comando=lambda _v: self._actualizar_ventanas(), ancho=330)
        self.combo_corrida.grid(row=1, column=1, sticky="w", padx=(0, 12))
        self.lbl_corrida = ctk.CTkLabel(fuente, text="", font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w")
        self.lbl_corrida.grid(row=1, column=2, sticky="w")
        ctk.CTkRadioButton(fuente, text="Archivo Propuestas_Netting", value="archivo", **opciones).grid(
            row=2, column=0, sticky="w", padx=18, pady=4)
        self.lbl_archivo = ctk.CTkLabel(fuente, text="", font=T.CUERPO_CHICO, anchor="w", justify="left", wraplength=520)
        self.lbl_archivo.grid(row=2, column=1, columnspan=2, sticky="w")
        self.btn_archivo = _boton(fuente, "Elegir…", lambda: self.elegir("propuestas"), tipo="secundario", ancho=110, alto=32)
        self.btn_archivo.grid(row=2, column=3, sticky="e", padx=18)

        fila_ventana = ctk.CTkFrame(fuente, fg_color="transparent")
        fila_ventana.grid(row=3, column=0, columnspan=4, sticky="w", padx=18, pady=(6, 12))
        ctk.CTkLabel(fila_ventana, text="Ventana", font=T.ETIQUETA, text_color=T.TEXTO).pack(side="left", padx=(0, 10))
        self.botones_ventana = {}
        for ventana in ("24", "48"):
            boton = ctk.CTkButton(fila_ventana, text=f"{ventana} hs", width=80, height=32, corner_radius=T.RADIO_BOTON,
                                  font=T.ETIQUETA, command=lambda v=ventana: self._elegir_ventana(v))
            boton.pack(side="left", padx=(0, 4))
            self.botones_ventana[ventana] = boton
        ctk.CTkLabel(fila_ventana, text="Como la macro: se controla una ventana por vez.", font=T.NOTA,
                     text_color=T.TEXTO_TENUE).pack(side="left", padx=12)
        self._marcar_ventana()

        # --- Reportes
        panel = _panel(self)
        panel.pack(fill="x", padx=20, pady=(0, 12))
        panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(panel, text="Reportes de E1", font=T.SUBTITULO, text_color=T.TEXTO).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(10, 2))
        self.lbl_rutas = {}
        for fila, (clave, titulo, ayuda) in enumerate((
                ("020", "Reporte 020", "Pagos y Cobros · se toma de data"),
                ("067", "Reporte 067", "Vouchers pendientes · se toma de data"),
        ), start=1):
            textos = ctk.CTkFrame(panel, fg_color="transparent")
            textos.grid(row=fila, column=0, sticky="nw", padx=(18, 12), pady=2)
            ctk.CTkLabel(textos, text=titulo, font=T.ETIQUETA, text_color=T.TEXTO, anchor="w", height=20).pack(anchor="w")
            ctk.CTkLabel(textos, text=ayuda, font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w", height=16).pack(anchor="w")
            etiqueta = ctk.CTkLabel(panel, text="", font=T.CUERPO_CHICO, anchor="w", justify="left", wraplength=620)
            etiqueta.grid(row=fila, column=1, sticky="w", pady=2)
            _boton(panel, "Elegir…", lambda c=clave: self.elegir(c), tipo="secundario", ancho=110, alto=32).grid(
                row=fila, column=2, sticky="e", padx=18, pady=2)
            self.lbl_rutas[clave] = etiqueta
        ctk.CTkFrame(panel, fg_color="transparent", height=6, width=10).grid(row=3, column=2)
        self._refrescar_rutas()

    # ------------------------------------------------------------------ datos
    def _buscar_reportes(self):
        """020 y 067 del día: el más nuevo de la carpeta data (el 020 para limpiar no cuenta)."""
        for clave, encontrado in (("020", buscar_en_data("020", sin=("limpiar",))), ("067", buscar_en_data("067"))):
            if clave not in self._elegidos and encontrado:
                self.rutas[clave] = encontrado

    def al_mostrar(self):
        if self._procesando:
            return
        self._buscar_reportes()
        try:
            self._corridas = cargas.listar_corridas(cargas.ruta_registro_por_defecto())
        except Exception:
            logger.exception("No se pudo leer el registro de Netting")
            self._corridas = []
        textos = [self._texto_corrida(c) for c in self._corridas] or ["No hay corridas pendientes"]
        actual = self.combo_corrida.get()
        self.combo_corrida.configure(values=textos)
        self.combo_corrida.set(actual if actual in textos else textos[0])
        if not self._corridas and self.var_fuente.get() == "registro" and self.rutas.get("propuestas"):
            self.var_fuente.set("archivo")
        self._cambiar_fuente()

    @staticmethod
    def _texto_corrida(corrida):
        ventanas = "  ·  ".join(f"{v} hs: {n}" for v, n in sorted(corrida["ventanas"].items()))
        return f"{corrida['generado']}   ({ventanas})"

    def _corrida_elegida(self):
        texto = self.combo_corrida.get()
        return next((c for c in self._corridas if self._texto_corrida(c) == texto), None)

    def _actualizar_ventanas(self):
        corrida = self._corrida_elegida()
        if corrida is None:
            self.lbl_corrida.configure(text="Primero hay que dar salida a un netting en la app." if not self._corridas else "")
            return
        self.lbl_corrida.configure(text=f"Fecha de proceso {corrida['fecha_proceso']}. Solo documentos sin liberar.")
        if self.ventana not in corrida["ventanas"] and corrida["ventanas"]:
            self._elegir_ventana(sorted(corrida["ventanas"])[0])

    def _cambiar_fuente(self):
        registro = self.var_fuente.get() == "registro"
        self.combo_corrida.configure(state="normal" if registro and self._corridas else "disabled")
        self.btn_archivo.configure(state="disabled" if registro else "normal")
        self._actualizar_ventanas()
        self._refrescar_rutas()

    def _elegir_ventana(self, ventana):
        self.ventana = ventana
        self._marcar_ventana()

    def _marcar_ventana(self):
        for ventana, boton in self.botones_ventana.items():
            if ventana == self.ventana:
                boton.configure(fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER, text_color=T.TEXTO_SOBRE_COLOR)
            else:
                boton.configure(fg_color=T.SECUNDARIO, hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO)

    def _refrescar_rutas(self):
        for clave, etiqueta in self.lbl_rutas.items():
            _texto_ruta(etiqueta, self.rutas.get(clave))
        if self.var_fuente.get() == "archivo":
            _texto_ruta(self.lbl_archivo, self.rutas.get("propuestas"))
        else:
            self.lbl_archivo.configure(text="Propuestas_Netting.xlsx (de la app o de la macro)", text_color=T.TEXTO_TENUE)

    def elegir(self, clave):
        actual = self.rutas.get(clave) or ""
        carpeta = str(Path(actual).parent) if actual else str(APP_DATA_PATH)
        ruta = filedialog.askopenfilename(
            title="Elegir archivo", initialdir=carpeta if Path(carpeta).exists() else None,
            filetypes=[("Excel", "*.xlsb *.xlsx *.xlsm *.xls"), ("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if ruta:
            self.rutas[clave] = ruta
            self._elegidos.add(clave)
            self._refrescar_rutas()

    # ------------------------------------------------------------------ proceso
    def _fuente(self):
        if self.var_fuente.get() == "registro":
            corrida = self._corrida_elegida()
            if corrida is None:
                raise ValueError("No hay corridas de netting pendientes en el registro. Elegí un archivo Propuestas_Netting.")
            if self.ventana not in corrida["ventanas"]:
                raise ValueError(f"La corrida {corrida['generado']} no tiene propuestas de {self.ventana} hs pendientes.")
            return {"tipo": "registro", "ruta": str(cargas.ruta_registro_por_defecto()),
                    "generado": corrida["generado"], "ventana": self.ventana}
        if not self.rutas.get("propuestas"):
            raise ValueError("Elegí el archivo Propuestas_Netting.")
        return {"tipo": "archivo", "ruta": self.rutas["propuestas"], "ventana": self.ventana}

    def controlar(self):
        if self._procesando:
            return
        faltan = [nombre for clave, nombre in (("020", "Reporte 020"), ("067", "Reporte 067")) if not self.rutas.get(clave)]
        if faltan:
            messagebox.showwarning("Faltan archivos", "Elegí: " + ", ".join(faltan) + ".")
            return
        try:
            fuente = self._fuente()
        except ValueError as exc:
            messagebox.showwarning("Propuestas", str(exc))
            return
        if getattr(self.master, "liberacion_resultado", None) is not None and not messagebox.askyesno(
                "Volver a controlar", "Ya hay un control hecho en esta sesión. Se va a reemplazar. ¿Seguir?"):
            return
        self.config["rutas"].update(self.rutas)
        try:
            guardar_config(self.config)
        except Exception:
            logger.exception("No se pudo guardar la configuración de Liberación")

        self._set_procesando(True)
        origen = f"corrida {fuente['generado']}" if fuente["tipo"] == "registro" else Path(fuente["ruta"]).name
        self._agregar_log(f"Controlando {origen}, {fuente['ventana']} hs.")
        ruta_020, ruta_067, config = self.rutas["020"], self.rutas["067"], dict(self.config)
        self._iniciar_tarea(lambda progreso: ejecutar_control(fuente, ruta_020, ruta_067, config, progreso),
                            self._terminar, self._fallar)

    def _fallar(self, mensaje):
        self._set_procesando(False)
        self.estado.configure(text=mensaje, text_color=T.ERROR)
        self._agregar_log(f"Error: {mensaje}")
        messagebox.showerror("No se pudo controlar", mensaje)

    def _terminar(self, resultado):
        self._set_procesando(False)
        self.master.liberacion_resultado = resultado
        self.master.liberacion_output = None
        for aviso in resultado.avisos.revisar:
            self._agregar_log(f"REVISAR: {aviso}")
        e = resultado.estadisticas()
        partes = ", ".join(f"{n} {c}" for c, n in sorted(e["por_control"].items()))
        texto = f"{e['visibles']} paquetes: {partes}."
        if e["ya_liberados"]:
            texto += f" {e['ya_liberados']} ya liberados en E1."
        avisos = len(resultado.avisos.revisar)
        self.estado.configure(text=texto, text_color=T.AVISO if avisos else T.OK)
        self.btn_revisar.pack(side="left", padx=(12, 0), after=self.btn_controlar)
        self.al_mostrar()

    def _set_procesando(self, activo):
        self._procesando = activo
        self.master.bloquear_navegacion(activo)
        self.btn_controlar.configure(state="disabled" if activo else "normal",
                                     text="Controlando…" if activo else "Controlar pagos")
        if activo:
            self.estado.configure(text="Procesando…", text_color=T.EN_CURSO)
            self.btn_revisar.pack_forget()
        self._barra(activo)


# ====================================================================== revisar y liberar

class PantallaLiberacionRevision(ctk.CTkFrame):
    """El visor de la macro: un paquete por ID de netting con sus controles."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self._visibles = []
        self._actual = None
        self._crear()

    def _crear(self):
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x")
        izquierda = ctk.CTkFrame(cabecera, fg_color="transparent")
        izquierda.pack(side="left")
        _encabezado(izquierda, "Revisar y liberar", "")
        controles = ctk.CTkFrame(cabecera, fg_color="transparent")
        controles.pack(side="right", padx=20, pady=(18, 0))
        self.btn_output = _boton(controles, "Generar Output E1", self.generar_output, ancho=180, alto=36)
        self.btn_output.pack(side="right", padx=(8, 0))
        self.btn_avisos = _boton(controles, "Avisos", self.ver_avisos, tipo="borde", ancho=110, alto=36)
        self.btn_avisos.pack(side="right", padx=(8, 0))

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=20, pady=(0, 6))
        self.lbl_totales = ctk.CTkLabel(filtros, text="", font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_totales.pack(side="left")
        self.combo_grupo = _combo(filtros, ["Todos"], comando=lambda _v: self._llenar_lista(), ancho=90)
        self.combo_grupo.pack(side="right")
        ctk.CTkLabel(filtros, text="Grupo", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="right", padx=(16, 6))
        self.combo_control = _combo(filtros, FILTROS, comando=lambda _v: self._llenar_lista(), ancho=170)
        self.combo_control.pack(side="right")
        ctk.CTkLabel(filtros, text="Control", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="right", padx=(0, 6))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        cuerpo.grid_columnconfigure(0, weight=0, minsize=390)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        lista = _panel(cuerpo)
        lista.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.ent_buscar = ctk.CTkEntry(lista, placeholder_text="Buscar cliente, N° o ID…",
                                       fg_color=T.SUPERFICIE_HUNDIDA, border_color=T.BORDE_FUERTE)
        self.ent_buscar.pack(fill="x", padx=12, pady=(12, 8))
        self.ent_buscar.bind("<KeyRelease>", lambda _e: self._llenar_lista())
        marco, self.tabla = _tabla(lista, ("N°", "Cliente", "Control"), {"N°": 56, "Cliente": 160, "Control": 140},
                                   alto=10, estirar=("Cliente",))
        marco.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        for control, (texto, fondo) in COLOR_CONTROL.items():
            self.tabla.tag_configure(control, foreground=texto, background=fondo)
        self.tabla.tag_configure("liberado", foreground=T.TEXTO_TENUE)
        self.tabla.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_seleccion())

        detalle = _panel(cuerpo)
        detalle.grid(row=0, column=1, sticky="nsew")
        detalle.grid_columnconfigure(0, weight=1)
        detalle.grid_rowconfigure(4, weight=1)

        encabezado = ctk.CTkFrame(detalle, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        encabezado.grid_columnconfigure(0, weight=1)
        self.lbl_tipo = ctk.CTkLabel(encabezado, text="", font=T.ETIQUETA_CHICA, text_color=T.MARCA, anchor="w")
        self.lbl_tipo.grid(row=0, column=0, sticky="w")
        self.lbl_cliente = ctk.CTkLabel(encabezado, text="", font=(T.FUENTE, 20, "bold"), text_color=T.TEXTO, anchor="w")
        self.lbl_cliente.grid(row=1, column=0, sticky="w")
        chips = ctk.CTkFrame(encabezado, fg_color="transparent")
        chips.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.lbl_id = ctk.CTkLabel(chips, text="", font=T.ETIQUETA, text_color=T.INFO, fg_color=T.INFO_FONDO,
                                   corner_radius=8, cursor="hand2")
        self.lbl_id.pack(side="left")
        self.lbl_id.bind("<Button-1>", lambda _e: self._copiar_id())
        self.lbl_control = ctk.CTkLabel(chips, text="", font=T.ETIQUETA, corner_radius=8)
        self.lbl_control.pack(side="left", padx=(8, 0))
        self.lbl_estado = ctk.CTkLabel(chips, text="", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO,
                                       fg_color=T.SUPERFICIE_ELEVADA, corner_radius=8)
        self.lbl_estado.pack(side="left", padx=(8, 0))
        neto = ctk.CTkFrame(encabezado, fg_color="transparent")
        neto.grid(row=0, column=1, rowspan=3, sticky="e")
        ctk.CTkLabel(neto, text="Neto de la propuesta", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_TENUE).pack(anchor="e")
        self.lbl_neto = ctk.CTkLabel(neto, text="", font=(T.FUENTE, 22, "bold"), text_color=T.TEXTO)
        self.lbl_neto.pack(anchor="e")
        self.lbl_067 = ctk.CTkLabel(neto, text="", font=T.CUERPO_CHICO, text_color=T.TEXTO_SECUNDARIO)
        self.lbl_067.pack(anchor="e")

        ctk.CTkFrame(detalle, fg_color=T.BORDE, height=1, corner_radius=0).grid(row=1, column=0, sticky="ew", padx=16, pady=8)

        ctk.CTkLabel(detalle, text="Instrumentos del netting (067)", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO,
                     anchor="w").grid(row=2, column=0, sticky="w", padx=16)
        marco067, self.tabla_067 = _tabla(
            detalle, ("Letra", "Instrumento", "Banco", "Cuenta", "Importe"),
            {"Letra": 50, "Instrumento": 180, "Banco": 180, "Cuenta": 160, "Importe": 120}, alto=3,
            derecha=("Importe",), estirar=("Instrumento", "Banco"))
        marco067.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 8))

        documentos = ctk.CTkFrame(detalle, fg_color="transparent")
        documentos.grid(row=4, column=0, sticky="nsew", padx=16)
        ctk.CTkLabel(documentos, text="Documentos y controles", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO,
                     anchor="w").pack(anchor="w")
        columnas = ("Mov.", "N° Doc", "Tipo", "Total") + COLUMNAS_CONTROL
        anchos = {"Mov.": 72, "N° Doc": 70, "Tipo": 40, "Total": 100}
        anchos.update({t: 88 for t in COLUMNAS_CONTROL})
        marco_docs, self.tabla_docs = _tabla(documentos, columnas, anchos, alto=6, derecha=("Total",),
                                             estirar=COLUMNAS_CONTROL)
        marco_docs.pack(fill="both", expand=True, pady=(2, 0))
        self.tabla_docs.tag_configure("error", background=T.ERROR_FONDO, foreground=T.ERROR)

        pie = ctk.CTkFrame(detalle, fg_color="transparent")
        pie.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 12))
        pie.grid_columnconfigure(0, weight=1)
        self.lbl_errores = ctk.CTkLabel(pie, text="", font=T.CUERPO_CHICO, text_color=T.ERROR, anchor="w",
                                        justify="left", wraplength=620)
        self.lbl_errores.grid(row=0, column=0, sticky="w")
        acciones = ctk.CTkFrame(pie, fg_color="transparent")
        acciones.grid(row=0, column=1, sticky="e")
        self.btn_manual = _boton(acciones, "Liberación manual", self._liberar_manual, tipo="secundario", ancho=160, alto=34)
        self.btn_manual.pack(side="left", padx=(0, 12))
        _boton(acciones, "«", lambda: self._mover(-1), tipo="secundario", ancho=44, alto=30).pack(side="left")
        self.lbl_posicion = ctk.CTkLabel(acciones, text="", font=T.ETIQUETA, text_color=T.TEXTO, width=80)
        self.lbl_posicion.pack(side="left")
        _boton(acciones, "»", lambda: self._mover(1), tipo="secundario", ancho=44, alto=30).pack(side="left")

        self.vacio = crear_estado_vacio(self, "Todavía no hay pagos controlados",
                                        "Controlá los pagos en el paso 1 para revisarlos acá.", "Ir a controlar pagos",
                                        lambda: self.master.mostrar_pantalla("liberacion_control"))

    # ------------------------------------------------------------------ datos
    @property
    def _resultado(self):
        return getattr(self.master, "liberacion_resultado", None)

    def al_mostrar(self):
        resultado = self._resultado
        alternar_estado_vacio(self.vacio, resultado is None)
        if resultado is None:
            return
        cantidad = len(resultado.avisos.revisar)
        self.btn_avisos.configure(text=f"⚠  Avisos ({cantidad})" if cantidad else "Avisos",
                                  text_color=T.AVISO if cantidad else T.TEXTO_SECUNDARIO)
        grupos = sorted({str(p["grupo"]) for p in resultado.paquetes if str(p["grupo"]) not in ("", "None")},
                        key=lambda g: (len(g), g))
        valores = ["Todos"] + grupos
        actual = self.combo_grupo.get()
        self.combo_grupo.configure(values=valores)
        self.combo_grupo.set(actual if actual in valores else "Todos")
        self._actualizar_totales()
        self._llenar_lista()

    def _actualizar_totales(self):
        resultado = self._resultado
        e = resultado.estadisticas()
        fuente = resultado.fuente
        origen = f"Corrida {fuente['generado']}" if fuente["tipo"] == "registro" else Path(fuente["ruta"]).name
        texto = (f"{origen} · {fuente['ventana']} hs  ·  {e['visibles']} paquetes (comparar con E1)  ·  "
                 f"{e['a_liberar']} para liberar")
        if e["ya_liberados"]:
            texto += f"  ·  {e['ya_liberados']} ya liberados"
        self.lbl_totales.configure(text=texto)

    def _llenar_lista(self):
        resultado = self._resultado
        if resultado is None:
            return
        self.tabla.delete(*self.tabla.get_children())
        filtro = self.ent_buscar.get().strip().casefold()
        control = self.combo_control.get()
        grupo = self.combo_grupo.get()
        self._visibles = []
        for indice, paquete in enumerate(resultado.paquetes):
            liberado = ya_liberado(paquete["filas"][0])
            if control == "Ya liberados":
                if not liberado:
                    continue
            elif liberado or (control != "Todos" and paquete["control"] != control):
                continue
            if grupo != "Todos" and str(paquete["grupo"]) != grupo:
                continue
            texto = f"{paquete['n_propuesta']} {paquete['benef']} {paquete['id']} {paquete['ab_benef']}".casefold()
            if filtro and filtro not in texto:
                continue
            self._visibles.append(indice)
            etiqueta = "liberado" if liberado else paquete["control"]
            self.tabla.insert("", "end", iid=str(indice), tags=(etiqueta,),
                              values=(paquete["n_propuesta"], paquete["benef"], paquete["control"]))
        if self._visibles:
            siguiente = self._actual if self._actual in self._visibles else self._visibles[0]
            self._seleccionar(siguiente)
        else:
            self._actual = None
            self._limpiar_detalle()

    def _seleccionar(self, indice):
        self.tabla.selection_set(str(indice))
        self.tabla.focus(str(indice))
        self.tabla.see(str(indice))
        self._mostrar_paquete(indice)

    def _mostrar_seleccion(self):
        seleccion = self.tabla.selection()
        if seleccion and int(seleccion[0]) != self._actual:
            self._mostrar_paquete(int(seleccion[0]))

    def _mover(self, paso):
        if not self._visibles or self._actual not in self._visibles:
            return
        self._seleccionar(self._visibles[(self._visibles.index(self._actual) + paso) % len(self._visibles)])

    def _limpiar_detalle(self):
        for etiqueta in (self.lbl_tipo, self.lbl_cliente, self.lbl_id, self.lbl_control, self.lbl_estado,
                         self.lbl_neto, self.lbl_067, self.lbl_errores, self.lbl_posicion):
            etiqueta.configure(text="")
        self.lbl_control.configure(fg_color="transparent")
        self.tabla_067.delete(*self.tabla_067.get_children())
        self.tabla_docs.delete(*self.tabla_docs.get_children())
        self.btn_manual.configure(state="disabled")

    def _mostrar_paquete(self, indice):
        self._actual = indice
        paquete = self._resultado.paquetes[indice]
        fuente = self._resultado.fuente
        self.lbl_tipo.configure(text=f"PROPUESTA {fuente['ventana']} HS  ·  N° {paquete['n_propuesta']}  ·  "
                                     f"GRUPO {paquete['grupo'] or '—'}  ·  {paquete['tipo_benef']}  ·  "
                                     f"AB {paquete['ab_benef']}" + (f"  ·  {paquete['accion']}" if paquete["accion"] else ""))
        self.lbl_cliente.configure(text=paquete["benef"])
        sin_id = paquete["id"] in (NO_SE_ENCONTRO, "")
        self.lbl_id.configure(text="  Sin ID de netting en el 020  " if sin_id else f"  ID {paquete['id']}   ⧉  ",
                              text_color=T.AVISO if sin_id else T.INFO, fg_color=T.AVISO_FONDO if sin_id else T.INFO_FONDO)
        texto, fondo = COLOR_CONTROL.get(paquete["control"], (T.TEXTO_SECUNDARIO, T.SUPERFICIE_ELEVADA))
        self.lbl_control.configure(text=f"  {paquete['control']}  ", text_color=texto, fg_color=fondo)
        self.lbl_estado.configure(text=f"  E1: {paquete['estado_ne']}  " if not sin_id else "")
        self.lbl_estado.configure(fg_color=T.SUPERFICIE_ELEVADA if not sin_id else "transparent")
        self.lbl_neto.configure(text=_moneda(paquete["neto"]), text_color=T.ERROR if paquete["neto"] < 0 else T.TEXTO)
        cuenta_k = [l for l in paquete["lineas_067"] if str(l.get("letra", "")).strip() == "K"]
        if cuenta_k:
            self.lbl_067.configure(text=f"Por liberar en la cuenta K (067): {_moneda(sum(float(l['importe'] or 0) for l in cuenta_k))}")
        else:
            self.lbl_067.configure(text="Sin cuenta K en el 067" if paquete["lineas_067"] else "Sin líneas en el 067")

        self.tabla_067.delete(*self.tabla_067.get_children())
        for n, linea in enumerate(paquete["lineas_067"]):
            instrumento = " ".join(str(x) for x in (linea.get("instrumento"), linea.get("nombre_instrumento")) if x not in (None, ""))
            self.tabla_067.insert("", "end", tags=("par" if n % 2 == 0 else "impar",), values=(
                linea.get("letra", ""), instrumento, linea.get("banco", ""), linea.get("cuenta", ""),
                _moneda(linea.get("importe"))))

        self.tabla_docs.delete(*self.tabla_docs.get_children())
        for n, fila in enumerate(paquete["filas"]):
            controles = [fila.get(c, "") for c, _t in CONTROLES]
            hay_error = any(v not in ("OK", "", "OK-S/PARA LIBERAR") for v in controles)
            etiqueta = "error" if hay_error else ("par" if n % 2 == 0 else "impar")
            self.tabla_docs.insert("", "end", tags=(etiqueta,), values=(
                "A pagar" if fila["tipo"] == "PAGAR" else "Descuento", fila["doc"], fila["tipo_doc"],
                _moneda(fila["total"]), *(TEXTO_CORTO.get(str(v), str(v)) for v in controles)))

        errores = paquete["errores"]
        if sin_id:
            self.lbl_errores.configure(text="Ningún documento de la propuesta está en el 020: revisá que el netting se "
                                            "haya generado en E1 y que el 020 sea de después.", text_color=T.AVISO)
        elif errores:
            lineas = [f"{doc} {tipo}: {titulo} → {valor}" for doc, tipo, titulo, valor in errores[:4]]
            if len(errores) > 4:
                lineas.append(f"… y {len(errores) - 4} más")
            self.lbl_errores.configure(text="\n".join(lineas), text_color=T.ERROR)
        else:
            self.lbl_errores.configure(text="Todos los controles dieron OK.", text_color=T.OK)
        puede_manual = (not sin_id and paquete["control"] not in A_LIBERAR_EN_E1 and not ya_liberado(paquete["filas"][0]))
        self.btn_manual.configure(state="normal" if puede_manual else "disabled")
        posicion = self._visibles.index(indice) + 1 if indice in self._visibles else 0
        self.lbl_posicion.configure(text=f"{posicion} / {len(self._visibles)}")

    # ------------------------------------------------------------------ acciones
    def _copiar_id(self):
        if self._actual is None:
            return
        paquete = self._resultado.paquetes[self._actual]
        if paquete["id"] in (NO_SE_ENCONTRO, ""):
            return
        self.clipboard_clear()
        self.clipboard_append(str(paquete["id"]))
        self.lbl_id.configure(text=f"  ID {paquete['id']}   ✓ copiado  ")
        self.after(1200, lambda: self._actual is not None and self._mostrar_paquete(self._actual))

    def _liberar_manual(self):
        if self._actual is None:
            return
        paquete = self._resultado.paquetes[self._actual]
        if not messagebox.askyesno(
                "Liberación manual",
                f"El paquete N° {paquete['n_propuesta']} (ID {paquete['id']}) quedó en {paquete['control']}.\n\n"
                "¿Lo revisaste y lo querés liberar igual? Va a entrar en el Output E1."):
            return
        try:
            liberacion_manual(self._resultado, paquete)
        except (ValueError, PermissionError) as exc:
            messagebox.showwarning("Liberación manual", str(exc))
            return
        self._actualizar_totales()
        self._llenar_lista()

    def generar_output(self):
        resultado = self._resultado
        if resultado is None:
            return
        e = resultado.estadisticas()
        if not e["a_liberar"]:
            messagebox.showinfo("Output E1", "No hay paquetes en LIBERAR ni en LIBERACIÓN MANUAL.")
            return
        config = cargar_config()
        actual = config.get("rutas", {}).get("output_e1") or str(Path(APP_DATA_PATH) / NOMBRE_OUTPUT_E1)
        ruta = filedialog.asksaveasfilename(
            title="Output E1", defaultextension=".xlsx", initialdir=str(Path(actual).parent),
            initialfile=Path(actual).name, filetypes=[("Excel", "*.xlsx")], confirmoverwrite=False,
        )
        if not ruta:
            return
        manuales = sum(1 for p in resultado.paquetes if p["control"] in (MANUAL, COMPENSA_MANUAL)
                       and not ya_liberado(p["filas"][0]))
        aviso = f"\n\n{manuales} paquete(s) en MANUAL no van a entrar." if manuales else ""
        if not messagebox.askyesno("Output E1", f"Se van a agregar {e['a_liberar']} ID(s) a la hoja E1 de "
                                                f"{Path(ruta).name}.{aviso}\n\n¿Seguir?"):
            return
        try:
            cantidad = generar_output_e1(resultado, ruta)
        except (ValueError, PermissionError) as exc:
            messagebox.showwarning("Output E1", str(exc))
            return
        config["rutas"]["output_e1"] = ruta
        try:
            guardar_config(config)
        except Exception:
            logger.exception("No se pudo guardar la configuración de Liberación")
        self.master.liberacion_output = ruta
        messagebox.showinfo("Output E1", f"Se agregaron {cantidad} ID(s) a {Path(ruta).name} (hoja E1).\n\n"
                                         "Subilo en E1 para liberar los pagos.")

    def ver_avisos(self):
        resultado = self._resultado
        if resultado is None:
            return
        ventana = ctk.CTkToplevel(self)
        ventana.title("Avisos del control")
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


# ====================================================================== limpiar pagadas

class PantallaLiberacionLimpieza(_ConTarea, ctk.CTkFrame):
    """Botón LIMPIAR LIQUIDACIONES PAGADAS: primero una vista previa, después se confirma."""

    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.configure(fg_color=T.FONDO)
        self.config = cargar_config()
        rutas = self.config.get("rutas", {})
        self.rutas = {
            "020_limpiar": rutas.get("020_limpiar") if rutas.get("020_limpiar") and Path(rutas["020_limpiar"]).exists() else "",
            "historico": rutas.get("historico") or (str(HISTORICO_POR_DEFECTO) if HISTORICO_POR_DEFECTO.exists() else ""),
            "pagados": rutas.get("pagados") or str(PAGADOS_POR_DEFECTO),
        }
        if not self.rutas["020_limpiar"]:
            self.rutas["020_limpiar"] = buscar_en_data("020", con="limpiar")
        self._previa = None
        self._parametros_previa = None
        self._procesando = False
        self._crear()

    def _crear(self):
        _encabezado(self, "Limpiar liquidaciones pagadas",
                    "Bajá el 020 de nuevo (desde la fecha del netting hasta la de liberación). Lo pagado pasa del "
                    "Histórico de controlados al Histórico de pagados.")
        self._crear_log(alto=48)
        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        self.btn_previa = _boton(acciones, "Vista previa", self.vista_previa, tipo="secundario", ancho=160)
        self.btn_previa.pack(side="left")
        self.btn_limpiar = _boton(acciones, "Limpiar pagadas", self.limpiar, ancho=180)
        self.btn_limpiar.pack(side="left", padx=(12, 0))
        self.btn_limpiar.configure(state="disabled")
        self.estado = ctk.CTkLabel(acciones, text="", font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO, anchor="w",
                                   justify="left", wraplength=620)
        self.estado.pack(side="left", padx=16)

        panel = _panel(self)
        panel.pack(fill="x", padx=20, pady=(0, 10))
        panel.grid_columnconfigure(1, weight=1)
        self.lbl_rutas = {}
        for fila, (clave, titulo, ayuda) in enumerate((
                ("020_limpiar", "Reporte 020 (nuevo)", "Bajado después de liberar (020_LIMPIAR… en data)"),
                ("historico", "Histórico de controlados", "El .xlsx que genera CONTROLAR"),
                ("pagados", "Histórico de pagados", "Si no existe, se crea"),
        )):
            textos = ctk.CTkFrame(panel, fg_color="transparent")
            textos.grid(row=fila, column=0, sticky="nw", padx=(18, 12), pady=(10 if fila == 0 else 2, 2))
            ctk.CTkLabel(textos, text=titulo, font=T.ETIQUETA, text_color=T.TEXTO, anchor="w", height=20).pack(anchor="w")
            ctk.CTkLabel(textos, text=ayuda, font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w", height=16).pack(anchor="w")
            etiqueta = ctk.CTkLabel(panel, text="", font=T.CUERPO_CHICO, anchor="w", justify="left", wraplength=620)
            etiqueta.grid(row=fila, column=1, sticky="w")
            _boton(panel, "Elegir…", lambda c=clave: self.elegir(c), tipo="secundario", ancho=110, alto=32).grid(
                row=fila, column=2, sticky="e", padx=18, pady=2)
            self.lbl_rutas[clave] = etiqueta

        parametros = ctk.CTkFrame(panel, fg_color="transparent")
        parametros.grid(row=3, column=0, columnspan=3, sticky="w", padx=18, pady=(6, 12))
        hoy = date.today()
        ayer = hoy - timedelta(days=1)
        while ayer.weekday() >= 5:
            ayer -= timedelta(days=1)
        ctk.CTkLabel(parametros, text="Fecha de netting", font=T.ETIQUETA, text_color=T.TEXTO).pack(side="left")
        self.ent_netting = _entrada(parametros, texto=ayer.strftime("%d/%m/%Y"))
        self.ent_netting.pack(side="left", padx=(8, 24))
        ctk.CTkLabel(parametros, text="Fecha de acreditación", font=T.ETIQUETA, text_color=T.TEXTO).pack(side="left")
        self.ent_acreditacion = _entrada(parametros, texto=hoy.strftime("%d/%m/%Y"))
        self.ent_acreditacion.pack(side="left", padx=(8, 24))
        self.var_solo_a = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            parametros, text="Mover solo pagos liberados (estado A o P)", variable=self.var_solo_a,
            font=T.CUERPO_CHICO, text_color=T.TEXTO_SUAVE, fg_color=T.PRIMARIO, hover_color=T.PRIMARIO_HOVER,
            border_color=T.BORDE_FUERTE, checkbox_width=18, checkbox_height=18, command=self._invalidar,
        ).pack(side="left")
        for entrada in (self.ent_netting, self.ent_acreditacion):
            entrada.bind("<KeyRelease>", lambda _e: self._invalidar())

        resultados = _panel(self)
        resultados.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        cabecera = ctk.CTkFrame(resultados, fg_color="transparent")
        cabecera.pack(fill="x", padx=16, pady=(10, 4))
        self.lbl_resumen = ctk.CTkLabel(cabecera, text="Hacé la vista previa para ver qué se va a mover.",
                                        font=T.ETIQUETA, text_color=T.TEXTO_SECUNDARIO, anchor="w")
        self.lbl_resumen.pack(side="left")
        self.combo_vista = _combo(cabecera, ["A mover", "Pendientes de pago", "No están en el histórico", "No están en A ni P"],
                                  comando=lambda _v: self._llenar_resultados(), ancho=200)
        self.combo_vista.pack(side="right")
        marco, self.tabla = _tabla(resultados, ("N° Doc", "Tipo", "Dato"), {"N° Doc": 120, "Tipo": 70, "Dato": 300},
                                   alto=6, estirar=("Dato",))
        marco.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._refrescar_rutas()

    def al_mostrar(self):
        self._refrescar_rutas()

    def _refrescar_rutas(self):
        for clave, etiqueta in self.lbl_rutas.items():
            _texto_ruta(etiqueta, self.rutas.get(clave))

    def elegir(self, clave):
        actual = self.rutas.get(clave) or ""
        carpeta = str(Path(actual).parent) if actual else str(APP_DATA_PATH)
        opciones = dict(title="Elegir archivo", initialdir=carpeta if Path(carpeta).exists() else None)
        if clave == "pagados":
            ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                confirmoverwrite=False, initialfile=Path(actual).name if actual else "",
                                                **opciones)
        else:
            tipos = [("Excel", "*.xlsx *.xlsm")] if clave == "historico" else [
                ("Excel", "*.xlsb *.xlsx *.xlsm *.xls"), ("CSV", "*.csv"), ("Todos", "*.*")]
            ruta = filedialog.askopenfilename(filetypes=tipos, **opciones)
        if ruta:
            self.rutas[clave] = ruta
            self._refrescar_rutas()
            self._invalidar()

    def _invalidar(self):
        self._previa = None
        self.btn_limpiar.configure(state="disabled")

    def _parametros(self):
        faltan = [nombre for clave, nombre in (("020_limpiar", "Reporte 020"), ("historico", "Histórico de controlados"),
                                                ("pagados", "Histórico de pagados")) if not self.rutas.get(clave)]
        if faltan:
            raise ValueError("Elegí: " + ", ".join(faltan) + ".")
        netting = _leer_fecha(self.ent_netting.get(), "Fecha de netting")
        acreditacion = _leer_fecha(self.ent_acreditacion.get(), "Fecha de acreditación")
        if acreditacion < netting:
            raise ValueError("La fecha de acreditación no puede ser anterior a la de netting.")
        registro = cargas.ruta_registro_por_defecto()
        return dict(ruta_020=self.rutas["020_limpiar"], ruta_historico=self.rutas["historico"],
                    ruta_pagados=self.rutas["pagados"], fecha_netting=netting, fecha_acreditacion=acreditacion,
                    solo_estado_a=bool(self.var_solo_a.get()),
                    ruta_registro=str(registro) if registro.exists() else None)

    def vista_previa(self):
        self._correr(simular=True)

    def limpiar(self):
        if self._previa is None:
            return
        previa = self._previa
        if not messagebox.askyesno(
                "Limpiar pagadas",
                f"Se van a mover {previa.filas_movidas} fila(s) ({len(previa.documentos)} documentos) del Histórico de "
                "controlados al Histórico de pagados.\n\nAntes se guarda una copia de los dos archivos. ¿Seguir?"):
            return
        self._correr(simular=False)

    def _correr(self, simular):
        if self._procesando:
            return
        try:
            parametros = self._parametros()
        except ValueError as exc:
            messagebox.showwarning("Limpiar pagadas", str(exc))
            return
        self.config["rutas"].update(self.rutas)
        try:
            guardar_config(self.config)
        except Exception:
            logger.exception("No se pudo guardar la configuración de Liberación")
        self._set_procesando(True)
        self._agregar_log("Calculando la vista previa…" if simular else "Moviendo las liquidaciones pagadas…")
        self._iniciar_tarea(lambda _p: limpiar_pagadas(simular=simular, **parametros),
                            lambda r: self._terminar(r, simular), self._fallar)

    def _fallar(self, mensaje):
        self._set_procesando(False)
        self.estado.configure(text=mensaje, text_color=T.ERROR)
        self._agregar_log(f"Error: {mensaje}")
        messagebox.showerror("Limpiar pagadas", mensaje)

    def _terminar(self, resultado, simular):
        self._set_procesando(False)
        self._ultimo = resultado
        texto = (f"{len(resultado.documentos)} documentos ({resultado.filas_movidas} filas) "
                 f"{'para mover' if simular else 'movidos'}  ·  {len(resultado.pendientes)} pendientes de pago  ·  "
                 f"{len(resultado.no_encontrados)} no están en el histórico")
        if resultado.omitidos_estado:
            texto += f"  ·  {len(resultado.omitidos_estado)} renglones del 020 no están en A ni P"
        self.lbl_resumen.configure(text=texto, text_color=T.TEXTO)
        if simular:
            self._previa = resultado if resultado.filas_movidas else None
            self.btn_limpiar.configure(state="normal" if self._previa else "disabled")
            self.estado.configure(text="Revisá la vista previa y confirmá con «Limpiar pagadas»." if self._previa
                                  else "No hay nada para mover.", text_color=T.TEXTO_SECUNDARIO)
            self._agregar_log(texto)
        else:
            self._previa = None
            self.btn_limpiar.configure(state="disabled")
            copias = ", ".join(Path(p).name for p in resultado.copias)
            self.estado.configure(text=f"Listo. Copias de seguridad: {copias}", text_color=T.OK)
            self._agregar_log(f"Listo: {texto}. Copias: {copias}")
        self.combo_vista.set("A mover")
        self._llenar_resultados()

    def _llenar_resultados(self):
        self.tabla.delete(*self.tabla.get_children())
        resultado = getattr(self, "_ultimo", None)
        if resultado is None:
            return
        vista = self.combo_vista.get()
        if vista == "A mover":
            filas = [(d, t, f"ID de pago {i}") for d, t, i in resultado.documentos]
        elif vista == "Pendientes de pago":
            filas = [(d, t, f"Fecha de pago {_fecha(f)}") for d, t, f in resultado.pendientes]
        elif vista == "No están en el histórico":
            filas = [(d, t, "Pagado en el 020, no está en el Histórico de controlados") for d, t in resultado.no_encontrados]
        else:
            filas = [(d, t, f"Estado {e}") for d, t, e in resultado.omitidos_estado]
        for n, valores in enumerate(filas):
            self.tabla.insert("", "end", tags=("par" if n % 2 == 0 else "impar",), values=valores)

    def _set_procesando(self, activo):
        self._procesando = activo
        self.master.bloquear_navegacion(activo)
        estado = "disabled" if activo else "normal"
        self.btn_previa.configure(state=estado)
        if activo:
            self.btn_limpiar.configure(state="disabled")
            self.estado.configure(text="Procesando…", text_color=T.EN_CURSO)
        self._barra(activo)
