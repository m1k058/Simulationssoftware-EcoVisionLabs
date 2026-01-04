"""EconomicCalculator module

Implements `EconomicCalculator` to perform a simple economic analysis for
an energy system simulation using constants for WACC, commodities, and
technology costs.

Assumptions:
- `inputs` holds installed capacities per technology per year.
- `simulation_results` holds generation per technology and total consumption per year.
- Units between `inputs` and `const.TECHNOLOGY_COSTS` are consistent (no conversion).
"""

from typing import Any, Dict, Optional

import constants as const


class EconomicCalculator:
    """Performs investment and LCOE analysis between a base year and target year.

    Structure per requirements:
    - Stores `inputs` and `simulation_results` and uses base year 2025.
    - Computes annuity factor.
    - Computes variable OPEX from fuel and CO2 prices, efficiency, and CO2 factor.
    - Performs calculation of investments, annual costs, and system LCOE.
    """

    def __init__(self, inputs: Dict[str, Any], simulation_results: Dict[str, Any]) -> None:
        self.inputs = inputs or {}
        self.simulation_results = simulation_results or {}
        self.base_year = 2025

    def _calculate_annuity_factor(self, wacc: float, lifetime: float) -> float:
        """Annuitätenformel: (q^n * i) / (q^n - 1), q = 1 + wacc.

        Handles wacc == 0 by returning 1 / lifetime (if lifetime > 0) else 0.
        """
        try:
            i = float(wacc)
            n = float(lifetime)
        except Exception:
            return 0.0

        if n <= 0:
            return 0.0

        if i == 0.0:
            return 1.0 / n

        q_n = (1.0 + i) ** n
        denom = q_n - 1.0
        if denom == 0.0:
            return 0.0
        return (q_n * i) / denom

    def _get_variable_opex_cost(
        self,
        tech_id: str,
        year: int,
        efficiency: Optional[float],
        params: Dict[str, Any],
    ) -> float:
        """Berechne variable Kosten in EUR/MWh_el.

        Formel: (FuelPrice + (CO2_Price * CO2_Faktor)) / Wirkungsgrad
        - Falls kein `fuel_type` vorhanden ist, 0 zurückgeben.
        - Sucht Preise/Faktoren robust in `const.COMMODITIES`.
        """
        try:
            commodities = getattr(const, "COMMODITIES", {}) or {}
            fuel_type = params.get("fuel_type")
            if not fuel_type:
                return 0.0

            # Efficiency guard
            eff = float(efficiency) if efficiency not in (None, 0) else 0.0
            if eff <= 0.0:
                return 0.0

            # Try to locate fuel prices structure
            fuel_prices = (
                commodities.get("FUEL_PRICES")
                or commodities.get("fuel_prices")
                or commodities.get("FUEL", {}).get("PRICES")
                or {}
            )

            def _price_for_year(entry: Any, ft: str, y: int) -> float:
                if isinstance(entry, dict):
                    val = entry.get(ft)
                    if isinstance(val, dict):
                        return float(val.get(y, val.get("default", 0.0)) or 0.0)
                    return float(val or 0.0)
                return 0.0

            fuel_price = _price_for_year(fuel_prices, fuel_type, year)

            # CO2 price per year
            co2_price_map = (
                commodities.get("CO2_PRICE")
                or commodities.get("co2_price")
                or {}
            )
            if isinstance(co2_price_map, dict):
                co2_price = co2_price_map.get(year, co2_price_map.get("default", 0.0))
            else:
                co2_price = co2_price_map or 0.0
            try:
                co2_price = float(co2_price)
            except Exception:
                co2_price = 0.0

            # CO2 factor per fuel type
            co2_factor_map = (
                commodities.get("CO2_FACTOR")
                or commodities.get("co2_factor")
                or commodities.get("CO2_EMISSION_FACTOR")
                or commodities.get("co2_emission_factor")
                or {}
            )
            if isinstance(co2_factor_map, dict):
                co2_factor = float(co2_factor_map.get(fuel_type, 0.0) or 0.0)
            else:
                co2_factor = 0.0

            return (fuel_price + (co2_price * co2_factor)) / eff
        except Exception:
            return 0.0

    # ---- Internal helpers for robust data access ----
    def _get_wacc(self, year: int) -> float:
        """Retrieve WACC for a given year from `const.WACC`.

        Supports scalar or dict forms. Falls back to 0.05 if missing.
        """
        wacc_default = 0.05
        wacc_data = getattr(const, "WACC", wacc_default)
        try:
            if isinstance(wacc_data, dict):
                if year in wacc_data:
                    return float(wacc_data[year])
                # Try default fallbacks
                if "default" in wacc_data:
                    return float(wacc_data["default"])
                # First value if any
                for v in wacc_data.values():
                    try:
                        return float(v)
                    except Exception:
                        continue
                return wacc_default
            return float(wacc_data)
        except Exception:
            return wacc_default

    def _get_capacity(self, tech_inputs: Any, year: int) -> float:
        """Get installed capacity for a technology in a given year.

        Accepts dicts keyed by int or str. Returns 0.0 if missing.
        """
        if not isinstance(tech_inputs, dict):
            return 0.0
        # Direct int key
        if year in tech_inputs:
            try:
                return float(tech_inputs[year] or 0.0)
            except Exception:
                return 0.0
        # String key fallback
        y_str = str(year)
        if y_str in tech_inputs:
            try:
                return float(tech_inputs[y_str] or 0.0)
            except Exception:
                return 0.0
        return 0.0

    def _get_generation(self, tech_id: str, year: int) -> float:
        """Get generation in MWh for a technology in a given year.

        Tries common structures in `simulation_results`:
        - simulation_results["generation"][year][tech_id]
        - simulation_results["generation_by_tech"][tech_id][year]
        - simulation_results[tech_id][year]
        Returns 0.0 if missing.
        """
        sr = self.simulation_results or {}
        candidates = []

        # Nested by year then tech
        gen = sr.get("generation") or sr.get("Generation")
        if isinstance(gen, dict):
            gen_y = gen.get(year) or gen.get(str(year))
            if isinstance(gen_y, dict):
                val = gen_y.get(tech_id)
                if val is not None:
                    candidates.append(val)

        # Nested by tech then year
        gen_bt = sr.get("generation_by_tech") or sr.get("GenerationByTech")
        if isinstance(gen_bt, dict):
            gen_t = gen_bt.get(tech_id)
            if isinstance(gen_t, dict):
                val = gen_t.get(year) or gen_t.get(str(year))
                if val is not None:
                    candidates.append(val)

        # Direct mapping
        direct = sr.get(tech_id)
        if isinstance(direct, dict):
            val = direct.get(year) or direct.get(str(year))
            if val is not None:
                candidates.append(val)

        for c in candidates:
            try:
                return float(c or 0.0)
            except Exception:
                continue
        return 0.0

    def _get_total_consumption(self, year: int) -> float:
        """Get total consumption in MWh for the system in a given year.

        Tries keys: total_consumption, consumption, demand, load.
        Supports nested dict per year. Returns 0.0 if missing.
        """
        sr = self.simulation_results or {}
        for key in [
            "total_consumption",
            "TotalConsumption",
            "consumption",
            "Consumption",
            "demand",
            "Demand",
            "load",
            "Load",
        ]:
            val = sr.get(key)
            if isinstance(val, dict):
                v = val.get(year) or val.get(str(year))
                if v is not None:
                    try:
                        return float(v or 0.0)
                    except Exception:
                        continue
            elif val is not None and not isinstance(val, dict):
                try:
                    return float(val or 0.0)
                except Exception:
                    continue
        return 0.0

    def perform_calculation(self, target_year: int) -> Dict[str, float]:
        """Run the economic calculation for a given `target_year`.

        Steps:
        - Iterate technologies in `inputs`.
        - Compute investment (delta from base to target) and annual costs.
        - Compute System-LCOE = total annual costs / total consumption.
        - Return result dict with values in requested units.
        """
        # Verwende ECONOMICS_CONSTANTS aus constants.py
        econ_consts = getattr(const, "ECONOMICS_CONSTANTS", {}) or {}
        wacc_default = econ_consts.get("global_parameter", {}).get("wacc", 0.05)
        source_specific = econ_consts.get("source_specific", {})

        total_investment = 0.0  # EUR
        total_annual_cost = 0.0  # EUR per year

        wacc = wacc_default

        print(f"[CALC DEBUG] WACC: {wacc}")
        print(f"[CALC DEBUG] Source Specific Costs: {source_specific}")

        for tech_id, tech_inputs in (self.inputs or {}).items():
            print(f"[CALC DEBUG] Verarbeite Tech: {tech_id}")
            
            # Mapping: Tech-IDs zu Parametern
            tech_mapping = {
                'Photovoltaik': 'Photovoltaik',
                'Wind_Onshore': 'Wind Onshore',
                'Wind_Offshore': 'Wind Offshore',
                'Biomasse': 'Biomasse',
                'Wasserkraft': 'Wasserkraft',
                'Erdgas': 'Erdgas',
                'Steinkohle': 'Steinkohle',
                'Braunkohle': 'Braunkohle',
                'Kernenergie': 'Kernenergie'
            }
            
            param_name = tech_mapping.get(tech_id, tech_id)
            params = source_specific.get(param_name, {}) or {}

            # Cost parameters, default safe values
            capex = float(params.get("capex_eur_per_mw", 0.0) or 0.0)
            opex_fix = float(params.get("opex_eur_per_mw_year", 0.0) or 0.0)
            lifetime = float(params.get("lifetime_years", 0.0) or 0.0)
            efficiency = params.get("efficiency", 1.0)

            print(f"[CALC DEBUG]   {tech_id}: CAPEX={capex}, OpEx={opex_fix}, Lifetime={lifetime}")

            p_base = self._get_capacity(tech_inputs, self.base_year)
            p_target = self._get_capacity(tech_inputs, target_year)

            print(f"[CALC DEBUG]   {tech_id}: P_base={p_base} MW, P_target={p_target} MW")

            # Investment: only for new build (delta)
            delta_p = max(0.0, p_target - p_base)
            delta_capex = delta_p * capex
            total_investment += delta_capex

            print(f"[CALC DEBUG]   {tech_id}: Delta={delta_p} MW, Delta CAPEX={delta_capex/1e9:.3f} Mrd. €")

            # Annual capital cost: on TOTAL capacity (replacement value approach)
            if lifetime > 0:
                annuity_factor = self._calculate_annuity_factor(wacc, lifetime)
                annual_capital_cost = p_target * capex * annuity_factor
            else:
                annual_capital_cost = 0.0

            # Annual fixed OPEX
            annual_opex_fix = p_target * opex_fix

            # Annual variable OPEX
            generation_mwh = self._get_generation(tech_id, target_year)
            var_cost_specific = self._get_variable_opex_cost(
                tech_id=tech_id,
                year=target_year,
                efficiency=efficiency,
                params=params,
            )
            annual_opex_var = generation_mwh * var_cost_specific

            print(f"[CALC DEBUG]   {tech_id}: Capital={annual_capital_cost/1e9:.3f}, Fixed OpEx={annual_opex_fix/1e9:.3f}, Var OpEx={annual_opex_var/1e9:.3f} Mrd. €")

            total_annual_cost += annual_capital_cost + annual_opex_fix + annual_opex_var

        # System LCOE: EUR/MWh -> ct/kWh
        total_consumption_mwh = self._get_total_consumption(target_year)
        system_lcoe_eur_per_mwh = (
            (total_annual_cost / total_consumption_mwh) if total_consumption_mwh > 0 else 0.0
        )
        system_lcoe_ct_per_kwh = system_lcoe_eur_per_mwh * 0.1

        print(f"[CALC DEBUG] Total Investment: {total_investment/1e9:.3f} Mrd. €")
        print(f"[CALC DEBUG] Total Annual Cost: {total_annual_cost/1e9:.3f} Mrd. €")
        print(f"[CALC DEBUG] Total Consumption: {total_consumption_mwh/1e6:.3f} TWh")
        print(f"[CALC DEBUG] System LCOE: {system_lcoe_ct_per_kwh:.2f} ct/kWh")

        result = {
            "year": float(target_year),
            "total_investment_bn": total_investment / 1e9,
            "total_annual_cost_bn": total_annual_cost / 1e9,
            "system_lco_e": system_lcoe_ct_per_kwh,
        }
        return result
