# Métricas de Validación Cruzada - Clasificador de Transacciones

## Configuración del Test

- **Dataset total**: 15,641 transacciones
- **Entrenamiento**: 14,641 transacciones (primeras)
- **Test**: 1,000 transacciones (últimas, excluidas del Exact Match)
- **Fecha**: 2026-02-13

---

## 📊 RESULTADOS PRINCIPALES

### Métricas Generales (sobre 1,000 transacciones de test)

| Métrica | Resultado | Objetivo | Estado |
|---------|-----------|----------|--------|
| **Cat1 accuracy (clasificadas)** | **93.49%** | 95% | ~ Aceptable (92-95%) |
| **Cat1+Cat2 accuracy (clasificadas)** | **87.37%** | 85% | ✓ OBJETIVO ALCANZADO |
| **% clasificadas (no SIN_CLASIFICAR)** | **78.40%** | 90% | ✗ Por debajo (objetivo: 85-90%) |
| **Cat1 accuracy total** | **73.30%** | 85% | ✗ Por debajo (objetivo: 80-85%) |

### Cobertura por Capa

| Capa | Transacciones | % del Test | Descripción |
|------|--------------|------------|-------------|
| **Capa 1** (Exact Match) | 196 | 19.6% | Descripciones ya vistas en entrenamiento |
| **Capa 2** (Merchants) | 227 | 22.7% | Detectadas por keywords de merchants |
| **Capa 3** (Transfers) | 206 | 20.6% | Transferencias detectadas |
| **Capa 4** (Tokens) | 155 | 15.5% | Tokens heurísticos |
| **Capa 5** (SIN_CLASIFICAR) | 216 | 21.6% | No clasificadas |

---

## 🎯 RENDIMIENTO DE CAPAS 2-5 (sin Exact Match)

**Transacciones procesadas por Capas 2-5**: 804 (80.4% del test)

| Métrica | Resultado |
|---------|-----------|
| **Cat1 accuracy (Capas 2-5)** | **91.33%** (537 / 588) |
| **Cat1+Cat2 accuracy (Capas 2-5)** | **83.50%** (491 / 588) |
| **% clasificadas (Capas 2-5)** | **73.13%** (588 / 804) |

**Interpretación**: De las transacciones que NO están en Exact Match (804), el clasificador logra clasificar correctamente el 91.33% de Cat1 y el 83.50% de Cat1+Cat2. Sin embargo, el 26.87% (216 transacciones) quedan como SIN_CLASIFICAR.

---

## ❌ ERRORES MÁS COMUNES

### Top 10 Errores en Cat1

| Veces | Error |
|-------|-------|
| 73x | Restauración → SIN_CLASIFICAR |
| 31x | Alimentación → SIN_CLASIFICAR |
| 30x | Compras → SIN_CLASIFICAR |
| 24x | Transporte → SIN_CLASIFICAR |
| 13x | Devoluciones → Comisiones |
| 10x | Ocio y Cultura → SIN_CLASIFICAR |
| 10x | Suscripciones → Divisas |
| 9x | Suscripciones → SIN_CLASIFICAR |
| 8x | Salud y Belleza → SIN_CLASIFICAR |
| 7x | Cashback → SIN_CLASIFICAR |

### Top 10 Errores en Cat1|Cat2

| Veces | Error |
|-------|-------|
| 27x | Restauración\|Otros → SIN_CLASIFICAR\| |
| 15x | Transporte\|Combustible → SIN_CLASIFICAR\| |
| 14x | Restauración\|CAFETERIA PROA → Restauración\|Cafeterías |
| 13x | Devoluciones\| → Comisiones\| |
| 12x | Restauración\|Bares → SIN_CLASIFICAR\| |
| 8x | Alimentación\|Frutería → SIN_CLASIFICAR\| |
| 7x | Alimentación\|Panadería → SIN_CLASIFICAR\| |
| 7x | Cashback\| → SIN_CLASIFICAR\| |
| 7x | Compras\|Regularización → Compras\|Amazon |
| 7x | Intereses\| → SIN_CLASIFICAR\| |

---

## 🔍 ANÁLISIS DE TRANSACCIONES SIN_CLASIFICAR (216 total)

### Distribución por Categoría Real

| Categoría Real | Transacciones SIN_CLASIFICAR |
|----------------|------------------------------|
| Restauración | 73 (33.8%) |
| Alimentación | 31 (14.4%) |
| Compras | 30 (13.9%) |
| Transporte | 24 (11.1%) |
| Ocio y Cultura | 10 (4.6%) |
| Suscripciones | 9 (4.2%) |
| Salud y Belleza | 8 (3.7%) |
| Cashback | 7 (3.2%) |
| Intereses | 7 (3.2%) |
| Ropa y Calzado | 6 (2.8%) |
| Otros | 11 (5.1%) |

---

## 🐛 PROBLEMAS IDENTIFICADOS

### 1. Trade Republic - Merchants Específicos No Detectados

**Problema**: La mayoría de transacciones SIN_CLASIFICAR son de Trade Republic con nombres de merchants específicos que no están en las reglas.

