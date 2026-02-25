# FASE 4B: Asistente Financiero con LLM

## Contexto

La Fase 4A está cerrada: QueryEngine + SQLite + CLI funcionando. Ahora conectamos un LLM para que Pablo pueda hacer preguntas en lenguaje natural y recibir análisis inteligentes.

## Arquitectura

```
Pregunta usuario ("¿cómo voy este mes?")
    ↓
ai_assistant.py (detecta intención)
    ↓
query_engine.py (ejecuta consultas, devuelve datos JSON)
    ↓
LLM (recibe datos + pregunta → genera respuesta inteligente en español)
    ↓
Respuesta ("Este mes llevas gastados €2,345. Vas un 12% por debajo de tu media...")
```

## Paso 1: Instalar Ollama + modelo

```bash
# Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Descargar modelo (el VPS tiene 16GB RAM)
ollama pull qwen2.5:14b

# Verificar que funciona
ollama run qwen2.5:14b "Hola, responde en español: ¿cuánto es 2+2?"
```

Si qwen2.5:14b es demasiado pesado para 16GB, usar como fallback:
```bash
ollama pull qwen2.5:7b
```

## Paso 2: Implementar ai_assistant.py

```python
# src/ai_assistant.py
import json
import requests
from query_engine import QueryEngine

class FinancialAssistant:
    """
    Asistente financiero que combina QueryEngine + LLM.
    
    Flujo:
    1. Recibe pregunta en lenguaje natural
    2. Detecta intención y extrae parámetros (año, mes, categoría)
    3. Ejecuta las consultas relevantes del QueryEngine
    4. Envía datos + pregunta al LLM con system prompt financiero
    5. Devuelve respuesta en español
    """
    
    SYSTEM_PROMPT = """Eres el asistente financiero personal de Pablo. 
Analizas sus datos bancarios y respondes en español, de forma directa y útil.

Reglas:
- Sé conciso pero informativo. No repitas datos que Pablo puede ver.
- Destaca lo importante: alertas, tendencias, logros.
- Usa € para importes. Redondea a enteros para cantidades grandes.
- Si algo va bien, dilo. Si algo va mal, dilo claro con sugerencia.
- Pablo busca FIRE (independencia financiera) para 2029-2030. 
  Su ingreso mensual es ~4,000€. Cada euro ahorrado cuenta.
- NO inventes datos. Solo usa los que recibes en el contexto.
- Responde en el idioma de la pregunta (normalmente español).
"""

    def __init__(self, db_path='finsense.db', provider='ollama', 
                 ollama_model='qwen2.5:14b', ollama_url='http://localhost:11434',
                 claude_api_key=None):
        self.engine = QueryEngine(db_path)
        self.provider = provider
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url
        self.claude_api_key = claude_api_key
    
    def ask(self, question: str) -> str:
        """Pregunta en lenguaje natural → respuesta inteligente."""
        
        # 1. Detectar intención y recopilar datos
        context_data = self._gather_context(question)
        
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
        """
        from datetime import datetime, date
        
        # Detectar año y mes en la pregunta
        today = date.today()
        year = today.year
        month = today.month
        
        # Buscar año explícito (2024, 2025, etc.)
        import re
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
        
        try:
            context['resumen'] = self.engine.resumen_mensual(year, use_month or month)
        except:
            pass
        
        try:
            context['comparativa'] = self.engine.comparativa_mensual(year, use_month or month)
        except:
            pass
        
        try:
            context['ahorro'] = self.engine.evolucion_ahorro(meses=6)
        except:
            pass
        
        try:
            context['top_merchants'] = self.engine.top_merchants(n=10, year=year, month=use_month)
        except:
            pass
        
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
            except:
                pass
        
        for cat in categorias_mencionadas:
            if not cat.startswith('_'):
                try:
                    context[f'detalle_{cat}'] = self.engine.gasto_por_categoria_detalle(
                        cat, year, use_month)
                except:
                    pass
        
        return context
    
    def _build_prompt(self, question: str, context: dict) -> str:
        """Construye el prompt con datos para el LLM."""
        
        # Serializar contexto a JSON legible
        context_json = json.dumps(context, ensure_ascii=False, indent=2, default=str)
        
        # Limitar tamaño del contexto (modelos locales tienen ventana menor)
        if self.provider == 'ollama' and len(context_json) > 8000:
            # Priorizar resumen y comparativa, recortar el resto
            essential = {k: v for k, v in context.items() 
                        if k in ('pregunta_original', 'periodo_analizado', 'resumen', 'comparativa', 'ahorro')}
            context_json = json.dumps(essential, ensure_ascii=False, indent=2, default=str)
        
        return f"""Datos financieros de Pablo:

{context_json}

Pregunta de Pablo: {question}

Responde de forma directa y útil, en español. Incluye cifras concretas de los datos proporcionados."""
    
    def _call_ollama(self, user_prompt: str) -> str:
        """Llama al LLM local via Ollama API."""
        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Bajo para respuestas factuales
                    "num_predict": 1024,  # Respuestas concisas
                }
            },
            timeout=120  # 2 min timeout para modelo grande
        )
        response.raise_for_status()
        return response.json()['message']['content']
    
    def _call_claude(self, user_prompt: str) -> str:
        """Llama a Claude API."""
        import anthropic
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
```

