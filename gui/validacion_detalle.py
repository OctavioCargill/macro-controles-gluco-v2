"""Validación de la liquidación abierta en el detalle contra la Power App (captura) y su factura (PDF).

Se usa como mixin de PantallaControl: agrega la barra «Validar con la Power App», pinta las tarjetas de datos
(verde coincide, rojo distinto) y muestra el detalle de cada comparación. Todo corre en la PC.
"""

import json
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd

from gui import tema as T
from services.auditoria import APP_CONFIG_PATH
from validacion import normalizar as N
from validacion.comparador import (
    COINCIDE, DISTINTO, NO_SE_VE, REVISAR, TOLERANCIA_POR_DEFECTO, campo, comparar_captura, comparar_factura,
)

ICONO = {COINCIDE: "✓ Coincide", DISTINTO: "✗ Distinto", NO_SE_VE: "— No se ve", REVISAR: "! A revisar"}
COLOR = {COINCIDE: (T.OK, T.OK_FONDO), DISTINTO: (T.ERROR, T.ERROR_FONDO), NO_SE_VE: (T.TEXTO_TENUE, T.SUPERFICIE),
         REVISAR: (T.AVISO, T.AVISO_FONDO)}
ARCHIVO_CONFIG = Path(APP_CONFIG_PATH) / "validacion.json"


def leer_tolerancia():
    """% de variación aceptado en los importes de la factura (uno solo para todas las facturas)."""
    try:
        valor = float(json.loads(ARCHIVO_CONFIG.read_text(encoding="utf-8")).get("tolerancia_factura_pct"))
        return valor if 0 <= valor <= 50 else TOLERANCIA_POR_DEFECTO
    except (OSError, ValueError, TypeError):
        return TOLERANCIA_POR_DEFECTO


