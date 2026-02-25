# Resumen Ejecutivo: Mejorar Compras/Otros

**Para**: Opus 4.5 (revisión arquitectónica)  
**De**: Haiku (BUILD)  
**Decisión requerida**: Opción B vs Opción C para clasificación de merchants

---

## El Problema

1,697 transacciones en `GASTO/Compras/Otros` están sin categoría específica.
- Ejemplo: `"Apple pay: COMPRA EN CARTAGO PADEL, CON LA TARJETA : 5489... EL 2025-02-26"`
- **Debería ser**: `Deportes/Pádel`
- **Está como**: `Compras/Otros`

**Causa**: Las descripciones incluyen "ruido" (tarjeta, fecha) que impide el Exact Match. El merchant está ahí pero oculto.

---

## Dos Opciones Evaluadas

### Opción B — Extractor Regex (RECOMENDADO)

**Idea**: Extraer `"CARTAGO PADEL"` de la descripción con regex, luego buscar en reglas existentes.

**Implementación**: 
- 20 líneas de código en `merchants.py`
- ~30 keywords nuevas para merchants frecuentes
- ~1 hora de trabajo

**Resultados**:
- ~300-400 transacciones mejoradas
- Cero dependencias nuevas
- Cero latencia adicional
- Mantenimiento trivial

**Ventajas**:
- ✅ Simple, directo, auditable
- ✅ Funciona ya, sin hardware adicional
- ✅ Resiliente a cambios menores de formato
- ✅ Ya resolvemos 80% del problema

**Desventajas**:
- ❌ Si el banco cambia mucho el formato, hay que actualizar regex
- ❌ No es "inteligente" semánticamente (pero tampoco lo necesita)

---

### Opción C — Embeddings (FUTURO OPCIONAL)

**Idea**: Usar vectores semánticos (Ollama + nomic-embed-text) para clasificar merchants desconocidos.

**Implementación**:
- ~500 líneas de código
- Nueva capa en clasificador
- Generación de vectores de referencia
- Script de fallback offline

**Resultados**:
- Similar cobertura (~300-500 tx)
- Pero resuelve casos edge no identificables

**Ventajas**:
- ✅ Resiliente a cambios de formato
- ✅ No requiere mantenimiento manual de reglas
- ✅ Escalable a nuevos merchants automáticamente

**Desventajas**:
- ❌ Complejidad significativa (+500 líneas)
- ❌ Depende de RTX 3080 activa (no siempre disponible)
- ❌ Debugging opaco (¿por qué clasificó como X?)
- ❌ Umbral de confianza requiere calibración
- ❌ Overhead de latencia (50-100ms por tx)
- ❌ La ganancia marginal es pequeña vs Opción B

---

## Recomendación: Fase 1 + Fase 2

### **Fase 1 (AHORA)**: Opción B — Implementar regex extractor
- Sencillo, rápido, bajo riesgo
- Resuelve el 80% del problema
- Da valor inmediato

### **Fase 2 (FUTURO)**: Opción C — Embeddings como Capa 6 experimental
- **Solo si** después de Fase 1 hay transacciones que regex no resuelve
- **Precondición**: Mostrar logging de qué reglas fallan en Fase 1
- **Propósito**: Capas 1-5 + Embeddings como fallback

---

## Contexto de Decisión

**Por qué Opción B ahora:**

1. **Principio YAGNI** (You Aren't Gonna Need It): No agreguemos complejidad hasta que la necesitemos

2. **Estado actual del proyecto**: 
   - 15,060 transacciones correctamente deduplicadas ✅
   - 100% clasificadas en Cat1 ✅
   - Solo falta granularidad en Cat2 (14.8% en "Otros")

3. **Frecuencia de cambios**: Recibes ~pocos CSVs por semana, no es volumen que justifique ML

4. **Deuda técnica**: Cada capa de ML añadida es deuda a pagar en debugging y mantenimiento

**Por qué no Opción C ahora:**

- Embeddings brillan cuando hay **ambigüedad semántica real** (ej: "REPSOL" = ¿luz o gasolina?)
- Aquí no hay ambigüedad: `"SUSHI WU"` es claramente restaurante, `"PADEL"` es deporte
- El problema es técnico (formato), no semántico
- Hardware (RTX 3080) no siempre disponible = complejidad operacional

---

## Después de Fase 1, evaluar Fase 2 si:

- [ ] Hay >500 transacciones que Fase 1 no resuelve
- [ ] El usuario reporta frustración recurrente con merchants nuevos
- [ ] El análisis de logs muestra un patrón de fallos predecible

Si ninguno se cumple → Fase 1 es suficiente.

---

## Plan de Implementación (BUILD)

Ver archivo: `PLAN_COMPRAS_OTROS.md`

**Timeline**: ~1 hora
**Riesgo**: Bajo (cambios aislados en merchants.py)
**Rollback**: Trivial (revertir cambios, reprocesar)

---

## Pregunta a Opus

¿Apruebas la Fase 1 (Opción B) ahora + dejar Fase 2 (Opción C) como "nice to have" futuro?
