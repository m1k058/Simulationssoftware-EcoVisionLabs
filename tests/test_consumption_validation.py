#!/usr/bin/env python3
"""Detaillierte Validierung der simulate_consumption Funktion"""

import sys
from pathlib import Path
# Add source-code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

from io_handler import load_data
from data_processing.simulation import simulate_consumption
import pandas as pd

print("="*70)
print("DETAILLIERTE VALIDIERUNG")
print("="*70)

# Lade Lastprofile
base = Path(__file__).parent / "raw-data"
lastH = load_data(base / "BDEW-Standardlastprofile-H25.csv", datatype="BDEW-Last")
lastG = load_data(base / "BDEW-Standardlastprofile-G25.csv", datatype="BDEW-Last")
lastL = load_data(base / "BDEW-Standardlastprofile-L25.csv", datatype="BDEW-Last")

print("\n1. ÜBERPRÜFUNG DER LASTPROFILE")
print("-"*70)
print(f"H25: {len(lastH)} Zeilen")
print(f"  - Unique months: {lastH['month'].unique()}")
print(f"  - Unique day_types: {lastH['day_type'].unique()}")
print(f"  - Min/Max value_kWh: {lastH['value_kWh'].min():.3f} / {lastH['value_kWh'].max():.3f}")

print(f"\nG25: {len(lastG)} Zeilen")
print(f"  - Unique months: {lastG['month'].unique()}")
print(f"  - Unique day_types: {lastG['day_type'].unique()}")

print(f"\nL25: {len(lastL)} Zeilen")
print(f"  - Unique months: {lastL['month'].unique()}")
print(f"  - Unique day_types: {lastL['day_type'].unique()}")

print("\n2. TEST MIT KLEINEN WERTEN (Jahr 2030)")
print("-"*70)

df_2030 = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=10.0,   # 10 TWh
    lastZielG=20.0,   # 20 TWh
    lastZielL=5.0,    # 5 TWh
    simu_jahr=2030
)

print("\n3. VALIDIERUNG DER ERGEBNISSE")
print("-"*70)

# Prüfe auf fehlende Werte
missing_H = df_2030['Haushalte [MWh]'].isna().sum()
missing_G = df_2030['Gewerbe [MWh]'].isna().sum()
missing_L = df_2030['Landwirtschaft [MWh]'].isna().sum()

print(f"Fehlende Werte:")
print(f"  - Haushalte: {missing_H}")
print(f"  - Gewerbe: {missing_G}")
print(f"  - Landwirtschaft: {missing_L}")

# Prüfe ob alle Werte >= 0
negative_H = (df_2030['Haushalte [MWh]'] < 0).sum()
negative_G = (df_2030['Gewerbe [MWh]'] < 0).sum()
negative_L = (df_2030['Landwirtschaft [MWh]'] < 0).sum()

print(f"\nNegative Werte:")
print(f"  - Haushalte: {negative_H}")
print(f"  - Gewerbe: {negative_G}")
print(f"  - Landwirtschaft: {negative_L}")

# Prüfe Zeitstempel
print(f"\nZeitstempel:")
print(f"  - Start: {df_2030['Zeitpunkt'].min()}")
print(f"  - Ende: {df_2030['Zeitpunkt'].max()}")
print(f"  - Anzahl: {len(df_2030)}")
print(f"  - Erwartete Anzahl für 2030: {365 * 96} (365 Tage * 96 Viertelstunden)")

# Prüfe auf Duplikate
duplicates = df_2030['Zeitpunkt'].duplicated().sum()
print(f"  - Duplikate: {duplicates}")

# Prüfe Lücken
time_diff = df_2030['Zeitpunkt'].diff()
expected_diff = pd.Timedelta(minutes=15)
gaps = (time_diff != expected_diff).sum() - 1  # -1 für ersten Wert (NaT)
print(f"  - Zeitlücken: {gaps}")

# Detaillierte Monats-Statistik
print(f"\n4. MONATSSTATISTIK")
print("-"*70)
df_2030['Monat'] = df_2030['Zeitpunkt'].dt.month
monthly = df_2030.groupby('Monat')['Gesamt [MWh]'].sum() / 1e6  # in TWh

for month in range(1, 13):
    print(f"  Monat {month:2d}: {monthly[month]:.4f} TWh")

print(f"\n  SUMME: {monthly.sum():.4f} TWh (Ziel: 35.0000 TWh)")

print("\n5. TEST SCHALTJAHR (2024)")
print("-"*70)

df_2024 = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=10.0,
    lastZielG=20.0,
    lastZielL=5.0,
    simu_jahr=2024  # Schaltjahr!
)

print(f"  - Anzahl Zeilen: {len(df_2024)}")
print(f"  - Erwartete Anzahl für 2024 (Schaltjahr): {366 * 96} (366 Tage * 96 Viertelstunden)")
print(f"  - Start: {df_2024['Zeitpunkt'].min()}")
print(f"  - Ende: {df_2024['Zeitpunkt'].max()}")

# Prüfe 29. Februar
feb_29 = df_2024[df_2024['Zeitpunkt'].dt.date == pd.Timestamp('2024-02-29').date()]
print(f"  - 29. Februar vorhanden: {len(feb_29) > 0} ({len(feb_29)} Einträge)")

print("\n6. FEIERTAGS-ÜBERPRÜFUNG")
print("-"*70)

# Erstelle Test-DataFrame mit allen Tagen
df_2030['Datum'] = df_2030['Zeitpunkt'].dt.date
tage = df_2030.groupby('Datum').first()

print("Bekannte Feiertage 2030:")
test_dates = [
    ('2030-01-01', 'Neujahr'),
    ('2030-05-01', 'Tag der Arbeit'),
    ('2030-10-03', 'Tag der deutschen Einheit'),
    ('2030-12-25', 'Weihnachten'),
    ('2030-12-26', '2. Weihnachtstag'),
]

for date_str, name in test_dates:
    date = pd.Timestamp(date_str).date()
    if date in tage.index:
        day_info = tage.loc[date]
        print(f"  {date} ({name}): Wochentag={day_info['weekday']}, day_type={day_info['day_type']}")

print("\n" + "="*70)
if (missing_H == 0 and missing_G == 0 and missing_L == 0 and 
    negative_H == 0 and negative_G == 0 and negative_L == 0 and
    duplicates == 0 and gaps == 0):
    print("✓✓✓ ALLE VALIDIERUNGEN BESTANDEN! ✓✓✓")
else:
    print("⚠ WARNUNG: Es wurden Probleme gefunden!")
print("="*70)