def guardar_tolerancia(valor):
    try:
        contenido = json.loads(ARCHIVO_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        contenido = {}
    contenido["tolerancia_factura_pct"] = valor
    ARCHIVO_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_CONFIG.write_text(json.dumps(contenido, indent=2), encoding="utf-8")
ORIGEN = {"captura": "Power App", "factura": "Factura"}
# Datos que se verifican contra la captura de la Power App (el resto se controla a mano)
CAMPOS_CAPTURA = ("Contrato", "Kilos", "Nro. Legal (COE)", "Fecha de Pago", "Nro. Doc. Interno")


def _valor(fila, columnas):
    for columna in columnas:
        if columna in fila.index and pd.notna(fila.get(columna)) and str(fila.get(columna)).strip() not in ("", "nan"):
            valor = fila.get(columna)
            if isinstance(valor, pd.Timestamp):
                return valor.strftime("%d/%m/%Y")
            if isinstance(valor, float) and valor.is_integer():
                return str(int(valor))
            return str(valor)
    return ""


class ValidacionDetalleMixin:

    # ------------------------------------------------------------------ preparación
    def _iniciar_validacion(self):
        self._validaciones = {}            # numero_doc → {"captura": Validacion, "factura": Validacion}
        self._campos_validacion = {}
        self._facturas_cargadas = {}       # numero_doc → ruta del PDF (para recalcular si cambia el margen)
        self._validando = False
        self.winfo_toplevel().bind("<Control-v>", self._pegar_captura_atajo, add="+")
        self.winfo_toplevel().bind("<Control-V>", self._pegar_captura_atajo, add="+")

    def _armar_campos(self, numero_doc, primer_fila, registros_tax):
        """Qué se compara: los datos de las tarjetas del detalle, con otras formas válidas de cada uno."""
        alternativas = {
            "Tipo liquidación": [_valor(primer_fila, ["Tip Liquidacion"]), _valor(primer_fila, ["Descripcion de la liquidacion"])],
            "Forma de Pago": [_valor(primer_fila, [c]) for c in ("Condicion de Pago", "Forma de Pago", "Pago Contra")],
            "Nro. Legal (COE)": [_valor(primer_fila, [c]) for c in ("Numero de CAE COE Factura", "Numero documento fiscal",
                                                                   "Nro_Legal", "COE")],
            "Vendedor": [_valor(primer_fila, ["Nombre Vendedor"]), _valor(primer_fila, ["Vendedor"])],
            "Corredor": [_valor(primer_fila, ["Nombre Corredor"]), _valor(primer_fila, ["Corredor"])],
        }
        todos = [campo(t["titulo"], t["valor"], alternativas=alternativas.get(t["titulo"], ()))
                 for t in getattr(self, "_tarjetas_detalle", []) if t["titulo"] != "ID solicitado"]
        impuestos = []
        for registro in registros_tax:
            impuesto = campo(f"{registro['Tipo']}: {registro['Concepto']}", registro["Importe"], tipo="importe")
            impuesto.grupo = "retencion" if registro["Tipo"].startswith("Ret") else "percepcion"
            impuesto.base = N.importe(registro.get("Base de cálculo"))
            impuesto.alicuota = N.importe(registro.get("Alícuota (%)"))
            impuestos.append(impuesto)
        por_titulo = {c.titulo: c for c in todos}
        captura = [por_titulo[t] for t in CAMPOS_CAPTURA if t in por_titulo]

        factura = [por_titulo[t] for t in ("Total a pagar", "Nro. Legal (COE)", "Contrato", "Kilos", "Vendedor")
                   if t in por_titulo]
        imponible = _valor(primer_fila, ["Imponible"])
        if imponible:
            factura.append(campo("Importe imponible (subtotal)", imponible, tipo="importe"))
        factura += impuestos
        self._campos_validacion[numero_doc] = {"captura": captura, "factura": factura}

    # ------------------------------------------------------------------ interfaz
    def _crear_barra_validacion(self, cabecera, numero_doc):
        barra = ctk.CTkFrame(cabecera, fg_color=T.SUPERFICIE_HUNDIDA, corner_radius=12)
        barra.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
        ctk.CTkLabel(barra, text="Validar", font=T.ETIQUETA, text_color=T.TEXTO_SUAVE).pack(side="left", padx=(14, 10), pady=10)
        estilo = dict(height=32, corner_radius=T.RADIO_BOTON, font=T.ETIQUETA_CHICA, fg_color=T.SECUNDARIO,
                      hover_color=T.SECUNDARIO_HOVER, text_color=T.TEXTO_SOBRE_SECUNDARIO)
        self.btn_pegar_captura = ctk.CTkButton(barra, text="Pegar captura de la Power App (Ctrl+V)", width=260,
                                               command=self._pegar_captura, **estilo)
        self.btn_pegar_captura.pack(side="left", pady=10)
        ctk.CTkButton(barra, text="Elegir imagen…", width=120, command=self._elegir_captura, **estilo).pack(
            side="left", padx=6, pady=10)
        ctk.CTkButton(barra, text="Cargar factura PDF…", width=150, command=self._elegir_factura, **estilo).pack(
            side="left", pady=10)
        ctk.CTkLabel(barra, text="Margen ±", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(
            side="left", padx=(12, 2))
        self.ent_tolerancia = ctk.CTkEntry(barra, width=48, height=30, justify="right", font=T.ETIQUETA_CHICA,
                                           fg_color=T.SUPERFICIE, border_color=T.BORDE_FUERTE)
        self.ent_tolerancia.insert(0, f"{leer_tolerancia():g}".replace(".", ","))
        self.ent_tolerancia.pack(side="left")
        self.ent_tolerancia.bind("<Return>", lambda _e: self._cambiar_tolerancia())
        self.ent_tolerancia.bind("<FocusOut>", lambda _e: self._cambiar_tolerancia())
        ctk.CTkLabel(barra, text="%", font=T.ETIQUETA_CHICA, text_color=T.TEXTO_SECUNDARIO).pack(side="left", padx=(2, 0))
        self.lbl_validacion = ctk.CTkLabel(barra, text="Sacá una captura (Win + Shift + S) y pegala acá.",
                                           font=T.CUERPO_CHICO, text_color=T.TEXTO_TENUE, anchor="w")
        self.lbl_validacion.pack(side="left", padx=12, pady=10)

    def _crear_panel_resultados(self, contenido, numero_doc):
        self._panel_validacion = ctk.CTkFrame(contenido, fg_color=T.SUPERFICIE, corner_radius=10, border_width=1,
                                              border_color=T.BORDE)
        self._panel_validacion.grid(row=99, column=0, columnspan=3, sticky="ew", padx=6, pady=(12, 0))
        self._panel_validacion.grid_remove()
        self._pintar_validacion(numero_doc)

    # ------------------------------------------------------------------ acciones
    def _pegar_captura_atajo(self, evento=None):
        if not self.detalle_abierto() or not self.winfo_ismapped():
            return None
        foco = self.focus_get()
        if foco is not None and foco.winfo_class() in ("Entry", "TEntry", "Text"):
            return None                     # Ctrl+V en un campo de texto pega texto, como siempre
        self._pegar_captura()
        return "break"

    def _pegar_captura(self):
        from validacion.lectura import imagen_del_portapapeles

        imagen = imagen_del_portapapeles()
        if imagen is None:
            messagebox.showinfo(
                "Pegar captura", "No hay una imagen copiada.\n\nEn la Power App apretá Win + Shift + S, marcá la "
                                 "liquidación y volvé acá a pegarla (o usá «Elegir imagen…»).")
            return
        self._validar("captura", imagen, "captura pegada")

    def _elegir_captura(self):
        ruta = filedialog.askopenfilename(title="Captura de la Power App",
                                          filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp *.webp"), ("Todos", "*.*")])
        if ruta:
            self._validar("captura", ruta, Path(ruta).name)

    def _elegir_factura(self):
        ruta = filedialog.askopenfilename(title="Factura de la liquidación", filetypes=[("PDF", "*.pdf")])
        if ruta:
            self._validar("factura", ruta, Path(ruta).name)

    def _cambiar_tolerancia(self):
        """Guarda el margen (global) y, si ya se cargó la factura de esta liquidación, la vuelve a comparar."""
        valor = N.importe(self.ent_tolerancia.get())
        if valor is None or not 0 <= valor <= 50:
            messagebox.showwarning("Margen", "Ingresá un porcentaje entre 0 y 50 (por ejemplo 2 o 1,5).")
            self.ent_tolerancia.delete(0, "end")
            self.ent_tolerancia.insert(0, f"{leer_tolerancia():g}".replace(".", ","))
            return
        if valor == leer_tolerancia():
            return
        try:
            guardar_tolerancia(valor)
        except OSError:
            pass
        ruta = self._facturas_cargadas.get(self._doc_detalle)
        if ruta and not self._validando:
            self._validar("factura", ruta, Path(ruta).name)

    def _validar(self, origen, fuente, nombre):
        numero_doc = self._doc_detalle
        if not numero_doc or self._validando:
            return
        campos = self._campos_validacion.get(numero_doc, {}).get(origen, [])
        if not campos:
            return
        if origen == "factura":
            self._facturas_cargadas[numero_doc] = fuente
        tolerancia = leer_tolerancia()
        self._validando = True
        self.lbl_validacion.configure(
            text=f"Leyendo {'la captura' if origen == 'captura' else 'la factura'}… (la primera vez tarda un poco más)",
            text_color=T.EN_CURSO)

        def tarea():
            from validacion.lectura import LecturaNoDisponible, leer_imagen, leer_pdf

            try:
                if origen == "captura":
                    resultado = comparar_captura(campos, leer_imagen(fuente), nombre)
                else:
                    resultado = comparar_factura(campos, leer_pdf(fuente), nombre, tolerancia_pct=tolerancia)
                error = None if resultado.renglones_leidos else "No se pudo leer texto en el archivo."
            except LecturaNoDisponible as exc:
                resultado, error = None, str(exc)
            except Exception as exc:  # pragma: no cover
                resultado, error = None, f"Error inesperado: {exc}"
            self.after(0, lambda: self._terminar_validacion(numero_doc, origen, resultado, error))

        threading.Thread(target=tarea, daemon=True).start()

    def _terminar_validacion(self, numero_doc, origen, resultado, error):
        self._validando = False
        if error:
            if self._doc_detalle == numero_doc:
                self.lbl_validacion.configure(text=error, text_color=T.ERROR)
            messagebox.showwarning("Validar", error)
            return
        self._validaciones.setdefault(numero_doc, {})[origen] = resultado
        if self._doc_detalle == numero_doc:
            self._pintar_validacion(numero_doc)

    # ------------------------------------------------------------------ mostrar resultados
    def _pintar_validacion(self, numero_doc):
        validaciones = self._validaciones.get(numero_doc, {})
        estados = {}                        # titulo → [(origen, Resultado)]
        for origen, validacion in validaciones.items():
            for resultado in validacion.resultados:
                estados.setdefault(resultado.titulo, []).append((origen, resultado))

        for tarjeta in getattr(self, "_tarjetas_detalle", []):
            tarjeta.pop("borde_validacion", None)
            items = estados.get(tarjeta["titulo"], [])
            if any(r.estado == DISTINTO for _, r in items):
                origen, distinto = next((o, r) for o, r in items if r.estado == DISTINTO)
                tarjeta["borde_validacion"] = T.ERROR
                tarjeta["frame"].configure(border_color=T.ERROR, border_width=2)
                tarjeta["aviso"].configure(text=f"✗ {ORIGEN[origen]}: {distinto.leido}"[:38], text_color=T.ERROR)
            elif any(r.estado == REVISAR for _, r in items):
                tarjeta["borde_validacion"] = T.AVISO
                tarjeta["frame"].configure(border_color=T.AVISO, border_width=2)
                tarjeta["aviso"].configure(text="! A revisar en la factura", text_color=T.AVISO)
            elif any(r.estado == COINCIDE for _, r in items):
                tarjeta["borde_validacion"] = T.OK
                tarjeta["frame"].configure(border_color=T.OK, border_width=2)
                origenes = " y ".join(ORIGEN[o] for o, r in items if r.estado == COINCIDE)
                tarjeta["aviso"].configure(text=f"✓ {origenes}", text_color=T.OK)

        if not hasattr(self, "lbl_validacion"):
            return
        if not validaciones:
            self.lbl_validacion.configure(text="Sacá una captura (Win + Shift + S) y pegala acá.", text_color=T.TEXTO_TENUE)
            return
        partes = [f"{ORIGEN[o]}: {v.resumen}" for o, v in validaciones.items()]
        hay_diferencias = any(v.hay_diferencias for v in validaciones.values())
        self.lbl_validacion.configure(text="   ·   ".join(partes), text_color=T.ERROR if hay_diferencias else T.OK)
        self._tabla_resultados(validaciones)

    def _tabla_resultados(self, validaciones):
        panel = getattr(self, "_panel_validacion", None)
        if panel is None or not panel.winfo_exists():
            return
        for hijo in panel.winfo_children():
            hijo.destroy()
        panel.grid()
        cabeza = ctk.CTkFrame(panel, fg_color="transparent")
        cabeza.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(cabeza, text="Validación con la Power App y la factura", font=T.SUBTITULO,
                     text_color=T.TEXTO).pack(side="left")
        archivos = "  ·  ".join(
            f"{ORIGEN[o]}: {v.archivo}" + (f" (margen ±{v.tolerancia_pct:g}%)".replace(".", ",")
                                          if getattr(v, "tolerancia_pct", None) is not None else "")
            for o, v in validaciones.items())
        ctk.CTkLabel(cabeza, text=archivos, font=T.NOTA, text_color=T.TEXTO_TENUE).pack(side="right")

        columnas = ("Origen", "Dato", "En la app", "Leído", "Resultado", "Detalle")
        filas = sum(len(v.resultados) for v in validaciones.values())
        tabla = ttk.Treeview(panel, columns=columnas, show="headings", height=min(max(filas, 3), 30),
                             selectmode="browse")
        anchos = {"Origen": 90, "Dato": 220, "En la app": 190, "Leído": 190, "Resultado": 110, "Detalle": 300}
        for columna in columnas:
            tabla.heading(columna, text=columna)
            tabla.column(columna, width=anchos[columna], anchor="w", stretch=columna in ("Dato", "Detalle"))
        for estado, (texto, fondo) in COLOR.items():
            tabla.tag_configure(estado, foreground=texto, background=fondo)
        orden = {DISTINTO: 0, REVISAR: 1, NO_SE_VE: 2, COINCIDE: 3}
        for origen, validacion in validaciones.items():
            for resultado in sorted(validacion.resultados, key=lambda r: orden[r.estado]):
                tabla.insert("", "end", tags=(resultado.estado,), values=(
                    ORIGEN[origen], resultado.titulo, resultado.valor_app, resultado.leido, ICONO[resultado.estado],
                    resultado.nota))
        tabla.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(
            panel, font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w", justify="left", wraplength=1000,
            text=("«No se ve»: el dato no aparece en la captura o en la factura (no es un error). «A revisar»: el "
                  "impuesto no figura tal cual en la factura pero el total coincide. Los importes de la factura "
                  "coinciden si están dentro del margen ± % elegido. La lectura se hace en esta PC, sin internet."),
        ).pack(fill="x", padx=14, pady=(0, 12))

    # ------------------------------------------------------------------ al marcar como controlada
    def _confirmar_diferencias(self, numero_doc):
        """Si la validación encontró diferencias, se pide confirmación antes de marcarla controlada."""
        validaciones = self._validaciones.get(numero_doc, {})
        distintos = [(o, r) for o, v in validaciones.items() for r in v.resultados if r.estado == DISTINTO]
        if not distintos:
            return True
        detalle = "\n".join(f"• {ORIGEN[o]} — {r.titulo}: app {r.valor_app} / leído {r.leido}" for o, r in distintos[:8])
        return messagebox.askyesno(
            "Hay diferencias",
            f"La validación encontró {len(distintos)} diferencia(s):\n\n{detalle}\n\n¿La marcás como controlada igual?")
