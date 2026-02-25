#!/usr/bin/env python3
"""
Diagnóstico detallado de las 1,150 transacciones no matched.

Clasifica por causa raíz:
a) Solo en maestro → Parser no las leyó
b) Solo en output → Parser generó fantasmas
c) En ambos pero no matchean → Diferencias en encoding/formato
"""
import csv
from collections import defaultdict
from typing import Dict, List, Tuple
import re


def load_maestro(filepath: str) -> List[Dict]:
    """Cargar CSV maestro."""
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            fecha = row.get('Fecha', '').strip()

            # Normalizar fecha DD/MM/YYYY → YYYY-MM-DD
            if fecha and '/' in fecha:
                parts = fecha.split('/')
                if len(parts) == 3:
                    dia, mes, anio = parts
                    fecha = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"

            record = {
                'fecha': fecha,
                'importe': row.get('Importe', '').strip(),
                'descripcion': row.get('Descripción', '').strip(),
                'banco': row.get('Banco', '').strip(),
                'cuenta': row.get('Cuenta', '').strip(),
                'tipo': row.get('Tipo', '').strip(),
                'cat1': row.get('Cat1', '').strip(),
                'cat2': row.get('Cat2', '').strip(),
            }
            records.append(record)
    return records


def load_output(filepath: str) -> List[Dict]:
    """Cargar CSV de output."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            record = {
                'fecha': row.get('fecha', '').strip(),
                'importe': row.get('importe', '').strip(),
                'descripcion': row.get('descripcion', '').strip(),
                'banco': row.get('banco', '').strip(),
                'cuenta': row.get('cuenta', '').strip(),
                'tipo': row.get('tipo', '').strip(),
                'cat1': row.get('cat1', '').strip(),
                'cat2': row.get('cat2', '').strip(),
                'source_file': row.get('source_file', '').strip(),
            }
            records.append(record)
    return records


def normalize_number(s: str) -> float:
    """Convertir string a float, manejando diferentes formatos."""
    if not s:
        return 0.0
    # Eliminar espacios y comillas
    s = s.strip().replace(' ', '').replace('"', '')
    # Si tiene punto Y coma: formato internacional (coma=separador de miles, punto=decimal)
    # Ejemplo: "17,305.00" → 17305.0
    if '.' in s and ',' in s:
        s = s.replace(',', '')  # Eliminar separador de miles
    # Si solo tiene coma: formato europeo (coma=decimal)
    # Ejemplo: "1234,56" → 1234.56
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


def normalize_cuenta(cuenta: str) -> str:
    """Normalizar cuenta a últimos 4 dígitos."""
    if not cuenta:
        return ""
    digits = ''.join(c for c in cuenta if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits


def create_key(record: Dict) -> str:
    """Crear clave única para matching."""
    try:
        importe = normalize_number(record['importe'])
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{importe:.2f}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"
    except:
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{record['importe']}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"


def create_partial_key(record: Dict) -> str:
    """Crear clave parcial (fecha + importe) para buscar candidatos."""
    try:
        importe = normalize_number(record['importe'])
        return f"{record['fecha']}|{importe:.2f}"
    except:
        return f"{record['fecha']}|{record['importe']}"


def has_encoding_issues(text: str) -> bool:
    """Detectar problemas de encoding comunes."""
    # Patrones de encoding roto: Ã³ → ó, Ã± → ñ, etc.
    bad_patterns = ['Ã', '¿', 'â', '€', 'º', 'ª']
    return any(pattern in text for pattern in bad_patterns)


def normalize_whitespace(text: str) -> str:
    """Normalizar espacios en blanco."""
    return re.sub(r'\s+', ' ', text).strip()


def detect_difference_type(m_rec: Dict, o_rec: Dict) -> str:
    """Detectar tipo de diferencia entre maestro y output."""
    differences = []

    # Comparar descripción
    m_desc = m_rec['descripcion']
    o_desc = o_rec['descripcion']

    if m_desc != o_desc:
        # Encoding
        if has_encoding_issues(o_desc) or has_encoding_issues(m_desc):
            differences.append('ENCODING')

        # Whitespace
        if normalize_whitespace(m_desc) == normalize_whitespace(o_desc):
            differences.append('WHITESPACE')

        # Truncamiento
        if m_desc.startswith(o_desc) or o_desc.startswith(m_desc):
            differences.append('TRUNCAMIENTO')

        if not differences:
            differences.append('DESC_DIFERENTE')

    # Comparar banco
    if m_rec['banco'] != o_rec['banco']:
        differences.append('BANCO')

    # Comparar cuenta
    m_cuenta_norm = normalize_cuenta(m_rec['cuenta'])
    o_cuenta_norm = normalize_cuenta(o_rec['cuenta'])
    if m_cuenta_norm != o_cuenta_norm:
        differences.append('CUENTA')

    # Comparar fecha
    if m_rec['fecha'] != o_rec['fecha']:
        differences.append('FECHA')

    # Comparar importe
    try:
        m_imp = normalize_number(m_rec['importe'])
        o_imp = normalize_number(o_rec['importe'])
        if abs(m_imp - o_imp) > 0.01:
            differences.append('IMPORTE')
    except:
        differences.append('IMPORTE_FORMATO')

    return ','.join(differences) if differences else 'DESCONOCIDO'


def main():
    print("\n" + "=" * 120)
    print("DIAGNÓSTICO DETALLADO DE TRANSACCIONES NO MATCHED")
    print("=" * 120)

    # Cargar datos
    print("\n📂 Cargando datos...")
    maestro_records = load_maestro('Validación_Categorias_Finsense_04020206_5.csv')
    output_records = load_output('output/transacciones_completas.csv')

    print(f"  Maestro: {len(maestro_records):,} registros")
    print(f"  Output:  {len(output_records):,} registros")

    # Crear índices
    print("\n📊 Creando índices...")
    maestro_index = {}
    for i, rec in enumerate(maestro_records):
        key = create_key(rec)
        if key not in maestro_index:
            maestro_index[key] = []
        maestro_index[key].append((i, rec))

    output_index = {}
    for i, rec in enumerate(output_records):
        key = create_key(rec)
        if key not in output_index:
            output_index[key] = []
        output_index[key].append((i, rec))

    # Crear índices parciales (fecha + importe)
    maestro_partial_index = {}
    for i, rec in enumerate(maestro_records):
        pkey = create_partial_key(rec)
        if pkey not in maestro_partial_index:
            maestro_partial_index[pkey] = []
        maestro_partial_index[pkey].append((i, rec))

    output_partial_index = {}
    for i, rec in enumerate(output_records):
        pkey = create_partial_key(rec)
        if pkey not in output_partial_index:
            output_partial_index[pkey] = []
        output_partial_index[pkey].append((i, rec))

    # Identificar matches
    matches = sum(len(v) for k, v in maestro_index.items() if k in output_index)

    print(f"  Matches exactos: {matches:,}")

    # CATEGORÍA A: Solo en maestro (parser no leyó)
    print("\n" + "=" * 120)
    print("CATEGORÍA A: SOLO EN MAESTRO (Parser no las leyó)")
    print("=" * 120)

    solo_maestro = []
    for key, maestro_list in maestro_index.items():
        if key not in output_index:
            for idx, rec in maestro_list:
                solo_maestro.append(rec)

    print(f"\nTotal: {len(solo_maestro):,} registros")

    # Agrupar por banco
    by_banco = defaultdict(int)
    for rec in solo_maestro:
        by_banco[rec['banco']] += 1

    print(f"\nPor banco:")
    for banco in sorted(by_banco.keys(), key=lambda x: -by_banco[x]):
        print(f"  {banco:20s} {by_banco[banco]:5d}")

    # Primeras 30
    print(f"\nPrimeras 30:")
    print(f"{'Fecha':<12} {'Importe':>12} {'Banco':<15} {'Cuenta':<10} {'Descripción':<60}")
    print("-" * 120)
    for rec in solo_maestro[:30]:
        print(f"{rec['fecha']:<12} {rec['importe']:>12} {rec['banco']:<15} {rec['cuenta']:<10} {rec['descripcion'][:60]}")

    # CATEGORÍA B: Solo en output (fantasmas)
    print("\n" + "=" * 120)
    print("CATEGORÍA B: SOLO EN OUTPUT (Parser generó fantasmas)")
    print("=" * 120)

    solo_output = []
    for key, output_list in output_index.items():
        if key not in maestro_index:
            for idx, rec in output_list:
                solo_output.append(rec)

    print(f"\nTotal: {len(solo_output):,} registros")

    # Agrupar por banco
    by_banco = defaultdict(int)
    for rec in solo_output:
        by_banco[rec['banco']] += 1

    print(f"\nPor banco:")
    for banco in sorted(by_banco.keys(), key=lambda x: -by_banco[x]):
        print(f"  {banco:20s} {by_banco[banco]:5d}")

    # Primeras 30
    print(f"\nPrimeras 30:")
    print(f"{'Fecha':<12} {'Importe':>12} {'Banco':<15} {'Source':<30} {'Descripción':<60}")
    print("-" * 120)
    for rec in solo_output[:30]:
        print(f"{rec['fecha']:<12} {rec['importe']:>12} {rec['banco']:<15} {rec['source_file'][-30:]:<30} {rec['descripcion'][:60]}")

    # CATEGORÍA C: En ambos pero no matchean (buscar candidatos)
    print("\n" + "=" * 120)
    print("CATEGORÍA C: POSIBLES MATCHES CON DIFERENCIAS (Encoding/Formato)")
    print("=" * 120)

    print("\nBuscando candidatos por fecha+importe...")

    candidatos = []

    # Para cada registro solo_maestro, buscar candidatos en solo_output por fecha+importe
    for m_rec in solo_maestro:
        pkey = create_partial_key(m_rec)
        if pkey in output_partial_index:
            for o_idx, o_rec in output_partial_index[pkey]:
                # Verificar que este output_rec también está en solo_output
                o_key = create_key(o_rec)
                if o_key not in maestro_index:
                    # Candidato encontrado
                    diff_type = detect_difference_type(m_rec, o_rec)
                    candidatos.append({
                        'm_rec': m_rec,
                        'o_rec': o_rec,
                        'diff_type': diff_type,
                    })

    print(f"\nCandidatos encontrados: {len(candidatos):,}")

    # Agrupar por tipo de diferencia
    by_diff_type = defaultdict(int)
    for cand in candidatos:
        by_diff_type[cand['diff_type']] += 1

    print(f"\nPor tipo de diferencia:")
    for diff_type in sorted(by_diff_type.keys(), key=lambda x: -by_diff_type[x]):
        print(f"  {diff_type:40s} {by_diff_type[diff_type]:5d}")

    # Mostrar ejemplos de cada tipo
    print("\n" + "=" * 120)
    print("EJEMPLOS POR TIPO DE DIFERENCIA")
    print("=" * 120)

    for diff_type in sorted(by_diff_type.keys(), key=lambda x: -by_diff_type[x])[:10]:
        print(f"\n{diff_type} ({by_diff_type[diff_type]} casos) - Primeros 5:")
        print("-" * 120)

        examples = [c for c in candidatos if c['diff_type'] == diff_type][:5]
        for cand in examples:
            m_rec = cand['m_rec']
            o_rec = cand['o_rec']
            print(f"Maestro: {m_rec['fecha']} | {m_rec['importe']:>10} | {m_rec['banco']:15s} | {m_rec['descripcion'][:60]}")
            print(f"Output:  {o_rec['fecha']} | {o_rec['importe']:>10} | {o_rec['banco']:15s} | {o_rec['descripcion'][:60]}")
            print()

    # Resumen final
    print("\n" + "=" * 120)
    print("RESUMEN FINAL")
    print("=" * 120)
    print(f"Total registros maestro:           {len(maestro_records):,}")
    print(f"Total registros output:            {len(output_records):,}")
    print(f"Matches exactos:                   {matches:,}")
    print()
    print(f"A) Solo en maestro (no leídos):    {len(solo_maestro):,}")
    print(f"B) Solo en output (fantasmas):     {len(solo_output):,}")
    print(f"C) Candidatos con diferencias:     {len(candidatos):,}")
    print()
    print(f"Total no-matched (A + B):          {len(solo_maestro) + len(solo_output):,}")
    print(f"Match rate:                        {100 * matches / len(maestro_records):.1f}%")
    print("=" * 120 + "\n")

    # Guardar listas completas en archivos
    print("💾 Guardando listas completas...")

    with open('diagnostico_solo_maestro.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fecha', 'importe', 'descripcion', 'banco', 'cuenta', 'cat1', 'cat2', 'tipo'])
        writer.writeheader()
        writer.writerows(solo_maestro)
    print(f"  ✓ diagnostico_solo_maestro.csv ({len(solo_maestro):,} registros)")

    with open('diagnostico_solo_output.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fecha', 'importe', 'descripcion', 'banco', 'cuenta', 'cat1', 'cat2', 'tipo', 'source_file'])
        writer.writeheader()
        writer.writerows(solo_output)
    print(f"  ✓ diagnostico_solo_output.csv ({len(solo_output):,} registros)")

    with open('diagnostico_candidatos.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['diff_type', 'm_fecha', 'm_importe', 'm_descripcion', 'm_banco', 'm_cuenta',
                        'o_fecha', 'o_importe', 'o_descripcion', 'o_banco', 'o_cuenta'])
        for cand in candidatos:
            m = cand['m_rec']
            o = cand['o_rec']
            writer.writerow([
                cand['diff_type'],
                m['fecha'], m['importe'], m['descripcion'], m['banco'], m['cuenta'],
                o['fecha'], o['importe'], o['descripcion'], o['banco'], o['cuenta']
            ])
    print(f"  ✓ diagnostico_candidatos.csv ({len(candidatos):,} registros)")
    print()


if __name__ == '__main__':
    main()
