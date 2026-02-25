#!/usr/bin/env python3
"""
Script para REPROCESAR todas las transacciones en la BBDD.
Aplica las reglas actualizadas del clasificador a TODAS las transacciones.

IMPORTANTE: Lee REGLAS_PROYECTO.md antes de usar este script.
"""
import sqlite3
from classifier import Classifier
from classifier.engine import determine_tipo
from classifier.normalization import normalize_description

def main():
    # Conectar a la BBDD
    conn = sqlite3.connect('finsense.db')
    cursor = conn.cursor()

    # Inicializar clasificador
    print("🔧 Inicializando clasificador...")
    classifier = Classifier('validate/Validacion_Categorias_Finsense_MASTER_v9.csv')

    # Leer TODAS las transacciones
    print("\n📖 Leyendo transacciones de la BBDD...")
    cursor.execute("""
        SELECT id, descripcion, banco, importe, fecha, tipo, cat1, cat2
        FROM transacciones
        ORDER BY id
    """)

    transactions = cursor.fetchall()
    total = len(transactions)
    print(f"   Total: {total:,} transacciones\n")

    # Contadores
    cambios = {
        'tipo': 0,
        'cat1': 0,
        'cat2': 0,
        'total': 0
    }

    cambios_detalle = []

    # Reprocesar cada transacción
    print("🔄 Reclasificando transacciones...")
    print("─" * 80)

    for i, (tx_id, descripcion, banco, importe, fecha, tipo_old, cat1_old, cat2_old) in enumerate(transactions, 1):
        # Mostrar progreso cada 1000 transacciones
        if i % 1000 == 0:
            print(f"   Procesadas: {i:,}/{total:,} ({100*i/total:.1f}%)")

        # Normalizar descripción
        descripcion_normalizada = normalize_description(descripcion or "")

        # (BUGFIX Openbank) Para Openbank, pasar siempre la descripción ORIGINAL al clasificador para que funcione la extracción de merchant y patrón 'COMPRA EN'
        if banco == "Openbank":
            descripcion_clasificador = descripcion
        else:
            descripcion_clasificador = descripcion_normalizada

        # Clasificar
        result = classifier.classify(
            descripcion=descripcion_clasificador,
            banco=banco,
            importe=importe,
            fecha=fecha
        )

        tipo_new = result['tipo']
        cat1_new = result['cat1']
        cat2_new = result['cat2']

        # Comparar con clasificación antigua
        cambio = False
        if tipo_new != tipo_old:
            cambios['tipo'] += 1
            cambio = True
        if cat1_new != cat1_old:
            cambios['cat1'] += 1
            cambio = True
        if cat2_new != (cat2_old or ''):
            cambios['cat2'] += 1
            cambio = True

        if cambio:
            cambios['total'] += 1

            # Guardar detalles de cambios importantes
            if len(cambios_detalle) < 50:  # Guardar primeros 50 cambios para mostrar
                cambios_detalle.append({
                    'id': tx_id,
                    'fecha': fecha,
                    'importe': importe,
                    'descripcion': descripcion[:60],
                    'banco': banco,
                    'old': f"{tipo_old}/{cat1_old}/{cat2_old or ''}",
                    'new': f"{tipo_new}/{cat1_new}/{cat2_new}"
                })

            # Actualizar en BBDD
            cursor.execute("""
                UPDATE transacciones
                SET tipo = ?, cat1 = ?, cat2 = ?
                WHERE id = ?
            """, (tipo_new, cat1_new, cat2_new, tx_id))

    # Commit cambios
    conn.commit()

    print("─" * 80)
    print(f"\n✅ Reprocesamiento completado!\n")

    # Reportar estadísticas
    print("=" * 80)
    print("📊 RESUMEN DE CAMBIOS")
    print("=" * 80)
    print(f"\n📝 Transacciones procesadas: {total:,}")
    print(f"🔄 Transacciones modificadas: {cambios['total']:,} ({100*cambios['total']/total:.2f}%)")
    print(f"\n   • Cambios en Tipo:  {cambios['tipo']:,}")
    print(f"   • Cambios en Cat1:  {cambios['cat1']:,}")
    print(f"   • Cambios en Cat2:  {cambios['cat2']:,}")

    if cambios_detalle:
        print(f"\n📋 PRIMEROS {len(cambios_detalle)} CAMBIOS:")
        print("─" * 80)
        for c in cambios_detalle:
            print(f"{c['fecha']} | {c['importe']:>9.2f} | {c['banco']:15s} | {c['descripcion']}")
            print(f"   ANTES: {c['old']:30s} → DESPUÉS: {c['new']}")
            print()

    # Verificar reglas específicas
    print("=" * 80)
    print("🔍 VERIFICACIÓN DE REGLAS ESPECÍFICAS")
    print("=" * 80)

    # REGLA 1: B100 Health/Save/Traspaso
    cursor.execute("""
        SELECT COUNT(*), tipo, cat1
        FROM transacciones
        WHERE banco = 'B100'
          AND (descripcion LIKE '%Health%'
               OR descripcion LIKE '%Save%'
               OR descripcion LIKE '%Traspaso%'
               OR descripcion LIKE '%AHORRO PARA HUCHA%'
               OR descripcion LIKE '%Move to save%')
        GROUP BY tipo, cat1
        ORDER BY COUNT(*) DESC
    """)

    print("\n1️⃣  REGLA B100 (Health/Save/Traspaso → TRANSFERENCIA/Interna):")
    b100_results = cursor.fetchall()
    for count, tipo, cat1 in b100_results:
        icono = "✅" if (tipo == "TRANSFERENCIA" and cat1 == "Interna") else "❌"
        print(f"   {icono} {count:4d} transacciones → {tipo}/{cat1}")

    # REGLA 2: Amazon/refunds con importe positivo
    cursor.execute("""
        SELECT COUNT(*), tipo, cat1, cat2
        FROM transacciones
        WHERE importe > 0
          AND (descripcion LIKE '%Amazon%'
               OR descripcion LIKE '%AMZN%'
               OR descripcion LIKE '%devolución%'
               OR descripcion LIKE '%reembolso%'
               OR descripcion LIKE '%refund%')
        GROUP BY tipo, cat1, cat2
        ORDER BY COUNT(*) DESC
    """)

    print("\n2️⃣  REGLA Amazon/Refunds (importe+ → GASTO con importe positivo):")
    amazon_results = cursor.fetchall()
    for count, tipo, cat1, cat2 in amazon_results:
        # Para Amazon, debería ser GASTO (ya que es devolución)
        # Para otras devoluciones genéricas, podría ser INGRESO/Devoluciones
        if 'Amazon' in (cat2 or ''):
            icono = "✅" if tipo == "GASTO" else "❌"
        elif cat1 == "Devoluciones":
            icono = "✅" if tipo == "INGRESO" else "❌"
        else:
            icono = "⚠️"
        print(f"   {icono} {count:4d} transacciones → {tipo}/{cat1}/{cat2 or ''}")

    # REGLA 3: Importes positivos con Cat1 de gasto
    cursor.execute("""
        SELECT COUNT(*)
        FROM transacciones
        WHERE importe > 0
          AND tipo = 'GASTO'
          AND cat1 IN ('Compras', 'Alimentación', 'Restauración', 'Transporte',
                       'Vivienda', 'Salud y Belleza', 'Ocio y Cultura', 'Ropa y Calzado',
                       'Educación', 'Recibos', 'Finanzas', 'Suscripciones', 'Tecnología',
                       'Mascotas', 'Hogar', 'Deporte', 'Otros')
    """)

    count_refunds = cursor.fetchone()[0]
    print(f"\n3️⃣  REGLA Devoluciones generales (importe+ con Cat1 de gasto → GASTO):")
    print(f"   ✅ {count_refunds:4d} transacciones clasificadas como GASTO positivo (devoluciones)")

    print("\n" + "=" * 80)
    print("✅ Reprocesamiento completado exitosamente")
    print("=" * 80 + "\n")

    conn.close()

if __name__ == '__main__':
    main()
