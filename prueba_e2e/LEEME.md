# Prueba de punta a punta: CONTROLAR → NETTING → LIBERACIÓN

Todos los datos son **inventados** (clientes "… PRUEBA SA", AB 3599xxxx / 4299xxxx, compañía 99999).
La prueba corre en una **copia aparte de la app**, así no se mezcla con tu `data` real.

## 0. Preparar la copia

Desde la carpeta del repo:

```
py prueba_e2e\preparar_copia.py
cd ..\macro-controles-gluco-v2-PRUEBA
py -m gui.app
```

La copia arranca con un Histórico de controlados con 2 documentos viejos (79013 y 80012), un Histórico
de pagados con 1 (80014) y, en `data`, todos los reportes de la prueba: 044, 090, 077, 020, 067 y el 020 para limpiar.
Como en CONTROLAR, Liberación toma solo de `data` el 020 y el 067 más nuevos (`020_LIMPIAR…` queda para el paso de limpieza).

## 1. CONTROLAR

1. **Controlar → Cargar bases → Procesar** (044, 090 y 077 se toman solos de `data`).
2. Esperado: **15 registros** (la 80012 no aparece porque ya estaba controlada): **10 CONTROL MACRO** y **5 CONTROL MANUAL**:

| Doc | Motivo | Por qué |
|---|---|---|
| 80011 | SIN MATCH 090 | el contrato 903999999A no está en el 090 |
| 80013 | REVISAR | mismo COE y N° fiscal que la 79013 del histórico |
| 80014 | YA PAGADO | está en el Histórico de pagados |
| 80015 | ERROR CESION | cede 99.999 kg y el contrato tiene 50.000 |
| 80016 | ERROR BENEFICIARIO | el beneficiario no es el vendedor ni el corredor |

3. En **Visualizar**, marcá como controladas las 10 CONTROL MACRO (80001 a 80010); las 5 manuales no.
4. **Limpieza de controladas → Pasar al histórico**: "Se registraron 10 liquidación(es)".

## 2. NETTING

> **Importante:** la fecha de proceso tiene que ser **09/11/2026**, no la de hoy que propone la pantalla.
> Las liquidaciones de la prueba pagan el 10/11 y el 11/11: con otra fecha no entran en 24 ni 48 hs y no sale
> ninguna propuesta (y Liberación no tiene nada que controlar).

1. **Netting → Armar propuestas**:
   - Histórico: `data\Historico_Documentos_Controlados.xlsx`
   - 077: `data\077_PRUEBA.xlsx`
   - 090: `data\090_PRUEBA.xlsx`
   - Fecha de proceso **09/11/2026**, último N° **54700**.
   - Va a avisar que los archivos son anteriores a la fecha de proceso: es normal en la prueba.
2. Esperado: 077 con 7 documentos → 1 de otro tipo (ZZ) y 1 sin contrato en el 090 (RM 61003) → **5 para descontar**.

| N° | Ventana | Beneficiario | Tipo | A pagar | A descontar | Neto |
|---|---|---|---|---|---|---|
| 54701 | 24 | CORREDORA PAMPEANA PRUEBA SA | CORREDOR | 80001, 80002, 80003 (C0) = 21.050.000 | RI 61001, AH 61002 = -1.550.000 | 19.500.000 |
| 54702 | 24 | AGROSUR PRUEBA SRL | CORREDOR | 80008 = 7.250.000 | RT 61005, X@ 61007 = -700.000 | 6.550.000 |
| 54703 | 24 | CAMPO NUEVO PRUEBA SA | VENDEDOR | 80004, 80005 (H7) = 6.550.000 | RI 61004 = -900.000 | 5.650.000 |
| 54704 | 24 | BANCO PRUEBA SA | VENDEDOR-CESION | 80007 = 4.000.000 | — | 4.000.000 |
| 54705 | 48 | LOS TALAS PRUEBA SH | CORREDOR-DIRECTO | 80006 = 9.100.000 | — | 9.100.000 |

80009 (paga 18/11), 80010 (29/11), 79013 (20/11) y 80012 (25/11) quedan afuera: no vencen todavía.

3. **Dar salida** → `Propuestas_Netting.xlsx` (comparalo con `prueba_e2e\esperado\Propuestas_Netting.xlsx`).

## 3. LIBERACIÓN

### Controlar 24 hs
**Liberación → Controlar pagos**:
- corrida de netting de la app, **24 hs**
- 020 y 067: ya aparecen cargados desde `data` (`020_PRUEBA.xlsx` y `067_PRUEBA.xlsx`)

| N° | ID | Control | Por qué |
|---|---|---|---|
| 54701 | 2147100001 | **LIBERAR** | todo coincide (los descuentos vienen en positivo en el 020) |
| 54702 | 2147100002 | Ya liberado | está en estado **P** (Transmitido a A9): filtro «Ya liberados» |
| 54703 | 2147100003 | **MANUAL** | E1 tomó 6.000.000 de la 80004 (la propuesta dice 6.700.000): MONTO - MAYOR y error de cronología |
| 54704 | — | **NO SE ENCONTRO** | el netting de la cesión no se generó en E1 |

### Revisar y liberar
1. Abrí la 54703 → **Liberación manual**.
2. **Generar Output E1** → agrega **2 IDs**: 2147100001 y 2147100003. Guardalo en `data\Netting_liberar.xlsx`.

### Controlar 48 hs
1. Volvé a **Controlar pagos** con **48 hs** (mismos 020 y 067) → **54705 LIBERAR** (ID 2147100005).
2. **Generar Output E1** con el mismo archivo → agrega **1 ID** al final (total 3).
3. Comparalo con `prueba_e2e\esperado\Netting_liberar.xlsx`.

### Limpiar pagadas
1. Datos:
   - 020: aparece cargado `data\020_LIMPIAR_PRUEBA.xlsx` (ya liberado: todo en A, salvo AGROSUR en P)
   - Histórico: `data\Historico_Documentos_Controlados.xlsx`
   - Pagados: `data\historico_pagados.xlsx`
   - Fecha de netting **09/11/2026**, acreditación **11/11/2026**, «solo liberados (A o P)» tildado.
2. **Vista previa**: **7 documentos** para mover (80001, 80002, 80003, 80004, 80005, 80006, 80008) y **1 pendiente de pago** (80007, la cesión que no se neteó).
3. **Limpiar pagadas**. Resultado:
   - El Histórico de controlados queda con 79013, 80012, 80007, 80009 y 80010.
   - El Histórico de pagados suma las 7, con Fecha Netting, Fecha Acreditación e ID de pago.
   - En `data\Netting_Propuestos.xlsx`, todo queda en **LIBERADO** salvo la 54704 (EN PROPUESTA).
   - Se guardan copias `_backup_` de los dos históricos.

Si volvés a correr Netting con la misma fecha, no tiene que proponer nada de lo liberado, y la 80007 no vuelve
a entrar porque sigue en una propuesta abierta (54704).
