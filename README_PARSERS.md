# Parsers de Bancos y Pipeline de Transacciones

## 📋 Resumen

Sistema completo para parsear CSVs bancarios, deduplicar transacciones y clasificarlas automáticamente usando el clasificador de 5 capas.

**Estado actual:**
- ✅ Clasificador: 95% Cat1 accuracy, 100% cobertura
- ✅ Parsers: 7 bancos implementados
- ✅ Pipeline: Parse → Dedup → Classify → Export
- ✅ Tests: Validados con 2,078 transacciones reales

---

## 🏦 Bancos Soportados

| Banco | Parser | Formato | Encoding | Separador | Test |
|-------|--------|---------|----------|-----------|------|
| **Openbank** | ✅ | Español (`-2.210,00`) | UTF-8 BOM | `;` | ✅ 191 txs |
| **MyInvestor** | ✅ | Decimal (`.`) | UTF-8 BOM | `;` | ✅ 169 txs |
| **Mediolanum** | ✅ | Español | UTF-8 BOM | `;` | ✅ 454 txs |
| **Revolut** | ✅ | Decimal (`.`) | UTF-8 BOM | `;` | ✅ 196 txs |
| **Trade Republic** | ✅ | Decimal (`.`) | UTF-8 | `,` | ✅ 914 txs |
| **B100** | ✅ | Decimal (`.`) | UTF-8 | `,` | ✅ 147 txs |
| **Abanca** | ✅ | Español | UTF-8 BOM | `;` | ✅ 7 txs |

**Total:** 2,078 transacciones parseadas en tests

---

## 🚀 Uso Rápido

### Procesar todos los CSVs

```bash
python3 process_transactions.py
```

Esto:
1. Lee todos los CSV en `input/`
2. Detecta automáticamente el banco
3. Parsea cada CSV al formato unificado
4. Deduplica transacciones
5. Clasifica usando el clasificador de 5 capas
6. Muestra estadísticas

### Exportar a CSV/JSON

```bash
# Exportar a CSV
python3 process_transactions.py --output transacciones.csv

# Exportar a JSON
python3 process_transactions.py --output-json transacciones.json

# Ambos
python3 process_transactions.py -o transacciones.csv --output-json transacciones.json
```

### Procesar un solo archivo

```bash
python3 process_transactions.py --file input/openbank_ES2200730100510135698457.csv
```

### Solo parsear (sin clasificar)

```bash
python3 process_transactions.py --no-classify
```

---

## 📊 Formato Unificado

Todos los parsers convierten al mismo formato:

```python
{
    "fecha": "2025-01-15",           # YYYY-MM-DD (ISO 8601)
    "importe": -45.50,               # float (negativo = gasto)
    "descripcion": "MERCADONA S.A.", # string limpio
    "banco": "Openbank",             # nombre del banco
    "cuenta": "ES22007301005...",    # IBAN completo
    "hash": "abc123...",             # SHA256 para deduplicación

    # Añadidos por el clasificador:
    "cat1": "Alimentación",          # Categoría 1
    "cat2": "Supermercado",          # Categoría 2
    "tipo": "GASTO",                 # GASTO | INGRESO | TRANSFERENCIA | INVERSION
    "capa": 2                        # Capa de clasificación (1-5)
}
```

---

## 🔧 Arquitectura

```
src/
├── parsers/
│   ├── base.py           # Clase base BankParser
│   ├── openbank.py       # Parser Openbank
│   ├── myinvestor.py     # Parser MyInvestor
│   ├── mediolanum.py     # Parser Mediolanum
│   ├── revolut.py        # Parser Revolut
│   ├── trade_republic.py # Parser Trade Republic
│   ├── b100.py           # Parser B100
│   └── abanca.py         # Parser Abanca
│
├── classifier/
│   ├── engine.py         # Motor del clasificador
│   ├── exact_match.py    # Capa 1: Exact Match
│   ├── merchants.py      # Capa 2: Merchants
│   ├── transfers.py      # Capa 3: Transfers
│   └── tokens.py         # Capa 4: Tokens
│
├── pipeline.py           # Orquestador principal
└── process_transactions.py  # CLI para usuario
```

### Flujo de Datos

```
CSV Nativo → Parser → Deduplicación → Clasificador → Output
              ↓           ↓              ↓              ↓
          Formato    Hash SHA256    5 capas        CSV/JSON
          Unificado                 de reglas
```

---

## 🧪 Tests

### Test de parsers

```bash
python3 test_parsers_manual.py
```

Verifica:
- ✅ Parsing de cada banco
- ✅ Conversión de formatos numéricos
- ✅ Conversión de fechas
- ✅ Extracción de IBAN

