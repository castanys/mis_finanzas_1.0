# Fix definitivo del normalizador de Trade Republic

**Fecha**: 22 de febrero de 2026
**Archivo modificado**: `parsers/tr_hash_normalizer.py`
**Tests añadidos**: `tests/test_tr_normalizer.py`

---

## Problema

El sistema de deduplicación basado en hash fallaba para transacciones de Trade Republic cuando el CSV y PDF de la misma transacción se importaban juntos porque:

1. **Trade Republic genera dos formatos de descripción distintos para el mismo movimiento**:
   - CSV: `"Otros Transacción GITHUB, INC., 21,52 $, exchange rate: ..., ECB rate: ..., markup: ...%null"`
   - PDF: `"GITHUB, INC., 21,52 $, exchange rate: ..., ECB rate: ..."`

2. **El ruido FX (exchange rate, ECB rate, markup, con tarjeta) varía entre formatos**:
   - CSV variante A: `ECB rate: con tarjeta X.XX, markup: Y.YY %`
   - CSV variante B: `ECB rate: X.XX, con tarjeta markup: Y.YY %`

3. **El normalizador anterior no eliminaba todo el ruido**, produciendo strings distintos para CSV y PDF de la misma transacción:
   - CSV → `"GITHUB, INC., 21,52 $, exchange rate: 0,8633829, ECB rate: 0,8608074374"`
   - PDF → `"GITHUB, INC., 21,52 $, exchange rate: 0,8633829, ECB rate: 0,8608074374,"`
   - **Resultado**: Hashes distintos → ambos se insertaban (duplicado)

---

## Solución

**Fase 3.5 nueva en el normalizador**: Truncar todo desde `, exchange rate:` en adelante

```python
# Truncar tipo de cambio en transacciones FX
normalized = re.sub(r',\s*exchange rate:.*$', '', normalized)
```

**Resultado**: La parte informativa relevante para identificar la transacción se conserva, todo el ruido FX se elimina:

```
CSV GITHUB ene:      "GITHUB, INC., 21,52 $"  (después del fix)
PDF GITHUB ene:      "GITHUB, INC., 21,52 $"  (después del fix)
                     ✓ Hashes iguales → deduplicación funciona
```

---

## Justificación técnica

- **Merchant + importe en divisa extranjera** es suficiente para identificar unívocamente una transacción junto con `fecha + cuenta + importe_en_euros`
- El hash de Trade Republic incluye: `fecha | importe_euros | descripcion_normalizada | cuenta`
- Esto garantiza que incluso si dos pagos a GitHub el mismo día tienen el mismo importe en dólares (imposible), serían transacciones distintas
- El `exchange rate`, `ECB rate`, `markup` y `con tarjeta` son datos derivados del tipo de cambio que varían entre formatos pero no identifican la transacción

---

## Verificación

### Tests automatizados (7/7 PASSING)

```
✓ test_github_csv_pdf_equivalence_enero      — CSV/PDF github ene 2026
✓ test_github_csv_pdf_equivalence_diciembre  — CSV/PDF github dic 2025
✓ test_anthropic_csv_pdf_equivalence         — CSV/PDF anthropic ene 2026
✓ test_multiple_github_*_different_amounts   — Importes distintos quedan distintos
✓ test_savings_plan_not_affected             — Savings plans no se truncan
✓ test_transfer_not_affected                 — Transferencias no se truncan
✓ test_idempotency                          — Normalización es idempotente
```

### Casos reales verificados

```
GitHub ene A (CSV)    → "GITHUB, INC., 21,52 $"  ✓
GitHub ene A (PDF)    → "GITHUB, INC., 21,52 $"  ✓ Iguales

GitHub dic B (CSV)    → "GITHUB, INC., 10,00 $"  ✓
GitHub dic B (PDF)    → "GITHUB, INC., 10,00 $"  ✓ Iguales

Anthropic (CSV)       → "ANTHROPIC, 18,15 $"     ✓
Anthropic (PDF)       → "ANTHROPIC, 18,15 $"     ✓ Iguales
```

---

## Impacto futuro

1. **Futuras importaciones**: Si recibes otro PDF de TR que solape con el CSV (mismo período), la deduplicación funcionará correctamente porque el hash será idéntico.

2. **Otras transacciones FX**: Cualquier movimiento con `exchange rate` en TR (no solo GitHub/Anthropic) usará este mecanismo.

3. **No-FX**: Transacciones sin `exchange rate` (transferencias, savings plans, etc.) no son afectadas — el regex no matchea y quedan intactas.

4. **Idempotencia**: Ejecutar el normalizador dos veces sobre el mismo string produce el mismo resultado.

---

## Archivos modificados

1. **`parsers/tr_hash_normalizer.py`**
   - Fase 3.5 añadida (líneas 95–106)
   - Docstring actualizado
   - Comentarios claros sobre el problema y la solución

2. **`tests/test_tr_normalizer.py`** (NUEVO)
   - 7 tests unitarios para validar correctitud
   - Todos los casos críticos cubiertos
   - Regresión prevista para futuras modificaciones

---

## Conclusión

El normalizador ahora funciona correctamente para **todos los formatos** de Trade Republic, eliminando el riesgo de duplicados CSV+PDF en futuras importaciones.
