"""Data input/output module"""

from pathlib import Path

import pandas as pd
import io
import zipfile

from ecovision.data import constants

def load_csv(filepath: str, datatype: str, log: bool) -> pd.DataFrame:
    """Liest eine CSV basierend auf der config ein und bereinigt die Header."""

    path = Path(filepath)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Datei nicht gefunden oder kein gültiger Pfad: {filepath}")
    
    if datatype not in constants.FILE_FORMAT:
        raise ValueError(f"Unbekannter Datentyp: {datatype}")

    # Einlesen mit den Formaten aus Config
    format_options = constants.FILE_FORMAT[datatype]

    df = pd.read_csv(filepath, **format_options)

    # Header bereinigen
    for phrase in constants.SCRAPE_FOR:
        df.columns = df.columns.str.replace(phrase, "", regex=False)

    # unnötige Leerzeichen aus Spaltennamen entfernen
    df.columns = df.columns.str.strip()

    # Prüfen ob alle erwarteten Spalten da sind
    expected_cols = set(constants.HEADER[datatype])
    actual_cols = set(df.columns)
    
    missing_cols = expected_cols - actual_cols
    if missing_cols and log:
        print(f"Warnung: Folgende erwartete Spalten fehlen in {filepath}: {missing_cols}")

    if log:
        print(f"Datei '{filepath}' erfolgreich geladen mit {len(df)} Zeilen und {len(df.columns)} Spalten.")
    return df

def df_to_csv_bytes(df: pd.DataFrame, sep: str = ";", decimal: str = ",") -> bytes:
    """Wandelt einen DataFrame in ein CSV-Byte-Objekt für den Download um"""
    return df.to_csv(index=False, sep=sep, decimal=decimal).encode('utf-8')

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Wandelt einen DataFrame in ein Excel-Byte-Objekt für den Download um"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()

def dfs_to_zip_bytes(dfs: dict[str, pd.DataFrame], file_format: str = "csv") -> bytes:
    """
    Packt ein Dictionary von DataFrames in ein ZIP-Archiv.
    file_format kann "csv" oder "excel" sein.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, df in dfs.items():
            if file_format == "csv":
                file_data = df.to_csv(index=False, sep=";", decimal=",").encode('utf-8')
                zip_file.writestr(f"{filename}.csv", file_data)
                
            elif file_format == "excel":
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                zip_file.writestr(f"{filename}.xlsx", excel_buffer.getvalue())
                
            else:
                raise ValueError("file_format muss 'csv' oder 'excel' sein.")
                
    return zip_buffer.getvalue()