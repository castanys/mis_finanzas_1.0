# 🚀 Quickstart - Pipeline de Transacciones (v3 con Excel + Logs)

## 5 Minutos para Empezar

### 1️⃣ Coloca tus CSVs en `input/`

```bash
input/
  ├── openbank_ES2200730100510135698457.csv
  ├── MyInvestor_ES5215447889746650686253.csv
  ├── Revolut_ES1215830001199090471794.csv
  └── ...
```

### 2️⃣ Procesa todas las transacciones (con Excel automático)

```bash
python3 process_transactions.py
```

**Salida esperada en pantalla + logs:**
```
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] ======================================================================
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] INICIANDO FINSENSE
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] ======================================================================
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] Directorio entrada: input
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] Maestro CSV: validate/Validacion_Categorias_Finsense_MASTER_v9.csv
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] BD: finsense.db

[2026-02-19 14:30:15] [INFO] [finsense.src.logger] Encontrados 16 archivos CSV en input
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] ✓ openbank_ES22...csv           55 tx
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] ✓ MyInvestor_ES52...csv          9 tx
[2026-02-19 14:30:15] [INFO] [finsense.src.logger] Total: 2078 transacciones nuevas

[2026-02-19 14:30:16] [INFO] [finsense.src.logger] Insertadas 2078 nuevas transacciones en BD
[2026-02-19 14:30:16] [INFO] [finsense.src.logger] Total en BD después: 15800
[2026-02-19 14:30:16] [INFO] [finsense.src.logger] Exportando a Excel...
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] ✓ Excel generado: output/transacciones_20260219_143017.xlsx

[2026-02-19 14:30:17] [INFO] [finsense.src.logger] ======================================================================
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] RESUMEN DE EJECUCIÓN
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] ======================================================================
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] Timestamp: 2026-02-19 14:30:17
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] Log guardado en: logs/finsense_20260219_143017.log

--- Estadísticas de Procesamiento ---
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   CSVs encontrados:                16
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   CSVs procesados:                16
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   CSVs ignorados:                 0
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   Transacciones leídas:           2078
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   Duplicados (mismo archivo):     0
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   Duplicados (ya en BD):          0
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   Nuevas transacciones:           2078
[2026-02-19 14:30:17] [INFO] [finsense.src.logger]   Total en BD después:            15800
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] ======================================================================
[2026-02-19 14:30:17] [INFO] [finsense.src.logger] FIN DE EJECUCIÓN
```

**Archivos generados automáticamente:**
- ✅ `output/transacciones_20260219_143017.xlsx` — Excel con todas las tx + id_contrapartida
- ✅ `logs/finsense_20260219_143017.log` — Log completo de la ejecución

### 3️⃣ Exporta a CSV/JSON adicionales (opcional)

```bash
# El Excel SIEMPRE se genera automáticamente
# Estos flags son opcionales si necesitas otros formatos

# CSV para herramientas externas
python3 process_transactions.py --output transacciones_2026.csv

# JSON para programación
python3 process_transactions.py --output-json transacciones_2026.json

# Ambos
python3 process_transactions.py -o transacciones.csv --output-json transacciones.json
```

---

## 📊 Casos de Uso Comunes

### Procesar todo (default) — genera Excel + Logs

```bash
python3 process_transactions.py
# Output:
# - output/transacciones_YYYYMMDD_HHMMSS.xlsx (con id_contrapartida)
# - logs/finsense_YYYYMMDD_HHMMSS.log
```

### Analizar transacciones de un solo banco

```bash
python3 process_transactions.py --file input/openbank_ES2200730100510135698457.csv
```

### Solo parsear sin clasificar (más rápido)

```bash
python3 process_transactions.py --no-classify
```

### Procesar sin insertar en BD (debug)

```bash
python3 process_transactions.py --no-db-insert
```

### Modo debug con logs detallados

```bash
python3 process_transactions.py --debug
# Muestra DEBUG level en pantalla + fichero
```

### Limpiar archivos con >30 días

```bash
python3 process_transactions.py --cleanup
# Elimina logs y Excels antiguos
```

### Procesar + CSV + JSON + Excel (full output)

```bash
python3 process_transactions.py -o output/tx.csv --output-json output/tx.json
# Genera automáticamente:
# - output/transacciones_YYYYMMDD_HHMMSS.xlsx
# - output/tx.csv
# - output/tx.json
# - logs/finsense_YYYYMMDD_HHMMSS.log
```

### Especificar maestro CSV distinto

