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
import io
import zipfile
from typing import List, Dict, Any, Optional
from config_manager import ConfigManager
from data_processing.storage_simulation import StorageSimulation
from data_processing.heat_pump_simulation import HeatPumpSimulation
from data_processing.balance_calculator import BalanceCalculator
from data_processing.generation_simulation import simulate_production
from data_processing.consumption_simulation import simulate_consumption_all
from data_processing.economic_calculator import calculate_economics_from_simulation
from data_processing.e_mobility_simulation import (
    simulate_emobility_fleet, 
    generate_ev_profile,
    EVConfigParams, 
    EVScenarioParams,
    validate_ev_results
)
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
        verbose: bool = False,
        calculation_mode: str = "cpu_optimized"
    ):
        """
        Initialisiert die Simulation Engine mit benötigten Managern.
        
        Args:
            cfg: ConfigManager für Konfigurationszugriff
            data_manager: DataManager für Rohdaten (SMARD, BDEW, Wetter)
            scenario_manager: ScenarioManager für Szenario-Parameter
            verbose: Wenn True, detaillierte Logging-Ausgaben
            calculation_mode: Berechnungsmodus für Wärmepumpen ("normal", "cpu_optimized")
        """
        self.cfg = cfg
        self.dm = data_manager
        self.sm = scenario_manager
        self.logger = _SimpleLogger(verbose=verbose)
        self.calculation_mode = calculation_mode
        
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
            Dictionary mit allen Simulationsergebnissen für dieses Jahr:
            - consumption: BDEW + Wärmepumpen + E-Mobility Verbrauch
            - production: Erzeugung
            - emobility: E-Mobility Details (Verbrauch + V2G/SOC/Charge/Discharge)
            - storage: Speicher Details (SOC, Geladene, Entladene für alle Speicher)
            - balance_pre_flex: Bilanz VOR Flexibilitäten (nur Bilanz-Spalten)
            - balance_after_emob: Bilanz NACH E-Mobility V2G, VOR Speichern
            - balance_post_flex: Bilanz NACH allen Flexibilitäten (nur Bilanz-Spalten)
            - economics: Wirtschaftlichkeit
        """
        # 1) Verbrauchssimulation (BDEW + Wärmepumpen)
        df_cons = self._simulate_consumption(year, year_num, total_years)
        
        # 2) Erzeugungssimulation
        df_prod = self._simulate_production(year, year_num, total_years)
        
        # 3) E-MOBILITY-VERBRAUCH (gehört zur Last!)
        df_cons, df_emobility_consumption = self._simulate_emobility_consumption(df_cons, year, year_num, total_years)
        
        # 4) BILANZ VOR FLEXIBILITÄTEN (Erzeugung - Gesamt-Verbrauch inkl. E-Mobility)
        df_balance_pre = self._calculate_balance(df_prod, df_cons, year, year_num, total_years)

        # 5) E-MOBILITY V2G FLEXIBILITÄT (bidirektionales Laden)
        df_emobility_full, df_balance_after_emob = self._simulate_emobility_flexibility(
            df_balance_pre.copy(), df_emobility_consumption, year, year_num, total_years
        )

        # 6) SPEICHER-FLEXIBILITÄT (Batterie -> Pumpspeicher -> H2)
        df_storage, df_balance_post = self._simulate_storage(df_balance_after_emob.copy(), year, year_num, total_years)
        
        # 7) Wirtschaftlichkeitsanalyse
        econ_result = self._calculate_economics(df_prod, df_cons, df_balance_pre, df_balance_post, year, year_num, total_years)
        
        return {
            "consumption": df_cons,                    # BDEW + Wärmepumpen + E-Mobility Verbrauch
            "production": df_prod,                     # Erzeugung
            "emobility": df_emobility_full,            # E-Mobility mit ALLEN Daten (Verbrauch + V2G)
            "storage": df_storage,                     # Separate Speicher-Daten
            "balance_pre_flex": df_balance_pre,        # Bilanz vor Flexibilitäten (ursprünglich)
            "balance_after_emob": df_balance_after_emob,  # Bilanz nach E-Mobility V2G, VOR Speichern
            "balance_post_flex": df_balance_post,      # Finale Bilanz nach allen Flexibilitäten
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
                debug=self.logger.verbose,
                calculation_mode=self.calculation_mode
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
    
    def _simulate_emobility_consumption(
        self,
        df_cons: pd.DataFrame,
        year: int,
        year_num: int,
        total_years: int
    ) -> tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Berechnet E-Mobility als VERBRAUCHSKOMPONENTE (nicht als Flexibilität).
        
        Fügt df_consumption folgende Spalten hinzu:
        - E-Mobility Fahrverbrauch [MWh]
        - E-Mobility Ladeverluste [MWh]  
        - E-Mobility [MWh] (Summe)
        
        Aktualisiert:
        - Gesamt [MWh] um E-Mobility-Verbrauch
        
        Args:
            df_cons: DataFrame mit Verbrauchsdaten
            year: Simulationsjahr
            year_num: Fortschrittszähler
            total_years: Gesamtzahl der Jahre
            
        Returns:
            Tuple: (Erweitertes df_consumption mit E-Mobility-Verbrauch, E-Mobility Ergebnis-DataFrame)
        """
        self.logger.start_step(f"[{year_num}/{total_years}] E-Mobilitäts-Verbrauch {year}")
        
        try:
            # Hole E-Mobility Parameter aus Szenario
            em_data = self.sm.get_emobility_parameters(year)
            
            if not em_data:
                self.logger.warning(f"Keine E-Mobility-Parameter für {year} definiert - überspringe")
                return df_cons, None
            
            # Prüfe ob neue Parameter vorhanden sind
            if 's_EV' not in em_data and 'N_cars' not in em_data:
                self.logger.warning(f"E-Mobility-Parameter unvollständig für {year} - überspringe")
                return df_cons, None
            
            # Szenario-Parameter aus YAML
            scenario_params = EVScenarioParams(
                s_EV=em_data.get('s_EV', 0.9),
                N_cars=int(em_data.get('N_cars', em_data.get('installed_units', 5_000_000))),
                E_drive_car_year=em_data.get('E_drive_car_year', 2250.0),
                E_batt_car=em_data.get('E_batt_car', 50.0),
                plug_share_max=em_data.get('plug_share_max', 0.6),
                SOC_min_day=em_data.get('SOC_min_day', 0.4),
                SOC_min_night=em_data.get('SOC_min_night', 0.2),
                SOC_target_depart=em_data.get('SOC_target_depart', 0.6),
                t_depart=str(em_data.get('t_depart', "07:30")),
                t_arrive=str(em_data.get('t_arrive', "18:00")),
                thr_surplus=float(em_data.get('thr_surplus', 200_000.0)),
                thr_deficit=float(em_data.get('thr_deficit', 200_000.0))
            )
            
            # Config-Parameter aus config.json laden
            ev_config_data = self.cfg.config.get("EV_PARAMETERS", {})
            config_params = EVConfigParams(
                SOC0=ev_config_data.get("SOC0", 0.6),
                eta_ch=ev_config_data.get("eta_ch", 0.95),
                eta_dis=ev_config_data.get("eta_dis", 0.95),
                P_ch_car_max=ev_config_data.get("P_ch_car_max", 11.0),
                P_dis_car_max=ev_config_data.get("P_dis_car_max", 11.0),
                dt_h=ev_config_data.get("dt_h", 0.25)
            )
            
            # Hole Zeitstempel aus consumption DataFrame
            if 'Zeitpunkt' in df_cons.columns:
                timestamps = pd.to_datetime(df_cons['Zeitpunkt'])
            else:
                timestamps = df_cons.index if isinstance(df_cons.index, pd.DatetimeIndex) else pd.to_datetime(df_cons.index)
            
            # Berechne E-Mobility Verbrauch
            n_ev = scenario_params.s_EV * scenario_params.N_cars
            
            # Generiere EV-Profil
            df_ev_profile = generate_ev_profile(timestamps, scenario_params, config_params)
            
            # Berechne Fahrverbrauch in MWh (drive_power_kw ist in kW)
            # drive_power_kw [kW] * dt_h [h] = Energie pro Zeitschritt [kWh] -> / 1000 = [MWh]
            e_mobility_drive_mwh = df_ev_profile['drive_power_kw'].values * config_params.dt_h / 1000.0
            
            # Ladeverluste: 5-10% vom Fahrverbrauch (verwende 7.5% als Mittelwert)
            charging_loss_factor = 0.075
            e_mobility_loss_mwh = e_mobility_drive_mwh * charging_loss_factor
            
            # Gesamt E-Mobility Verbrauch
            e_mobility_total_mwh = e_mobility_drive_mwh + e_mobility_loss_mwh
            
            # Erstelle E-Mobility Ergebnis-DataFrame
            df_emobility = pd.DataFrame({
                'Zeitpunkt': timestamps,
                'Fahrverbrauch [MWh]': e_mobility_drive_mwh,
                'Ladeverluste [MWh]': e_mobility_loss_mwh,
                'Gesamt Verbrauch [MWh]': e_mobility_total_mwh,
                'Anzahl Fahrzeuge': n_ev,
                'Angeschlossene Quote': df_ev_profile['plug_share'].values,
                'Fahrleistung [kW]': df_ev_profile['drive_power_kw'].values
            })
            
            # Füge NUR die Summe zu df_cons hinzu (Details sind im E-Mobility Tab)
            df_cons = df_cons.copy()
            df_cons['E-Mobility [MWh]'] = e_mobility_total_mwh
            
            # Aktualisiere Gesamt-Verbrauch
            if 'Gesamt [MWh]' in df_cons.columns:
                df_cons['Gesamt [MWh]'] = df_cons['Gesamt [MWh]'] + e_mobility_total_mwh
            
            # Berechne Statistiken für Logging
            total_emobility_twh = e_mobility_total_mwh.sum() / 1e6
            total_drive_twh = e_mobility_drive_mwh.sum() / 1e6
            total_loss_twh = e_mobility_loss_mwh.sum() / 1e6
            
            self.logger.finish_step(
                True, 
                f"{n_ev/1e6:.1f} Mio EVs, Verbrauch: {total_emobility_twh:.2f} TWh (Fahren: {total_drive_twh:.2f}, Verluste: {total_loss_twh:.2f})"
            )
            
            return df_cons, df_emobility
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            self.logger.warning(f"E-Mobilitäts-Verbrauch übersprungen: {e}")
            # Bei Fehler: Original-DataFrame zurückgeben (graceful degradation)
            return df_cons, None

    def _simulate_emobility_flexibility(
        self,
        df_balance: pd.DataFrame,
        df_emobility_consumption: Optional[pd.DataFrame],
        year: int,
        year_num: int,
        total_years: int
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Wendet E-Mobility V2G-Flexibilität auf die Bilanz an.
        
        Args:
            df_balance: Bilanz vor E-Mobility Flexibilität
            df_emobility_consumption: E-Mobility Verbrauchsdaten aus _simulate_emobility_consumption
            year: Simulationsjahr
            year_num: Fortschrittszähler
            total_years: Gesamtzahl der Jahre
            
        Returns:
            Tuple: (df_emobility_full mit allen Spalten, df_balance mit aktualisierter Rest Bilanz)
        """
        self.logger.start_step(f"[{year_num}/{total_years}] E-Mobilitäts-Flexibilität (V2G) {year}")
        
        try:
            # Hole E-Mobility Parameter aus Szenario
            em_data = self.sm.get_emobility_parameters(year)
            
            if not em_data or df_emobility_consumption is None:
                self.logger.warning(f"Keine E-Mobility-Flexibilität für {year} - überspringe V2G")
                # Erstelle leeres E-Mobility DF mit Verbrauchsdaten falls vorhanden
                if df_emobility_consumption is not None:
                    df_emob_full = df_emobility_consumption.copy()
                else:
                    df_emob_full = pd.DataFrame()
                return df_emob_full, df_balance
            
            # Szenario-Parameter aus YAML
            scenario_params = EVScenarioParams(
                s_EV=em_data.get('s_EV', 0.9),
                N_cars=int(em_data.get('N_cars', em_data.get('installed_units', 5_000_000))),
                E_drive_car_year=em_data.get('E_drive_car_year', 2250.0),
                E_batt_car=em_data.get('E_batt_car', 50.0),
                plug_share_max=em_data.get('plug_share_max', 0.6),
                v2g_share=em_data.get('v2g_share', 0.3),
                SOC_min_day=em_data.get('SOC_min_day', 0.4),
                SOC_min_night=em_data.get('SOC_min_night', 0.2),
                SOC_target_depart=em_data.get('SOC_target_depart', 0.6),
                t_depart=str(em_data.get('t_depart', "07:30")),
                t_arrive=str(em_data.get('t_arrive', "18:00")),
                thr_surplus=float(em_data.get('thr_surplus', 200_000.0)),
                thr_deficit=float(em_data.get('thr_deficit', 200_000.0))
            )
            
            # Config-Parameter aus config.json laden
            ev_config_data = self.cfg.config.get("EV_PARAMETERS", {})
            config_params = EVConfigParams(
                SOC0=ev_config_data.get("SOC0", 0.6),
                eta_ch=ev_config_data.get("eta_ch", 0.95),
                eta_dis=ev_config_data.get("eta_dis", 0.95),
                P_ch_car_max=ev_config_data.get("P_ch_car_max", 11.0),
                P_dis_car_max=ev_config_data.get("P_dis_car_max", 11.0),
                dt_h=ev_config_data.get("dt_h", 0.25)
            )
            
            # Rufe simulate_emobility_fleet auf (macht V2G)
            df_result = simulate_emobility_fleet(
                df_balance=df_balance,
                scenario_params=scenario_params,
                config_params=config_params
            )
            
            # Extrahiere E-Mobility Spalten
            emob_cols = ['Zeitpunkt', 'EMobility SOC [MWh]', 'EMobility Charge [MWh]', 
                        'EMobility Discharge [MWh]', 'EMobility Drive [MWh]', 'EMobility Power [MW]']
            
            # Kombiniere mit Verbrauchsdaten
            df_emobility_full = df_result[emob_cols].copy()
            if df_emobility_consumption is not None:
                # Füge Verbrauchsstatistiken hinzu
                for col in df_emobility_consumption.columns:
                    if col not in df_emobility_full.columns:
                        df_emobility_full[col] = df_emobility_consumption[col]
            
            # Erstelle sauberes Balance DataFrame (nur Bilanz-Spalten)
            df_balance_clean = pd.DataFrame({
                'Zeitpunkt': df_result['Zeitpunkt'],
                'Produktion [MWh]': df_balance['Produktion [MWh]'].values if 'Produktion [MWh]' in df_balance.columns else df_result.get('Produktion [MWh]', 0),
                'Verbrauch [MWh]': df_balance['Verbrauch [MWh]'].values if 'Verbrauch [MWh]' in df_balance.columns else df_result.get('Verbrauch [MWh]', 0),
                'Bilanz [MWh]': df_balance['Bilanz [MWh]'].values if 'Bilanz [MWh]' in df_balance.columns else df_result.get('Bilanz [MWh]', 0),
                'Rest Bilanz [MWh]': df_result['Rest Bilanz [MWh]']
            })
            
            n_ev = scenario_params.s_EV * scenario_params.N_cars
            v2g_energy = df_emobility_full['EMobility Discharge [MWh]'].sum()
            charge_energy = df_emobility_full['EMobility Charge [MWh]'].sum()
            
            self.logger.finish_step(
                True,
                f"{n_ev/1e6:.1f} Mio EVs, V2G: {v2g_energy/1e6:.2f} TWh entladen, {charge_energy/1e6:.2f} TWh geladen"
            )
            
            return df_emobility_full, df_balance_clean
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            self.logger.warning(f"E-Mobilitäts-Flexibilität übersprungen: {e}")
            # Bei Fehler: Verbrauchsdaten + Original-Balance zurückgeben
            if df_emobility_consumption is not None:
                df_emob_full = df_emobility_consumption.copy()
            else:
                df_emob_full = pd.DataFrame()
            return df_emob_full, df_balance

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
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Führt die Speichersimulation aus (Batterie -> Pumpspeicher -> H2).
        
        Returns:
            Tuple: (df_storage mit Speicher-Spalten, df_balance mit nur Bilanz-Spalten)
        """
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
            
            # Trenne Speicher-Spalten von Bilanz-Spalten
            storage_cols = ['Zeitpunkt'] + [c for c in res_h2.columns if 'speicher' in c.lower() or 'SOC' in c or 'Geladene' in c or 'Entladene' in c]
            balance_cols = ['Zeitpunkt', 'Produktion [MWh]', 'Verbrauch [MWh]', 'Bilanz [MWh]', 'Rest Bilanz [MWh]']
            
            df_storage = res_h2[storage_cols].copy()
            df_balance = res_h2[[c for c in balance_cols if c in res_h2.columns]].copy()
            
            self.logger.finish_step(True)
            return df_storage, df_balance
            
        except Exception as e:
            self.logger.finish_step(False, str(e))
            raise RuntimeError(f"Speichersimulation {year} fehlgeschlagen: {e}")
    
    def _calculate_economics(
        self,
        df_prod: pd.DataFrame,
        df_cons: pd.DataFrame,
        df_balance_pre: pd.DataFrame,
        df_balance_post: pd.DataFrame,
        year: int,
        year_num: int,
        total_years: int
    ) -> Dict[str, Any]:
        """Führt die Wirtschaftlichkeitsanalyse aus.
        
        Args:
            df_prod: Erzegungs-DataFrame
            df_cons: Verbrauchs-DataFrame (inkl. E-Mobility)
            df_balance_pre: Bilanz VOR Flexibilitäten (für Referenz)
            df_balance_post: Bilanz NACH Flexibilitäten (finale Bilanz)
            year: Simulationsjahr
            year_num: Fortschrittszähler
            total_years: Gesamtzahl der Jahre
        """
        self.logger.start_step(f"[{year_num}/{total_years}] Wirtschaftlichkeitsanalyse {year}")
        
        try:
            econ_result = calculate_economics_from_simulation(
                scenario_manager=self.sm,
                simulation_results={
                    "production": df_prod,
                    "consumption": df_cons,
                    "balance": df_balance_post,  # Nutze finale Bilanz nach allen Flexibilitäten
                    "storage": df_balance_pre    # Dummy-Eintrag, wird aktuell nicht genutzt
                },
                target_year=year,
                baseline_capacities=None  # Nutzt automatisch BASELINE_2025_DEFAULTS
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

    def export_results_to_excel(results: Dict[int, Dict[str, Any]], year: int) -> io.BytesIO:
        """
        Exportiert die Simulationsergebnisse eines Jahres in eine Excel-Datei.
        Optimiert für schnelle Generierung.
        
        Args:
            results: Gesamtergebnis-Dictionary von run_scenario()
            year: Jahr, das exportiert werden soll.
        
        Returns:
            io.BytesIO Objekt mit den Ergebnissen.
        """
        output = io.BytesIO()
        year_data = results.get(year)
        if not year_data:
            raise ValueError(f"Keine Ergebnisse für Jahr {year} gefunden.")
        
        # Optimierte ExcelWriter-Einstellungen für bessere Performance
        with pd.ExcelWriter(output, engine='openpyxl', mode='w') as writer:
            # Verbrauch (inkl. E-Mobility)
            year_data['consumption'].to_excel(writer, sheet_name='Verbrauch', index=True)
            # Erzeugung
            year_data['production'].to_excel(writer, sheet_name='Erzeugung', index=True)
            # E-Mobility (wenn vorhanden)
            if year_data.get('emobility') is not None and not year_data['emobility'].empty:
                year_data['emobility'].to_excel(writer, sheet_name='E-Mobility', index=True)
            # Speicher (wenn vorhanden)
            if year_data.get('storage') is not None and not year_data['storage'].empty:
                year_data['storage'].to_excel(writer, sheet_name='Speicher', index=True)
            # Bilanz VOR Flexibilitäten
            year_data['balance_pre_flex'].to_excel(writer, sheet_name='Bilanz_vor_Flex', index=True)
            # Bilanz NACH Flexibilitäten
            year_data['balance_post_flex'].to_excel(writer, sheet_name='Bilanz_nach_Flex', index=True)
            # Wirtschaftlichkeit
            econ_df = pd.DataFrame.from_dict(year_data['economics'], orient='index', columns=['Wert'])
            econ_df.to_excel(writer, sheet_name='Wirtschaftlichkeit', index=True)
        
        output.seek(0)
        return output
    
    def export_results_to_zip(results: Dict[int, Dict[str, Any]]) -> io.BytesIO:
        """
        Exportiert die Simulationsergebnisse aller Jahre in eine ZIP-Datei mit Excel-Dateien.
        Optimiert mit direktem Schreiben statt mehrfacher Excel-Generierung.
        
        Args:
            results: Gesamtergebnis-Dictionary von run_scenario()
        Returns:
            io.BytesIO Objekt mit der ZIP-Datei.
        """
        zip_buffer = io.BytesIO()
        # Komprimierung als 'stored' für schnelleres Schreiben, dann können Dateien bereits gezippt sein
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            for year in sorted(results.keys()):
                excel_buffer = SimulationEngine.export_results_to_excel(results, year)
                zip_file.writestr(f"simulationsergebnisse_{year}.xlsx", excel_buffer.getvalue())
        
        zip_buffer.seek(0)
        return zip_buffer