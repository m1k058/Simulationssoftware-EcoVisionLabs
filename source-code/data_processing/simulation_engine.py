"""
Simulation Engine - Zentrale Koordination der Energiesystem-Simulation.

Dieser Engine führt die komplette Simulationspipeline aus:
1. Verbrauchssimulation (BDEW + Wärmepumpen + E-Mobilität)
2. Erzeugungssimulation (SMARD-basiert, skaliert auf Zielkapazitäten)
3. Bilanzberechnung (Erzeugung - Verbrauch)
4. Speichersimulation (Batterie -> Pumpspeicher -> Wasserstoff)
5. Wirtschaftlichkeitsanalyse (CAPEX/OPEX/LCOE)

"""

import pandas as pd
from typing import List, Dict, Any, Optional
from config_manager import ConfigManager
from data_processing.storage_simulation import StorageSimulation
from data_processing.heat_pump_simulation import HeatPumpSimulation
from data_processing.balance_calculator import BalanceCalculator
from data_processing.generation_simulation import simulate_production
from data_processing.consumption_simulation import simulate_consumption_all
from data_processing.economic_calculator import calculate_economics_from_simulation
from constants import HEATPUMP_LOAD_PROFILE_NAME


class _SimpleLogger:
    """Einfacher Logger für die Simulation."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.steps = []
        
    def start_step(self, msg: str, detail: str = ""):
        if self.verbose:
            print(f"  ▶ {msg}" + (f": {detail}" if detail else ""))
            
    def finish_step(self, success: bool, msg: str = ""):
        if self.verbose:
            status = "✓" if success else "✗"
            print(f"    {status}" + (f" {msg}" if msg else ""))
            
    def warning(self, msg: str):
        if self.verbose:
            print(f"  ⚠ {msg}")
            
    def print_summary(self):
        pass  # Optional: implement if needed


class SimulationEngine:
    """
    Zentrale Engine für die Energiesystem-Simulation.
    
    Koordiniert alle Simulationsschritte und verwaltet den Datenfluss zwischen
    den spezialisierten Modulen. Ersetzt die monolithische "kobi"-Funktion.
    """
    
    def __init__(
        self,
        cfg: ConfigManager,
        data_manager,
        scenario_manager,
        verbose: bool = False
    ):
        """
        Initialisiert die Simulation Engine mit benötigten Managern.
        
        Args:
            cfg: ConfigManager für Konfigurationszugriff
            data_manager: DataManager für Rohdaten (SMARD, BDEW, Wetter)
            scenario_manager: ScenarioManager für Szenario-Parameter
            verbose: Wenn True, detaillierte Logging-Ausgaben
        """
        self.cfg = cfg
        self.dm = data_manager
        self.sm = scenario_manager
        self.logger = _SimpleLogger(verbose=verbose)
        
        # Initialisiere spezialisierte Module
        self.storage_sim = StorageSimulation()
        self.heatpump_sim = HeatPumpSimulation()
        self.balance_calc = BalanceCalculator()
    
    def run_scenario(self, years: Optional[List[int]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Führt die vollständige Simulation für alle Jahre aus.
        
        Args:
            years: Liste der zu simulierenden Jahre. Wenn None, aus Szenario entnommen.
        
        Returns:
            Dictionary mit Struktur:
            {
                jahr: {
                    "consumption": pd.DataFrame,
                    "production": pd.DataFrame,
                    "balance": pd.DataFrame,
                    "storage": pd.DataFrame,
                    "economics": dict
                }
            }
        """
        self.logger.start_step("Simulation wird vorbereitet", "Laden von Konfiguration und Daten")
        
        # Jahre bestimmen
        if years is None:
            years = self.sm.scenario_data.get("metadata", {}).get("valid_for_years", [])
            if not years:
                self.logger.finish_step(False, "Keine gültigen Jahre im Szenario gefunden")
                raise ValueError("Keine gültigen Jahre im Szenario gefunden und keine years übergeben.")
        
        self.logger.finish_step(True, f"{len(years)} Jahre identifiziert: {years}")
        
        # Lade Basisdaten (einmalig)
        self._load_base_data()
        
        # Simuliere jedes Jahr
        results = {}
        for idx, year in enumerate(years, 1):
            year_result = self._simulate_year(year, idx, len(years))
            results[year] = year_result
        
        # Abschließende Zusammenfassung
        self.logger.print_summary()
        return results
    
    def _load_base_data(self):
        """Lädt alle Basisdaten, die für alle Jahre benötigt werden."""
        self.logger.start_step("Verbrauchsprofile werden geladen")
        try:
            load_cfg = self.sm.scenario_data.get("target_load_demand_twh", {})
            last_H_name = load_cfg["Haushalt_Basis"]["load_profile"]
            last_G_name = load_cfg["Gewerbe_Basis"]["load_profile"]
            last_L_name = load_cfg["Landwirtschaft_Basis"]["load_profile"]
            
            self.last_H = self.dm.get(last_H_name)
            self.last_G = self.dm.get(last_G_name)
            self.last_L = self.dm.get(last_L_name)
            self.logger.finish_step(True, "H/G/L-Profile erfolgreich geladen")
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise KeyError(f"Fehlende Load-Profile in Szenario: {e}")
        
        # SMARD-Daten laden
        self.logger.start_step("SMARD-Erzeugungsdaten werden geladen")
        try:
            self.smard_generation = pd.concat([
                self.dm.get("SMARD_2015-2019_Erzeugung"),
                self.dm.get("SMARD_2020-2025_Erzeugung"),
            ])
            self.smard_installed = pd.concat([
                self.dm.get("SMARD_Installierte Leistung 2015-2019"),
                self.dm.get("SMARD_Installierte Leistung 2020-2025"),
            ])
            self.logger.finish_step(True)
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise
        
        # Ziel-Kapazitäten und Wetterprofile
        self.capacity_dict = self.sm.get_generation_capacities()
        self.weather_profiles = self.sm.scenario_data.get("weather_generation_profiles", {})
    
    def _simulate_year(self, year: int, year_num: int, total_years: int) -> Dict[str, Any]:
        """
        Simuliert ein einzelnes Jahr komplett.
        
        Args:
            year: Simulationsjahr
            year_num: Fortschrittszähler (z.B. 1 von 3)
            total_years: Gesamtzahl der Jahre
        
        Returns:
            Dictionary mit allen Simulationsergebnissen für dieses Jahr
        """
        # 1) Verbrauchssimulation
        df_cons = self._simulate_consumption(year, year_num, total_years)
        
        # 2) Erzeugungssimulation
        df_prod = self._simulate_production(year, year_num, total_years)
        
        # 3) E-Mobilitätssimulation


        # 4) Bilanzberechnung
        df_bal = self._calculate_balance(df_prod, df_cons, year, year_num, total_years)

        # 5) Speichersimulation
        df_storage = self._simulate_storage(df_bal, year, year_num, total_years)

        # 6) Bilanzberechnung nach Speicher
        
        
        # 7) Wirtschaftlichkeitsanalyse
        econ_result = self._calculate_economics(df_prod, df_cons, df_bal, df_storage, year, year_num, total_years)
        
        return {
            "consumption": df_cons,
            "production": df_prod,
            "balance": df_bal,
            "storage": df_storage,
            "economics": econ_result,
        }
    
    def _simulate_consumption(self, year: int, year_num: int, total_years: int) -> pd.DataFrame:
        """Führt die Verbrauchssimulation aus (BDEW + Wärmepumpen)."""
        self.logger.start_step(f"[{year_num}/{total_years}] Verbrauchssimulation {year}")
        
        try:
            targets = self.sm.scenario_data.get("target_load_demand_twh", {})
            
            # Wärmepumpen-Konfiguration holen
            hp_config = self._get_heatpump_config(year)
            
            # Komplette Verbrauchssimulation (BDEW + Wärmepumpen)
            df_result = simulate_consumption_all(
                lastH=self.last_H,
                lastG=self.last_G,
                lastL=self.last_L,
                wetter_df=hp_config.get("wetter_df") if hp_config else None,
                hp_profile_matrix=hp_config.get("hp_profile_matrix") if hp_config else None,
                lastZielH=targets["Haushalt_Basis"][year],
                lastZielG=targets["Gewerbe_Basis"][year],
                lastZielL=targets["Landwirtschaft_Basis"][year],
                anzahl_heatpumps=hp_config.get("n_heatpumps", 0) if hp_config else 0,
                Q_th_a=hp_config.get("Q_th_a", 51000) if hp_config else 51000,
                COP_avg=hp_config.get("COP_avg", 3.4) if hp_config else 3.4,
                dt=0.25,
                simu_jahr=year,
                debug=self.logger.verbose
            )
            
            cons_twh = df_result['Gesamt [MWh]'].sum() / 1e6 if 'Gesamt [MWh]' in df_result.columns else 0
            self.logger.finish_step(True, f"{cons_twh:.1f} TWh")
            return df_result
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise RuntimeError(f"Verbrauchssimulation {year} fehlgeschlagen: {e}")
    
    def _simulate_production(self, year: int, year_num: int, total_years: int) -> pd.DataFrame:
        """Führt die Erzeugungssimulation aus."""
        self.logger.start_step(f"[{year_num}/{total_years}] Erzeugungssimulation {year}")
        
        try:
            wprof = self.weather_profiles.get(year, {})
            df_prod = simulate_production(
                self.cfg,
                self.smard_generation,
                self.smard_installed,
                self.capacity_dict,
                wprof.get("Wind_Onshore", "average"),
                wprof.get("Wind_Offshore", "average"),
                wprof.get("Photovoltaik", "average"),
                year,
            )
            prod_twh = df_prod[df_prod.columns[1:]].sum().sum() / 1e6 if len(df_prod.columns) > 1 else 0
            self.logger.finish_step(True, f"{prod_twh:.1f} TWh")
            return df_prod
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise RuntimeError(f"Erzeugungssimulation {year} fehlgeschlagen: {e}")
    
    def _calculate_balance(
        self, 
        df_prod: pd.DataFrame, 
        df_cons: pd.DataFrame, 
        year: int,
        year_num: int, 
        total_years: int
    ) -> pd.DataFrame:
        """Berechnet die Bilanz zwischen Erzeugung und Verbrauch."""
        self.logger.start_step(f"[{year_num}/{total_years}] Bilanzberechnung {year}")
        
        try:
            df_bal = self.balance_calc.calculate_balance(df_prod, df_cons, year)
            self.logger.finish_step(True)
            return df_bal
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise RuntimeError(f"Bilanzberechnung {year} fehlgeschlagen: {e}")
    
    def _simulate_storage(
        self, 
        df_bal: pd.DataFrame, 
        year: int,
        year_num: int, 
        total_years: int
    ) -> pd.DataFrame:
        """Führt die Speichersimulation aus (Batterie -> Pumpspeicher -> H2)."""
        self.logger.start_step(f"[{year_num}/{total_years}] Speichersimulation {year}")
        
        try:
            # Hole Speicher-Konfiguration aus Szenario
            stor_bat = self.sm.get_storage_capacities("battery_storage", year) or {}
            stor_pump = self.sm.get_storage_capacities("pumped_hydro_storage", year) or {}
            stor_h2 = self.sm.get_storage_capacities("h2_storage", year) or {}
            
            # Kaskade: Batterie -> Pumpspeicher -> Wasserstoff
            res_bat = self.storage_sim.simulate_battery_storage(
                df_bal,
                stor_bat.get("installed_capacity_mwh", 0.0),
                stor_bat.get("max_charge_power_mw", 0.0),
                stor_bat.get("max_discharge_power_mw", 0.0),
                stor_bat.get("initial_soc", 0.0),
            )
            
            res_pump = self.storage_sim.simulate_pump_storage(
                res_bat,
                stor_pump.get("installed_capacity_mwh", 0.0),
                stor_pump.get("max_charge_power_mw", 0.0),
                stor_pump.get("max_discharge_power_mw", 0.0),
                stor_pump.get("initial_soc", 0.0),
            )
            
            res_h2 = self.storage_sim.simulate_hydrogen_storage(
                res_pump,
                stor_h2.get("installed_capacity_mwh", 0.0),
                stor_h2.get("max_charge_power_mw", 0.0),
                stor_h2.get("max_discharge_power_mw", 0.0),
                stor_h2.get("initial_soc", 0.0),
            )
            
            self.logger.finish_step(True)
            return res_h2
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise RuntimeError(f"Speichersimulation {year} fehlgeschlagen: {e}")
    
    def _calculate_economics(
        self,
        df_prod: pd.DataFrame,
        df_cons: pd.DataFrame,
        df_bal: pd.DataFrame,
        df_storage: pd.DataFrame,
        year: int,
        year_num: int,
        total_years: int
    ) -> Dict[str, Any]:
        """Führt die Wirtschaftlichkeitsanalyse aus."""
        self.logger.start_step(f"[{year_num}/{total_years}] Wirtschaftlichkeitsanalyse {year}")
        
        try:
            econ_result = calculate_economics_from_simulation(
                scenario_manager=self.sm,
                simulation_results={
                    "production": df_prod,
                    "consumption": df_cons,
                    "balance": df_bal,
                    "storage": df_storage
                },
                target_year=year,
                baseline_capacities=None  # Wird automatisch geschätzt
            )
            
            lcoe = econ_result.get('system_lco_e', 0)
            self.logger.finish_step(True, f"LCOE: {lcoe:.2f} ct/kWh")
            return econ_result
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            self.logger.warning(f"Wirtschaftlichkeitsanalyse fehlgeschlagen: {e}")
            return {
                "year": float(year),
                "total_investment_bn": 0.0,
                "total_annual_cost_bn": 0.0,
                "system_lco_e": 0.0,
                "error": str(e)
            }
    
    def _get_heatpump_config(self, year: int) -> Optional[Dict[str, Any]]:
        """
        Lädt Wärmepumpen-Konfiguration für ein Jahr.
        
        Returns:
            Dictionary mit HP-Parametern oder None wenn keine WP konfiguriert
        """
        try:
            # Hole Jahres-HP-Konfiguration aus ScenarioManager
            if hasattr(self.sm, "get_heat_pump_parameters"):
                hp_config = self.sm.get_heat_pump_parameters(year) or {}
            else:
                hp_config = self.sm.scenario_data.get("target_heat_pump_parameters", {}).get(year, {})
            
            if not hp_config or hp_config.get("installed_units", 0) == 0:
                return None
            
            # Lade Wetterdaten
            wetter_df = None
            wd_name = hp_config.get("weather_data")
            if wd_name:
                try:
                    wetter_df = self.dm.get(wd_name)
                except Exception:
                    pass
            
            # Lade Lastprofil-Matrix
            hp_profile_matrix = None
            try:
                hp_profile_matrix = self.dm.get(HEATPUMP_LOAD_PROFILE_NAME)
            except Exception:
                pass
            
            # Nur zurückgeben wenn alle Daten vorhanden
            if wetter_df is None or hp_profile_matrix is None:
                return None
            
            return {
                "wetter_df": wetter_df,
                "hp_profile_matrix": hp_profile_matrix,
                "n_heatpumps": hp_config.get("installed_units", 0),
                "Q_th_a": hp_config.get("annual_heat_demand_kwh", 51000),
                "COP_avg": hp_config.get("cop_avg", 3.4),
            }
            
        except Exception:
            return None
