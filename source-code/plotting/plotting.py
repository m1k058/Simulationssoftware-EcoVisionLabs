"""
Moved plotting module into `plotting` package.
Original file: source-code/plotting.py
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import warnings
import os
import numpy as np

from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES
from errors import PlotNotFoundError, DataProcessingError, WarningMessage
from data_processing import gen


def plot_auto(config_manager, manager, plot_identifier, show=True, save=False, output_dir=None):
    # Function body unchanged (moved)
    try:
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

        df_ids = plot_cfg.get("dataframes", [])
        if not df_ids:
            raise DataProcessingError(f"Plot '{plot_cfg['name']}' has no DataFrames assigned.")

        plot_type = plot_cfg.get("plot_type", "stacked_bar")
        if plot_type == "histogram":
            if len(df_ids) != 2:
                raise DataProcessingError(
                    f"Plot '{plot_cfg['name']}' requires exactly 2 DataFrames (generation + consumption) for histogram."
                )
        elif len(df_ids) > 1:
            raise NotImplementedError(
                f"Plot '{plot_cfg['name']}' defines multiple datasets ({df_ids}). "
                "Combining multiple DataFrames is not yet supported."
            )

        df_id = df_ids[0]
        df = manager.get(df_id)
        if df is None:
            raise DataProcessingError(
                f"DataFrame with ID '{df_id}' not found for plot '{plot_cfg['name']}'."
            )

        date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
        date_end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")
        if pd.isna(date_start) or pd.isna(date_end):
            raise DataProcessingError(f"Invalid date format in plot '{plot_cfg['name']}'.")

        df_filtered = df[(df["Zeitpunkt"] >= date_start) & (df["Zeitpunkt"] <= date_end)]
        if df_filtered.empty:
            raise DataProcessingError(f"No data found in the given time range for plot '{plot_cfg['name']}'.")

        if plot_type == "stacked_bar":
            plot_stacked_bar(df_filtered, plot_cfg, show=show, save=save, output_dir=output_dir)
        elif plot_type == "line":
            cols = plot_cfg.get("columns")
            title = plot_cfg.get("name", "Line chart")
            plot_line_chart(config_manager, df_filtered, columns=cols, title=title, show=show, save=save, output_dir=output_dir)
        elif plot_type == "balance":
            col1 = plot_cfg.get("column1")
            col2 = plot_cfg.get("column2")
            if not col1 or not col2:
                raise DataProcessingError(f"Plot '{plot_cfg['name']}' missing 'column1' or 'column2' for balance plot.")
            title = plot_cfg.get("name", "Balance plot")
            plot_balance(config_manager, df_filtered, column1=col1, column2=col2, title=title, show=show, save=save, output_dir=output_dir)
        elif plot_type == "histogram":
            df_id_2 = df_ids[1]
            df_2 = manager.get(df_id_2)
            if df_2 is None:
                raise DataProcessingError(
                    f"DataFrame with ID '{df_id_2}' not found for plot '{plot_cfg['name']}'."
                )
            df_2_filtered = df_2[(df_2["Zeitpunkt"] >= date_start) & (df_2["Zeitpunkt"] <= date_end)]
            if df_2_filtered.empty:
                raise DataProcessingError(f"No consumption data found in the given time range for plot '{plot_cfg['name']}'.")
            title = plot_cfg.get("name", "Renewable Energy Share Histogram")
            plot_ee_consumption_histogram(config_manager, df_filtered, df_2_filtered, title=title, show=show, save=save, output_dir=output_dir)
        else:
            raise NotImplementedError(f"Plot type '{plot_type}' is not implemented.")

    except Exception as e:
        warnings.warn(f"Plotting failed for '{plot_identifier}': {e}", WarningMessage)


def plot_stacked_bar(df, plot_cfg, show=True, save=False, output_dir=None):
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

        fig, ax = plt.subplots(figsize=(20, 10))
        ax.stackplot(df["Zeitpunkt"], *data_matrix, labels=labels, colors=colors)

        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Generation [MWh]")
        ax.set_title(f"{plot_cfg['name']}\n{plot_cfg['description']}")
        ax.set_xlim(df["Zeitpunkt"].min(), df["Zeitpunkt"].max())
        ax.legend(loc="upper left", ncol=2, fontsize=9)
        ax.grid(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y %H:%M"))
        fig.autofmt_xdate(rotation=45, ha="right")

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = Path(output_dir or "output")
            outdir.mkdir(parents=True, exist_ok=True)
            filename = outdir / f"{plot_cfg['name']}_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches="tight")
            print(f"Plot saved: {filename}")

        if show:
            plt.show()
            print(f"Plot displayed.")
        elif not save:
            warnings.warn("Plot was neither shown nor saved.", WarningMessage)

    except Exception as e:
        raise DataProcessingError(f"Failed to generate stacked bar plot: {e}")

    finally:
        plt.close()


def plot_ee_consumption_histogram(config_manager, df_erzeugung: pd.DataFrame, df_verbrauch: pd.DataFrame, title: str = "Renewable Energy Share Histogram", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Gesamterzeugung Erneuerbare [MWh]' not in df_erzeugung.columns:
            df_erzeugung_processed = gen.add_total_renewable_generation(df_erzeugung.copy())
        else:
            df_erzeugung_processed = df_erzeugung

        erzeugung_ee = df_erzeugung_processed['Gesamterzeugung Erneuerbare [MWh]']
        
        if 'Netzlast [MWh]' not in df_verbrauch.columns:
            raise ValueError("Consumption DataFrame is missing column 'Netzlast [MWh]'.")
        
        verbrauch = df_verbrauch['Netzlast [MWh]']

        df_merged = pd.DataFrame({
            'Erzeugung_EE': erzeugung_ee,
            'Verbrauch': verbrauch
        }).dropna()

        df_merged['EE_Anteil_Verbrauch'] = 0.0
        mask_verbrauch_pos = df_merged['Verbrauch'] > 0
        
        df_merged.loc[mask_verbrauch_pos, 'EE_Anteil_Verbrauch'] = \
            (df_merged.loc[mask_verbrauch_pos, 'Erzeugung_EE'] / df_merged.loc[mask_verbrauch_pos, 'Verbrauch']) * 100
        
        plt.figure(figsize=(16, 9))

        bins = np.arange(0, 110, 10)
        histogramm_value = np.clip(df_merged['EE_Anteil_Verbrauch'], bins[0], bins[-1] - 0.001)

        plt.hist(histogramm_value, bins=bins, edgecolor='black')

        plt.title(f"Histogram: {title}", fontsize=24)
        plt.xlabel("Share of renewable energy in consumption (%)", fontsize=14)
        plt.ylabel("Number of 15-minute intervals", fontsize=14)
        plt.figtext(
                0.95, 0.01, "© EcoVision Labs Team",
                ha="right",
                va="bottom",
                fontsize=11,
                color='gray'
            )

        tick_positions = bins[:-1]
        tick_labels = [str(int(x)) for x in bins[:-2]] + ['100+']
        plt.xticks(tick_positions, tick_labels)
        plt.grid(axis='y', alpha=0.75)

        if save:
            timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
            filename = f"{clean_title}_{timestamp}.png"
            outdir = Path(output_dir)
            outdir.mkdir(parents=True, exist_ok=True)
            plot_path = outdir / filename
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            print(f"Histogram saved to: {plot_path}")

        if show:
            plt.show()
            print("Histogram displayed.")
        elif not save:
            warnings.warn("Plot was neither shown nor saved.", WarningMessage)

    except Exception as e:
        print(f"Error creating histogram: {e}")
        raise
    
    finally:
        plt.close()


def plot_balance(config_manager, df: pd.DataFrame, column1: str, column2: str, title="Balance plot", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame must contain a 'Zeitpunkt' column.")
        
        if column1 not in df.columns:
            raise ValueError(f"Column '{column1}' not found in DataFrame.")
        
        if column2 not in df.columns:
            raise ValueError(f"Column '{column2}' not found in DataFrame.")
        
        balance = df[column1] - df[column2]
        
        fig, ax = plt.subplots(figsize=(16, 9))
        
        ax.plot(df['Zeitpunkt'], balance, color='black', linewidth=1.5, label=f'{column1} - {column2}')
        
        ax.fill_between(df['Zeitpunkt'], balance, 0, where=(balance >= 0), 
                        color='green', alpha=0.4, interpolate=True, label='Surplus (≥ 0)')
        ax.fill_between(df['Zeitpunkt'], balance, 0, where=(balance < 0), 
                        color='red', alpha=0.4, interpolate=True, label='Deficit (< 0)')
        
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        
        ax.set_xlabel("Timestamp", fontsize=14)
        ax.set_ylabel("Balance [MWh]", fontsize=14)
        ax.set_title(title, fontsize=24)
        ax.legend(loc='best', fontsize=11)
        ax.grid(True, alpha=0.75)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y %H:%M"))
        fig.autofmt_xdate(rotation=45, ha="right")
        plt.figtext(
            0.95, 0.01, "© EcoVision Labs Team",
            ha="right",
            va="bottom",
            fontsize=11,
            color='gray'
        )

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = Path(output_dir)
            outdir.mkdir(parents=True, exist_ok=True)
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
            filename = outdir / f"{clean_title}_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Balance plot saved: {filename}")

        if show:
            plt.show()
            print("Balance plot displayed.")
        elif not save:
            warnings.warn("Plot was neither shown nor saved.", WarningMessage)

    except Exception as e:
        print(f"Error creating balance plot: {e}")
        raise

    finally:
        plt.close()


def plot_line_chart(config_manager, df: pd.DataFrame, columns=None, title="Line chart", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame must contain a 'Zeitpunkt' column.")
        
        if columns is None:
            columns = [col for col in df.columns if col != 'Zeitpunkt']
        else:
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found in DataFrame: {missing_cols}")
        
        fig, ax = plt.subplots(figsize=(16, 9))
        
        for column in columns:
            ax.plot(df['Zeitpunkt'], df[column], label=column, linewidth=1.5)

        ax.set_xlabel("Timestamp", fontsize=14)
        ax.set_ylabel("Value", fontsize=14)
        ax.set_title(title, fontsize=24)
        ax.legend(loc='best', fontsize=11)
        ax.grid(True, alpha=0.75)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y %H:%M"))
        fig.autofmt_xdate(rotation=45, ha="right")
        plt.figtext(
            0.95, 0.01, "© EcoVision Labs Team",
            ha="right",
            va="bottom",
            fontsize=11,
            color='gray'
        )

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = Path(output_dir)
            outdir.mkdir(parents=True, exist_ok=True)
            clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
            filename = outdir / f"{clean_title}_{timestamp}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"Line chart saved: {filename}")

        if show:
            plt.show()
            print("Line chart displayed.")
        elif not save:
            warnings.warn("Plot was neither shown nor saved.", WarningMessage)

    except Exception as e:
        print(f"Error creating line chart: {e}")
        raise

    finally:
        plt.close()
