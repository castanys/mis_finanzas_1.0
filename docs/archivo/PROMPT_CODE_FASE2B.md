# FASE 2B: Validación, PDF Trade Republic, y Transferencias Internas

## Contexto
La Fase 2 está "completada" con 15,640 transacciones procesadas y 99.7% clasificadas. Pero ANTES de cerrarla necesitas ejecutar 3 tareas de verificación y ampliación.

**NO modifiques el clasificador existente ni los parsers que ya funcionan.** Solo añade y verifica.

---

## TAREA 1: Validación cruzada contra CSV maestro (CRÍTICA)

El CSV maestro `Validación_Categorias_Finsense_04020206_5.csv` tiene 15,640 transacciones ya clasificadas manualmente. Es la verdad absoluta.

**Lo que debes hacer:**

```python
# Pseudocódigo de la validación
maestro = cargar("Validación_Categorias_Finsense_04020206_5.csv")  
# Columnas: Fecha;Importe;Descripción;Banco;Cuenta;Tipo;Cat1;Cat2;Hash;id

output = cargar("output/transacciones_completas.csv")

# 1. ¿Mismo número de registros?
assert len(output) == len(maestro) == 15640

# 2. Para cada registro del maestro, ¿existe en output con mismos valores?
#    Comparar por: Fecha + Importe + Descripción + Banco + Cuenta
#    (NO comparar hash porque puede haberse generado diferente)

# 3. Donde AMBOS tienen clasificación, ¿coinciden Cat1 y Cat2?
#    Reportar: 
#    - Total coincidencias Cat1
#    - Total discrepancias Cat1 (listar las primeras 50)
#    - Total coincidencias Cat1+Cat2
#    - Total discrepancias Cat2 (listar las primeras 50)

# 4. Las 40 sin clasificar: ¿cuáles son? Listar todas con su Fecha, Importe, Descripción, Banco
```

**Output esperado:** Un reporte de validación con métricas y listado de discrepancias.

---

## TAREA 2: Parser PDF → CSV para Trade Republic

Trade Republic entrega sus extractos como PDF, no CSV. El CSV de 920 líneas que ya tienes fue generado previamente a partir de ese PDF y sirve como validación.

**Lo que debes hacer:**

1. Pablo te subirá el PDF de Trade Republic al directorio de trabajo
2. Usa `pdfplumber` (pip install pdfplumber) para extraer las tablas del PDF
3. Crea un parser `trade_republic_pdf.py` que:
   - Lee el PDF
   - Extrae cada transacción (fecha, descripción, importe)
   - Genera el formato unificado igual que los otros parsers
4. **VALIDA** comparando el resultado contra el CSV de 920 líneas existente:
   - ¿Mismo número de transacciones?
   - ¿Mismas fechas e importes?
   - ¿Descripciones coinciden o similares?
   - Reporta discrepancias

**Estructura del parser:**
```python
# src/parsers/trade_republic_pdf.py
class TradeRepublicPDFParser(BankParser):
    BANK_NAME = "Trade Republic"
    
    def parse(self, filepath: str) -> List[Dict]:
        """Parse Trade Republic PDF statement."""
        import pdfplumber
        # ... extraer transacciones del PDF
        # El PDF tiene un formato específico que debes descubrir
        # inspeccionando el archivo
```

**IMPORTANTE:** Antes de codear, inspecciona el PDF:
```python
import pdfplumber
with pdfplumber.open("ruta/al/pdf") as pdf:
    for i, page in enumerate(pdf.pages[:3]):
        print(f"=== Página {i} ===")
        print(page.extract_text()[:500])
        tables = page.extract_tables()
        for t in tables:
            for row in t[:5]:
                print(row)
```

---

## TAREA 3: Verificar detección de transferencias internas

Las transferencias internas son transacciones entre las propias cuentas de Pablo. Son críticas porque:
- Se anulan mutuamente (misma cantidad +/- entre dos cuentas)
- No deben contarse como gasto ni ingreso real
- La Fase 3 las cazará por pares, pero primero deben estar bien clasificadas

**Lo que debes verificar:**

