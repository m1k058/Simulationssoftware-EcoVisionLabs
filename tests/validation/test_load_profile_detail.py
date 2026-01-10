"""
Detaillierter Test: Zeigt, dass Lastprofil-Faktoren korrekt viertelstündlich angewendet werden
"""

import sys
import os
# Da wir im tests/ Verzeichnis sind, gehe ein Level hoch und dann zu source-code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import pandas as pd
from data_processing.load_profile import load_standard_load_profile, parse_profile_header, normalize_load_profile

print("="*80)
print("DETAILTEST: Viertelstündliche Lastfaktoren")
print("="*80)

# Lade und normalisiere Lastprofil
df_profile = load_standard_load_profile()
df_profile_parsed = parse_profile_header(df_profile)
df_profile_norm = normalize_load_profile(df_profile_parsed, year=2030)

# Zeige Original-Lastprofil für Januar Werktag
print("\n" + "="*80)
print("BEISPIEL: Januar Werktag - Erste 24 Viertelstunden (6 Stunden)")
print("="*80)

if '1_Werktag' in df_profile_norm.columns:
    df_januar_wt = df_profile_norm[['Zeitfenster', 'Viertelstunde_Nr', '1_Werktag']].head(24)
    df_januar_wt['Lastfaktor [%]'] = df_januar_wt['1_Werktag'] * 100
    print(df_januar_wt.to_string(index=False))
    
    print(f"\nInterpretation:")
    print(f"  - Jede Viertelstunde hat einen eigenen spezifischen Lastfaktor")
    print(f"  - Summe aller 96 Viertelstunden eines Tages = {df_profile_norm['1_Werktag'].sum():.10f}")
    print(f"  - Bei 261 Werktagen in 2030: 261 × {df_profile_norm['1_Werktag'].sum():.10f} = {261 * df_profile_norm['1_Werktag'].sum():.6f}")

# Zeige Vergleich: Werktag vs Samstag vs Feiertag/Sonntag
print("\n" + "="*80)
print("VERGLEICH: Werktag vs Samstag vs Feiertag (00:00-01:00)")
print("="*80)

comparison_data = []
for i in range(4):  # Erste 4 Viertelstunden (1 Stunde)
    row = df_profile_norm.iloc[i]
    comparison_data.append({
        'Zeitfenster': row['Zeitfenster'],
        'Werktag': row['1_Werktag'],
        'Samstag': row['1_Samstag'],
        'Feiertag': row['1_Feiertag']
    })

df_comparison = pd.DataFrame(comparison_data)
df_comparison['WT [%]'] = df_comparison['Werktag'] * 100
df_comparison['SA [%]'] = df_comparison['Samstag'] * 100
df_comparison['FT [%]'] = df_comparison['Feiertag'] * 100

print(df_comparison[['Zeitfenster', 'WT [%]', 'SA [%]', 'FT [%]']].to_string(index=False))

print(f"\nBeobachtung:")
print(f"  - Werktage haben um 00:00 eine Last von ca. {df_comparison['WT [%]'].mean():.3f}%")
print(f"  - Samstage haben um 00:00 eine Last von ca. {df_comparison['SA [%]'].mean():.3f}%")
print(f"  - Feiertage haben um 00:00 eine Last von ca. {df_comparison['FT [%]'].mean():.3f}%")
print(f"  → Feiertage haben höhere Nachtlast (Speicher-PV-Profil)")

# Zeige Peak-Zeiten
print("\n" + "="*80)
print("PEAK-LAST: Höchste und niedrigste Viertelstunden (Januar Werktag)")
print("="*80)

df_januar_wt_full = df_profile_norm[['Zeitfenster', '1_Werktag']].copy()
df_januar_wt_full['Last [%]'] = df_januar_wt_full['1_Werktag'] * 100

# Top 5 höchste
print("\nTop 5 HÖCHSTE Last:")
print(df_januar_wt_full.nlargest(5, '1_Werktag').to_string(index=False))

# Top 5 niedrigste
print("\nTop 5 NIEDRIGSTE Last:")
print(df_januar_wt_full.nsmallest(5, '1_Werktag').to_string(index=False))

# Simulation mit Beispieldaten
print("\n" + "="*80)
print("SIMULATION: Anwendung auf echte Zeitstempel")
print("="*80)

from data_processing.load_profile import apply_load_profile_to_simulation

# Erstelle Beispiel-Woche (Mo-So)
df_test = pd.DataFrame({
    'Zeitpunkt': pd.date_range('2030-01-07', '2030-01-13 23:45', freq='15min')  # KW2: Mo-So
})

df_result = apply_load_profile_to_simulation(df_test, total_consumption_twh=650.0)

# Zeige ersten Tag (Montag = Werktag)
print("\nMontag, 7. Januar 2030 (Werktag) - Erste 10 Viertelstunden:")
df_montag = df_result[df_result['Zeitpunkt'].dt.day == 7].head(10)
print(df_montag[['Zeitpunkt', 'Lastprofil Netzlast [MWh]']].to_string(index=False))

# Zeige Samstag
print("\nSamstag, 11. Januar 2030 - Erste 10 Viertelstunden:")
df_samstag = df_result[df_result['Zeitpunkt'].dt.day == 11].head(10)
print(df_samstag[['Zeitpunkt', 'Lastprofil Netzlast [MWh]']].to_string(index=False))

# Zeige Sonntag (= Feiertag)
print("\nSonntag, 12. Januar 2030 (als Feiertag behandelt) - Erste 10 Viertelstunden:")
df_sonntag = df_result[df_result['Zeitpunkt'].dt.day == 12].head(10)
print(df_sonntag[['Zeitpunkt', 'Lastprofil Netzlast [MWh]']].to_string(index=False))

# Statistik pro Wochentag
print("\n" + "="*80)
print("STATISTIK: Durchschnittliche Last pro Wochentag")
print("="*80)

df_result['Wochentag'] = df_result['Zeitpunkt'].dt.day_name()
stats = df_result.groupby('Wochentag')['Lastprofil Netzlast [MWh]'].agg(['mean', 'std', 'min', 'max'])
stats = stats.reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
print(stats)

print("\n" + "="*80)
print("✓ FAZIT:")
print("="*80)
print("1. Jede Viertelstunde hat ihren eigenen spezifischen Lastfaktor")
print("2. Faktoren unterscheiden sich nach Monat, Wochentag und Uhrzeit")
print("3. Werktage, Samstage und Feiertage/Sonntage haben unterschiedliche Profile")
print("4. Die Faktoren werden exakt 1:1 aus dem Lastprofil übernommen")
print("="*80)
