import json
from pathlib import Path
from copy import deepcopy
from errors import FileLoadError, DataframeNotFoundError, WarningMessage, PlotNotFoundError
import warnings


CONFIG_PATH = Path("source-code/config.json")

class ConfigManager:
    """Handles reading, modifying and saving the configuaration to config.json."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = {}
        self.load()

    # load base config from JSON
    def load(self):
        """Load the configuration from the JSON file.

    Reads and parses the config file defined by `self.config_path`.
    Converts path strings to `Path` objects for easier usage.
    Can be called again at any time to reload configuration changes from disk.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
        if not self.config_path.exists():
            raise FileLoadError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Normalize path separators AND resolve relative to config file location
        out_dir = data["GLOBAL"].get("output_dir", "output")
        out_dir = out_dir.replace("\\", "/")
        data["GLOBAL"]["output_dir"] = Path(out_dir)

        # HIER IST DIE ÄNDERUNG:
        # Wir merken uns, wo die config.json liegt
        base_dir = self.config_path.parent.resolve()

        for df in data.get("DATAFRAMES", []):
            p = df.get("path", "")
            if isinstance(p, str):
                p = p.replace("\\", "/")
            
            # Wir bauen den absoluten Pfad zusammen:
            # Ordner der Config + Relativer Pfad aus der JSON
            full_path = (base_dir / p).resolve()
            
            df["path"] = full_path

        self.config = data

        self.dataframes = self.config.get("DATAFRAMES", [])
        self.plots = self.config.get("PLOTS", [])
        self.global_cfg = self.config.get("GLOBAL", {})

        # Remove duplicate plots (by ID) - can happen from old bugs
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
        """Save the current configuration back to the JSON file.

    All in-memory changes will be written to disk, overwriting the existing config.

    Warning:
        This operation overwrites the existing config file permanently.

    Returns:
        None
    """
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

    def get_global(self, key=None):
        """Retrieve the global configuration or a specific key from it.

    Args:
        key (str, optional): Specific key within GLOBAL to retrieve. 
            If None, the entire GLOBAL configuration is returned.

    Returns:
         dict | Any: The full GLOBAL configuration or a single value if key is provided.
    """
        if key:
            return self.global_cfg.get(key)
        return self.global_cfg
    
    # getters for DATAFRAMES
    def get_dataframes(self):
        """Retrieve all DataFrame configurations.

    Returns:
        list[dict]: A list containing all DataFrame configuration dictionaries.
    """
        return self.config["DATAFRAMES"]
    
    def get_dataframe(self, identifier):
        """Retrieve a specific DataFrame configuration by ID or name.

        Args:
            identifier (int | str): The ID or name of the DataFrame to retrieve.

        Returns:
            dict: The corresponding DataFrame configuration.

        Raises:
            DataframeNotFoundError: If no matching DataFrame is found.
        """
        if isinstance(identifier, int):
            for df_cfg in self.dataframes:
                if df_cfg.get("id") == identifier:
                    return df_cfg
        else:
            for df_cfg in self.dataframes:
                if df_cfg.get("name") == identifier:
                    return df_cfg
        raise DataframeNotFoundError(f"DataFrame with identifier '{identifier}' not found.")

    def create_plot_from_ui(self, ui_selections: dict) -> int:
        """Create a new plot configuration from user interface selections.

        Args:
            ui_selections (dict): Dictionary containing user selections from user_interface.get_user_input()

        Returns:
            int: ID of the newly created plot configuration

        Raises:
            ValueError: If the UI selections are invalid
        """
        # Generate new plot ID
        new_id = max((plot.get('id', -1) for plot in self.plots), default=-1) + 1

        # Determine plot type and optional parameters
        plot_type = ui_selections.get("plot_type", "stacked_bar")

        # Determine dataframes list
        # For histogram, we might have multiple datasets in ui_selections
        if "dataframes" in ui_selections:
            # Direct list of dataframe IDs (used by new UI v2)
            dataframes_list = ui_selections["dataframes"]
        elif "dataset" in ui_selections:
            # Single dataset (legacy format)
            dataframes_list = [ui_selections["dataset"]["id"]]
        else:
            raise ValueError("UI selections must contain either 'dataframes' or 'dataset'")

        # Create new plot configuration (base)
        new_plot = {
            "id": new_id,
            "name": ui_selections.get("plot_name", f"plot_{new_id}"),
            "dataframes": dataframes_list,
            "date_start": ui_selections.get("date_start"),
            "date_end": ui_selections.get("date_end"),
            "plot_type": plot_type,
            "description": ui_selections.get("description", f"Plot created with ID {new_id}"),
        }

        # Attach type-specific fields
        if plot_type == "stacked_bar":
            new_plot["energy_sources"] = ui_selections.get("energy_sources", [])
        elif plot_type == "line":
            # list of column names to plot
            new_plot["columns"] = ui_selections.get("columns", [])
        elif plot_type == "balance":
            new_plot["column1"] = ui_selections.get("column1")
            new_plot["column2"] = ui_selections.get("column2")
        elif plot_type == "histogram":
            # No extra fields required for histogram
            pass
        elif plot_type == "table":
            # No extra fields required for table
            pass

        # Ensure internal structures exist and append
        if not isinstance(self.plots, list):
            self.plots = []
        if "PLOTS" not in self.config:
            self.config["PLOTS"] = []

        # Append only once (self.plots and self.config["PLOTS"] point to the same list)
        self.plots.append(new_plot)
        # Make sure they stay synchronized
        if self.plots is not self.config["PLOTS"]:
            self.config["PLOTS"] = self.plots

        # Save the configuration if plot should be saved
        if ui_selections.get("save_plot"):
            self.save()

        return new_id
    
    def list_dataframes(self):
        """List all DataFrames with only their IDs and names.

    Returns:
        list[dict]: A compact list containing only the ID and name of each DataFrame.
    """
        return [{"id": d["id"], "name": d["name"]} for d in self.dataframes]

    # getters for PLTOS
    def get_plots(self):
        """Retrieve all plot configurations.

    Returns:
        list[dict]: A list containing all plot configuration dictionaries.
    """
        return self.config["PLOTS"]

    def get_plot(self, identifier):
        """Retrieve a specific plot configuration by ID or name.

    Args:
        identifier (int | str): The ID or name of the plot to retrieve.

    Returns:
        dict: The corresponding plot configuration.

    Raises:
        KeyError: If no matching plot is found.
    """
        if isinstance(identifier, int):
            for plot_cfg in self.plots:
                if plot_cfg["id"] == identifier:
                    return plot_cfg
        else:
            for plot_cfg in self.plots:
                if plot_cfg["name"] == identifier:
                    return plot_cfg
        raise PlotNotFoundError(f"Plot with identifier '{identifier}' not found.")
    
    def list_plots(self):
        """List all plots with only their IDs and names.

    Returns:
        list[dict]: A compact list containing only the ID and name of each plot.
    """
        return [{"id": p["id"], "name": p["name"]} for p in self.plots]

    # add/delete/edit dataframes
    def add_dataframe(self, name, path, datatype="SMARD", description=""):
        """Add a new DataFrame configuration entry.

    Args:
        name (str): Name of the new DataFrame.
        path (str | Path): File path of the dataset.
        datatype (str, optional): Data type of the dataset (e.g. "SMARD"). Defaults to "SMARD".
        description (str, optional): Short description of the dataset. Defaults to "".

    Returns:
        int: The automatically generated ID of the new DataFrame.
    """
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
        """Delete a DataFrame configuration by ID or name.

    Args:
        identifier (int | str): The ID or name of the DataFrame to delete.

    Returns:
        bool: True if the DataFrame was deleted, False if not found.
    """

        if not self.config.get("DATAFRAMES"):
            warnings.warn("No datasets found in config.", WarningMessage)
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
            warnings.warn(f"Dataset '{identifier}' not found.", WarningMessage)
            return False
        
    def edit_dataframe(self, identifier, **updates):
        """Edit an existing DataFrame configuration.

    Args:
        identifier (int | str): The ID or name of the DataFrame to edit.
        **updates (dict): Key-value pairs representing the fields to update.
            Unknown keys are ignored with a warning.

    Returns:
        dict: The updated DataFrame configuration dictionary.

    Example:
        >>> manager.edit_dataframe(1, name="Updated Dataset", description="New data for 2025")
    """
        df_cfg = self.get_dataframe(identifier)

        for key, value in updates.items():
            if key not in df_cfg:
                warnings.warn(f"Key '{key}' doesn't exist in DataFrame config. Skipping...", WarningMessage)
                continue
            df_cfg[key] = value

        print(f"DataFrame '{df_cfg['name']}' was updated:\n{updates}")
        return df_cfg

    # add/delete/edit plots
    def add_plot(self, name, dataframes, date_start, date_end, energy_sources,
             plot_type="stacked_bar", description="", columns=None, column1=None, column2=None):
        """Add a new plot configuration entry.

        Args:
            name (str): Name of the plot.
            dataframes (list[int | str]): List of DataFrame IDs or names used as input.
                If names are provided, they will be automatically converted to IDs.
            date_start (str): Start date/time of the plot range.
            date_end (str): End date/time of the plot range.
            energy_sources (list[str]): Energy source keys to include in the plot.
            plot_type (str, optional): Type of plot (e.g. "stacked_bar"). Defaults to "stacked_bar".
            description (str, optional): Short description of the plot. Defaults to "".

        Returns:
            int: The automatically generated ID of the new plot.
        """
        # --- Convert DataFrame names to IDs if needed ---
        resolved_df_ids = []
        for df_ref in dataframes:
            if isinstance(df_ref, int):
                resolved_df_ids.append(df_ref)
            elif isinstance(df_ref, str):
                try:
                    df_cfg = self.get_dataframe(df_ref)
                    resolved_df_ids.append(df_cfg["id"])
                except Exception:
                    warnings.warn(
                        f"DataFrame '{df_ref}' not found — skipping this entry.",
                        WarningMessage
                    )
            else:
                warnings.warn(f"Ignoring invalid DataFrame reference: {df_ref}", WarningMessage)

        if not resolved_df_ids:
            warnings.warn(
                f"No valid DataFrames found for plot '{name}'. Plot will not be usable.",
                WarningMessage
            )

        # --- Create plot config ---
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
        # Optional fields depending on type
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
        # Keep self.plots synchronized
        self.plots = self.config["PLOTS"]
        print(f"Added new plot: {name} (ID={new_id})")
        return new_id

    def delete_plot(self, identifier):
        """Delete a plot configuration by ID or name.

    Args:
        identifier (int | str): The ID or name of the plot to delete.

    Returns:
        bool: True if the plot was deleted successfully, False if not found.
    """
        if isinstance(identifier, int):
            before = len(self.config["PLOTS"])
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["id"] != identifier]
        else:
            before = len(self.config["PLOTS"])
            self.config["PLOTS"] = [p for p in self.config["PLOTS"] if p["name"] != identifier]

        # Keep self.plots synchronized
        self.plots = self.config["PLOTS"]

        if len(self.config["PLOTS"]) < before:
            print(f"Deleted plot '{identifier}'")
            return True
        warnings.warn(f"Plot '{identifier}' not found.", WarningMessage)
        return False

    def edit_plot(self, identifier, **updates):
        """Edit an existing plot configuration.

    Args:
        identifier (int | str): The ID or name of the plot to edit.
        **updates (dict): Key-value pairs representing the fields to update.
            Unknown keys are ignored with a warning.

    Returns:
        dict: The updated plot configuration dictionary.

    Example:
        >>> manager.edit_plot("Example_1", date_start="01.02.2024 00:00", date_end="05.02.2024 23:59")
    """
        plot_cfg = self.get_plot(identifier)

        for key, value in updates.items():
            if key not in plot_cfg:
                warnings.warn(f"Key '{key}' doesnt exist in Plot config. Skipping...", WarningMessage)
                continue
            plot_cfg[key] = value

        print(f"Plot '{plot_cfg['name']}' updated:\n{updates}")
        return plot_cfg
    
    def get_generation_year(self, tech, scenario="good"):
        table = self.config.get("GENERATION_SIMULATION", {}).get("optimal_reference_years_by_technology", {})
        tech_entry = table.get(tech) or {}
        return tech_entry.get(scenario) or table.get("default")