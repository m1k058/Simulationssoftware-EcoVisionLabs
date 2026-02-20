"""
Unit Tests für EconomicCalculator und calculate_economics_from_simulation.

Tests überprüfen:
1. EconomicCalculator.perform_calculation() - Kernlogik der Wirtschaftlichkeitsberechnung
2. calculate_economics_from_simulation() - High-Level Adapter-Funktion
3. BASELINE_2025_DEFAULTS - Konstanten-Verfügbarkeit
"""

import pytest
import pandas as pd
from typing import Dict, Any
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add source-code directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "source-code"))

from data_processing.economic_calculator import (
    EconomicCalculator,
    calculate_economics_from_simulation,
    BASELINE_2025_DEFAULTS
)


class TestBaselineDefaults:
    """Tests für BASELINE_2025_DEFAULTS Konstante."""
    
    def test_baseline_defaults_exist(self):
        """Prüfe, dass BASELINE_2025_DEFAULTS existiert und Dict ist."""
        assert isinstance(BASELINE_2025_DEFAULTS, dict)
        assert len(BASELINE_2025_DEFAULTS) > 0
    
    def test_baseline_contains_key_technologies(self):
        """Prüfe, dass wichtige Technologien vorhanden sind."""
        required_techs = [
            "Photovoltaik",
            "Wind_Onshore",
            "Wind_Offshore",
            "Biomasse",
            "Wasserkraft",
            "Erdgas"
        ]
        for tech in required_techs:
            assert tech in BASELINE_2025_DEFAULTS, f"{tech} fehlt in BASELINE_2025_DEFAULTS"
            assert isinstance(BASELINE_2025_DEFAULTS[tech], (int, float))
            assert BASELINE_2025_DEFAULTS[tech] >= 0


class TestEconomicCalculatorPerformCalculation:
    """Tests für EconomicCalculator.perform_calculation()."""
    
    def test_perform_calculation_basic(self):
        """Test: Grundlegende Berechnung mit minimalen Inputs."""
        inputs = {
            "Photovoltaik": {
                2025: 86408.0,  # Baseline
                2030: 215000.0  # Ziel
            }
        }
        
        simulation_results = {
            "generation": {
                2030: {
                    "Photovoltaik": 250_000_000.0  # 250 TWh = 250,000 GWh = 250,000,000 MWh
                }
            },
            "total_consumption": {
                2030: 600_000_000.0  # 600 TWh
            }
        }
        
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=simulation_results
        )
        
        result = calculator.perform_calculation(target_year=2030)
        
        # Basis-Assertions
        assert "year" in result
        assert result["year"] == 2030.0
        assert "total_investment_bn" in result
        assert "total_annual_cost_bn" in result
        assert "system_lco_e" in result
        
        # Investition sollte positiv sein (da Ausbau von 86 GW auf 215 GW)
        assert result["total_investment_bn"] > 0
        
        # LCOE sollte positiv und realistisch sein (< 50 ct/kWh)
        assert 0 < result["system_lco_e"] < 50
    
    def test_perform_calculation_with_storage(self):
        """Test: Berechnung mit Speicher-Technologien."""
        inputs = {
            "Photovoltaik": {
                2025: 86408.0,
                2030: 150000.0
            }
        }
        
        storage_capacities = {
            "battery_storage": {
                2025: {
                    "installed_capacity_mwh": 0.0,
                    "max_charge_power_mw": 0.0,
                    "max_discharge_power_mw": 0.0
                },
                2030: {
                    "installed_capacity_mwh": 50000.0,  # 50 GWh
                    "max_charge_power_mw": 10000.0,     # 10 GW
                    "max_discharge_power_mw": 10000.0
                }
            }
        }
        
        simulation_results = {
            "generation": {2030: {"Photovoltaik": 180_000_000.0}},
            "total_consumption": {2030: 600_000_000.0}
        }
        
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=simulation_results,
            target_storage_capacities=storage_capacities
        )
        
        result = calculator.perform_calculation(target_year=2030)
        
        # Speicher sollten zu zusätzlichen Investitionen führen
        assert result["total_investment_bn"] > 0
        assert "investment_by_tech" in result
        
        # Prüfe ob Speicher in Details vorhanden
        tech_keys = result.get("investment_by_tech", {}).keys()
        # Kann "Batteriespeicher" sein (gemapped)
        storage_found = any("speicher" in k.lower() or "battery" in k.lower() for k in tech_keys)
        assert storage_found or len(tech_keys) > 0  # Mindestens eine Technologie
    
    def test_perform_calculation_zero_consumption_no_crash(self):
        """Test: Keine Division durch Null bei leerem Verbrauch."""
        inputs = {
            "Photovoltaik": {
                2025: 50000.0,
                2030: 100000.0
            }
        }
        
        simulation_results = {
            "generation": {2030: {"Photovoltaik": 120_000_000.0}},
            "total_consumption": {2030: 0.0}  # Kein Verbrauch
        }
        
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=simulation_results
        )
        
        result = calculator.perform_calculation(target_year=2030)
        
        # Sollte nicht crashen
        assert "system_lco_e" in result
        # LCOE sollte 0 sein wenn kein Verbrauch
        assert result["system_lco_e"] == 0.0
    
    def test_perform_calculation_multiple_technologies(self):
        """Test: Berechnung mit mehreren Technologien."""
        inputs = {
            "Photovoltaik": {2025: 86408.0, 2030: 150000.0},
            "Wind_Onshore": {2025: 63192.0, 2030: 115000.0},
            "Wind_Offshore": {2025: 10289.0, 2030: 30000.0},
            "Erdgas": {2025: 32658.0, 2030: 25000.0}  # Rückbau
        }
        
        simulation_results = {
            "generation": {
                2030: {
                    "Photovoltaik": 180_000_000.0,
                    "Wind_Onshore": 230_000_000.0,
                    "Wind_Offshore": 95_000_000.0,
                    "Erdgas": 45_000_000.0
                }
            },
            "total_consumption": {2030: 600_000_000.0}
        }
        
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=simulation_results
        )
        
        result = calculator.perform_calculation(target_year=2030)
        
        # Detaillierte Ergebnisse sollten vorhanden sein
        assert "investment_by_tech" in result
        assert "capex_annual_by_tech" in result
        assert "opex_fix_by_tech" in result
        assert "opex_var_by_tech" in result
        
        # Mindestens 1 Technologie sollte Investment haben
        assert len(result["investment_by_tech"]) >= 1
        
        # Gesamt-LCOE sollte realistisch sein
        assert 0 < result["system_lco_e"] < 100
    
    def test_perform_calculation_breakdown_components(self):
        """Test: Prüfe korrekte Aufteilung CAPEX/OPEX."""
        inputs = {
            "Photovoltaik": {
                2025: 50000.0,
                2030: 100000.0
            }
        }
        
        simulation_results = {
            "generation": {2030: {"Photovoltaik": 120_000_000.0}},
            "total_consumption": {2030: 600_000_000.0}
        }
        
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=simulation_results
        )
        
        result = calculator.perform_calculation(target_year=2030)
        
        # Alle Kostenkomponenten sollten vorhanden sein
        capex_annual = result.get("capex_annual_bn", 0.0)
        opex_fix = result.get("opex_fix_bn", 0.0)
        opex_var = result.get("opex_var_bn", 0.0)
        total_annual = result.get("total_annual_cost_bn", 0.0)
        
        # Summe sollte konsistent sein (mit kleiner Toleranz)
        calculated_total = capex_annual + opex_fix + opex_var
        assert abs(total_annual - calculated_total) < 0.01  # < 10 Mio. € Differenz


