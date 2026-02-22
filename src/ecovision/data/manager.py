"""Data manager module."""

import pandas as pd
from datetime import datetime
import os

from ecovision.data import io_handler
from ecovision.config import constants 

class DataManager:
    def __init__(self, auto_load: bool = False, progress_callback=None):
        self._data: dict[str, pd.DataFrame] = {}
        self.progress_callback = progress_callback
        
        if auto_load:
            self.load_all()

    def load_all(self) -> None:
        """Lädt alle Datensätze, die in constants.DATA_SOURCES definiert sind.
        
        Bereits geladene Datensätze werden übersprungen.
        """
        if not hasattr(constants, 'DATA_SOURCES'):
            print("Fehler: DATA_SOURCES nicht in constants.py gefunden.")
            return

        sources = constants.DATA_SOURCES
        to_load = [s for s in sources if s["name"] not in self._data]

        if not to_load:
            print("Alle Datensätze bereits geladen – überspringe load_all.")
            return

        print(f"Starte Ladevorgang ({len(to_load)} von {len(sources)} Datensätzen)...")
        total = len(to_load)
        for idx, source in enumerate(to_load, start=1):
            name = source["name"]
            filepath = source["path"]
            datatype = source["datatype"]

            if self.progress_callback:
                self.progress_callback(idx, total, name)

            if os.path.exists(filepath):
                print(f" -> Lade '{name}' (Typ: {datatype}) aus {filepath}...")
                self.load_csv(name=name, filepath=filepath, datatype=datatype)
            else:
                print(f" -> WARNUNG: Datei für '{name}' nicht gefunden unter: {filepath}")

    def load_csv(self, name: str, filepath: str, datatype: str) -> None:
        """Lädt eine CSV über den io_handler und speichert sie im RAM."""
        if name in self._data:
            print(f"Warnung: Datensatz '{name}' existiert bereits und wird überschrieben.")
        
        df = io_handler.load_csv(filepath, datatype, log=True)
        self._data[name] = df

    def get_data(self, name: str) -> pd.DataFrame:
        """Holt einen DataFrame aus dem Speicher."""
        if name not in self._data:
            raise KeyError(f"Datensatz '{name}' existiert nicht im Manager.")
        return self._data[name]

    # Kurz-Alias – wird u.a. von SimulationEngine genutzt
    def get(self, name: str) -> pd.DataFrame:
        """Alias für get_data."""
        return self.get_data(name)

    def list_datasets(self) -> list:
        """Gibt eine Liste aller aktuell geladenen Datensätze mit Metadaten zurück."""
        return [
            {"ID": i, "Name": name, "Rows": len(df)}
            for i, (name, df) in enumerate(self._data.items())
        ]

    def list_dataset_names(self) -> list[str]:
        """Gibt eine Liste aller geladenen Datensatz-Namen zurück."""
        return list(self._data.keys())

    def remove_data(self, name: str) -> None:
        """Löscht einen Datensatz aus dem Speicher, um RAM freizugeben."""
        if name in self._data:
            del self._data[name]

    def get_export(self, name: str, file_format: str = "csv") -> tuple[str, bytes]:
        """Gibt einen automatisierten Dateinamen und die Bytes für Streamlit zurück."""
        df = self.get_data(name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if file_format == "csv":
            filename = f"{name}_{timestamp}.csv"
            file_bytes = io_handler.df_to_csv_bytes(df)
        elif file_format == "excel":
            filename = f"{name}_{timestamp}.xlsx"
            file_bytes = io_handler.df_to_excel_bytes(df)
        else:
            raise ValueError("Format muss 'csv' oder 'excel' sein.")
            
        return filename, file_bytes

    def get_zip_export(self, names: list[str], zip_name: str = "export", file_format: str = "csv") -> tuple[str, bytes]:
        """Packt mehrere Datensätze aus dem Manager in ein ZIP und gibt Name + Bytes zurück."""
        dfs_to_zip = {name: self.get_data(name) for name in names if name in self._data}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{zip_name}_{timestamp}.zip"
        
        zip_bytes = io_handler.dfs_to_zip_bytes(dfs_to_zip, file_format=file_format)
        
        return filename, zip_bytes