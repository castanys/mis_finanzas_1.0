# Plan: Mejorar GASTO/Compras/Otros (1,697 transacciones)

**Fecha**: 2026-02-18  
**Estado**: Listo para implementación (Opción B recomendada)  
**Prioridad**: Alta (después de CHECK 2 y REPSOL)

---

## Problema

1,697 transacciones en `GASTO/Compras/Otros` no tienen categoría Cat2 específica.
- 1,460 tienen patrón claro: `"COMPRA EN [MERCHANT], CON LA TARJETA..."`
- 237 son otros formatos (regularizaciones, compras genéricas, etc.)

Ejemplos:
```
"Apple pay: COMPRA EN CARTAGO PADEL, CON LA TARJETA : 5489133068682036 EL 2025-02-26"
→ Debería ser: Compras/Deporte (no Compras/Otros)

"COMPRA EN PRIMARK ESPACIO MEDITE, CON LA TARJETA : 5489133068682010 EL 2024-06-08"
→ Debería ser: Compras/Ropa y Calzado (no Compras/Otros)
```

**Causa raíz**: Las descripciones incluyen ruido (tarjeta, fecha, banco) que impide que el Exact Match las capture como descripciones únicas. El merchant está ahí pero enterrado.

---

## Solución: Opción B — Extractor de Merchant + Lookup existente

### Arquitectura

```
Descripción raw:
"Apple pay: COMPRA EN CARTAGO PADEL, CON LA TARJETA : 5489133068682036 EL 2025-02-26"
                   ↓
Paso 1: Extractor regex (nueva lógica en classifier/merchants.py)
                   ↓
Merchant extraído: "CARTAGO PADEL"
                   ↓
Paso 2: Buscar en reglas existentes de MERCHANT_RULES
                   ↓
Resultado: ("Deportes", "Pádel") ✅
```

### Ventajas vs embeddings

| Aspecto | Opción B (Regex) | Opción C (Embeddings) |
|---------|------------------|----------------------|
| **Complejidad** | 20 líneas de código | 500+ líneas + dependencias |
| **Latencia** | <1ms por transacción | 50-100ms por transacción |
| **Dependencias** | regex (stdlib) | Ollama/modelos, librerías |
| **Mantenimiento** | Trivial | Actualizar vectores, debuggear ML |
| **Tolerancia cambios formato** | Media | Alta (pero falsa sensación) |
| **Cobertura inmediata** | ~300-500 tx | ~300-500 tx (similar) |
| **Hardware requerido** | Ninguno | RTX 3080 activa |

**Conclusión**: Opción B da 80% del beneficio con 10% del esfuerzo.

---

## Implementación: Opción B

### Paso 1: Crear función extractora en `classifier/merchants.py`

Añadir al final del archivo:

```python
import re

def extract_merchant_from_compra_en(descripcion: str) -> Optional[str]:
    """
    Extrae el merchant de descripciones tipo "COMPRA EN X, CON LA TARJETA..."
    
    Ejemplos:
        "COMPRA EN CARTAGO PADEL, CON LA TARJETA : 5489..." → "CARTAGO PADEL"
        "Apple pay: COMPRA EN SUSHI WU, CON LA TARJETA..." → "SUSHI WU"
        "REGULARIZACION COMPRA EN CEDIPSA, CON LA TARJETA..." → "CEDIPSA"
    
    Args:
        descripcion: Texto completo de la transacción
    
    Returns:
        Nombre del merchant limpio, o None si no coincide patrón
    """
    # Patrón: encuentra "COMPRA EN X" donde X termina en coma o fin de palabra
    match = re.search(r'COMPRA EN\s+(.+?)(?:,\s*CON LA TARJETA|$)', descripcion)
    
    if match:
        merchant_raw = match.group(1).strip()
        # Limpiar espacios múltiples
        merchant_clean = re.sub(r'\s+', ' ', merchant_raw)
        return merchant_clean
    
    return None
```

### Paso 2: Modificar `lookup_merchant()` para usar el extractor

En `lookup_merchant()` (línea 393), **antes** de buscar en `MERCHANT_RULES`:

```python
def lookup_merchant(descripcion, merchant_name=None):
    """
    Busca keywords en la descripción y en el merchant extraído.
    PRIMERO intenta extraer merchant de "COMPRA EN X" pattern.
    Luego busca en Google Places merchants, luego en las reglas manuales.
    
    Returns:
        Tupla (Cat1, Cat2) si hay match, None si no
    """
    desc_upper = descripcion.upper()
    
    # NUEVO: Intentar extraer merchant de "COMPRA EN"
    merchant_extraido = extract_merchant_from_compra_en(desc_upper)
    
    # 1. PRIORIDAD: Buscar merchant extraído en Google Places
    if merchant_extraido and merchant_extraido in GOOGLE_PLACES_MERCHANTS:
        merchant_data = GOOGLE_PLACES_MERCHANTS[merchant_extraido]
        return (merchant_data['cat1'], merchant_data['cat2'])
    
    # 2. Buscar en descripción completa Y en merchant extraído
    search_texts = [desc_upper]
    if merchant_name:
        search_texts.append(merchant_name.upper())
    if merchant_extraido:  # NUEVO
        search_texts.append(merchant_extraido)
    
    # ... resto del código sin cambios
```

