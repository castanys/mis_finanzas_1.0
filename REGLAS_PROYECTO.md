# REGLAS_PROYECTO.md — mis_finanzas_1.0

---

## Regla #1: Nunca parchear, siempre arreglar

❌ PROHIBIDO:
- Editar datos individuales en BD/CSV/JSON directamente
- Scripts "one-off" para parchear casos
- Modificar archivos de salida manualmente

✅ CORRECTO:
- Modificar lógica/reglas/configuración
- Reprocesar desde cero
- Verificar con test/query

### Flujo correcto
1. Identificar qué está mal
2. Analizar por qué
3. Arreglar regla/config/lógica en `classifier/`
4. Ejecutar `python3 reclassify_all.py`
5. Validar resultado con query SQL
6. Actualizar SESIONES.md

---

## Regla #2: Nunca inventar datos

- TODO dato debe tener fuente verificable
- Si necesitas crear excepciones → confirmar con usuario PRIMERO
- Si no estás seguro → preguntar, no asumir

**Protocolo de validación**:
1. Verificar existencia: `SELECT * FROM transacciones WHERE descripcion='...'`
2. Confirmar con usuario: "¿Quieres que modifique esto? Aquí está el registro real"
3. Ejecutar cambio: Solo después de aprobación explícita
4. Documentar: Incluir query SQL que demuestre la fuente

---

## Regla #3: Taxonomía cerrada

**NO crear Cat1 nuevas sin aprobación explícita del usuario.**

Cat2 puede añadirse si:
- La combinación Cat1|Cat2 es válida según `classifier/valid_combos.py`
- Existe evidencia en la BD de al menos 2 transacciones que la necesiten
- Se agrega a `valid_combos.py` antes de usar

Las 21 Cat1 existentes están en `AGENTS.md` (sección Taxonomía de Referencia).

---

## Regla #4: Verificación obligatoria

**Nunca marcar tarea completada sin verificar con query SQL real.**

Ejemplo correcto:
1. Modificar REGLA #35 en `classifier/engine.py`
2. Ejecutar: `python3 reclassify_all.py`
3. Verificar: `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE descripcion='COMPRAS Y OPERACIONES CON TARJETA 4B' AND importe > 0 AND cat2='Devoluciones';"`
4. Confirmar: número real (6) == número esperado (6)
5. Actualizar SESIONES.md con número REAL verificado, no asumido

---

## Regla #5: Prohibición UPDATE directo de cat1/cat2

❌ PROHIBIDO:
```sql
UPDATE transacciones SET cat1='X', cat2='Y' WHERE ...
```

✅ CORRECTO:
1. Crear/modificar regla en `classifier/merchants.py`, `classifier/engine.py`, o `classifier/tokens.py`
2. Ejecutar `python3 reclassify_all.py`
3. Verificar resultado con query SQL
4. Documentar en SESIONES.md

La BD debe reflejar SIEMPRE el estado que definen las reglas de código, nunca al revés.

---

## Criterio de Éxito

Antes de dar una tarea por completada:
1. ¿Resultado coincide con objetivo del usuario?
2. ¿Query SQL confirma el cambio?
3. ¿SESIONES.md actualizado con métricas verificadas?

Si alguna es NO → no está terminado.
