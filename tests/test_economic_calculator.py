"""Test module for EconomicCalculator

Performs basic validation of economic calculations including:
- Investment calculation (delta in capacities)
- Annual cost components (capital, fixed OPEX, variable OPEX)
- System LCOE computation
"""

import sys
import unittest
from pathlib import Path

# Add source-code folder to path
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

from data_processing.economic_calculator import EconomicCalculator
import constants as const


class TestEconomicCalculatorBasic(unittest.TestCase):
    """Basic tests for EconomicCalculator with simple mock data."""

    def setUp(self):
        """Set up test fixtures with minimal data."""
        # Mock inputs: installed capacities per technology per year (MW)
        self.inputs = {
            "PV": {
                2025: 100.0,      # Base year
                2030: 200.0,      # +100 MW new build
            },
            "Wind": {
                2025: 50.0,
                2030: 100.0,      # +50 MW new build
            }
        }

        # Mock simulation results: generation per technology (MWh) and consumption
        self.simulation_results = {
            "generation": {
                2030: {
                    "PV": 180000.0,     # MWh
                    "Wind": 220000.0,   # MWh
                }
            },
            "total_consumption": {
                2030: 500000.0  # MWh total system demand
            }
        }

    def test_calculator_initialization(self):
        """Test that calculator initializes without errors."""
        calc = EconomicCalculator(self.inputs, self.simulation_results)
        self.assertIsNotNone(calc)
        self.assertEqual(calc.base_year, 2025)
        self.assertEqual(calc.inputs, self.inputs)
        self.assertEqual(calc.simulation_results, self.simulation_results)

    def test_annuity_factor_calculation(self):
        """Test annuity factor formula."""
        calc = EconomicCalculator({}, {})
        
        # Test normal case: wacc=5%, lifetime=20 years
        factor = calc._calculate_annuity_factor(0.05, 20)
        self.assertGreater(factor, 0)
        self.assertLess(factor, 0.2)  # Should be roughly 0.08
        
        # Test edge case: zero WACC
        factor_zero = calc._calculate_annuity_factor(0.0, 20)
        self.assertAlmostEqual(factor_zero, 0.05, places=3)  # 1/20 = 0.05
        
        # Test edge case: zero lifetime
        factor_zero_life = calc._calculate_annuity_factor(0.05, 0)
        self.assertEqual(factor_zero_life, 0.0)

    def test_capacity_retrieval(self):
        """Test capacity lookup for int and string keys."""
        calc = EconomicCalculator(self.inputs, {})
        
        # Test int key
        cap_pv = calc._get_capacity(self.inputs["PV"], 2025)
        self.assertEqual(cap_pv, 100.0)
        
        # Test year 2030
        cap_wind = calc._get_capacity(self.inputs["Wind"], 2030)
        self.assertEqual(cap_wind, 100.0)
        
        # Test missing year
        cap_missing = calc._get_capacity(self.inputs["PV"], 2040)
        self.assertEqual(cap_missing, 0.0)

    def test_generation_retrieval(self):
        """Test generation lookup from nested structures."""
        calc = EconomicCalculator({}, self.simulation_results)
        
        # Test retrieval from nested "generation" -> year -> tech_id
        gen_pv = calc._get_generation("PV", 2030)
        self.assertEqual(gen_pv, 180000.0)
        
        gen_wind = calc._get_generation("Wind", 2030)
        self.assertEqual(gen_wind, 220000.0)
        
        # Test missing technology
        gen_missing = calc._get_generation("Solar", 2030)
        self.assertEqual(gen_missing, 0.0)

    def test_total_consumption_retrieval(self):
        """Test total consumption lookup."""
        calc = EconomicCalculator({}, self.simulation_results)
        
        consumption = calc._get_total_consumption(2030)
        self.assertEqual(consumption, 500000.0)
        
        # Test missing year
        consumption_missing = calc._get_total_consumption(2040)
        self.assertEqual(consumption_missing, 0.0)

    def test_wacc_retrieval(self):
        """Test WACC lookup with fallback."""
        calc = EconomicCalculator({}, {})
        
        # Should fall back to default 0.05 if const.WACC not defined properly
        wacc = calc._get_wacc(2030)
        self.assertGreater(wacc, 0)
        self.assertLess(wacc, 1)  # Should be a reasonable percentage

    def test_full_calculation(self):
        """Test complete economic calculation."""
        calc = EconomicCalculator(self.inputs, self.simulation_results)
        result = calc.perform_calculation(2030)
        
        # Check result structure
        self.assertIn("year", result)
        self.assertIn("total_investment_bn", result)
        self.assertIn("total_annual_cost_bn", result)
        self.assertIn("system_lco_e", result)
        
        # Check result values
        self.assertEqual(result["year"], 2030)
        self.assertGreaterEqual(result["total_investment_bn"], 0)
        self.assertGreaterEqual(result["total_annual_cost_bn"], 0)
        self.assertGreaterEqual(result["system_lco_e"], 0)

    def test_calculation_with_empty_data(self):
        """Test calculation handles empty data gracefully."""
        calc = EconomicCalculator({}, {})
        result = calc.perform_calculation(2030)
        
        # Should return zeros, not crash
        self.assertEqual(result["year"], 2030)
        self.assertEqual(result["total_investment_bn"], 0.0)
        self.assertEqual(result["total_annual_cost_bn"], 0.0)
        self.assertEqual(result["system_lco_e"], 0.0)

    def test_calculation_with_none_values(self):
        """Test calculation handles None values robustly."""
        calc = EconomicCalculator(None, None)
        result = calc.perform_calculation(2030)
        
        # Should return zeros without crashing
        self.assertIsNotNone(result)
        self.assertEqual(result["total_investment_bn"], 0.0)


if __name__ == "__main__":
    unittest.main()