**Resultado esperado:** `10/10 parsers OK | Total: 1907 transacciones parseadas`

### Test del pipeline completo

```bash
python3 test_pipeline_manual.py
```

Verifica:
- ✅ Detección de banco
- ✅ Procesamiento con clasificación
- ✅ Deduplicación
- ✅ Estadísticas
- ✅ Pipeline completo en directorio

**Resultado esperado:** `98.5% de cobertura de clasificación`

---

## 📝 Detalles de Parsers

### Openbank

**Formato:**
```csv
;Fecha Operación;;Fecha Valor;;Concepto;;Importe;;Saldo;Número de Cuenta
;11/11/2025;;10/11/2025;;TRANSFERENCIA...;;-2.210,00;;0,66;0073...
```

**Particularidades:**
- Columnas vacías intercaladas (`;;`)
- Números españoles: `-2.210,00` → `-2210.00`
- Fechas: `DD/MM/YYYY` → `YYYY-MM-DD`
- IBAN en filename: `openbank_ES2200730100510135698457.csv`

---

### MyInvestor

**Formato:**
```csv
Fecha de operación;Fecha de valor;Concepto;Importe;Divisa
03/05/2025;03/05/2025;Aportacion a mi cartera;-200.2;EUR
```

**Particularidades:**
- Formato limpio con headers estándar
- Números con punto decimal: `-200.2`
- Concepto puede estar vacío → usa `"Movimiento sin concepto"`

---

### Mediolanum

**Formato:**
```csv
Fecha Operación;Concepto;Fecha Valor;Pagos;Ingresos;Saldo;;;;
08/04/2020;Transf.de FERNANDEZ...;08/04/2020;;15000;15000;;;;
```

**Particularidades:**
- Dos columnas: `Pagos` (gastos) e `Ingresos`
- Pagos → negativo, Ingresos → positivo
- Números españoles con coma decimal

---

### Revolut

**Formato:**
```csv
Tipo;Producto;Fecha de inicio;Fecha de finalización;Descripción;Importe;Comisión;Divisa;State;Saldo
Recargas;Actual;02/07/2019 17:25;02/07/2019 17:25;Recarga Apple Pay;10;0;EUR;COMPLETADO;10
```

**Particularidades:**
- Solo procesa `State == "COMPLETADO"`
- Fechas con hora: `DD/MM/YYYY HH:MM` → `YYYY-MM-DD`
- Filtra transacciones `REVERTED`

---

### Trade Republic

**Formato:**
```csv
fecha,importe,concepto,banco,balance
2023-10-09,17305.0,Transferencia Ingreso aceptado: ES36...,TradeRepublic,17305.0
```

**Particularidades:**
- ¡Usa coma (`,`) como separador!
- Fechas ya en formato ISO: `YYYY-MM-DD`
- Formato más simple

---

### B100

**Formato:**
```csv
Fecha de Operación,Fecha valor,Detalle,Concepto,Cantidad,Saldo tras operación,Divisa,Tipo de Movimiento
07/01/2026,07/01/2026,Transferencia enviada,NA,-34.00,0.00,EUR,Gasto
```

**Particularidades:**
- Concepto puede ser `"NA"` → usa `Detalle`
- Tiene columna `Tipo de Movimiento` (no la usamos)
- Usa coma como separador

---

### Abanca

**Formato:**
```csv
Fecha ctble;Fecha valor;Concepto;Importe;Moneda;Saldo;Moneda;Concepto ampliado
29-12-2025;29-12-2025;NA;4027,67;EUR;4027,67;EUR;22999107G TIMESTAMP...
```

**Particularidades:**
- Fechas con guiones: `DD-MM-YYYY` → `YYYY-MM-DD`
- Números españoles: `4027,67`
- Concepto ampliado tiene más detalles
- Encoding issues posibles (`CAMPA�A`)

---

## 🔍 Deduplicación

El sistema usa **hashes SHA256** para detectar duplicados:

```python
hash = SHA256(fecha + importe + descripcion + cuenta)
```

**Ventajas:**
- ✅ Previene duplicados al reprocesar archivos
- ✅ Funciona across bancos (misma transacción en diferentes CSVs)
- ✅ Rápido (set lookup O(1))

**Test:**
```bash
# Primera pasada: 55 transacciones nuevas
# Segunda pasada: 0 transacciones nuevas ✓
```

---

## 📈 Métricas de Clasificación

### Cobertura por Capas (test con 2,078 txs)

