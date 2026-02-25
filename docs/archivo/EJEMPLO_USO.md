# 📖 Ejemplos de Uso del Sistema

## Inicio Rápido

### 1. Procesar Todos los CSVs
```bash
cd /home/pablo/apps/mis_finanzas_1.0
python3 process_transactions.py
```

**Salida:**
```
================================================================================
🚀 PIPELINE DE TRANSACCIONES BANCARIAS
================================================================================

✓ Cargadas 10606 descripciones únicas en Exact Match
✓ Pipeline inicializado con 0 transacciones conocidas en 0 cuentas

📁 Procesando 16 archivos CSV...
────────────────────────────────────────────────────────────────────────────────
✓ openbank_TOTAL_ES3600730100550435513660_EUR.csv              13529 parseadas
✓ ABANCA_ES5120800823473040166463.csv                             7 parseadas
✓ MovimientosB100_ES88208001000130433834426.csv                 148 parseadas
...
────────────────────────────────────────────────────────────────────────────────
Total: 15640 transacciones nuevas
```

---

## Casos de Uso Comunes

### 2. Exportar a CSV
```bash
python3 process_transactions.py --output mi_export.csv
```

**Resultado:** Archivo `mi_export.csv` con 15,640 transacciones clasificadas

**Columnas del CSV:**
- `fecha` - Fecha en formato YYYY-MM-DD
- `importe` - Importe en euros (float)
- `descripcion` - Descripción original
- `banco` - Nombre del banco
- `cuenta` - IBAN de la cuenta
- `cat1` - Categoría principal (ej: "Alimentación")
- `cat2` - Subcategoría (ej: "Supermercado")
- `tipo` - GASTO / INGRESO / TRANSFERENCIA / INVERSION
- `capa` - Capa de clasificación (1-5)
- `hash` - Hash SHA256 para deduplicación
- `source_file` - Archivo CSV origen
- `line_num` - Número de línea en el archivo origen

### 3. Exportar a JSON
```bash
python3 process_transactions.py --output-json transacciones.json
```

**Resultado:** Archivo JSON con array de objetos:
```json
[
  {
    "fecha": "2024-12-25",
    "importe": -50.00,
    "descripcion": "COMPRA EN MERCADONA",
    "banco": "Openbank",
    "cuenta": "ES3600730100550435513660",
    "cat1": "Alimentación",
    "cat2": "Supermercado",
    "tipo": "GASTO",
    "capa": 1,
    "hash": "abc123...",
    "source_file": "openbank_TOTAL.csv",
    "line_num": 1234
  },
  ...
]
```

### 4. Procesar un Solo Archivo
```bash
python3 process_transactions.py --file input/Revolut_ES1215830001199090471794.csv
```

**Uso:** Útil para probar un parser específico o procesar archivos nuevos

### 5. Solo Parsear (Sin Clasificar)
```bash
python3 process_transactions.py --no-classify --output raw_transactions.csv
```

**Uso:** Para verificar que el parsing funciona correctamente sin clasificación

### 6. Sin Estadísticas
```bash
python3 process_transactions.py --no-stats
```

**Uso:** Para procesamiento rápido sin mostrar estadísticas al final

---

## Análisis de Resultados

### 7. Ver Estadísticas Completas
```bash
python3 process_transactions.py
```

**Salida incluye:**
```
================================================================================
📊 ESTADÍSTICAS
================================================================================

📅 Periodo: 2004-05-03 → 2026-01-30
📝 Total transacciones: 15,640

💰 Totales:
  Ingresos: +€3,055,352.70
  Gastos:   -€3,055,719.10
  Balance:   €-366.40

🏦 Por banco:
  Openbank             13727 ( 87.8%)
  Trade Republic         920 (  5.9%)
  Mediolanum             457 (  2.9%)
  ...

📂 Por categoría (Top 10):
  Compras                         2784 ( 17.8%)
  Interna                         2468 ( 15.8%)
  Alimentación                    1551 (  9.9%)
  ...

🎯 Por tipo:
  GASTO                10178 ( 65.1%)
  TRANSFERENCIA         4290 ( 27.4%)
  INGRESO                836 (  5.3%)
  ...
```

### 8. Analizar Transacciones Sin Clasificar
```bash
python3 analyze_unclassified.py
```

**Salida:**
```
================================================================================
ANÁLISIS DE TRANSACCIONES SIN_CLASIFICAR
================================================================================

Total SIN_CLASIFICAR: 40

TOP MERCHANTS SIN CLASIFICAR:
  21x  Movimiento sin concepto (MyInvestor)
   4x  Movimiento Abanca
   6x  Openbank (merchants nuevos)
   ...
```

---

