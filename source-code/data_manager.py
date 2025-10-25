from pathlib import Path
import pandas as pd
from io_handler import load_data


class DataManager:
    """Class to manage loading, deleting and accessing datasets."""

    def __init__(self, config_manager=None):
        self.dataframes: dict[int, pd.DataFrame] = {}
        self.metadata: dict[int, dict] = {}
        self.config_manager = config_manager

        if self.config_manager:
            self.max_datasets = self.config_manager.get_global()["max_datasets"]
        else:
            self.max_datasets = 100
        self.load_from_config()
    
    def load_from_config(self):
        """Loads dataframes as defined in the config file."""
        if not self.config_manager:
            raise ValueError("No ConfigManager provided to DataManager.")

        dataframes = self.config_manager.get_dataframes()
        
        for df in dataframes[: self.max_datasets]:
            self.load_from_path(
                path=df["path"],
                dataset_id=df["id"],
                name=df["name"],
                datatype=df.get("datatype", "SMARD"),
                description=df.get("description", "")
            )

    def load_from_path(self, path, datatype="SMARD", dataset_id=None, name=None, description=""):
        """Loads a dataset from the given path.
        Args:
        path: Path to the dataset file.
        datatype: Type of the dataset (for io_handler).
        dataset_id: ID to assign to the dataset.
        name: Name for the dataset.
        description: Optional description for the dataset.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        df = load_data(path=path, datatype=datatype)
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
        
    def list_datasets(self):
        """Lists all loaded datasets with their metadata."""

        if not self.dataframes:
            print("No datasets loaded.")
            return
            
        info = []
        for ds_id, meta in self.metadata.items():
            rows = len(self.dataframes[ds_id])
            info.append({
            "ID": ds_id,
            "name": meta["name"],
            "rows": rows,
            "path": meta["path"],
            "datatype": meta["datatype"]
            })
        return info
        
    def get(self, identifier):
        """Get a dataframe by ID or name."""

        if isinstance(identifier, int):
            return self.dataframes.get(identifier)
            
        # Search by name
        for ds_id, meta in self.metadata.items():
            if meta["name"] == identifier:
                return self.dataframes[ds_id]
        raise KeyError(f"Dataset with name '{identifier}' not found.")
        
    def delete(self, identifier):
        """Deletes a dataset by ID or name."""

        if isinstance(identifier, int):
            ds_id = identifier
        else:
            # Search by name
            ds_id = None
            for id, meta in self.metadata.items():
                if meta["name"] == identifier:
                    ds_id = id
                    break
            if ds_id is None:
                print(f"Dataset with name '{identifier}' not found.")
                return False
            
        # Delete dataset
        del self.dataframes[ds_id]
        del self.metadata[ds_id]
        return True