## Paso 3: CLI interactivo

```python
# ask.py - CLI principal del asistente
# 
# Uso:
#   python3 ask.py "¿cuánto gasté en alimentación este mes?"
#   python3 ask.py "resumen de enero"
#   python3 ask.py "¿cómo voy de ahorro?"
#   python3 ask.py "¿qué recibos me llegan este mes?"
#   python3 ask.py --provider claude "análisis profundo de mis finanzas"
#
# Modo interactivo:
#   python3 ask.py
#   > ¿cuánto gasté en bares en diciembre?
#   > ¿y comparado con noviembre?
#   > salir

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Asistente financiero Finsense')
    parser.add_argument('question', nargs='?', help='Pregunta directa')
    parser.add_argument('--provider', default='ollama', choices=['ollama', 'claude'])
    parser.add_argument('--model', default='qwen2.5:14b', help='Modelo Ollama')
    parser.add_argument('--claude-key', default=None, help='API key de Claude')
    parser.add_argument('--debug', action='store_true', help='Muestra datos enviados al LLM')
    args = parser.parse_args()
    
    assistant = FinancialAssistant(
        provider=args.provider,
        ollama_model=args.model,
        claude_api_key=args.claude_key or os.environ.get('ANTHROPIC_API_KEY')
    )
    
    if args.question:
        # Modo single question
        response = assistant.ask(args.question)
        print(response)
    else:
        # Modo interactivo
        print("🏦 Finsense - Asistente Financiero")
        print(f"   Provider: {args.provider} ({args.model if args.provider == 'ollama' else 'claude'})")
        print("   Escribe 'salir' para terminar\n")
        
        while True:
            try:
                question = input("💬 > ").strip()
                if question.lower() in ('salir', 'exit', 'quit', 'q'):
                    break
                if not question:
                    continue
                
                print()
                response = assistant.ask(question)
                print(response)
                print()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    main()
```

## Paso 4: Verificación

Ejecuta estas preguntas de test y verifica que las respuestas son coherentes con los datos:

```bash
# Test básico
python3 ask.py "¿cuánto gasté en enero 2025?"

# Test por categoría
python3 ask.py "¿cuánto gasté en alimentación en enero?"

# Test comparativa
python3 ask.py "¿cómo va enero comparado con los meses anteriores?"

# Test ahorro
python3 ask.py "¿cómo voy de ahorro?"

# Test recurrentes
python3 ask.py "¿qué recibos me llegan este mes?"

# Test resumen
python3 ask.py "resumen de enero 2025"

# Test modo interactivo
python3 ask.py
```

Si Ollama no está instalado o el modelo no cabe en 16GB, usar Claude como fallback:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 ask.py --provider claude "resumen de enero"
```

## Criterios de cierre

| Métrica | Objetivo |
|---------|----------|
| Ollama instalado y modelo funcionando | ✅ |
| 6 preguntas de test respondidas con datos correctos | ✅ |
| Modo interactivo funcional | ✅ |
| Fallback a Claude API funcional | ✅ |
| Respuestas en español, concisas, con cifras reales | ✅ |
| Tiempo de respuesta Ollama < 30 segundos | ✅ |

## Notas para Code

1. **Ollama es prioridad.** Claude API es fallback. Si Ollama no se puede instalar en el VPS (permisos, etc.), usa solo Claude.
2. **Temperature baja (0.3).** Las respuestas deben ser factuales, no creativas.
3. **Limitar contexto para Ollama.** Los modelos locales tienen ventana de contexto más pequeña. Enviar solo los datos relevantes, no todo.
4. **El system prompt es clave.** Menciona FIRE, los 4,000€ de ingreso, y que sea directo. Pablo no quiere rodeos.
5. **NO hace falta detección perfecta de intención.** Es mejor enviar un contexto amplio y dejar que el LLM filtre, que fallar en parsear la pregunta.
6. **Si algo falla, mostrar el error claramente.** No tragarse excepciones en silencio.
