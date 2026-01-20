from pathlib import Path
import pandas as pd
import warnings
from io_handler import load_data
import warnings


class DataManager:
    """Handles loading, accessing, and managing datasets from the configuration or directly from file paths."""

    def __init__(self, config_manager=None, progress_callback=None):
        """
        Initialize the DataManager.

        Args:
            config_manager (ConfigManager, optional):
                Reference to a ConfigManager instance used to load datasets automatically.
            progress_callback (callable, optional):
                Callback function(current, total, dataset_name) for progress tracking.
        """
        self.dataframes: dict[int, pd.DataFrame] = {}
        self.metadata: dict[int, dict] = {}
        self.config_manager = config_manager
        self.progress_callback = progress_callback

        if self.config_manager:
            self.max_datasets = self.config_manager.get_global("max_datasets") or 100
        else:
            self.max_datasets = 100

        # Try to auto-load datasets from config if available
        if self.config_manager:
            self.load_from_config()

    # -------------------------------------------------------------------------
    def load_from_config(self):
        """Load all DataFrames defined in the configuration file.

        Raises:
            FileLoadError: If any dataset path from the configuration does not exist.
        """
        if not self.config_manager:
            raise ValueError("No ConfigManager provided to DataManager.")

        dataframes = self.config_manager.get_dataframes()
        if not dataframes:
            warnings.warn("No datasets defined in configuration.", category=UserWarning)
            return

        total_datasets = len(dataframes[: self.max_datasets])
        
        for idx, df in enumerate(dataframes[: self.max_datasets], start=1):
            path = df["path"]
            dataset_name = df["name"]
            
            # Report progress
            if self.progress_callback:
                self.progress_callback(idx, total_datasets, dataset_name)
            
            if not path.exists():
                warnings.warn(f"File not found for dataset '{dataset_name}': {path}", category=UserWarning)
                continue

            try:
                self.load_from_path(
                    path=path,
                    dataset_id=df["id"],
                    name=dataset_name,
                    datatype=df.get("datatype", "SMARD"),
                    description=df.get("description", "")
                )
                print(f"Loaded dataset '{dataset_name}' successfully.")
            except Exception as e:
                warnings.warn(f"Failed to load dataset '{dataset_name}': {e}", category=UserWarning)

        if not self.dataframes:
            warnings.warn("No datasets could be loaded from configuration.", category=UserWarning)

    # -------------------------------------------------------------------------
    def load_from_path(self, path, datatype="SMARD", dataset_id=None, name=None, description=""):
        """Load a dataset from a specific file path.

        Args:
            path (Path | str): Path to the dataset file.
            datatype (str, optional): Type of the dataset (for io_handler). Defaults to "SMARD".
            dataset_id (int, optional): Optional dataset ID to assign.
            name (str, optional): Custom name for the dataset.
            description (str, optional): Optional description text.

        Returns:
            int: The ID assigned to the loaded dataset.

        Raises:
            FileLoadError: If the file does not exist or cannot be read.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            df = load_data(path=path, datatype=datatype)
        except Exception as e:
            raise ValueError(f"Failed to load data from {path}: {e}")

        if dataset_id is None:
            dataset_id = max(self.dataframes.keys(), default=-1) + 1

        self.dataframes[dataset_id] = df
        self.metadata[dataset_id] = {
            "name": name or path.stem,
            "path": str(path),
            "datatype": datatype,
            "description": description,
        }

        return dataset_id

    # -------------------------------------------------------------------------
    def list_datasets(self):
        """Return a summary of all loaded datasets.

        Returns:
            list[dict]: List of dataset metadata including ID, name, row count, and path.
        """
        if not self.dataframes:
            warnings.warn("No datasets are currently loaded.", category=UserWarning)
            return []

        info = []
        for ds_id, meta in self.metadata.items():
            rows = len(self.dataframes[ds_id])
            info.append({
                "ID": ds_id,
                "Name": meta["name"],
                "Rows": rows,
                "Path": meta["path"],
                "Datatype": meta["datatype"]
            })
        return info

    # -------------------------------------------------------------------------
    def list_dataset_names(self):
        """Return a list of all loaded dataset names.

        Returns:
            list[str]: List of dataset names.
        """
        return [meta["name"] for meta in self.metadata.values()]

    def get_dataset_id(self, name):
        """Get the dataset ID for a given dataset name.

        Args:
            name (str): The name of the dataset.
        Returns:
            int: The ID of the dataset.
        """
        for ds_id, meta in self.metadata.items():
            if meta["name"] == name:
                return ds_id
        raise KeyError(f"Dataset with name '{name}' not found.")

    # -------------------------------------------------------------------------
    def get(self, identifier):
        """Retrieve a DataFrame by its ID or name.

        Args:
            identifier (int | str): Dataset ID or dataset name.

        Returns:
            pd.DataFrame: The corresponding DataFrame object.

        Raises:
            DataframeNotFoundError: If the requested dataset does not exist.
        """
        if isinstance(identifier, int):
            if identifier in self.dataframes:
                return self.dataframes[identifier]
            raise KeyError(f"Dataset with ID '{identifier}' not found.")

        # Search by name
        for ds_id, meta in self.metadata.items():
            if meta["name"] == identifier:
                return self.dataframes[ds_id]

        raise KeyError(f"Dataset with name '{identifier}' not found.")

    # -------------------------------------------------------------------------
    def delete(self, identifier):
        """Delete a dataset from memory by its ID or name.

        Args:
            identifier (int | str): ID or name of the dataset to delete.

        Returns:
            bool: True if successfully deleted, False if not found.
        """
        if isinstance(identifier, int):
            ds_id = identifier if identifier in self.dataframes else None
        else:
            ds_id = next((id for id, meta in self.metadata.items() if meta["name"] == identifier), None)

        if ds_id is None:
            warnings.warn(f"Dataset '{identifier}' not found. Nothing deleted.", category=UserWarning)
            return False

        del self.dataframes[ds_id]
        del self.metadata[ds_id]
        print(f"Deleted dataset '{identifier}' (ID={ds_id}).")
        return True

    # -------------------------------------------------------------------------
    def add(self, df, name, description="", datatype="Custom"):
        """Add an existing DataFrame to the DataManager.

        Args:
            df (pd.DataFrame): The DataFrame to add.
            name (str): Name for the dataset.            
            description (str, optional): Optional description text.
            datatype (str, optional): Type of the dataset. Defaults to "Custom".

        Returns:
            int: The ID assigned to the added dataset.
        """
        dataset_id = max(self.dataframes.keys(), default=-1) + 1
        self.dataframes[dataset_id] = df
        self.metadata[dataset_id] = {
            "name": name,
            "path": "N/A",
            "datatype": datatype,
            "description": description,
        }
        return dataset_id