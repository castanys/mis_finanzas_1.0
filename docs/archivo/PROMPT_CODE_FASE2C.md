# FASE 2C: Cerrar los 4 problemas pendientes de Fase 2B

## Contexto

La Fase 2B validó el sistema contra el CSV maestro con buenos resultados (99.8% Cat1 accuracy), pero dejó 4 problemas abiertos que hay que cerrar ANTES de pasar a Fase 3.

**Regla de oro: NO rompas lo que ya funciona.** Cada fix debe ser quirúrgico y verificable.

---

## PROBLEMA 1: 1,150 transacciones no matched (7.4%) — CRÍTICO

El reporte dice "B100 nuevas + encoding" pero eso es insuficiente. Necesito diagnóstico exacto.

**Lo que debes hacer:**

```python
# 1. Genera la lista COMPLETA de las 1,150 no-matched
# Para cada una, muestra: Fecha, Importe, Descripción, Banco, Cuenta, origen (maestro vs output)

# 2. Clasifícalas por causa raíz:
#    a) ¿Están en el maestro pero no en output? → Parser no las leyó
#    b) ¿Están en output pero no en el maestro? → Parser generó registros fantasma
#    c) ¿Están en ambos pero no matchean? → Diferencia en fecha/importe/descripción
#       Para estas, muestra la versión maestro vs output lado a lado

# 3. Para el caso (c), identifica el patrón:
#    - ¿Encoding? (caracteres especiales rotos: ó vs Ã³, ñ vs Ã±, etc.)
#    - ¿Formato numérico? (el maestro tiene "15,000.00" y output tiene "15000.0")
#    - ¿Fecha? (DD/MM/YYYY vs YYYY-MM-DD mal convertido)
#    - ¿Descripción truncada o con espacios extra?

# 4. ARREGLA la causa raíz en el parser correspondiente
# 5. Re-ejecuta la validación y confirma que el número baja a <1%
```

**Criterio de cierre:** <100 no-matched (idealmente <50). Las que queden deben tener explicación individual documentada.

---

## PROBLEMA 2: 1 Bizum clasificado como Interna — BUG

Un Bizum fue clasificado como Cat1=Interna cuando debería ser Cat1=Bizum.

**Lo que debes hacer:**

```python
# 1. Identifica cuál es el Bizum mal clasificado (muestra la transacción completa)

# 2. La regla es simple y absoluta:
#    Si la descripción contiene "BIZUM" → Cat1=Bizum, SIEMPRE
#    Los Bizum NUNCA son transferencias internas (son pagos a terceros)
#    
#    Prioridad: la regla BIZUM debe evaluarse ANTES que las reglas de transferencia interna
#    Es decir: primero detectar Bizum, luego detectar internas

# 3. Fix: ajusta el orden de prioridad en el clasificador/pipeline
#    para que BIZUM se detecte antes que "FERNANDEZ CASTANYS" u otros patrones de interna

# 4. Verifica que TODOS los Bizums del maestro (hay ~100+) siguen clasificados como Bizum
#    y que el fix no rompe nada más
```

**Criterio de cierre:** 0 Bizums clasificados como Interna. 0 regresiones en otras categorías.

---

## PROBLEMA 3: 729 transacciones INVERSION no implementada — GORDO

Casi 5% del total. Esto incluye aportaciones a fondos, compra/venta de ETFs, dividendos, intereses de inversión, etc.

**Lo que debes hacer:**

