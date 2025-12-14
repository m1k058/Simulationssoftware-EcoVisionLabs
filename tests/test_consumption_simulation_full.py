#!/usr/bin/env python3
"""Vollständiger Test für simulate_consumption mit Export"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "source-code"))

from io_handler import load_data
from data_processing.simulation import simulate_consumption

print("="*70)
print("VOLLSTÄNDIGER TEST: simulate_consumption")
print("="*70)

# Lade Lastprofile
print("\n1. Lade BDEW-Lastprofile...")
base = Path(__file__).parent / "raw-data"
lastH = load_data(base / "BDEW-Standardlastprofile-H25.csv", datatype="BDEW-Last")
lastG = load_data(base / "BDEW-Standardlastprofile-G25.csv", datatype="BDEW-Last")
lastL = load_data(base / "BDEW-Standardlastprofile-L25.csv", datatype="BDEW-Last")
print("   ✓ H25, G25, L25 erfolgreich geladen")

# Test 1: Jahr 2030
print("\n" + "="*70)
print("TEST 1: Simulation für 2030")
print("="*70)

df_2030 = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=130.0,  # TWh - Beispielwert Haushalte
    lastZielG=150.0,  # TWh - Beispielwert Gewerbe
    lastZielL=20.0,   # TWh - Beispielwert Landwirtschaft
    simu_jahr=2030
)

print("\n✓ Simulation 2030 erfolgreich!")

# Test 2: Jahr 2045
print("\n" + "="*70)
print("TEST 2: Simulation für 2045")
print("="*70)

df_2045 = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=140.0,  # TWh - Beispielwert Haushalte
    lastZielG=160.0,  # TWh - Beispielwert Gewerbe
    lastZielL=25.0,   # TWh - Beispielwert Landwirtschaft
    simu_jahr=2045
)

print("\n✓ Simulation 2045 erfolgreich!")

# Export
print("\n" + "="*70)
print("EXPORT DER ERGEBNISSE")
print("="*70)

output_path = Path(__file__).parent / "output" / "csv"
output_path.mkdir(parents=True, exist_ok=True)

file_2030 = output_path / "Verbrauch_Simulation_2030.csv"
file_2045 = output_path / "Verbrauch_Simulation_2045.csv"

df_2030.to_csv(file_2030, sep=';', decimal=',', index=False, date_format='%Y-%m-%d %H:%M:%S')
df_2045.to_csv(file_2045, sep=';', decimal=',', index=False, date_format='%Y-%m-%d %H:%M:%S')

print(f"\n✓ Ergebnisse exportiert:")
print(f"  - {file_2030}")
print(f"  - {file_2045}")

# Statistiken
print("\n" + "="*70)
print("ZUSAMMENFASSUNG")
print("="*70)
print(f"\n2030:")
print(f"  Anzahl Datenpunkte: {len(df_2030)}")
print(f"  Zeitraum: {df_2030['Zeitpunkt'].min()} bis {df_2030['Zeitpunkt'].max()}")
print(f"  Gesamt: {df_2030['Gesamt [MWh]'].sum() / 1e6:.2f} TWh")

print(f"\n2045:")
print(f"  Anzahl Datenpunkte: {len(df_2045)}")
print(f"  Zeitraum: {df_2045['Zeitpunkt'].min()} bis {df_2045['Zeitpunkt'].max()}")
print(f"  Gesamt: {df_2045['Gesamt [MWh]'].sum() / 1e6:.2f} TWh")

print("\n" + "="*70)
print("✓✓✓ ALLE TESTS ERFOLGREICH! ✓✓✓")
print("="*70)
