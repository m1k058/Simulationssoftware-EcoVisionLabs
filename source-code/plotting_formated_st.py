"""
Streamlit-optimierte Plotting-Funktionen
Basiert auf plotting_formated.py, angepasst für die Verwendung mit Streamlit.
Alle Funktionen geben matplotlib Figure-Objekte zurück statt sie direkt anzuzeigen.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import pandas as pd
import warnings
import numpy as np

from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES
from errors import PlotNotFoundError, DataProcessingError, WarningMessage
from data_processing import gen


def _setup_plot_style(darkmode=False):
    """Set up the visual style for plots based on the main_custom_calc.py design.
    
    Args:
        darkmode (bool): If True, uses dark color scheme.
        
    Returns:
        dict: Dictionary containing all style parameters.
    """
    # Update font manager
    fm.fontManager.__init__()
    
    # Color scheme
    if darkmode:
        COLOR_BG = "#1a1a1a"
        COLOR_BORDER = "#3B3B3B"
        COLOR_GRID = "#FFFFFF"
        COLOR_TEXT = "#FFFFFF"
    else:
        COLOR_BG = "#ffffff"
        COLOR_BORDER = "#3B3B3B"
        COLOR_GRID = "#000000"
        COLOR_TEXT = "#000000"
    
    # Fonts with fallback
    FONT_MAIN = 'Open Sans'
    FONT_WEIGHT_MAIN = 'normal'
    FONT_TITLE = 'Druk Wide Trial'
    
    # Check if custom fonts are available, otherwise use fallbacks
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    if FONT_MAIN not in available_fonts:
        FONT_MAIN = 'Arial'
    if FONT_TITLE not in available_fonts:
        FONT_TITLE = 'Arial'
    
    # Matplotlib default settings
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': [FONT_MAIN, 'Arial'],
        'font.size': 16,
        'font.weight': FONT_WEIGHT_MAIN
    })
    
    return {
        'COLOR_BG': COLOR_BG,
        'COLOR_BORDER': COLOR_BORDER,
        'COLOR_GRID': COLOR_GRID,
        'COLOR_TEXT': COLOR_TEXT,
        'FONT_MAIN': FONT_MAIN,
        'FONT_WEIGHT_MAIN': FONT_WEIGHT_MAIN,
        'FONT_TITLE': FONT_TITLE
    }


def _add_info_box(fig, description, style, x=0.065, y=0.92):
    """Add an info box to the figure with the plot description.
    
    Args:
        fig: Matplotlib figure object.
        description (str): Description text to display.
        style (dict): Style dictionary from _setup_plot_style.
        x (float): X position of the info box.
        y (float): Y position of the info box.
    """
    if description:
        fig.text(
            x, y, description,
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT'],
            verticalalignment='top',
            bbox=dict(
                boxstyle='square,pad=0.6',
                facecolor=style['COLOR_BG'],
                edgecolor=style['COLOR_BORDER'],
                linewidth=1.5
            )
        )


def _add_copyright(fig, style):
    """Add copyright text to the figure.
    
    Args:
        fig: Matplotlib figure object.
        style (dict): Style dictionary from _setup_plot_style.
    """
    fig.text(
        0.99, 0.01,
        "© EcoVision Labs Team",
        ha="right",
        va="bottom",
        fontsize=14,
        fontfamily=style['FONT_MAIN'],
        fontweight=style['FONT_WEIGHT_MAIN'],
        color=style['COLOR_TEXT']
    )


def _style_legend(legend, style):
    """Apply styling to a legend object.
    
    Args:
        legend: Matplotlib legend object.
        style (dict): Style dictionary from _setup_plot_style.
    """
    legend.get_title().set_fontfamily(style['FONT_TITLE'])
    legend.get_title().set_fontweight('bold')
    legend.get_title().set_fontstyle('italic')
    legend.get_title().set_fontsize(18)
    legend.get_title().set_color(style['COLOR_TEXT'])
    
    for text in legend.get_texts():
        text.set_color(style['COLOR_TEXT'])


def create_stacked_bar_plot(df: pd.DataFrame, energy_keys: list, title: str = "Energieerzeugung", 
                            description: str = "", darkmode: bool = False):
    """Erstellt ein Stacked-Area-Plot für Streamlit.
    
    Args:
        df (pd.DataFrame): Gefiltertes DataFrame mit Zeitpunkt und Energie-Daten.
        energy_keys (list): Liste der Energiequellen-Keys aus ENERGY_SOURCES.
        title (str): Titel des Plots.
        description (str): Beschreibungstext für die Info-Box.
        darkmode (bool): Ob dunkles Farbschema verwendet werden soll.
        
    Returns:
        matplotlib.figure.Figure: Das erstellte Figure-Objekt.
        
    Raises:
        DataProcessingError: Wenn keine passenden Spalten gefunden werden.
    """
    try:
        # Setup style
        style = _setup_plot_style(darkmode)
        
        available_cols = [
            ENERGY_SOURCES[k]["colname"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        if not available_cols:
            raise DataProcessingError(f"No matching columns found for plot '{title}'.")

        labels = [
            ENERGY_SOURCES[k]["name"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        colors = [
            ENERGY_SOURCES[k]["color"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        data_matrix = [df[c].to_numpy(dtype=float) for c in available_cols]

        # Create figure and axes
        fig, ax = plt.subplots(figsize=(22, 10), facecolor=style['COLOR_BG'])
        ax.set_facecolor(style['COLOR_BG'])
        
        # Create stacked area plot
        ax.stackplot(df["Zeitpunkt"], *data_matrix, labels=labels, colors=colors)

        # Axes labels
        ax.set_xlabel(
            "Zeitpunkt",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        ax.set_ylabel(
            "Erzeugung [MWh]",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )

        # Title
        ax.set_title(
            title,
            fontsize=26,
            fontweight='bold',
            fontstyle='italic',
            pad=60,
            fontfamily=style['FONT_TITLE'],
            loc='left',
            color=style['COLOR_TEXT']
        )
        
        # Info box with description
        _add_info_box(fig, description, style)
        
        # Legend
        legend = ax.legend(
            title='Energiequellen',
            bbox_to_anchor=(1.05, 1),
            loc='upper left',
            fontsize=16,
            facecolor=style['COLOR_BG'],
            edgecolor=style['COLOR_BORDER'],
            prop={'family': style['FONT_MAIN'], 'weight': style['FONT_WEIGHT_MAIN']}
        )
        _style_legend(legend, style)
        
        # Axes styling
        ax.set_xlim(df["Zeitpunkt"].min(), df["Zeitpunkt"].max())
        ax.grid(axis='y', alpha=0.2, linestyle='--', color=style['COLOR_GRID'])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=0,
            color=style['COLOR_TEXT'],
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN']
        )
        ax.tick_params(axis='both', colors=style['COLOR_TEXT'], which='both')
        
        # Y-axis labels formatting
        for label in ax.get_yticklabels():
            label.set_fontfamily(style['FONT_MAIN'])
            label.set_fontweight(style['FONT_WEIGHT_MAIN'])
        
        # Spines formatting
        for spine in ax.spines.values():
            spine.set_edgecolor(style['COLOR_BORDER'])
            spine.set_linewidth(1.5)
        
        fig.autofmt_xdate(rotation=45, ha="right")
        
        # Copyright
        _add_copyright(fig, style)

        plt.tight_layout()
        
        return fig

    except Exception as e:
        raise DataProcessingError(f"Failed to generate stacked bar plot: {e}")


def create_line_chart(df: pd.DataFrame, columns: list = None, title: str = "Line chart", 
                     description: str = "", darkmode: bool = False):
    """Erstellt ein Linien-Diagramm für Streamlit.
    
    Args:
        df (pd.DataFrame): DataFrame mit 'Zeitpunkt'-Spalte.
        columns (list[str], optional): Liste der zu plottenden Spalten. Wenn None, werden alle außer 'Zeitpunkt' verwendet.
        title (str): Titel des Plots.
        description (str): Beschreibungstext für die Info-Box.
        darkmode (bool): Ob dunkles Farbschema verwendet werden soll.
        
    Returns:
        matplotlib.figure.Figure: Das erstellte Figure-Objekt.
    """
    try:
        # Setup style
        style = _setup_plot_style(darkmode)
        
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame must contain a 'Zeitpunkt' column.")
        
        # If no columns specified, use all except 'Zeitpunkt'
        if columns is None:
            columns = [col for col in df.columns if col != 'Zeitpunkt']
        else:
            # Validate columns exist
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found in DataFrame: {missing_cols}")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10), facecolor=style['COLOR_BG'])
        ax.set_facecolor(style['COLOR_BG'])
        
        # Plot lines
        for column in columns:
            ax.plot(df['Zeitpunkt'], df[column], label=column, linewidth=1.5)

        # Title
        ax.set_title(
            title,
            fontsize=26,
            fontweight='bold',
            fontstyle='italic',
            pad=80,
            fontfamily=style['FONT_TITLE'],
            loc='left',
            color=style['COLOR_TEXT']
        )
        
        # Axes labels
        ax.set_xlabel(
            "Zeitpunkt",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        ax.set_ylabel(
            "Wert",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        
        # Info box
        if description:
            fig.text(
                0.14, 0.89, description,
                fontsize=16,
                fontfamily=style['FONT_MAIN'],
                fontweight=style['FONT_WEIGHT_MAIN'],
                color=style['COLOR_TEXT'],
                verticalalignment='top',
                bbox=dict(
                    boxstyle='square,pad=0.6',
                    facecolor=style['COLOR_BG'],
                    edgecolor=style['COLOR_BORDER'],
                    linewidth=1.5
                )
            )
        
        # Legend
        legend = ax.legend(
            title='Datenreihen',
            bbox_to_anchor=(1.0, 1.25),
            loc='upper right',
            fontsize=16,
            facecolor=style['COLOR_BG'],
            edgecolor=style['COLOR_BORDER'],
            prop={'family': style['FONT_MAIN'], 'weight': style['FONT_WEIGHT_MAIN']}
        )
        _style_legend(legend, style)
        
        # Grid and styling
        ax.grid(axis='y', alpha=0.2, linestyle='--', color=style['COLOR_GRID'])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=45,
            ha='right',
            color=style['COLOR_TEXT'],
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN']
        )
        ax.tick_params(axis='both', colors=style['COLOR_TEXT'], which='both')
        
        # Y-axis labels formatting
        for label in ax.get_yticklabels():
            label.set_fontfamily(style['FONT_MAIN'])
            label.set_fontweight(style['FONT_WEIGHT_MAIN'])
        
        # Spines formatting
        for spine in ax.spines.values():
            spine.set_edgecolor(style['COLOR_BORDER'])
            spine.set_linewidth(1.5)
        
        fig.autofmt_xdate(rotation=45, ha="right")
        
        # Copyright
        _add_copyright(fig, style)

        plt.subplots_adjust(top=0.82)
        
        return fig

    except Exception as e:
        raise ValueError(f"Error creating line chart: {e}")


def create_balance_plot(df: pd.DataFrame, column1: str, column2: str, title: str = "Balance plot", 
                       description: str = "", darkmode: bool = False):
    """Erstellt ein Balance-Plot für Streamlit.
    
    Args:
        df (pd.DataFrame): DataFrame mit 'Zeitpunkt'-Spalte.
        column1 (str): Erste Spalte (Minuend).
        column2 (str): Zweite Spalte (Subtrahend). Balance = column1 - column2.
        title (str): Titel des Plots.
        description (str): Beschreibungstext für die Info-Box.
        darkmode (bool): Ob dunkles Farbschema verwendet werden soll.
        
    Returns:
        matplotlib.figure.Figure: Das erstellte Figure-Objekt.
    """
    try:
        # Setup style
        style = _setup_plot_style(darkmode)
        
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame must contain a 'Zeitpunkt' column.")
        
        if column1 not in df.columns:
            raise ValueError(f"Column '{column1}' not found in DataFrame.")
        
        if column2 not in df.columns:
            raise ValueError(f"Column '{column2}' not found in DataFrame.")
        
        # Calculate balance
        balance = df[column1] - df[column2]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10), facecolor=style['COLOR_BG'])
        ax.set_facecolor(style['COLOR_BG'])
        
        # Plot balance line
        ax.plot(df['Zeitpunkt'], balance, color=style['COLOR_TEXT'], linewidth=1.5, 
                label=f'{column1} - {column2}')
        
        # Fill areas
        ax.fill_between(df['Zeitpunkt'], balance, 0, where=(balance >= 0), 
                        color='green', alpha=0.4, interpolate=True, label='Überschuss (≥ 0)')
        ax.fill_between(df['Zeitpunkt'], balance, 0, where=(balance < 0), 
                        color='red', alpha=0.4, interpolate=True, label='Defizit (< 0)')
        
        # Zero reference line
        ax.axhline(y=0, color=style['COLOR_GRID'], linestyle='--', linewidth=1, alpha=0.7)
        
        # Title
        ax.set_title(
            title,
            fontsize=26,
            fontweight='bold',
            fontstyle='italic',
            pad=80,
            fontfamily=style['FONT_TITLE'],
            loc='left',
            color=style['COLOR_TEXT']
        )
        
        # Axes labels
        ax.set_xlabel(
            "Zeitpunkt",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        ax.set_ylabel(
            "Balance [MWh]",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        
        # Info box
        if description:
            fig.text(
                0.14, 0.89, description,
                fontsize=16,
                fontfamily=style['FONT_MAIN'],
                fontweight=style['FONT_WEIGHT_MAIN'],
                color=style['COLOR_TEXT'],
                verticalalignment='top',
                bbox=dict(
                    boxstyle='square,pad=0.6',
                    facecolor=style['COLOR_BG'],
                    edgecolor=style['COLOR_BORDER'],
                    linewidth=1.5
                )
            )
        
        # Legend
        legend = ax.legend(
            title='Balance',
            bbox_to_anchor=(1.0, 1.27),
            loc='upper right',
            fontsize=16,
            facecolor=style['COLOR_BG'],
            edgecolor=style['COLOR_BORDER'],
            prop={'family': style['FONT_MAIN'], 'weight': style['FONT_WEIGHT_MAIN']}
        )
        _style_legend(legend, style)
        
        # Grid and styling
        ax.grid(axis='y', alpha=0.2, linestyle='--', color=style['COLOR_GRID'])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.%Y"))
        ax.set_xticklabels(
            ax.get_xticklabels(),
            rotation=45,
            ha='right',
            color=style['COLOR_TEXT'],
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN']
        )
        ax.tick_params(axis='both', colors=style['COLOR_TEXT'], which='both')
        
        # Y-axis labels formatting
        for label in ax.get_yticklabels():
            label.set_fontfamily(style['FONT_MAIN'])
            label.set_fontweight(style['FONT_WEIGHT_MAIN'])
        
        # Spines formatting
        for spine in ax.spines.values():
            spine.set_edgecolor(style['COLOR_BORDER'])
            spine.set_linewidth(1.5)
        
        fig.autofmt_xdate(rotation=45, ha="right")
        
        # Copyright
        _add_copyright(fig, style)

        plt.subplots_adjust(top=0.82)
        
        return fig

    except Exception as e:
        raise ValueError(f"Error creating balance plot: {e}")


def create_histogram_plot(df_erzeugung: pd.DataFrame, df_verbrauch: pd.DataFrame, 
                         title: str = "Renewable Energy Share Histogram", 
                         description: str = "", darkmode: bool = False):
    """Erstellt ein Histogramm für den Anteil erneuerbarer Energien für Streamlit.
    
    Args:
        df_erzeugung (pd.DataFrame): DataFrame mit Erzeugungsdaten.
        df_verbrauch (pd.DataFrame): DataFrame mit Verbrauchsdaten.
        title (str): Titel des Plots.
        description (str): Beschreibungstext für die Info-Box.
        darkmode (bool): Ob dunkles Farbschema verwendet werden soll.
        
    Returns:
        matplotlib.figure.Figure: Das erstellte Figure-Objekt.
    """
    try:
        # Setup style
        style = _setup_plot_style(darkmode)
        
        # Check if renewable generation column exists, otherwise calculate it
        if 'Gesamterzeugung Erneuerbare [MWh]' not in df_erzeugung.columns:
            df_erzeugung_processed = gen.add_total_conventional_generation(df_erzeugung.copy())
        else:
            df_erzeugung_processed = df_erzeugung

        erzeugung_ee = df_erzeugung_processed['Gesamterzeugung Erneuerbare [MWh]']
        
        if 'Netzlast [MWh]' not in df_verbrauch.columns:
            raise ValueError("Consumption DataFrame is missing column 'Netzlast [MWh]'.")
            
        verbrauch = df_verbrauch['Netzlast [MWh]']

        # Combine into a single DataFrame
        df_merged = pd.DataFrame({
            'Erzeugung_EE': erzeugung_ee,
            'Verbrauch': verbrauch
        }).dropna()

        # Calculate percentage
        df_merged['EE_Anteil_Verbrauch'] = 0.0
        mask_verbrauch_pos = df_merged['Verbrauch'] > 0
        
        df_merged.loc[mask_verbrauch_pos, 'EE_Anteil_Verbrauch'] = \
            (df_merged.loc[mask_verbrauch_pos, 'Erzeugung_EE'] / df_merged.loc[mask_verbrauch_pos, 'Verbrauch']) * 100
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10), facecolor=style['COLOR_BG'])
        ax.set_facecolor(style['COLOR_BG'])

        # Define bins
        bins = np.arange(0, 110, 10)
        histogramm_value = np.clip(df_merged['EE_Anteil_Verbrauch'], bins[0], bins[-1] - 0.001)

        # Create histogram
        ax.hist(histogramm_value, bins=bins, edgecolor=style['COLOR_BORDER'], color='#4CAF50')

        # Title
        ax.set_title(
            title,
            fontsize=26,
            fontweight='bold',
            fontstyle='italic',
            pad=60,
            fontfamily=style['FONT_TITLE'],
            loc='left',
            color=style['COLOR_TEXT']
        )
        
        # Axes labels
        ax.set_xlabel(
            "Anteil erneuerbarer Energien am Verbrauch (%)",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        ax.set_ylabel(
            "Anzahl 15-Minuten-Intervalle",
            fontsize=16,
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN'],
            color=style['COLOR_TEXT']
        )
        
        # Info box
        if description:
            fig.text(
                0.09, 0.92, description,
                fontsize=16,
                fontfamily=style['FONT_MAIN'],
                fontweight=style['FONT_WEIGHT_MAIN'],
                color=style['COLOR_TEXT'],
                verticalalignment='top',
                bbox=dict(
                    boxstyle='square,pad=0.6',
                    facecolor=style['COLOR_BG'],
                    edgecolor=style['COLOR_BORDER'],
                    linewidth=1.5
                )
            )
        
        # Custom x-tick labels
        tick_positions = bins[:-1]
        tick_labels = [str(int(x)) for x in bins[:-2]] + ['100+']
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(
            tick_labels,
            color=style['COLOR_TEXT'],
            fontfamily=style['FONT_MAIN'],
            fontweight=style['FONT_WEIGHT_MAIN']
        )
        
        # Grid and styling
        ax.grid(axis='y', alpha=0.2, linestyle='--', color=style['COLOR_GRID'])
        ax.tick_params(axis='both', colors=style['COLOR_TEXT'], which='both')
        
        # Y-axis labels formatting
        for label in ax.get_yticklabels():
            label.set_fontfamily(style['FONT_MAIN'])
            label.set_fontweight(style['FONT_WEIGHT_MAIN'])
        
        # Spines formatting
        for spine in ax.spines.values():
            spine.set_edgecolor(style['COLOR_BORDER'])
            spine.set_linewidth(1.5)
        
        # Copyright
        _add_copyright(fig, style)

        plt.tight_layout()
        
        return fig

    except Exception as e:
        raise ValueError(f"Error creating histogram: {e}")
