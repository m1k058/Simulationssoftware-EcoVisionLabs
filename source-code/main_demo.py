import warnings
from pathlib import Path
from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from plotting import plot_auto
from constants import SOURCES_GROUPS


def main():
    """Main for EcoVisionLabs data and plotting"""
    try:
        # --- Load configuration
        cfg = ConfigManager(Path("source-code/config.json"))

        # --- Initialize DataManager and load available datasets
        dm = DataManager(config_manager=cfg)

        # --- Add a new dataset temporarily for this session
        cfg.add_dataframe(
            name="Example Data",
            path=Path("raw-data/DATA_EXAMPLE.csv"),
            datatype="SMARD",
            description="Beispiel-Datensatz (aus 2020-2025)"
        )

        # Reload datasets into memory
        dm.load_from_config()
        print("\nLoaded Datasets:")
        print(cfg.list_dataframes())

        # --- Add a sample plot configuration
        cfg.add_plot(
            name="Example Plot",
            dataframes=["Example Data"],
            date_start="01.01.2019 00:00",
            date_end="07.01.2019 23:59",
            energy_sources=SOURCES_GROUPS["All"],
            plot_type="stacked_bar",
            description="Demo-Plot mit erneuerbaren Energiequellen"
        )

        # --- Generate plot from config
        print("\nGenerating example plot...")
        plot_auto(cfg, dm, "Example Plot", show=True, save=False)

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
