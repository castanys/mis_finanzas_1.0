# 📋 Guía de Comunicación con Haiku - Desarrollador

**Objetivo**: Maximizar eficiencia y claridad en la colaboración con Claude Haiku (BUILD mode)

---

## 1️⃣ Estructura de Peticiones Efectivas

### Formato Recomendado

```
[CONTEXTO]
Estoy trabajando en: <qué componente>
Objetivo: <qué quiero lograr>

[PROBLEMA/TAREA]
<descripción clara del qué>
<por qué es importante>

[RESTRICCIONES]
- Usar reglas en classifier/, NO parchear BD
- Verificar con query después
- Mantener español en código

[ENTREGABLES ESPERADOS]
1. <archivo que se debe modificar>
2. <comando de verificación>
3. <resultado esperado>
```

### Ejemplo Real

```
[CONTEXTO]
Estoy en el clasificador de transacciones.
Objetivo: Reducir Cat2="Otros" de 391 a <300

[PROBLEMA]
Hay 78 transacciones Recibos con Cat2="Otros" que podrían 
clasificarse mejor:
- IVA Autoliquidaciones (7) → Cat2="Impuestos"
- WIZINK BANK (3) → Cat2="Tarjeta crédito"
- REPSOL (8) → Cat2="Combustible"

[RESTRICCIONES]
- Crear reglas en classifier/merchants.py
- Reprocesar con reclassify_all.py
- Verificar con: SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'

[ENTREGABLES]
1. Reglas en classifier/merchants.py
2. Output de reclassify_all.py mostrando cambios
3. Verificación: Cat2="Otros" < 300
```

---

## 2️⃣ Cómo Describir Problemas para BUILD

### ✅ BIEN

```
"Añade una regla que clasifique transacciones con 'IVA AUTOLIQUIDACION' 
como Recibos|Impuestos en la Capa 2 de merchants.py. 
Verifica que el cambio funciona reprocesando y contando cuántas 
transacciones se reclasificaron."
```

### ❌ MAL

```
"Mejora el clasificador de impuestos"
```

---

## 3️⃣ Cuándo Escalar a PLAN (no es malo)

**BUILD escala a PLAN cuando:**

```
[ESCALADO A PLAN REQUERIDO]
Problema detectado: Necesito añadir una nueva columna 'confianza' 
a la tabla transacciones para rastrear qué tan segura es cada clasificación

Evidencia: 
- SELECT COUNT(*) FROM transacciones WHERE capa=5  → 31 sin clasificar
- Quiero guardar score de confianza para futuras auditorías

Hipótesis: Necesito cambiar el schema de la BD para persistir este dato

Bloqueo: BUILD no puede modificar constraints ni schema. El cambio 
es estructural, no operativo.

Solicitud a PLAN: ¿Debo crear una tabla separada 'clasificacion_confianza' 
o ampliar la tabla 'transacciones' con una columna nueva?
```

**No temas escalar.** Es mejor un diseño correcto desde el principio que parchear después.

---

## 4️⃣ Verificación de Tareas

Haiku SIEMPRE debe terminar con una verificación explícita:

```bash
# 1. Modificar la regla
# (editar classifier/merchants.py)

# 2. Reprocesar
python3 reclassify_all.py

# 3. VERIFICAR con query
sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat2='Otros';"

# Resultado esperado: < 300
# Resultado actual: 285 ✅
```

Si el número no coincide, Haiku debe investigar por qué.

---

## 5️⃣ Información Clave para Haiku

### Antes de cualquier tarea, Haiku debe saber:

1. **¿Qué significa "NUNCA parchear datos"?**
   - NO: Hacer UPDATE directo en finsense.db
   - SÍ: Modificar regla, reprocesar todo

2. **¿Dónde están las reglas?**
   - `classifier/engine.py` → reglas prioritarias
   - `classifier/merchants.py` → keywords
   - `classifier/tokens.py` → tokens heurísticos
   - `excepciones_clasificacion.json` → casos especiales

3. **¿Cómo reprocesar?**
   - `python3 reclassify_all.py` → reprocesa las 15,912 transacciones
   - Esto actualiza finsense.db automáticamente

4. **¿Cuál es el objetivo final?**
   - 100% cobertura de clasificación
   - 0 Bizum contado como ingreso/gasto
   - 0 transferencias internas contadas como ingreso/gasto

---

## 6️⃣ Flujo Típico de una Tarea

