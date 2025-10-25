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

# To save added or removed Dataframes or Plots to config.json use:
# cfg.save

# If config.json was updated you can reload it with:
# cfg.load

# Reload Dataframes from config
dm.load_from_config()

# Add new Plot
cfg.add_plot(
    "Example Plot",
    ["Example Data"],
    "01.01.2019 00:00",
    "07.01.2019 23:59",
    ["KE", "BK", "SK", "EG", "SOK", "SOE", "BIO", "PS", "WAS", "WOF", "WON", "PV"],
    "stacked_bar",
    "This is an example Plot"
    )

# List Plots
print(cfg.list_plots())

# Generate Plot
plot_auto(cfg, dm, "Example Plot", True)