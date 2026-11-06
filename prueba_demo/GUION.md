# Demo Glucovil de punta a punta

Datos **inventados** ("… DEMO SA", AB 3699xxxx / 4399xxxx, compañía 99999).

| Fecha | Qué es |
|---|---|
| **{HOY}** | Fecha de proceso de la demo |
| {P24} | Pagos de 24 hs |
| {P48} | Pagos de 48 hs |

En `data` ya están todos los reportes: 044, 090, 077, 020, 067 y el 020 para limpiar.

Para grabar en Windows: **Win + Alt + R** (barra de juegos) o la Herramienta Recortes → Grabar.
Conviene grabar la ventana de la app maximizada.

---

## 1. CONTROLAR (≈ 2 min)

1. **Controlar → Cargar bases**. El 044, el 090 y el 077 se cargan solos desde `data`. **Procesar**.
2. Resultado esperado: **16 registros**: **11 CONTROL MACRO** y **5 CONTROL MANUAL**. La 85017 no aparece porque ya estaba controlada.

| Doc | Motivo | Para mostrar |
|---|---|---|
| 85012 | SIN MATCH 090 | el contrato no está en el 090 |
| 85013 | REVISAR | mismo COE que la 78013 que ya está en el histórico |
| 85014 | YA PAGADO | está en el Histórico de pagados |
| 85015 | ERROR CESION | cede más kilos que el contrato |
| 85016 | ERROR BENEFICIARIO | el beneficiario no es vendedor ni corredor |

3. **Visualizar liquidaciones**:
   - Abrí una (por ejemplo, la 85001) para mostrar el detalle, copiar el COE y compararlo con un dato.
   - Volvé y marcá como controladas las 11 CONTROL MACRO (de 85001 a 85011). Las 5 manuales quedan sin marcar.
4. **Limpieza de controladas → Pasar al histórico**: "Se registraron 11 liquidación(es)".

## 2. NETTING (≈ 3 min)

1. **Netting → Armar propuestas**:
   - Elegí los archivos de `data`: `Historico_Documentos_Controlados.xlsx`, `077_DEMO.xlsx` y `090_DEMO.xlsx`.
   - Dejá la fecha de proceso **{HOY}** y el último N° que aparece (54628).
   - **Armar propuestas**.
2. Resultado: **6 propuestas de 24 hs y 2 de 48 hs**. El 077 trae 6 documentos: se descartan 1 de otro tipo (ZZ) y 1 sin contrato en el 090 (RM 62005), y quedan **4 para descontar**.

| N° | Hs | Beneficiario | Tipo | A pagar | Descuentos | Neto |
|---|---|---|---|---|---|---|
| 54629 | 24 | CEREALES DEL LITORAL DEMO SA | CORREDOR | 85001 + 85002 = 25.000.000 | RI 62001 + AH 62002 = -1.500.000 | 23.500.000 |
| 54630 | 24 | GRANOS DEL CENTRO DEMO SRL | CORREDOR | 85005 = 5.600.000 | RT 62004 = -300.000 | 5.300.000 |
| 54631 | 24 | DON ALBERTO DEMO SA | VENDEDOR | 85003 + 85004 (H7) = 7.280.000 | RI 62003 = -600.000 | 6.680.000 |
| 54632 | 24 | EL OMBU DEMO SA | VENDEDOR | 85006 = 3.900.000 | — | 3.900.000 |
| 54633 | 24 | LOS NOGALES DEMO SA | VENDEDOR | 85008 = 2.300.000 | — | 2.300.000 |
| 54634 | 24 | BANCO DEMO SA | VENDEDOR-CESION | 85007 = 4.500.000 | — | 4.500.000 |
| 54635 | 48 | CEREALES DEL LITORAL DEMO SA | CORREDOR | 85010 = 2.700.000 | — | 2.700.000 |
| 54636 | 48 | LA ESPERANZA DEMO SA | CORREDOR-DIRECTO | 85009 = 6.100.000 | — | 6.100.000 |

La 85011 no entra porque todavía no vence.

3. **Revisar propuestas**:
   - Recorré los paquetes y pasá de 24 a 48 hs.
   - Mostrá «Por fecha de pago».
   - Copiá el AB para buscarlo en E1.
4. **Dar salida** → `Propuestas_Netting.xlsx`. Se guarda en el registro de Netting.

## 3. LIBERACIÓN (≈ 4 min)

### Controlar pagos, 24 hs

**Liberación → Controlar pagos**: corrida de netting de la app, **24 hs**. El 020 y el 067 ya aparecen cargados desde `data`. **Controlar pagos**.

| N° | ID E1 | Control | Por qué |
|---|---|---|---|
| 54629 | 2147200001 | **LIBERAR** | todo coincide |
| 54631 | 2147200002 | **LIBERAR** | todo coincide (con el ajuste H7) |
| 54630 | 2147200003 | **MANUAL** | E1 tomó una RT (62099) que no estaba en la propuesta: «documentos devengados» |
| 54632 | 2147200004 | **MANUAL** | E1 tomó 3.500.000 de 3.900.000 y quedan 400.000 en la cuenta K |
| 54634 | — | **NO SE ENCONTRO** | el netting de la cesión no se generó en E1 |
| 54633 | 2147200006 | Ya liberado | ya está en **A** en E1: filtro «Ya liberados» |

### Revisar y liberar
1. Mostrá los filtros por control, el detalle de los errores y cómo se copia el ID.
2. Abrí la **54632 (EL OMBU) → Liberación manual**. La 54630 queda en MANUAL.
3. **Generar Output E1** → guardalo como `data\Netting_liberar.xlsx`. Se agregan **3 IDs**: 2147200001, 2147200002 y 2147200004.

### Controlar pagos, 48 hs
1. Volvé a **Controlar pagos** con **48 hs** → **54635 y 54636 LIBERAR**.
2. **Generar Output E1** en el mismo archivo → agrega **2 IDs** (5 en total).

### Limpiar pagadas
1. Configuración:
   - El 020 aparece cargado: `020_LIMPIAR_DEMO.xlsx`, el 020 bajado después de liberar. Todo está en A salvo GRANOS DEL CENTRO, que sigue en H.
   - Fecha de netting **{HOY}** y fecha de acreditación **{ACREDITACION}**.
   - Dejá tildado «solo liberados (A o P)».
2. **Vista previa**:
   - **8 documentos** para mover: 85001, 85002, 85003, 85004, 85006, 85008, 85009 y 85010.
   - **2 pendientes de pago**: 85005, la MANUAL que no se liberó, y 85007, la cesión.
   - **3 renglones del 020 no están en A ni P**: los de GRANOS DEL CENTRO.
3. **Limpiar pagadas**. Resultado:
   - El Histórico de controlados queda con 78013, 85017, 85005, 85007 y 85011.
   - El Histórico de pagados suma las 8.
   - En el registro de Netting, todo queda LIBERADO salvo la 54630 (CON ID DE PAGO) y la 54634 (EN PROPUESTA).
   - Se guardan copias `_backup_` de los dos históricos.

Para cerrar la demo, podés volver al **Menú principal**: las tres etapas muestran su estado.
