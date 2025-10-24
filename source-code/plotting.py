import matplotlib.pyplot as plt
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
    
    # combine dataframes if multiple are specified
    combined_df = pd.DataFrame()
    for df_id in plot_cfg["dataframes"]:
        df = manager.get(df_id)
        if df is None:
            print(ValueError(f"Dataframe with ID: '{df_id}' not found for plot: '{plot_cfg['name']}'."))
            continue
        combined_df = pd.concat([combined_df, df]) if not combined_df.empty else df

    if combined_df.empty:
        print(f"⚠️ Kein Datensatz für Plot '{plot_cfg['name']}' verfügbar.")
        return
    
    # date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
    # date_end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")

    # Filter DataFrame for specified date range
    df_filtered = df[(df["Zeitpunkt"] >= plot_cfg["date_start"]) & (df["Zeitpunkt"] <= plot_cfg["date_end"])]
    if df_filtered.empty:
        print(ValueError(f"No data in this time for plot '{plot_cfg['name']}'."))
        return
    
    # Call specific plot function based on plot type
    if plot_cfg["plot_type"] == "stacked_bar":
        plot_stacked_bar(df_filtered, plot_cfg, save=save, output_dir=output_dir)

    # Add more plot types HERE  <--------------------------------

    else:
        print(NotImplementedError(f"Plot type '{plot_cfg['plot_type']}' not implemented."))

    

def plot_stacked_bar(df, plot_config, save=False, output_dir=None):
    """Erzeugt einen einzelnen Plot aus der Config (per Name oder ID).

    Args:
        manager: Instanz von DataManager (liefert DataFrames)
        plot_identifier: Name (str) oder ID (int) des Plots aus config.PLOTS
        save (bool): Wenn True -> speichern statt anzeigen
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

    labels = [ENERGY_SOURCES[k]["name"] for k in energy_keys if ENERGY_SOURCES[k]['colname'] in df.columns]
    colors = [ENERGY_SOURCES[k]["color"] for k in energy_keys if ENERGY_SOURCES[k]['colname'] in df.columns]
    data_matrix = [df[c].to_numpy(dtype=float) for c in available_cols]

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.stackplot(df["Zeitpunkt"], *data_matrix, labels=labels, colors=colors)

    ax.set_xlabel("Zeitpunkt")
    ax.set_ylabel("Erzeugung [MWh]")
    ax.set_title(f"{plot_cfg['name']}\n{plot_cfg['description']}")
    ax.set_title
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    ax.grid(True)
    fig.autofmt_xdate()

    # --- Speichern oder anzeigen ---
    if save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / f"{plot_cfg['name']}_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"💾 Plot gespeichert: {filename}")
    else:
        plt.show()