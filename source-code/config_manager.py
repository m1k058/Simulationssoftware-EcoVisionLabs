import json
from pathlib import Path
from copy import deepcopy

CONFIG_PATH = Path("source-code/config.json")

class ConfigManager:
    """Handles reading, modifying and saving the config.json."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = {}
        self.load()

    # load base config from JSON
    def load(self):
        """Load config.json and convert paths to Path objects."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["GLOBAL"]["output_dir"] = Path(data["GLOBAL"]["output_dir"])
        for df in data["DATAFRAMES"]:
            df["path"] = Path(df["path"])

        self.config = data
        print(f"Config loaded from {self.config_path}")

    def save(self):
        """Save current config back to JSON (convert Paths to strings)."""
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

    # getters for GLOBAL
    def get_global(self):
        return self.config["GLOBAL"]

    def get_global(self, key=None):
        """Gibt die globale Konfiguration oder einen einzelnen Wert zurück."""
        if key:
            return self.global_cfg.get(key)
        return self.global_cfg
    
    # getters for DATAFRAMES
    def get_dataframes(self):
        return self.config["DATAFRAMES"]
    
    def get_dataframe(self, identifier):
        """Gibt einen DataFrame-Eintrag aus der Config zurück (per ID oder Name)."""
        if isinstance(identifier, int):
            for df_cfg in self.dataframes:
                if df_cfg["id"] == identifier:
                    return df_cfg
        else:
            for df_cfg in self.dataframes:
                if df_cfg["name"] == identifier:
                    return df_cfg
        raise KeyError(f"DataFrame with identifier '{identifier}' not found.")
    
    def list_dataframes(self):
        """Listet alle DataFrames (nur ID und Name)."""
        return [{"id": d["id"], "name": d["name"]} for d in self.dataframes]

    # getters for PLTOS
    def get_plots(self):
        return self.config["PLOTS"]

    def get_plot(self, identifier):
        """Gibt eine Plot-Konfiguration aus der Config zurück (per ID oder Name)."""
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
        """Listet alle Plots (nur ID und Name)."""
        return [{"id": p["id"], "name": p["name"]} for p in self.plots]

    # add/delete/edit dataframes
    def add_dataframe(self, name, path, datatype, description=""):
        """Add a new dataframe."""
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
        """Delete a dataframe definition from config by ID or name."""

        if not self.config.get("DATAFRAMES"):
            print("No datasets found in config.")
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
        else:
            print(f"Dataset '{identifier}' not found.")
            return False
        
    def edit_dataframe(self, identifier, **updates):
        """Bearbeitet einen DataFrame-Eintrag in der Config."""
        df_cfg = self.get_dataframe(identifier)

        for key, value in updates.items():
            if key not in df_cfg:
                print(f"Key '{key}' doesn't exist in DataFrame config. Skipping...")
                continue
            df_cfg[key] = value

        print(f"DataFrame '{df_cfg['name']}' was updated:\n{updates}")
        return df_cfg

    # add/delete/edit plots
    def add_plot(self, name, dataframes, date_start, date_end, energy_sources,
                 plot_type="stacked_bar", description=""):
        """Add a new plot configuration."""
        new_id = max((p["id"] for p in self.config["PLOTS"]), default=-1) + 1
        new_plot = {
            "id": new_id,
            "name": name,
            "dataframes": dataframes,
            "date_start": date_start,
            "date_end": date_end,
            "energy_sources": energy_sources,
            "plot_type": plot_type,
            "description": description,
        }
        self.config["PLOTS"].append(new_plot)
        print(f"Added new plot: {name} (ID={new_id})")
        return new_id

    def delete_plot(self, identifier):
        """Delete a plot by ID or name."""
        if isinstance(identifier, int):
            before = len(self.config["PLOTS"])
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["id"] != identifier]
        else:
            before = len(self.config["PLOTS"])
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["name"] != identifier]

        if len(self.config["PLOTS"]) < before:
            print(f"Deleted plot '{identifier}'")
            return True
        print(f"Plot '{identifier}' not found.")
        return False

    def edit_plot(self, identifier, **updates):
        """Bearbeitet einen Plot-Eintrag in der Config."""
        plot_cfg = self.get_plot(identifier)

        for key, value in updates.items():
            if key not in plot_cfg:
                print(f"Key '{key}' doesnt exist in Plot config. Skipping...")
                continue
            plot_cfg[key] = value

        print(f"Plot '{plot_cfg['name']}' updated:\n{updates}")
        return plot_cfg