```bash
python3 process_transactions.py --master-csv validate/mi_maestro.csv
```

---

## 🧪 Validar que Todo Funciona

### Test de parsers (30 segundos)

```bash
python3 test_parsers_manual.py
```

**✓ Esperado:** `10/10 parsers OK | Total: 1907 transacciones parseadas`

### Test del pipeline completo (1 minuto)

```bash
python3 test_pipeline_manual.py
```

**✓ Esperado:** `98.5% de cobertura de clasificación`

---

## 📁 Estructura de Archivos

```
mis_finanzas_1.0/
│
├── input/                          # 👈 Pon tus CSVs aquí
│   ├── openbank_*.csv
│   ├── MyInvestor_*.csv
│   └── ...
│
├── parsers/                        # Parsers de cada banco
│   ├── openbank.py
│   ├── myinvestor.py
│   └── ...
│
├── classifier/                     # Clasificador de 5 capas
│   ├── engine.py
│   ├── merchants.py
│   └── ...
│
├── pipeline.py                     # Motor principal
├── process_transactions.py         # 👈 Script principal (usa este)
│
├── test_parsers_manual.py         # Tests de parsers
├── test_pipeline_manual.py        # Tests de pipeline
│
├── README_PARSERS.md              # Documentación completa
└── QUICKSTART.md                  # Este archivo
```

---

## 🎯 Lo Que el Sistema Hace Automáticamente

**En cada ejecución:**
1. **Detecta el banco** del filename
2. **Parsea** usando el formato correcto
3. **Convierte** números españoles (`-2.210,00`) a formato estándar
4. **Convierte** fechas a formato ISO (`YYYY-MM-DD`)
5. **Extrae** IBAN del filename
6. **Deduplica** usando hash SHA256
7. **Clasifica** con 5 capas de reglas (98.5% precisión)
8. **Inserta** nuevas transacciones en BD
9. **Empareja** transferencias internas automáticamente
10. **Exporta** Excel completo con `id_contrapartida` para cada transferencia interna
11. **Genera** logs detallados de todo el proceso
12. **Limpia** archivos con >30 días de antigüedad

**Archivos de salida automáticos:**
- `output/transacciones_YYYYMMDD_HHMMSS.xlsx` — Excel con todas las tx + id_contrapartida
- `logs/finsense_YYYYMMDD_HHMMSS.log` — Log completo de ejecución
- Pantalla — Resumen ejecutivo en tiempo real

---

## 🏦 Bancos Soportados

| Banco | Estado | Ejemplo de Filename |
|-------|--------|---------------------|
| Openbank | ✅ | `openbank_ES2200730100510135698457.csv` |
| MyInvestor | ✅ | `MyInvestor_ES5215447889746650686253.csv` |
| Mediolanum | ✅ | `mediolanum_ES2501865001680510084831.csv` |
| Revolut | ✅ | `Revolut_ES1215830001199090471794.csv` |
| Trade Republic | ✅ | `TradeRepublic_ES8015860001420977164411.csv` |
| B100 | ✅ | `MovimientosB100_ES88208001000130433834426.csv` |
| Abanca | ✅ | `ABANCA_ES5120800823473040166463.csv` |

**Importante:** El filename DEBE contener el nombre del banco para autodetección.

---

## ❓ FAQ

### ¿Qué pasa si proceso el mismo CSV dos veces?

**R:** El sistema deduplica automáticamente. La segunda vez retorna 0 transacciones nuevas.

### ¿Puedo mezclar CSVs de diferentes bancos?

**R:** ¡Sí! El pipeline detecta automáticamente el banco de cada archivo.

### ¿Qué hago con transacciones sin clasificar?

**R:** Ejecuta `python3 analyze_unclassified.py` para ver qué transacciones no se clasificaron y añade reglas en `classifier/merchants.py` o `classifier/tokens.py`.

### ¿Cómo añado un nuevo banco?

**R:**
1. Crea un parser en `parsers/nuevo_banco.py`
2. Hereda de `BankParser`
3. Implementa el método `parse()`
4. Regístralo en `parsers/__init__.py`
5. Añade detección en `pipeline.detect_bank()`

### ¿Puedo usar esto programáticamente?

**R:** Sí, importa `TransactionPipeline`:

```python
from pipeline import TransactionPipeline

pipeline = TransactionPipeline('master.csv')
records = pipeline.process_directory('input/')
```

Ver `README_PARSERS.md` para API completa.

---

## 📋 Argumentos Disponibles

