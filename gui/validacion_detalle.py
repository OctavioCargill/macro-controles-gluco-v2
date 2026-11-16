"""Validación de la liquidación abierta en el detalle contra la Power App (captura) y su factura (PDF).

Se usa como mixin de PantallaControl: agrega la barra «Validar con la Power App», pinta las tarjetas de datos
(verde coincide, rojo distinto) y muestra el detalle de cada comparación. Todo corre en la PC.
"""

import threading
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd

from gui import tema as T
from validacion.comparador import COINCIDE, DISTINTO, NO_SE_VE, campo, comparar_captura, comparar_factura

ICONO = {COINCIDE: "✓ Coincide", DISTINTO: "✗ Distinto", NO_SE_VE: "— No se ve"}
COLOR = {COINCIDE: (T.OK, T.OK_FONDO), DISTINTO: (T.ERROR, T.ERROR_FONDO), NO_SE_VE: (T.TEXTO_TENUE, T.SUPERFICIE)}
ORIGEN = {"captura": "Power App", "factura": "Factura"}


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
        captura = [campo(t["titulo"], t["valor"], alternativas=alternativas.get(t["titulo"], ()))
                   for t in getattr(self, "_tarjetas_detalle", []) if t["titulo"] != "ID solicitado"]
        for registro in registros_tax:
            captura.append(campo(f"{registro['Tipo']}: {registro['Concepto']}", registro["Importe"], tipo="importe"))

        por_titulo = {c.titulo: c for c in captura}
        factura = [por_titulo[t] for t in ("Total a pagar", "Nro. Legal (COE)", "Contrato", "Kilos", "Vendedor")
                   if t in por_titulo]
        imponible = _valor(primer_fila, ["Imponible"])
        if imponible:
            factura.append(campo("Importe imponible (subtotal)", imponible, tipo="importe"))
        factura += [c for c in captura if c.titulo.startswith(("Retención:", "Percepción:"))]
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

    def _validar(self, origen, fuente, nombre):
        numero_doc = self._doc_detalle
        if not numero_doc or self._validando:
            return
        campos = self._campos_validacion.get(numero_doc, {}).get(origen, [])
        if not campos:
            return
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
                    resultado = comparar_factura(campos, leer_pdf(fuente), nombre)
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
        archivos = "  ·  ".join(f"{ORIGEN[o]}: {v.archivo}" for o, v in validaciones.items())
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
        orden = {DISTINTO: 0, NO_SE_VE: 1, COINCIDE: 2}
        for origen, validacion in validaciones.items():
            for resultado in sorted(validacion.resultados, key=lambda r: orden[r.estado]):
                tabla.insert("", "end", tags=(resultado.estado,), values=(
                    ORIGEN[origen], resultado.titulo, resultado.valor_app, resultado.leido, ICONO[resultado.estado],
                    resultado.nota))
        tabla.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(
            panel, font=T.NOTA, text_color=T.TEXTO_TENUE, anchor="w", justify="left", wraplength=1000,
            text=("«No se ve» quiere decir que el dato no aparece en la captura o en la factura (no es un error): "
                  "revisalo a mano si corresponde. La lectura se hace en esta PC, sin internet."),
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
