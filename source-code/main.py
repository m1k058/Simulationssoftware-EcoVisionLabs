from constants import ENERGY_SOURCES
from data_manager import DataManager
from config import DATAFRAMES, PLOTS, GLOBAL
from plotting import plot_auto

# Create DataManager instance
dm = DataManager(max_datasets=100)

# Load data from config to DataManager
dm.load_from_config()

# Beispielplot erstellen
plot_auto(dm, "Example_1")