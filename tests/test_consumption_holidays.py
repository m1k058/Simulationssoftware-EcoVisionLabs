#!/usr/bin/env python3
"""Test mit holidays Package für korrekte Feiertagserkennung"""

import sys
from pathlib import Path
# Add source-code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

from io_handler import load_data
from data_processing.simulation import simulate_consumption
import holidays

print("="*70)
print("TEST MIT HOLIDAYS PACKAGE")
print("="*70)

# Deutsche Feiertage 2030
de_holidays_2030 = holidays.Germany(years=2030)
print("\nAlle deutschen Feiertage 2030:")
for date, name in sorted(de_holidays_2030.items()):
    weekday = date.strftime("%A")
    print(f"  {date} ({weekday}): {name}")

print(f"\nGesamt: {len(de_holidays_2030)} Feiertage")

# Lade Lastprofile
base = Path(__file__).parent / "raw-data"
lastH = load_data(base / "BDEW-Standardlastprofile-H25.csv", datatype="BDEW-Last")
lastG = load_data(base / "BDEW-Standardlastprofile-G25.csv", datatype="BDEW-Last")
lastL = load_data(base / "BDEW-Standardlastprofile-L25.csv", datatype="BDEW-Last")

print("\n" + "="*70)
print("SIMULATION 2030")
print("="*70)

df = simulate_consumption(
    lastH=lastH,
    lastG=lastG,
    lastL=lastL,
    lastZielH=10.0,
    lastZielG=20.0,
    lastZielL=5.0,
    simu_jahr=2030
)

print("\n✓ Mit holidays Package sollten alle Feiertage korrekt sein!")