## Uso Programático (Python)

### 9. Usar el Pipeline en tu Código
```python
from pipeline import TransactionPipeline

# Inicializar
pipeline = TransactionPipeline(
    master_csv_path='Validación_Categorias_Finsense_04020206_5.csv'
)

# Procesar un archivo
records = pipeline.process_file('input/openbank_TOTAL.csv')

# Procesar directorio completo
all_records = pipeline.process_directory('input/')

# Exportar
pipeline.export_to_csv(all_records, 'output.csv')
pipeline.export_to_json(all_records, 'output.json')

# Estadísticas
stats = pipeline.get_statistics(all_records)
print(f"Total: {stats['total']}")
print(f"Balance: €{stats['total_ingreso'] - stats['total_gasto']:.2f}")
```

### 10. Usar un Parser Directamente
```python
from parsers import OpenbankParser, RevolutParser

# Parser individual
openbank = OpenbankParser()
records = openbank.parse('input/openbank_TOTAL.csv')

revolut = RevolutParser()
records = revolut.parse('input/Revolut_ES12*.csv')

# Cada record es un diccionario:
# {
#   'fecha': '2024-12-25',
#   'importe': -50.00,
#   'descripcion': 'COMPRA EN MERCADONA',
#   'banco': 'Openbank',
#   'cuenta': 'ES3600730100550435513660',
#   'line_num': 123,
#   'hash': 'abc123...'
# }
```

### 11. Clasificar Manualmente
```python
from classifier import Classifier

# Inicializar clasificador
classifier = Classifier(master_csv_path='Validación_Categorias_Finsense_04020206_5.csv')

# Clasificar una transacción
result = classifier.classify(
    descripcion='COMPRA EN MERCADONA',
    banco='Openbank',
    importe=-50.00
)

print(result)
# {
#   'cat1': 'Alimentación',
#   'cat2': 'Supermercado',
#   'tipo': 'GASTO',
#   'capa': 1,
#   'confidence': 0.95
# }
```

---

## Casos Avanzados

### 12. Procesar Archivos Nuevos (Incremental)
```python
from pipeline import TransactionPipeline
import json
import os

# Cargar hashes conocidos de ejecución anterior
if os.path.exists('known_hashes.json'):
    with open('known_hashes.json', 'r') as f:
        known_hashes = json.load(f)
else:
    known_hashes = {}

# Inicializar con hashes conocidos
pipeline = TransactionPipeline(
    master_csv_path='Validación_Categorias_Finsense_04020206_5.csv',
    known_hashes=known_hashes
)

# Procesar solo archivos nuevos
new_records = pipeline.process_file('input/nuevo_archivo.csv')

# Guardar hashes para próxima vez
with open('known_hashes.json', 'w') as f:
    json.dump(pipeline.known_hashes, f)

print(f"Procesadas {len(new_records)} transacciones nuevas")
```

### 13. Filtrar Resultados
```python
from pipeline import TransactionPipeline

pipeline = TransactionPipeline(master_csv_path='Validación_Categorias_Finsense_04020206_5.csv')
records = pipeline.process_directory('input/')

# Filtrar por categoría
alimentacion = [r for r in records if r['cat1'] == 'Alimentación']
print(f"Gastos en alimentación: {len(alimentacion)}")

# Filtrar por fecha
from datetime import datetime
records_2025 = [r for r in records if r['fecha'].startswith('2025')]

# Filtrar por banco
openbank_only = [r for r in records if r['banco'] == 'Openbank']

# Filtrar por importe
gastos_grandes = [r for r in records if r['importe'] < -100]

# Calcular totales
total_alimentacion = sum(abs(r['importe']) for r in alimentacion if r['importe'] < 0)
print(f"Total gastado en alimentación: €{total_alimentacion:.2f}")
```

### 14. Detectar el Banco de un Archivo
```python
from pipeline import TransactionPipeline

pipeline = TransactionPipeline(master_csv_path='Validación_Categorias_Finsense_04020206_5.csv')

# Detectar banco por filename y contenido
bank = pipeline.detect_bank('input/movimientos_desconocido.csv')
print(f"Banco detectado: {bank}")

# Opciones: openbank, myinvestor, mediolanum, revolut,
#           trade_republic, b100, abanca, preprocessed, unknown
```

