#!/usr/bin/env python3
"""
Test manual del pipeline completo.
"""
import os
from pipeline import TransactionPipeline

INPUT_DIR = 'input'
MASTER_CSV = 'Validación_Categorias_Finsense_04020206_5.csv'


def main():
    print("\n" + "=" * 100)
    print("TEST PIPELINE COMPLETO")
    print("=" * 100)

    # Inicializar pipeline
    print(f"\n📦 Inicializando pipeline con master CSV: {MASTER_CSV}")
    pipeline = TransactionPipeline(MASTER_CSV)

    # Test 1: Detección de banco
    print("\n🏦 Test 1: Detección de banco")
    print("-" * 100)
    test_files = [
        ('openbank_ES2200730100510135698457.csv', 'openbank'),
        ('MyInvestor_ES5215447889746650686253.csv', 'myinvestor'),
        ('mediolanum_ES2501865001680510084831.csv', 'mediolanum'),
        ('Revolut_ES1215830001199090471794.csv', 'revolut'),
        ('TradeRepublic_ES8015860001420977164411.csv', 'trade_republic'),
        ('MovimientosB100_ES88208001000130433834426.csv', 'b100'),
        ('ABANCA_ES5120800823473040166463.csv', 'abanca'),
    ]

    for filename, expected_bank in test_files:
        detected = pipeline.detect_bank(filename)
        status = "✓" if detected == expected_bank else "✗"
        print(f"  {status} {filename:60s} → {detected}")

    # Test 2: Procesar archivo individual CON clasificación
    print("\n📄 Test 2: Procesar archivo individual (Openbank) con clasificación")
    print("-" * 100)
    filepath = os.path.join(INPUT_DIR, 'openbank_ES2200730100510135698457.csv')
    records = pipeline.process_file(filepath, classify=True)

    print(f"  ✓ Parseadas: {len(records)} transacciones")

    if records:
        # Verificar campos
        r = records[0]
        campos_requeridos = ['fecha', 'importe', 'descripcion', 'banco', 'cuenta', 'hash',
                            'cat1', 'cat2', 'tipo', 'capa']
        print(f"\n  Campos en transacción:")
        for campo in campos_requeridos:
            presente = "✓" if campo in r else "✗"
            valor = r.get(campo, 'MISSING')
            print(f"    {presente} {campo:15s} → {valor}")

        # Estadísticas de clasificación
        capas = {}
        categorias = {}
        tipos = {}
        for r in records:
            capa = r.get('capa', 0)
            capas[f'Capa {capa}'] = capas.get(f'Capa {capa}', 0) + 1

            cat1 = r.get('cat1', 'MISSING')
            categorias[cat1] = categorias.get(cat1, 0) + 1

            tipo = r.get('tipo', 'MISSING')
            tipos[tipo] = tipos.get(tipo, 0) + 1

        print(f"\n  📊 Distribución por capa de clasificación:")
        for capa, count in sorted(capas.items()):
            pct = 100 * count / len(records)
            print(f"    {capa}: {count:3d} ({pct:5.1f}%)")

        print(f"\n  📂 Categorías (Top 5):")
        top_cats = sorted(categorias.items(), key=lambda x: -x[1])[:5]
        for cat, count in top_cats:
            pct = 100 * count / len(records)
            print(f"    {cat:30s} {count:3d} ({pct:5.1f}%)")

        print(f"\n  🎯 Tipos de transacción:")
        for tipo, count in sorted(tipos.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(records)
            print(f"    {tipo:20s} {count:3d} ({pct:5.1f}%)")

    # Test 3: Deduplicación
    print("\n🔄 Test 3: Deduplicación (procesar mismo archivo dos veces)")
    print("-" * 100)

    # Reset pipeline para test limpio
    pipeline2 = TransactionPipeline(MASTER_CSV)

    records1 = pipeline2.process_file(filepath, classify=False)
    print(f"  Primera pasada:  {len(records1)} transacciones nuevas")

    records2 = pipeline2.process_file(filepath, classify=False)
    print(f"  Segunda pasada:  {len(records2)} transacciones nuevas")

    if len(records2) == 0 and len(records1) > 0:
        print(f"  ✓ Deduplicación funciona correctamente")
    else:
        print(f"  ✗ ERROR: Deduplicación no funciona")

    # Test 4: Procesar directorio completo
    print("\n📁 Test 4: Procesar directorio completo CON clasificación")
    print("-" * 100)

    # Reset pipeline
    pipeline3 = TransactionPipeline(MASTER_CSV)

    all_records = pipeline3.process_directory(INPUT_DIR, classify=True)

    print(f"\n  📊 Resumen global:")
    print(f"    Total transacciones: {len(all_records)}")

    if all_records:
        # Por banco
        by_bank = {}
        for r in all_records:
            banco = r['banco']
            by_bank[banco] = by_bank.get(banco, 0) + 1

        print(f"\n    Por banco:")
        for banco, count in sorted(by_bank.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(all_records)
            print(f"      {banco:20s} {count:5d} ({pct:5.1f}%)")

        # Cobertura de clasificación
        sin_clasificar = sum(1 for r in all_records if r.get('cat1') == 'SIN_CLASIFICAR')
        clasificadas = len(all_records) - sin_clasificar
        pct_clasificadas = 100 * clasificadas / len(all_records) if all_records else 0

        print(f"\n    Cobertura de clasificación:")
        print(f"      Clasificadas:     {clasificadas:5d} ({pct_clasificadas:5.1f}%)")
        print(f"      Sin clasificar:   {sin_clasificar:5d} ({100-pct_clasificadas:5.1f}%)")

        if sin_clasificar == 0:
            print(f"\n    ✅ ¡Todas las transacciones clasificadas!")
        else:
            print(f"\n    ⚠️  {sin_clasificar} transacciones sin clasificar")

    # Test 5: Estadísticas completas
    print("\n📈 Test 5: Estadísticas completas")
    print("-" * 100)

    pipeline3.print_statistics(all_records)

    print("\n" + "=" * 100)
    print("✅ Tests del pipeline completados")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
