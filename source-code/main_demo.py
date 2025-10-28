import warnings
from pathlib import Path
from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from plotting import plot_auto, plot_ee_consumption_histogram
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

        plot_ee_consumption_histogram(
            config_manager=cfg,
            df_erzeugung=dm.get("SMARD_2020-2025_Erzeugung"),
            df_verbrauch=dm.get("SMARD_2020-2025_Verbrauch"),
            title="Anteil der Erneuerbaren Energien am Gesamtstromverbrauch"
            )

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
