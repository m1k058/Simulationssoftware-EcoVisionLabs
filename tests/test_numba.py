# tests/test_numba_better.py
from numba import jit, prange
import numpy as np
import pandas as pd
import time

# Simuliert deine Wärmepumpen-Berechnung
@jit(nopython=True, parallel=True)
def calculate_heatpump_numba(temperatures, hours, factors):
    """
    Numba-optimiert: Wärmepumpen-Faktoren berechnen
    """
    n = len(temperatures)
    result = np.zeros(n)
    
    for i in prange(n):  # Parallel über alle Zeilen
        temp = temperatures[i]
        hour = hours[i]
        
        # Beispiel-Logik (ähnlich zu deinem _get_hp_factor)
        if temp < 0:
            temp_factor = 0.8
        elif temp < 10:
            temp_factor = 1.0
        else:
            temp_factor = 1.2
        
        # Stunden-Faktor
        if 6 <= hour <= 10 or 17 <= hour <= 22:
            hour_factor = 1.5  # Peak hours
        else:
            hour_factor = 1.0
        
        # Kombination
        result[i] = temp_factor * hour_factor * factors[i]
    
    return result


# Normal Python (wie dein iterrows)
def calculate_heatpump_python(df):
    """
    Normale Python-Loop (langsam!)
    """
    result = []
    for idx, row in df.iterrows():
        temp = row['temp']
        hour = row['hour']
        factor = row['factor']
        
        if temp < 0:
            temp_factor = 0.8
        elif temp < 10:
            temp_factor = 1.0
        else:
            temp_factor = 1.2
        
        if 6 <= hour <= 10 or 17 <= hour <= 22:
            hour_factor = 1.5
        else:
            hour_factor = 1.0
        
        result.append(temp_factor * hour_factor * factor)
    
    return result


print("=" * 60)
print("🔍 Numba Test - Realistische Wärmepumpen-Berechnung")
print("=" * 60)

# Erstelle Test-Daten (1 Jahr, 15-Minuten-Takt)
n_rows = 35040  # 365 * 24 * 4
print(f"\n📊 Datensatz: {n_rows:,} Zeilen (1 Jahr, 15-Min-Takt)")

dates = pd.date_range('2024-01-01', periods=n_rows, freq='15min')
df = pd.DataFrame({
    'time': dates,
    'temp': np.random.randn(n_rows) * 10 + 8,
    'hour': dates.hour,
    'factor': np.random.rand(n_rows) * 0.5 + 0.75
})

print(f"💾 Größe: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# Test 1: Normal Python (nur 1000 Zeilen, sonst zu langsam!)
print("\n⏱️  Test 1: Python iterrows (1000 Zeilen)...")
df_small = df.head(1000)
start = time.time()
result_python = calculate_heatpump_python(df_small)
python_time = time.time() - start
print(f"   Zeit: {python_time:.3f}s")

# Test 2: Numba (ALLE Zeilen!)
print("\n⚡ Test 2: Numba parallel (35,040 Zeilen)...")
temps = df['temp'].values
hours = df['hour'].values
factors = df['factor'].values

# Warmup (Kompilierung)
print("   Kompiliere...")
_ = calculate_heatpump_numba(temps[:100], hours[:100], factors[:100])

# Echter Test
print("   Berechne...")
start = time.time()
result_numba = calculate_heatpump_numba(temps, hours, factors)
numba_time = time.time() - start
print(f"   Zeit: {numba_time:.3f}s")

# Vergleich
python_time_full = python_time * (n_rows / 1000)  # Hochgerechnet
print(f"\n📊 Ergebnisse:")
print(f"   Python (hochgerechnet):  {python_time_full:.1f}s ({python_time_full/60:.1f} Minuten)")
print(f"   Numba (tatsächlich):     {numba_time:.3f}s")
print(f"   🚀 Speedup: {python_time_full/numba_time:.0f}x schneller!")

if python_time_full > 60:
    print(f"\n✅ Von {python_time_full/60:.1f} Minuten auf {numba_time:.1f} Sekunden!")
else:
    print(f"\n✅ Von {python_time_full:.1f}s auf {numba_time:.1f}s!")

print("=" * 60)