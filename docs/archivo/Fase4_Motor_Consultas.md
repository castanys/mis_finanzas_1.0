# FASE 4: Motor de Consultas Financieras

## Contexto

Tienes 15,640 transacciones clasificadas en `output/transacciones_completas.csv` con columnas:
- Fecha, Importe, Descripción, Banco, Cuenta, Tipo, Cat1, Cat2, Hash, id
- Columnas extra de Fase 3: par_id, par_tipo

El objetivo es construir un motor que responda preguntas financieras sobre estos datos.
Este motor será consumido después por un LLM (local o Claude API) para dar respuestas en lenguaje natural.

## Paso 1: Base de datos SQLite

Carga las transacciones en SQLite para consultas eficientes:

```sql
CREATE TABLE transacciones (
    id INTEGER PRIMARY KEY,
    fecha DATE NOT NULL,
    importe REAL NOT NULL,
    descripcion TEXT,
    banco TEXT,
    cuenta TEXT,
    tipo TEXT,          -- GASTO, INGRESO, TRANSFERENCIA, INVERSION
    cat1 TEXT,
    cat2 TEXT,
    hash TEXT UNIQUE,
    par_id TEXT,         -- NULL si no emparejada
    par_tipo TEXT,       -- emparejada, interna_sin_pareja, hucha_b100, etc.
    source_file TEXT
);

-- Índices para queries rápidas
CREATE INDEX idx_fecha ON transacciones(fecha);
CREATE INDEX idx_tipo ON transacciones(tipo);
CREATE INDEX idx_cat1 ON transacciones(cat1);
CREATE INDEX idx_cat2 ON transacciones(cat2);
CREATE INDEX idx_banco ON transacciones(banco);
CREATE INDEX idx_year_month ON transacciones(strftime('%Y-%m', fecha));
```

## Paso 2: Módulo de consultas

Crear `src/query_engine.py` con funciones que devuelven datos estructurados (diccionarios/listas), NO strings formateados. La capa de presentación viene después.

### Consultas requeridas:

```python
class QueryEngine:
    """Motor de consultas financieras sobre transacciones clasificadas."""
    
    def __init__(self, db_path='finsense.db'):
        self.db = sqlite3.connect(db_path)
    
    # =========================================
    # 1. GASTO POR CATEGORÍA
    # =========================================
    
    def gasto_por_categoria(self, year: int, month: int = None) -> dict:
        """
        Gasto total por Cat1, opcionalmente filtrado por mes.
        EXCLUYE: Tipo=TRANSFERENCIA y Tipo=INVERSION (solo GASTO puro).
        
        Returns: {
            'periodo': '2025-01' o '2025',
            'total': -1234.56,
            'categorias': [
                {'cat1': 'Alimentación', 'total': -456.78, 'pct': 37.0,
                 'subcategorias': [
                     {'cat2': 'Mercadona', 'total': -234.56, 'pct': 51.3},
                     {'cat2': 'Lidl', 'total': -123.45, 'pct': 27.0},
                 ]},
                ...
            ]
        }
        """
    
    def gasto_por_categoria_detalle(self, cat1: str, year: int, month: int = None) -> dict:
        """Desglose de Cat2 dentro de una Cat1 específica."""
    
    # =========================================
    # 2. COMPARATIVA MENSUAL
    # =========================================
    
    def comparativa_mensual(self, year: int, month: int, meses_atras: int = 6) -> dict:
        """
        Compara el mes actual con los N meses anteriores.
        
        Returns: {
            'mes_actual': {'periodo': '2025-01', 'gasto_total': -2345.67},
            'media_anterior': -2100.00,
            'variacion_pct': +11.7,  # positivo = gastas más
            'por_categoria': [
                {
                    'cat1': 'Alimentación',
                    'mes_actual': -456.78,
                    'media_anterior': -400.00,
                    'variacion_pct': +14.2,
                    'tendencia': 'subiendo'  # subiendo/bajando/estable (±5%)
                },
                ...
            ],
            'alertas': [
                'Restauración: +32% vs media (€234 más de lo habitual)',
                'Transporte: -15% vs media (€45 menos, buen mes)',
            ]
        }
        """
    
    # =========================================
    # 3. RECIBOS RECURRENTES
    # =========================================
    
    def recibos_recurrentes(self, year: int = None, month: int = None) -> dict:
        """
        Detecta gastos recurrentes (mismo merchant, frecuencia regular).
        Un recibo es recurrente si aparece >=3 veces con periodicidad similar.
        
        Returns: {
            'recurrentes': [
                {
                    'descripcion': 'RECIBO SEGURO HOGAR',
                    'cat1': 'Seguros',
                    'frecuencia': 'mensual',  # mensual/trimestral/anual
                    'importe_medio': -89.50,
                    'ultimo_cargo': '2025-01-15',
                    'proximo_estimado': '2025-02-15',
                    'total_anual_estimado': -1074.00,
                },
                ...
            ],
            'total_mensual_recurrente': -567.89,
            'total_anual_recurrente': -6814.68,
        }
        """
    
    # =========================================
    # 4. EVOLUCIÓN DE AHORRO
    # =========================================
    
    def evolucion_ahorro(self, meses: int = 12) -> dict:
        """
        Calcula ahorro mensual = ingresos - gastos (excluyendo transferencias internas).
        
        IMPORTANTE: 
        - Ingresos = Tipo=INGRESO (nóminas, intereses, etc.)
        - Gastos = Tipo=GASTO (compras, recibos, etc.)
        - EXCLUIR Tipo=TRANSFERENCIA (movimiento entre cuentas, no es gasto ni ingreso real)
        - EXCLUIR Tipo=INVERSION (es ahorro/inversión, no gasto consumo)
        
        Returns: {
            'meses': [
                {
                    'periodo': '2025-01',
                    'ingresos': 4000.00,
                    'gastos': -2345.67,
                    'ahorro': 1654.33,
                    'tasa_ahorro_pct': 41.4,  # ahorro/ingresos * 100
                },
                ...
            ],
            'media_ahorro': 1200.00,
            'tendencia': 'mejorando',  # mejorando/empeorando/estable
            'mejor_mes': {'periodo': '2025-03', 'ahorro': 2100.00},
            'peor_mes': {'periodo': '2024-11', 'ahorro': 200.00},
        }
        """
    
    # =========================================
    # 5. TOP MERCHANTS
    # =========================================
    
    def top_merchants(self, n: int = 20, year: int = None, month: int = None) -> dict:
        """
        Top N merchants por volumen de gasto.
        Agrupa por Cat2 (merchant específico) o por descripción normalizada.
        
        Returns: {
            'periodo': '2025' o '2025-01',
            'top': [
                {
                    'merchant': 'Mercadona',
                    'cat1': 'Alimentación',
                    'total': -3456.78,
                    'num_transacciones': 87,
                    'ticket_medio': -39.73,
                },
                ...
            ]
        }
        """
    
    # =========================================
    # 6. RESUMEN MENSUAL INTELIGENTE
    # =========================================
    
    def resumen_mensual(self, year: int, month: int) -> dict:
        """
        Resumen completo de un mes. Esta función es la que el LLM
        usará para generar el análisis en lenguaje natural.
        
        Combina: gasto por categoría + comparativa + recurrentes + ahorro + top merchants
        
        Returns: {
            'periodo': '2025-01',
            'gasto_total': -2345.67,
            'ingreso_total': 4000.00,
            'ahorro': 1654.33,
            'tasa_ahorro_pct': 41.4,
            'vs_media': {
                'variacion_pct': +5.2,
                'categorias_arriba': [...],   # gastaste más
                'categorias_abajo': [...],    # gastaste menos
            },
            'top_5_gastos': [...],
            'recurrentes_del_mes': [...],
            'alertas': [
                'Has gastado un 32% más en Restauración que tu media de 6 meses',
                'Tu ahorro este mes (41.4%) es mejor que tu media (35%)',
                'Mercadona: ticket medio 42 EUR vs 38 EUR habitual (+10%)',
            ],
            'logros': [
                'Mejor mes de ahorro en los últimos 6 meses',
                'Has reducido Suscripciones un 15%',
            ],
        }
        """
```

