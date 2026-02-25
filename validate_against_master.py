#!/usr/bin/env python3
"""
Validación cruzada contra CSV maestro.

Compara el output del pipeline contra el CSV maestro (verdad absoluta)
para verificar:
1. Mismo número de registros
2. Coincidencia de datos (fecha, importe, descripción, banco, cuenta)
3. Coincidencia de clasificación (Cat1, Cat2, Tipo)
"""
import csv
from collections import defaultdict
from typing import Dict, List, Tuple


def load_maestro(filepath: str) -> List[Dict]:
    """
    Cargar CSV maestro.

    Columnas: Fecha;Importe;Descripción;Banco;Cuenta;Tipo;Cat1;Cat2;Hash;id
    """
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:  # utf-8-sig para BOM
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Normalizar nombres de columnas
            fecha = row.get('Fecha', '').strip()
            cuenta = row.get('Cuenta', '').strip()

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
                'cuenta': cuenta,  # Mantener cuenta original (puede ser abreviada)
                'tipo': row.get('Tipo', '').strip(),
                'cat1': row.get('Cat1', '').strip(),
                'cat2': row.get('Cat2', '').strip(),
                'hash': row.get('Hash', '').strip(),
                'id': row.get('id', '').strip(),
            }
            records.append(record)
    return records


def load_output(filepath: str) -> List[Dict]:
    """
    Cargar CSV de output del pipeline.

    Columnas: fecha,importe,descripcion,banco,cuenta,cat1,cat2,tipo,capa,hash,source_file,line_num
    """
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
                'capa': row.get('capa', '').strip(),
                'hash': row.get('hash', '').strip(),
                'source_file': row.get('source_file', '').strip(),
                'line_num': row.get('line_num', '').strip(),
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
    """
    Normalizar cuenta para matching.

    Maestro usa últimos 4 dígitos (ej: 3660)
    Output usa IBAN completo (ej: ES3600730100550435513660)

    Retornamos los últimos 4 dígitos para compatibilidad.
    """
    if not cuenta:
        return ""
    # Extraer solo dígitos
    digits = ''.join(c for c in cuenta if c.isdigit())
    # Retornar últimos 4
    return digits[-4:] if len(digits) >= 4 else digits


def create_key(record: Dict) -> str:
    """
    Crear clave única para matching.

    Usa: fecha + importe + descripcion + banco + cuenta_normalizada
    NO usa hash porque puede haberse generado diferente.
    """
    try:
        importe = normalize_number(record['importe'])
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{importe:.2f}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"
    except:
        cuenta_norm = normalize_cuenta(record['cuenta'])
        return f"{record['fecha']}|{record['importe']}|{record['descripcion']}|{record['banco']}|{cuenta_norm}"


