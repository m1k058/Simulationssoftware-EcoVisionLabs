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


# Baseline-Kapazitäten 2025
BASELINE_2025_DEFAULTS = {
    "Photovoltaik": 86408.0,
    "Wind Onshore": 63192.0,
    "Wind Offshore": 9215.0,
    "Biomasse": 8766.0,
    "Wasserkraft": 5350.0,
    "Erdgas": 36614.0,
    "Steinkohle": 15951.0,
    "Braunkohle": 15176.0,
    "Kernenergie": 0.0,
    "Pumpspeicher": 9384.0,
    "Sonstige Erneuerbare": 446.0,
    "Sonstige Konventionelle": 12971.0
}


class EconomicCalculator:
    """Performs investment and LCOE analysis between a base year and target year.

    Structure per requirements:
    - Stores `inputs` and `simulation_results` and uses base year 2025.
    - Computes annuity factor.
    - Computes variable OPEX from fuel and CO2 prices, efficiency, and CO2 factor.
    - Performs calculation of investments, annual costs, and system LCOE.
    """

    def __init__(self, inputs: Dict[str, Any], simulation_results: Dict[str, Any], 
                 target_storage_capacities: Optional[Dict[str, Any]] = None) -> None:
        self.inputs = inputs or {}
        self.simulation_results = simulation_results or {}
        self.target_storage_capacities = target_storage_capacities or {}
        self.base_year = 2025

    def _get_capex_value(self, capex_data: Any, mode: str = "average") -> float:
        """Extrahiere CAPEX-Wert aus Liste [Min, Max] oder Skalar.
        
        Args:
            capex_data: Kann sein [Min, Max] oder Skalar
            mode: "average" (default) für Durchschnitt, "min", "max", "conservative"
        
        Returns:
            float: CAPEX-Wert in EUR/MW
        """
        try:
            if isinstance(capex_data, (list, tuple)):
                if len(capex_data) >= 2:
                    min_val = float(capex_data[0])
                    max_val = float(capex_data[1])
                    
                    if mode == "min":
                        return min_val
                    elif mode == "max":
                        return max_val
                    elif mode == "conservative":  # Nutze Max für konservative Schätzung
                        return max_val
                    else:  # average
                        return (min_val + max_val) / 2.0
            # Skalar-Wert
            return float(capex_data or 0.0)
        except Exception:
            return 0.0

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
        """Berechne Brennstoffkosten-Beitrag zu variable Kosten in EUR/MWh_el.

        Dies ist NUR die Brennstoff- und CO2-Komponente, nicht die Verschleißkosten!
        
        Formel: (FuelPrice + (CO2_Price * CO2_Faktor)) / Wirkungsgrad
        - Falls kein `fuel_type` vorhanden ist, 0 zurückgeben.
        - Sucht Preise/Faktoren robust in `const.COMMODITIES`.
        
        RÜCKGABEWERT: EUR/MWh (bereits umgerechnet!)
        """
        try:
            commodities = getattr(const, "COMMODITIES", {}) or {}
            fuel_type = params.get("fuel_type")
            if not fuel_type:
                return 0.0

            # Efficiency guard
            eff = float(efficiency) if efficiency not in (None, 0) else 1.0
            if eff <= 0.0:
                return 0.0

            # Brennstoffpreis (neue flache Struktur: COMMODITIES[fuel_type])
            fuel_price = float(commodities.get(fuel_type, 0.0) or 0.0)

            # CO2-Preis
            co2_price = float(commodities.get("co2_price", 0.0) or 0.0)

            # CO2-Emissionsfaktor (fest kodiert, da nicht mehr in COMMODITIES)
            # Quelle: UBA - Erdgas: 0.2 t/MWh, Biomasse/H2: 0.0 t/MWh
            co2_emission_factors = {
                "Erdgas": 0.2,
                "Biomasse": 0.0,
                "Wasserstoff": 0.0
            }
            co2_factor = float(co2_emission_factors.get(fuel_type, 0.0))

            # Brennstoffkosten in EUR/MWh
            fuel_cost_eur_per_mwh = (fuel_price + (co2_price * co2_factor)) / eff
            return fuel_cost_eur_per_mwh
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

    def _normalize_cost_value(self, value: Any) -> float:
        """Normalisiere CAPEX/OPEX-Werte.
        
        Falls value eine Liste [Min, Max] ist: Durchschnitt ((Min+Max)/2).
        Sonst: zu float konvertieren.
        Gibt 0.0 zurück bei Fehler.
        """
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            try:
                return (float(value[0]) + float(value[1])) / 2.0
            except (TypeError, ValueError):
                return 0.0
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _is_thermal_technology(self, tech_id: str, params: Dict[str, Any]) -> bool:
        """Prüfe, ob Technologie thermisch ist (Brennstoff hat).
        
        Thermische Technologien: Erdgas, Biomasse, Kohle (Stein/Braun), H2-Kraftwerke.
        """
        thermal_keywords = [
            "erdgas", "gas", "h2", "hydrogen", "wasserstoff",
            "biomasse", "steinkohle", "braunkohle", "kohle"
        ]
        tech_id_lower = tech_id.lower()
        
        # Check in tech_id
        if any(kw in tech_id_lower for kw in thermal_keywords):
            return True
        
        # Check fuel_type in params
        fuel_type = params.get("fuel_type", "").lower()
        if fuel_type and any(kw in fuel_type for kw in thermal_keywords):
            return True
        
        return False

    def perform_calculation(self, target_year: int) -> Dict[str, float]:
        """Führt die Wirtschaftlichkeitsberechnung durch.
        """
        tech_costs = getattr(const, "TECHNOLOGY_COSTS", {}) or {}
        wacc_default = 0.05
        
        total_investment = 0.0  # EUR
        total_annual_cost = 0.0  # EUR per year

        # Detail-Tracker
        investment_by_tech: Dict[str, float] = {}
        capex_annual_by_tech: Dict[str, float] = {}
        opex_fix_by_tech: Dict[str, float] = {}
        opex_var_by_tech: Dict[str, float] = {}

        wacc = wacc_default
    
        flat_inputs = {}
        reserved_keys = {"storage", "storage_capacities", "storages"}
        for key, val in (self.inputs or {}).items():
            if key in reserved_keys and isinstance(val, dict):
                flat_inputs.update(val)
            else:
                flat_inputs[key] = val

        # Speicher
        storage_key_mapping = {
            "battery_storage": "Batteriespeicher",
            "h2_storage": "Wasserstoffspeicher",
            "pumped_hydro_storage": "Pumpspeicher"
        }
        
        for internal_key, tech_id in storage_key_mapping.items():
            storage_data = self.target_storage_capacities.get(internal_key, {})
            if storage_data:
                flat_inputs[tech_id] = storage_data

        for tech_id, tech_inputs in flat_inputs.items():
            if not isinstance(tech_inputs, dict) or not tech_inputs:
                continue
            
            params = tech_costs.get(tech_id, {}) or {}
            if not params:
                continue

            # Capex
            capex_data = params.get("capex", [0, 0])
            capex_eur_per_mw = self._get_capex_value(capex_data, mode="average")
            
            lifetime = float(params.get("lifetime", 20.0) or 20.0)
            efficiency = float(params.get("efficiency", 1.0) or 1.0)

            # Opex fix
            opex_fix_eur_per_mw = float(params.get("opex_fix", 0.0) or 0.0)
            
            # Opex var
            opex_var_eur_per_mwh = float(params.get("opex_var", 0.0) or 0.0)

            # helper
            def extract_val(data, key: str, fallback: float = 0.0) -> float:
                """Extrahiert Wert aus Input-Daten (dict oder direkt float)."""
                if isinstance(data, dict):
                    return float(data.get(key, fallback) or fallback)
                return float(data or fallback)

            # kapazitäten
            is_storage = tech_id in ["Batteriespeicher", "Wasserstoffspeicher"]
            
            if is_storage:
                # Speicher
                capacity_base_mwh = extract_val(tech_inputs.get(self.base_year, 0), "installed_capacity_mwh", 0.0)
                capacity_target_mwh = extract_val(tech_inputs.get(target_year, 0), "installed_capacity_mwh", 0.0)
                
                # Capex
                p_base_for_capex = capacity_base_mwh
                p_target_for_capex = capacity_target_mwh
                
                # Opex fix
                p_base_mw = extract_val(tech_inputs.get(self.base_year, 0), "max_discharge_power_mw", capacity_base_mwh)
                p_target_mw = extract_val(tech_inputs.get(target_year, 0), "max_discharge_power_mw", capacity_target_mwh)
            else:
                # Erzeuger
                p_base_mw = self._get_capacity(tech_inputs, self.base_year)
                p_target_mw = self._get_capacity(tech_inputs, target_year)
                
                p_base_for_capex = p_base_mw
                p_target_for_capex = p_target_mw

            # CAPEX BERECHNUNG
            # 1. Investitionsbedarf (Delta)
            delta_p = max(0.0, p_target_for_capex - p_base_for_capex)
            investment = delta_p * capex_eur_per_mw
            total_investment += investment
            investment_by_tech[tech_id] = investment

            # 2. Kapitalkosten (Annual Capital Cost)
            if lifetime > 0 and capex_eur_per_mw > 0:
                annuity_factor = self._calculate_annuity_factor(wacc, lifetime)
                annual_capital_cost = p_target_for_capex * capex_eur_per_mw * annuity_factor
            else:
                annual_capital_cost = 0.0

            # OPEX FIX BERECHNUNG
            annual_opex_fix = p_target_mw * opex_fix_eur_per_mw

            # OPEX VAR BERECHNUNG
            generation_mwh = self._get_generation(tech_id, target_year)
            
            base_var_cost_eur_per_mwh = opex_var_eur_per_mwh
            
            additional_var_cost = self._get_variable_opex_cost(
                tech_id=tech_id,
                year=target_year,
                efficiency=efficiency,
                params=params,
            )
            
            total_var_cost_eur_per_mwh = base_var_cost_eur_per_mwh + additional_var_cost
            
            annual_opex_var = generation_mwh * total_var_cost_eur_per_mwh

            is_thermal = "fuel_type" in params and params.get("fuel_type") is not None

            # Summen
            annual_cost = annual_capital_cost + annual_opex_fix + annual_opex_var
            total_annual_cost += annual_cost

            # Details
            capex_annual_by_tech[tech_id] = annual_capital_cost
            opex_fix_by_tech[tech_id] = annual_opex_fix
            opex_var_by_tech[tech_id] = annual_opex_var

        total_consumption_mwh = self._get_total_consumption(target_year)
        system_lcoe_eur_per_mwh = (
            (total_annual_cost / total_consumption_mwh) if total_consumption_mwh > 0 else 0.0
        )
        system_lcoe_ct_per_kwh = system_lcoe_eur_per_mwh * 0.1

        result = {
            "year": float(target_year),
            "total_investment_bn": total_investment / 1e9,
            "total_annual_cost_bn": total_annual_cost / 1e9,
            "system_lco_e": system_lcoe_ct_per_kwh,
            "investment_by_tech": {k: v / 1e9 for k, v in investment_by_tech.items()},
            "capex_annual_bn": sum(capex_annual_by_tech.values()) / 1e9,
            "opex_fix_bn": sum(opex_fix_by_tech.values()) / 1e9,
            "opex_var_bn": sum(opex_var_by_tech.values()) / 1e9,
            "capex_annual_by_tech": {k: v / 1e9 for k, v in capex_annual_by_tech.items()},
            "opex_fix_by_tech": {k: v / 1e9 for k, v in opex_fix_by_tech.items()},
            "opex_var_by_tech": {k: v / 1e9 for k, v in opex_var_by_tech.items()},
        }
        return result


