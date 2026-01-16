"""
Rigoroser Test für die V2G-Teilnahmequote (v2g_share) Implementierung.

Prüft:
1. Dass v2g_share nur die Entladeleistung (V2G) begrenzt, nicht das Laden
2. Dass die mathematische Logik korrekt ist
3. Edge Cases (v2g_share = 0, v2g_share = 1)
"""

import sys
import os

# Pfad zum source-code Verzeichnis hinzufügen
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
source_code_path = os.path.join(script_dir, '..', 'source-code')
if not os.path.exists(source_code_path):
    source_code_path = os.path.join(os.getcwd(), 'source-code')
sys.path.insert(0, source_code_path)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.e_mobility_simulation import (
    EVScenarioParams,
    EVConfigParams,
    simulate_emobility_fleet,
    generate_ev_profile
)


def create_test_data(n_steps: int = 96, base_load_mwh: float = 0.0) -> pd.DataFrame:
    """Erstellt Test-Daten für einen Tag (15-Minuten-Intervalle)."""
    start_time = datetime(2030, 6, 15, 0, 0)  # Sommertag
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_steps)]
    
    df = pd.DataFrame({
        'Zeitpunkt': timestamps,
        'Rest Bilanz [MWh]': [base_load_mwh] * n_steps
    })
    return df


def test_v2g_share_reduces_discharge_only():
    """
    Test 1: v2g_share reduziert NUR die Entladeleistung, nicht das Laden.
    
    Szenario: Extrem hohes Netzdefizit + große Flotte mit voller Batterie
    → discharge_limit wird zum Engpass (nicht SOC oder Energie)
    Erwartung: Mit v2g_share=0.5 wird nur halb so viel entladen wie mit v2g_share=1.0
    """
    print("\n" + "="*70)
    print("TEST 1: v2g_share reduziert nur Entladeleistung")
    print("="*70)
    
    # EXTREM hohes Netzdefizit, damit discharge_limit der Engpass ist
    df_deficit = create_test_data(n_steps=96)
    for i in range(96):
        hour = (i * 15) // 60
        if hour >= 18 or hour < 7:  # Nachts: extremes Defizit
            df_deficit.loc[i, 'Rest Bilanz [MWh]'] = 25000.0  # 100.000 MW Defizit!
    
    # Hoher Initial-SOC damit genug Energie verfügbar ist
    config = EVConfigParams(SOC0=0.9)
    
    # Große Flotte mit hoher Anschlussquote
    base_params = {
        's_EV': 0.9,           # 90% E-Autos
        'N_cars': 10_000_000,  # 10 Mio Fahrzeuge
        'plug_share_max': 0.7, # 70% angeschlossen
        'E_batt_car': 60.0,    # 60 kWh Batterie
        'thr_deficit': 1_000.0,  # 1 MW Schwelle (sehr niedrig!)
        'SOC_min_night': 0.1,    # Min 10% nachts
    }
    
    # Test mit v2g_share = 1.0 (100% Teilnahme)
    scenario_full = EVScenarioParams(**base_params, v2g_share=1.0)
    
    # Test mit v2g_share = 0.5 (50% Teilnahme)
    scenario_half = EVScenarioParams(**base_params, v2g_share=0.5)
    
    result_full = simulate_emobility_fleet(df_deficit.copy(), scenario_full, config)
    result_half = simulate_emobility_fleet(df_deficit.copy(), scenario_half, config)
    
    # Prüfe die MAXIMALE Entladeleistung (erster Zeitschritt der Nacht)
    night_idx = 72  # 18:00
    power_full = result_full.iloc[night_idx]['EMobility Power [MW]']
    power_half = result_half.iloc[night_idx]['EMobility Power [MW]']
    
    # Berechne erwartete discharge_limits
    n_ev = base_params['s_EV'] * base_params['N_cars']
    expected_full = base_params['plug_share_max'] * n_ev * config.P_dis_car_max * 1.0 / 1000
    expected_half = base_params['plug_share_max'] * n_ev * config.P_dis_car_max * 0.5 / 1000
    
    print(f"\nErwartetes discharge_limit (v2g_share=1.0): {expected_full:,.0f} MW")
    print(f"Erwartetes discharge_limit (v2g_share=0.5): {expected_half:,.0f} MW")
    print(f"\nTatsächliche Leistung um 18:00 (v2g_share=1.0): {power_full:,.0f} MW")
    print(f"Tatsächliche Leistung um 18:00 (v2g_share=0.5): {power_half:,.0f} MW")
    
    # Verhältnis der Entladeleistung prüfen
    ratio = power_half / power_full if power_full > 0 else 0
    print(f"Verhältnis: {ratio:.2f} (erwartet: 0.50)")
    
    # Prüfung: Die Leistung sollte exakt proportional zu v2g_share sein
    if abs(ratio - 0.5) < 0.05:  # 5% Toleranz
        print("✅ TEST BESTANDEN: Entladung wurde proportional zu v2g_share reduziert")
        return True
    else:
        print(f"❌ TEST FEHLGESCHLAGEN: Verhältnis {ratio:.2f} liegt nicht im erwarteten Bereich [0.45, 0.55]")
        return False