## Paso 3: Script CLI para testing

```python
# query_cli.py - Para probar el motor desde terminal

# Comandos estructurados:
# python3 query_cli.py gasto 2025 1              -> gasto enero 2025
# python3 query_cli.py comparar 2025 1            -> compara enero vs meses previos
# python3 query_cli.py recurrentes                 -> lista recibos recurrentes
# python3 query_cli.py ahorro 12                   -> evolución ahorro 12 meses
# python3 query_cli.py merchants 2025              -> top merchants 2025
# python3 query_cli.py resumen 2025 1              -> resumen completo enero
```

## Paso 4: Integración con LLM (preparar, NO implementar aún)

Deja preparado un fichero `src/ai_assistant.py` con la estructura:

```python
# src/ai_assistant.py
"""
Asistente financiero con IA.
Recibe pregunta en lenguaje natural -> consulta QueryEngine -> 
envía datos a LLM -> devuelve respuesta inteligente.

Soportará dos providers:
1. Ollama (modelo local 13B en VPS con 16GB RAM) - para consultas rutinarias
2. Claude API (api key disponible) - para análisis profundos

NO IMPLEMENTAR AÚN. Solo dejar la estructura.
"""

class FinancialAssistant:
    def __init__(self, query_engine, provider='ollama'):
        self.engine = query_engine
        self.provider = provider  # 'ollama' o 'claude'
    
    def ask(self, question: str) -> str:
        """
        Flujo:
        1. Parsear la pregunta (detectar intención: gasto, comparar, recurrentes, etc.)
        2. Llamar a la función correcta del QueryEngine
        3. Enviar los datos + la pregunta original al LLM
        4. LLM genera respuesta en lenguaje natural con análisis
        """
        pass  # TODO: Fase 4B
```

## Validación

```bash
# Ejecutar todas las consultas y verificar que devuelven datos coherentes
python3 query_cli.py gasto 2025 1
python3 query_cli.py comparar 2025 1
python3 query_cli.py recurrentes
python3 query_cli.py ahorro 12
python3 query_cli.py merchants 2025
python3 query_cli.py resumen 2025 1
```

Criterios:
- Todas las funciones devuelven datos sin errores
- Los totales cuadran (gasto + ingreso = ahorro)
- Transferencias internas emparejadas están EXCLUIDAS de gastos/ingresos
- Recurrentes detectados son razonables (hipoteca, seguros, suscripciones)
- Top merchants coinciden con lo que Pablo esperaría (Mercadona, gasolineras, etc.)

## Notas para Code

1. **EXCLUIR transferencias de los cálculos de gasto/ingreso.** Solo Tipo=GASTO y Tipo=INGRESO cuentan.
2. **Las inversiones NO son gasto.** Tipo=INVERSION se excluye del gasto pero puede tener su propia sección.
3. **Usar par_tipo para filtrar.** Las transacciones con par_tipo='emparejada' son internas confirmadas.
4. **Fechas:** los datos van de 2004 a 2026. Para comparativas, usar solo los últimos 12-24 meses relevantes.
5. **Los importes negativos son gastos.** Positivos son ingresos. No confundir signos.
6. **NO construir frontend.** Solo motor + CLI. La presentación viene después con LLM.