```python
# 1. Del CSV maestro, extrae TODAS las transacciones con Cat1=Inversión (o variantes)
#    Lista los patrones de descripción únicos, agrupados por Cat2

# 2. Estos son los Cat2 conocidos dentro de Inversión (del maestro):
#    - Aportación (aportes a fondos/carteras MyInvestor)
#    - Broker (comisiones Trade Republic)
#    - Dividendos
#    - Divisas (conversiones Revolut)
#    - Cripto (si hay)
#    - ETFs / Fondos
#    Verifica contra el maestro cuáles existen realmente

# 3. Patrones conocidos por banco:
#
#    MYINVESTOR:
#      "Aportacion a mi cartera" → Inversión|Aportación
#      "Movimiento MyInvestor salida" con importe 0 → puede ser rebalanceo
#      "EFECTIVO-EUR @ 0" → Inversión|Comisiones (o similar)
#
#    TRADE REPUBLIC:
#      "Interest Payment" → Inversión|Intereses (o Ingreso|Intereses)
#      "Saveback" → Inversión|Cashback
#      "Cash Reward" → Inversión|Cashback  
#      "Round up" → Inversión|Redondeo
#      "Transacción <MERCHANT> con tarjeta" → GASTO, no inversión
#      Compra/venta de acciones/ETFs → Inversión|ETFs
#
#    REVOLUT:
#      "Conversión a CHF/USD/GBP" → Inversión|Divisas
#
# 4. Implementa las reglas de clasificación para INVERSION
#    CUIDADO: no confundir "Interest Payment" de Trade Republic (inversión)
#    con "INTERESES A SU FAVOR" de Openbank (ingreso bancario normal)

# 5. Re-ejecuta clasificación y verifica que las 729 ahora matchean con el maestro
```

**Criterio de cierre:** >95% de las 729 inversiones correctamente clasificadas. Las restantes documentadas.

---

## PROBLEMA 4: 316 Cat2 como "Otros" — COBERTURA

316 transacciones tienen Cat1 correcto pero Cat2="Otros" cuando el maestro tiene un Cat2 específico.

**Lo que debes hacer:**

```python
# 1. Lista las 316 transacciones con Cat2="Otros" en output
#    pero Cat2 != "Otros" en el maestro
#    Agrupa por Cat1 y Cat2_maestro para ver los patrones

# 2. Para cada grupo, identifica qué keyword/patrón en la descripción
#    debería triggear el Cat2 correcto

# 3. Ejemplo esperado del análisis:
#    Cat1=Restauración, Cat2_output="Otros", Cat2_maestro="Cafeterías" (23 casos)
#    → Descripciones contienen: "CAFETERIA", "CAFE", "COFFEE"
#    → Añadir regla: si desc contiene CAFETERIA/CAFE/COFFEE → Cat2=Cafeterías
#
#    Cat1=Transporte, Cat2_output="Otros", Cat2_maestro="Combustible" (15 casos)
#    → Descripciones contienen: "REPSOL", "CEPSA", "E.S.", "GASOLINERA"
#    → Añadir reglas para esos merchants

# 4. Implementa las reglas de Cat2 más frecuentes (las que cubran >5 transacciones)
#    Las que sean únicas (<3 casos) pueden quedar como "Otros"

# 5. Re-ejecuta y verifica
```

**Criterio de cierre:** <100 transacciones con Cat2="Otros" cuando el maestro tiene valor específico.

---

## Orden de ejecución

1. **Problema 1** primero — si hay registros fantasma o perdidos, todo lo demás se invalida
2. **Problema 3** segundo — las 729 INVERSION son el gap más grande
3. **Problema 2** tercero — fix rápido del Bizum
4. **Problema 4** último — refinamiento de Cat2

## Validación final

Después de los 4 fixes, ejecuta la validación cruzada completa de nuevo:

```
=== VALIDACIÓN FINAL FASE 2C ===
Registros matched:      XX,XXX / 15,640 (objetivo: >99%)
Cat1 accuracy:          XX.X% (objetivo: >99.5%)
Cat2 accuracy:          XX.X% (objetivo: >98%)
Tipo accuracy:          XX.X% (objetivo: >98%)
Sin clasificar:         XX (objetivo: <20)
Internas correctas:     XX.X% (objetivo: 100%)
Bizums correctos:       XX/XX (objetivo: 100%)
INVERSION correctas:    XXX/729 (objetivo: >95%)
Cat2 "Otros" restantes: XX (objetivo: <100)
```

**La Fase 2 NO se cierra hasta que estos números estén en objetivo.**
