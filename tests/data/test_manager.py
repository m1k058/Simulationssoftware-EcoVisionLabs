import pytest
import pandas as pd
from ecovision.data.manager import DataManager

# Wir importieren beide Dateien und geben ihnen Alias-Namen
from ecovision.data import constants as data_constants
from ecovision.config import constants as config_constants

# --- FIXTURE: Baut eine saubere Dummy-Datei für die Tests ---
@pytest.fixture
def dummy_csv_path(tmp_path):
    """Erstellt eine temporäre CSV-Datei und gibt den Pfad zurück."""
    test_file = tmp_path / "dummy_smard.csv"
    
    # Header und Format kommen aus dem data-Ordner
    headers = data_constants.HEADER["SMARD-con"]
    
    # Eine Zeile mit Nullen/Platzhaltern passend zur Spaltenanzahl
    data = [["01.01.2023 00:00", "01.01.2023 00:15"] + ["0"] * (len(headers) - 2)]
    df = pd.DataFrame(data, columns=headers)
    
    fmt = data_constants.FILE_FORMAT["SMARD-con"]
    df.to_csv(
        test_file, 
        sep=fmt["sep"], 
        decimal=fmt["decimal"], 
        encoding=fmt["encoding"], 
        index=False
    )
    return str(test_file)

# --- TESTS ---

def test_manager_load_and_get(dummy_csv_path):
    mgr = DataManager()
    mgr.load_csv("test_dataset", dummy_csv_path, "SMARD-con")
    
    assert "test_dataset" in mgr.list_dataset_names()
    df = mgr.get_data("test_dataset")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

def test_manager_remove_data(dummy_csv_path):
    mgr = DataManager()
    mgr.load_csv("test_dataset", dummy_csv_path, "SMARD-con")
    mgr.remove_data("test_dataset")
    
    assert "test_dataset" not in mgr.list_dataset_names()
    with pytest.raises(KeyError):
        mgr.get_data("test_dataset")

def test_manager_exports(dummy_csv_path):
    mgr = DataManager()
    mgr.load_csv("test_dataset", dummy_csv_path, "SMARD-con")
    
    csv_filename, csv_bytes = mgr.get_export("test_dataset", file_format="csv")
    assert csv_filename.endswith(".csv")
    assert len(csv_bytes) > 0
    
    excel_filename, excel_bytes = mgr.get_export("test_dataset", file_format="excel")
    assert excel_filename.endswith(".xlsx")
    assert len(excel_bytes) > 0
    
    zip_filename, zip_bytes = mgr.get_zip_export(["test_dataset"], zip_name="test_archive", file_format="csv")
    assert zip_filename.startswith("test_archive")
    assert zip_filename.endswith(".zip")
    assert len(zip_bytes) > 0

def test_manager_load_all(dummy_csv_path, monkeypatch):
    mock_sources = [
        {
            "id": 99,
            "name": "Auto_Loaded_Data",
            "path": dummy_csv_path,
            "datatype": "SMARD-con",
            "description": "Mock Data"
        }
    ]
    # DATA_SOURCES überschreiben wir im config-Ordner
    monkeypatch.setattr(config_constants, "DATA_SOURCES", mock_sources)
    
    mgr = DataManager(auto_load=True)
    
    assert "Auto_Loaded_Data" in mgr.list_dataset_names()
    assert not mgr.get_data("Auto_Loaded_Data").empty