def main():
    print("\n" + "=" * 100)
    print("VALIDACIÓN CRUZADA CONTRA CSV MAESTRO")
    print("=" * 100)

    # Cargar datos
    print("\n📂 Cargando datos...")
    maestro_records = load_maestro('Validación_Categorias_Finsense_04020206_5.csv')
    output_records = load_output('output/transacciones_completas.csv')

    print(f"  Registros en maestro: {len(maestro_records):,}")
    print(f"  Registros en output:  {len(output_records):,}")

    # 1. Verificar número de registros
    print("\n" + "=" * 100)
    print("1. VERIFICACIÓN DE CANTIDAD")
    print("=" * 100)
    if len(maestro_records) == len(output_records):
        print(f"✅ Mismo número de registros: {len(maestro_records):,}")
    else:
        diff = len(output_records) - len(maestro_records)
        print(f"⚠️  Diferencia: {diff:+,} registros")
        print(f"   Maestro: {len(maestro_records):,}")
        print(f"   Output:  {len(output_records):,}")

    # 2. Crear índices para matching
    print("\n📊 Creando índices para matching...")
    maestro_index = {}
    for i, record in enumerate(maestro_records):
        key = create_key(record)
        if key not in maestro_index:
            maestro_index[key] = []
        maestro_index[key].append((i, record))

    output_index = {}
    for i, record in enumerate(output_records):
        key = create_key(record)
        if key not in output_index:
            output_index[key] = []
        output_index[key].append((i, record))

    print(f"  Claves únicas en maestro: {len(maestro_index):,}")
    print(f"  Claves únicas en output:  {len(output_index):,}")

    # 3. Matching y comparación de clasificación
    print("\n" + "=" * 100)
    print("2. MATCHING Y COMPARACIÓN DE CLASIFICACIÓN")
    print("=" * 100)

    matches = 0
    no_match_in_output = []
    no_match_in_maestro = []

    cat1_matches = 0
    cat1_discrepancies = []
    cat2_matches = 0
    cat2_discrepancies = []
    tipo_matches = 0
    tipo_discrepancies = []

    sin_clasificar_output = []
    sin_clasificar_maestro = []

    # Comparar maestro -> output
    for key, maestro_list in maestro_index.items():
        if key in output_index:
            matches += len(maestro_list)

            # Comparar clasificaciones
            for m_idx, m_rec in maestro_list:
                for o_idx, o_rec in output_index[key]:
                    # Cat1
                    m_cat1 = m_rec['cat1']
                    o_cat1 = o_rec['cat1']

                    if o_cat1 == 'SIN_CLASIFICAR':
                        sin_clasificar_output.append(o_rec)

                    if m_cat1 and o_cat1 and m_cat1 != 'SIN_CLASIFICAR' and o_cat1 != 'SIN_CLASIFICAR':
                        if m_cat1 == o_cat1:
                            cat1_matches += 1
                        else:
                            cat1_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'maestro_cat1': m_cat1,
                                'output_cat1': o_cat1,
                            })

                    # Cat2
                    m_cat2 = m_rec['cat2']
                    o_cat2 = o_rec['cat2']

                    if m_cat2 and o_cat2 and m_cat1 == o_cat1:  # Solo si Cat1 coincide
                        if m_cat2 == o_cat2:
                            cat2_matches += 1
                        else:
                            cat2_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'cat1': m_cat1,
                                'maestro_cat2': m_cat2,
                                'output_cat2': o_cat2,
                            })

                    # Tipo
                    m_tipo = m_rec['tipo']
                    o_tipo = o_rec['tipo']

                    if m_tipo and o_tipo:
                        if m_tipo == o_tipo:
                            tipo_matches += 1
                        else:
                            tipo_discrepancies.append({
                                'fecha': m_rec['fecha'],
                                'importe': m_rec['importe'],
                                'descripcion': m_rec['descripcion'][:50],
                                'banco': m_rec['banco'],
                                'maestro_tipo': m_tipo,
                                'output_tipo': o_tipo,
                            })

                    break  # Solo comparar con el primer match
        else:
            for m_idx, m_rec in maestro_list:
                no_match_in_output.append(m_rec)

    # Buscar registros en output que no están en maestro
    for key, output_list in output_index.items():
        if key not in maestro_index:
            for o_idx, o_rec in output_list:
                no_match_in_maestro.append(o_rec)

    # Resultados
    print(f"\n✅ Matches exactos: {matches:,} / {len(maestro_records):,}")
    if no_match_in_output:
        print(f"⚠️  Registros en maestro NO encontrados en output: {len(no_match_in_output)}")
    if no_match_in_maestro:
        print(f"⚠️  Registros en output NO encontrados en maestro: {len(no_match_in_maestro)}")

    print(f"\n📊 Clasificación Cat1:")
    total_cat1_comparisons = cat1_matches + len(cat1_discrepancies)
    if total_cat1_comparisons > 0:
        cat1_accuracy = 100 * cat1_matches / total_cat1_comparisons
        print(f"  Coincidencias:  {cat1_matches:,} / {total_cat1_comparisons:,} ({cat1_accuracy:.1f}%)")
        print(f"  Discrepancias:  {len(cat1_discrepancies):,}")

    print(f"\n📊 Clasificación Cat2:")
    total_cat2_comparisons = cat2_matches + len(cat2_discrepancies)
    if total_cat2_comparisons > 0:
        cat2_accuracy = 100 * cat2_matches / total_cat2_comparisons
        print(f"  Coincidencias:  {cat2_matches:,} / {total_cat2_comparisons:,} ({cat2_accuracy:.1f}%)")
        print(f"  Discrepancias:  {len(cat2_discrepancies):,}")

    print(f"\n📊 Tipo:")
    total_tipo_comparisons = tipo_matches + len(tipo_discrepancies)
    if total_tipo_comparisons > 0:
        tipo_accuracy = 100 * tipo_matches / total_tipo_comparisons
        print(f"  Coincidencias:  {tipo_matches:,} / {total_tipo_comparisons:,} ({tipo_accuracy:.1f}%)")
        print(f"  Discrepancias:  {len(tipo_discrepancies):,}")

    # Mostrar discrepancias Cat1 (primeras 50)
    if cat1_discrepancies:
        print("\n" + "=" * 100)
        print("3. DISCREPANCIAS CAT1 (Primeras 50)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Maestro Cat1':<20} {'Output Cat1':<20} {'Descripción':<30}")
        print("-" * 100)
        for disc in cat1_discrepancies[:50]:
            print(f"{disc['fecha']:<12} {disc['importe']:>10} {disc['banco']:<15} {disc['maestro_cat1']:<20} {disc['output_cat1']:<20} {disc['descripcion']:<30}")

    # Mostrar discrepancias Cat2 (primeras 50)
    if cat2_discrepancies:
        print("\n" + "=" * 100)
        print("4. DISCREPANCIAS CAT2 (Primeras 50)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Cat1':<20} {'Maestro Cat2':<20} {'Output Cat2':<20} {'Descripción':<30}")
        print("-" * 100)
        for disc in cat2_discrepancies[:50]:
            print(f"{disc['fecha']:<12} {disc['importe']:>10} {disc['cat1']:<20} {disc['maestro_cat2']:<20} {disc['output_cat2']:<20} {disc['descripcion']:<30}")

    # Mostrar discrepancias Tipo (primeras 50)
    if tipo_discrepancies:
        print("\n" + "=" * 100)
        print("5. DISCREPANCIAS TIPO (Primeras 50)")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Maestro Tipo':<20} {'Output Tipo':<20} {'Descripción':<30}")
        print("-" * 100)
        for disc in tipo_discrepancies[:50]:
            print(f"{disc['fecha']:<12} {disc['importe']:>10} {disc['banco']:<15} {disc['maestro_tipo']:<20} {disc['output_tipo']:<20} {disc['descripcion']:<30}")

    # Deduplicate sin clasificar (en caso de que haya duplicados en el matching)
    seen = set()
    unique_sin_clasificar = []
    for rec in sin_clasificar_output:
        key = create_key(rec)
        if key not in seen:
            seen.add(key)
            unique_sin_clasificar.append(rec)

    # Mostrar transacciones sin clasificar en output
    if unique_sin_clasificar:
        print("\n" + "=" * 100)
        print(f"6. TRANSACCIONES SIN CLASIFICAR EN OUTPUT ({len(unique_sin_clasificar)})")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Cuenta':<26} {'Descripción':<50}")
        print("-" * 100)

        for rec in unique_sin_clasificar:
            print(f"{rec['fecha']:<12} {rec['importe']:>10} {rec['banco']:<15} {rec['cuenta']:<26} {rec['descripcion'][:50]:<50}")

    # Mostrar registros no encontrados
    if no_match_in_output:
        print("\n" + "=" * 100)
        print(f"7. REGISTROS EN MAESTRO NO ENCONTRADOS EN OUTPUT ({len(no_match_in_output)})")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Descripción':<50}")
        print("-" * 100)
        for rec in no_match_in_output[:50]:
            print(f"{rec['fecha']:<12} {rec['importe']:>10} {rec['banco']:<15} {rec['descripcion'][:50]:<50}")

    if no_match_in_maestro:
        print("\n" + "=" * 100)
        print(f"8. REGISTROS EN OUTPUT NO ENCONTRADOS EN MAESTRO ({len(no_match_in_maestro)})")
        print("=" * 100)
        print(f"{'Fecha':<12} {'Importe':>10} {'Banco':<15} {'Descripción':<50}")
        print("-" * 100)
        for rec in no_match_in_maestro[:50]:
            print(f"{rec['fecha']:<12} {rec['importe']:>10} {rec['banco']:<15} {rec['descripcion'][:50]:<50}")

    # Resumen final
    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)
    print(f"Registros maestro:      {len(maestro_records):,}")
    print(f"Registros output:       {len(output_records):,}")
    print(f"Matches exactos:        {matches:,}")
    print(f"Sin match en output:    {len(no_match_in_output):,}")
    print(f"Sin match en maestro:   {len(no_match_in_maestro):,}")
    print()
    if total_cat1_comparisons > 0:
        print(f"Cat1 Accuracy:          {cat1_accuracy:.1f}% ({cat1_matches:,} / {total_cat1_comparisons:,})")
    if total_cat2_comparisons > 0:
        print(f"Cat2 Accuracy:          {cat2_accuracy:.1f}% ({cat2_matches:,} / {total_cat2_comparisons:,})")
    if total_tipo_comparisons > 0:
        print(f"Tipo Accuracy:          {tipo_accuracy:.1f}% ({tipo_matches:,} / {total_tipo_comparisons:,})")
    print(f"Sin clasificar output:  {len(unique_sin_clasificar):,}")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
