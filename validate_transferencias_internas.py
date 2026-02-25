#!/usr/bin/env python3
"""
Validación de transferencias internas.

Verifica que las transferencias entre cuentas propias estén correctamente
clasificadas como Cat1=Interna, comparando contra el CSV maestro.
"""
import csv
from collections import defaultdict
from typing import Dict, List


def load_csv(filepath: str, delimiter: str, encoding: str = 'utf-8-sig') -> List[Dict]:
    """Cargar CSV genérico."""
    records = []
    with open(filepath, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            records.append(dict(row))
    return records


def normalize_fecha(fecha: str) -> str:
    """Normalizar fecha a YYYY-MM-DD."""
    if not fecha:
        return ""
    fecha = fecha.strip()
    if '/' in fecha:
        parts = fecha.split('/')
        if len(parts) == 3:
            dia, mes, anio = parts
            return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
    return fecha


def main():
    print("\n" + "=" * 100)
    print("VALIDACIÓN DE TRANSFERENCIAS INTERNAS")
    print("=" * 100)

    # Cargar maestro
    print("\n📂 Cargando datos...")
    maestro_records = load_csv('Validación_Categorias_Finsense_04020206_5.csv', delimiter=';')
    output_records = load_csv('output/transacciones_completas.csv', delimiter=',', encoding='utf-8')

    print(f"  Maestro: {len(maestro_records):,} registros")
    print(f"  Output:  {len(output_records):,} registros")

    # Normalizar fechas en maestro
    for rec in maestro_records:
        rec['Fecha'] = normalize_fecha(rec.get('Fecha', ''))

    # Filtrar transferencias internas en cada dataset
    maestro_internas = []
    for rec in maestro_records:
        cat1 = rec.get('Cat1', '').strip()
        tipo = rec.get('Tipo', '').strip()
        if cat1 == 'Interna' or (tipo == 'TRANSFERENCIA' and cat1 == 'Interna'):
            maestro_internas.append(rec)

    output_internas = []
    for rec in output_records:
        cat1 = rec.get('cat1', '').strip()
        tipo = rec.get('tipo', '').strip()
        if cat1 == 'Interna' or (tipo == 'TRANSFERENCIA' and cat1 == 'Interna'):
            output_internas.append(rec)

    print(f"\n📊 Transferencias Internas:")
    print(f"  En maestro: {len(maestro_internas):,}")
    print(f"  En output:  {len(output_internas):,}")

    # Estadísticas por banco en maestro
    print(f"\n📊 Internas por banco (Maestro):")
    maestro_by_bank = defaultdict(int)
    for rec in maestro_internas:
        banco = rec.get('Banco', '').strip()
        maestro_by_bank[banco] += 1

    for banco in sorted(maestro_by_bank.keys()):
        count = maestro_by_bank[banco]
        print(f"  {banco:20s} {count:5d}")

    # Estadísticas por banco en output
    print(f"\n📊 Internas por banco (Output):")
    output_by_bank = defaultdict(int)
    for rec in output_internas:
        banco = rec.get('banco', '').strip()
        output_by_bank[banco] += 1

    for banco in sorted(output_by_bank.keys()):
        count = output_by_bank[banco]
        diff = count - maestro_by_bank.get(banco, 0)
        diff_str = f"({diff:+d})" if diff != 0 else ""
        print(f"  {banco:20s} {count:5d} {diff_str}")

    # Verificar Bizums (NO deben ser Interna)
    print(f"\n🔍 Verificando Bizums (NO deben ser Interna)...")
    output_bizum_como_interna = []
    for rec in output_records:
        cat1 = rec.get('cat1', '').strip()
        desc = rec.get('descripcion', '').upper()
        if cat1 == 'Interna' and 'BIZUM' in desc:
            output_bizum_como_interna.append(rec)

    if output_bizum_como_interna:
        print(f"  ⚠️  {len(output_bizum_como_interna)} Bizums clasificados como Interna (INCORRECTO)")
        print(f"\n{'Fecha':<12} {'Importe':>10} {'Descripción':<70}")
        print("-" * 100)
        for rec in output_bizum_como_interna[:20]:
            print(f"{rec['fecha']:<12} {rec['importe']:>10} {rec['descripcion'][:70]}")
    else:
        print(f"  ✅ Ningún Bizum clasificado como Interna")

    # Analizar patrones en maestro internas
    print(f"\n📋 Patrones más frecuentes en Maestro Internas:")
    maestro_patterns = defaultdict(int)
    for rec in maestro_internas:
        desc = rec.get('Descripción', '').strip()
        # Extraer patrón (primeras 40 caracteres)
        pattern = desc[:40] if desc else "SIN DESCRIPCION"
        maestro_patterns[pattern] += 1

    for pattern, count in sorted(maestro_patterns.items(), key=lambda x: -x[1])[:30]:
        print(f"  {count:4d}x  {pattern}")

    # Falsos negativos: En maestro como Interna pero no en output
    print(f"\n🔍 Buscando FALSOS NEGATIVOS (Maestro=Interna, Output≠Interna)...")

    # Crear índice del output por fecha+importe+descripcion
    output_index = {}
    for rec in output_records:
        fecha = rec.get('fecha', '').strip()
        importe = rec.get('importe', '').strip()
        desc = rec.get('descripcion', '').strip()[:50]  # Primeros 50 chars
        banco = rec.get('banco', '').strip()
        key = f"{fecha}|{importe}|{desc}|{banco}"
        if key not in output_index:
            output_index[key] = []
        output_index[key].append(rec)

    falsos_negativos = []
    for m_rec in maestro_internas:
        fecha = m_rec.get('Fecha', '').strip()
        importe = m_rec.get('Importe', '').strip()
        desc = m_rec.get('Descripción', '').strip()[:50]
        banco = m_rec.get('Banco', '').strip()
        key = f"{fecha}|{importe}|{desc}|{banco}"

        if key in output_index:
            for o_rec in output_index[key]:
                o_cat1 = o_rec.get('cat1', '').strip()
                if o_cat1 != 'Interna':
                    falsos_negativos.append({
                        'fecha': fecha,
                        'importe': importe,
                        'descripcion': desc,
                        'banco': banco,
                        'maestro_cat1': 'Interna',
                        'output_cat1': o_cat1,
                    })
                    break

    print(f"\n  Total falsos negativos: {len(falsos_negativos)}")
    if falsos_negativos:
        print(f"\n{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Output Cat1':<20} {'Descripción':<40}")
        print("-" * 100)
        for fn in falsos_negativos[:50]:
            print(f"{fn['fecha']:<12} {fn['importe']:>10} {fn['banco']:<15} {fn['output_cat1']:<20} {fn['descripcion']:<40}")

    # Falsos positivos: En output como Interna pero no en maestro
    print(f"\n🔍 Buscando FALSOS POSITIVOS (Output=Interna, Maestro≠Interna)...")

    # Crear índice del maestro
    maestro_index = {}
    for rec in maestro_records:
        fecha = rec.get('Fecha', '').strip()
        importe = rec.get('Importe', '').strip()
        desc = rec.get('Descripción', '').strip()[:50]
        banco = rec.get('Banco', '').strip()
        key = f"{fecha}|{importe}|{desc}|{banco}"
        if key not in maestro_index:
            maestro_index[key] = []
        maestro_index[key].append(rec)

    falsos_positivos = []
    for o_rec in output_internas:
        fecha = o_rec.get('fecha', '').strip()
        importe = o_rec.get('importe', '').strip()
        desc = o_rec.get('descripcion', '').strip()[:50]
        banco = o_rec.get('banco', '').strip()
        key = f"{fecha}|{importe}|{desc}|{banco}"

        if key in maestro_index:
            for m_rec in maestro_index[key]:
                m_cat1 = m_rec.get('Cat1', '').strip()
                if m_cat1 != 'Interna':
                    falsos_positivos.append({
                        'fecha': fecha,
                        'importe': importe,
                        'descripcion': desc,
                        'banco': banco,
                        'maestro_cat1': m_cat1,
                        'output_cat1': 'Interna',
                    })
                    break

    print(f"\n  Total falsos positivos: {len(falsos_positivos)}")
    if falsos_positivos:
        print(f"\n{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Maestro Cat1':<20} {'Descripción':<40}")
        print("-" * 100)
        for fp in falsos_positivos[:50]:
            print(f"{fp['fecha']:<12} {fp['importe']:>10} {fp['banco']:<15} {fp['maestro_cat1']:<20} {fp['descripcion']:<40}")

    # Resumen final
    print(f"\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)
    print(f"Internas en maestro:     {len(maestro_internas):,}")
    print(f"Internas en output:      {len(output_internas):,}")
    print(f"Diferencia:              {len(output_internas) - len(maestro_internas):+,}")
    print()
    print(f"Falsos negativos:        {len(falsos_negativos):,} (Maestro=Interna, Output≠Interna)")
    print(f"Falsos positivos:        {len(falsos_positivos):,} (Output=Interna, Maestro≠Interna)")
    print(f"Bizums como Interna:     {len(output_bizum_como_interna):,}")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