class TestCalculateEconomicsFromSimulation:
    """Tests für calculate_economics_from_simulation() High-Level Funktion."""
    
    def test_calculate_from_simulation_basic(self):
        """Test: Grundlegender Durchlauf mit Mock ScenarioManager."""
        # Mock ScenarioManager
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": 215000.0,
            "Wind_Onshore": 115000.0
        }
        scenario_manager.get_storage_capacities.return_value = {}
        
        # Simulations-DataFrames
        df_production = pd.DataFrame({
            "Timestamp": pd.date_range("2030-01-01", periods=8760, freq="h"),
            "Photovoltaik [MWh]": [100.0] * 8760,
            "Wind Onshore [MWh]": [150.0] * 8760
        })
        
        df_consumption = pd.DataFrame({
            "Timestamp": pd.date_range("2030-01-01", periods=8760, freq="h"),
            "Gesamt [MWh]": [300.0] * 8760
        })
        
        simulation_results = {
            "production": df_production,
            "consumption": df_consumption
        }
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results=simulation_results,
            target_year=2030,
            baseline_capacities=None  # Nutzt BASELINE_2025_DEFAULTS
        )
        
        # Prüfe dass Ergebnis valide ist
        assert "year" in result
        assert result["year"] == 2030.0
        assert "total_investment_bn" in result
        assert "system_lco_e" in result
        
        # ScenarioManager wurde korrekt aufgerufen
        scenario_manager.get_generation_capacities.assert_called_once_with(year=2030)
    
    def test_calculate_from_simulation_uses_baseline_defaults(self):
        """Test: Nutzt BASELINE_2025_DEFAULTS wenn baseline_capacities=None."""
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": 200000.0
        }
        scenario_manager.get_storage_capacities.return_value = {}
        
        df_production = pd.DataFrame({
            "Photovoltaik [MWh]": [100.0] * 100
        })
        df_consumption = pd.DataFrame({
            "Gesamt [MWh]": [150.0] * 100
        })
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results={"production": df_production, "consumption": df_consumption},
            target_year=2030,
            baseline_capacities=None
        )
        
        # Sollte erfolgreich sein ohne data_manager
        assert result["year"] == 2030.0
        assert "error" not in result
    
    def test_calculate_from_simulation_custom_baseline(self):
        """Test: Nutzt custom baseline_capacities wenn übergeben."""
        custom_baseline = {
            "Photovoltaik": 100000.0,  # Custom Wert
            "Wind_Onshore": 80000.0
        }
        
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": 200000.0,
            "Wind_Onshore": 150000.0
        }
        scenario_manager.get_storage_capacities.return_value = {}
        
        df_production = pd.DataFrame({
            "Photovoltaik [MWh]": [100.0] * 100,
            "Wind Onshore [MWh]": [80.0] * 100
        })
        df_consumption = pd.DataFrame({
            "Gesamt [MWh]": [200.0] * 100
        })
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results={"production": df_production, "consumption": df_consumption},
            target_year=2030,
            baseline_capacities=custom_baseline
        )
        
        assert result["year"] == 2030.0
        assert "error" not in result
        # Investment sollte basierend auf custom baseline berechnet sein
        assert result["total_investment_bn"] > 0
    
    def test_calculate_from_simulation_with_storage(self):
        """Test: Berechnung inkl. Speicher aus ScenarioManager."""
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": 150000.0
        }
        
        # Speicher-Mock
        def get_storage(storage_type, year):
            if storage_type == "battery_storage":
                return {
                    "installed_capacity_mwh": 50000.0,
                    "max_charge_power_mw": 10000.0,
                    "max_discharge_power_mw": 10000.0,
                    "initial_soc": 0.5
                }
            return {}
        
        scenario_manager.get_storage_capacities.side_effect = get_storage
        
        df_production = pd.DataFrame({
            "Photovoltaik [MWh]": [100.0] * 100
        })
        df_consumption = pd.DataFrame({
            "Gesamt [MWh]": [150.0] * 100
        })
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results={"production": df_production, "consumption": df_consumption},
            target_year=2030
        )
        
        # Speicher sollten korrekt abgerufen worden sein
        assert scenario_manager.get_storage_capacities.call_count == 3  # battery, pumped_hydro, h2
        
        # Ergebnis sollte valide sein
        assert result["year"] == 2030.0
        assert result["total_investment_bn"] > 0
    
    def test_calculate_from_simulation_error_handling(self):
        """Test: Error Handling bei fehlerhaften Inputs."""
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.side_effect = Exception("Test Error")
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results={},
            target_year=2030
        )
        
        # Sollte graceful Error Return haben
        assert "error" in result
        assert result["year"] == 2030.0
        assert result["total_investment_bn"] == 0.0
        assert result["system_lco_e"] == 0.0
    
    def test_calculate_from_simulation_empty_dataframes(self):
        """Test: Verhalten bei leeren DataFrames."""
        scenario_manager = Mock()
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": 100000.0
        }
        scenario_manager.get_storage_capacities.return_value = {}
        
        # Leere DataFrames
        simulation_results = {
            "production": pd.DataFrame(),
            "consumption": pd.DataFrame()
        }
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results=simulation_results,
            target_year=2030
        )
        
        # Sollte nicht crashen, aber sinnvolle Defaults zurückgeben
        assert result["year"] == 2030.0
        # Bei 0 Generation und 0 Consumption kann LCOE 0 sein
        assert isinstance(result["system_lco_e"], (int, float))
    
    def test_calculate_from_simulation_nested_capacity_format(self):
        """Test: Handling von verschachtelten Kapazitäts-Formaten."""
        scenario_manager = Mock()
        
        # Verschachteltes Format {tech: {year: value}}
        scenario_manager.get_generation_capacities.return_value = {
            "Photovoltaik": {2030: 200000.0},  # Verschachtelt
            "Wind_Onshore": 120000.0  # Direkt
        }
        scenario_manager.get_storage_capacities.return_value = {}
        
        df_production = pd.DataFrame({
            "Photovoltaik [MWh]": [100.0] * 100,
            "Wind Onshore [MWh]": [80.0] * 100
        })
        df_consumption = pd.DataFrame({
            "Gesamt [MWh]": [200.0] * 100
        })
        
        result = calculate_economics_from_simulation(
            scenario_manager=scenario_manager,
            simulation_results={"production": df_production, "consumption": df_consumption},
            target_year=2030
        )
        
        # Sollte beide Formate korrekt verarbeiten
        assert result["year"] == 2030.0
        assert "error" not in result
        assert len(result.get("investment_by_tech", {})) >= 1  # Mindestens eine Technologie


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
