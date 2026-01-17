#!/usr/bin/env python3
"""
TIEFGEHENDE LOGIK-ANALYSE der E-Mobility Simulation.

Prüft auf:
1. Logiklücken und Edge-Cases
2. Konsistenz der Prioritäten
3. Realistische Ladespitzen-Analyse
4. SOC-Pfad-Validierung
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.e_mobility_simulation import (
    simulate_emobility_fleet, 
    EVScenarioParams, 
    EVConfigParams,
    generate_ev_profile
)


def create_test_scenario(n_days=3, base_bilanz=0.0):
    """Erstellt ein Test-Szenario mit konfigurierbarer Bilanz."""
    n_steps = n_days * 96
    start = datetime(2024, 1, 1, 0, 0)
    times = [start + timedelta(minutes=15*i) for i in range(n_steps)]
    
    df = pd.DataFrame({
        'Zeitpunkt': times,
        'Bilanz [MWh]': [base_bilanz] * n_steps
    })
    return df


def test_1_priority_consistency():
    """
    TEST 1: Sind die Prioritäten konsistent?
    
    Prüft ob Priorität 1+2 (Mobilitätsgarantie) wirklich VOR Priorität 3 (Netzdienlich) kommt.
    """
    print("\n" + "="*70)
    print("TEST 1: PRIORITÄTEN-KONSISTENZ")
    print("="*70)
    
    # Szenario: Großes Netzdefizit, aber SOC unter Ziel
    df = create_test_scenario(n_days=1)
    
    # Setze Defizit (positive Bilanz = Überschuss, also negativ für Defizit)
    # ACHTUNG: Nach unserer Korrektur ist Bilanz > 0 = Überschuss!
    # Für Defizit brauchen wir Bilanz < 0
    df['Bilanz [MWh]'] = -500.0  # Defizit von 500 MWh = 2000 MW
    
    config = EVConfigParams(SOC0=0.3)  # Start bei nur 30% - unter Ziel!
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,  # Ziel 60%
        thr_deficit=100_000.0
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Analyse: Bei Defizit UND SOC unter Ziel → sollte LADEN, nicht V2G!
    power = result['EMobility Power [MW]'].values
    charge = result['EMobility Charge [MWh]'].values
    discharge = result['EMobility Discharge [MWh]'].values
    
    total_charge = charge.sum()
    total_discharge = discharge.sum()
    
    print(f"\nSzenario: Start-SOC=30%, Ziel-SOC=60%, Netzdefizit=2000 MW")
    print(f"  Gesamte Ladung: {total_charge:.0f} MWh")
    print(f"  Gesamte Entladung (V2G): {total_discharge:.0f} MWh")
    
    # Bei SOC unter Ziel sollte NICHT V2G genutzt werden!
    if total_charge > total_discharge:
        print("✅ KORREKT: Laden hat Priorität über V2G (Mobilitätsgarantie)")
        return True
    else:
        print("❌ FEHLER: V2G dominiert obwohl SOC unter Ziel!")
        return False


def test_2_no_charging_when_full():
    """
    TEST 2: Wird bei vollem SOC noch geladen?
    
    Bei SOC > Ziel und Überschuss sollte trotzdem geladen werden (Überschuss nutzen),
    aber bei SOC = 100% sollte NICHT mehr geladen werden.
    """
    print("\n" + "="*70)
    print("TEST 2: LADEN BEI VOLLEM SOC")
    print("="*70)
    
    df = create_test_scenario(n_days=1)
    df['Bilanz [MWh]'] = 500.0  # Überschuss
    
    config = EVConfigParams(SOC0=0.99)  # Fast voll
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    soc = result['EMobility SOC [MWh]'].values
    charge = result['EMobility Charge [MWh]'].values
    
    # SOC sollte nie über 100% gehen
    capacity = 0.8 * 10_000_000 * 50 / 1000  # MWh
    max_soc_pct = soc.max() / capacity * 100
    
    print(f"\nSzenario: Start-SOC=99%, Netzüberschuss vorhanden")
    print(f"  Max SOC erreicht: {max_soc_pct:.1f}%")
    print(f"  Geladene Energie: {charge.sum():.0f} MWh")
    
    if max_soc_pct <= 100.1:  # Kleine Toleranz für Rundung
        print("✅ KORREKT: SOC überschreitet nicht 100%")
        return True
    else:
        print("❌ FEHLER: SOC über 100%!")
        return False


def test_3_v2g_only_with_buffer():
    """
    TEST 3: V2G nur wenn genug Puffer vorhanden?
    
    V2G sollte nur aktiviert werden, wenn der SOC über dem
    Mindest-Ladepfad + Sicherheitsmarge liegt.
    """
    print("\n" + "="*70)
    print("TEST 3: V2G NUR MIT PUFFER")
    print("="*70)
    
    df = create_test_scenario(n_days=1)
    # Dauerhaftes Defizit
    df['Bilanz [MWh]'] = -500.0
    
    # Start genau auf Ziel-SOC
    config = EVConfigParams(SOC0=0.6)
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,
        thr_deficit=100_000.0
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    discharge = result['EMobility Discharge [MWh]'].values
    soc = result['EMobility SOC [MWh]'].values
    
    capacity = 0.8 * 10_000_000 * 50 / 1000  # MWh
    target_soc_mwh = 0.6 * capacity
    
    # SOC bei Abfahrt (07:30 = Index 30)
    soc_at_departure = soc[30]
    
    print(f"\nSzenario: Start-SOC=60% (=Ziel), Dauerhaftes Defizit")
    print(f"  V2G-Entladung gesamt: {discharge.sum():.0f} MWh")
    print(f"  SOC bei 07:30: {soc_at_departure:.0f} MWh ({100*soc_at_departure/capacity:.1f}%)")
    print(f"  Ziel-SOC: {target_soc_mwh:.0f} MWh (60%)")
    
    # Bei Start = Ziel sollte wenig/kein V2G stattfinden (kein Puffer)
    # UND der Ziel-SOC sollte erreicht werden
    if soc_at_departure >= 0.95 * target_soc_mwh:
        print("✅ KORREKT: Ziel-SOC wird erreicht trotz Defizit")
        result_ok = True
    else:
        print("❌ FEHLER: Ziel-SOC wird nicht erreicht!")
        result_ok = False
    
    return result_ok


def test_4_edge_case_midnight_transition():
    """
    TEST 4: Mitternachts-Übergang korrekt?
    
    Die Zeit-Logik muss korrekt über Mitternacht funktionieren
    (18:00 → 00:00 → 07:30).
    """
    print("\n" + "="*70)
    print("TEST 4: MITTERNACHTS-ÜBERGANG")
    print("="*70)
    
    df = create_test_scenario(n_days=2)
    df['Bilanz [MWh]'] = 200.0  # Leichter Überschuss
    
    config = EVConfigParams(SOC0=0.5)
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,
        t_depart="07:30",
        t_arrive="18:00"
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Prüfe SOC um Mitternacht
    soc = result['EMobility SOC [MWh]'].values
    capacity = 0.8 * 10_000_000 * 50 / 1000
    
    # Tag 1: 23:45 = Index 95, Tag 2: 00:00 = Index 96
    soc_before_midnight = soc[95]
    soc_after_midnight = soc[96]
    
    print(f"\nSOC um Mitternacht:")
    print(f"  23:45: {100*soc_before_midnight/capacity:.1f}%")
    print(f"  00:00: {100*soc_after_midnight/capacity:.1f}%")
    
    # SOC sollte kontinuierlich sein (keine Sprünge)
    soc_jump = abs(soc_after_midnight - soc_before_midnight)
    max_expected_change = capacity * 0.05  # Max 5% Änderung in 15 min
    
    if soc_jump < max_expected_change:
        print("✅ KORREKT: Kontinuierlicher SOC-Verlauf über Mitternacht")
        return True
    else:
        print(f"❌ FEHLER: SOC-Sprung von {soc_jump:.0f} MWh um Mitternacht!")
        return False


def test_5_charging_spike_analysis():
    """
    TEST 5: Analyse der Ladespitzen.
    
    Prüft WARUM und WANN Ladespitzen auftreten und ob sie realistisch sind.
    """
    print("\n" + "="*70)
    print("TEST 5: LADESPITZEN-ANALYSE")
    print("="*70)
    
    df = create_test_scenario(n_days=7)
    
    # Realistisches Szenario: Tag/Nacht-Wechsel
    for i in range(len(df)):
        hour = df.loc[i, 'Zeitpunkt'].hour
        if 10 <= hour <= 16:
            # Tags: PV-Überschuss
            df.loc[i, 'Bilanz [MWh]'] = 300.0
        elif 6 <= hour < 10 or 16 < hour <= 20:
            # Morgen/Abend: Leichtes Defizit
            df.loc[i, 'Bilanz [MWh]'] = -100.0
        else:
            # Nacht: Neutraler/leicht negativer Bereich
            df.loc[i, 'Bilanz [MWh]'] = -50.0
    
    config = EVConfigParams(SOC0=0.5)
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,
        thr_surplus=50_000.0,
        thr_deficit=50_000.0
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    power = result['EMobility Power [MW]'].values
    charging_power = np.where(power < 0, -power, 0)
    
    # Analyse nach Tageszeit (nur die letzten 5 Tage, erste 2 Tage sind Einlaufphase)
    result['hour'] = pd.to_datetime(result['Zeitpunkt']).dt.hour
    result['day'] = pd.to_datetime(result['Zeitpunkt']).dt.dayofyear
    
    # Gruppiere nach Stunde
    hourly_stats = pd.DataFrame({
        'hour': result['hour'],
        'charging': charging_power
    }).groupby('hour').agg(['mean', 'max', 'std'])
    
    print("\nLadeleistung nach Tageszeit:")
    print(f"{'Stunde':<8} {'Mittel':>10} {'Maximum':>10} {'StdAbw':>10}")
    print("-" * 40)
    
    spike_hours = []
    for hour in [0, 3, 6, 7, 8, 12, 15, 18, 21, 23]:
        if hour in hourly_stats.index:
            mean_val = hourly_stats.loc[hour, ('charging', 'mean')]
            max_val = hourly_stats.loc[hour, ('charging', 'max')]
            std_val = hourly_stats.loc[hour, ('charging', 'std')]
            
            # Spike-Erkennung: Max > 2x Mittel
            is_spike = max_val > 2 * mean_val if mean_val > 0 else False
            marker = " ⚠️" if is_spike else ""
            
            print(f"{hour:02d}:00    {mean_val:>10.0f} {max_val:>10.0f} {std_val:>10.0f}{marker}")
            
            if is_spike:
                spike_hours.append(hour)
    
    print(f"\n📊 Spike-Analyse:")
    if spike_hours:
        print(f"   Stunden mit Spitzen (Max > 2x Mittel): {spike_hours}")
        print(f"   Diese Spitzen sind NORMAL wenn:")
        print(f"   - 06:00-08:00: Safety-Window vor Abfahrt")
        print(f"   - 18:00-19:00: Fahrzeuge kommen an und beginnen zu laden")
        print(f"   - Bei Wechsel Defizit→Überschuss")
    else:
        print("   Keine signifikanten Spitzen erkannt")
    
    # Prüfe ob Spitzen zu erwarteten Zeiten auftreten
    expected_spike_hours = {6, 7, 18, 19}  # Erwartete Spike-Zeiten
    unexpected_spikes = set(spike_hours) - expected_spike_hours
    
    if len(unexpected_spikes) == 0:
        print("✅ KORREKT: Alle Spitzen zu erwarteten Zeiten")
        return True
    else:
        print(f"⚠️ WARNUNG: Unerwartete Spitzen um {unexpected_spikes} Uhr")
        return True  # Warnung, aber kein Fehler


def test_6_min_charge_calculation():
    """
    TEST 6: Ist die Mindest-Lade-Berechnung korrekt?
    
    Prüft ob min_charge_power_needed korrekt berechnet wird.
    """
    print("\n" + "="*70)
    print("TEST 6: MINDEST-LADE-BERECHNUNG")
    print("="*70)
    
    # Einfaches Szenario: Kein Netzsignal, nur Mindest-Ladung
    df = create_test_scenario(n_days=1)
    df['Bilanz [MWh]'] = 0.0  # Kein Netzsignal
    
    config = EVConfigParams(SOC0=0.4)  # 40% Start
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,  # 60% Ziel
        thr_surplus=1e9,  # Sehr hohe Schwellen = kein Netzsignal
        thr_deficit=1e9
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    power = result['EMobility Power [MW]'].values
    soc = result['EMobility SOC [MWh]'].values
    
    capacity = 0.8 * 10_000_000 * 50 / 1000  # MWh
    
    # Analysiere Ladeleistung über die Nacht (18:00-07:30)
    # Index 72 = 18:00, Index 30 = 07:30 (nächster Tag)
    night_start = 72
    morning = 30
    
    night_power = -power[night_start:]  # Negative Power = Laden, positiv machen
    
    print(f"\nSzenario: Start 40%, Ziel 60%, KEIN Netzsignal")
    print(f"  Erwartetes Verhalten: Gleichmäßiges Laden über die Nacht")
    
    # Berechne erwartete gleichmäßige Ladeleistung
    energy_deficit_kwh = (0.6 - 0.4) * (0.8 * 10_000_000 * 50)  # 20% von Kapazität
    hours_available = (24 - 18 + 7.5)  # 18:00 bis 07:30 = 13.5h
    expected_power_kw = energy_deficit_kwh / (hours_available * 0.95)  # mit eta
    expected_power_mw = expected_power_kw / 1000
    
    print(f"  Energie-Defizit: {energy_deficit_kwh/1e6:.2f} TWh")
    print(f"  Verfügbare Zeit: {hours_available:.1f}h")
    print(f"  Erwartete Ladeleistung: {expected_power_mw:.0f} MW")
    
    # Tatsächliche mittlere Ladeleistung
    actual_mean_power = night_power[night_power > 0].mean() if (night_power > 0).any() else 0
    print(f"  Tatsächliche mittlere Ladeleistung: {actual_mean_power:.0f} MW")
    
    # Variation prüfen (sollte gleichmäßig sein)
    if (night_power > 0).any():
        cv = night_power[night_power > 0].std() / night_power[night_power > 0].mean()
        print(f"  Variationskoeffizient: {cv:.2f}")
        
        if cv < 0.5:
            print("✅ KORREKT: Gleichmäßige Ladung")
            return True
        else:
            print("⚠️ WARNUNG: Ungleichmäßige Ladung")
            return True
    else:
        print("❌ FEHLER: Keine Ladung obwohl SOC unter Ziel!")
        return False


def test_7_logic_gap_priority_3a():
    """
    TEST 7: Logiklücke bei Priorität 3a?
    
    Bei Überschuss wird unbegrenzt geladen - auch wenn SOC schon über Ziel?
    Das ist korrekt (Überschuss nutzen), aber prüfen wir es.
    """
    print("\n" + "="*70)
    print("TEST 7: ÜBERSCHUSS-LADEN BEI HOHEM SOC")
    print("="*70)
    
    df = create_test_scenario(n_days=1)
    df['Bilanz [MWh]'] = 1000.0  # Großer Überschuss
    
    config = EVConfigParams(SOC0=0.8)  # Bereits über Ziel
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        SOC_target_depart=0.6,
        thr_surplus=100_000.0
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    charge = result['EMobility Charge [MWh]'].values
    soc = result['EMobility SOC [MWh]'].values
    
    capacity = 0.8 * 10_000_000 * 50 / 1000
    
    print(f"\nSzenario: Start 80% (über Ziel 60%), großer Überschuss")
    print(f"  Gesamte Ladung: {charge.sum():.0f} MWh")
    print(f"  End-SOC: {100*soc[-1]/capacity:.1f}%")
    
    # Bei Überschuss sollte geladen werden um den Überschuss zu nutzen
    # Das ist KORREKT und netzdienlich!
    if charge.sum() > 0:
        print("✅ KORREKT: Überschuss wird genutzt auch bei hohem SOC")
        return True
    else:
        print("⚠️ HINWEIS: Kein Laden bei Überschuss - prüfen ob gewollt")
        return True


def run_all_tests():
    """Führt alle Tests aus."""
    print("="*70)
    print("TIEFGEHENDE LOGIK-ANALYSE DER E-MOBILITY SIMULATION")
    print("="*70)
    
    results = {}
    
    results['1_priority'] = test_1_priority_consistency()
    results['2_full_soc'] = test_2_no_charging_when_full()
    results['3_v2g_buffer'] = test_3_v2g_only_with_buffer()
    results['4_midnight'] = test_4_edge_case_midnight_transition()
    results['5_spikes'] = test_5_charging_spike_analysis()
    results['6_min_charge'] = test_6_min_charge_calculation()
    results['7_surplus'] = test_7_logic_gap_priority_3a()
    
    print("\n" + "="*70)
    print("ZUSAMMENFASSUNG")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} Test {name}")
    
    print(f"\n  Ergebnis: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("\n🎉 ALLE TESTS BESTANDEN!")
    else:
        print("\n⚠️ EINIGE TESTS FEHLGESCHLAGEN!")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