```bash
python3 process_transactions.py --help

Argumentos principales:
  --input-dir DIR           Directorio con CSVs (default: input)
  --master-csv CSV          Maestro CSV para exact match (default: validate/...)
  --db PATH                 BD SQLite (default: finsense.db)
  --file PATH               Procesar solo este archivo
  --output PATH             Exportar resultados a CSV
  --output-json PATH        Exportar resultados a JSON
  --output-dir DIR          Directorio para Excel (default: output)
  --no-classify             Solo parsear, sin clasificar
  --no-stats                No mostrar estadísticas
  --no-db-insert            No insertar en BD (debug)
  --cleanup                 Limpiar archivos >30 días
  --debug                   Modo debug (logs detallados)
```

---

## 🐛 Problemas Comunes

### "No se pudo detectar el banco"

**Causa:** El filename no contiene el nombre del banco

**Solución:** Renombra el archivo para incluir el banco:
```bash
mv movimientos.csv openbank_movimientos.csv
```

### "No se encuentra el master CSV"

**Causa:** Falta el CSV maestro para exact match

**Solución:**
```bash
python3 process_transactions.py --master-csv validate/Validacion_Categorias_Finsense_MASTER_v9.csv
```

### Números parseados incorrectamente

**Causa:** Formato español vs inglés

**Solución:** Verifica que el parser use `parse_spanish_number()` para formato español o `float()` para formato inglés.

### Transferencias sin pareja en Excel

**Verificación:** Abre `logs/finsense_*.log` y busca la sección "ADVERTENCIAS"
```
--- ⚠ ADVERTENCIAS: Transferencias Internas sin Pareja ---
  ID: 4831 | Fecha: 2024-01-15 | Importe:   -5000.00 | TRASPASO INTERNO A CUENTA CERRADA
```
**Causa:** Probablemente la contrapartida está en una cuenta no importada
**Solución:** Verificar que has importado todos los CSVs de tus cuentas

---

## 📈 Métricas de Éxito

Después de procesar, espera:

- ✅ **98%+** de cobertura de clasificación
- ✅ **0** duplicados
- ✅ **Todas** las fechas en formato ISO
- ✅ **Todos** los importes como float

---

## 🎓 Próximos Pasos

Una vez que hayas procesado tus transacciones:

1. **Abre el Excel:** `output/transacciones_YYYYMMDD_HHMMSS.xlsx`
   - Todas las columnas: id, fecha, importe, descripcion, banco, cuenta, tipo, cat1, cat2, hash, id_contrapartida
   - id_contrapartida solo tiene valor en transferencias internas (vincula entrada/salida)

2. **Revisa el log:** `logs/finsense_YYYYMMDD_HHMMSS.log`
   - Resumen completo de la ejecución
   - Advertencias de transferencias sin pareja
   - Debug si necesitas investigar

3. **Analiza** las transacciones sin clasificar (si las hay)
   ```bash
   python3 analyze_unclassified.py
   ```

4. **Exporta** a CSV/JSON para herramientas externas
   ```bash
   python3 process_transactions.py -o transacciones.csv --output-json transacciones.json
   ```

5. **Procesa** nuevos CSVs cuando los descargues
   ```bash
   # Los hashes se leen de BD automáticamente, así que no hay duplicados
   python3 process_transactions.py
   ```

---

## 📞 Documentación

- **Uso avanzado:** ver docstring de `process_transactions.py`
- **Documentación completa:** `README_PARSERS.md`
- **Tests:** `test_parsers_manual.py` y `test_pipeline_manual.py`
- **Estructura:** `FICHEROS_FINALES_v2.2.md`

---

## 🤖 Programación (uso como librería)

```python
from pipeline import TransactionPipeline
from src.exporter import ExcelExporter

# Procesar
pipeline = TransactionPipeline('validate/Validacion_Categorias_Finsense_MASTER_v9.csv')
records = pipeline.process_directory('input/')

# Exportar Excel con id_contrapartida
exporter = ExcelExporter('finsense.db')
excel_file = exporter.export_to_excel('output')
print(f"Generado: {excel_file}")
```

---

## 📅 Ejecución Automática (Cron)

**Procesar cada día a las 02:00:**
```bash
0 2 * * * cd /home/pablo/apps/mis_finanzas_1.0 && python3 process_transactions.py >> logs/cron.log 2>&1
```

**Procesar cada lunes a las 08:00:**
```bash
0 8 * * 1 cd /home/pablo/apps/mis_finanzas_1.0 && python3 process_transactions.py --cleanup
```

---

**¡Listo para procesar tus transacciones!** 🚀