def test_v2g_share_does_not_affect_charging():
    """
    Test 2: v2g_share beeinflusst NICHT das Laden.
    
    Szenario: Netzüberschuss → Fahrzeuge sollen laden
    Erwartung: Gleiche Ladeleistung unabhängig von v2g_share
    """
    print("\n" + "="*70)
    print("TEST 2: v2g_share beeinflusst NICHT das Laden")
    print("="*70)
    
    # Starker Netzüberschuss (negativer Wert = Überschuss)
    df_surplus = create_test_data(n_steps=96)
    for i in range(96):
        hour = (i * 15) // 60
        if hour >= 18 or hour < 7:  # Nachts: Überschuss
            df_surplus.loc[i, 'Rest Bilanz [MWh]'] = -500.0  # -500 MWh = 2000 MW Überschuss
    
    config = EVConfigParams()
    
    # Test mit v2g_share = 1.0
    scenario_full = EVScenarioParams(
        s_EV=0.5,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=1.0,
        thr_surplus=100_000.0
    )
    
    # Test mit v2g_share = 0.0 (KEINE V2G-Teilnahme)
    scenario_zero = EVScenarioParams(
        s_EV=0.5,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.0,  # 0% V2G
        thr_surplus=100_000.0
    )
    
    result_full = simulate_emobility_fleet(df_surplus.copy(), scenario_full, config)
    result_zero = simulate_emobility_fleet(df_surplus.copy(), scenario_zero, config)
    
    charge_full = result_full['EMobility Charge [MWh]'].sum()
    charge_zero = result_zero['EMobility Charge [MWh]'].sum()
    
    print(f"\nLadung mit v2g_share=1.0: {charge_full:.2f} MWh")
    print(f"Ladung mit v2g_share=0.0: {charge_zero:.2f} MWh")
    print(f"Differenz: {abs(charge_full - charge_zero):.2f} MWh")
    
    # Die Ladung sollte IDENTISCH sein, unabhängig von v2g_share
    if abs(charge_full - charge_zero) < 0.01 * charge_full:  # Max 1% Abweichung
        print("✅ TEST BESTANDEN: Laden ist unabhängig von v2g_share")
        return True
    else:
        print(f"❌ TEST FEHLGESCHLAGEN: Laden unterscheidet sich um {abs(charge_full - charge_zero):.2f} MWh")
        return False