# ---------------------------- #
#   Main Berechnungsfunktion   #
# ---------------------------- #

def calculate_economics_from_simulation(
    scenario_manager,
    simulation_results: Dict[str, Any],
    target_year: int,
    baseline_capacities: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Berechnet Wirtschaftlichkeitskennzahlen aus Simulationsergebnissen

    
    Args:
        scenario_manager: ScenarioManager mit Szenario-Konfiguration
        simulation_results: Dictionary mit Simulations-DataFrames:
            - "production": DataFrame mit Erzeugung [MWh] pro Technologie
            - "consumption": DataFrame mit Verbrauch [MWh]
            - "balance": Optional, wird nicht genutzt
            - "storage": Optional, wird nicht genutzt
        target_year: Zieljahr der Simulation (z.B. 2030, 2045)
        baseline_capacities: Optional, Dict mit Baseline-Kapazitäten [MW] pro Technologie
                            Falls None: Nutze BASELINE_2025_DEFAULTS
    
    Returns:
        Dictionary mit wirtschaftlichen KPIs:
        - year: Simulationsjahr
        - total_investment_bn: Gesamt-Investitionsbedarf [Mrd. €]
        - total_annual_cost_bn: Jährliche Gesamtkosten [Mrd. €/Jahr]
        - system_lco_e: System-LCOE [ct/kWh]
        - investment_by_tech: Investitionen pro Technologie [Mrd. €]
        - capex_annual_bn: Annualisierte CAPEX [Mrd. €/Jahr]
        - opex_fix_bn: Fixe OPEX [Mrd. €/Jahr]
        - opex_var_bn: Variable OPEX [Mrd. €/Jahr]
    """
    import pandas as pd
    
    try:
        # Technologie-Mappings: Szenario-IDs <-> DataFrame-Spalten
        tech_mapping = {
            'Photovoltaik': 'Photovoltaik [MWh]',
            'Wind_Onshore': 'Wind Onshore [MWh]',
            'Wind_Offshore': 'Wind Offshore [MWh]',
            'Biomasse': 'Biomasse [MWh]',
            'Wasserkraft': 'Wasserkraft [MWh]',
            'Erdgas': 'Erdgas [MWh]',
            'Steinkohle': 'Steinkohle [MWh]',
            'Braunkohle': 'Braunkohle [MWh]',
            'Kernenergie': 'Kernenergie [MWh]'
        }
        
        # 1. Hole Ziel-Kapazitäten aus ScenarioManager
        capacities_target_raw = scenario_manager.get_generation_capacities(year=target_year)
        
        capacities_target = {}
        for tech_id, val in capacities_target_raw.items():
            if isinstance(val, dict):
                capacities_target[tech_id] = val.get(target_year, 0)
            else:
                capacities_target[tech_id] = val
        
        # 2. Hole Speicher-Kapazitäten
        storage_targets = {
            "battery_storage": scenario_manager.get_storage_capacities("battery_storage", target_year) or {},
            "pumped_hydro_storage": scenario_manager.get_storage_capacities("pumped_hydro_storage", target_year) or {},
            "h2_storage": scenario_manager.get_storage_capacities("h2_storage", target_year) or {},
        }
        
        # 3. Bestimme Baseline-Kapazitäten
        if baseline_capacities is None:
            baseline_capacities = BASELINE_2025_DEFAULTS.copy()
        
        # 4. Strukturiere Inputs
        name_fix = {
            "Wind_Onshore": "Wind Onshore",
            "Wind_Offshore": "Wind Offshore",
            "Sonstige_Erneuerbare": "Sonstige Erneuerbare",
            "Sonstige_Konventionelle": "Sonstige Konventionelle"
        }
        
        inputs = {}
        
        # Erzeugungstechnologien
        for tech_id_raw, target_cap in capacities_target.items():
            if isinstance(target_cap, (int, float)) and target_cap > 0:
                tech_id = name_fix.get(tech_id_raw, tech_id_raw)
                
                base_val = baseline_capacities.get(tech_id_raw)
                if base_val is None:
                    base_val = baseline_capacities.get(tech_id)
                if base_val is None:
                    base_val = BASELINE_2025_DEFAULTS.get(tech_id, 0.0)
                
                inputs[tech_id] = {
                    2025: base_val,
                    target_year: target_cap
                }
        
        # Speicher
        storage_inputs = {}
        for storage_id, storage_config in storage_targets.items():
            if isinstance(storage_config, dict) and storage_config:
                baseline_storage = {
                    "installed_capacity_mwh": 0.0,
                    "max_charge_power_mw": 0.0,
                    "max_discharge_power_mw": 0.0,
                    "initial_soc": storage_config.get("initial_soc", 0.0)
                }
                storage_inputs[storage_id] = {
                    2025: baseline_storage,
                    target_year: storage_config
                }
        
        if storage_inputs:
            inputs["storage"] = storage_inputs
        
        # 5. Extrahiere Erzeugungsdaten aus Simulations-DataFrames
        df_production = simulation_results.get("production", pd.DataFrame())
        df_consumption = simulation_results.get("consumption", pd.DataFrame())
        
        generation_by_tech = {}
        for tech_id, df_col in tech_mapping.items():
            if df_col in df_production.columns:
                try:
                    gen_mwh = pd.to_numeric(df_production[df_col], errors='coerce').sum()
                    if pd.notna(gen_mwh) and gen_mwh > 0:
                        generation_by_tech[tech_id] = float(gen_mwh)
                except Exception:
                    pass
        
        # Gesamtverbrauch
        total_consumption_mwh = 0.0
        if "Gesamt [MWh]" in df_consumption.columns:
            total_consumption_mwh = float(pd.to_numeric(df_consumption["Gesamt [MWh]"], errors='coerce').sum())
        
        # 6. Strukturiere Simulationsergebnisse
        sim_results_formatted = {
            "generation": {target_year: generation_by_tech},
            "total_consumption": {target_year: total_consumption_mwh}
        }
        
        # 7. Führe Berechnung durch
        calculator = EconomicCalculator(
            inputs=inputs,
            simulation_results=sim_results_formatted,
            target_storage_capacities=storage_inputs
        )
        
        result = calculator.perform_calculation(target_year)
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "year": float(target_year),
            "total_investment_bn": 0.0,
            "total_annual_cost_bn": 0.0,
            "system_lco_e": 0.0,
            "error": str(e)
        }
