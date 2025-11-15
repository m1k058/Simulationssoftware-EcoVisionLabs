"""
Kritische Überprüfung: Summengleichheit und realistische Verteilung
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source-code'))

import pandas as pd
import locale
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing.simulation import calc_scaled_consumption

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

print("="*80)
print("KRITISCHE ÜBERPRÜFUNG: Summengleichheit und Verteilung")
print("="*80)

# Lade Daten
config_manager = ConfigManager()
config_manager.load()
data_manager = DataManager(config_manager)

df_consumption = data_manager.get("SMARD_2020-2025_Verbrauch")
df_prognose = data_manager.get("Erzeugungs/Verbrauchs Prognose Daten")

print("\n" + "="*80)
print("TEST 1: Vergleich der Jahressummen")
print("="*80)

# Simulation MIT Lastprofil
df_mit = calc_scaled_consumption(
    conDf=df_consumption,
    progDf=df_prognose,
    prog_dat_studie="Agora",
    simu_jahr=2030,
    ref_jahr=2024,
    use_load_profile=True
)

# Simulation OHNE Lastprofil
df_ohne = calc_scaled_consumption(
    conDf=df_consumption,
    progDf=df_prognose,
    prog_dat_studie="Agora",
    simu_jahr=2030,
    ref_jahr=2024,
    use_load_profile=False
)

summe_mit = df_mit['Skalierter Netzlast [MWh]'].sum()
summe_ohne = df_ohne['Skalierter Netzlast [MWh]'].sum()

print(f"\nJahressummen:")
print(f"  MIT Lastprofil:  {summe_mit / 1_000_000:.6f} TWh")
print(f"  OHNE Lastprofil: {summe_ohne / 1_000_000:.6f} TWh")
print(f"  Differenz:       {(summe_mit - summe_ohne) / 1_000_000:.6f} TWh")
print(f"  Abweichung:      {(summe_mit / summe_ohne - 1) * 100:.3f}%")

if abs(summe_mit - summe_ohne) / summe_ohne > 0.01:  # > 1% Abweichung
    print(f"\n⚠️  WARNUNG: Abweichung > 1%! Die Summen sollten (fast) gleich sein!")
else:
    print(f"\n✓ OK: Summen sind fast gleich (< 1% Abweichung)")

print("\n" + "="*80)
print("TEST 2: Viertelstunden-Vergleich (höher/niedriger)")
print("="*80)

# Vergleiche jede einzelne Viertelstunde
df_vergleich = pd.DataFrame({
    'Zeitpunkt': df_mit['Zeitpunkt'],
    'MIT_Profil': df_mit['Skalierter Netzlast [MWh]'],
    'OHNE_Profil': df_ohne['Skalierter Netzlast [MWh]']
})

df_vergleich['Differenz'] = df_vergleich['MIT_Profil'] - df_vergleich['OHNE_Profil']
df_vergleich['Differenz_Prozent'] = (df_vergleich['MIT_Profil'] / df_vergleich['OHNE_Profil'] - 1) * 100

# Zähle höher/niedriger
anzahl_hoeher = (df_vergleich['Differenz'] > 0).sum()
anzahl_niedriger = (df_vergleich['Differenz'] < 0).sum()
anzahl_gleich = (df_vergleich['Differenz'] == 0).sum()

print(f"\nVon {len(df_vergleich)} Viertelstunden sind:")
print(f"  {anzahl_hoeher:>6} Viertelstunden HÖHER mit Lastprofil ({anzahl_hoeher/len(df_vergleich)*100:.1f}%)")
print(f"  {anzahl_niedriger:>6} Viertelstunden NIEDRIGER mit Lastprofil ({anzahl_niedriger/len(df_vergleich)*100:.1f}%)")
print(f"  {anzahl_gleich:>6} Viertelstunden GLEICH ({anzahl_gleich/len(df_vergleich)*100:.1f}%)")

if anzahl_niedriger == 0:
    print(f"\n⚠️  FEHLER: ALLE Werte sind höher! Das kann nicht stimmen!")
    print(f"   Es MUSS auch niedrigere Werte geben, wenn die Summe gleich bleiben soll.")
else:
    print(f"\n✓ OK: Es gibt sowohl höhere als auch niedrigere Werte")

print("\n" + "="*80)
print("TEST 3: Extremwerte - Top 10 höher/niedriger")
print("="*80)

print("\nTop 10 HÖCHSTE Abweichungen (MIT Profil > OHNE Profil):")
df_top_hoeher = df_vergleich.nlargest(10, 'Differenz')
print(df_top_hoeher[['Zeitpunkt', 'MIT_Profil', 'OHNE_Profil', 'Differenz_Prozent']].to_string(index=False))

print("\n\nTop 10 NIEDRIGSTE Abweichungen (MIT Profil < OHNE Profil):")
df_top_niedriger = df_vergleich.nsmallest(10, 'Differenz')
print(df_top_niedriger[['Zeitpunkt', 'MIT_Profil', 'OHNE_Profil', 'Differenz_Prozent']].to_string(index=False))

print("\n" + "="*80)
print("TEST 4: Beispiel-Tag - Stündliche Werte")
print("="*80)

# Wähle einen Montag im Sommer (hohe PV-Erzeugung)
beispiel_tag = pd.to_datetime('2030-07-01')  # Montag
df_beispiel = df_vergleich[df_vergleich['Zeitpunkt'].dt.date == beispiel_tag.date()].copy()

# Gruppiere nach Stunde (Durchschnitt der 4 Viertelstunden)
df_beispiel['Stunde'] = df_beispiel['Zeitpunkt'].dt.hour
df_stuendlich = df_beispiel.groupby('Stunde').agg({
    'MIT_Profil': 'mean',
    'OHNE_Profil': 'mean',
    'Differenz': 'mean',
    'Differenz_Prozent': 'mean'
}).reset_index()

print(f"\n{beispiel_tag.strftime('%A, %d. %B %Y')} (Werktag, Sommer):")
print(f"\n{'Stunde':<10} {'MIT [MWh]':<15} {'OHNE [MWh]':<15} {'Diff [MWh]':<15} {'Diff [%]':<10}")
print("-" * 70)
for _, row in df_stuendlich.iterrows():
    stunde = int(row['Stunde'])
    print(f"{stunde:02d}:00-{stunde+1:02d}:00  {row['MIT_Profil']:>13.2f}  {row['OHNE_Profil']:>13.2f}  {row['Differenz']:>13.2f}  {row['Differenz_Prozent']:>8.1f}%")

print("\n" + "="*80)
print("TEST 5: Mittagszeit (12:00-14:00) - Sollte NIEDRIGER sein (PV-Effekt)")
print("="*80)

# Alle Mittags-Viertelstunden
df_mittag = df_vergleich[df_vergleich['Zeitpunkt'].dt.hour.isin([12, 13])].copy()

mittag_durchschnitt_mit = df_mittag['MIT_Profil'].mean()
mittag_durchschnitt_ohne = df_mittag['OHNE_Profil'].mean()
mittag_differenz = mittag_durchschnitt_mit - mittag_durchschnitt_ohne

print(f"\nDurchschnitt aller Viertelstunden zwischen 12:00-14:00 Uhr:")
print(f"  MIT Lastprofil:  {mittag_durchschnitt_mit:.2f} MWh")
print(f"  OHNE Lastprofil: {mittag_durchschnitt_ohne:.2f} MWh")
print(f"  Differenz:       {mittag_differenz:+.2f} MWh ({mittag_differenz/mittag_durchschnitt_ohne*100:+.1f}%)")

if mittag_differenz > 0:
    print(f"\n⚠️  FEHLER: Mittagswerte sind HÖHER mit Lastprofil!")
    print(f"   Erwartet wäre NIEDRIGER wegen PV-Erzeugung (Mittagssenke)")
else:
    print(f"\n✓ OK: Mittagswerte sind niedriger mit Lastprofil (PV-Effekt sichtbar)")

print("\n" + "="*80)
print("TEST 6: Morgen/Abend-Peak (07:00-09:00, 18:00-20:00)")
print("="*80)

# Morgen-Peak
df_morgen = df_vergleich[df_vergleich['Zeitpunkt'].dt.hour.isin([7, 8])].copy()
morgen_durchschnitt_mit = df_morgen['MIT_Profil'].mean()
morgen_durchschnitt_ohne = df_morgen['OHNE_Profil'].mean()

# Abend-Peak
df_abend = df_vergleich[df_vergleich['Zeitpunkt'].dt.hour.isin([18, 19])].copy()
abend_durchschnitt_mit = df_abend['MIT_Profil'].mean()
abend_durchschnitt_ohne = df_abend['OHNE_Profil'].mean()

print(f"\nMorgen-Peak (07:00-09:00):")
print(f"  MIT Lastprofil:  {morgen_durchschnitt_mit:.2f} MWh")
print(f"  OHNE Lastprofil: {morgen_durchschnitt_ohne:.2f} MWh")
print(f"  Differenz:       {morgen_durchschnitt_mit - morgen_durchschnitt_ohne:+.2f} MWh")

print(f"\nAbend-Peak (18:00-20:00):")
print(f"  MIT Lastprofil:  {abend_durchschnitt_mit:.2f} MWh")
print(f"  OHNE Lastprofil: {abend_durchschnitt_ohne:.2f} MWh")
print(f"  Differenz:       {abend_durchschnitt_mit - abend_durchschnitt_ohne:+.2f} MWh")

print("\n" + "="*80)
print("ZUSAMMENFASSUNG")
print("="*80)

print(f"\n1. Jahressumme:")
if abs(summe_mit - summe_ohne) / summe_ohne < 0.01:
    print(f"   ✓ Summen sind fast gleich ({abs(summe_mit - summe_ohne) / summe_ohne * 100:.3f}% Abweichung)")
else:
    print(f"   ✗ Summen weichen zu stark ab ({abs(summe_mit - summe_ohne) / summe_ohne * 100:.3f}%)")

print(f"\n2. Verteilung:")
if anzahl_niedriger > 0 and anzahl_hoeher > 0:
    print(f"   ✓ Es gibt höhere UND niedrigere Werte")
else:
    print(f"   ✗ Alle Werte sind nur höher oder nur niedriger")

print(f"\n3. Mittagssenke:")
if mittag_differenz < 0:
    print(f"   ✓ Mittagswerte sind niedriger (PV-Effekt)")
else:
    print(f"   ✗ Mittagswerte sind höher (sollte niedriger sein!)")

print("\n" + "="*80)
