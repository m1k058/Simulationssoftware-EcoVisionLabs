from data_manager import DataManager
from config_manager import ConfigManager
from plotting import plot_auto
from pathlib import Path
from constants import SOURCES_GROUPS

# Create ConfigManager instance and load config.json
cfg = ConfigManager(Path("source-code/config.json"))

# Create DataManager instance and load config
dm = DataManager(config_manager=cfg)

# Add new file for session
cfg.add_dataframe("Example Data", Path("raw-data/DATA_EXAMPLE.csv"), "SMARD", "Beispiel Daten (py of 2020-2025 data)")

# Reload Dataframes from config
dm.load_from_config()

# Add new Plot
cfg.add_plot(
    "Example Plot",
    ["Example Data"],
    "01.01.2019 00:00",
    "07.01.2019 23:59",
    SOURCES_GROUPS["Renewable"],
    "stacked_bar",
    "This is an example Plot"
    )

# List Plots
print(cfg.get_plot("Example Plot"))

# Generate Plot
plot_auto(cfg, dm, "Example Plot", True)