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
                "valid_years_from": 2025,
                "valid_years_to": 2045,
                "description": "Beispielhaftes Szenario mit plausiblen Dummy-Werten zur Simulation.",
                "version": "1.0",
                "author": "SW-Team EcoVisionLabs",
                "created": datetime.now().isoformat(),
            },
            "load_parameters": {
                "target_demand_twh": {
                    2030: 520,
                    2035: 540,
                    2040: 560,
                    2045: 580,
                },
                "load_profile": "2025-BDEW",
            },
            "generation_profile_parameters": {
                "time_resolution": "15min",
                "source": "SMARD",
                "good_year": {
                    "wind_onshore": 2017,
                    "wind_offshore": 2017,
                    "photovoltaics": 2019,
                },
                "bad_year": {
                    "wind_onshore": 2021,
                    "wind_offshore": 2021,
                    "photovoltaics": 2016,
                },
                "average_year": {
                    "wind_onshore": 2015,
                    "wind_offshore": 2015,
                    "photovoltaics": 2018,
                },
            },
            "generation_capacities_mw": {
                "Photovoltaik": {2030: 140_000, 2035: 180_000, 2040: 210_000, 2045: 240_000},
                "Wind Onshore": {2030: 90_000, 2035: 115_000, 2040: 135_000, 2045: 150_000},
                "Wind Offshore": {2030: 40_000, 2035: 55_000, 2040: 70_000, 2045: 85_000},
                "Wasserkraft": {2030: 5_000, 2035: 5_000, 2040: 5_000, 2045: 5_000},
                "Biomasse": {2030: 4_500, 2035: 4_500, 2040: 4_500, 2045: 4_500},
                "Erdgas": {2030: 15_000, 2035: 12_000, 2040: 9_000, 2045: 8_000},
                "Steinkohle": {2030: 0, 2035: 0, 2040: 0, 2045: 0},
                "Braunkohle": {2030: 0, 2035: 0, 2040: 0, 2045: 0},
                "Kernenergie": {2030: 0, 2035: 0, 2040: 0, 2045: 0},
            },
            "storage_capacities": {
                "battery_storage": {
                    "installed_capacity_mwh": 50000,
                    "max_charge_power_mw": 12000,
                    "max_discharge_power_mw": 12000,
                    "charge_efficiency": 0.92,
                    "discharge_efficiency": 0.92,
                    "soc": {"initial": 0.55, "min": 0.10, "max": 0.90},
                },
                "pumped_hydro_storage": {
                    "installed_capacity_mwh": 180000,
                    "max_charge_power_mw": 35000,
                    "max_discharge_power_mw": 35000,
                    "charge_efficiency": 0.88,
                    "discharge_efficiency": 0.88,
                    "soc": {"initial": 0.60, "min": 0.20, "max": 0.95},
                },
                "h2_storage": {
                    "installed_capacity_mwh": 250000,
                    "max_charge_power_mw": 50000,
                    "max_discharge_power_mw": 50000,
                    "charge_efficiency": 0.60,
                    "discharge_efficiency": 0.60,
                    "soc": {"initial": 0.45, "min": 0.10, "max": 0.90},
                },
            },
        }

    def create_scenario_yaml(self, scenario_data: Dict[str, Any]) -> str:
        """
        Erstellt einen YAML-String aus Scenario-Daten.

        Erwartet ein Dictionary mit: metadata, load_parameters, generation_profile_parameters,
        generation_capacities_mw, storage_capacities.
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
                "version": meta.get("version", "1.0"),
                "author": meta.get("author", "SW-Team EcoVisionLabs"),
                "valid_years_from": meta.get("valid_years_from", 2025),
                "valid_years_to": meta.get("valid_years_to", 2045),
            })
            scenario["metadata"]["created"] = datetime.now().isoformat()

        # Verbrauchsdaten
        if "load_parameters" in scenario_data:
            lp = scenario_data["load_parameters"]
            if "target_demand_twh" in lp:
                scenario["load_parameters"]["target_demand_twh"] = lp["target_demand_twh"]
            if "load_profile" in lp:
                scenario["load_parameters"]["load_profile"] = lp["load_profile"]

        # Erzeugungsprofile
        if "generation_profile_parameters" in scenario_data:
            scenario["generation_profile_parameters"].update(scenario_data["generation_profile_parameters"])

        # Kapazitäten
        if "generation_capacities_mw" in scenario_data:
            scenario["generation_capacities_mw"] = scenario_data["generation_capacities_mw"]

        # Speicher
        if "storage_capacities" in scenario_data:
            scenario["storage_capacities"] = scenario_data["storage_capacities"]

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