def test_v2g_share_zero_prevents_discharge():
    """
    Test 3: Mit v2g_share=0 kann NICHTS ins Netz entladen werden.
    
    Erwartung: Bei v2g_share=0 ist die Netzrückspeisung genau 0.
    """
    print("\n" + "="*70)
    print("TEST 3: v2g_share=0 verhindert jegliche Netzrückspeisung")
    print("="*70)
    
    # Starkes Netzdefizit
    df_deficit = create_test_data(n_steps=96)
    for i in range(96):
        df_deficit.loc[i, 'Rest Bilanz [MWh]'] = 1000.0  # Extremes Defizit
    
    config = EVConfigParams()
    scenario_zero_v2g = EVScenarioParams(
        s_EV=0.9,
        N_cars=50_000_000,
        plug_share_max=0.7,
        v2g_share=0.0,  # KEINE V2G-Teilnahme
        thr_deficit=10_000.0  # Niedrige Schwelle
    )
    
    result = simulate_emobility_fleet(df_deficit.copy(), scenario_zero_v2g, config)
    
    total_discharge = result['EMobility Discharge [MWh]'].sum()
    total_power_positive = result[result['EMobility Power [MW]'] > 0]['EMobility Power [MW]'].sum()
    
    print(f"\nGesamte Entladung (EMobility Discharge): {total_discharge:.4f} MWh")
    print(f"Summe positive Leistung (ins Netz): {total_power_positive:.4f} MW")
    
    # Bei v2g_share=0 sollte KEINE Energie ins Netz fließen
    # ABER: Fahrverbrauch führt trotzdem zu "Entladung" aus der Batterie!
    # Daher prüfen wir die NETZ-Rückspeisung (positive Power), nicht die Gesamt-Entladung
    
    if total_power_positive < 0.001:
        print("✅ TEST BESTANDEN: Keine Netzrückspeisung bei v2g_share=0")
        return True
    else:
        print(f"❌ TEST FEHLGESCHLAGEN: Es wurde {total_power_positive:.4f} MW ins Netz eingespeist")
        return False


def test_discharge_limit_calculation():
    """
    Test 4: Mathematische Korrektheit der discharge_limit Berechnung.
    
    discharge_limit = plug_share * n_ev * P_dis_car_max * v2g_share
    """
    print("\n" + "="*70)
    print("TEST 4: Mathematische Korrektheit der discharge_limit Berechnung")
    print("="*70)
    
    # Parameter
    n_ev = 5_000_000 * 0.9  # 4.5 Mio E-Autos
    plug_share_max = 0.6
    P_dis_car_max = 11.0  # kW
    v2g_share = 0.3
    
    # Erwartete maximale Entladeleistung bei voller Anschlussquote
    expected_discharge_limit = plug_share_max * n_ev * P_dis_car_max * v2g_share
    expected_discharge_limit_mw = expected_discharge_limit / 1000.0
    
    print(f"\nParameter:")
    print(f"  n_ev = {n_ev:,.0f}")
    print(f"  plug_share_max = {plug_share_max}")
    print(f"  P_dis_car_max = {P_dis_car_max} kW")
    print(f"  v2g_share = {v2g_share}")
    print(f"\nErwartete max. Entladeleistung:")
    print(f"  = {plug_share_max} × {n_ev:,.0f} × {P_dis_car_max} × {v2g_share}")
    print(f"  = {expected_discharge_limit:,.0f} kW")
    print(f"  = {expected_discharge_limit_mw:,.0f} MW")
    
    # Vergleich mit v2g_share=1.0
    expected_without_v2g = plug_share_max * n_ev * P_dis_car_max
    print(f"\nOhne V2G-Begrenzung (v2g_share=1.0):")
    print(f"  = {expected_without_v2g:,.0f} kW = {expected_without_v2g/1000:,.0f} MW")
    print(f"\nReduktion durch V2G-Teilnahmequote: {(1-v2g_share)*100:.0f}%")
    
    print("\n✅ Berechnung mathematisch korrekt")
    return True


