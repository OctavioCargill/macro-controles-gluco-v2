"""Preguntas y respuestas del asistente.

Cada entrada tiene:
- id: identificador único (para relacionar preguntas).
- proceso: "general", "controlar", "netting" o "liberacion".
- pregunta: cómo aparece en la lista.
- claves: otras palabras o frases con las que alguien podría preguntar lo mismo (ayudan al buscador).
- respuesta: texto. Los renglones que empiezan con "• " se muestran como viñetas.
- pantalla: (opcional) pantalla de la app a la que lleva el botón «Ir a …».
- relacionadas: (opcional) ids de otras preguntas para sugerir.

Para agregar una pregunta, copiá una entrada, cambiá el id y completá los campos.
"""

PROCESOS = {
    "general": "General",
    "controlar": "Controlar",
    "netting": "Netting",
    "liberacion": "Liberación",
}

PREGUNTAS = [
    # =========================================================================== GENERAL
    {
        "id": "gen_que_es",
        "proceso": "general",
        "pregunta": "¿Qué hace esta app?",
        "claves": "para que sirve objetivo glucovil macro reemplaza resumen",
        "respuesta": (
            "Reemplaza las macros de Excel del proceso de liquidaciones de Glucovil. Tiene tres etapas que se "
            "hacen en orden:\n"
            "• Controlar: carga los reportes de SAP (044, 090 y 077), controla cada liquidación y pasa las "
            "controladas al Histórico de controlados.\n"
            "• Netting: arma las propuestas de pago de 24 y 48 hs por beneficiario, con lo que se paga y lo que se "
            "descuenta.\n"
            "• Liberación: controla los netting generados en E1 contra las propuestas, arma el Output E1 y pasa lo "
            "pagado al Histórico de pagados.\n"
            "Todo queda en la computadora: no usa OneDrive, SharePoint ni Excel."
        ),
        "pantalla": "inicio",
        "relacionadas": ["gen_orden", "gen_archivos_data"],
    },
    {
        "id": "gen_orden",
        "proceso": "general",
        "pregunta": "¿En qué orden se usan las tres etapas?",
        "claves": "flujo pasos secuencia primero despues circuito dia",
        "respuesta": (
            "1. Controlar: cada vez que bajás un 044 nuevo. Las liquidaciones que marcás como controladas pasan al "
            "Histórico de controlados.\n"
            "2. Netting: el día de netting. Toma el Histórico de controlados, el 077 y el 090 y arma las propuestas. "
            "Al dar salida, los documentos quedan registrados como EN PROPUESTA.\n"
            "3. Liberación: después de generar los netting en E1. Primero se controlan los pagos con el 020 y el "
            "067 y se genera el Output E1; cuando E1 los liberó, se limpian las pagadas con un 020 nuevo.\n"
            "Cada etapa usa lo que dejó la anterior, por eso conviene no saltear pasos."
        ),
        "relacionadas": ["gen_que_es", "net_registro"],
    },
    {
        "id": "gen_archivos_data",
        "proceso": "general",
        "pregunta": "¿Qué archivos hay en la carpeta data y para qué sirve cada uno?",
        "claves": "carpeta data archivos donde se guarda historico pagados registro netting propuestos",
        "respuesta": (
            "• 044, 090, 077, 020, 067: los reportes que bajás de SAP/E1. La app toma el más nuevo de cada uno.\n"
            "• Historico_Documentos_Controlados.xlsx: lo escribe Controlar; es lo que entra al Netting.\n"
            "• historico_pagados.xlsx: lo escribe Liberación al limpiar; lo que está acá no vuelve a controlarse "
            "ni a netearse.\n"
            "• Netting_Propuestos.xlsx: registro de cada documento propuesto, con su N° de propuesta, ID de pago "
            "y estado (EN PROPUESTA, CON ID DE PAGO, LIBERADO).\n"
            "• Propuestas_Netting.xlsx: la salida del Netting para trabajar en E1.\n"
            "• Netting_liberar.xlsx: el Output E1 con los IDs a liberar.\n"
            "No borres los históricos ni el registro: son la memoria del proceso."
        ),
        "relacionadas": ["gen_backup", "net_registro"],
    },
    {
        "id": "gen_backup",
        "proceso": "general",
        "pregunta": "¿La app hace copias de seguridad?",
        "claves": "backup copia respaldo recuperar perdi borrado deshacer",
        "respuesta": (
            "Sí, antes de los cambios que no se pueden deshacer:\n"
            "• Limpiar pagadas guarda una copia «_backup_fecha_hora» del Histórico de controlados y del de pagados.\n"
            "• Si el Histórico de controlados tiene un encabezado que no se reconoce, se guarda una copia antes de "
            "arrancar uno nuevo.\n"
            "Para volver atrás, cerrá la app, renombrá la copia con el nombre original y volvé a abrir."
        ),
        "relacionadas": ["gen_archivos_data", "lib_limpiar"],
    },
    {
        "id": "gen_excel_abierto",
        "proceso": "general",
        "pregunta": "Me dice que no pudo guardar un archivo. ¿Qué hago?",
        "claves": "error guardar permiso permissionerror abierto excel bloqueado no se pudo actualizar",
        "respuesta": (
            "Casi siempre es porque el archivo está abierto en Excel: Windows no deja escribirlo. Cerralo y volvé "
            "a apretar el botón. No se pierde nada: la app no cambia los archivos hasta poder guardarlos.\n"
            "Si sigue pasando, fijate que la carpeta no sea de solo lectura y que el archivo no esté sincronizándose."
        ),
    },
    {
        "id": "gen_volver",
        "proceso": "general",
        "pregunta": "¿Cómo me muevo entre pantallas?",
        "claves": "navegar volver atras menu ruta barra",
        "respuesta": (
            "Arriba está el botón «← Volver», que te lleva a la pantalla anterior, y la ruta (por ejemplo "
            "Menú principal › Netting › Revisar propuestas): cada parte se puede clickear para ir directo.\n"
            "Mientras la app está procesando algo, la navegación se bloquea hasta que termine."
        ),
    },
    {
        "id": "gen_prueba",
        "proceso": "general",
        "pregunta": "¿Cómo pruebo la app sin tocar mis datos reales?",
        "claves": "prueba demo test datos inventados copia simulacion ensayo",
        "respuesta": (
            "Desde la carpeta del repo corré:\n"
            "• py prueba_demo\\preparar_demo.py: arma una copia aparte (…-DEMO) con datos inventados y fechas del día, "
            "más un GUION.md con los pasos y los resultados esperados.\n"
            "• py prueba_e2e\\preparar_copia.py: lo mismo con fechas fijas (fecha de proceso 09/11/2026).\n"
            "Después abrí la app desde esa copia (cd a la carpeta y py -m gui.app). Tu carpeta data no se toca."
        ),
    },
    # =========================================================================== CONTROLAR
    {
        "id": "ctl_cargar",
        "proceso": "controlar",
        "pregunta": "¿Qué archivos necesito para controlar y de dónde los saca?",
        "claves": "cargar bases 044 090 077 reportes sap prefijo automatico procesar",
        "respuesta": (
            "Necesita el 044 (liquidaciones), el 090 (contratos) y el 077. En «Cargar bases» se toman solos de la "
            "carpeta data: el archivo más nuevo cuyo nombre empieza con 044, 090 o 077. También tienen que existir "
            "el Histórico de controlados y el Histórico de pagados.\n"
            "Bajá los reportes, guardalos en data con ese prefijo en el nombre y apretá «Procesar»."
        ),
        "pantalla": "carga",
        "relacionadas": ["ctl_macro_manual", "ctl_que_controla"],
    },
    {
        "id": "ctl_que_controla",
        "proceso": "controlar",
        "pregunta": "¿Qué controla la app en cada liquidación?",
        "claves": "controles validaciones reglas chequea revisa",
        "respuesta": (
            "Para cada liquidación del 044:\n"
            "• Que no esté ya controlada (Histórico de controlados): si está, no aparece.\n"
            "• Que el contrato exista en el 090.\n"
            "• Que no haya otra con el mismo COE y N° fiscal en el histórico (REVISAR).\n"
            "• Que no esté ya pagada (Histórico de pagados).\n"
            "• Que el beneficiario sea el vendedor, el corredor o un cesionario.\n"
            "• Que el volumen cedido no supere las unidades del contrato.\n"
            "También calcula la fecha de pago según la condición, pero ese control todavía es informativo."
        ),
        "relacionadas": ["ctl_macro_manual", "ctl_motivos"],
    },
    {
        "id": "ctl_macro_manual",
        "proceso": "controlar",
        "pregunta": "¿Qué diferencia hay entre CONTROL MACRO y CONTROL MANUAL?",
        "claves": "resultado final macro manual diferencia estado",
        "respuesta": (
            "• CONTROL MACRO: pasó todos los controles. Solo hay que verificarla contra la Power App y marcarla "
            "como controlada.\n"
            "• CONTROL MANUAL: falló algún control; la columna «Motivo» dice cuál. Hay que revisarla a mano antes de "
            "darla por controlada (o dejarla pendiente)."
        ),
        "pantalla": "visualizacion",
        "relacionadas": ["ctl_motivos", "ctl_marcar"],
    },
    {
        "id": "ctl_motivos",
        "proceso": "controlar",
        "pregunta": "¿Qué significa cada motivo de control manual?",
        "claves": "sin match 090 revisar ya pagado error beneficiario error cesion motivo",
        "respuesta": (
            "• SIN MATCH 090: el contrato de la liquidación no está en el 090. Revisá el contrato o bajá un 090 "
            "más completo.\n"
            "• REVISAR: ya hay en el Histórico una liquidación con el mismo COE y N° fiscal (pero otra fecha de "
            "pago). Puede ser un duplicado o una reliquidación.\n"
            "• YA PAGADO: el documento está en el Histórico de pagados.\n"
            "• ERROR BENEFICIARIO: el beneficiario del pago no es el vendedor, ni el corredor, ni hay cesión.\n"
            "• ERROR CESION: el volumen cedido es mayor que las unidades originales del contrato en el 090."
        ),
        "relacionadas": ["ctl_revisar", "ctl_macro_manual"],
    },
    {
        "id": "ctl_revisar",
        "proceso": "controlar",
        "pregunta": "¿Por qué una liquidación sale como REVISAR?",
        "claves": "revisar duplicada coe numero fiscal id corto repetida",
        "respuesta": (
            "Porque en el Histórico de controlados ya hay un documento con el mismo COE y el mismo N° de documento "
            "fiscal (el «id corto»), aunque con otra fecha de pago o número. Suele ser una liquidación que se "
            "volvió a emitir. Compará las dos antes de controlarla."
        ),
        "pantalla": "busqueda",
        "relacionadas": ["ctl_ya_controlada"],
    },
    {
        "id": "ctl_ya_controlada",
        "proceso": "controlar",
        "pregunta": "¿Por qué no aparece una liquidación que está en el 044?",
        "claves": "no aparece falta desaparecio filtrada ya controlada id largo",
        "respuesta": (
            "Seguramente ya está en el Histórico de controlados: la app compara el «id largo» (tipo + número de "
            "documento + COE + N° fiscal + fecha de pago) y saca las que ya se controlaron. Al procesar, el resumen "
            "dice cuántas se filtraron. Si cambió la fecha de pago, vuelve a aparecer (y probablemente como "
            "REVISAR)."
        ),
        "relacionadas": ["ctl_revisar"],
    },
    {
        "id": "ctl_marcar",
        "proceso": "controlar",
        "pregunta": "¿Cómo marco una liquidación como controlada?",
        "claves": "marcar controlada tildar check detalle visualizar",
        "respuesta": (
            "En «Visualizar liquidaciones» abrí la liquidación (doble clic o «Ver detalle»). En el detalle tenés "
            "todos los datos, el total y «✓ Marcar como controlada»; con «Controlada y siguiente ›» la marcás y "
            "pasás a la próxima sin volver a la lista. También podés usar «Marcar controlado» desde la lista."
        ),
        "pantalla": "visualizacion",
        "relacionadas": ["ctl_copiar", "ctl_limpieza"],
    },
    {
        "id": "ctl_copiar",
        "proceso": "controlar",
        "pregunta": "¿Cómo copio el COE u otro dato para compararlo con la Power App?",
        "claves": "copiar coe portapapeles comparar power app dato",
        "respuesta": (
            "En el detalle de la liquidación hacé clic en cualquier dato (o en «⧉ Copiar») para copiarlo. También "
            "podés pegar un dato de la Power App en «Comparar con la PowerApp» y la app te dice si coincide con "
            "algún dato de la liquidación (ignora puntos, guiones y espacios). En la lista, clic derecho sobre una "
            "celda para copiarla."
        ),
        "pantalla": "visualizacion",
    },
    {
        "id": "ctl_filtros",
        "proceso": "controlar",
        "pregunta": "¿Puedo filtrar por fecha de pago o buscar un documento?",
        "claves": "filtrar fecha pago buscar documento buscador global",
        "respuesta": (
            "Sí. En «Visualizar liquidaciones» podés filtrar por fecha de pago y por tipo (parciales, finales, "
            "comisiones, ajustes), y ves el N° de "
            "documento interno, la forma de pago y el tipo de liquidación en cada fila. Para buscar por cualquier "
            "dato (contrato, COE, beneficiario) usá el «Buscador global»."
        ),
        "pantalla": "busqueda",
    },
    {
        "id": "ctl_limpieza",
        "proceso": "controlar",
        "pregunta": "¿Qué hace la Limpieza de controladas?",
        "claves": "limpieza pasar historico registrar controladas eliminar",
        "respuesta": (
            "Pasa al Histórico de controlados todas las liquidaciones que marcaste como controladas y las saca de "
            "la lista. Desde ese momento están disponibles para el Netting y, si vuelven a venir en un 044, no se "
            "muestran. Las que no marcaste quedan en la app para seguir revisándolas."
        ),
        "pantalla": "limpieza",
        "relacionadas": ["net_que_toma"],
    },
    {
        "id": "ctl_historico_error",
        "proceso": "controlar",
        "pregunta": "Me dice que no encuentra el encabezado del Histórico. ¿Qué pasó?",
        "claves": "error encabezado historico titulos no encontro columnas",
        "respuesta": (
            "El archivo de Histórico de controlados no tiene la fila de títulos esperada (por ejemplo, porque se "
            "copió uno de otra macro). Al pasar al histórico, la app guarda una copia del archivo viejo y arranca "
            "uno nuevo con los títulos correctos, alineando las columnas por nombre."
        ),
    },
    # =========================================================================== NETTING
    {
        "id": "net_que_toma",
        "proceso": "netting",
        "pregunta": "¿Qué archivos usa el Netting?",
        "claves": "archivos netting insumos historico 077 090 compensas",
        "respuesta": (
            "Tres archivos:\n"
            "• Histórico de controlados (lo que dejó Controlar): lo que se paga.\n"
            "• 077: lo que se descuenta (RI, RT, RM, AH, X@, X&…).\n"
            "• 090: para saber a qué corredor y vendedor corresponde cada contrato.\n"
            "No usa el Excel de compensas ni el de control de la macro. Además excluye lo que ya está en el "
            "Histórico de pagados y lo que ya salió en una propuesta abierta."
        ),
        "pantalla": "netting_carga",
        "relacionadas": ["net_fecha", "net_registro"],
    },
    {
        "id": "net_fecha",
        "proceso": "netting",
        "pregunta": "¿Qué es la fecha de proceso y cómo arma las ventanas de 24 y 48 hs?",
        "claves": "fecha proceso dias a pagar 24 48 horas ventana feriados habiles",
        "respuesta": (
            "Es el día del netting (por defecto, hoy). Para cada documento se cuentan los días hábiles hasta su "
            "fecha de pago, salteando fines de semana y feriados:\n"
            "• 0 o 1 día (vence hoy, mañana o ya venció): propuesta de 24 hs.\n"
            "• 2 días: propuesta de 48 hs.\n"
            "• Más: todavía no entra.\n"
            "Si ponés una fecha equivocada puede no salir ninguna propuesta: la app te avisa y te muestra las "
            "próximas fechas de pago."
        ),
        "pantalla": "netting_carga",
        "relacionadas": ["net_sin_propuestas", "net_feriados"],
    },
    {
        "id": "net_sin_propuestas",
        "proceso": "netting",
        "pregunta": "No sale ninguna propuesta. ¿Por qué?",
        "claves": "no sale nada cero propuestas vacio sin propuestas",
        "respuesta": (
            "Las causas más comunes:\n"
            "• La fecha de proceso no es la correcta: ningún documento vence en 24 o 48 hs. El aviso te dice las "
            "próximas fechas de pago del histórico.\n"
            "• El Histórico de controlados está vacío: primero hay que controlar y pasar al histórico.\n"
            "• Los documentos ya salieron en una propuesta (están EN PROPUESTA en el registro) o ya están pagados.\n"
            "Revisá los «Avisos» de la pantalla de revisión: dicen cuántos documentos se excluyeron y por qué."
        ),
        "relacionadas": ["net_fecha", "net_registro"],
    },
    {
        "id": "net_tipos_benef",
        "proceso": "netting",
        "pregunta": "¿Qué significan CORREDOR, VENDEDOR, CORREDOR-DIRECTO y VENDEDOR-CESION?",
        "claves": "tipo beneficiario corredor vendedor directo cesion banco",
        "respuesta": (
            "Es a quién se le paga, como en la macro:\n"
            "• CORREDOR: el beneficiario es el corredor; sus liquidaciones de distintos vendedores van en un mismo "
            "paquete y se descuentan los documentos de esos vendedores.\n"
            "• VENDEDOR: el vendedor cobra directo (sin corredor).\n"
            "• CORREDOR-DIRECTO: hay corredor, pero se le paga al vendedor.\n"
            "• VENDEDOR-CESION: el pago está cedido (por ejemplo, a un banco); se paga al cesionario."
        ),
        "pantalla": "netting_revision",
    },
    {
        "id": "net_descuentos",
        "proceso": "netting",
        "pregunta": "¿Cómo decide qué documentos del 077 se descuentan?",
        "claves": "descuentos 077 ri rt rm ah facturas descontar cobrar compensar",
        "respuesta": (
            "Toma del 077 los tipos que descuenta la macro (RI, RT, RM, AH, X@, X&…) y los asocia al cliente y al "
            "contrato usando el 090. Se descartan los de otros tipos y los que tienen un contrato que no está en el "
            "090 (los avisos dicen cuántos). En cada paquete ves en rojo lo que se descuenta y en azul lo que se paga."
        ),
        "relacionadas": ["net_neto_negativo"],
    },
    {
        "id": "net_neto_negativo",
        "proceso": "netting",
        "pregunta": "¿Qué pasa si los descuentos superan lo que se paga?",
        "claves": "neto negativo descuento mayor saldo deudor",
        "respuesta": (
            "El paquete queda con neto negativo y aparece en los avisos para revisar. En E1 no se puede generar un "
            "netting negativo: hay que sacar algún descuento (dejar la factura para otro netting) o esperar a que "
            "entre otra liquidación del mismo beneficiario."
        ),
    },
    {
        "id": "net_revisar",
        "proceso": "netting",
        "pregunta": "¿Qué puedo hacer en Revisar propuestas?",
        "claves": "revisar propuestas paquete accion observaciones grupo analistas repartir",
        "respuesta": (
            "Ves la lista de paquetes a la izquierda y el detalle a la derecha, como el formulario de la macro:\n"
            "• Acción y Observaciones de cada paquete (por ejemplo PERMUTA).\n"
            "• «Mi grupo» y «Repartir» para dividir los paquetes entre analistas.\n"
            "• «Por fecha de pago» para ver totales por día.\n"
            "• «Avisos» con todo lo que conviene revisar antes de dar salida."
        ),
        "pantalla": "netting_revision",
        "relacionadas": ["net_salida"],
    },
    {
        "id": "net_salida",
        "proceso": "netting",
        "pregunta": "¿Qué genera «Dar salida»?",
        "claves": "dar salida propuestas netting xlsx archivo exportar",
        "respuesta": (
            "Genera Propuestas_Netting.xlsx con:\n"
            "• Propuestas_24 / Propuestas_48: un bloque por AB con lo que se paga y lo que se descuenta.\n"
            "• Detalle_24 / Detalle_48: las mismas filas en el formato de la macro.\n"
            "• Control: fecha de proceso, archivos usados y totales.\n"
            "Además registra cada documento en Netting_Propuestos.xlsx como EN PROPUESTA y actualiza el último N° "
            "de propuesta."
        ),
        "pantalla": "netting_salida",
        "relacionadas": ["net_registro", "lib_corrida"],
    },
    {
        "id": "net_registro",
        "proceso": "netting",
        "pregunta": "¿Por qué un documento no vuelve a salir en el Netting?",
        "claves": "registro propuestos en propuesta bloquear duplicado no vuelve anulada",
        "respuesta": (
            "Porque ya está en una propuesta abierta del registro (Netting_Propuestos.xlsx) o porque ya se pagó "
            "(Histórico de pagados). Así no se propone dos veces lo mismo. Vuelve a entrar si en el registro su "
            "estado pasa a ANULADA. Se puede desactivar con la opción «bloquear propuestos» de la pantalla de carga."
        ),
        "relacionadas": ["gen_archivos_data"],
    },
    {
        "id": "net_numero",
        "proceso": "netting",
        "pregunta": "¿De dónde sale el N° de propuesta?",
        "claves": "numero propuesta ultimo n correlativo numeracion",
        "respuesta": (
            "Es correlativo: la app arranca desde el «último N°» de la pantalla de carga y suma uno por paquete. Al "
            "dar salida se guarda el último usado para la próxima vez. Si lo necesitás, lo podés corregir antes de "
            "armar las propuestas."
        ),
        "pantalla": "netting_carga",
    },
    {
        "id": "net_feriados",
        "proceso": "netting",
        "pregunta": "¿Dónde se cargan los feriados?",
        "claves": "feriados dias no laborables calendario config",
        "respuesta": (
            "Están en config\\netting.json, en la lista «feriados» (formato aaaa-mm-dd). Vienen los de la macro más "
            "los de 2026. Agregá los nuevos ahí con la app cerrada."
        ),
    },
    {
        "id": "net_estatus",
        "proceso": "netting",
        "pregunta": "¿Qué significa el aviso de documentos que no están en estatus A o P?",
        "claves": "estatus a p alerta contrato parciales id de pago",
        "respuesta": (
            "E1 genera el ID de pago solo cuando todas las liquidaciones del contrato están en estatus A o P. Si "
            "alguna está en otro estatus, el paquete se marca con una alerta: conviene resolverlo antes de generar "
            "el netting en E1."
        ),
    },
    # =========================================================================== LIBERACIÓN
    {
        "id": "lib_que_hace",
        "proceso": "liberacion",
        "pregunta": "¿Cuáles son los pasos de Liberación?",
        "claves": "liberacion pasos proceso liberar pagos e1",
        "respuesta": (
            "Tres pasos, como la macro de Liberación:\n"
            "1. Controlar pagos: con el 020 y el 067 bajados después de generar los netting en E1, la app busca el "
            "ID de cada propuesta y controla montos, documentos y estados.\n"
            "2. Revisar y liberar: revisás paquete por paquete, liberás a mano los que corresponda y generás el "
            "Output E1 para subir.\n"
            "3. Limpiar pagadas: con un 020 nuevo, lo que ya está liberado pasa del Histórico de controlados al de "
            "pagados."
        ),
        "pantalla": "liberacion",
        "relacionadas": ["lib_archivos", "lib_controles"],
    },
    {
        "id": "lib_archivos",
        "proceso": "liberacion",
        "pregunta": "¿Qué archivos necesito para controlar los pagos?",
        "claves": "020 067 reporte pagos cobros vouchers archivos liberacion",
        "respuesta": (
            "• Las propuestas: la corrida de netting que diste de salida en la app (o un Propuestas_Netting.xlsx).\n"
            "• 020 «Reporte de Pagos y Cobros»: de acá salen los IDs de pago y lo que tomó E1.\n"
            "• 067 «Vouchers pendientes de liberação»: instrumentos de pago y la cuenta K.\n"
            "El 020 y el 067 se toman solos de data (el más nuevo; el que dice «limpiar» queda para la limpieza)."
        ),
        "pantalla": "liberacion_control",
        "relacionadas": ["lib_corrida", "lib_id"],
    },
    {
        "id": "lib_corrida",
        "proceso": "liberacion",
        "pregunta": "No me aparece ninguna corrida para controlar. ¿Por qué?",
        "claves": "no hay corridas pendientes corrida registro vacia liberacion",
        "respuesta": (
            "Las corridas salen del registro de Netting: aparecen las que diste de salida y tienen documentos sin "
            "liberar. Si no hay ninguna:\n"
            "• No se dio salida al Netting (o salió sin propuestas: revisá la fecha de proceso).\n"
            "• Todo lo de esas corridas ya está LIBERADO.\n"
            "También podés elegir «Archivo Propuestas_Netting» y controlar un archivo de la macro."
        ),
        "pantalla": "liberacion_control",
        "relacionadas": ["net_sin_propuestas"],
    },
    {
        "id": "lib_id",
        "proceso": "liberacion",
        "pregunta": "¿Tengo que cargar los IDs de pago a mano?",
        "claves": "id pago cargar manual id transaccion netting e1 buscar",
        "respuesta": (
            "No. La app busca en el 020 el primer documento de cada propuesta (número y tipo) y toma su ID de "
            "transacción, como la macro. Ese ID queda guardado en el registro de Netting (estado CON ID DE PAGO). "
            "Si ningún documento está en el 020, el paquete sale como NO SE ENCONTRO."
        ),
        "relacionadas": ["lib_no_encontro"],
    },
    {
        "id": "lib_controles",
        "proceso": "liberacion",
        "pregunta": "¿Qué controla en cada paquete?",
        "claves": "controles montos tipo doc cronologia monto por liberar devengados permuta cuenta k saldo",
        "respuesta": (
            "Por cada documento de la propuesta, comparado con lo que tomó E1 en el 020:\n"
            "• Montos: que el importe coincida (MONTO - MAYOR / MENOR o NO SE ENCONTRO DOCUMENTO).\n"
            "• Tipo doc: que haya al menos una liquidación L#.\n"
            "• Cronología: que no haya un documento pagado después de uno que no se pagó.\n"
            "• Por liberar: si quedó algo sin pagar, la cuenta K del 067 no tiene que tener saldo.\n"
            "• Devengados: que E1 no haya tomado descuentos que no estaban en la propuesta.\n"
            "• Permuta: si la acción es PERMUTA, el 020 tiene que decir Permuta = S.\n"
            "Si todo da OK, el paquete queda en LIBERAR; si no, en MANUAL."
        ),
        "pantalla": "liberacion_revision",
        "relacionadas": ["lib_estados_control", "lib_manual"],
    },
    {
        "id": "lib_estados_control",
        "proceso": "liberacion",
        "pregunta": "¿Qué significa cada resultado: NO SE ENCONTRO, COMPENSA, MANUAL o LIBERAR?",
        "claves": "estados resultado compensa q4 qj no se encontro significado control paquete",
        "respuesta": (
            "• LIBERAR: todo coincide; entra al Output E1.\n"
            "• MANUAL: algún control falló; hay que revisarlo. No entra al Output salvo que lo liberes a mano.\n"
            "• COMPENSA-LIBERAR / COMPENSA-MANUAL: igual, pero el paquete tiene compensaciones Q4/QJ.\n"
            "• LIBERACION MANUAL: lo liberaste a mano después de revisarlo; entra al Output.\n"
            "• NO SE ENCONTRO: ningún documento de la propuesta está en el 020."
        ),
        "relacionadas": ["lib_manual", "lib_no_encontro"],
    },
    {
        "id": "lib_manual",
        "proceso": "liberacion",
        "pregunta": "¿Cuándo uso «Liberación manual»?",
        "claves": "liberacion manual aprobar forzar liberar igual paquete manual que hago",
        "respuesta": (
            "Cuando un paquete quedó en MANUAL, lo revisaste y está bien liberarlo igual (por ejemplo, una "
            "diferencia que ya se explicó). Pasa a LIBERACION MANUAL y entra al próximo Output E1. Si no "
            "corresponde liberarlo, dejalo en MANUAL y resolvelo en E1."
        ),
        "pantalla": "liberacion_revision",
        "relacionadas": ["lib_output"],
    },
    {
        "id": "lib_no_encontro",
        "proceso": "liberacion",
        "pregunta": "¿Por qué un paquete sale NO SE ENCONTRO?",
        "claves": "no se encontro sin id no esta en el 020 netting no generado",
        "respuesta": (
            "Ningún documento de la propuesta está en el 020. Puede ser que el netting no se haya generado en E1, "
            "que el 020 se haya bajado antes, o que no cubra esas fechas. Generá el netting y volvé a bajar el 020."
        ),
    },
    {
        "id": "lib_ya_liberado",
        "proceso": "liberacion",
        "pregunta": "¿Qué pasa con los pagos que ya están en estado A o P?",
        "claves": "ya liberado estado a p transmitido a9 liberado e1 filtro",
        "respuesta": (
            "Ya están liberados en E1 (A = Liberado, P = Transmitido a A9). No entran al Output E1 para no "
            "mandarlos dos veces; los ves con el filtro «Ya liberados». En la limpieza, A y P cuentan como pagados."
        ),
        "relacionadas": ["lib_limpiar"],
    },
    {
        "id": "lib_output",
        "proceso": "liberacion",
        "pregunta": "¿Qué es el Output E1 y qué hago con él?",
        "claves": "output e1 netting liberar xlsx subir liberar ids archivo",
        "respuesta": (
            "Es el archivo con los IDs a liberar (hoja E1: ID, estado y «SECUNDARIA»), igual al de la macro. Entran "
            "los paquetes en LIBERAR y LIBERACION MANUAL. Si el archivo ya existe, los IDs se agregan al final. "
            "Después lo subís en E1 para liberar los pagos."
        ),
        "pantalla": "liberacion_revision",
        "relacionadas": ["lib_limpiar"],
    },
    {
        "id": "lib_24_48",
        "proceso": "liberacion",
        "pregunta": "¿Cómo controlo las propuestas de 24 y de 48 hs?",
        "claves": "ventana 24 48 controlar ambas dos veces",
        "respuesta": (
            "Como en la macro, una ventana por vez: controlá 24 hs, revisá y generá el Output; después volvé a "
            "«Controlar pagos», elegí 48 hs y repetí. El Output se agrega al mismo archivo."
        ),
        "pantalla": "liberacion_control",
    },
    {
        "id": "lib_limpiar",
        "proceso": "liberacion",
        "pregunta": "¿Cómo funciona «Limpiar pagadas»?",
        "claves": "limpiar pagadas liquidaciones pagadas mover historico pagados vista previa",
        "respuesta": (
            "Bajá el 020 de nuevo (desde la fecha del netting hasta la de liberación) y guardalo en data con "
            "«limpiar» en el nombre. Poné la fecha de netting y la de acreditación y hacé la «Vista previa»: muestra "
            "qué documentos se van a mover, cuáles siguen pendientes de pago y qué renglones no están liberados. "
            "Al confirmar, se guardan copias de los dos históricos y lo pagado pasa del Histórico de controlados al "
            "de pagados; en el registro quedan como LIBERADO."
        ),
        "pantalla": "liberacion_limpieza",
        "relacionadas": ["lib_diferencias", "gen_backup"],
    },
    {
        "id": "lib_pendientes",
        "proceso": "liberacion",
        "pregunta": "¿Qué son los «pendientes de pago» de la limpieza?",
        "claves": "pendientes de pago quedaron sin pagar vencidas limpieza",
        "respuesta": (
            "Documentos que siguen en el Histórico de controlados con fecha de pago igual o anterior a la de "
            "acreditación, pero que el 020 no muestra pagados. Revisalos: puede ser un paquete que quedó en MANUAL, "
            "uno que no se neteó o un 020 que no cubre esas fechas."
        ),
    },
    {
        "id": "lib_diferencias",
        "proceso": "liberacion",
        "pregunta": "¿En qué se diferencia de la macro de Liberación?",
        "claves": "diferencias macro distinto cambios desvio",
        "respuesta": (
            "Hace los mismos controles, con algunos cambios a propósito:\n"
            "• Al limpiar mueve todas las filas del documento (Controlar guarda varias por documento).\n"
            "• Por defecto solo mueve pagos liberados (A o P); se puede destildar.\n"
            "• Guarda copias de los históricos antes de modificarlos.\n"
            "• El Output E1 no incluye lo que ya está liberado en E1.\n"
            "• Los IDs de pago quedan registrados en el registro de Netting."
        ),
    },
]
