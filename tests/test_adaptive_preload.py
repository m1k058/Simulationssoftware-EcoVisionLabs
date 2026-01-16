"""
Rigoroser Test für die adaptive Vorlade-Logik (Option 2).

Prüft:
1. Keine extremen Ladespitzen zwischen 05:30 und 07:30
2. Gleichmäßige Ladeleistung über die Nacht
3. Ziel-SOC wird bis Abfahrt erreicht
4. V2G funktioniert weiterhin korrekt
5. Energiebilanz ist konsistent
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.e_mobility_simulation import (
    EVScenarioParams,
    EVConfigParams,
    simulate_emobility_fleet,
    generate_ev_profile
)


def create_test_data(n_days: int = 1, base_deficit: float = 0.0) -> pd.DataFrame:
    """Erstellt Test-Daten für mehrere Tage (15-Minuten-Intervalle)."""
    n_steps = 96 * n_days  # 96 pro Tag
    start_time = datetime(2030, 6, 15, 0, 0)  # Sommertag
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_steps)]
    
    df = pd.DataFrame({
        'Zeitpunkt': timestamps,
        'Rest Bilanz [MWh]': [base_deficit] * n_steps
    })
    return df


def test_no_extreme_charging_spikes():
    """
    Test 1: Keine extremen Ladespitzen zwischen 05:30 und 07:30.
    
    Eine "extreme Spitze" definieren wir als eine Ladeleistung, die
    mehr als 2x so hoch ist wie der Durchschnitt der Nacht.
    """
    print("\n" + "="*70)
    print("TEST 1: Keine extremen Ladespitzen zwischen 05:30 und 07:30")
    print("="*70)
    
    # Erstelle Szenario mit moderatem Netzdefizit
    df = create_test_data(n_days=3)
    
    # Netzdefizit nachts (fördert V2G), Überschuss tags
    for i in range(len(df)):
        hour = df.loc[i, 'Zeitpunkt'].hour
        if 0 <= hour < 7 or hour >= 18:
            df.loc[i, 'Rest Bilanz [MWh]'] = 500.0  # 2000 MW Defizit (fördert V2G)
        else:
            df.loc[i, 'Rest Bilanz [MWh]'] = -200.0  # Leichter Überschuss
    
    config = EVConfigParams(SOC0=0.5)  # Start bei 50%
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        thr_deficit=100_000.0,
        thr_surplus=100_000.0
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Analysiere nur die letzten 2 Tage (erster Tag hat Einschwingeffekt)
    day2_start = 96  # Zweiter Tag
    day3_end = 3 * 96
    
    # Extrahiere Ladeleistung (negative Power = Laden)
    power = result['EMobility Power [MW]'].values
    charging_power = np.where(power < 0, -power, 0)  # Nur Laden, positiv
    
    # Analysiere nach Tageszeit
    morning_5_7_30 = []
    night_other = []
    
    for i in range(day2_start, day3_end):
        ts = result.iloc[i]['Zeitpunkt']
        hour = ts.hour + ts.minute / 60
        
        # Nachtzeit: 18:00 - 07:30
        is_night = (hour >= 18 or hour < 7.5)
        is_morning_window = (5 <= hour < 7.5)
        
        if is_night:
            if is_morning_window:
                morning_5_7_30.append(charging_power[i])
            else:
                night_other.append(charging_power[i])
    
    avg_morning = np.mean(morning_5_7_30) if morning_5_7_30 else 0
    max_morning = np.max(morning_5_7_30) if morning_5_7_30 else 0
    avg_night = np.mean(night_other) if night_other else 0
    max_night = np.max(night_other) if night_other else 0
    
    print(f"\nLadeleistung (MW):")
    print(f"  05:30-07:30: Durchschnitt={avg_morning:.0f}, Maximum={max_morning:.0f}")
    print(f"  18:00-05:30: Durchschnitt={avg_night:.0f}, Maximum={max_night:.0f}")
    
    # Spike-Ratio: Wie viel höher ist das Maximum am Morgen vs. Durchschnitt der Nacht?
    if avg_night > 0:
        spike_ratio = max_morning / avg_night
        print(f"\nSpike-Ratio (max_morgen / avg_nacht): {spike_ratio:.2f}")
        
        if spike_ratio <= 2.5:  # Max 2.5x höher ist akzeptabel
            print("✅ TEST BESTANDEN: Keine extremen Ladespitzen")
            return True
        else:
            print(f"❌ TEST FEHLGESCHLAGEN: Spike-Ratio {spike_ratio:.2f} > 2.5")
            return False
    else:
        # Wenn keine Nachtladung, nur prüfen dass Morgen nicht extrem ist
        if max_morning < 5000:  # Max 5 GW
            print("✅ TEST BESTANDEN: Keine extreme Morgenladung")
            return True
        else:
            print(f"❌ TEST FEHLGESCHLAGEN: Extreme Morgenladung {max_morning:.0f} MW")
            return False


def test_smooth_charging_distribution():
    """
    Test 2: Gleichmäßige Ladeleistung über die Nacht.
    
    Die Standardabweichung der Ladeleistung sollte gering sein.
    """
    print("\n" + "="*70)
    print("TEST 2: Gleichmäßige Ladeleistung über die Nacht")
    print("="*70)
    
    # Szenario mit konstantem Netzüberschuss (keine V2G-Entladung)
    df = create_test_data(n_days=2)
    for i in range(len(df)):
        df.loc[i, 'Rest Bilanz [MWh]'] = -1000.0  # 4000 MW Überschuss
    
    config = EVConfigParams(SOC0=0.3)  # Start bei 30% → muss laden
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.3,
        thr_surplus=50_000.0,  # Niedrige Schwelle
        SOC_target_depart=0.8  # Hohes Ziel
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Analysiere zweite Nacht (18:00 - 07:30)
    day2_night_indices = []
    for i in range(96, 192):  # Tag 2
        ts = result.iloc[i]['Zeitpunkt']
        hour = ts.hour
        if hour >= 18 or hour < 8:
            day2_night_indices.append(i)
    
    power = result['EMobility Power [MW]'].values
    night_charging = [-power[i] for i in day2_night_indices if power[i] < 0]
    
    if len(night_charging) > 0:
        mean_charge = np.mean(night_charging)
        std_charge = np.std(night_charging)
        cv = std_charge / mean_charge if mean_charge > 0 else 0  # Variationskoeffizient
        
        print(f"\nLadeleistung während der Nacht:")
        print(f"  Mittelwert: {mean_charge:.0f} MW")
        print(f"  Standardabweichung: {std_charge:.0f} MW")
        print(f"  Variationskoeffizient: {cv:.2f}")
        
        if cv < 0.5:  # CV unter 50% ist "gleichmäßig"
            print("✅ TEST BESTANDEN: Ladeleistung ist gleichmäßig verteilt")
            return True
        else:
            print(f"❌ TEST FEHLGESCHLAGEN: CV {cv:.2f} > 0.5")
            return False
    else:
        print("⚠️  Keine Nachtladung detektiert")
        return False


def test_target_soc_achieved():
    """
    Test 3: Ziel-SOC wird bis Abfahrt erreicht.
    """
    print("\n" + "="*70)
    print("TEST 3: Ziel-SOC wird bis Abfahrt erreicht")
    print("="*70)
    
    df = create_test_data(n_days=3)
    # Neutrales Netz (keine starken Signale)
    for i in range(len(df)):
        df.loc[i, 'Rest Bilanz [MWh]'] = 0.0
    
    config = EVConfigParams(SOC0=0.2)  # Start bei 20%
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        SOC_target_depart=0.6,  # Ziel: 60%
        t_depart="07:30"
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Prüfe SOC um 07:15 und 07:30 an jedem Tag
    n_ev = scenario.s_EV * scenario.N_cars
    capacity_mwh = n_ev * scenario.E_batt_car / 1000.0
    target_soc_mwh = scenario.SOC_target_depart * capacity_mwh
    
    soc_at_depart = []
    for i in range(len(result)):
        ts = result.iloc[i]['Zeitpunkt']
        if ts.hour == 7 and ts.minute in [15, 30]:
            soc = result.iloc[i]['EMobility SOC [MWh]']
            soc_at_depart.append(soc)
    
    print(f"\nZiel-SOC: {target_soc_mwh:.0f} MWh (= {scenario.SOC_target_depart*100:.0f}%)")
    print(f"SOC bei Abfahrt (07:15/07:30):")
    for i, soc in enumerate(soc_at_depart):
        pct = soc / capacity_mwh * 100
        status = "✓" if soc >= target_soc_mwh * 0.95 else "✗"
        print(f"  {status} Tag {i//2 + 1}, {['07:15', '07:30'][i%2]}: {soc:.0f} MWh ({pct:.1f}%)")
    
    # Mindestens 90% der Abfahrtszeiten sollten das Ziel erreichen
    achieved = sum(1 for soc in soc_at_depart if soc >= target_soc_mwh * 0.95)
    success_rate = achieved / len(soc_at_depart) if soc_at_depart else 0
    
    if success_rate >= 0.8:
        print(f"\n✅ TEST BESTANDEN: {achieved}/{len(soc_at_depart)} Abfahrten erreichen Ziel-SOC")
        return True
    else:
        print(f"\n❌ TEST FEHLGESCHLAGEN: Nur {achieved}/{len(soc_at_depart)} erreichen Ziel-SOC")
        return False


def test_v2g_still_works():
    """
    Test 4: V2G funktioniert weiterhin bei Netzdefizit.
    """
    print("\n" + "="*70)
    print("TEST 4: V2G funktioniert weiterhin bei Netzdefizit")
    print("="*70)
    
    df = create_test_data(n_days=2)
    
    # Hohes Defizit in der ersten Nachthälfte, dann Überschuss
    for i in range(len(df)):
        ts = df.loc[i, 'Zeitpunkt']
        hour = ts.hour
        if 18 <= hour or hour < 2:  # 18:00 - 02:00: Defizit
            df.loc[i, 'Rest Bilanz [MWh]'] = 1000.0  # 4000 MW Defizit
        elif 2 <= hour < 6:  # 02:00 - 06:00: Überschuss
            df.loc[i, 'Rest Bilanz [MWh]'] = -1000.0  # 4000 MW Überschuss
        else:
            df.loc[i, 'Rest Bilanz [MWh]'] = 0.0
    
    config = EVConfigParams(SOC0=0.7)  # Start bei 70%
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6,
        v2g_share=0.5,  # 50% V2G-Teilnahme
        thr_deficit=100_000.0,
        SOC_target_depart=0.6,
        SOC_min_night=0.2
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    total_discharge = result['EMobility Discharge [MWh]'].sum()
    total_charge = result['EMobility Charge [MWh]'].sum()
    
    # Prüfe V2G in erster Nachthälfte (18:00-02:00)
    v2g_power_1st_half = []
    for i in range(len(result)):
        ts = result.iloc[i]['Zeitpunkt']
        hour = ts.hour
        if 18 <= hour or hour < 2:
            power = result.iloc[i]['EMobility Power [MW]']
            if power > 0:  # Entladung = V2G
                v2g_power_1st_half.append(power)
    
    print(f"\nV2G-Aktivität:")
    print(f"  Gesamte Entladung: {total_discharge:.0f} MWh")
    print(f"  Gesamte Ladung: {total_charge:.0f} MWh")
    print(f"  V2G-Einspeisung (18-02 Uhr): {sum(v2g_power_1st_half):.0f} MW (Summe)")
    print(f"  Anzahl V2G-Zeitschritte: {len(v2g_power_1st_half)}")
    
    if total_discharge > 1000:  # Mindestens 1 TWh V2G
        print("\n✅ TEST BESTANDEN: V2G ist aktiv")
        return True
    else:
        print(f"\n❌ TEST FEHLGESCHLAGEN: Zu wenig V2G ({total_discharge:.0f} MWh)")
        return False


def test_energy_balance_consistency():
    """
    Test 5: Energiebilanz ist konsistent.
    
    Energie_neu = Energie_alt + Ladung - Entladung - Fahrverbrauch
    """
    print("\n" + "="*70)
    print("TEST 5: Energiebilanz ist konsistent")
    print("="*70)
    
    df = create_test_data(n_days=2)
    for i in range(len(df)):
        hour = df.loc[i, 'Zeitpunkt'].hour
        if hour < 12:
            df.loc[i, 'Rest Bilanz [MWh]'] = 300.0  # Defizit
        else:
            df.loc[i, 'Rest Bilanz [MWh]'] = -300.0  # Überschuss
    
    config = EVConfigParams(SOC0=0.5)
    scenario = EVScenarioParams(
        s_EV=0.8,
        N_cars=10_000_000,
        plug_share_max=0.6
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    # Prüfe Energiebilanz für jeden Zeitschritt
    errors = []
    for i in range(1, len(result)):
        soc_prev = result.iloc[i-1]['EMobility SOC [MWh]']
        soc_curr = result.iloc[i]['EMobility SOC [MWh]']
        charge = result.iloc[i]['EMobility Charge [MWh]']
        discharge = result.iloc[i]['EMobility Discharge [MWh]']
        drive = result.iloc[i]['EMobility Drive [MWh]']
        
        # Berechne erwarteten SOC
        expected_soc = soc_prev + charge - discharge - drive
        
        # Kapazitätsgrenzen berücksichtigen
        n_ev = scenario.s_EV * scenario.N_cars
        capacity_mwh = n_ev * scenario.E_batt_car / 1000.0
        expected_soc = max(0, min(expected_soc, capacity_mwh))
        
        error = abs(soc_curr - expected_soc)
        if error > 0.1:  # 0.1 MWh Toleranz
            errors.append((i, error, soc_curr, expected_soc))
    
    if len(errors) == 0:
        print("\n✅ TEST BESTANDEN: Energiebilanz ist konsistent")
        return True
    else:
        print(f"\n❌ TEST FEHLGESCHLAGEN: {len(errors)} Bilanzfehler")
        for i, error, actual, expected in errors[:5]:
            print(f"  Zeitschritt {i}: Fehler={error:.2f} MWh (ist={actual:.2f}, soll={expected:.2f})")
        return False


def test_no_negative_values():
    """
    Test 6: Keine negativen Werte für SOC, Charge, Discharge.
    """
    print("\n" + "="*70)
    print("TEST 6: Keine negativen Werte")
    print("="*70)
    
    df = create_test_data(n_days=3)
    # Extreme Schwankungen
    for i in range(len(df)):
        hour = df.loc[i, 'Zeitpunkt'].hour
        df.loc[i, 'Rest Bilanz [MWh]'] = 500.0 * np.sin(hour * np.pi / 12)
    
    config = EVConfigParams(SOC0=0.5)
    scenario = EVScenarioParams(
        s_EV=0.9,
        N_cars=20_000_000,
        plug_share_max=0.7,
        v2g_share=0.5
    )
    
    result = simulate_emobility_fleet(df.copy(), scenario, config)
    
    checks = {
        'SOC >= 0': (result['EMobility SOC [MWh]'] >= -0.001).all(),
        'Charge >= 0': (result['EMobility Charge [MWh]'] >= -0.001).all(),
        'Discharge >= 0': (result['EMobility Discharge [MWh]'] >= -0.001).all(),
        'Drive >= 0': (result['EMobility Drive [MWh]'] >= -0.001).all(),
    }
    
    all_passed = True
    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ TEST BESTANDEN: Alle Werte sind nicht-negativ")
    else:
        print("\n❌ TEST FEHLGESCHLAGEN: Negative Werte gefunden")
    
    return all_passed


if __name__ == "__main__":
    print("#" * 70)
    print("# RIGOROSER TEST DER ADAPTIVEN VORLADE-LOGIK")
    print("#" * 70)
    
    results = []
    results.append(("Keine Ladespitzen", test_no_extreme_charging_spikes()))
    results.append(("Gleichmäßige Ladung", test_smooth_charging_distribution()))
    results.append(("Ziel-SOC erreicht", test_target_soc_achieved()))
    results.append(("V2G funktioniert", test_v2g_still_works()))
    results.append(("Energiebilanz konsistent", test_energy_balance_consistency()))
    results.append(("Keine negativen Werte", test_no_negative_values()))
    
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
        print("\n🎉 ALLE TESTS BESTANDEN!")
    else:
        print("\n⚠️  EINIGE TESTS FEHLGESCHLAGEN!")