1. En el output actual, ¿cuántas transacciones tienen Tipo=TRANSFERENCIA y Cat1=Interna?
2. Compara con el CSV maestro: ¿coincide la clasificación de internas?
3. Estos son los patrones que deben detectarse como transferencia interna POR BANCO:

```
OPENBANK:
  - "ORDEN TRASPASO INTERNO" → Interna
  - "TRASPASO INTERNO" → Interna  
  - "TRANSFERENCIA A FAVOR DE FERNANDEZ CASTANYS" → Interna (a cuenta propia)
  - "TRANSFERENCIA DE FERNANDEZ CASTANYS" → Interna (de cuenta propia)
  - "TRANSFERENCIA INMEDIATA A FAVOR DE Pablo" → Interna
  - "TRANSFERENCIA INMEDIATA DE Pablo" → Interna

MYINVESTOR:
  - "Movimiento MyInvestor salida" → Interna
  - "Movimiento MyInvestor entrada" → Interna
  - "FERNANDEZ CASTANYS ORTIZ DE VI" → Interna
  - "Transferencia desde MyInvestor" → Interna

MEDIOLANUM:
  - "Transf.de FERNANDEZ CASTANYS" → Interna (si viene de cuenta propia)
  - "SIN CONCEPTO" con importe redondo → Interna (posible)
  - "Transf. Inm. Concepto no especificado" → Interna (posible)

B100:
  - "FERNANDEZ CASTANYS ORTIZ DE VILLAJOS PABLO" → Interna
  - "Transferencia enviada" → Interna (posible, depende del destino)
  - "AHORRO PARA HUCHA" / "TRASPASO DESDE HUCHA" → Interna (movimiento dentro de B100)
  - "Move to save" / "OFF TO SAVE" → Interna (ahorro automático B100)

REVOLUT:
  - "Una recarga de Apple Pay con *XXXX" → Interna (recarga desde otra cuenta)
  - "Recarga de *****" → Interna

TRADE REPUBLIC:
  - "Ingreso aceptado: ESXXXX a Transferencia DEXXXX" → Interna (viene de cuenta propia)
  - "Transferencia PayOut to transit" → Interna (salida a cuenta propia)
  - "Incoming transfer from FERNANDEZ CASTANYS" → Interna

ABANCA:
  - "SIN CONCEPTO" con importe grande y redondo → MUY PROBABLE Interna
  - Las 4 de 7 transacciones Abanca marcadas como Interna en el maestro son "SIN CONCEPTO"

CASO ESPECIAL - BIZUM (Openbank):
  - "BIZUM A FAVOR DE..." → Tipo=TRANSFERENCIA pero Cat1=Bizum, NO Interna
  - "BIZUM DE..." → Tipo=TRANSFERENCIA pero Cat1=Bizum, NO Interna
  - Los Bizum NUNCA son internos (son pagos a terceros)
```

**Reporta:**
- Total transferencias internas detectadas vs maestro
- Falsos negativos: internas en el maestro que tu sistema clasifica como otra cosa
- Falsos positivos: las que tu sistema marca como internas pero en el maestro no lo son
- Caso Bizum: ¿se clasifican correctamente como Bizum y NO como Interna?

---

## Orden de ejecución

1. **Tarea 1 primero** — si la validación cruzada falla, hay que arreglar parsers antes de seguir
2. **Tarea 3 segundo** — verificar internas con los datos actuales
3. **Tarea 2 último** — el PDF parser es aditivo, no afecta lo existente

## Output esperado

Un reporte consolidado con:
```
=== VALIDACIÓN CRUZADA ===
Registros maestro: 15,640
Registros output:  15,640
Matches exactos:   X,XXX
Discrepancias Cat1: XX (listar)
Discrepancias Cat2: XX (listar)
Sin clasificar:     40 (listar todas)

=== TRANSFERENCIAS INTERNAS ===
Internas en maestro:    2,534  (o el número que sea)
Internas en output:     X,XXX
Coincidencias:          X,XXX
Falsos negativos:       XX (listar)
Falsos positivos:       XX (listar)
Bizums correctos:       XX/XX

=== PDF TRADE REPUBLIC ===
Transacciones en PDF:    XXX
Transacciones en CSV:    920
Matches:                 XXX
Discrepancias:           XX (listar)
```
