import warnings
from pathlib import Path
from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from plotting.plotting import plot_auto
from constants import SOURCES_GROUPS
from user_interface import get_user_input


def main():
    """Main for EcoVisionLabs data and plotting"""
    try:
        # --- Load configuration
        cfg = ConfigManager(Path("source-code/config.json"))

        # --- Initialize DataManager and load available datasets
        dm = DataManager(config_manager=cfg)

        # Start interactive UI to collect user selections
        ui = get_user_input(config_manager=cfg)

        # Create a new plot configuration from the UI selections
        new_plot_id = cfg.create_plot_from_ui(ui)
        print(f"Created plot configuration with ID: {new_plot_id}")

        # Trigger plotting using the DataManager and the new plot
        # Desired behavior:
        # - If user chose NOT to save -> show only
        # - If user chose to save -> save first, then ask whether to also show
        save_choice = ui.get("save_plot", False)
        if not save_choice:
            # Only show the plot
            plot_auto(config_manager=cfg, manager=dm, plot_identifier=new_plot_id,
                      show=True, save=False)
        else:
            # Save the plot first
            plot_auto(config_manager=cfg, manager=dm, plot_identifier=new_plot_id,
                      show=False, save=True)

            # Ask whether the user also wants to see the saved plot now
            try:
                while True:
                    ans = input("Plot saved. Do you want to also display it now? (y/n): ").strip().lower()
                    if ans in ("y", "n"):
                        break
                    print("Please enter 'y' or 'n'.")
                if ans == "y":
                    plot_auto(config_manager=cfg, manager=dm, plot_identifier=new_plot_id,
                              show=True, save=False)
            except Exception:
                # Non-interactive environments may not support input(); ignore in that case
                pass

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

