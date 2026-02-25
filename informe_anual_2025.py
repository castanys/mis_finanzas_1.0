#!/usr/bin/env python3
"""
Informe anual 2025: ingresos, gastos, ahorro, tasa, top categorías,
evolución mensual y comparativa FIRE.
"""
import sqlite3
from collections import defaultdict

def format_eur(amount):
    """Formatea cantidad como euros"""
    return f"€{amount:,.2f}".replace(',', '.')

def main():
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    print("=" * 80)
    print("INFORME ANUAL 2025")
    print("=" * 80)

    # === 1. TOTALES ANUALES ===
    cursor.execute("""
        SELECT tipo, SUM(importe)
        FROM transacciones
        WHERE strftime('%Y', fecha) = '2025'
          AND tipo IN ('INGRESO', 'GASTO')
        GROUP BY tipo
    """)

    totales = {}
    for tipo, total in cursor.fetchall():
        totales[tipo] = total

    ingresos = abs(totales.get('INGRESO', 0))
    gastos = abs(totales.get('GASTO', 0))
    ahorro = ingresos - gastos
    tasa_ahorro = (ahorro / ingresos * 100) if ingresos > 0 else 0

    print(f"\n📊 RESUMEN FINANCIERO 2025")
    print("─" * 80)
    print(f"{'Ingresos totales:':25s} {format_eur(ingresos):>20s}")
    print(f"{'Gastos totales:':25s} {format_eur(gastos):>20s}")
    print(f"{'Ahorro neto:':25s} {format_eur(ahorro):>20s}")
    print(f"{'Tasa de ahorro:':25s} {tasa_ahorro:>19.1f}%")

    # === 2. TOP CATEGORÍAS DE GASTO ===
    print(f"\n💸 TOP 10 CATEGORÍAS DE GASTO")
    print("─" * 80)

    cursor.execute("""
        SELECT cat1, SUM(importe) as total
        FROM transacciones
        WHERE strftime('%Y', fecha) = '2025'
          AND tipo = 'GASTO'
        GROUP BY cat1
        ORDER BY total ASC
        LIMIT 10
    """)

    print(f"{'#':>3s} {'CATEGORÍA':30s} {'IMPORTE':>15s} {'% DEL GASTO':>12s}")
    print("─" * 80)

    for i, (cat1, total) in enumerate(cursor.fetchall(), 1):
        pct = (abs(total) / gastos * 100) if gastos > 0 else 0
        print(f"{i:>3d}. {cat1:28s} {format_eur(abs(total)):>15s} {pct:>11.1f}%")

    # === 3. EVOLUCIÓN MENSUAL ===
    print(f"\n📈 EVOLUCIÓN MENSUAL 2025")
    print("─" * 80)

    cursor.execute("""
        SELECT strftime('%m', fecha) as mes, tipo, SUM(importe)
        FROM transacciones
        WHERE strftime('%Y', fecha) = '2025'
          AND tipo IN ('INGRESO', 'GASTO')
        GROUP BY mes, tipo
        ORDER BY mes
    """)

    # Organizar por mes
    meses_data = defaultdict(dict)
    for mes, tipo, total in cursor.fetchall():
        meses_data[mes][tipo] = abs(total)

    print(f"{'MES':>4s} {'INGRESOS':>12s} {'GASTOS':>12s} {'AHORRO':>12s} {'TASA':>8s}")
    print("─" * 80)

    meses_nombres = {
        '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
        '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
        '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }

    ahorro_acumulado = 0
    for mes in sorted(meses_data.keys()):
        data = meses_data[mes]
        ing = data.get('INGRESO', 0)
        gast = data.get('GASTO', 0)
        ahor = ing - gast
        tasa = (ahor / ing * 100) if ing > 0 else 0

        ahorro_acumulado += ahor

        print(f"{meses_nombres[mes]:>4s} {format_eur(ing):>12s} {format_eur(gast):>12s} "
              f"{format_eur(ahor):>12s} {tasa:>7.1f}%")

    print("─" * 80)
    print(f"{'TOTAL':>4s} {format_eur(ingresos):>12s} {format_eur(gastos):>12s} "
          f"{format_eur(ahorro):>12s} {tasa_ahorro:>7.1f}%")

    # === 4. MÉTRICAS FIRE ===
    print(f"\n🔥 COMPARATIVA FIRE (Financial Independence, Retire Early)")
    print("─" * 80)

    gastos_mensuales = gastos / 12
    fondo_emergencia = gastos_mensuales * 6

    # Calcular años para FIRE (asumiendo 4% withdrawal rate)
    # FIRE number = gastos anuales * 25
    fire_number = gastos * 25
    años_para_fire = fire_number / ahorro if ahorro > 0 else float('inf')

    print(f"{'Gastos mensuales promedio:':35s} {format_eur(gastos_mensuales):>20s}")
    print(f"{'Fondo emergencia (6 meses):':35s} {format_eur(fondo_emergencia):>20s}")
    print(f"{'FIRE Number (gastos × 25):':35s} {format_eur(fire_number):>20s}")

    if años_para_fire < 100:
        print(f"{'Años para FIRE (ritmo actual):':35s} {años_para_fire:>19.1f} años")
    else:
        print(f"{'Años para FIRE (ritmo actual):':35s} {'> 100 años':>20s}")

    # Tasa de ahorro recomendada FIRE
    tasas_fire = {
        'FIRE Agresivo (70%)': 70,
        'FIRE Estándar (50%)': 50,
        'FIRE Moderado (30%)': 30,
    }

    print(f"\n{'Tasas de ahorro FIRE recomendadas:':35s} {'TU TASA':>20s}")
    print("─" * 80)

    for label, tasa in tasas_fire.items():
        status = "✓" if tasa_ahorro >= tasa else "✗"
        print(f"{status} {label:33s} {tasa:>6.1f}% vs {tasa_ahorro:>6.1f}%")

    # === 5. ANÁLISIS DE PATRONES ===
    print(f"\n🔍 ANÁLISIS DE PATRONES")
    print("─" * 80)

    # Top merchants por gasto
    cursor.execute("""
        SELECT descripcion, COUNT(*) as freq, SUM(importe) as total
        FROM transacciones
        WHERE strftime('%Y', fecha) = '2025'
          AND tipo = 'GASTO'
        GROUP BY descripcion
        ORDER BY total ASC
        LIMIT 10
    """)

    print(f"\nTop 10 Merchants más caros:")
    for i, (desc, freq, total) in enumerate(cursor.fetchall(), 1):
        print(f"  {i:2d}. {desc[:50]:50s} {format_eur(abs(total)):>12s} ({freq} tx)")

    # Distribución por banco
    cursor.execute("""
        SELECT banco, COUNT(*) as freq, SUM(CASE WHEN tipo='GASTO' THEN importe ELSE 0 END) as gasto
        FROM transacciones
        WHERE strftime('%Y', fecha) = '2025'
        GROUP BY banco
        ORDER BY gasto ASC
    """)

    print(f"\nDistribución de gastos por banco:")
    for banco, freq, gasto_banco in cursor.fetchall():
        if gasto_banco != 0:
            pct = (abs(gasto_banco) / gastos * 100) if gastos > 0 else 0
            print(f"  • {banco:10s}: {format_eur(abs(gasto_banco)):>12s} ({pct:>5.1f}%) - {freq} transacciones")

    print("\n" + "=" * 80)
    print("FIN DEL INFORME")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
