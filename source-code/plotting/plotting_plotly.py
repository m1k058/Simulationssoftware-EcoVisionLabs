import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import warnings
import os
import numpy as np

from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES # Annahme, dass diese Datei unverändert bleibt
from errors import PlotNotFoundError, DataProcessingError, WarningMessage
from data_processing import gen

# --- Haupt-Dispatcher (fast unverändert) ---

def plot_auto(config_manager, manager, plot_identifier, show=True, save=False, output_dir=None):
    try:
        PLOTS = config_manager.get_plots()
        output_dir = output_dir or config_manager.get_global("output_dir")

        if isinstance(plot_identifier, int):
            plot_cfg = next((p for p in PLOTS if p["id"] == plot_identifier), None)
        elif isinstance(plot_identifier, str):
            plot_cfg = next((p for p in PLOTS if p["name"] == plot_identifier), None)
        else:
            raise TypeError("plot_identifier muss ein int (ID) oder str (Name) sein.")

        if not plot_cfg:
            raise PlotNotFoundError(f"Kein Plot mit Bezeichner '{plot_identifier}' gefunden.")

        df_ids = plot_cfg.get("dataframes", [])
        if not df_ids:
            raise DataProcessingError(f"Plot '{plot_cfg['name']}' hat keine DataFrames zugewiesen.")
        
        plot_type = plot_cfg.get("plot_type", "stacked_bar")
        if plot_type == "histogram":
            if len(df_ids) != 2:
                raise DataProcessingError(
                    f"Plot '{plot_cfg['name']}' benötigt genau 2 DataFrames (Erzeugung + Verbrauch) für Histogramm."
                )
        elif len(df_ids) > 1:
            raise NotImplementedError(
                f"Plot '{plot_cfg['name']}' definiert mehrere Datensätze ({df_ids}). "
                "Kombinieren mehrerer DataFrames wird noch nicht unterstützt."
            )

        df_id = df_ids[0]
        df = manager.get(df_id)
        if df is None:
            raise DataProcessingError(
                f"DataFrame mit ID '{df_id}' nicht gefunden für Plot '{plot_cfg['name']}'."
            )

        date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
        date_end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")
        if pd.isna(date_start) or pd.isna(date_end):
            raise DataProcessingError(f"Ungültiges Datumsformat in Plot '{plot_cfg['name']}'.")

        df_filtered = df[(df["Zeitpunkt"] >= date_start) & (df["Zeitpunkt"] <= date_end)]
        if df_filtered.empty:
            raise DataProcessingError(f"Keine Daten im angegebenen Zeitbereich für Plot '{plot_cfg['name']}' gefunden.")

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
                raise DataProcessingError(f"Plot '{plot_cfg['name']}' fehlen 'column1' oder 'column2' für Bilanzplot.")
            title = plot_cfg.get("name", "Balance plot")
            plot_balance(config_manager, df_filtered, column1=col1, column2=col2, title=title, show=show, save=save, output_dir=output_dir)
        elif plot_type == "histogram":
            df_id_2 = df_ids[1]
            df_2 = manager.get(df_id_2)
            if df_2 is None:
                raise DataProcessingError(
                    f"DataFrame mit ID '{df_id_2}' nicht gefunden für Plot '{plot_cfg['name']}'."
                )
            df_2_filtered = df_2[(df_2["Zeitpunkt"] >= date_start) & (df_2["Zeitpunkt"] <= date_end)]
            if df_2_filtered.empty:
                raise DataProcessingError(f"Keine Verbrauchsdaten im angegebenen Zeitbereich für Plot '{plot_cfg['name']}' gefunden.")
            
            title = plot_cfg.get("name", "Renewable Energy Share Histogram")
            plot_ee_consumption_histogram(config_manager, df_filtered, df_2_filtered, title=title, show=show, save=save, output_dir=output_dir)
        else:
            raise NotImplementedError(f"Plot-Typ '{plot_type}' ist nicht implementiert.")

    except Exception as e:
        warnings.warn(f"Plotting fehlgeschlagen für '{plot_identifier}': {e}", WarningMessage)