### Paso 3: Agregar keywords nuevas en MERCHANT_RULES

Agregar estas reglas después de la sección de COMPRAS existente (alrededor de línea 70):

```python
    # ===== COMPRAS (adicionales - merchants frecuentes extraídos de COMPRA EN) =====
    ("CEDIPSA", "Compras", "Construcción"),
    ("E S SAN JAVIER", "Alimentación", "Supermercado"),  # Es una tienda
    ("PRIMARK", "Compras", "Ropa y Calzado"),
    ("PULL AND BEAR", "Compras", "Ropa y Calzado"),
    ("H&M", "Compras", "Ropa y Calzado"),
    ("MANGO", "Compras", "Ropa y Calzado"),
    ("JYSK", "Compras", "Muebles"),
    ("MAISONS DU MONDE", "Compras", "Muebles"),
    ("IKEA", "Compras", "Muebles"),
    ("TREKKINN", "Compras", "Deporte"),
    ("FORUM SPORT", "Compras", "Deporte"),
    ("PADEL CENTER", "Deportes", "Pádel"),
    ("PADEL", "Deportes", "Pádel"),
    ("BOWLING", "Ocio y Cultura", "Entretenimiento"),
    ("RUGBY", "Deportes", "Rugby"),
    ("SUSHI", "Restauración", "Sushi/Japonés"),
    ("PIZZA", "Restauración", "Pizza"),
    ("TAPAS", "Restauración", "Tapería"),
    ("BARBERIA", "Salud y Belleza", "Peluquería"),
    ("PELUQUERIA", "Salud y Belleza", "Peluquería"),
    ("PCCOMPONENTES", "Compras", "Tecnología"),
    ("PC BOX", "Compras", "Tecnología"),
    ("STEAM", "Compras", "Videojuegos"),
    ("AENA PARK", "Transporte", "Parking"),
    ("VINOSELECCION", "Compras", "Alimentación Especializada"),  # Vino
    ("ALDEASA", "Compras", "Duty Free"),
    ("RAKUTEN", "Compras", "Online"),
    ("CLICKAIR", "Viajes", "Vuelos"),
    ("NATIONAL EXPRESS", "Viajes", "Transporte"),
```

### Paso 4: Reprocesar

```bash
python3 reclassify_all.py
```

**Impacto estimado**:
- ~300-400 transacciones de `Compras/Otros` mejoradas
- Nuevas categorías: `Deportes/Pádel`, `Restauración/Sushi`, `Compras/Ropa y Calzado`, etc.
- ~1,300 transacciones seguirán en `Compras/Otros` (merchants genéricos sin patrón claro)

---

## Validación

Después de reprocesar, ejecutar:

```bash
# Ver cuántas mejoramos
sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat1='Compras' AND cat2='Otros';"
# Esperado: ~1,300 (antes: 1,697)

# Ver nuevas categorías creadas
sqlite3 finsense.db "SELECT cat1, cat2, COUNT(*) FROM transacciones WHERE cat2 IS NOT NULL AND cat2 != 'Otros' GROUP BY cat1, cat2 HAVING COUNT(*) < 50 ORDER BY COUNT(*);"
```

---

## Alternativa: Opción C (Embeddings) — Para revisión de Opus

Si después de esta sesión el usuario decide que quiere embeddings como Capa 6 experimental:

1. **Crear `classifier/embedding_layer.py`**: Lógica de embeddings con fallback offline
2. **Generar vectores de categorías**: Una sola vez desde `taxonomia.py` + histórico
3. **Script `reclassify_pending.py`**: Para reprocesar `SIN_CLASIFICAR` cuando Ollama esté activo
4. **Logging auditable**: Qué clasifica como embedding y con qué confianza

**Precondición**: Opción B ya implementada y estable. Embeddings es para casos edge que regex no resuelva.

---

## Riesgos y mitigaciones

| Riesgo | Mitigation |
|--------|-----------|
| Regex demasiado genérico | Validar con queries antes de hacer reclassify_all |
| Nuevas Cat2 no en taxonomía | Verificar que todas las Cat2 nuevas existan en taxonomia.py |
| Merchants mal clasificados | Logging de debug para verificar qué se clasificó como qué |
| Falsos positivos (PADEL captura PADDINGTON) | Tests antes del deploy |

---

## Timeline

- **Paso 1-2**: 30 min (modificar merchants.py y lookup_merchant)
- **Paso 3**: 20 min (agregar keywords nuevas)
- **Paso 4**: 5 min (reprocesar)
- **Paso 5**: 10 min (validación y logging)

**Total**: ~1 hora de trabajo BUILD

---

## Criterio de éxito

✅ **Completado cuando:**
1. `Compras/Otros` pasa de 1,697 a ~1,300 tx
2. Nuevas Cat2 (Deporte, Sushi, Ropa, etc.) aparecen en BD
3. Todas las nuevas combinaciones están en taxonomía.py whitelist
4. 0 combinaciones inválidas en BD
5. Maestro v6 regenerado desde BD

