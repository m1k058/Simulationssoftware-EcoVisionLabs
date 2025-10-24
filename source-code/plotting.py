import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES
from config import PLOTS


def plot_auto(manager, plot_identifier, save=False, output_dir=None):
    """Generates a plot based on the plot configuration identified by name or ID.
    
    Args:
        manager: Instance of DataManager (provides DataFrames)
        plot_identifier: Name (str) or ID (int) of the plot from config.PLOTS
        save (bool): If True -> save instead of show
        output_dir (Path, optional): Target directory (default = GLOBAL["output_dir"])
    """
    
    # get plot config from config file
    plot_cfg = None
    if isinstance(plot_identifier, int):
        plot_cfg = next((p for p in PLOTS if p["id"] == plot_identifier), None)
    elif isinstance(plot_identifier, str):
        plot_cfg = next((p for p in PLOTS if p["name"] == plot_identifier), None)
    else:
        raise TypeError("plot_identifier must be int (ID) or str (Name).")
    
    # check if plot config found
    if not plot_cfg:
        raise KeyError(f"No Plot with ID: '{plot_identifier}' found.")
    
    # check assigned dataframes
    df_ids = plot_cfg.get("dataframes", [])
    if not df_ids:
        raise ValueError(f"Plot '{plot_cfg['name']}' has no dataframes assigned.")
    if len(df_ids) > 1:
        raise NotImplementedError(
            f"Plot '{plot_cfg['name']}' defines multiple dataframes "
            f"({df_ids}) — combining is not supported yet."
        )

    # load dataframe
    df_id = df_ids[0]
    df = manager.get(df_id)
    if df is None:
        raise ValueError(f"Dataframe with ID '{df_id}' not found for plot '{plot_cfg['name']}'.")
    
    # --- Parse date range from config (German format)
    date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
    date_end   = pd.to_datetime(plot_cfg["date_end"],   format="%d.%m.%Y %H:%M", errors="coerce")

    # Filter DataFrame for specified date range
    df_filtered = df[
        (df["Zeitpunkt"] >= date_start) &
        (df["Zeitpunkt"] <= date_end)]
    
    if df_filtered.empty:
        raise ValueError(f"No data in this time for plot '{plot_cfg['name']}'.")
    
    # Call specific plot function based on plot type
    if plot_cfg["plot_type"] == "stacked_bar":
        plot_stacked_bar(df_filtered, plot_cfg, save=save, output_dir=output_dir)

    # Add more plot types HERE  <--------------------------------

    else:
        raise NotImplementedError(f"Plot type '{plot_cfg['plot_type']}' not implemented.")

    

def plot_stacked_bar(df, plot_config, show=True, save=False, output_dir=None):
    """Erzeugt einen einzelnen Plot aus der Config (per Name oder ID).

    Args:
        df: dataframe with data to plot
        plot_identifier: Name (str) or ID (int) for the plot from the config file
        show (bool): If True -> display the plot
        save (bool): If True -> safe the plot
        output_dir (Path, optional): Zielordner (default = GLOBAL["output_dir"])
    """
    
    plot_cfg=plot_config

    energy_keys = plot_cfg["energy_sources"]
    available_cols = [
        ENERGY_SOURCES[k]['colname'] for k in energy_keys
        if ENERGY_SOURCES[k]['colname'] in df.columns
    ]
    if not available_cols:
        print(ValueError(f"No matching columns found for plot '{plot_cfg['name']}'."))
        return

    # generate data for plotting
    labels = [ENERGY_SOURCES[k]["name"] for k in energy_keys if ENERGY_SOURCES[k]['colname'] in df.columns]
    colors = [ENERGY_SOURCES[k]["color"] for k in energy_keys if ENERGY_SOURCES[k]['colname'] in df.columns]
    data_matrix = [df[c].to_numpy(dtype=float) for c in available_cols]

    # plotting
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


    # save or show
    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / f"{plot_cfg['name']}_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Plot saved: {filename}")
    if show:
        plt.show()
    if not save and not show:
        print("Warning: Plot neither saved nor shown.")
        plt.close()