def _handle_plotly_output(fig, fig_title, show=True, save=False, output_dir=None):
    try:
        if show:
            fig.show()
            print("Plot angezeigt.")

        if save:
            outdir = Path(output_dir or "output")
            outdir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_title = "".join(c for c in fig_title if c.isalnum() or c in (' ', '_')).rstrip()
            filename_base = outdir / f"{clean_title}_{timestamp}"

            filename_html = filename_base.with_suffix(".html")
            fig.write_html(str(filename_html))
            print(f"Interaktiver Plot gespeichert: {filename_html}")

            try:
                filename_png = filename_base.with_suffix(".png")
                fig.write_image(str(filename_png), width=1920, height=1080, scale=1)
                print(f"Statischer Plot gespeichert: {filename_png}")
            except ValueError as e:
                warnings.warn(f"PNG-Speichern fehlgeschlagen. Ist 'kaleido' installiert? (pip install kaleido). Fehler: {e}", WarningMessage)
        
        if not show and not save:
            warnings.warn("Plot wurde weder angezeigt noch gespeichert.", WarningMessage)

    except Exception as e:
        print(f"Fehler beim Anzeigen/Speichern des Plots: {e}")


def plot_stacked_bar(df, plot_cfg, show=True, save=False, output_dir=None):
    try:
        energy_keys = plot_cfg["energy_sources"]
        
        available_cols = [
            ENERGY_SOURCES[k]["colname"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        if not available_cols:
            raise DataProcessingError(f"Keine passenden Spalten für Plot '{plot_cfg['name']}' gefunden.")

        labels = [
            ENERGY_SOURCES[k]["name"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        colors = [
            ENERGY_SOURCES[k]["color"] for k in energy_keys
            if ENERGY_SOURCES[k]["colname"] in df.columns
        ]
        
        fig = go.Figure()

        for i in range(len(available_cols)):
            fig.add_trace(go.Scatter(
                x=df["Zeitpunkt"], 
                y=df[available_cols[i]],
                name=labels[i],
                mode='lines',
                line=dict(width=0.5, color=colors[i]),
                stackgroup='one',
                fillcolor=colors[i],
                hoverinfo='x+y+name'
            ))

        fig.update_layout(
            title=f"{plot_cfg['name']}<br>{plot_cfg['description']}",
            xaxis_title="Timestamp",
            yaxis_title="Generation [MWh]",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_dark",
            xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()])
        )
        
        _handle_plotly_output(fig, plot_cfg['name'], show, save, output_dir)

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Stacked Bar Plots: {e}")


def plot_ee_consumption_histogram(config_manager, df_erzeugung: pd.DataFrame, df_verbrauch: pd.DataFrame, title: str = "Renewable Energy Share Histogram", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Gesamterzeugung Erneuerbare [MWh]' not in df_erzeugung.columns:
            df_erzeugung_processed = gen.add_total_renewable_generation(df_erzeugung.copy())
        else:
            df_erzeugung_processed = df_erzeugung

        erzeugung_ee = df_erzeugung_processed['Gesamterzeugung Erneuerbare [MWh]']
        
        if 'Netzlast [MWh]' not in df_verbrauch.columns:
            raise ValueError("Verbrauchs-DataFrame fehlt Spalte 'Netzlast [MWh]'.")
            
        verbrauch = df_verbrauch['Netzlast [MWh]']

        df_merged = pd.DataFrame({
            'Erzeugung_EE': erzeugung_ee,
            'Verbrauch': verbrauch
        }).dropna()

        df_merged['EE_Anteil_Verbrauch'] = 0.0
        mask_verbrauch_pos = df_merged['Verbrauch'] > 0
        
        df_merged.loc[mask_verbrauch_pos, 'EE_Anteil_Verbrauch'] = \
            (df_merged.loc[mask_verbrauch_pos, 'Erzeugung_EE'] / df_merged.loc[mask_verbrauch_pos, 'Verbrauch']) * 100
        
        df_merged['EE_Anteil_Verbrauch_Clipped'] = df_merged['EE_Anteil_Verbrauch'].clip(0, 100.1)

        fig = px.histogram(
            df_merged, 
            x="EE_Anteil_Verbrauch_Clipped",
            nbins=11,
            title=f"Histogram: {title}",
            template="plotly_dark"
        )

        tick_vals = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105]
        tick_text = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100", "100+"]
        
        fig.update_layout(
            xaxis_title="Share of renewable energy in consumption (%)",
            yaxis_title="Number of 15-minute intervals",
            xaxis=dict(
                tickvals=tick_vals,
                ticktext=tick_text
            ),
            bargap=0.1,
            annotations=[
                dict(
                    text="© EcoVision Labs Team",
                    align='right',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=0.95,
                    y=-0.15,
                    font=dict(size=11, color='gray')
                )
            ]
        )

        _handle_plotly_output(fig, title, show, save, output_dir)

    except Exception as e:
        print(f"Fehler beim Erstellen des Histogramms: {e}")
        raise


def plot_balance(config_manager, df: pd.DataFrame, column1: str, column2: str, title="Balance plot", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame muss 'Zeitpunkt'-Spalte enthalten.")
        if column1 not in df.columns:
            raise ValueError(f"Spalte '{column1}' nicht gefunden.")
        if column2 not in df.columns:
            raise ValueError(f"Spalte '{column2}' nicht gefunden.")
        
        df['Balance'] = df[column1] - df[column2]
        df['Surplus'] = df['Balance'].clip(lower=0)
        df['Deficit'] = df['Balance'].clip(upper=0)
        
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['Zeitpunkt'],
            y=df['Deficit'],
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.4)',
            mode='none',
            name='Deficit (< 0)',
            hoverinfo='none'
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Zeitpunkt'],
            y=df['Surplus'],
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.4)',
            mode='none',
            name='Surplus (≥ 0)',
            hoverinfo='none'
        ))

        fig.add_trace(go.Scatter(
            x=df['Zeitpunkt'],
            y=df['Balance'],
            mode='lines',
            line=dict(color='black', width=1.5),
            name=f'{column1} - {column2}',
            hoverinfo='x+y'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Timestamp",
            yaxis_title="Balance [MWh]",
            hovermode="x unified",
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            annotations=[
                dict(
                    text="© EcoVision Labs Team",
                    align='right',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=0.95,
                    y=-0.15,
                    font=dict(size=11, color='gray')
                )
            ]
        )
        
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")
        
        _handle_plotly_output(fig, title, show, save, output_dir)

    except Exception as e:
        print(f"Fehler beim Erstellen des Bilanzplots: {e}")
        raise


def plot_line_chart(config_manager, df: pd.DataFrame, columns=None, title="Line chart", show=True, save=False, output_dir=None):
    output_dir = output_dir or config_manager.get_global("output_dir")
    try:
        if 'Zeitpunkt' not in df.columns:
            raise ValueError("DataFrame muss 'Zeitpunkt'-Spalte enthalten.")
        
        if columns is None:
            columns = [col for col in df.columns if col != 'Zeitpunkt']
        else:
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Spalten nicht gefunden: {missing_cols}")
        
        fig = px.line(
            df, 
            x='Zeitpunkt', 
            y=columns, 
            title=title,
            template="plotly_dark"
        )
        
        fig.update_layout(
            xaxis_title="Timestamp",
            yaxis_title="Value",
            hovermode="x unified",
            annotations=[
                dict(
                    text="© EcoVision Labs Team",
                    align='right',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=0.95,
                    y=-0.15,
                    font=dict(size=11, color='gray')
                )
            ]
        )
        
        _handle_plotly_output(fig, title, show, save, output_dir)

    except Exception as e:
        print(f"Fehler beim Erstellen des Liniendiagramms: {e}")
        raise
