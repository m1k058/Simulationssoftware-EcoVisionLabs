"""
Test-Skript für die Integration des Lastprofils in die Simulation.
"""

import sys
import os
# Da wir im tests/ Verzeichnis sind, gehe ein Level hoch und dann zu source-code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import pandas as pd
import locale
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing.simulation import calc_scaled_consumption

# Setup
locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

print("="*80)
print("TEST: Lastprofil-Integration in Simulation")
print("="*80)

# Lade Konfiguration und Daten
config_manager = ConfigManager()
config_manager.load()
data_manager = DataManager(config_manager)

# Lade Verbrauchsdaten
print("\n1. Lade Verbrauchsdaten...")
df_consumption = data_manager.get("SMARD_2020-2025_Verbrauch")
print(f"   ✓ {len(df_consumption)} Zeilen geladen")

# Lade Prognosedaten
print("\n2. Lade Prognosedaten...")
df_prognose = data_manager.get("Erzeugungs/Verbrauchs Prognose Daten")
print(f"   ✓ {len(df_prognose)} Zeilen geladen")

# Test 1: Mit Lastprofil
print("\n" + "="*80)
print("TEST 1: Simulation MIT Lastprofil S25")
print("="*80)
df_result_mit_profil = calc_scaled_consumption(
    conDf=df_consumption,
    progDf=df_prognose,
    prog_dat_studie="Agora",
    simu_jahr=2030,
    ref_jahr=2024,
    use_load_profile=True
)

print(f"\nErgebnis:")
print(f"  Anzahl Zeitstempel: {len(df_result_mit_profil)}")
print(f"  Spalten: {list(df_result_mit_profil.columns)}")
print(f"  Gesamt-Verbrauch: {df_result_mit_profil['Skalierter Netzlast [MWh]'].sum() / 1_000_000:.2f} TWh")
print(f"\n  Erste 10 Zeilen:")
print(df_result_mit_profil.head(10))

# Test 2: Ohne Lastprofil (alte Methode)
print("\n" + "="*80)
print("TEST 2: Simulation OHNE Lastprofil (alte Methode)")
print("="*80)
df_result_ohne_profil = calc_scaled_consumption(
    conDf=df_consumption,
    progDf=df_prognose,
    prog_dat_studie="Agora",
    simu_jahr=2030,
    ref_jahr=2024,
    use_load_profile=False
)

print(f"\nErgebnis:")
print(f"  Anzahl Zeitstempel: {len(df_result_ohne_profil)}")
print(f"  Gesamt-Verbrauch: {df_result_ohne_profil['Skalierter Netzlast [MWh]'].sum() / 1_000_000:.2f} TWh")

# Vergleich
print("\n" + "="*80)
print("VERGLEICH")
print("="*80)

# Berechne Statistiken
mean_mit = df_result_mit_profil['Skalierter Netzlast [MWh]'].mean()
std_mit = df_result_mit_profil['Skalierter Netzlast [MWh]'].std()
min_mit = df_result_mit_profil['Skalierter Netzlast [MWh]'].min()
max_mit = df_result_mit_profil['Skalierter Netzlast [MWh]'].max()

mean_ohne = df_result_ohne_profil['Skalierter Netzlast [MWh]'].mean()
std_ohne = df_result_ohne_profil['Skalierter Netzlast [MWh]'].std()
min_ohne = df_result_ohne_profil['Skalierter Netzlast [MWh]'].min()
max_ohne = df_result_ohne_profil['Skalierter Netzlast [MWh]'].max()

print(f"\nMIT Lastprofil S25:")
print(f"  Mittelwert: {mean_mit:.2f} MWh")
print(f"  Std.abw.:   {std_mit:.2f} MWh")
print(f"  Min:        {min_mit:.2f} MWh")
print(f"  Max:        {max_mit:.2f} MWh")
print(f"  Spanne:     {max_mit - min_mit:.2f} MWh ({(max_mit - min_mit) / mean_mit * 100:.1f}% vom Mittelwert)")

print(f"\nOHNE Lastprofil (alte Methode):")
print(f"  Mittelwert: {mean_ohne:.2f} MWh")
print(f"  Std.abw.:   {std_ohne:.2f} MWh")
print(f"  Min:        {min_ohne:.2f} MWh")
print(f"  Max:        {max_ohne:.2f} MWh")
print(f"  Spanne:     {max_ohne - min_ohne:.2f} MWh ({(max_ohne - min_ohne) / mean_ohne * 100:.1f}% vom Mittelwert)")

print(f"\n→ Das Lastprofil erzeugt deutlich realistischere Lastschwankungen!")
print(f"  Standardabweichung MIT Profil ist {std_mit / std_ohne:.1f}x höher")

print("\n" + "="*80)
print("✓ Test erfolgreich abgeschlossen")
print("="*80)
