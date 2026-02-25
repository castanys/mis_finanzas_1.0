# Reglas Implementadas - Febrero 2026

Este documento describe las reglas permanentes implementadas en el clasificador.

## ✅ Reglas Activas

### REGLA #1: B100 Transferencias Internas
**Ubicación**: `classifier/engine.py` (líneas 145-157)

**Descripción**: Cualquier transacción de B100 cuya descripción contenga las siguientes palabras clave se clasifica automáticamente como TRANSFERENCIA/Interna:
- `HEALTH`
- `SAVE`
- `TRASPASO`
- `AHORRO PARA HUCHA`
- `MOVE TO SAVE`

**Prioridad**: Capa 0 (antes de Exact Match)

**Justificación**: Estas son transferencias automáticas del sistema de ahorro de B100. Deben clasificarse SIEMPRE como internas, independientemente de lo que diga el CSV maestro.

**Transacciones afectadas**: 127 transacciones
- Antes: GASTO/Finanzas/Ahorro o INGRESO/Finanzas/Ahorro
- Ahora: TRANSFERENCIA/Interna/

**Ejemplo**:
```
TRASPASO DESDE CUENTA HEALTH 29/12/2025 14:51:31 → TRANSFERENCIA/Interna
OFF TO SAVE 25/12 → TRANSFERENCIA/Interna
Move to save día 25/12 → TRANSFERENCIA/Interna
```

---

### REGLA #2: Amazon Devoluciones
**Ubicación**: `classifier/engine.py` función `determine_tipo()` (líneas 40-47)

**Descripción**: Transacciones con **importe POSITIVO** que contienen estas palabras clave se clasifican como GASTO (devoluciones):
- `AMAZON`
- `AMZN`
- `DEVOLUCIÓN` / `DEVOLUCION`
- `REEMBOLSO`
- `REFUND`
- `RETURN`

**Comportamiento**:
- Importe positivo + keyword → `tipo=GASTO` (es una devolución)
- Cat1/Cat2 se mantienen según el merchant (ej: Compras/Amazon)

**Transacciones afectadas**: 10 transacciones Amazon
- Antes: INGRESO/Compras/Amazon
- Ahora: GASTO/Compras/Amazon (con importe positivo)

**Ejemplo**:
```
AMZN Mktp ES | +34.95 → GASTO/Compras/Amazon (devolución)
```

---

### REGLA #3: Devoluciones Generales
**Ubicación**: `classifier/engine.py` función `determine_tipo()` (líneas 49-57)

**Descripción**: Cuando una transacción tiene **importe POSITIVO** y su Cat1 pertenece a categorías típicas de gasto, se clasifica como GASTO (devolución).

**Categorías de gasto**:
- Compras, Alimentación, Restauración, Transporte, Vivienda
- Salud y Belleza, Ocio y Cultura, Ropa y Calzado, Educación
- Recibos, Finanzas, Suscripciones, Tecnología, Mascotas, Hogar, Deporte, Otros

**Comportamiento**:
- Si ya hay una regla para ese merchant como GASTO → mantener GASTO con importe positivo
- NO convertir a INGRESO

**Transacciones afectadas**: 220 transacciones
- Antes: INGRESO/[Cat1]/[Cat2]
- Ahora: GASTO/[Cat1]/[Cat2] (con importe positivo = devolución)

**Ejemplo**:
```
COMPRAS Y OPERACIONES CON TARJETA 4B | +40.00 → GASTO/Compras/Ajustes (devolución)
```

---

## 🔧 Mantenimiento

### Reprocesar todas las transacciones
Si modificas reglas del clasificador, ejecuta:
```bash
python3 reclassify_all.py
```

Este script:
1. Lee las 15,800 transacciones de la BBDD
2. Aplica las reglas actuales del clasificador
3. Actualiza la BBDD con nuevas clasificaciones
4. Reporta estadísticas de cambios

### Verificar que las reglas funcionan
```bash
sqlite3 finsense.db <<EOF
-- REGLA #1: B100
SELECT COUNT(*), tipo, cat1
FROM transacciones
WHERE banco='B100' AND (descripcion LIKE '%Health%' OR descripcion LIKE '%Save%')
GROUP BY tipo, cat1;

-- REGLA #2: Amazon refunds
SELECT COUNT(*), tipo
FROM transacciones
WHERE importe > 0 AND cat2='Amazon'
GROUP BY tipo;

-- REGLA #3: Devoluciones generales
SELECT COUNT(*)
FROM transacciones
WHERE importe > 0 AND tipo='GASTO'
  AND cat1 IN ('Compras','Alimentación','Restauración','Transporte','Vivienda',
               'Salud y Belleza','Ocio y Cultura','Ropa y Calzado');
EOF
```

Resultados esperados:
- REGLA #1: ~127 transacciones → TRANSFERENCIA/Interna
- REGLA #2: ~10 transacciones → GASTO
- REGLA #3: ~220 transacciones

---

## 📝 Historial

### 2026-02-14: Implementación inicial
- ✅ REGLA #1: B100 Health/Save → Interna
- ✅ REGLA #2: Amazon refunds → GASTO positivo
- ✅ REGLA #3: Devoluciones generales → GASTO positivo
- ✅ Reprocesadas 15,800 transacciones
- ✅ 2,549 transacciones actualizadas (16.13%)

---

## ⚠️ IMPORTANTE

**Lee `REGLAS_PROYECTO.md` antes de hacer cambios.**

Principio fundamental: **NUNCA parchear datos, SIEMPRE arreglar reglas.**

Las correcciones se hacen en:
- `classifier/engine.py` - Lógica principal y reglas prioritarias
- `classifier/transfers.py` - Detección de transferencias
- `classifier/tokens.py` - Reglas basadas en tokens
- `classifier/exact_match.py` - Construcción del diccionario
- `excepciones_clasificacion.json` - Excepciones específicas

**NUNCA** modificar:
- Transacciones individuales en `finsense.db`
- Archivos CSV de salida manualmente
- Scripts one-off para casos específicos
