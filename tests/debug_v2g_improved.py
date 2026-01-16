"""
Verbesserter Test: Stelle sicher, dass discharge_limit der limitierende Faktor ist.
"""
import sys
sys.path.insert(0, 'source-code')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.e_mobility_simulation import (
    EVScenarioParams,
    EVConfigParams,
    simulate_emobility_fleet,
)

def test_discharge_limit_is_limiting():
    """
    Test, bei dem das discharge_limit definitiv der limitierende Faktor ist.
    
    Strategie: Sehr hohes Netzdefizit + viel Energie in Batterien
    So wird das discharge_limit zum Engpass.
    """
    
    print("="*70)
    print("TEST: discharge_limit als limitierender Faktor")
    print("="*70)
    
    # Erstelle Testdaten mit EXTREM hohem Defizit
    n_steps = 96
    start_time = datetime(2030, 6, 15, 0, 0)
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_steps)]
    
    df = pd.DataFrame({
        'Zeitpunkt': timestamps,
        'Rest Bilanz [MWh]': [0.0] * n_steps
    })
    
    # Extremes Defizit: 100.000 MW = 25.000 MWh pro 15 min
    for i in range(n_steps):
        hour = (i * 15) // 60
        if hour >= 18 or hour < 7:
            df.loc[i, 'Rest Bilanz [MWh]'] = 25000.0  # 100.000 MW Defizit!
    
    # Config mit hohem Initial-SOC
    config = EVConfigParams(SOC0=0.9)  # 90% voll am Start
    
    # Parameter für große Flotte
    base_params = {
        's_EV': 0.9,           # 90% E-Autos
        'N_cars': 10_000_000,  # 10 Mio Fahrzeuge
        'plug_share_max': 0.7, # 70% angeschlossen
        'E_batt_car': 60.0,    # 60 kWh Batterie
        'thr_deficit': 1_000.0,  # 1 MW Schwelle (sehr niedrig!)
        'SOC_min_night': 0.1,    # Min 10% nachts
    }
    
    n_ev = base_params['s_EV'] * base_params['N_cars']
    plug_share = base_params['plug_share_max']
    P_dis_max = config.P_dis_car_max
    
    # Berechne verfügbare Energie (sollte NICHT der Engpass sein)
    capacity_kwh = n_ev * base_params['E_batt_car']
    available_energy = (config.SOC0 - base_params['SOC_min_night']) * capacity_kwh
    available_power_mw = (available_energy * config.eta_dis) / (config.dt_h) / 1000
    
    print(f"\nFlotten-Konfiguration:")
    print(f"  n_ev = {n_ev:,.0f}")
    print(f"  Batteriekapazität = {capacity_kwh/1e6:,.1f} GWh")
    print(f"  Verfügbare Energie (80% des Speichers): {available_energy/1e6:,.1f} GWh")
    print(f"  Verfügbare Entladeleistung: {available_power_mw:,.0f} MW")
    print(f"\n  Netzdefizit pro Zeitschritt: 100.000 MW")
    
    results = {}
    
    for v2g in [1.0, 0.5, 0.3]:
        scenario = EVScenarioParams(**base_params, v2g_share=v2g)
        
        # Erwartetes discharge_limit
        discharge_limit_mw = plug_share * n_ev * P_dis_max * v2g / 1000
        
        print(f"\n--- v2g_share = {v2g} ---")
        print(f"  Erwartetes discharge_limit: {discharge_limit_mw:,.0f} MW")
        
        result = simulate_emobility_fleet(df.copy(), scenario, config)
        
        # Nur den ERSTEN Nacht-Zeitschritt analysieren (wenn Batterie voll)
        night_idx = 72  # 18:00
        first_power = result.iloc[night_idx]['EMobility Power [MW]']
        max_power = result['EMobility Power [MW]'].max()
        
        print(f"  Tatsächliche Leistung bei 18:00: {first_power:,.0f} MW")
        print(f"  Max Entladeleistung gesamt: {max_power:,.0f} MW")
        
        results[v2g] = {
            'expected': discharge_limit_mw,
            'actual': first_power,
            'max': max_power
        }
        
        # Prüfe ob discharge_limit der Engpass ist
        if abs(first_power - discharge_limit_mw) < 100:  # 100 MW Toleranz
            print(f"  ✅ Leistung entspricht discharge_limit (Differenz: {abs(first_power - discharge_limit_mw):.0f} MW)")
        else:
            print(f"  ⚠️  Leistung weicht ab von discharge_limit (Differenz: {abs(first_power - discharge_limit_mw):.0f} MW)")
    
    # Vergleiche die Verhältnisse
    print("\n" + "="*70)
    print("VERHÄLTNIS-ANALYSE")
    print("="*70)
    
    ratio_05_to_10 = results[0.5]['actual'] / results[1.0]['actual']
    ratio_03_to_10 = results[0.3]['actual'] / results[1.0]['actual']
    
    print(f"\nLeistung(v2g=0.5) / Leistung(v2g=1.0) = {ratio_05_to_10:.2f} (erwartet: 0.50)")
    print(f"Leistung(v2g=0.3) / Leistung(v2g=1.0) = {ratio_03_to_10:.2f} (erwartet: 0.30)")
    
    # Erfolgs-Prüfung
    success = True
    if abs(ratio_05_to_10 - 0.5) < 0.05:
        print("✅ v2g_share=0.5 korrekt implementiert")
    else:
        print("❌ v2g_share=0.5 NICHT korrekt")
        success = False
        
    if abs(ratio_03_to_10 - 0.3) < 0.05:
        print("✅ v2g_share=0.3 korrekt implementiert")
    else:
        print("❌ v2g_share=0.3 NICHT korrekt")
        success = False
    
    return success


if __name__ == "__main__":
    test_discharge_limit_is_limiting()
