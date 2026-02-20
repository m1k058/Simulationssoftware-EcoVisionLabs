from pathlib import Path

import pandas as pd
import pytest

from ecovision.data import constants
from ecovision.data.io_handler import load_csv


def test_load_csv_raises_for_missing_path(tmp_path):
    """Prüft, dass ein nicht vorhandener Pfad sauber abgefangen wird."""
    missing_file = tmp_path / "nicht_vorhanden.csv"

    with pytest.raises(FileNotFoundError):
        load_csv(str(missing_file), "SMARD-con", log=False)


def test_load_csv_reads_dirty_and_real_data(tmp_path):
    """Liest fehleranfällige Testdatei und echte raw-data ein, inkl. Head-Ausgabe."""
    datatype = "SMARD-con"
    test_file = tmp_path / "test_dirty_smard.csv"

    headers = constants.HEADER[datatype].copy()
    dirty_phrase = constants.SCRAPE_FOR[0]
    headers[2] = f"  {headers[2]} {dirty_phrase}  "

    data = [[
        "01.01.2023 00:00",
        "01.01.2023 00:15",
        "10,5",
        "20,1",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
    ]]
    df_dummy = pd.DataFrame(data, columns=headers)

    fmt = constants.FILE_FORMAT[datatype]
    df_dummy.to_csv(
        test_file,
        sep=fmt["sep"],
        decimal=fmt["decimal"],
        encoding=fmt["encoding"],
        index=False,
    )

    df_dirty = load_csv(str(test_file), datatype, log=True)
    print("DIRTY_TEST_HEAD")
    print(df_dirty.head())

    assert f"Biomasse [MWh] {dirty_phrase}" not in df_dirty.columns
    assert "Biomasse [MWh]" in df_dirty.columns
    assert len(df_dirty) == 1

    project_root = Path(__file__).resolve().parents[2]
    real_file = project_root / "raw-data" / "Realisierter_Stromverbrauch_2020-2025.csv"

    df_real = load_csv(str(real_file), "SMARD-pro", log=True)
    print("REAL_DATA_HEAD")
    print(df_real.head())

    assert not df_real.empty
    assert "Netzlast [MWh]" in df_real.columns