"""Verifiziere die vollständige Integration der neuen Konfigurationsstruktur."""
import sys
sys.path.insert(0, 'source-code')

from scenario_manager import ScenarioManager
from config_manager import ConfigManager
from constants import HEATPUMP_LOAD_PROFILE_NAME

print("=" * 70)
print("INTEGRATION TEST: Wärmepumpen-Konfiguration")
print("=" * 70)

# Initialize
cfg = ConfigManager()
sm = ScenarioManager()

# Test 1: Verfügbare Temperature-Datasets
print("\n✓ TEST 1: Temperature-Datasets verfügbar")
temps = sm.get_available_temperature_datasets(cfg)
print(f"  Anzahl verfügbarer Datasets: {len(temps)}")
for temp in temps:
    print(f"    - {temp}")

# Test 2: Alle Szenarien laden und prüfen
print("\n✓ TEST 2: Alle Szenarien laden und validieren")
scenario_paths = [
    'scenarios/Szenario 2030/Agora 2030_1.0.yaml',
    'scenarios/Szenario 2030/BDI-230_1.0.yaml',
    'scenarios/Szenario 2030/dena-2030_1.0.yaml',
    'scenarios/Szenario 2045/2045-REF_1.0.yaml',
]

all_valid = True
for path in scenario_paths:
    try:
        scenario = sm.load_scenario(path)
        hp_params = scenario.get('target_heat_pump_parameters', {})
        
        # Prüfe ob load_profile entfernt wurde
        for year, params in hp_params.items():
            if 'load_profile' in params:
                print(f"  ✗ {path} - Jahr {year} hat noch load_profile!")
                all_valid = False
            
            # Prüfe ob weather_data existiert
            if 'weather_data' not in params:
                print(f"  ✗ {path} - Jahr {year} fehlt weather_data!")
                all_valid = False
            elif params['weather_data'] not in temps:
                print(f"  ✗ {path} - weather_data '{params['weather_data']}' nicht in verfügbaren Datasets!")
                all_valid = False
        
        if all_valid:
            print(f"  ✓ {path}")
    except Exception as e:
        print(f"  ✗ {path} - Fehler: {e}")
        all_valid = False

# Test 3: Konstante validieren
print("\n✓ TEST 3: Konstante HEATPUMP_LOAD_PROFILE_NAME")
print(f"  Wert: '{HEATPUMP_LOAD_PROFILE_NAME}'")

# Test 4: Prüfe ob Lastprofil im DataManager verfügbar ist
print("\n✓ TEST 4: Lastprofil-Matrix im DataManager")
from data_manager import DataManager
dm = DataManager(cfg)
try:
    hp_profile = dm.get(HEATPUMP_LOAD_PROFILE_NAME)
    if hp_profile is not None:
        print(f"  ✓ Lastprofil geladen: {hp_profile.shape if hasattr(hp_profile, 'shape') else 'OK'}")
    else:
        print(f"  ✗ Lastprofil nicht gefunden!")
        all_valid = False
except Exception as e:
    print(f"  ✗ Fehler beim Laden: {e}")
    all_valid = False

# Finale Bewertung
print("\n" + "=" * 70)
if all_valid:
    print("✓✓✓ ALLE TESTS BESTANDEN ✓✓✓")
    print("Die Integration ist vollständig und funktionsfähig!")
else:
    print("✗✗✗ EINIGE TESTS FEHLGESCHLAGEN ✗✗✗")
    print("Bitte die Fehler oben prüfen.")
print("=" * 70)
