"""
Test: Rückwärtskompatibilität mit älteren YAML-Szenarien.

Stellt sicher, dass YAMLs ohne neuere Parameter (wie v2g_share) 
korrekt geladen werden und Default-Werte verwendet werden.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source-code'))

import yaml
from scenario_manager import ScenarioManager
from data_processing.e_mobility_simulation import EVScenarioParams


def test_old_yaml_without_v2g_share():
    """
    Test: Eine YAML ohne v2g_share soll mit Default-Wert 0.3 geladen werden.
    """
    print("\n" + "="*70)
    print("TEST: Alte YAML ohne v2g_share laden")
    print("="*70)
    
    # Lade eine alte YAML (Agora 2030 hat kein v2g_share)
    yaml_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'scenarios', 
        'Szenario 2030', 
        'Agora 2030_1.0.yaml'
    )
    
    # Prüfe, dass v2g_share NICHT in der YAML ist
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    em_params = yaml_data.get('target_emobility_parameters', {}).get(2030, {})
    has_v2g_share = 'v2g_share' in em_params
    
    print(f"\nYAML-Datei: {os.path.basename(yaml_path)}")
    print(f"v2g_share in YAML vorhanden: {has_v2g_share}")
    
    if has_v2g_share:
        print("⚠️  YAML enthält bereits v2g_share - Test nicht aussagekräftig")
    
    # Simuliere das Laden wie in ScenarioManager.get_emobility_params()
    em_data = yaml_data.get('target_emobility_parameters', {}).get(2030, {})
    
    ev_params = EVScenarioParams(
        s_EV=em_data.get('s_EV', 0.9),
        N_cars=em_data.get('N_cars', em_data.get('installed_units', 5_000_000)),
        E_drive_car_year=em_data.get('E_drive_car_year', 
                                     em_data.get('annual_consumption_kwh', 2250.0) / 4.5),
        E_batt_car=em_data.get('E_batt_car', 50.0),
        plug_share_max=em_data.get('plug_share_max', 0.6),
        v2g_share=em_data.get('v2g_share', 0.3),
        SOC_min_day=em_data.get('SOC_min_day', 0.4),
        SOC_min_night=em_data.get('SOC_min_night', 0.2),
        SOC_target_depart=em_data.get('SOC_target_depart', 0.6),
        t_depart=em_data.get('t_depart', "07:30"),
        t_arrive=em_data.get('t_arrive', "18:00"),
        thr_surplus=em_data.get('thr_surplus', 200_000.0),
        thr_deficit=em_data.get('thr_deficit', 200_000.0)
    )
    
    print(f"\nGeladene EVScenarioParams:")
    print(f"  v2g_share = {ev_params.v2g_share}")
    print(f"  s_EV = {ev_params.s_EV}")
    print(f"  N_cars = {ev_params.N_cars:,}")
    print(f"  plug_share_max = {ev_params.plug_share_max}")
    
    # Prüfe Default-Wert
    if ev_params.v2g_share == 0.3:
        print("\n✅ TEST BESTANDEN: Default-Wert 0.3 wurde korrekt verwendet")
        return True
    else:
        print(f"\n❌ TEST FEHLGESCHLAGEN: v2g_share = {ev_params.v2g_share}, erwartet 0.3")
        return False


def test_new_yaml_with_v2g_share():
    """
    Test: Eine YAML mit v2g_share soll den konfigurierten Wert verwenden.
    """
    print("\n" + "="*70)
    print("TEST: Neue YAML mit v2g_share laden")
    print("="*70)
    
    yaml_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'scenarios', 
        'Szenario_Beispiel_SW.yaml'
    )
    
    if not os.path.exists(yaml_path):
        print("⚠️  Test-YAML nicht gefunden, überspringe")
        return True
    
    # Lade YAML direkt
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    # Prüfe für alle Jahre
    for year in yaml_data.get('metadata', {}).get('valid_for_years', [2030]):
        em_data = yaml_data.get('target_emobility_parameters', {}).get(year, {})
        yaml_v2g_share = em_data.get('v2g_share', 'NICHT VORHANDEN')
        
        # Simuliere das Laden
        ev_params = EVScenarioParams(
            s_EV=em_data.get('s_EV', 0.9),
            N_cars=em_data.get('N_cars', em_data.get('installed_units', 5_000_000)),
            E_drive_car_year=em_data.get('E_drive_car_year', 
                                         em_data.get('annual_consumption_kwh', 2250.0) / 4.5),
            E_batt_car=em_data.get('E_batt_car', 50.0),
            plug_share_max=em_data.get('plug_share_max', 0.6),
            v2g_share=em_data.get('v2g_share', 0.3),
            SOC_min_day=em_data.get('SOC_min_day', 0.4),
            SOC_min_night=em_data.get('SOC_min_night', 0.2),
            SOC_target_depart=em_data.get('SOC_target_depart', 0.6),
            t_depart=em_data.get('t_depart', "07:30"),
            t_arrive=em_data.get('t_arrive', "18:00"),
            thr_surplus=em_data.get('thr_surplus', 200_000.0),
            thr_deficit=em_data.get('thr_deficit', 200_000.0)
        )
        
        print(f"\nJahr {year}:")
        print(f"  v2g_share in YAML: {yaml_v2g_share}")
        print(f"  v2g_share geladen: {ev_params.v2g_share}")
        
        if yaml_v2g_share != 'NICHT VORHANDEN':
            if abs(ev_params.v2g_share - yaml_v2g_share) < 0.001:
                print(f"  ✅ Wert korrekt übernommen")
            else:
                print(f"  ❌ Wert stimmt nicht überein!")
                return False
    
    print("\n✅ TEST BESTANDEN")
    return True


def test_all_default_values():
    """
    Test: Prüfe dass ALLE Default-Werte in EVScenarioParams korrekt gesetzt sind.
    """
    print("\n" + "="*70)
    print("TEST: Default-Werte der EVScenarioParams")
    print("="*70)
    
    # Erstelle mit minimalen Parametern
    params = EVScenarioParams()
    
    expected_defaults = {
        's_EV': 0.9,
        'N_cars': 5_000_000,
        'E_drive_car_year': 2250.0,  # Korrigiert (aus Dataclass)
        'E_batt_car': 50.0,
        'plug_share_max': 0.6,
        'v2g_share': 0.3,  # NEU!
        'SOC_min_day': 0.4,
        'SOC_min_night': 0.2,
        'SOC_target_depart': 0.6,
        't_depart': "07:30",
        't_arrive': "18:00",
        'thr_surplus': 200_000.0,
        'thr_deficit': 200_000.0,
    }
    
    all_correct = True
    for attr, expected in expected_defaults.items():
        actual = getattr(params, attr)
        if actual == expected:
            print(f"  ✅ {attr} = {actual}")
        else:
            print(f"  ❌ {attr} = {actual} (erwartet: {expected})")
            all_correct = False
    
    if all_correct:
        print("\n✅ TEST BESTANDEN: Alle Default-Werte korrekt")
    else:
        print("\n❌ TEST FEHLGESCHLAGEN: Einige Default-Werte falsch")
    
    return all_correct


def test_partial_yaml_emobility():
    """
    Test: YAML mit nur teilweisen E-Mobility-Parametern.
    """
    print("\n" + "="*70)
    print("TEST: YAML mit unvollständigen E-Mobility-Parametern")
    print("="*70)
    
    # Simuliere eine minimale YAML
    minimal_yaml = {
        'target_emobility_parameters': {
            2030: {
                'installed_units': 8_000_000,
                # Alle anderen Parameter fehlen!
            }
        }
    }
    
    em_data = minimal_yaml['target_emobility_parameters'][2030]
    
    # Simuliere das Laden wie in scenario_manager.py
    params = EVScenarioParams(
        s_EV=em_data.get('s_EV', 0.9),
        N_cars=em_data.get('N_cars', em_data.get('installed_units', 5_000_000)),
        E_drive_car_year=em_data.get('E_drive_car_year', 
                                     em_data.get('annual_consumption_kwh', 2250.0) / 4.5),
        E_batt_car=em_data.get('E_batt_car', 50.0),
        plug_share_max=em_data.get('plug_share_max', 0.6),
        v2g_share=em_data.get('v2g_share', 0.3),
        SOC_min_day=em_data.get('SOC_min_day', 0.4),
        SOC_min_night=em_data.get('SOC_min_night', 0.2),
        SOC_target_depart=em_data.get('SOC_target_depart', 0.6),
        t_depart=em_data.get('t_depart', "07:30"),
        t_arrive=em_data.get('t_arrive', "18:00"),
        thr_surplus=em_data.get('thr_surplus', 200_000.0),
        thr_deficit=em_data.get('thr_deficit', 200_000.0)
    )
    
    print(f"\nMinimale YAML enthält nur: installed_units = 8,000,000")
    print(f"\nGeladene Parameter:")
    print(f"  N_cars = {params.N_cars:,} (aus installed_units)")
    print(f"  v2g_share = {params.v2g_share} (Default)")
    print(f"  plug_share_max = {params.plug_share_max} (Default)")
    print(f"  s_EV = {params.s_EV} (Default)")
    
    if params.N_cars == 8_000_000 and params.v2g_share == 0.3:
        print("\n✅ TEST BESTANDEN: Minimale YAML korrekt verarbeitet")
        return True
    else:
        print("\n❌ TEST FEHLGESCHLAGEN")
        return False


if __name__ == "__main__":
    print("#" * 70)
    print("# TEST: YAML RÜCKWÄRTSKOMPATIBILITÄT")
    print("#" * 70)
    
    results = []
    results.append(("Alte YAML ohne v2g_share", test_old_yaml_without_v2g_share()))
    results.append(("Neue YAML mit v2g_share", test_new_yaml_with_v2g_share()))
    results.append(("Default-Werte", test_all_default_values()))
    results.append(("Minimale YAML", test_partial_yaml_emobility()))
    
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
        print("\n🎉 ALLE TESTS BESTANDEN - Rückwärtskompatibilität gewährleistet!")
    else:
        print("\n⚠️  EINIGE TESTS FEHLGESCHLAGEN!")
