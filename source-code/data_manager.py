from pathlib import Path
import pandas as pd
import warnings
from io_handler import load_data
from errors import FileLoadError, DataframeNotFoundError, DataProcessingError, WarningMessage


class DataManager:
    """Handles loading, accessing, and managing datasets from the configuration or directly from file paths."""

    def __init__(self, config_manager=None):
        """
        Initialize the DataManager.

        Args:
            config_manager (ConfigManager, optional):
                Reference to a ConfigManager instance used to load datasets automatically.
        """
        self.dataframes: dict[int, pd.DataFrame] = {}
        self.metadata: dict[int, dict] = {}
        self.config_manager = config_manager

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
            raise DataProcessingError("No ConfigManager provided to DataManager.")

        dataframes = self.config_manager.get_dataframes()
        if not dataframes:
            warnings.warn("No datasets defined in configuration.", WarningMessage)
            return

        for df in dataframes[: self.max_datasets]:
            path = df["path"]
            if not path.exists():
                warnings.warn(f"File not found for dataset '{df['name']}': {path}", WarningMessage)
                continue

            try:
                self.load_from_path(
                    path=path,
                    dataset_id=df["id"],
                    name=df["name"],
                    datatype=df.get("datatype", "SMARD"),
                    description=df.get("description", "")
                )
                print(f"Loaded dataset '{df['name']}' successfully.")
            except Exception as e:
                warnings.warn(f"Failed to load dataset '{df['name']}': {e}", WarningMessage)

        if not self.dataframes:
            warnings.warn("No datasets could be loaded from configuration.", WarningMessage)

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
            raise FileLoadError(f"File not found: {path}")

        try:
            df = load_data(path=path, datatype=datatype)
        except Exception as e:
            raise DataProcessingError(f"Failed to load data from {path}: {e}")

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
            warnings.warn("No datasets are currently loaded.", WarningMessage)
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
            raise DataframeNotFoundError(f"Dataset with ID '{identifier}' not found.")

        # Search by name
        for ds_id, meta in self.metadata.items():
            if meta["name"] == identifier:
                return self.dataframes[ds_id]

        raise DataframeNotFoundError(f"Dataset with name '{identifier}' not found.")

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
            warnings.warn(f"Dataset '{identifier}' not found. Nothing deleted.", WarningMessage)
            return False

        del self.dataframes[ds_id]
        del self.metadata[ds_id]
        print(f"Deleted dataset '{identifier}' (ID={ds_id}).")
        return True
