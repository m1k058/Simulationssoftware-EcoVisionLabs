from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import copy
import yaml


class ScenarioManager:
    """Verwaltet Szenario-Konfigurationen für Simulationen."""
    
    def __init__(self, base_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        # Sicherstellen, dass der Szenario-Ordner immer im Projektwurzelverzeichnis liegt
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.output_dir = Path(output_dir) if output_dir else self.base_dir / "scenarios"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def default_template(self) -> Dict[str, Any]:
        """Gibt ein plausibles Dummy-Szenario im gewünschten Schema zurück."""
        return {
            "metadata": {
                "name": "Szenario Beispiel",
                "valid_for_years": [2030, 2045],
                "description": "Beispielhaftes Szenario mit plausiblen Dummy-Werten zur Simulation.",
                "version": "0.0.0",
                "author": "SW-Team EcoVisionLabs",
            },
            "target_load_demand_twh": {
                "Haushalt_Basis": {
                    2030: 130,
                    2045: 120,
                    "load_profile": "BDEW-25-Haushalte",
                },
                "Gewerbe_Basis": {
                    2030: 140,
                    2045: 130,
                    "load_profile": "BDEW-25-Gewerbe",
                },
                "Industrie_Basis": {
                    2030: 280,
                    2045: 350,
                    "load_profile": "BDEW-25-Industrie",
                },
                "EMobility": {
                    2030: 60,
                    2045: 140,
                    "load_profile": "EMobility-self",
                },
                "Heat_Pumps": {
                    2030: 50,
                    2045: 110,
                    "load_profile": "HeatPumps-self",
                },
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
                2030: {
                    "Wind_Offshore": "good",
                    "Wind_Onshore": "average",
                    "Photovoltaik": "average",
                },
                2045: {
                    "Wind_Offshore": "bad",
                    "Wind_Onshore": "good",
                    "Photovoltaik": "good",
                },
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

    def load_scenario(self, filepath: Path) -> Dict[str, Any]:
        """Lädt Szenario aus YAML."""
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

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