**Ejemplos**:
- `CARREF CARTAGENA II` → debería detectar "CARREF" como Carrefour
- `JIJONENCA CARTAGENA` → debería detectar "JIJONENCA" (heladería conocida)
- `LA COLEGIALA` → panadería específica
- `PLENOIL`, `ROYMAGA PETROLEOS` → gasolineras
- `CHAMFER`, `AVALON` → restaurantes específicos de Cartagena

### 2. Keywords Importantes No Detectadas

**Trade Republic - Palabras clave en inglés**:
- `SAVEBACK` / `Cash reward` → debería clasificar como Cashback
- `INTEREST PAYMENT` / `Interest payment` → debería clasificar como Intereses
- `ENTRADAS CINE` → debería clasificar como Ocio y Cultura|Cines

**Otros**:
- `TAXI` → debería clasificar como Transporte|Taxi
- `AUTOESCUELA` → debería clasificar como Transporte
- `HETZNER` → cloud hosting conocido (Suscripciones|Cloud/Backup)
- `ANTHROPIC`, `CLAUDE` → Suscripciones|Software/IA

### 3. Detección de Tokens Genéricos Insuficiente

Faltan tokens genéricos para:
- `CAFE` en medio de nombre (ej: "EL MOLI PAN Y CAFE")
- `PETROLEOS` → Transporte|Combustible
- `ENTRADAS` → Ocio y Cultura
- `REWARD` → Cashback
- `INTEREST` → Intereses

---

## 💡 RECOMENDACIONES DE MEJORA

### Alta Prioridad (mejora >10% cobertura)

1. **Ampliar reglas de Merchants (Capa 2)**:
   - Añadir variaciones: `CARREF` → Carrefour
   - Añadir merchants específicos de Trade Republic frecuentes
   - Añadir keywords de Trade Republic en inglés: `SAVEBACK`, `INTEREST PAYMENT`

2. **Mejorar Tokens (Capa 4)**:
   - Añadir: `SAVEBACK`, `REWARD` → Cashback
   - Añadir: `INTEREST` → Intereses
   - Añadir: `ENTRADAS` → necesita contexto (CINE, teatro, etc.)
   - Añadir: `TAXI` → Transporte|Taxi
   - Añadir: `PETROLEOS` → Transporte|Combustible

3. **Detección de Combustible**:
   - Ampliar keywords: `PLENOIL`, `BP`, `SHELL`, `PETROLEOS`, `ROYMAGA`

### Media Prioridad (mejora 5-10%)

4. **Mejorar extracción de Merchants**:
   - Trade Republic: el merchant name a veces tiene ciudad/código
   - Ejemplo: "CARREF CARTAGENA II" → extraer solo "CARREF"

5. **Añadir merchants específicos frecuentes**:
   - Restauración: JIJONENCA, CHAMFER, AVALON, EL MOLI
   - Alimentación: LA COLEGIALA, VENTA HNOS BLAYA
   - Suscripciones: HETZNER, ANTHROPIC, CLAUDE, COOKIDOO

### Baja Prioridad (mejora <5%)

6. **Detección de colisiones**:
   - "ZARA" → problema: se clasifica como Ropa vs CARREFOUR ZARAICHE
   - Necesita contexto o reglas específicas

---

## ✅ CONCLUSIONES

### Fortalezas

1. **Capa 1 (Exact Match)** funciona perfectamente (99.72% accuracy)
2. **Capas 2-5** tienen rendimiento sólido:
   - 91.33% Cat1 accuracy en transacciones nuevas
   - 83.50% Cat1+Cat2 accuracy
3. **Arquitectura de capas** es robusta y mantenible

### Áreas de Mejora

1. **Cobertura**: 21.6% de transacciones nuevas quedan SIN_CLASIFICAR
   - Principalmente por merchants específicos de Trade Republic
   - Se puede mejorar a ~10-15% con reglas adicionales

2. **Trade Republic**: Requiere atención especial
   - Formato diferente (inglés)
   - Merchants específicos locales (Cartagena)
   - Keywords en inglés (SAVEBACK, INTEREST PAYMENT)

### Siguiente Paso

**Implementar mejoras de Alta Prioridad** podría llevar la cobertura del 78.4% al ~85-88%, acercándose al objetivo del 90%.

---

## 📈 COMPARATIVA: Test Normal vs Validación Cruzada

| Métrica | Test Normal | Validación Cruzada | Diferencia |
|---------|-------------|-------------------|------------|
| Cat1 accuracy (clasificadas) | 99.72% | 93.49% | -6.23 pp |
| Cat1+Cat2 accuracy (clasificadas) | 97.31% | 87.37% | -9.94 pp |
| % clasificadas | 100.00% | 78.40% | -21.60 pp |
| Capa 1 (Exact Match) | 100.00% | 19.60% | -80.40 pp |

**Interpretación**: El test normal (con todas las transacciones en Exact Match) muestra el límite superior de rendimiento. La validación cruzada muestra el rendimiento real en transacciones nuevas, que depende de las Capas 2-5.
