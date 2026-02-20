"""Configuration manager module."""

import json
from pathlib import Path
from copy import deepcopy
import warnings


# Default: relative to the project root (where `streamlit run src/run_ui.py` is executed)
CONFIG_PATH = Path("source-code/config.json")


class ConfigManager:
    """Handles reading, modifying and saving the configuration to config.json."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = {}
        self.load()

    def load(self):
        """Load the configuration from the JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        out_dir = data["GLOBAL"].get("output_dir", "output")
        out_dir = out_dir.replace("\\", "/")
        data["GLOBAL"]["output_dir"] = Path(out_dir)

        base_dir = self.config_path.parent.resolve()

        for df in data.get("DATAFRAMES", []):
            p = df.get("path", "")
            if isinstance(p, str):
                p = p.replace("\\", "/")
            full_path = (base_dir / p).resolve()
            df["path"] = full_path

        self.config = data
        self.dataframes = self.config.get("DATAFRAMES", [])
        self.plots = self.config.get("PLOTS", [])
        self.global_cfg = self.config.get("GLOBAL", {})
        self._deduplicate_plots()
        print(f"Config loaded from {self.config_path}")

    def _deduplicate_plots(self):
        """Remove duplicate plot entries with the same ID."""
        seen_ids = set()
        unique_plots = []
        for plot in self.plots:
            plot_id = plot.get("id")
            if plot_id not in seen_ids:
                seen_ids.add(plot_id)
                unique_plots.append(plot)
        if len(unique_plots) < len(self.plots):
            print(f"Removed {len(self.plots) - len(unique_plots)} duplicate plot(s)")
            self.plots = unique_plots
            self.config["PLOTS"] = unique_plots

    def save(self):
        """Save the current configuration back to the JSON file."""
        def convert_paths(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, list):
                return [convert_paths(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            return obj

        data_serializable = convert_paths(deepcopy(self.config))
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data_serializable, f, indent=4, ensure_ascii=False)
        print(f"Config saved to {self.config_path}")

    def get_global(self, key=None):
        if key:
            return self.global_cfg.get(key)
        return self.global_cfg

    def get_dataframes(self):
        return self.config["DATAFRAMES"]

    def get_dataframe(self, identifier):
        if isinstance(identifier, int):
            for df_cfg in self.dataframes:
                if df_cfg.get("id") == identifier:
                    return df_cfg
        else:
            for df_cfg in self.dataframes:
                if df_cfg.get("name") == identifier:
                    return df_cfg
        raise KeyError(f"DataFrame with identifier '{identifier}' not found.")

    def list_dataframes(self):
        return [{"id": d["id"], "name": d["name"]} for d in self.dataframes]

    def get_plots(self):
        return self.config["PLOTS"]

    def get_plot(self, identifier):
        if isinstance(identifier, int):
            for plot_cfg in self.plots:
                if plot_cfg["id"] == identifier:
                    return plot_cfg
        else:
            for plot_cfg in self.plots:
                if plot_cfg["name"] == identifier:
                    return plot_cfg
        raise KeyError(f"Plot with identifier '{identifier}' not found.")

    def list_plots(self):
        return [{"id": p["id"], "name": p["name"]} for p in self.plots]

    def add_dataframe(self, name, path, datatype="SMARD", description=""):
        new_id = max((df["id"] for df in self.config["DATAFRAMES"]), default=-1) + 1
        new_entry = {
            "id": new_id,
            "name": name,
            "path": Path(path),
            "datatype": datatype,
            "description": description,
        }
        self.config["DATAFRAMES"].append(new_entry)
        print(f"Added new dataset: {name} (ID={new_id})")
        return new_id

    def delete_dataframe(self, identifier):
        if not self.config.get("DATAFRAMES"):
            warnings.warn("No datasets found in config.", category=UserWarning)
            return False
        before = len(self.config["DATAFRAMES"])
        if isinstance(identifier, int):
            self.config["DATAFRAMES"] = [df for df in self.config["DATAFRAMES"] if df["id"] != identifier]
        else:
            self.config["DATAFRAMES"] = [df for df in self.config["DATAFRAMES"] if df["name"] != identifier]
        after = len(self.config["DATAFRAMES"])
        if after < before:
            print(f"Dataset '{identifier}' deleted successfully.")
            return True
        warnings.warn(f"Dataset '{identifier}' not found.", category=UserWarning)
        return False

    def edit_dataframe(self, identifier, **updates):
        df_cfg = self.get_dataframe(identifier)
        for key, value in updates.items():
            if key not in df_cfg:
                warnings.warn(f"Key '{key}' doesn't exist in DataFrame config. Skipping...", category=UserWarning)
                continue
            df_cfg[key] = value
        print(f"DataFrame '{df_cfg['name']}' was updated:\n{updates}")
        return df_cfg

    def create_plot_from_ui(self, ui_selections: dict) -> int:
        new_id = max((plot.get("id", -1) for plot in self.plots), default=-1) + 1
        plot_type = ui_selections.get("plot_type", "stacked_bar")
        if "dataframes" in ui_selections:
            dataframes_list = ui_selections["dataframes"]
        elif "dataset" in ui_selections:
            dataframes_list = [ui_selections["dataset"]["id"]]
        else:
            raise ValueError("UI selections must contain either 'dataframes' or 'dataset'")
        new_plot = {
            "id": new_id,
            "name": ui_selections.get("plot_name", f"plot_{new_id}"),
            "dataframes": dataframes_list,
            "date_start": ui_selections.get("date_start"),
            "date_end": ui_selections.get("date_end"),
            "plot_type": plot_type,
            "description": ui_selections.get("description", f"Plot created with ID {new_id}"),
        }
        if plot_type == "stacked_bar":
            new_plot["energy_sources"] = ui_selections.get("energy_sources", [])
        elif plot_type == "line":
            new_plot["columns"] = ui_selections.get("columns", [])
        elif plot_type == "balance":
            new_plot["column1"] = ui_selections.get("column1")
            new_plot["column2"] = ui_selections.get("column2")
        if not isinstance(self.plots, list):
            self.plots = []
        if "PLOTS" not in self.config:
            self.config["PLOTS"] = []
        self.plots.append(new_plot)
        if self.plots is not self.config["PLOTS"]:
            self.config["PLOTS"] = self.plots
        if ui_selections.get("save_plot"):
            self.save()
        return new_id

    def add_plot(self, name, dataframes, date_start, date_end, energy_sources,
                 plot_type="stacked_bar", description="", columns=None, column1=None, column2=None):
        resolved_df_ids = []
        for df_ref in dataframes:
            if isinstance(df_ref, int):
                resolved_df_ids.append(df_ref)
            elif isinstance(df_ref, str):
                try:
                    df_cfg = self.get_dataframe(df_ref)
                    resolved_df_ids.append(df_cfg["id"])
                except Exception:
                    warnings.warn(f"DataFrame '{df_ref}' not found — skipping.", category=UserWarning)
            else:
                warnings.warn(f"Ignoring invalid DataFrame reference: {df_ref}", category=UserWarning)
        if not resolved_df_ids:
            warnings.warn(f"No valid DataFrames found for plot '{name}'.", category=UserWarning)
        new_id = max((p["id"] for p in self.config["PLOTS"]), default=-1) + 1
        new_plot = {
            "id": new_id,
            "name": name,
            "dataframes": resolved_df_ids,
            "date_start": date_start,
            "date_end": date_end,
            "plot_type": plot_type,
            "description": description,
        }
        if plot_type == "stacked_bar":
            new_plot["energy_sources"] = energy_sources or []
        if plot_type == "line" and columns is not None:
            new_plot["columns"] = list(columns)
        if plot_type == "balance":
            if column1 is not None:
                new_plot["column1"] = column1
            if column2 is not None:
                new_plot["column2"] = column2
        self.config["PLOTS"].append(new_plot)
        self.plots = self.config["PLOTS"]
        print(f"Added new plot: {name} (ID={new_id})")
        return new_id

    def delete_plot(self, identifier):
        before = len(self.config["PLOTS"])
        if isinstance(identifier, int):
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["id"] != identifier]
        else:
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["name"] != identifier]
        self.plots = self.config["PLOTS"]
        if len(self.config["PLOTS"]) < before:
            print(f"Deleted plot '{identifier}'")
            return True
        warnings.warn(f"Plot '{identifier}' not found.", category=UserWarning)
        return False

    def edit_plot(self, identifier, **updates):
        plot_cfg = self.get_plot(identifier)
        for key, value in updates.items():
            if key not in plot_cfg:
                warnings.warn(f"Key '{key}' doesn't exist in Plot config. Skipping...", category=UserWarning)
                continue
            plot_cfg[key] = value
        print(f"Plot '{plot_cfg['name']}' updated:\n{updates}")
        return plot_cfg

    def get_generation_year(self, tech, scenario="good"):
        table = self.config.get("GENERATION_SIMULATION", {}).get("optimal_reference_years_by_technology", {})
        tech_entry = table.get(tech) or {}
        return tech_entry.get(scenario) or table.get("default")
