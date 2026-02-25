# FASE 3: Cazador de Transferencias Internas (Matching de Pares)

## Contexto

La Fase 2 está cerrada: 15,640 transacciones, 100% clasificadas, 99.4% Cat1 accuracy. Ahora necesitas el módulo que EMPAREJA transferencias internas entre cuentas.

**¿Por qué importa?** Pablo tiene 7 bancos y 15 cuentas. Cuando mueve €1,000 de Openbank a B100, aparecen DOS transacciones:
- Openbank: -€1,000 "TRANSFERENCIA A FAVOR DE..."
- B100: +€1,000 "FERNANDEZ CASTANYS..."

Si sumas todo sin emparejar, estás contando €2,000 de movimiento cuando en realidad son €0 netos. Para responder "¿cuánto gasté este mes?" necesitas anular estos pares.

## Reglas del Matching

Una transferencia interna es un PAR de transacciones que cumple **TODAS** estas condiciones:

1. **Mismo importe absoluto, signos opuestos**: una es +X y otra es -X (exactamente)
2. **Cuentas DISTINTAS**: la salida es de una cuenta y la entrada de otra
3. **Ventana temporal**: máximo ±3 días de diferencia entre fechas
4. **Al menos una marcada como Cat1=Interna**: el clasificador ya las marcó

### Condiciones EXCLUYENTES (NO son pares internos):
- Dos transacciones en la MISMA cuenta → no es transferencia entre cuentas
- Ninguna de las dos tiene Cat1=Interna → probablemente no es interna
- Cat1=Bizum → NUNCA es interna (son pagos a terceros)
- Cat1=Externa → no es interna por definición

## Algoritmo propuesto

```python
def find_internal_transfer_pairs(transactions):
    """
    Encuentra pares de transferencias internas.
    
    Returns:
        List of tuples: [(tx_salida, tx_entrada, confidence), ...]
        confidence: 'high', 'medium', 'low'
    """
    # 1. Filtrar candidatas: solo Cat1=Interna
    candidates = [tx for tx in transactions if tx['cat1'] == 'Interna']
    
    # 2. Separar en salidas (importe < 0) y entradas (importe > 0)
    salidas = [tx for tx in candidates if tx['importe'] < 0]
    entradas = [tx for tx in candidates if tx['importe'] > 0]
    
    # 3. Para cada salida, buscar su entrada correspondiente
    pairs = []
    used_entries = set()
    
    for sal in salidas:
        best_match = None
        best_score = 0
        
        for i, ent in enumerate(entradas):
            if i in used_entries:
                continue
            
            # Condición 1: mismo importe absoluto
            if abs(sal['importe'] + ent['importe']) > 0.01:  # tolerancia de 1 céntimo
                continue
            
            # Condición 2: cuentas distintas
            if sal['cuenta'] == ent['cuenta']:
                continue
            
            # Condición 3: ventana temporal ±3 días
            dias_diff = abs((parse_date(ent['fecha']) - parse_date(sal['fecha'])).days)
            if dias_diff > 3:
                continue
            
            # Scoring de confianza
            score = 0
            if dias_diff == 0: score += 3      # mismo día = alta confianza
            elif dias_diff == 1: score += 2    # día siguiente = buena
            elif dias_diff <= 3: score += 1    # 2-3 días = aceptable
            
            # Bonus: misma familia de banco (ej: Openbank→Openbank entre cuentas)
            if sal['banco'] == ent['banco']:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = (i, ent, dias_diff)
        
        if best_match:
            idx, ent, dias = best_match
            used_entries.add(idx)
            
            confidence = 'high' if dias <= 1 else 'medium' if dias <= 2 else 'low'
            pairs.append({
                'salida': sal,
                'entrada': ent,
                'importe': abs(sal['importe']),
                'dias_diferencia': dias,
                'confidence': confidence,
            })
    
    return pairs
```

## Casos especiales a manejar

### 1. Transferencias en cadena
Pablo a veces mueve dinero: Openbank → MyInvestor → Trade Republic
Esto genera 4 transacciones (2 pares), no 1 par de 2.

### 2. Importes duplicados en la misma ventana
Si Pablo hace dos transferencias de €200 en el mismo día a cuentas distintas, hay que emparejar correctamente (no cruzar los pares). El algoritmo greedy anterior podría fallar aquí. Solución: priorizar por cercanía temporal y luego por mismo banco.

### 3. Movimientos dentro del mismo banco
- Openbank cuenta 3660 → Openbank cuenta Fede 3470: ambas son Openbank pero cuentas distintas → SÍ es par interno
- B100 cuenta → B100 hucha: es movimiento dentro de B100 → SÍ es par interno (AHORRO PARA HUCHA / TRASPASO DESDE HUCHA)

### 4. Transferencias con importe 0
MyInvestor tiene movimientos de €0 ("Movimiento MyInvestor salida/entrada"). Estos son rebalanceos, NO transferencias internas. Excluirlos.

### 5. Las "casi-match" por comisiones
A veces Pablo envía €1,000 pero llegan €999.50 por comisión. Para la v1, NO matchear estos (exigir importe exacto). En v2 se puede añadir tolerancia configurable.

## Output esperado

### Archivo: output/transferencias_internas_pairs.csv
```
id_salida;id_entrada;importe;fecha_salida;fecha_entrada;cuenta_salida;cuenta_entrada;banco_salida;banco_entrada;dias_diferencia;confidence
```

### Reporte en consola:
```
=== CAZADOR DE TRANSFERENCIAS INTERNAS ===

Total transacciones Cat1=Interna: 2,534
Pares encontrados:               X,XXX
Transacciones emparejadas:       X,XXX (X.X%)
Internas sin pareja:             XXX

Por confianza:
  High (0-1 días):   XXX pares
  Medium (2 días):   XXX pares
  Low (3 días):      XXX pares

Por ruta más frecuente:
  Openbank 3660 → MyInvestor 6253:     XX pares (€XX,XXX total)
  Openbank 3660 → Mediolanum 4831:     XX pares (€XX,XXX total)
  Openbank 3660 → Trade Republic 4411: XX pares (€XX,XXX total)
  ...

Internas sin pareja (top 10):
  [fecha] [banco] [cuenta] [importe] [descripción]
  ...

Impacto financiero:
  Volumen total de transferencias internas: €XXX,XXX
  Sin pares = posibles transferencias externas mal clasificadas: €XX,XXX
```

## Validación

Las internas sin pareja son interesantes:
- Si son muchas → puede que haya contrapartidas en bancos que no tenemos (ej: Nexo)
- Si son pocas → el matching funciona bien
- Las de B100 (hucha) pueden ser pares consigo mismas (misma cuenta, mismo banco) — considerar como caso especial

## Integración

Crea un módulo independiente:
```
src/
  internal_transfer_hunter.py   # El cazador
```

Que se ejecute DESPUÉS del pipeline de clasificación:
```bash
python3 process_transactions.py          # Fase 2: parsea y clasifica
python3 internal_transfer_hunter.py      # Fase 3: empareja internas
```

NO modifiques el pipeline ni el clasificador. Este módulo lee el output clasificado y genera su propio output adicional.

## Criterios de cierre Fase 3

| Métrica | Objetivo |
|---------|----------|
| Pares encontrados | >80% de las Cat1=Interna emparejadas |
| Falsos positivos | <2% (pares que no deberían serlo) |
| Reporte de rutas | Generado con volúmenes por ruta |
| Internas sin pareja | Listadas y explicadas |
| Sin regresiones | Cat1/Cat2/Tipo accuracy sin cambios |
