"""Paleta y tipografía de la interfaz (tema claro, colores de Glucovil).

Todos los colores y fuentes de las pantallas salen de acá. Para ajustar el
estilo de la app (por ejemplo, el verde principal) alcanza con cambiar este
archivo: no hace falta tocar cada pantalla.

Base de marca: verde oliva (acción principal), naranja (acento) y fondo claro.
"""

FUENTE = "Segoe UI"

# --- Fondos y superficies
FONDO = "#f5f6f1"               # fondo de cada pantalla (blanco apenas verdoso)
SUPERFICIE_HUNDIDA = "#f1f4ec"  # campos de texto, tablas, registro de actividad
SUPERFICIE = "#ffffff"          # paneles y tarjetas
SUPERFICIE_ELEVADA = "#eef2e7"  # tarjetas y botones al pasar el mouse
ENCABEZADO_TABLA = "#e6ecdc"

# --- Bordes
BORDE = "#dfe4d6"
BORDE_FUERTE = "#c5ccb9"        # campos de texto y combos

# --- Texto
TEXTO = "#1d2618"
TEXTO_SUAVE = "#2c3727"
TEXTO_SECUNDARIO = "#56634e"
TEXTO_TENUE = "#677360"
TEXTO_SOBRE_COLOR = "#ffffff"   # texto sobre botones de color

# --- Acción principal (verde oliva de Glucovil, oscurecido para que el texto blanco se lea)
PRIMARIO = "#4f7a2b"
PRIMARIO_HOVER = "#426824"
PRIMARIO_ACTIVO = "#36561d"
ENLACE = "#3f6b1f"              # textos clickeables: "Abrir →", ruta de navegación

# --- Acción secundaria (volver, cerrar, salir)
SECUNDARIO = "#e7ebe0"
SECUNDARIO_HOVER = "#dbe1d2"
TEXTO_SOBRE_SECUNDARIO = "#33402c"

# --- Acciones con significado
EXITO = "#0e7c66"               # verde azulado: distinto del verde de marca
EXITO_HOVER = "#0b6655"
PELIGRO = "#c62828"
PELIGRO_HOVER = "#a61f1f"
EN_CURSO = "#b45309"
EN_CURSO_HOVER = "#92400e"

# --- Mensajes de estado: color del texto y fondo que lo acompaña
OK = "#17663a"
OK_FONDO = "#dcf2e3"
INFO = "#1f4f9a"
INFO_FONDO = "#e1ebf8"
AVISO = "#8a4b08"
AVISO_FONDO = "#fbefd5"
ERROR = "#a61f1f"
ERROR_FONDO = "#fbe2e0"

FONDO_DE_ESTADO = {
    OK: OK_FONDO,
    INFO: INFO_FONDO,
    AVISO: AVISO_FONDO,
    ERROR: ERROR_FONDO,
}

# --- Marca
MARCA = "#b0561a"               # naranja Glucovil (apenas oscurecido para texto chico): solo como acento (rótulos, etapa activa)

# --- Colores de las tarjetas de resumen
SERIE_TOTAL = "#2b5fb3"
SERIE_MACRO = "#0e7c66"
SERIE_MANUAL = "#b45309"
SERIE_PARCIALES = "#6d3fc2"
SERIE_FINALES = "#0b6e9e"
SERIE_COMISIONES = "#b0306f"
SERIE_AJUSTES = "#c2352f"

# --- Tipografía
TITULO_PANTALLA = (FUENTE, 26, "bold")
SUBTITULO = (FUENTE, 15, "bold")
ETIQUETA = (FUENTE, 12, "bold")
ETIQUETA_CHICA = (FUENTE, 11, "bold")
CUERPO = (FUENTE, 12)
CUERPO_CHICO = (FUENTE, 11)
NOTA = (FUENTE, 10)
BOTON = (FUENTE, 13, "bold")
BOTON_MENU = (FUENTE, 15, "bold")
VALOR_DESTACADO = (FUENTE, 24, "bold")

# --- Medidas
ALTO_BOTON = 44
RADIO_PANEL = 18
RADIO_BOTON = 10
