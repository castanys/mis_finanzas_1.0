#!/usr/bin/env python3
"""
Validación cruzada contra CSV maestro - VERSIÓN 2 con matching flexible.

Mejoras:
- Matching en 2 fases: fecha+importe+banco+cuenta, luego validar descripción similar
- Normalización de descripciones (eliminar prefijos, números tarjeta, fix encoding)
- Tolerancia a diferencias menores entre maestro normalizado y output
"""
import csv
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


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
    if '.' in s and ',' in s:
        s = s.replace(',', '')
    # Si solo tiene coma: formato europeo (coma=decimal)
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


def normalize_cuenta(cuenta: str) -> str:
    """Normalizar cuenta a últimos 4 dígitos."""
    if not cuenta:
        return ""
    digits = ''.join(c for c in cuenta if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits


def fix_encoding(text: str) -> str:
    """Fix encoding común (UTF-8 mal interpretado)."""
    replacements = {
        'Ã³': 'ó',
        'Ã±': 'ñ',
        'Ã¡': 'á',
        'Ã©': 'é',
        'Ã­': 'í',
        'Ãº': 'ú',
        'Ã': 'ñ',  # Genérico
        'NÂº': 'Nº',
        'nÂº': 'nº',
        '�': 'ñ',  # Otro encoding roto común
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def normalize_descripcion(desc: str) -> str:
    """
    Normalizar descripción para matching flexible.

    - Elimina prefijos comunes (Transferencia, Otros)
    - Reemplaza números largos (tarjetas) con XXXX
    - Fix encoding
    - Normaliza espacios
    """
    if not desc:
        return ""

    # Fix encoding
    desc = fix_encoding(desc)

    # Eliminar prefijos comunes al inicio
    prefixes = [
        'Transferencia ',
        'Otros ',
        'Ingreso ',
        'Pago ',
        'Compra ',
    ]
    for prefix in prefixes:
        if desc.startswith(prefix):
            desc = desc[len(prefix):]
            break

    # Reemplazar números largos (12+ dígitos) con XXXX (números de tarjeta)
    desc = re.sub(r'\d{12,}', 'XXXX', desc)

    # Normalizar espacios múltiples
    desc = re.sub(r'\s+', ' ', desc).strip()

    # Lowercase para comparación
    desc = desc.lower()

    return desc


def descripcion_similarity(desc1: str, desc2: str) -> float:
    """
    Calcular similitud entre dos descripciones (0.0 a 1.0).

    Usa distancia de Levenshtein simplificada (caracteres comunes).
    """
    d1 = normalize_descripcion(desc1)
    d2 = normalize_descripcion(desc2)

    if not d1 or not d2:
        return 0.0

    if d1 == d2:
        return 1.0

    # Similitud basada en caracteres comunes
    # Contar cuántos caracteres consecutivos coinciden
    max_len = max(len(d1), len(d2))
    min_len = min(len(d1), len(d2))

    # Si una contiene a la otra (substring), alta similitud
    if d1 in d2 or d2 in d1:
        return min_len / max_len

    # Calcular overlap simple (caracteres en común)
    common = 0
    for i in range(min_len):
        if d1[i] == d2[i]:
            common += 1
        else:
            break

    # Agregar caracteres comunes del final
    for i in range(1, min_len - common + 1):
        if d1[-i] == d2[-i]:
            common += 1
        else:
            break

    return common / max_len


def create_key_exact(record: Dict) -> str:
    """Crear clave exacta para matching (incluye descripción completa)."""
    try:
        importe = normalize_number(record['importe'])
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{importe:.2f}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"
    except:
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{record['importe']}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"


def create_key_base(record: Dict) -> str:
    """Crear clave base para matching flexible (sin descripción)."""
    try:
        importe = normalize_number(record['importe'])
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{importe:.2f}|{record['banco']}|{cuenta_norm}"
    except:
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{record['importe']}|{record['banco']}|{cuenta_norm}"


def main():
    print("\n" + "=" * 100)
    print("VALIDACIÓN CRUZADA CONTRA CSV MAESTRO - V2 (Matching Flexible)")
    print("=" * 100)

    # Cargar datos
    print("\n📂 Cargando datos...")
    maestro_records = load_maestro('Validación_Categorias_Finsense_04020206_5.csv')
    output_records = load_output('output/transacciones_completas.csv')

    print(f"  Registros en maestro: {len(maestro_records):,}")
    print(f"  Registros en output:  {len(output_records):,}")

    # FASE 1: Matching exacto
    print("\n" + "=" * 100)
    print("FASE 1: MATCHING EXACTO")
    print("=" * 100)

    maestro_exact_index = {}
    for i, rec in enumerate(maestro_records):
        key = create_key_exact(rec)
        if key not in maestro_exact_index:
            maestro_exact_index[key] = []
        maestro_exact_index[key].append((i, rec))

    output_exact_index = {}
    for i, rec in enumerate(output_records):
        key = create_key_exact(rec)
        if key not in output_exact_index:
            output_exact_index[key] = []
        output_exact_index[key].append((i, rec))

    exact_matches = sum(len(v) for k, v in maestro_exact_index.items() if k in output_exact_index)
    print(f"  Matches exactos: {exact_matches:,}")

    # FASE 2: Matching flexible (para los que no matchearon exacto)
    print("\n" + "=" * 100)
    print("FASE 2: MATCHING FLEXIBLE (fecha+importe+banco+cuenta + descripción similar)")
    print("=" * 100)

    # Crear índice base (sin descripción)
    maestro_base_index = {}
    for i, rec in enumerate(maestro_records):
        key_exact = create_key_exact(rec)
        # Solo agregar si NO matcheó exacto
        if key_exact not in output_exact_index:
            key_base = create_key_base(rec)
            if key_base not in maestro_base_index:
                maestro_base_index[key_base] = []
            maestro_base_index[key_base].append((i, rec))

    output_base_index = {}
    for i, rec in enumerate(output_records):
        key_exact = create_key_exact(rec)
        # Solo agregar si NO matcheó exacto
        if key_exact not in maestro_exact_index:
            key_base = create_key_base(rec)
            if key_base not in output_base_index:
                output_base_index[key_base] = []
            output_base_index[key_base].append((i, rec))

    # Matching flexible con validación de similitud de descripción
    flexible_matches = []
    SIMILARITY_THRESHOLD = 0.7  # 70% de similitud mínima

    for key_base, maestro_list in maestro_base_index.items():
        if key_base in output_base_index:
            # Hay candidatos con misma fecha+importe+banco+cuenta
            for m_idx, m_rec in maestro_list:
                for o_idx, o_rec in output_base_index[key_base]:
                    # Validar similitud de descripción
                    sim = descripcion_similarity(m_rec['descripcion'], o_rec['descripcion'])
                    if sim >= SIMILARITY_THRESHOLD:
                        flexible_matches.append({
                            'm_rec': m_rec,
                            'o_rec': o_rec,
                            'similarity': sim,
                        })
                        break  # Solo el primer match
                break

    print(f"  Matches flexibles encontrados: {len(flexible_matches):,}")
    print(f"  Similitud promedio: {sum(m['similarity'] for m in flexible_matches) / len(flexible_matches) * 100:.1f}%" if flexible_matches else "")

    # Mostrar ejemplos de matches flexibles
    if flexible_matches:
        print(f"\n  Ejemplos de matches flexibles (primeros 20):")
        print(f"  {'Fecha':<12} {'Importe':>12} {'Sim%':>5} {'Maestro → Output':<80}")
        print("  " + "-" * 100)
        for match in flexible_matches[:20]:
            m = match['m_rec']
            o = match['o_rec']
            sim_pct = match['similarity'] * 100
            print(f"  {m['fecha']:<12} {m['importe']:>12} {sim_pct:>5.0f}% {m['descripcion'][:35]} → {o['descripcion'][:35]}")

    # Totales
    total_matches = exact_matches + len(flexible_matches)
    print(f"\n✅ TOTAL MATCHES: {total_matches:,} / {len(maestro_records):,} ({100 * total_matches / len(maestro_records):.1f}%)")

    # Registros no matched
    maestro_matched_keys = set(maestro_exact_index.keys())
    maestro_matched_keys.update(create_key_exact(m['m_rec']) for m in flexible_matches)

    output_matched_keys = set(output_exact_index.keys())
    output_matched_keys.update(create_key_exact(m['o_rec']) for m in flexible_matches)

    no_match_maestro = []
    for i, rec in enumerate(maestro_records):
        key = create_key_exact(rec)
        if key not in output_exact_index:
            # Verificar si matcheó flexible
            found = False
            for fm in flexible_matches:
                if create_key_exact(fm['m_rec']) == key:
                    found = True
                    break
            if not found:
                no_match_maestro.append(rec)

    no_match_output = []
    for i, rec in enumerate(output_records):
        key = create_key_exact(rec)
        if key not in maestro_exact_index:
            # Verificar si matcheó flexible
            found = False
            for fm in flexible_matches:
                if create_key_exact(fm['o_rec']) == key:
                    found = True
                    break
            if not found:
                no_match_output.append(rec)

    print(f"\n⚠️  Sin match en output:  {len(no_match_maestro):,}")
    print(f"⚠️  Sin match en maestro: {len(no_match_output):,}")

    # VALIDACIÓN DE CLASIFICACIÓN (solo para matches)
    print("\n" + "=" * 100)
    print("VALIDACIÓN DE CLASIFICACIÓN")
    print("=" * 100)

    cat1_matches = 0
    cat1_discrepancies = []
    cat2_matches = 0
    cat2_discrepancies = []
    tipo_matches = 0
    tipo_discrepancies = []

    # Comparar matches exactos
    for key, maestro_list in maestro_exact_index.items():
        if key in output_exact_index:
            for m_idx, m_rec in maestro_list:
                for o_idx, o_rec in output_exact_index[key]:
                    # Cat1
                    if m_rec['cat1'] and o_rec['cat1'] and m_rec['cat1'] != 'SIN_CLASIFICAR' and o_rec['cat1'] != 'SIN_CLASIFICAR':
                        if m_rec['cat1'] == o_rec['cat1']:
                            cat1_matches += 1
                        else:
                            cat1_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'maestro_cat1': m_rec['cat1'],
                                'output_cat1': o_rec['cat1'],
                            })

                    # Cat2
                    if m_rec['cat2'] and o_rec['cat2'] and m_rec['cat1'] == o_rec['cat1']:
                        if m_rec['cat2'] == o_rec['cat2']:
                            cat2_matches += 1
                        else:
                            cat2_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'cat1': m_rec['cat1'],
                                'maestro_cat2': m_rec['cat2'],
                                'output_cat2': o_rec['cat2'],
                            })

                    # Tipo
                    if m_rec['tipo'] and o_rec['tipo']:
                        if m_rec['tipo'] == o_rec['tipo']:
                            tipo_matches += 1
                        else:
                            tipo_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'maestro_tipo': m_rec['tipo'],
                                'output_tipo': o_rec['tipo'],
                            })
                    break

    # Comparar matches flexibles
    for match in flexible_matches:
        m_rec = match['m_rec']
        o_rec = match['o_rec']

        # Cat1
        if m_rec['cat1'] and o_rec['cat1'] and m_rec['cat1'] != 'SIN_CLASIFICAR' and o_rec['cat1'] != 'SIN_CLASIFICAR':
            if m_rec['cat1'] == o_rec['cat1']:
                cat1_matches += 1
            else:
                cat1_discrepancies.append({
                    'fecha': m_rec['fecha'],
                    'importe': m_rec['importe'],
                    'descripcion': m_rec['descripcion'][:50],
                    'banco': m_rec['banco'],
                    'maestro_cat1': m_rec['cat1'],
                    'output_cat1': o_rec['cat1'],
                })

        # Cat2
        if m_rec['cat2'] and o_rec['cat2'] and m_rec['cat1'] == o_rec['cat1']:
            if m_rec['cat2'] == o_rec['cat2']:
                cat2_matches += 1
            else:
                cat2_discrepancies.append({
                    'fecha': m_rec['fecha'],
                    'importe': m_rec['importe'],
                    'descripcion': m_rec['descripcion'][:50],
                    'banco': m_rec['banco'],
                    'cat1': m_rec['cat1'],
                    'maestro_cat2': m_rec['cat2'],
                    'output_cat2': o_rec['cat2'],
                })

        # Tipo
        if m_rec['tipo'] and o_rec['tipo']:
            if m_rec['tipo'] == o_rec['tipo']:
                tipo_matches += 1
            else:
                tipo_discrepancies.append({
                    'fecha': m_rec['fecha'],
                    'importe': m_rec['importe'],
                    'descripcion': m_rec['descripcion'][:50],
                    'banco': m_rec['banco'],
                    'maestro_tipo': m_rec['tipo'],
                    'output_tipo': o_rec['tipo'],
                })

    total_cat1 = cat1_matches + len(cat1_discrepancies)
    total_cat2 = cat2_matches + len(cat2_discrepancies)
    total_tipo = tipo_matches + len(tipo_discrepancies)

    if total_cat1 > 0:
        cat1_acc = 100 * cat1_matches / total_cat1
        print(f"\n📊 Cat1 Accuracy: {cat1_acc:.1f}% ({cat1_matches:,} / {total_cat1:,})")
        print(f"   Discrepancias:  {len(cat1_discrepancies):,}")

    if total_cat2 > 0:
        cat2_acc = 100 * cat2_matches / total_cat2
        print(f"\n📊 Cat2 Accuracy: {cat2_acc:.1f}% ({cat2_matches:,} / {total_cat2:,})")
        print(f"   Discrepancias:  {len(cat2_discrepancies):,}")

    if total_tipo > 0:
        tipo_acc = 100 * tipo_matches / total_tipo
        print(f"\n📊 Tipo Accuracy: {tipo_acc:.1f}% ({tipo_matches:,} / {total_tipo:,})")
        print(f"   Discrepancias:  {len(tipo_discrepancies):,}")

    # Mostrar primeras discrepancias Cat1
    if cat1_discrepancies:
        print("\n" + "=" * 100)
        print("DISCREPANCIAS CAT1 (Primeras 30)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Maestro':<20} {'Output':<20} {'Descripción':<30}")
        print("-" * 100)
        for disc in cat1_discrepancies[:30]:
            print(f"{disc['fecha']:<12} {disc['importe']:>10} {disc['banco']:<15} {disc['maestro_cat1']:<20} {disc['output_cat1']:<20} {disc['descripcion']:<30}")

    # Resumen final
    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)
    print(f"Registros maestro:       {len(maestro_records):,}")
    print(f"Registros output:        {len(output_records):,}")
    print(f"Matches exactos:         {exact_matches:,}")
    print(f"Matches flexibles:       {len(flexible_matches):,}")
    print(f"TOTAL MATCHES:           {total_matches:,} ({100 * total_matches / len(maestro_records):.1f}%)")
    print(f"Sin match en output:     {len(no_match_maestro):,}")
    print(f"Sin match en maestro:    {len(no_match_output):,}")
    print()
    if total_cat1 > 0:
        print(f"Cat1 Accuracy:           {cat1_acc:.1f}%")
    if total_cat2 > 0:
        print(f"Cat2 Accuracy:           {cat2_acc:.1f}%")
    if total_tipo > 0:
        print(f"Tipo Accuracy:           {tipo_acc:.1f}%")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
