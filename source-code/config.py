from pathlib import Path

# Global configuration settings
GLOBAL = {
    "max_datasets": 100,
    "output_dir": Path("output/test_plots")
}

# Loaded Datasets
DATAFRAMES = [
    {
        "id": 0,
        "name": "SMARD_Stunde_2025",
        "path": Path("raw-data/Realisierte_Erzeugung_2025_Jan-Juni_Stunde_test.csv"),
        "datatype": "SMARD",
        "description": "Stündliche Stromerzeugungsdaten von SMARD für das erste Halbjahr 2025"
    },
    {
        "id": 1,
        "name": "SMARD_Viertelstunde_2020-2025",
        "path": Path("raw-data/1.1.2020-16.10.2025--Realisierte_Erzeugung_202001010000_202510170000_Viertelstunde.csv"),
        "datatype": "SMARD",
        "description": "Viertelstündliche Stromerzeugungsdaten von SMARD von 2020 bis 2025"
    }
]

# Saved Plot configuration
PLOTS = [
    {
        "id": 0,
        "name": "Example_1",
        "dataframes": [1],
        "date_start": "01.01.2024 00:00",
        "date_end": "02.01.2024 23:59",
        "energy_sources": ["KE", "BK", "SK", "EG", "SOK", "BIO", "PS", "WAS", "SOE", "WOF", "WON", "PV"],
        "plot_type": "stacked_bar",
        "description": "Beispielplot für verschiedene Energiequellen im Januar 2024"
    },
    {
        "id": 1,
        "name": "Example_2",
        "dataframes": [0],
        "date_start": "01.01.2025 00:00",
        "date_end": "01.06.2025 23:59",
        "energy_sources": ["KE", "BK", "SK", "EG", "SOK", "BIO", "PS", "WAS", "SOE", "WOF", "WON", "PV"],
        "plot_type": "stacked_bar",
        "description": "Beispielplot für verschiedene Energiequellen von Januar bis Juni 2025"
    }
]