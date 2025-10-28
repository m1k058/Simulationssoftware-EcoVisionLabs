import warnings
from pathlib import Path
from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from plotting import plot_auto, plot_ee_consumption_histogram
from io_handler import load_data, save_data
from data_processing import  add_total_generation, add_total_renewable_generation, add_total_conventional_generation
from constants import SOURCES_GROUPS


def main():
    """Main for EcoVisionLabs data and plotting"""
    try:
        # --- Load configuration
        cfg = ConfigManager(Path("source-code/config.json"))

        # --- Initialize DataManager and load available datasets
        dm = DataManager(config_manager=cfg)

    
        print("\nLoaded Datasets:")
        print(cfg.list_dataframes())
        add_total_generation(dm.get("SMARD_2020-2025_Erzeugung"))
        add_total_renewable_generation(dm.get("SMARD_2020-2025_Erzeugung"))
        add_total_conventional_generation(dm.get("SMARD_2020-2025_Erzeugung"))
        save_data(dm.get("SMARD_2020-2025_Erzeugung"), Path("output/processed_generation_data.csv"))
        

    # --- Handle controlled application errors
    except AppError as e:
        print(f"\n{e}")

    # --- Handle non-critical warnings
    except WarningMessage as w:
        warnings.warn(str(w), WarningMessage)

    # --- Handle unexpected Python errors
    except Exception as e:
        print(f"\nUnexpected error ({type(e).__name__}): {e}")

    finally:
        print("\nProgram finished.\n")


if __name__ == "__main__":
    main()
