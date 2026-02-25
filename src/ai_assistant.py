"""
Asistente financiero con IA.

Recibe pregunta en lenguaje natural → consulta QueryEngine →
envía datos a LLM → devuelve respuesta inteligente.

Soporta dos providers:
1. Ollama (modelo local 13B en VPS con 16GB RAM) - para consultas rutinarias
2. Claude API (api key disponible) - para análisis profundos
"""
import json
import re
import os
import requests
from datetime import datetime, date
from typing import Dict, Optional
from .query_engine import QueryEngine


class FinancialAssistant:
    """Asistente financiero con IA que responde preguntas en lenguaje natural."""

    SYSTEM_PROMPT = """Eres el asistente financiero personal de Pablo.
Analizas sus datos bancarios y respondes en español, de forma directa y útil.

Reglas CRÍTICAS sobre datos:
- USA EXACTAMENTE los números del contexto JSON. NO reinterpretes ni calcules.
- Cuando el usuario pregunta por una CATEGORÍA (ej: "restaurantes", "transporte"):
  * Usa el TOTAL de cat1 (categoría principal), NO subcategorías (cat2)
  * Si el JSON tiene "cat1": "Restauración", "total": -525.66, usa -525.66
  * NO uses totales de subcategorías como "Otros" a menos que el usuario lo especifique
- Los porcentajes de comparativas deben ser claros:
  * "tasa_ahorro_pct" = ahorro/ingresos (ej: 10.7% significa que ahorraste el 10.7% de tus ingresos)
  * "variacion_pct" = cambio vs media de meses anteriores (ej: -43% = gastaste 43% menos)
  * NO confundas estos dos conceptos

Reglas de estilo:
- Sé conciso pero informativo. Destaca lo importante.
- Usa € para importes. Redondea a enteros para cantidades grandes.
- Si algo va bien, dilo. Si algo va mal, dilo claro con sugerencia.
- Pablo busca FIRE (independencia financiera) para 2029-2030.
  Su ingreso mensual es ~4,000€. Cada euro ahorrado cuenta.
- Responde en el idioma de la pregunta (normalmente español).
"""

    def __init__(
        self,
        db_path='finsense.db',
        provider='claude',
        ollama_model='qwen2.5:14b',
        ollama_url='http://localhost:11434',
        claude_api_key=None
    ):
        """
        Inicializa el asistente.

        Args:
            db_path: Ruta a la base de datos SQLite
            provider: 'ollama' o 'claude'
            ollama_model: Modelo de Ollama a usar
            ollama_url: URL del servidor Ollama
            claude_api_key: API key de Claude (si None, usa ANTHROPIC_API_KEY env var)
        """
        self.engine = QueryEngine(db_path)
        self.provider = provider
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url
        self.claude_api_key = claude_api_key or os.environ.get('ANTHROPIC_API_KEY')

    def ask(self, question: str, debug: bool = False) -> str:
        """
        Pregunta en lenguaje natural → respuesta inteligente.

        Args:
            question: Pregunta del usuario
            debug: Si True, imprime los datos enviados al LLM

        Returns:
            Respuesta del asistente

        Ejemplos:
            - "¿Cuánto gasté en restaurantes en enero?"
            - "Compara mis gastos de este mes con el promedio"
            - "¿Cuáles son mis recibos recurrentes?"
            - "¿Estoy ahorrando más o menos que antes?"
            - "Dame un resumen de enero 2025"
        """
        # 1. Detectar intención y recopilar datos
        context_data = self._gather_context(question)

        if debug:
            print("\n=== CONTEXTO ENVIADO AL LLM ===")
            print(json.dumps(context_data, ensure_ascii=False, indent=2, default=str))
            print("=" * 40 + "\n")

        # 2. Construir prompt con datos
        user_prompt = self._build_prompt(question, context_data)

        # 3. Enviar al LLM
        if self.provider == 'ollama':
            return self._call_ollama(user_prompt)
        elif self.provider == 'claude':
            return self._call_claude(user_prompt)
        else:
            raise ValueError(f"Provider desconocido: {self.provider}")

    def _gather_context(self, question: str) -> dict:
        """
        Analiza la pregunta y recopila datos relevantes del QueryEngine.

        Estrategia: en vez de intentar parsear la pregunta con NLP,
        recopila un contexto amplio y deja que el LLM filtre lo relevante.
        Esto es más robusto que intentar detectar intenciones exactas.

        Args:
            question: Pregunta del usuario

        Returns:
            Dict con contexto relevante
        """
        # Detectar año y mes en la pregunta
        today = date.today()
        year = today.year
        month = today.month

        # Buscar año explícito (2024, 2025, etc.)
        year_match = re.search(r'20[12]\d', question)
        if year_match:
            year = int(year_match.group())

        # Buscar mes explícito
        meses_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        q_lower = question.lower()
        for nombre, num in meses_map.items():
            if nombre in q_lower:
                month = num
                break

        # Si dice "este mes" o no especifica, usar mes actual
        # Si dice "el año" o "anual", month = None
        use_month = month
        if 'anual' in q_lower or 'el año' in q_lower or 'todo el año' in q_lower:
            use_month = None

        # Recopilar datos amplios (el LLM filtrará)
        context = {
            'pregunta_original': question,
            'fecha_consulta': today.isoformat(),
            'periodo_analizado': f"{year}-{month:02d}" if use_month else str(year),
        }

        # Recopilar datos según lo que pida la pregunta
        try:
            if use_month:
                context['resumen'] = self.engine.resumen_mensual(year, month)
            else:
                context['gasto_anual'] = self.engine.gasto_por_categoria(year)
        except Exception as e:
            context['error_resumen'] = str(e)

        try:
            if use_month:
                context['comparativa'] = self.engine.comparativa_mensual(year, month)
        except Exception as e:
            context['error_comparativa'] = str(e)

        try:
            context['ahorro'] = self.engine.evolucion_ahorro(meses=6)
        except Exception as e:
            context['error_ahorro'] = str(e)

        try:
            context['top_merchants'] = self.engine.top_merchants(n=10, year=year, month=use_month)
        except Exception as e:
            context['error_merchants'] = str(e)

        # Si pregunta por categoría específica
        categorias_mencionadas = []
        cat_keywords = {
            'alimentación': 'Alimentación', 'comida': 'Alimentación', 'supermercado': 'Alimentación',
            'restaura': 'Restauración', 'comer fuera': 'Restauración', 'bares': 'Restauración',
            'transporte': 'Transporte', 'gasolina': 'Transporte', 'combustible': 'Transporte',
            'suscripcion': 'Suscripciones', 'netflix': 'Suscripciones',
            'ocio': 'Ocio y Cultura', 'viaje': 'Viajes', 'ropa': 'Ropa y Calzado',
            'seguro': 'Seguros', 'hipoteca': 'Préstamos', 'salud': 'Salud y Belleza',
            'recurrente': '_recurrentes', 'recibo': '_recurrentes',
            'ahorro': '_ahorro', 'ahorr': '_ahorro',
        }
        for keyword, cat in cat_keywords.items():
            if keyword in q_lower:
                categorias_mencionadas.append(cat)

        if '_recurrentes' in categorias_mencionadas:
            try:
                context['recurrentes'] = self.engine.recibos_recurrentes()
            except Exception as e:
                context['error_recurrentes'] = str(e)

        for cat in categorias_mencionadas:
            if not cat.startswith('_'):
                try:
                    detalle = self.engine.gasto_por_categoria_detalle(cat, year, use_month)
                    # Simplificar: solo enviar el total de la categoría, no todas las subcategorías
                    context[f'gasto_{cat}'] = {
                        'categoria': cat,
                        'total': detalle['total'],
                        'periodo': detalle['periodo']
                    }
                except Exception as e:
                    context[f'error_{cat}'] = str(e)

        return context

    def _build_prompt(self, question: str, context: dict) -> str:
        """
        Construye el prompt con datos para el LLM.

        Args:
            question: Pregunta original
            context: Datos del QueryEngine

        Returns:
            Prompt formateado para el LLM
        """
        # Serializar contexto a JSON legible
        context_json = json.dumps(context, ensure_ascii=False, indent=2, default=str)

        # Limitar tamaño del contexto (modelos locales tienen ventana menor)
        if self.provider == 'ollama':
            # Para Ollama, solo enviar datos esenciales (mucho más compacto)
            essential = {}

            # Solo incluir resumen si existe
            if 'resumen' in context:
                essential['resumen'] = {
                    'periodo': context['resumen'].get('periodo'),
                    'gasto_total': context['resumen'].get('gasto_total'),
                    'ingreso_total': context['resumen'].get('ingreso_total'),
                    'ahorro': context['resumen'].get('ahorro'),
                    'tasa_ahorro_pct': context['resumen'].get('tasa_ahorro_pct'),
                    'nota': 'tasa_ahorro_pct es ahorro/ingresos, NO comparativa con meses anteriores',
                    'top_5_gastos': context['resumen'].get('top_5_gastos', [])[:3],  # Solo top 3
                    'alertas': context['resumen'].get('alertas', [])[:3],  # Solo 3 alertas
                }

            # Comparativa simplificada
            if 'comparativa' in context:
                essential['comparativa'] = {
                    'variacion_pct': context['comparativa'].get('variacion_pct'),
                    'nota': 'variacion_pct es cambio vs media de meses anteriores',
                    'alertas': context['comparativa'].get('alertas', [])[:3],
                }

            # Incluir gastos específicos de categorías si existen
            for key in context:
                if key.startswith('gasto_'):
                    essential[key] = context[key]

            context_json = json.dumps(essential, ensure_ascii=False, indent=2, default=str)

        return f"""Datos financieros de Pablo:

{context_json}

Pregunta de Pablo: {question}

Responde de forma directa y útil, en español. Incluye cifras concretas de los datos proporcionados."""

    def _call_ollama(self, user_prompt: str) -> str:
        """
        Llama al LLM local via Ollama API.

        Args:
            user_prompt: Prompt construido

        Returns:
            Respuesta del LLM
        """
        try:
            # Combinar system prompt con user prompt para /api/generate
            full_prompt = f"{self.SYSTEM_PROMPT}\n\nUsuario: {user_prompt}\n\nAsistente:"

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Bajo para respuestas factuales
                        "num_predict": 512,  # Respuestas más concisas
                    }
                },
                timeout=300  # 5 min timeout para modelo grande
            )
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            return f"❌ Error al llamar a Ollama: {e}\n\nPrueba con --provider claude si Ollama no está disponible."

    def _call_claude(self, user_prompt: str) -> str:
        """
        Llama a Claude API.

        Args:
            user_prompt: Prompt construido

        Returns:
            Respuesta del LLM
        """
        try:
            import anthropic
        except ImportError:
            return "❌ Error: anthropic no está instalado. Instala con: pip install anthropic"

        if not self.claude_api_key:
            return "❌ Error: ANTHROPIC_API_KEY no está configurada. Usa: export ANTHROPIC_API_KEY='sk-ant-...'"

        try:
            client = anthropic.Anthropic(api_key=self.claude_api_key)

            message = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            return f"❌ Error al llamar a Claude API: {e}"

    def close(self):
        """Cierra la conexión al QueryEngine."""
        self.engine.close()
