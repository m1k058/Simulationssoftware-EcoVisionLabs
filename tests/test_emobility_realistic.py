#!/usr/bin/env python3
"""
Test der E-Mobility Simulation mit REALISTISCHEN Szenariodaten.

Dieser Test verwendet die tatsächlichen Szenario-YAML-Dateien und
Simulationsdaten, um die Lade-/Entladelogik unter realen Bedingungen zu prüfen.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import pandas as pd
import numpy as np
from datetime import datetime

from config_manager import ConfigManager
from data_manager import DataManager
from scenario_manager import ScenarioManager
from data_processing.simulation_engine import SimulationEngine


def run_realistic_emobility_test():
    """
    Führt die vollständige Simulation mit echten Szenariodaten aus
    und analysiert das E-Mobility Verhalten.
    """
    print("=" * 70)
    print("REALISTISCHER E-MOBILITY TEST MIT ECHTEN SZENARIODATEN")
    print("=" * 70)
    
    # Projektverzeichnis
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Wechsle ins Projektverzeichnis (für relative Pfade)
    os.chdir(project_dir)
    
    # Manager initialisieren
    cfg = ConfigManager()
    dm = DataManager(cfg)
    sm = ScenarioManager()
    
    # Lade ein realistisches Szenario mit vollständigen E-Mobility-Parametern
    scenario_path = os.path.join("scenarios", "Szenario 2045", "Agora_KN2045_1.0.yaml")
    
    if not os.path.exists(scenario_path):
        print(f"❌ Szenario nicht gefunden: {scenario_path}")
        return False
    
    print(f"\n📂 Lade Szenario: {scenario_path}")
    sm.load_scenario(scenario_path)
    
    # Simulation Engine erstellen
    engine = SimulationEngine(cfg, dm, sm, verbose=True)
    
    # Simulation nur für 2045 ausführen
    print(f"\n🚀 Starte Simulation für Jahr 2045...")
    
    try:
        results = engine.run_scenario(years=[2045])
    except Exception as e:
        print(f"❌ Simulation fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if 2045 not in results:
        print("❌ Keine Ergebnisse für 2045")
        return False
    
    # Ergebnisse analysieren
    result_2045 = results[2045]
    
    # DataFrame mit E-Mobility Daten
    df = result_2045.get("storage", result_2045.get("balance"))
    
    if df is None or 'EMobility Power [MW]' not in df.columns:
        print("❌ Keine E-Mobility Daten in den Ergebnissen")
        print(f"   Verfügbare Spalten: {list(df.columns) if df is not None else 'None'}")
        return False
    
    print("\n" + "=" * 70)
    print("ANALYSE DER E-MOBILITY ERGEBNISSE")
    print("=" * 70)
    
    # Grundlegende Statistiken
    power = df['EMobility Power [MW]'].values
    charge = df['EMobility Charge [MWh]'].values
    discharge = df['EMobility Discharge [MWh]'].values
    soc = df['EMobility SOC [MWh]'].values
    
    print(f"\n📊 Grundstatistiken:")
    print(f"   Zeitschritte: {len(df)}")
    print(f"   Gesamte Ladung: {charge.sum()/1e6:.2f} TWh")
    print(f"   Gesamte Entladung (V2G): {discharge.sum()/1e6:.2f} TWh")
    print(f"   SOC Min: {soc.min():.0f} MWh, Max: {soc.max():.0f} MWh")
    
    # Analyse nach Tageszeit
    print(f"\n⏰ Analyse nach Tageszeit:")
    
    if 'Zeitpunkt' in df.columns:
        df['hour'] = pd.to_datetime(df['Zeitpunkt']).dt.hour
    else:
        df['hour'] = df.index % 96 // 4  # 15-min Schritte -> Stunden
    
    # Lade-Leistung (negativer Power = Laden)
    charging_power = np.where(power < 0, -power, 0)
    discharging_power = np.where(power > 0, power, 0)
    
    # Gruppiere nach Stunde
    hourly_charge = pd.DataFrame({
        'hour': df['hour'],
        'charging': charging_power,
        'discharging': discharging_power
    }).groupby('hour').mean()
    
    print(f"\n   Durchschnittliche Ladeleistung nach Stunde (MW):")
    for hour in [0, 3, 6, 7, 12, 18, 21]:
        if hour in hourly_charge.index:
            ch = hourly_charge.loc[hour, 'charging']
            dis = hourly_charge.loc[hour, 'discharging']
            print(f"   {hour:02d}:00 - Laden: {ch:8.0f} MW, V2G: {dis:8.0f} MW")
    
    # Kritischer Test: Gibt es Morgen-Spitzen (05:30-07:30)?
    print(f"\n🔍 KRITISCHER TEST: Ladespitzen zwischen 05:30-07:30")
    
    morning_mask = (df['hour'] >= 5) & (df['hour'] < 8)
    night_mask = ((df['hour'] >= 18) | (df['hour'] < 5))
    
    morning_charge_avg = charging_power[morning_mask].mean()
    night_charge_avg = charging_power[night_mask].mean()
    morning_charge_max = charging_power[morning_mask].max()
    night_charge_max = charging_power[night_mask].max()
    
    print(f"   Morgen (05-08): Durchschnitt={morning_charge_avg:.0f} MW, Max={morning_charge_max:.0f} MW")
    print(f"   Nacht (18-05):  Durchschnitt={night_charge_avg:.0f} MW, Max={night_charge_max:.0f} MW")
    
    if night_charge_avg > 0:
        ratio = morning_charge_max / max(night_charge_avg, 1)
        print(f"   Spike-Ratio (Morning Max / Night Avg): {ratio:.2f}")
        
        if ratio > 5.0:
            print(f"   ⚠️  WARNUNG: Hoher Spike-Ratio - möglicherweise problematisch")
        else:
            print(f"   ✅ Spike-Ratio akzeptabel")
    else:
        print(f"   ℹ️  Keine Nachtladung - V2G dominiert oder kein Ladebedarf")
    
    # SOC-Verlauf prüfen
    print(f"\n🔋 SOC-Verlauf:")
    
    # Finde Abfahrts-Zeitpunkte (07:30)
    departure_mask = (df['hour'] == 7)
    if departure_mask.any():
        soc_at_departure = soc[departure_mask]
        print(f"   SOC bei Abfahrt (07:00-08:00): Min={soc_at_departure.min():.0f} MWh, "
              f"Max={soc_at_departure.max():.0f} MWh, Avg={soc_at_departure.mean():.0f} MWh")
    
    # Finde Ankunfts-Zeitpunkte (18:00)
    arrival_mask = (df['hour'] == 18)
    if arrival_mask.any():
        soc_at_arrival = soc[arrival_mask]
        print(f"   SOC bei Ankunft (18:00): Min={soc_at_arrival.min():.0f} MWh, "
              f"Max={soc_at_arrival.max():.0f} MWh, Avg={soc_at_arrival.mean():.0f} MWh")
    
    # Residuallast-Analyse (nutze Bilanz VOR E-Mobility für korrekte Interpretation)
    print(f"\n⚡ Residuallast-Analyse:")
    
    # Die 'Bilanz [MWh]' ist die Eingangs-Bilanz VOR E-Mobility
    if 'Bilanz [MWh]' in df.columns:
        residual = df['Bilanz [MWh]'].values
        print(f"   (Bilanz VOR E-Mobility und Speicher)")
        
        # Wie oft Defizit vs Überschuss? (Positive Bilanz = Überschuss!)
        surplus_count = (residual > 0).sum()
        deficit_count = (residual < 0).sum()
        
        print(f"   Zeitschritte mit Überschuss (Bilanz > 0): {surplus_count} ({100*surplus_count/len(df):.1f}%)")
        print(f"   Zeitschritte mit Defizit (Bilanz < 0): {deficit_count} ({100*deficit_count/len(df):.1f}%)")
        
        # Korrelation zwischen Residuallast und E-Mobility Verhalten
        # Bei Überschuss (positiv) sollte GELADEN werden (negativ correlation mit charging)
        # Bei Defizit (negativ) sollte V2G aktiv sein (negativ correlation mit discharging)
        correlation_charge = np.corrcoef(residual, charging_power)[0, 1]
        correlation_discharge = np.corrcoef(residual, discharging_power)[0, 1]
        
        print(f"   Korrelation Bilanz ↔ Laden: {correlation_charge:.3f}")
        print(f"   Korrelation Bilanz ↔ V2G: {correlation_discharge:.3f}")
        
        # Interpretation: 
        # - Positive Korrelation Bilanz-Laden = Laden bei Überschuss ✓
        # - Negative Korrelation Bilanz-V2G = V2G bei Defizit ✓
        if correlation_charge > 0.2:
            print(f"   ✅ Laden reagiert netzdienlich auf Überschuss")
        if correlation_discharge < -0.2:
            print(f"   ✅ V2G reagiert netzdienlich auf Defizit")
    
    # Detaillierte Tagesansicht (ein typischer Tag)
    print(f"\n📅 Detaillierte Ansicht: Tag 100 (Beispiel)")
    day_start = 100 * 96
    day_end = day_start + 96
    
    if day_end <= len(df):
        day_df = df.iloc[day_start:day_end].copy()
        day_power = power[day_start:day_end]
        day_soc = soc[day_start:day_end]
        
        print(f"   Zeitraum: {day_df.iloc[0]['Zeitpunkt'] if 'Zeitpunkt' in day_df.columns else 'Tag 100'}")
        print(f"   SOC Start: {day_soc[0]:.0f} MWh, Ende: {day_soc[-1]:.0f} MWh")
        print(f"   Max Laden: {-min(day_power):.0f} MW")
        print(f"   Max V2G: {max(day_power):.0f} MW")
    
    print("\n" + "=" * 70)
    print("TEST ABGESCHLOSSEN")
    print("=" * 70)
    
    return True


def analyze_specific_days(df, days_to_analyze=[1, 50, 100, 200, 300]):
    """Analysiert spezifische Tage im Detail."""
    print("\n" + "=" * 70)
    print("DETAILANALYSE SPEZIFISCHER TAGE")
    print("=" * 70)
    
    power = df['EMobility Power [MW]'].values
    soc = df['EMobility SOC [MWh]'].values
    
    for day in days_to_analyze:
        start_idx = day * 96
        end_idx = start_idx + 96
        
        if end_idx > len(df):
            continue
        
        day_power = power[start_idx:end_idx]
        day_soc = soc[start_idx:end_idx]
        
        # Finde Stunden
        hours = np.arange(96) * 0.25  # 15-min -> Stunden
        
        # Finde kritische Zeiten
        morning_idx = (hours >= 5.5) & (hours <= 7.5)  # 05:30-07:30
        night_idx = (hours >= 18) | (hours < 5.5)      # 18:00-05:30
        
        morning_charge = -np.minimum(day_power[morning_idx], 0).mean()
        night_charge = -np.minimum(day_power[night_idx], 0).mean()
        
        soc_at_0730 = day_soc[30]  # Index 30 = 07:30
        soc_at_1800 = day_soc[72]  # Index 72 = 18:00
        
        print(f"\n   Tag {day}:")
        print(f"      SOC 07:30: {soc_at_0730:.0f} MWh, SOC 18:00: {soc_at_1800:.0f} MWh")
        print(f"      Avg Laden Morgen: {morning_charge:.0f} MW, Nacht: {night_charge:.0f} MW")


if __name__ == "__main__":
    success = run_realistic_emobility_test()
    sys.exit(0 if success else 1)