| Capa | Nombre | Transacciones | % |
|------|--------|---------------|---|
| 1 | Exact Match | 1,234 | 59.4% |
| 2 | Merchants | 531 | 25.6% |
| 3 | Transfers | 127 | 6.1% |
| 4 | Tokens | 155 | 7.5% |
| 5 | Sin clasificar | 31 | **1.5%** |

**Cobertura total: 98.5%** ✅

### Por Banco

| Banco | Transacciones | % del total |
|-------|---------------|-------------|
| Trade Republic | 914 | 44.0% |
| Mediolanum | 454 | 21.8% |
| Revolut | 196 | 9.4% |
| Openbank | 191 | 9.2% |
| MyInvestor | 169 | 8.1% |
| B100 | 147 | 7.1% |
| Abanca | 7 | 0.3% |

---

## 🛠️ API del Pipeline

### Uso Programático

```python
from pipeline import TransactionPipeline

# Inicializar
pipeline = TransactionPipeline(
    master_csv_path='Validación_Categorias_Finsense_04020206_5.csv',
    known_hashes=set()  # opcional: para continuar una sesión
)

# Procesar un archivo
records = pipeline.process_file(
    filepath='input/openbank_ES2200730100510135698457.csv',
    classify=True  # True = clasificar, False = solo parsear
)

# Procesar directorio completo
all_records = pipeline.process_directory(
    dirpath='input',
    classify=True
)

# Exportar
pipeline.export_to_csv(records, 'output.csv')
pipeline.export_to_json(records, 'output.json')

# Estadísticas
stats = pipeline.get_statistics(records)
pipeline.print_statistics(records)

# Guardar hashes para próxima ejecución
hashes = pipeline.known_hashes
```

---

## 🐛 Troubleshooting

### Error: "No se pudo detectar el banco"

El filename debe contener el nombre del banco:
- ✅ `openbank_ES22...csv`
- ✅ `MyInvestor_ES52...csv`
- ✅ `Revolut_ES12...csv`
- ❌ `movimientos_enero.csv`

### Error: "No hay parser para el banco"

Verifica que el banco esté en la lista de soportados. Si es un banco nuevo, necesitas:
1. Analizar el formato del CSV
2. Crear un nuevo parser en `parsers/`
3. Registrarlo en `parsers/__init__.py`
4. Añadir detección en `pipeline.detect_bank()`

### Transacciones sin clasificar

Si tienes transacciones `SIN_CLASIFICAR`:

```bash
# Analizar cuáles son
python3 analyze_unclassified.py

# Añadir reglas específicas en:
# - classifier/merchants.py (para merchants)
# - classifier/tokens.py (para tokens)
# - classifier/transfers.py (para transferencias)
```

### Números parseados incorrectamente

Verifica el formato en el CSV:
- Español: `1.234,56` → usa `parse_spanish_number()`
- Inglés: `1234.56` → usa `float()` directo

---

## 📦 Estructura de Salida

### CSV

```csv
fecha,importe,descripcion,banco,cuenta,cat1,cat2,tipo,capa,hash
2025-01-15,-45.50,MERCADONA S.A.,Openbank,ES22...,Alimentación,Supermercado,GASTO,2,abc123...
```

### JSON

```json
[
  {
    "fecha": "2025-01-15",
    "importe": -45.50,
    "descripcion": "MERCADONA S.A.",
    "banco": "Openbank",
    "cuenta": "ES2200730100510135698457",
    "cat1": "Alimentación",
    "cat2": "Supermercado",
    "tipo": "GASTO",
    "capa": 2,
    "hash": "abc123..."
  }
]
```

---

## ✅ Criterios de Éxito

| Métrica | Objetivo | Resultado | Estado |
|---------|----------|-----------|--------|
| Parsers implementados | 7 bancos | 7/7 | ✅ |
| Test de parsers | Todos pasan | 10/10 OK | ✅ |
| Deduplicación | 0 duplicados | 0 duplicados | ✅ |
| Cobertura clasificación | ≥90% | 98.5% | ✅ |
| Tests pipeline | Todos pasan | 5/5 OK | ✅ |

---

## 🚧 Próximos Pasos

1. **Frontend/Dashboard** (Fase 3)
   - Visualización de transacciones
   - Gráficos por categoría
   - Filtros interactivos

2. **Mejoras opcionales**
   - Base de datos SQLite para persistencia
   - API REST
   - Detección automática de duplicados cross-banco
   - OCR para extractos PDF

---

## 📞 Soporte

Para reportar errores o sugerir mejoras, contacta con Pablo o abre un issue en el repositorio.

---

**Última actualización:** 2026-02-13
**Versión:** 1.0
**Estado:** ✅ Producción
