from constants import ENERGY_SOURCES
from data_manager import DataManager
from config import DATAFRAMES, PLOTS, GLOBAL
from plotting import plot_auto

# Create DataManager instance
dm = DataManager(max_datasets=100)

# Load data from config to DataManager
dm.load_from_config()

# Einzelnes Dataset holen
df = dm.get("SMARD_Viertelstunde_2020-2025")

# Beispielplot erstellen
plot_auto(dm, "Example_1")