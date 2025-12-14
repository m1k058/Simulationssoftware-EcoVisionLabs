"""
Streamlit-optimierte Plotly-Funktionen moved into package.
Original: source-code/plotting_plotly_st.py
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from typing import List, Optional
from pathlib import Path

from constants import ENERGY_SOURCES
import warnings
from data_processing import gen


def _plotly_template(darkmode: bool) -> str:
    return "plotly_dark" if darkmode else "plotly_white"


def create_stacked_bar_plot(
    df: pd.DataFrame,
    energy_keys: List[str],
    title: str = "Energieerzeugung",
    description: str = "",
    darkmode: bool = False,
):
    try:
        if "Zeitpunkt" not in df.columns:
            raise DataProcessingError("DataFrame muss Spalte 'Zeitpunkt' enthalten.")

        available = [
            (ENERGY_SOURCES[k]["colname"], ENERGY_SOURCES[k]["name"], ENERGY_SOURCES[k]["color"]) 
            for k in energy_keys if ENERGY_SOURCES.get(k, {}).get("colname") in df.columns
        ]
        if not available:
            raise DataProcessingError(f"Keine passenden Spalten für Plot '{title}' gefunden.")

        fig = go.Figure()
        for colname, label, color in available:
            fig.add_trace(
                go.Scatter(
                    x=df["Zeitpunkt"],
                    y=df[colname],
                    name=label,
                    mode="lines",
                    line=dict(width=0.5, color=color),
                    stackgroup="one",
                    fillcolor=color,
                    hoverinfo="x+y+name",
                )
            )

        subtitle = f"<br><sup>{description}</sup>" if description else ""
        fig.update_layout(
            title=f"{title}{subtitle}",
            xaxis_title="Zeitpunkt",
            yaxis_title="Erzeugung [MWh]",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template=_plotly_template(darkmode),
            xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
        )

        return fig

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Stacked Bar Plots: {e}")


def create_line_plot(
    df: pd.DataFrame,
    y_axis: str,
    title: str = "Line Plot",
    description: str = "",
    darkmode: bool = False,
):
    """
    Erstellt einen einfachen Line Plot für eine einzelne Spalte.
    
    Args:
        df: DataFrame mit den Daten
        y_axis: Name der Spalte für die Y-Achse
        title: Titel des Plots
        description: Optionale Beschreibung
        darkmode: Ob Dark Mode verwendet werden soll
        
    Returns:
        Plotly Figure Objekt
    """
    try:
        if "Zeitpunkt" not in df.columns:
            raise DataProcessingError("DataFrame muss Spalte 'Zeitpunkt' enthalten.")
        
        if y_axis not in df.columns:
            raise DataProcessingError(f"Spalte '{y_axis}' nicht im DataFrame gefunden.")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["Zeitpunkt"],
                y=df[y_axis],
                mode="lines",
                line=dict(width=2, color="#1f77b4"),
                fill="tozeroy",
                fillcolor="rgba(31, 119, 180, 0.3)",
                hoverinfo="x+y",
            )
        )

        subtitle = f"<br><sup>{description}</sup>" if description else ""
        fig.update_layout(
            title=f"{title}{subtitle}",
            xaxis_title="Zeitpunkt",
            yaxis_title=y_axis,
            hovermode="x unified",
            template=_plotly_template(darkmode),
            xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
            yaxis=dict(rangemode="tozero"),
        )

        return fig

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Line Plots: {e}")


def create_line_chart(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    title: str = "Line chart",
    description: str = "",
    darkmode: bool = False,
):
    try:
        if "Zeitpunkt" not in df.columns:
            raise DataProcessingError("DataFrame muss Spalte 'Zeitpunkt' enthalten.")

        if columns is None:
            columns = [c for c in df.columns if c != "Zeitpunkt"]
        else:
            missing = [c for c in columns if c not in df.columns]
            if missing:
                raise DataProcessingError(f"Spalten nicht gefunden: {missing}")

        fig = px.line(df, x="Zeitpunkt", y=columns, title=title, template=_plotly_template(darkmode))

        subtitle = f"<br><sup>{description}</sup>" if description else ""
        fig.update_layout(
            title=f"{title}{subtitle}",
            xaxis_title="Zeitpunkt",
            yaxis_title="Wert",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        return fig

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Liniendiagramms: {e}")


def create_balance_plot(
    df: pd.DataFrame,
    column1: str,
    column2: str,
    title: str = "Balance plot",
    description: str = "",
    darkmode: bool = False,
):
    try:
        if "Zeitpunkt" not in df.columns:
            raise DataProcessingError("DataFrame muss Spalte 'Zeitpunkt' enthalten.")
        if column1 not in df.columns:
            raise DataProcessingError(f"Spalte '{column1}' nicht gefunden.")
        if column2 not in df.columns:
            raise DataProcessingError(f"Spalte '{column2}' nicht gefunden.")

        dfx = df[["Zeitpunkt", column1, column2]].copy()
        dfx["Balance"] = dfx[column2] - dfx[column1]
        dfx["Surplus"] = dfx["Balance"].clip(lower=0)
        dfx["Deficit"] = dfx["Balance"].clip(upper=0)

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dfx["Zeitpunkt"],
                y=dfx["Deficit"],
                fill="tozeroy",
                fillcolor="rgba(255, 0, 0, 0.4)",
                mode="none",
                name="Defizit (< 0)",
                hoverinfo="none",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=dfx["Zeitpunkt"],
                y=dfx["Surplus"],
                fill="tozeroy",
                fillcolor="rgba(0, 255, 0, 0.4)",
                mode="none",
                name="Überschuss (≥ 0)",
                hoverinfo="none",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=dfx["Zeitpunkt"],
                y=dfx["Balance"],
                mode="lines",
                line=dict(color="black", width=1.5),
                name=f"{column2} - {column1}",
                hoverinfo="x+y",
            )
        )

        subtitle = f"<br><sup>{description}</sup>" if description else ""
        fig.update_layout(
            title=f"{title}{subtitle}",
            xaxis_title="Zeitpunkt",
            yaxis_title="Balance [MWh]",
            hovermode="x unified",
            template=_plotly_template(darkmode),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")

        return fig

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Balance-Plots: {e}")


def create_histogram_plot(
    df_erzeugung: pd.DataFrame,
    df_verbrauch: pd.DataFrame,
    title: str = "Renewable Energy Share Histogram",
    description: str = "",
    darkmode: bool = False,
):
    try:
        if "Gesamterzeugung Erneuerbare [MWh]" not in df_erzeugung.columns:
            df_erzeugung = gen.add_total_renewable_generation(df_erzeugung.copy())

        if "Netzlast [MWh]" not in df_verbrauch.columns:
            raise DataProcessingError("Verbrauchs-DataFrame fehlt Spalte 'Netzlast [MWh]'.")

        dfx = pd.DataFrame({
            "Erzeugung_EE": df_erzeugung["Gesamterzeugung Erneuerbare [MWh]"],
            "Verbrauch": df_verbrauch["Netzlast [MWh]"],
        }).dropna()

        dfx["EE_Anteil_Verbrauch"] = 0.0
        mask = dfx["Verbrauch"] > 0
        dfx.loc[mask, "EE_Anteil_Verbrauch"] = (
            dfx.loc[mask, "Erzeugung_EE"] / dfx.loc[mask, "Verbrauch"]
        ) * 100

        dfx["EE_Anteil_Verbrauch_Clipped"] = dfx["EE_Anteil_Verbrauch"].clip(0, 100.1)

        fig = px.histogram(
            dfx,
            x="EE_Anteil_Verbrauch_Clipped",
            nbins=11,
            title=title,
            template=_plotly_template(darkmode),
        )

        subtitle = f"<br><sup>{description}</sup>" if description else ""
        tick_vals = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105]
        tick_text = [
            "0-10",
            "10-20",
            "20-30",
            "30-40",
            "40-50",
            "50-60",
            "60-70",
            "70-80",
            "80-90",
            "90-100",
            "100+",
        ]

        fig.update_layout(
            title=f"{title}{subtitle}",
            xaxis_title="Anteil erneuerbarer Energien am Verbrauch (%)",
            yaxis_title="Anzahl 15-Minuten-Intervalle",
            xaxis=dict(tickvals=tick_vals, ticktext=tick_text),
            bargap=0.1,
        )

        return fig

    except Exception as e:
        raise DataProcessingError(f"Fehler beim Erstellen des Histogramms: {e}")
