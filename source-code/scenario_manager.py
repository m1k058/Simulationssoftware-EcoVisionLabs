from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import copy
import yaml
import pandas as pd

class ScenarioManager:
    """Verwaltet Szenario-Konfigurationen für Simulationen."""
    
    def __init__(self, base_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        # Sicherstellen, dass der Szenario-Ordner immer im Projektwurzelverzeichnis liegt
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "scenarios"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Aktuell geladenes Szenario speichern
        self.current_scenario: Dict[str, Any] = {}
        self.current_path: Optional[Path] = None

    def _static_default_template(self) -> Dict[str, Any]:
        """Fallback-Dummy-Szenario, falls die Beispiel-YAML fehlt."""
        return {
            "metadata": {
                "name": "Szenario Beispiel",
                "valid_for_years": [2030, 2045],
                "description": "Beispielhaftes Szenario mit plausiblen Dummy-Werten zur Simulation.",
                "version": "0.0.0",
                "author": "SW-Team EcoVisionLabs",
            },
            "target_load_demand_twh": {
                "Haushalt_Basis": {2030: 130, 2045: 120, "load_profile": "BDEW-25-Haushalte"},
                "Gewerbe_Basis": {2030: 140, 2045: 130, "load_profile": "BDEW-25-Gewerbe"},
                "Landwirtschaft_Basis": {2030: 280, 2045: 350, "load_profile": "BDEW-25-Landwirtschaft"},
                "EMobility": {2030: 60, 2045: 140, "load_profile": "EMobility-self"},
                "Heat_Pumps": {2030: 50, 2045: 110, "load_profile": "HeatPumps-self"},
            },
            "target_generation_capacities_mw": {
                "Photovoltaik": {2030: 215000, 2045: 400000},
                "Wind_Onshore": {2030: 115000, 2045: 160000},
                "Wind_Offshore": {2030: 30000, 2045: 70000},
                "Biomasse": {2030: 8500, 2045: 6000},
                "Wasserkraft": {2030: 5000, 2045: 5000},
                "Erdgas": {2030: 25000, 2045: 40000},
                "Steinkohle": {2030: 0, 2045: 0},
                "Braunkohle": {2030: 0, 2045: 0},
                "Kernenergie": {2030: 0, 2045: 0},
            },
            "weather_generation_profiles": {
                2030: {"Wind_Offshore": "good", "Wind_Onshore": "average", "Photovoltaik": "average"},
                2045: {"Wind_Offshore": "bad", "Wind_Onshore": "good", "Photovoltaik": "good"},
            },
            "target_storage_capacities": {
                "battery_storage": {
                    2030: {
                        "installed_capacity_mwh": 60000,
                        "max_charge_power_mw": 20000,
                        "max_discharge_power_mw": 20000,
                        "initial_soc": 0.5,
                    },
                    2045: {
                        "installed_capacity_mwh": 180000,
                        "max_charge_power_mw": 60000,
                        "max_discharge_power_mw": 60000,
                        "initial_soc": 0.5,
                    },
                },
                "pumped_hydro_storage": {
                    2030: {
                        "installed_capacity_mwh": 40000,
                        "max_charge_power_mw": 7000,
                        "max_discharge_power_mw": 7000,
                        "initial_soc": 0.6,
                    },
                    2045: {
                        "installed_capacity_mwh": 45000,
                        "max_charge_power_mw": 8000,
                        "max_discharge_power_mw": 8000,
                        "initial_soc": 0.6,
                    },
                },
                "h2_storage": {
                    2030: {
                        "installed_capacity_mwh": 500000,
                        "max_charge_power_mw": 10000,
                        "max_discharge_power_mw": 10000,
                        "initial_soc": 0.4,
                    },
                    2045: {
                        "installed_capacity_mwh": 3000000,
                        "max_charge_power_mw": 60000,
                        "max_discharge_power_mw": 40000,
                        "initial_soc": 0.45,
                    },
                },
            },
        }

    def default_template(self) -> Dict[str, Any]:
        """Lädt das Beispiel-Szenario aus /scenarios/Szenario_Beispiel_SW.yaml, Fallback auf statisch."""
        example_path = self.base_dir / "scenarios" / "Szenario_Beispiel_SW.yaml"
        if example_path.exists():
            try:
                with open(example_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    return copy.deepcopy(loaded)
            except Exception:
                # Im Fehlerfall auf statische Defaults zurückfallen
                pass
        return self._static_default_template()

    def create_scenario_yaml(self, scenario_data: Dict[str, Any]) -> str:
        """
        Erstellt einen YAML-String aus Scenario-Daten.

        Erwartet ein Dictionary mit: metadata, target_load_demand_twh, target_generation_capacities_mw,
        weather_generation_profiles, target_storage_capacities.
        """
        if "metadata" not in scenario_data or "name" not in scenario_data.get("metadata", {}):
            raise ValueError("Pflichtfeld 'metadata.name' fehlt")

        scenario = copy.deepcopy(self.default_template())

        # Metadaten überschreiben
        if "metadata" in scenario_data:
            meta = scenario_data["metadata"]
            scenario["metadata"].update({
                "name": meta.get("name", ""),
                "description": meta.get("description", scenario["metadata"].get("description", "")),
                "version": meta.get("version", "0.0.0"),
                "author": meta.get("author", "SW-Team EcoVisionLabs"),
                "valid_for_years": meta.get("valid_for_years", [2030, 2045]),
            })

        # Verbrauchsdaten (pro Sektor)
        if "target_load_demand_twh" in scenario_data:
            scenario["target_load_demand_twh"] = scenario_data["target_load_demand_twh"]

        # Kapazitäten
        if "target_generation_capacities_mw" in scenario_data:
            scenario["target_generation_capacities_mw"] = scenario_data["target_generation_capacities_mw"]

        # Wetterprofile
        if "weather_generation_profiles" in scenario_data:
            scenario["weather_generation_profiles"] = scenario_data["weather_generation_profiles"]

        # Speicher
        if "target_storage_capacities" in scenario_data:
            scenario["target_storage_capacities"] = scenario_data["target_storage_capacities"]

        # Wärmepumpen-Parameter
        if "target_heat_pump_parameters" in scenario_data:
            scenario["target_heat_pump_parameters"] = scenario_data["target_heat_pump_parameters"]

        # E-Mobility-Parameter
        if "target_emobility_parameters" in scenario_data:
            scenario["target_emobility_parameters"] = scenario_data["target_emobility_parameters"]

        return yaml.dump(
            scenario,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
        )

    def save_scenario(self, name: str, scenario_data: Dict[str, Any]) -> Path:
        """Speichert Szenario als YAML-Datei unterhalb von /scenarios."""
        yaml_content = self.create_scenario_yaml(scenario_data)

        filepath = self.output_dir / f"{self._safe_name(name)}.yaml"

        filepath.write_text(yaml_content, encoding="utf-8")
        return filepath

    def load_scenario(self, filepath_or_uploadedfile) -> Dict[str, Any]:
        """
        Lädt Szenario aus YAML-Datei oder Streamlit UploadedFile.
        
        Args:
            filepath_or_uploadedfile: Path-Objekt oder Streamlit UploadedFile
            
        Returns:
            Dictionary mit den Szenario-Daten
        """
        # Streamlit UploadedFile: direkt vom Stream lesen
        if hasattr(filepath_or_uploadedfile, 'read'):
            content = filepath_or_uploadedfile.read().decode("utf-8")
            self.current_scenario = yaml.safe_load(content)
            self.current_path = None
        else:
            # Normale Datei (Path)
            with open(filepath_or_uploadedfile, "r", encoding="utf-8") as f:
                self.current_scenario = yaml.safe_load(f)
            self.current_path = Path(filepath_or_uploadedfile)
        
        return self.current_scenario

    def delete_scenario(self, name_or_path: Union[str, Path]) -> bool:
        """Löscht ein Szenario im /scenarios-Ordner. Gibt True zurück, wenn gelöscht."""
        path = Path(name_or_path)

        if path.is_absolute():
            target = path
        elif path.suffix:
            target = self.output_dir / path
        else:
            target = self.output_dir / f"{self._safe_name(path.name)}.yaml"

        if not target.exists() or not target.is_file():
            return False

        # Sicherheitscheck: nur im vorgesehenen Ordner löschen
        try:
            target.relative_to(self.output_dir)
        except ValueError:
            return False

        target.unlink()
        return True

    @staticmethod
    def _safe_name(name: str) -> str:
        """Erzeugt einen Dateinamen-freundlichen String."""
        return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)

    @property
    def scenario_name(self) -> Optional[str]:
        """Gibt Namen des aktuellen Szenarios zurück."""
        return self.current_scenario.get("metadata", {}).get("name")

    @property
    def scenario_description(self) -> Optional[str]:
        """Gibt Beschreibung des aktuellen Szenarios zurück."""
        return self.current_scenario.get("metadata", {}).get("description")

    @property
    def scenario_data(self) -> Dict[str, Any]:
        """Gibt die kompletten Szenario-Daten zurück."""
        return self.current_scenario

    def get_load_demand(self, sector: Optional[str] = None, year: Optional[int] = None) -> Any:
        """
        Holt Verbrauchsdaten aus dem Szenario.
        
        Args:
            sector: Spezifischer Sektor (z.B. 'Haushalt_Basis'). Wenn None, alle Sektoren.
            year: Spezifisches Jahr. Wenn None, alle Jahre.
            
        Returns:
            Verbrauchsdaten in TWh
        """
        load_data = self.current_scenario.get("target_load_demand_twh", {})
        
        if sector is None:
            return load_data
        if year is None:
            return load_data.get(sector, {})
        return load_data.get(sector, {}).get(year)

    def get_generation_capacities(self, tech: Optional[str] = None, year: Optional[int] = None) -> Any:
        """
        Holt Erzeugungskapazitäten aus dem Szenario.
        
        Args:
            tech: Spezifische Technologie (z.B. 'Photovoltaik'). Wenn None, alle Technologien.
            year: Spezifisches Jahr. Wenn None, alle Jahre.
            
        Returns:
            Kapazitäten in MW
        """
        gen_data = self.current_scenario.get("target_generation_capacities_mw", {})
        
        if tech is None:
            return gen_data
        if year is None:
            return gen_data.get(tech, {})
        return gen_data.get(tech, {}).get(year)

    def get_storage_capacities(self, storage_type: Optional[str] = None, year: Optional[int] = None) -> Any:
        """
        Holt Speicherkapazitäten aus dem Szenario.
        
        Args:
            storage_type: Speichertyp (z.B. 'battery_storage'). Wenn None, alle Typen.
            year: Spezifisches Jahr. Wenn None, alle Jahre.
            
        Returns:
            Speicherkonfiguration
        """
        storage_data = self.current_scenario.get("target_storage_capacities", {})
        
        if storage_type is None:
            return storage_data
        if year is None:
            return storage_data.get(storage_type, {})
        return storage_data.get(storage_type, {}).get(year)

    def get_heat_pump_parameters(self, year: Optional[int] = None) -> Any:
        """
        Holt Wärmepumpen-Parameter aus dem Szenario (neue Struktur).
        
        Args:
            year: Spezifisches Jahr (z.B. 2030, 2045). Wenn None, alle Jahre.
            
        Returns:
            Dict mit Parametern:
            - installed_units: Anzahl Wärmepumpen
            - annual_heat_demand_kwh: Wärmebedarf pro WP [kWh/Jahr]
            - cop_avg: Durchschnittlicher COP
            - weather_data: Wetterdatensatz (aus DataManager)
            - load_profile: HP-Lastprofilmatrix
        """
        hp_data = self.current_scenario.get("target_heat_pump_parameters", {})
        
        if year is None:
            return hp_data
        return hp_data.get(year, {})

    def get_emobility_parameters(self, year: Optional[int] = None) -> Any:
        """
        Holt E-Mobilität-Parameter aus dem Szenario (vollständige Excel-konforme Struktur).
        
        Args:
            year: Spezifisches Jahr (z.B. 2030, 2045). Wenn None, alle Jahre.
            
        Returns:
            Dict mit Parametern (gemäß Excel-Logik):
            - s_EV: Anteil E-Fahrzeuge an Gesamtflotte
            - N_cars: Gesamtanzahl PKW
            - E_drive_car_year: Jahresfahrverbrauch pro E-Auto [kWh/a]
            - E_batt_car: Batteriekapazität pro Fahrzeug [kWh]
            - plug_share_max: Maximale Anschlussquote
            - v2g_share: V2G-Teilnahmequote (Anteil der angeschlossenen Fahrzeuge, die V2G nutzen)
            - SOC_min_day: Min. SOC tagsüber
            - SOC_min_night: Min. SOC nachts
            - SOC_target_depart: Ziel-SOC bei Abfahrt
            - t_depart: Abfahrtszeit (z.B. "07:30")
            - t_arrive: Ankunftszeit (z.B. "18:00")
            - thr_surplus: Schwellwert Überschuss [kW]
            - thr_deficit: Schwellwert Defizit [kW]
            
            Legacy-Parameter (für Rückwärtskompatibilität):
            - installed_units: Anzahl E-Autos
            - annual_consumption_kwh: Verbrauch pro Auto [kWh/Jahr]
            - load_profile: Lastprofilmatrix für Ladevorgänge
        """
        em_data = self.current_scenario.get("target_emobility_parameters", {})
        
        if year is None:
            return em_data
        return em_data.get(year, {})
    
    def get_emobility_scenario_params(self, year: int):
        """
        Erstellt EVScenarioParams-Objekt aus den Szenario-Daten.
        
        Args:
            year: Simulationsjahr
            
        Returns:
            EVScenarioParams Dataclass-Instanz oder None wenn keine Daten
        """
        from data_processing.e_mobility_simulation import EVScenarioParams
        
        em_data = self.get_emobility_parameters(year)
        if not em_data:
            return None
        
        # Neue Parameter haben Vorrang, Legacy als Fallback
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
        return params
    
    @staticmethod
    def get_available_temperature_datasets(config_manager) -> list:
        """
        Holt alle verfügbaren Temperature-Datensätze aus der config.json.
        
        Args:
            config_manager: ConfigManager-Instanz zum Zugriff auf die Konfiguration
            
        Returns:
            Liste von Namen der verfügbaren Temperature-Datensätze
        """
        available = []
        dataframes = config_manager.config.get("DATAFRAMES", [])
        for df_config in dataframes:
            if df_config.get("datatype") == "Temperature":
                available.append(df_config.get("name"))
        return available

    def get_generation_profile_df(self, year: int, include_conv: bool = False) -> pd.DataFrame:
        """
        Konvertiert die target_generation_capacities_mw in ein DataFrame kompatibel mit 
        der generate_generation_profile() Funktion.
        
        Args:
            year: Das Jahr für das die Kapazitäten extrahiert werden sollen
            include_conv: Ob konventionelle Energieträger eingebunden werden sollen
            
        Returns:
            pd.DataFrame: Ein DataFrame mit einer Zeile, die die installierten Kapazitäten 
                         für das angegebene Jahr enthält. Spaltenformat: "[Name] [MW]"
                         
        Example:
            >>> df_capacities = sm.get_generation_profile_df(2030, include_conv=True)
            >>> # df_capacities hat Spalten wie "Photovoltaik [MW]", "Wind Onshore [MW]" etc.
        """
        import pandas as pd
        from constants import ENERGY_SOURCES, SOURCES_GROUPS
        
        # Mapping von Szenario-Namen zu technischen Namen
        tech_mapping = {
            "Photovoltaik": "PV",
            "Wind_Offshore": "WOF",
            "Wind_Onshore": "WON",
            "Wasserkraft": "WAS",
            "Biomasse": "BIO",
            "Kernenergie": "KE",
            "Braunkohle": "BK",
            "Steinkohle": "SK",
            "Erdgas": "EG",
        }
        
        # Relevante Technologien auswählen
        if include_conv:
            relevant_sources = SOURCES_GROUPS["Renewable"] + SOURCES_GROUPS["Conventional"]
        else:
            relevant_sources = SOURCES_GROUPS["Renewable"]
        
        # Daten vorbereiten - hole ALL technologies für das Jahr
        gen_capacities_raw = self.current_scenario.get("target_generation_capacities_mw", {})
        if not gen_capacities_raw:
            raise ValueError(f"Keine Erzeugungskapazitäten im Szenario gefunden.")
        
        # DataFrame-Daten sammeln
        df_data = {}
        for tech_short in relevant_sources:
            if tech_short in ENERGY_SOURCES:
                col_name = ENERGY_SOURCES[tech_short]["colname_MW"]
                
                # Finde den entsprechenden Wert aus dem Szenario für das Jahr
                scenario_value = 0
                for scenario_name, tech_short_code in tech_mapping.items():
                    if tech_short_code == tech_short and scenario_name in gen_capacities_raw:
                        # gen_capacities_raw[scenario_name] ist ein Dict wie {2030: 215000, 2045: 400000}
                        year_data = gen_capacities_raw[scenario_name]
                        if isinstance(year_data, dict) and year in year_data:
                            scenario_value = year_data[year]
                        break
                
                df_data[col_name] = [scenario_value]
        
        # Erstelle DataFrame mit einer Zeile (ähnlich wie SMARD-Instalierte Leistung)
        df = pd.DataFrame(df_data)
        
        return df
