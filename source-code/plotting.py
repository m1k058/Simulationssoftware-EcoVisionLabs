import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES
from errors import PlotNotFoundError, DataProcessingError, WarningMessage


def plot_auto(config_manager, manager, plot_identifier, show=True, save=False, output_dir=None):
    """Automatically generates a plot based on configuration data.

    This function reads the plot settings (time range, energy sources, type, etc.)
    from the ConfigManager, retrieves the relevant DataFrame from the DataManager,
    filters it by date, and calls the appropriate plotting function.

    Args:
        config_manager (ConfigManager):
            Instance providing plot definitions and global configuration.
        manager (DataManager):
            Instance providing loaded pandas DataFrames.
        plot_identifier (int | str):
            ID or name of the plot to generate.
        show (bool, optional):
            If True, the plot is displayed interactively (default = True).
        save (bool, optional):
            If True, the plot image is saved to the configured output directory (default = False).
        output_dir (Path, optional):
            Custom output directory. If None, the path is taken from config.GLOBAL["output_dir"].

    Raises:
        PlotNotFoundError: If the requested plot configuration does not exist.
        DataProcessingError: If associated data cannot be found or processed.
        NotImplementedError: If the plot type is not supported.
    """
    try:
        # Retrieve plot configuration
        PLOTS = config_manager.get_plots()
        output_dir = output_dir or config_manager.get_global("output_dir")

        if isinstance(plot_identifier, int):
            plot_cfg = next((p for p in PLOTS if p["id"] == plot_identifier), None)
        elif isinstance(plot_identifier, str):
            plot_cfg = next((p for p in PLOTS if p["name"] == plot_identifier), None)
        else:
            raise TypeError("plot_identifier must be an int (ID) or str (name).")

        if not plot_cfg:
            raise PlotNotFoundError(f"No plot with identifier '{plot_identifier}' found.")

        # Check assigned DataFrames
        df_ids = plot_cfg.get("dataframes", [])
        if not df_ids:
            raise DataProcessingError(f"Plot '{plot_cfg['name']}' has no DataFrames assigned.")
        if len(df_ids) > 1:
            raise NotImplementedError(
                f"Plot '{plot_cfg['name']}' defines multiple datasets ({df_ids}). "
                "Combining multiple DataFrames is not yet supported."
            )

        # Load dataset
        df_id = df_ids[0]
        df = manager.get(df_id)
        if df is None:
            raise DataProcessingError(
                f"DataFrame with ID '{df_id}' not found for plot '{plot_cfg['name']}'."
            )

        # Parse date range
        date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
        date_end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")
        if pd.isna(date_start) or pd.isna(date_end):
            raise DataProcessingError(f"Invalid date format in plot '{plot_cfg['name']}'.")

        # Filter by date range
        df_filtered = df[(df["Zeitpunkt"] >= date_start) & (df["Zeitpunkt"] <= date_end)]
        if df_filtered.empty:
            raise DataProcessingError(f"No data found in the given time range for plot '{plot_cfg['name']}'.")

        # Choose plot type
        plot_type = plot_cfg.get("plot_type", "stacked_bar")
        if plot_type == "stacked_bar":
            plot_stacked_bar(df_filtered, plot_cfg, show=show, save=save, output_dir=output_dir)
        else:
            raise NotImplementedError(f"Plot type '{plot_type}' is not implemented.")

    except Exception as e:
        # Catch both handled and unexpected errors for clean output
        warnings.warn(f"Plotting failed for '{plot_identifier}': {e}", WarningMessage)


def plot_stacked_bar(df, plot_cfg, show=True, save=False, output_dir=None):
    """Generate a stacked bar (area) plot from a DataFrame according to the configuration.

    Args:
        df (pd.DataFrame):
            The data filtered for the relevant time range.
        plot_cfg (dict):
            The plot configuration dictionary from config.PLOTS.
        show (bool, optional):
            Whether to display the plot interactively (default = True).
        save (bool, optional):
            Whether to save the plot image (default = False).
        output_dir (Path, optional):
            Directory to save the plot image. Defaults to config.GLOBAL["output_dir"].

    Raises:
        DataProcessingError: If no valid columns for the energy sources are found.
    """
    try:
        energy_keys = plot_cfg["energy_sources"]

        available_cols = [
            ENERGY_SOURCES[k]["colname"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        if not available_cols:
            raise DataProcessingError(f"No matching columns found for plot '{plot_cfg['name']}'.")

        labels = [
            ENERGY_SOURCES[k]["name"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        colors = [
            ENERGY_SOURCES[k]["color"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        data_matrix = [df[c].to_numpy(dtype=float) for c in available_cols]

        # Plot creation
        fig, ax = plt.subplots(figsize=(20, 10))
        ax.stackplot(df["Zeitpunkt"], *data_matrix, labels=labels, colors=colors)

        ax.set_xlabel("Zeitpunkt")
        ax.set_ylabel("Erzeugung [MWh]")
        ax.set_title(f"{plot_cfg['name']}\n{plot_cfg['description']}")
        ax.set_xlim(df["Zeitpunkt"].min(), df["Zeitpunkt"].max())
        ax.legend(loc="upper left", ncol=2, fontsize=9)
        ax.grid(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y %H:%M"))
        fig.autofmt_xdate(rotation=45, ha="right")

        # Save or display
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = Path(output_dir or "output")
            outdir.mkdir(parents=True, exist_ok=True)
            filename = outdir / f"{plot_cfg['name']}_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            print(f"Plot saved: {filename}")

        if show:
            plt.show()
            print(f"Plot shown.")
        elif not save:
            warnings.warn("Plot was neither shown nor saved.", WarningMessage)

    except Exception as e:
        raise DataProcessingError(f"Failed to generate stacked bar plot: {e}")

    finally:
        plt.close()
