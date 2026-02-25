#!/usr/bin/env python3
"""
CLI para probar el motor de consultas financieras.

Uso:
    python3 query_cli.py gasto 2025 1              # gasto enero 2025
    python3 query_cli.py comparar 2025 1            # compara enero vs meses previos
    python3 query_cli.py recurrentes                 # lista recibos recurrentes
    python3 query_cli.py ahorro 12                   # evolución ahorro 12 meses
    python3 query_cli.py merchants 2025              # top merchants 2025
    python3 query_cli.py resumen 2025 1              # resumen completo enero
"""
import sys
import json
from src.query_engine import QueryEngine


def print_json(data):
    """Imprime datos en formato JSON legible."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def format_currency(amount):
    """Formatea cantidad como moneda."""
    return f"€{abs(amount):,.2f}" if amount < 0 else f"€{amount:,.2f}"


def print_gasto_por_categoria(data):
    """Imprime gasto por categoría de forma legible."""
    print(f"\n{'='*60}")
    print(f"  GASTO POR CATEGORÍA - {data['periodo']}")
    print(f"{'='*60}\n")
    print(f"  Total gastado: {format_currency(data['total'])}\n")
    print(f"{'Categoría':<30} {'Gasto':>12} {'%':>6} {'Tx':>5}")
    print(f"{'-'*55}")

    for cat in data['categorias']:
        print(f"{cat['cat1']:<30} {format_currency(cat['total']):>12} {cat['pct']:>5.1f}% {cat['num_tx']:>5}")

        # Mostrar subcategorías si existen y son relevantes
        if cat['subcategorias'] and len(cat['subcategorias']) > 1:
            for sub in cat['subcategorias'][:5]:  # Top 5
                print(f"  ↳ {sub['cat2']:<26} {format_currency(sub['total']):>12} {sub['pct']:>5.1f}% {sub['num_tx']:>5}")


def print_comparativa(data):
    """Imprime comparativa mensual."""
    print(f"\n{'='*60}")
    print(f"  COMPARATIVA MENSUAL - {data['mes_actual']['periodo']}")
    print(f"{'='*60}\n")
    print(f"  Gasto este mes: {format_currency(data['mes_actual']['gasto_total'])}")
    print(f"  Media 6 meses:  {format_currency(data['media_anterior'])}")
    print(f"  Variación:      {data['variacion_pct']:+.1f}%\n")

    if data['alertas']:
        print("  🚨 Alertas:")
        for alerta in data['alertas']:
            print(f"    • {alerta}")
        print()

    print(f"{'Categoría':<30} {'Este mes':>12} {'Media':>12} {'Var%':>6} {'Tend':<10}")
    print(f"{'-'*75}")

    for cat in data['por_categoria'][:15]:  # Top 15
        tendencia_emoji = {'subiendo': '📈', 'bajando': '📉', 'estable': '→'}
        emoji = tendencia_emoji.get(cat['tendencia'], '')
        print(f"{cat['cat1']:<30} {format_currency(cat['mes_actual']):>12} "
              f"{format_currency(cat['media_anterior']):>12} {cat['variacion_pct']:>5.1f}% "
              f"{emoji} {cat['tendencia']:<10}")


def print_recurrentes(data):
    """Imprime recibos recurrentes."""
    print(f"\n{'='*60}")
    print(f"  RECIBOS RECURRENTES")
    print(f"{'='*60}\n")
    print(f"  Total mensual recurrente: {format_currency(data['total_mensual_recurrente'])}")
    print(f"  Total anual estimado:     {format_currency(data['total_anual_recurrente'])}\n")

    if not data['recurrentes']:
        print("  No se encontraron recibos recurrentes.\n")
        return

    print(f"{'Descripción':<35} {'Frec':<12} {'Importe':>10} {'Próximo':>12}")
    print(f"{'-'*75}")

    for rec in data['recurrentes'][:20]:  # Top 20
        desc = rec['descripcion'][:34]
        print(f"{desc:<35} {rec['frecuencia']:<12} {format_currency(rec['importe_medio']):>10} "
              f"{rec['proximo_estimado']:>12}")


def print_ahorro(data):
    """Imprime evolución de ahorro."""
    print(f"\n{'='*60}")
    print(f"  EVOLUCIÓN DE AHORRO - Últimos {len(data['meses'])} meses")
    print(f"{'='*60}\n")
    print(f"  Media de ahorro: {format_currency(data['media_ahorro'])}")
    print(f"  Tendencia:       {data['tendencia']}")
    print(f"  Mejor mes:       {data['mejor_mes']['periodo']} ({format_currency(data['mejor_mes']['ahorro'])})")
    print(f"  Peor mes:        {data['peor_mes']['periodo']} ({format_currency(data['peor_mes']['ahorro'])})\n")

    print(f"{'Periodo':<10} {'Ingresos':>12} {'Gastos':>12} {'Ahorro':>12} {'Tasa%':>8}")
    print(f"{'-'*60}")

    for mes in data['meses']:
        print(f"{mes['periodo']:<10} {format_currency(mes['ingresos']):>12} "
              f"{format_currency(mes['gastos']):>12} {format_currency(mes['ahorro']):>12} "
              f"{mes['tasa_ahorro_pct']:>7.1f}%")


def print_top_merchants(data):
    """Imprime top merchants."""
    print(f"\n{'='*60}")
    print(f"  TOP MERCHANTS - {data['periodo']}")
    print(f"{'='*60}\n")

    print(f"{'#':<3} {'Merchant':<35} {'Categoría':<20} {'Total':>12} {'Tx':>5}")
    print(f"{'-'*80}")

    for i, merchant in enumerate(data['top'], 1):
        merc_name = merchant['merchant'][:34]
        print(f"{i:<3} {merc_name:<35} {merchant['cat1']:<20} "
              f"{format_currency(merchant['total']):>12} {merchant['num_transacciones']:>5}")


def print_resumen(data):
    """Imprime resumen mensual completo."""
    print(f"\n{'='*60}")
    print(f"  RESUMEN MENSUAL - {data['periodo']}")
    print(f"{'='*60}\n")

    print(f"  💰 Finanzas:")
    print(f"     Ingresos:     {format_currency(data['ingreso_total'])}")
    print(f"     Gastos:       {format_currency(data['gasto_total'])}")
    print(f"     Ahorro:       {format_currency(data['ahorro'])} ({data['tasa_ahorro_pct']:.1f}%)\n")

    print(f"  📊 vs Media (6 meses): {data['vs_media']['variacion_pct']:+.1f}%\n")

    if data['vs_media']['categorias_arriba']:
        print("  📈 Categorías que subieron:")
        for cat in data['vs_media']['categorias_arriba']:
            print(f"     • {cat['cat1']}: {cat['variacion_pct']:+.1f}%")
        print()

    if data['vs_media']['categorias_abajo']:
        print("  📉 Categorías que bajaron:")
        for cat in data['vs_media']['categorias_abajo']:
            print(f"     • {cat['cat1']}: {cat['variacion_pct']:+.1f}%")
        print()

    if data['top_5_gastos']:
        print("  🏆 Top 5 Gastos:")
        for i, merc in enumerate(data['top_5_gastos'], 1):
            print(f"     {i}. {merc['merchant'][:30]}: {format_currency(merc['total'])}")
        print()

    if data['alertas']:
        print("  🚨 Alertas:")
        for alerta in data['alertas']:
            print(f"     • {alerta}")
        print()

    if data['logros']:
        print("  🎯 Logros:")
        for logro in data['logros']:
            print(f"     • {logro}")
        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    comando = sys.argv[1]

    # Inicializar motor
    engine = QueryEngine('finsense.db')

    try:
        if comando == 'gasto':
            if len(sys.argv) < 3:
                print("Uso: python3 query_cli.py gasto YEAR [MONTH]")
                sys.exit(1)
            year = int(sys.argv[2])
            month = int(sys.argv[3]) if len(sys.argv) > 3 else None
            data = engine.gasto_por_categoria(year, month)
            print_gasto_por_categoria(data)

        elif comando == 'comparar':
            if len(sys.argv) < 4:
                print("Uso: python3 query_cli.py comparar YEAR MONTH [MESES_ATRAS]")
                sys.exit(1)
            year = int(sys.argv[2])
            month = int(sys.argv[3])
            meses_atras = int(sys.argv[4]) if len(sys.argv) > 4 else 6
            data = engine.comparativa_mensual(year, month, meses_atras)
            print_comparativa(data)

        elif comando == 'recurrentes':
            year = int(sys.argv[2]) if len(sys.argv) > 2 else None
            month = int(sys.argv[3]) if len(sys.argv) > 3 else None
            data = engine.recibos_recurrentes(year, month)
            print_recurrentes(data)

        elif comando == 'ahorro':
            meses = int(sys.argv[2]) if len(sys.argv) > 2 else 12
            data = engine.evolucion_ahorro(meses)
            print_ahorro(data)

        elif comando == 'merchants':
            year = int(sys.argv[2]) if len(sys.argv) > 2 else None
            month = int(sys.argv[3]) if len(sys.argv) > 3 else None
            n = int(sys.argv[4]) if len(sys.argv) > 4 else 20
            data = engine.top_merchants(n, year, month)
            print_top_merchants(data)

        elif comando == 'resumen':
            if len(sys.argv) < 4:
                print("Uso: python3 query_cli.py resumen YEAR MONTH")
                sys.exit(1)
            year = int(sys.argv[2])
            month = int(sys.argv[3])
            data = engine.resumen_mensual(year, month)
            print_resumen(data)

        elif comando == 'json':
            # Modo debug: devuelve JSON crudo
            if len(sys.argv) < 3:
                print("Uso: python3 query_cli.py json COMANDO [ARGS...]")
                sys.exit(1)
            sub_comando = sys.argv[2]
            if sub_comando == 'gasto':
                year = int(sys.argv[3])
                month = int(sys.argv[4]) if len(sys.argv) > 4 else None
                data = engine.gasto_por_categoria(year, month)
            elif sub_comando == 'resumen':
                year = int(sys.argv[3])
                month = int(sys.argv[4])
                data = engine.resumen_mensual(year, month)
            else:
                print(f"Comando desconocido: {sub_comando}")
                sys.exit(1)
            print_json(data)

        else:
            print(f"Comando desconocido: {comando}")
            print(__doc__)
            sys.exit(1)

    finally:
        engine.close()


if __name__ == '__main__':
    main()
