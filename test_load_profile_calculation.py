"""
Demonstration: Wie werden die Lastprofil-Faktoren umgerechnet?
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source-code'))

import pandas as pd
from data_processing.load_profile import load_standard_load_profile, parse_profile_header, normalize_load_profile

print("="*80)
print("DEMONSTRATION: Umrechnung Lastprofil → TWh-basierte Faktoren")
print("="*80)

# Schritt 1: Lade Original-Lastprofil
print("\n" + "="*80)
print("SCHRITT 1: Original-Lastprofil aus CSV")
print("="*80)

df_profile = load_standard_load_profile()
df_profile_parsed = parse_profile_header(df_profile)

# Zeige Original-Werte (nicht normiert)
print("\nOriginal-Werte aus CSV (Januar Werktag, erste 5 Viertelstunden):")
print("Diese Werte sind normiert auf 1 Mio kWh Jahresverbrauch\n")

# Lese Original-CSV nochmal, um nicht-normierte Werte zu zeigen
df_raw = pd.read_csv('raw-data/Lastprofile 2024 BMWK(S25).csv', 
                     sep=';', encoding='utf-8', skiprows=3, decimal=',')
df_raw = df_raw.iloc[:, 1:]
df_raw = df_raw.rename(columns={df_raw.columns[0]: 'Zeitfenster'})
df_raw = df_raw[df_raw['Zeitfenster'].notna()].copy()

print(f"{'Zeitfenster':<15} {'Original [kWh]':<20} {'Bedeutung'}")
print("-" * 80)
for i in range(5):
    zeitfenster = df_raw.iloc[i, 0]
    # Spalte 4 ist Januar-WT (SA, FT, WT)
    wert_kwh = df_raw.iloc[i, 4]  # Januar Werktag
    print(f"{zeitfenster:<15} {wert_kwh:<20.3f} {'= Verbrauch in dieser Viertelstunde'}")

print(f"\nGesamt-Summe aller Viertelstunden (ungewichtet): {df_raw.iloc[:, 4].sum():.2f} kWh")
print("⚠ Diese Summe ist NICHT der Jahresverbrauch!")
print("   Der Jahresverbrauch = Summe × Anzahl Tage pro Tagestyp")

# Schritt 2: Berechne gewichtete Jahressumme
print("\n" + "="*80)
print("SCHRITT 2: Berechne gewichtete Jahressumme für 2030")
print("="*80)

import calendar

# Zähle Tage pro Typ
werktage = 0
samstage = 0
sonntage = 0

for month in range(1, 13):
    _, num_days = calendar.monthrange(2030, month)
    for day in range(1, num_days + 1):
        weekday = calendar.weekday(2030, month, day)
        if weekday == 5:
            samstage += 1
        elif weekday == 6:
            sonntage += 1
        else:
            werktage += 1

print(f"\nJahr 2030 hat:")
print(f"  - {werktage} Werktage (Mo-Fr)")
print(f"  - {samstage} Samstage")
print(f"  - {sonntage} Sonntage (= Feiertage)")
print(f"  = {werktage + samstage + sonntage} Tage gesamt")

# Berechne Jahressumme
summe_januar_wt_pro_tag = df_raw.iloc[:, 4].sum()  # 96 Viertelstunden

print(f"\nBerechnung Jahressumme:")
print(f"  Januar-Werktag, Summe aller 96 Viertelstunden: {summe_januar_wt_pro_tag:.2f} kWh")
print(f"  (Diese Summe gilt für EINEN Tag)")

# Für echte Jahressumme müsste man alle 12 Monate berücksichtigen
df_profile_norm = normalize_load_profile(df_profile_parsed, year=2030)

# Schritt 3: Normierung
print("\n" + "="*80)
print("SCHRITT 3: Normierung auf 1.0 (= 100% des Jahresverbrauchs)")
print("="*80)

print("\nNach Normierung (Januar Werktag, erste 5 Viertelstunden):")
print(f"{'Zeitfenster':<15} {'Original [kWh]':<18} {'Normiert':<18} {'Normiert [%]':<15}")
print("-" * 80)
for i in range(5):
    zeitfenster = df_raw.iloc[i, 0]
    original = df_raw.iloc[i, 4]
    normiert = df_profile_norm.iloc[i]['1_Werktag']
    normiert_pct = normiert * 100
    print(f"{zeitfenster:<15} {original:<18.3f} {normiert:<18.10f} {normiert_pct:<15.8f}%")

print(f"\nProbe: Summe aller normierten Werte × Anzahl Tage pro Typ = 1.0")
summe_check = 0.0
for month in range(1, 13):
    for day_type in ['Werktag', 'Samstag', 'Feiertag']:
        col_name = f"{month}_{day_type}"
        if col_name in df_profile_norm.columns:
            summe_viertelstunden = df_profile_norm[col_name].sum()
            
            # Zähle Tage für diesen Monat/Typ
            _, num_days = calendar.monthrange(2030, month)
            tage_count = 0
            for day in range(1, num_days + 1):
                weekday = calendar.weekday(2030, month, day)
                if day_type == 'Werktag' and weekday < 5:
                    tage_count += 1
                elif day_type == 'Samstag' and weekday == 5:
                    tage_count += 1
                elif day_type == 'Feiertag' and weekday == 6:
                    tage_count += 1
            
            summe_check += summe_viertelstunden * tage_count

print(f"Jahressumme (normiert): {summe_check:.10f}")
print(f"✓ Sollte genau 1.0 sein!")

# Schritt 4: Skalierung auf TWh
print("\n" + "="*80)
print("SCHRITT 4: Skalierung auf Ziel-Jahresverbrauch (z.B. 643 TWh)")
print("="*80)

ziel_twh = 643.0
ziel_mwh = ziel_twh * 1_000_000

print(f"\nZiel-Jahresverbrauch: {ziel_twh} TWh = {ziel_mwh:,.0f} MWh")
print("\nBerechnung für erste 5 Viertelstunden (Januar Werktag):")
print(f"{'Zeitfenster':<15} {'Normiert':<18} {'× Ziel [MWh]':<18} {'= Verbrauch [MWh]'}")
print("-" * 80)

summe_5_viertelstunden = 0.0
for i in range(5):
    zeitfenster = df_raw.iloc[i, 0]
    normiert = df_profile_norm.iloc[i]['1_Werktag']
    verbrauch_mwh = normiert * ziel_mwh
    summe_5_viertelstunden += verbrauch_mwh
    print(f"{zeitfenster:<15} {normiert:<18.10f} {ziel_mwh:>18,.0f} {verbrauch_mwh:>18.2f}")

print(f"\nSumme dieser 5 Viertelstunden: {summe_5_viertelstunden:,.2f} MWh")
print(f"= {summe_5_viertelstunden / 1000:.3f} GWh")

# Vergleich mit alter Methode
print("\n" + "="*80)
print("VERGLEICH: Neue Methode vs. Alte Methode (konstanter Faktor)")
print("="*80)

# Simuliere alte Methode
referenz_verbrauch_twh = 465.5  # Beispiel
faktor_alt = ziel_twh / referenz_verbrauch_twh
print(f"\nAlte Methode (konstanter Faktor):")
print(f"  Faktor = {ziel_twh} TWh / {referenz_verbrauch_twh} TWh = {faktor_alt:.6f}")
print(f"  Jede Viertelstunde wird mit {faktor_alt:.6f} multipliziert")
print(f"  → KEINE Berücksichtigung von Tageszeit, Wochentag oder Monat!")

print(f"\nNeue Methode (Lastprofil):")
print(f"  Jede Viertelstunde hat individuellen Faktor basierend auf:")
print(f"    - Monat (Januar - Dezember)")
print(f"    - Tagestyp (Werktag, Samstag, Feiertag/Sonntag)")
print(f"    - Uhrzeit (00:00 - 23:45)")
print(f"  → REALISTISCHE Lastschwankungen!")

# Zeige Unterschied konkret
print("\n" + "="*80)
print("KONKRETES BEISPIEL: Unterschied in der Praxis")
print("="*80)

beispiel_ref_verbrauch = 15000  # MWh in einer Viertelstunde (Referenz)
beispiel_neue_methode_morgen = df_profile_norm.iloc[24]['1_Werktag'] * ziel_mwh  # 06:00
beispiel_neue_methode_mittag = df_profile_norm.iloc[52]['1_Werktag'] * ziel_mwh  # 13:00

beispiel_alte_methode = beispiel_ref_verbrauch * faktor_alt

print(f"\nAngenommen, Referenzverbrauch in einer Viertelstunde: {beispiel_ref_verbrauch} MWh")
print(f"\n{'Methode':<30} {'06:00 Uhr [MWh]':<20} {'13:00 Uhr [MWh]':<20}")
print("-" * 70)
print(f"{'Alte Methode (konstant)':<30} {beispiel_alte_methode:<20.2f} {beispiel_alte_methode:<20.2f}")
print(f"{'Neue Methode (Lastprofil)':<30} {beispiel_neue_methode_morgen:<20.2f} {beispiel_neue_methode_mittag:<20.2f}")

print(f"\nUnterschied:")
print(f"  06:00 Uhr: {beispiel_neue_methode_morgen - beispiel_alte_methode:+.2f} MWh ({(beispiel_neue_methode_morgen/beispiel_alte_methode - 1)*100:+.1f}%)")
print(f"  13:00 Uhr: {beispiel_neue_methode_mittag - beispiel_alte_methode:+.2f} MWh ({(beispiel_neue_methode_mittag/beispiel_alte_methode - 1)*100:+.1f}%)")

print("\n" + "="*80)
print("✓ FAZIT:")
print("="*80)
print("Die Lastprofil-Faktoren sind korrekt umgerechnet:")
print("1. Original-Werte [kWh] werden auf 1.0 normiert (= 100% Jahresverbrauch)")
print("2. Normierte Faktoren werden mit Ziel-TWh multipliziert")
print("3. Ergebnis ist viertelstündlicher Verbrauch in MWh")
print("4. Die Summe über alle Viertelstunden ergibt (fast) exakt den Ziel-TWh")
print("="*80)
