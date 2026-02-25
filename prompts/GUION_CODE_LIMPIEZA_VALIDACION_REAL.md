# GUIÓN CODE: LIMPIEZA PROFUNDA + VALIDACIÓN REAL

## CONTEXTO CRÍTICO
Los datos de 2026 están llenos de duplicados y errores de clasificación. NO se puede avanzar a ninguna fase nueva hasta que esto esté limpio. Este guión es la PRIORIDAD ABSOLUTA.

## REGLAS
1. SIEMPRE backup antes: `cp finsense.db finsense.db.bak`
2. NUNCA parchear tx individuales → arreglar REGLAS del clasificador
3. NUNCA borrar y reprocesar toda la BBDD → operaciones quirúrgicas

---

## TAREA 1: ELIMINAR DUPLICADOS (CRÍTICO)

### Problema
Casi todas las tx de Trade Republic aparecen DOS VECES:
- Una del CSV histórico con prefijo "Transferencia " o "Otros "
- Una del PDF con descripción limpia

También hay duplicados en Openbank:
- Una con tarjeta completa (5489133068682036)
- Una con tarjeta enmascarada (XXXXXXXXXXXX2036)

### Solución
1. Buscar TODOS los pares: misma fecha + mismo |importe| + mismo banco + misma cuenta
2. Para cada par duplicado: QUEDARSE CON UNO SOLO
   - Preferir la versión SIN prefijo "Otros " o "Transferencia " (la del PDF es más limpia)
   - Preferir la versión con tarjeta enmascarada (es la más reciente de Openbank)
3. ELIMINAR el duplicado de la BBDD (DELETE por hash o id)
4. Reportar: cuántos duplicados eliminados, por banco

### Validación post-limpieza:
- Enero 2026 NO debería tener pares con misma fecha+importe+banco
- El total de tx debería reducirse significativamente

---

## TAREA 2: CORREGIR REGLAS DE CLASIFICACIÓN

### Errores detectados que necesitan REGLAS (no parches):

#### 2A. Tatiana Santallana → GASTO / Vivienda / Limpieza
En el maestro histórico: GASTO / Vivienda / Limpieza ✅
En 2026: sale como TRANSFERENCIA / Externa ❌
Regla: cualquier tx con "Tatiana" + ("Santallana" o "Santillana") → Tipo=GASTO, Cat1=Vivienda, Cat2=Limpieza
Importes típicos: ~65€, ~108€, ~145€, ~181€ (varía por horas de trabajo)

#### 2B. Alejandro Fernández-Castanys → TRANSFERENCIA / Externa (préstamo hermano)
En el maestro: mezcla de Interna y Externa ❌ (debería ser siempre Externa = préstamo)
En 2026: sale como GASTO / Préstamos en una copia ❌
Regla: tx con "Alejandro" + ("Fernández-Castanys" o "Fernandez-Castanys" o "Fernández Castanys" o "FdezCastanys") + importe > 100€ → Tipo=GASTO, Cat1=Préstamos, Cat2=Hermano
NOTA: Alejandro es el hermano de Pablo. Le paga ~954€ trimestrales como devolución de préstamo. Es un GASTO real, no una transferencia interna.

#### 2C. Federico Fernandez-Castanys → TRANSFERENCIA / Interna (hijo)
En 2026: sale como Bizum ❌
Regla: tx con "Federico" + "Fernandez-Castanys" → Tipo=TRANSFERENCIA, Cat1=Interna
Federico es hijo de Pablo. Transferencias a/desde hijos = Interna.

#### 2D. Yolanda Arroyo Varo → TRANSFERENCIA / Cuenta Común
Ya está correcto en 2026 ✅. Verificar que la regla existe.

#### 2E. Nómina = TIMESTAMP SOLUTIONS
Regla actual parece funcionar para Abanca ✅ (4025.21€ en ene 2026)
Verificar que también funciona para Openbank (formato histórico: "TRANSFERENCIA DE TIMESTAMP SOLUTIONS...")

#### 2F. TRANSFERENCIA INTERNA NOMINA → Tipo=TRANSFERENCIA, Cat1=Interna
Es el reenvío automático de la nómina de Abanca a Trade Republic. NO es ingreso ni gasto.

---

## TAREA 3: VALIDACIÓN REAL - CHECKLIST POR MES

Después de limpiar duplicados y corregir reglas, ejecutar este validador para CADA mes.

### Script de validación (crear validate_month.py):

```python
# Para cada mes validado, verificar:

# 1. NÓMINA
# - ¿Hay exactamente 1 tx INGRESO/Nómina de ~4.000€?
# - ¿De Abanca (2026) o de Openbank (2025)?
# - ¿"TRANSFERENCIA INTERNA NOMINA" es TRANSFERENCIA/Interna (NO ingreso)?

# 2. DUPLICADOS
# - ¿Hay pares con misma fecha + mismo |importe| + mismo banco?
# - Si sí → ERROR, hay duplicados sin limpiar

# 3. TATIANA (limpieza)
# - ¿Todas las tx con "Tatiana"/"Santallana" son GASTO/Vivienda/Limpieza?
# - ¿Hay al menos 1-2 pagos a Tatiana por mes? (es recurrente)

# 4. ALEJANDRO (préstamo hermano)
# - ¿Tx con "Alejandro Fernández-Castanys" es GASTO/Préstamos?
# - Debería haber ~1 pago trimestral de ~954€

# 5. TRANSFERENCIAS INTERNAS
# - ¿Todas las tx entre cuentas propias (Openbank↔TR, B100↔B100 Save/Health) son TRANSFERENCIA/Interna?
# - ¿NINGUNA cuenta como ingreso o gasto?

# 6. BIZUM
# - ¿Todos los Bizum son TRANSFERENCIA/Bizum?
# - ¿NINGUNO cuenta como ingreso o gasto en el cálculo?

# 7. B100 SAVE/HEALTH
# - ¿Todos los traspasos entre cuentas B100 son TRANSFERENCIA/Interna?

# 8. COHERENCIA GLOBAL
# - Ingresos del mes ≈ 4.000€ (solo nómina + extras reales)
# - ¿No hay gastos absurdos (>2000€ sin explicación)?
# - ¿Top 5 categorías de gasto son razonables?

# 9. SIN DUPLICADOS EN RESULTADO FINAL
# - Contar tx únicas por fecha+importe+banco
# - Si total_tx != total_únicas → HAY DUPLICADOS

# 10. RESUMEN
# Mostrar: ingresos, gastos, balance, top 5 gastos, alertas
```

### Ejecutar para:
1. Enero 2026
2. Enero 2025
3. Diciembre 2025

### Criterio de éxito REAL:
- [ ] 0 duplicados (misma fecha+importe+banco)
- [ ] 1 nómina por mes (~4k€) como INGRESO
- [ ] Tatiana = GASTO/Vivienda/Limpieza (no Externa)
- [ ] Alejandro = GASTO/Préstamos (cuando aplique)
- [ ] Federico = TRANSFERENCIA/Interna (no Bizum)
- [ ] 0 transferencias internas como ingreso/gasto
- [ ] 0 Bizum como ingreso/gasto
- [ ] 0 B100 Save/Health como ingreso/gasto
- [ ] Ingresos mensuales coherentes (~4k€)
- [ ] Balance mensual razonable

SI ALGUNO FALLA → NO DAR POR COMPLETADA LA FASE. Reportar qué falla y proponer corrección de REGLA.
