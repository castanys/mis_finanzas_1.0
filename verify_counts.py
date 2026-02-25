"""Verificar conteos por archivo vs expectativas."""
import sys
sys.path.insert(0, '/home/pablo/apps/mis_finanzas_1.0')

from pipeline import TransactionPipeline
import os

# Expectativas de Pablo
expected = {
    'openbank_TOTAL_ES3600730100550435513660_EUR.csv': 13529,
    'Openbank_ES3600730100550435513660.csv': 6,
    'Revolut_ES1215830001199090471794.csv': 210,
    'ABANCA_ES5120800823473040166463.csv': 7,
    'MovimientosB100_ES88208001000130433834426.csv': 148,
    'MyInvestor_ES5215447889746650686253.csv': 10,
    'MyInvestor_ES6115447889736650701175.csv': 76,
    'MyInvestor_ES7715447889736650686240.csv': 26,
    'Myinvestor_ES6015447889796650683633.csv': 30,
    'Myinvestor_ES7415447889716653144178.csv': 29,
    'Openbank_Fede_ES1900730100500502943470.xls.csv': 26,
    'Openbank_Miguel_ES6700730100510502943333.xls.csv': 30,
    'Openbank_Violeta_ES4200730100550502943296.xls.csv': 81,
    'TradeRepublic_ES8015860001420977164411.csv': 920,
    'mediolanum_ES2501865001680510084831.csv': 457,
    'openbank_ES2200730100510135698457.csv': 55,
}

# Inicializar pipeline
pipeline = TransactionPipeline(
    master_csv_path='Validación_Categorias_Finsense_04020206_5.csv'
)

# Procesar cada archivo individualmente
input_dir = 'input'
actual = {}

for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        filepath = os.path.join(input_dir, filename)
        try:
            records = pipeline.process_file(filepath, classify=False)
            actual[filename] = len(records)
        except Exception as e:
            print(f"Error procesando {filename}: {e}")

# Comparar
print("\n" + "=" * 100)
print("VERIFICACIÓN DE CONTEOS POR ARCHIVO")
print("=" * 100)
print(f"{'Archivo':<60s} {'Esperado':>10s} {'Actual':>10s} {'Estado':>10s}")
print("-" * 100)

total_esperado = 0
total_actual = 0
errores = []

for filename in sorted(expected.keys()):
    esp = expected[filename]
    act = actual.get(filename, 0)
    total_esperado += esp
    total_actual += act
    
    if esp == act:
        estado = "✓ OK"
    else:
        estado = "✗ ERROR"
        errores.append(f"{filename}: esperado {esp}, actual {act}")
    
    print(f"{filename:<60s} {esp:>10d} {act:>10d} {estado:>10s}")

print("-" * 100)
print(f"{'TOTAL':<60s} {total_esperado:>10d} {total_actual:>10d}")
print("=" * 100)

if errores:
    print("\n⚠️  ERRORES ENCONTRADOS:")
    for err in errores:
        print(f"  - {err}")
else:
    print("\n✅ Todos los conteos coinciden perfectamente!")

print(f"\nTotal esperado:  {total_esperado:,}")
print(f"Total actual:    {total_actual:,}")
print(f"Diferencia:      {total_actual - total_esperado:,}")