```
1. USUARIO PIDE CAMBIO
   "Reduce Cat2=Otros a < 300"

2. HAIKU ANALIZA
   - ¿Cuántos registros hay ahora?
   - ¿Cuáles se pueden reclasificar?
   - ¿Dónde cambio las reglas?

3. HAIKU MODIFICA
   - Edita classifier/merchants.py
   - Añade nuevas keyword rules

4. HAIKU REPROCESA
   - python3 reclassify_all.py
   - Reporta cuántos cambios hubo

5. HAIKU VERIFICA
   - SELECT COUNT(*) ... WHERE cat2='Otros'
   - Compara: era 391, ahora 285 ✅
   - Verifica que 0 Bizum/Interna se contaron mal

6. HAIKU REPORTA
   - Qué cambió
   - Cuántas transacciones se reclasificaron
   - Confirmación de éxito

7. USUARIO VALIDA
   - Revisa los números
   - Si todo OK: tarea completa
   - Si no: Haiku investiga por qué
```

---

## 7️⃣ Formato de Reporte Final

Cuando Haiku termina una tarea, debe decir:

```
✅ TAREA COMPLETADA: [Título]

Cambios realizados:
- Archivo: classifier/merchants.py
  Línea XXX: Añadida regla "IVA" → Impuestos
  
Reprocesamiento:
- Ejecutado: python3 reclassify_all.py
- Transacciones reclasificadas: 15 (Recibos ahora mejor clasificados)

Verificación:
- Cat2="Otros" antes: 391
- Cat2="Otros" después: 285  ← Meta < 300 ✅
- Bizum como ingreso/gasto: 0 ✅
- Sin clasificar: 31 (sin cambios esperados)

Status: ✅ Objetivo cumplido
```

---

## 8️⃣ Errores Frecuentes a Evitar

| Error | Síntoma | Solución |
|-------|---------|----------|
| No reprocesar después de cambiar regla | Los cambios no se ven en la BD | `python3 reclassify_all.py` obligatorio |
| Confundir Cat1 con Cat2 | Regla añadida pero con subcategoría incorrecta | Revisar `classifier/valid_combos.py` |
| Olvidar cerrar conexiones BD | Archivo .db locked | Asegurar `conn.close()` después de queries |
| Parchear BD directamente | La corrección se pierde al reprocesar | NUNCA hacer UPDATE directo |
| No verificar el resultado | Asumir que funcionó sin confirmar | Siempre ejecutar query de verificación |

---

## 9️⃣ Casos de Uso Comunes

### Caso 1: Añadir una regla de merchant

```
Usuario: "Clasifica transacciones 'RESTAURANT LA PAZ' como Bar"

Haiku:
1. Abre classifier/merchants.py
2. Busca dónde van las reglas de Restauración
3. Añade: ("RESTAURANT LA PAZ", "Restauración", "Bar")
4. python3 reclassify_all.py
5. SELECT COUNT(*) FROM transacciones WHERE cat2='Bar' AND descripcion LIKE '%LA PAZ%';
6. Reporta: "Reclasificadas 4 transacciones → Restauración|Bar"
```

### Caso 2: Investigar transacciones sin clasificar

```
Usuario: "¿Por qué hay 31 transacciones sin clasificar?"

Haiku:
1. python3 analyze_unclassified.py
2. Revisa los resultados
3. Identifica patrones (ej: "TRANSFERENCIA" sin especificar)
4. Propone agregar reglas a transfers.py
5. Reprocesa y verifica
6. Reporta: "31 → 10 sin clasificar (reducción 68%)"
```

### Caso 3: Validar un mes completo

```
Usuario: "Valida que enero 2026 está bien clasificado"

Haiku:
1. SELECT SUM(importe) ... WHERE fecha LIKE '2026-01%' AND tipo='GASTO';
2. Verifica que Bizum y transferencias internas NO inflan los números
3. Compara ingresos vs gastos para coherencia
4. Reporta: "Enero 2026: €1,192 ingresos, €3,116 gastos, balance razonable"
```

---

## 🔟 Checklist Antes de Declarar Tarea Completa

- [ ] Cambios hechos en archivos de reglas (NO en BD directamente)
- [ ] `reclassify_all.py` ejecutado (todas las transacciones reprocesadas)
- [ ] Query de verificación ejecutada y número coincide
- [ ] Explicación clara de qué cambió y por qué
- [ ] Confirmación de que el cambio funciona para TODOS los casos (no solo uno)
- [ ] Sin regresiones (Bizum/Interna/Sin clasificar OK)

---

## 📞 Escalada a PLAN

Si durante una tarea Haiku encuentra:
- Nueva tabla necesaria
- Constraint a modificar
- Cambio fundamental de lógica
- 2+ intentos fallidos en el mismo error

**USAR FORMATO ESCALADO** (sección 3 de esta guía)

El usuario o PLAN resolverán el problema estructural, luego Haiku continúa.

---

**Esta guía es para Haiku, pero tú (Pablo) también debes conocerla para comunicar mejor.**

Imprime este documento o guárdalo en favoritos. Es tu manual de operaciones. 🚀
