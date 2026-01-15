"""Test script to verify scenario loading with new configuration."""
import sys
sys.path.insert(0, 'source-code')

from scenario_manager import ScenarioManager
from config_manager import ConfigManager

# Initialize managers
cfg = ConfigManager()
sm = ScenarioManager()

# Test 1: Get available temperature datasets
print("=" * 60)
print("TEST 1: Available Temperature Datasets")
print("=" * 60)
temps = sm.get_available_temperature_datasets(cfg)
for temp in temps:
    print(f"  ✓ {temp}")

# Test 2: Load a scenario and check heat pump parameters
print("\n" + "=" * 60)
print("TEST 2: Load Scenario and Check Heat Pump Parameters")
print("=" * 60)
scenario = sm.load_scenario('scenarios/Szenario 2030/Agora 2030_1.0.yaml')
print(f"Scenario Name: {scenario.get('scenario_name', 'Unknown')}")

hp_params = scenario.get('target_heat_pump_parameters', {})
if hp_params:
    print("\nHeat Pump Parameters:")
    for year, params in hp_params.items():
        print(f"\n  Year {year}:")
        print(f"    capacity_gw: {params.get('capacity_gw', 'NOT SET')}")
        print(f"    weather_data: {params.get('weather_data', 'NOT SET')}")
        load_prof = params.get('load_profile', None)
        if load_prof is None:
            print(f"    load_profile: ✓ NOT IN YAML (using constant)")
        else:
            print(f"    load_profile: ✗ STILL IN YAML: {load_prof}")
else:
    print("  No heat pump parameters found")

# Test 3: Verify constant is being used
print("\n" + "=" * 60)
print("TEST 3: Verify Constant Usage")
print("=" * 60)
from constants import HEATPUMP_LOAD_PROFILE_NAME
print(f"Constant HEATPUMP_LOAD_PROFILE_NAME: {HEATPUMP_LOAD_PROFILE_NAME}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
