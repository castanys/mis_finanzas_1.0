#!/usr/bin/env python3
"""
Asistente Financiero Finsense - CLI

Uso:
  python3 ask.py "¿cuánto gasté en alimentación este mes?"
  python3 ask.py "resumen de enero"
  python3 ask.py "¿cómo voy de ahorro?"
  python3 ask.py "¿qué recibos me llegan este mes?"
  python3 ask.py --provider claude "análisis profundo de mis finanzas"

Modo interactivo:
  python3 ask.py
  > ¿cuánto gasté en bares en diciembre?
  > ¿y comparado con noviembre?
  > salir
"""
import sys
import os
import argparse
from src.ai_assistant import FinancialAssistant


def main():
    parser = argparse.ArgumentParser(
        description='Asistente Financiero Finsense',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 ask.py "¿cuánto gasté en enero?"
  python3 ask.py "resumen de este mes"
  python3 ask.py --provider ollama "¿cómo voy de ahorro?"
  python3 ask.py --debug "análisis de gastos"
        """
    )
    parser.add_argument('question', nargs='?', help='Pregunta directa')
    parser.add_argument('--provider', default='claude', choices=['ollama', 'claude'],
                        help='Provider LLM: ollama (local) o claude (API)')
    parser.add_argument('--model', default='qwen2.5:14b',
                        help='Modelo Ollama (default: qwen2.5:14b)')
    parser.add_argument('--claude-key', default=None,
                        help='API key de Claude (o usa ANTHROPIC_API_KEY env var)')
    parser.add_argument('--debug', action='store_true',
                        help='Muestra datos enviados al LLM')
    parser.add_argument('--db', default='finsense.db',
                        help='Ruta a la base de datos (default: finsense.db)')

    args = parser.parse_args()

    # Inicializar asistente
    try:
        assistant = FinancialAssistant(
            db_path=args.db,
            provider=args.provider,
            ollama_model=args.model,
            claude_api_key=args.claude_key
        )
    except Exception as e:
        print(f"❌ Error al inicializar asistente: {e}")
        sys.exit(1)

    try:
        if args.question:
            # Modo single question
            response = assistant.ask(args.question, debug=args.debug)
            print(response)
        else:
            # Modo interactivo
            provider_info = args.model if args.provider == 'ollama' else 'claude-sonnet-4.5'
            print("🏦 Finsense - Asistente Financiero")
            print(f"   Provider: {args.provider} ({provider_info})")
            print("   Escribe 'salir' para terminar\n")

            while True:
                try:
                    question = input("💬 > ").strip()
                    if question.lower() in ('salir', 'exit', 'quit', 'q'):
                        break
                    if not question:
                        continue

                    print()
                    response = assistant.ask(question, debug=args.debug)
                    print(response)
                    print()
                except KeyboardInterrupt:
                    print("\n👋 ¡Hasta luego!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}\n")

    finally:
        assistant.close()


if __name__ == '__main__':
    main()