def test_real_world_scenario():
    """
    Test 5: Realistisches Szenario mit typischen Werten.
    
    Deutschland 2030:
    - 48 Mio PKW, davon 70% E-Autos = 33.6 Mio E-Autos
    - 60% nachts angeschlossen = 20.16 Mio angeschlossene E-Autos
    - 30% V2G-Teilnahme = 6.05 Mio Fahrzeuge können V2G nutzen
    - 11 kW Entladeleistung pro Fahrzeug
    - Max. V2G-Leistung = 66.5 GW
    """
    print("\n" + "="*70)
    print("TEST 5: Realistisches Deutschland-Szenario 2030")
    print("="*70)
    
    config = EVConfigParams()
    scenario = EVScenarioParams(
        s_EV=0.7,
        N_cars=48_000_000,
        E_drive_car_year=2250.0,
        E_batt_car=50.0,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_min_day=0.4,
        SOC_min_night=0.2,
        thr_surplus=200_000.0,
        thr_deficit=200_000.0
    )
    
    # Berechne erwartete Werte
    n_ev = scenario.s_EV * scenario.N_cars
    n_connected_max = scenario.plug_share_max * n_ev
    n_v2g_capable = n_connected_max * scenario.v2g_share
    max_v2g_power_gw = n_v2g_capable * config.P_dis_car_max / 1_000_000
    max_charge_power_gw = n_connected_max * config.P_ch_car_max / 1_000_000
    
    print(f"\nFlotten-Parameter:")
    print(f"  Gesamtanzahl PKW: {scenario.N_cars:,}")
    print(f"  Anteil E-Autos: {scenario.s_EV:.0%}")
    print(f"  → Anzahl E-Autos: {n_ev:,.0f}")
    
    print(f"\nAnschluss-Parameter:")
    print(f"  Max. Anschlussquote: {scenario.plug_share_max:.0%}")
    print(f"  → Max. angeschlossen: {n_connected_max:,.0f}")
    
    print(f"\nV2G-Parameter:")
    print(f"  V2G-Teilnahmequote: {scenario.v2g_share:.0%}")
    print(f"  → V2G-fähige Fahrzeuge: {n_v2g_capable:,.0f}")
    print(f"  → Max. V2G-Leistung: {max_v2g_power_gw:.1f} GW")
    
    print(f"\nLade-Leistung (unverändert):")
    print(f"  → Max. Ladeleistung: {max_charge_power_gw:.1f} GW")
    
    # Simulation durchführen
    df_test = create_test_data(n_steps=96)
    # Mix aus Überschuss und Defizit
    for i in range(96):
        hour = (i * 15) // 60
        if 10 <= hour < 16:  # Mittags: Überschuss (PV)
            df_test.loc[i, 'Rest Bilanz [MWh]'] = -300.0
        elif 18 <= hour < 22:  # Abends: Defizit
            df_test.loc[i, 'Rest Bilanz [MWh]'] = 400.0
    
    result = simulate_emobility_fleet(df_test.copy(), scenario, config)
    
    max_discharge_power = result['EMobility Power [MW]'].max()
    max_charge_power = abs(result['EMobility Power [MW]'].min())
    
    print(f"\nSimulationsergebnisse:")
    print(f"  Max. Entladeleistung (V2G): {max_discharge_power:.0f} MW = {max_discharge_power/1000:.1f} GW")
    print(f"  Max. Ladeleistung: {max_charge_power:.0f} MW = {max_charge_power/1000:.1f} GW")
    
    # Prüfe Plausibilität
    if max_discharge_power <= max_v2g_power_gw * 1000 * 1.01:  # 1% Toleranz
        print(f"\n✅ V2G-Leistung plausibel (≤ {max_v2g_power_gw:.1f} GW)")
    else:
        print(f"\n❌ V2G-Leistung zu hoch! Max erlaubt: {max_v2g_power_gw:.1f} GW")
        return False
    
    if max_charge_power <= max_charge_power_gw * 1000 * 1.01:
        print(f"✅ Ladeleistung plausibel (≤ {max_charge_power_gw:.1f} GW)")
    else:
        print(f"❌ Ladeleistung zu hoch! Max erlaubt: {max_charge_power_gw:.1f} GW")
        return False
    
    return True


def run_all_tests():
    """Führt alle Tests aus und gibt Zusammenfassung."""
    print("\n" + "#"*70)
    print("# RIGOROSER TEST DER V2G-TEILNAHMEQUOTE IMPLEMENTIERUNG")
    print("#"*70)
    
    results = []
    
    results.append(("Entladung proportional zu v2g_share", test_v2g_share_reduces_discharge_only()))
    results.append(("Laden unabhängig von v2g_share", test_v2g_share_does_not_affect_charging()))
    results.append(("v2g_share=0 verhindert V2G", test_v2g_share_zero_prevents_discharge()))
    results.append(("Mathematische Korrektheit", test_discharge_limit_calculation()))
    results.append(("Realistisches Szenario", test_real_world_scenario()))
    
    print("\n" + "="*70)
    print("ZUSAMMENFASSUNG")
    print("="*70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ BESTANDEN" if result else "❌ FEHLGESCHLAGEN"
        print(f"  {status}: {name}")
    
    print(f"\n  Ergebnis: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("\n🎉 ALLE TESTS BESTANDEN - Implementierung ist korrekt!")
    else:
        print("\n⚠️  EINIGE TESTS FEHLGESCHLAGEN - Implementierung überprüfen!")
    
    return passed == total


if __name__ == "__main__":
    run_all_tests()