### 15. Generar Reporte HTML
```python
from pipeline import TransactionPipeline
import json

pipeline = TransactionPipeline(master_csv_path='Validación_Categorias_Finsense_04020206_5.csv')
records = pipeline.process_directory('input/')
stats = pipeline.get_statistics(records)

# Generar HTML simple
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Reporte Financiero</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Reporte Financiero</h1>
    <p>Periodo: {stats['date_range']['min']} → {stats['date_range']['max']}</p>
    <p>Total transacciones: {stats['total']:,}</p>

    <h2>Balance</h2>
    <p>Ingresos: €{stats['total_ingreso']:,.2f}</p>
    <p>Gastos: €{stats['total_gasto']:,.2f}</p>
    <p>Balance: €{stats['total_ingreso'] - stats['total_gasto']:,.2f}</p>

    <h2>Por Categoría</h2>
    <table>
        <tr><th>Categoría</th><th>Transacciones</th><th>%</th></tr>
"""

for cat, count in sorted(stats['by_cat1'].items(), key=lambda x: -x[1])[:10]:
    pct = 100 * count / stats['total']
    html += f"        <tr><td>{cat}</td><td>{count}</td><td>{pct:.1f}%</td></tr>\n"

html += """
    </table>
</body>
</html>
"""

with open('output/reporte.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Reporte generado: output/reporte.html")
```

---

## Troubleshooting

### Error: "No se pudo detectar el banco del archivo"
**Causa:** El archivo no tiene un nombre que identifique el banco

**Solución 1:** Renombra el archivo para incluir el nombre del banco:
```bash
mv archivo.csv openbank_archivo.csv
```

**Solución 2:** Si es un archivo preprocessed, asegúrate que tiene los headers correctos:
```
Fecha,Importe,Descripcion,Banco,Cuenta
```

### Error: "No hay parser para el banco: XXX"
**Causa:** El banco no está soportado

**Solución:** Crea un nuevo parser basado en `parsers/base.py`:
```python
from parsers.base import BankParser

class NuevoBancoParser(BankParser):
    BANK_NAME = "NuevoBanco"

    def parse(self, filepath: str):
        # Implementa lógica de parsing
        pass
```

### Error: FileNotFoundError master CSV
**Causa:** No se encuentra el archivo maestro

**Solución:** Especifica la ruta correcta:
```bash
python3 process_transactions.py --master-csv /ruta/al/maestro.csv
```

### Warning: "X transacciones sin clasificar"
**Causa:** Hay transacciones que no coinciden con ninguna regla

**Solución:** Analiza y añade reglas:
```bash
python3 analyze_unclassified.py
# Revisa los merchants sin clasificar
# Añade reglas en classifier/merchants.py
```

---

## Comandos de Referencia Rápida

```bash
# Básico
python3 process_transactions.py

# Exportar
python3 process_transactions.py --output transacciones.csv
python3 process_transactions.py --output-json transacciones.json

# Procesar archivo específico
python3 process_transactions.py --file input/revolut.csv

# Sin clasificar (solo parsear)
python3 process_transactions.py --no-classify

# Sin estadísticas
python3 process_transactions.py --no-stats

# Analizar sin clasificar
python3 analyze_unclassified.py

# Combinaciones
python3 process_transactions.py \
  --output output/transacciones.csv \
  --output-json output/transacciones.json \
  --master-csv custom_maestro.csv
```

---

## Archivos Generados

### output/transacciones_completas.csv
CSV con todas las transacciones procesadas y clasificadas (15,640 filas)

### output/results.json
JSON con todas las transacciones en formato estructurado

### known_hashes.json (opcional)
Diccionario de hashes conocidos para procesamiento incremental

---

## Tips y Trucos

### 1. Verificar Conteos por Archivo
```python
import json
from collections import Counter

with open('output/results.json', 'r') as f:
    records = json.load(f)

by_file = Counter(r['source_file'] for r in records)
for filename, count in sorted(by_file.items()):
    print(f"{filename:60s} {count:5d}")
```

### 2. Exportar Solo Sin Clasificar
```python
from pipeline import TransactionPipeline

pipeline = TransactionPipeline(master_csv_path='Validación_Categorias_Finsense_04020206_5.csv')
records = pipeline.process_directory('input/')

sin_clasificar = [r for r in records if r['cat1'] == 'SIN_CLASIFICAR']
pipeline.export_to_csv(sin_clasificar, 'output/sin_clasificar.csv')
```

### 3. Comparar Versiones
```bash
# Procesar con versión actual
python3 process_transactions.py --output-json v1.json

# Hacer cambios en el código...

# Procesar con nueva versión
python3 process_transactions.py --output-json v2.json

# Comparar
python3 -c "
import json
with open('v1.json') as f: v1 = json.load(f)
with open('v2.json') as f: v2 = json.load(f)
print(f'V1: {len(v1)} transacciones')
print(f'V2: {len(v2)} transacciones')
print(f'Diferencia: {len(v2) - len(v1)}')
"
```

---

**Última actualización:** 2026-02-13
**Versión del sistema:** 1.0
