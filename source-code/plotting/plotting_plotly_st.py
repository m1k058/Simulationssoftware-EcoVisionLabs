"""
Streamlit-optimierte Plotly-Funktionen 
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from constants import ENERGY_SOURCES
from data_processing import gen


def create_stacked_area_plot(
    df: pd.DataFrame,
    energy_keys: list[str] | None = None,
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """Erstellt einen gestapelten Area-Plot für Energieerzeugung."""
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    # Bestimme welche Energiequellen angezeigt werden sollen
    if energy_keys is None:
        energy_keys = list(ENERGY_SOURCES.keys())
    
    # Sammle verfügbare Spalten
    plot_data = []
    color_map = {}
    
    for key in energy_keys:
        if key not in ENERGY_SOURCES:
            continue
        
        source = ENERGY_SOURCES[key]
        colname = source.get("colname")
        
        if colname and colname in df.columns:
            plot_data.append({
                "colname": colname,
                "label": source.get("name", key),
                "color": source.get("color", "#cccccc")
            })
            color_map[source.get("name", key)] = source.get("color", "#cccccc")
    
    if not plot_data:
        raise ValueError("Keine passenden Energiespalten im DataFrame gefunden")
    
    # Daten in Long-Format umwandeln
    colnames = [item["colname"] for item in plot_data]
    label_map = {item["colname"]: item["label"] for item in plot_data}
    
    df_long = pd.melt(
        df[["Zeitpunkt"] + colnames],
        id_vars=["Zeitpunkt"],
        value_vars=colnames,
        var_name="Spalte",
        value_name="Wert"
    )
    df_long["Quelle"] = df_long["Spalte"].map(label_map)
    
    # Plot erstellen
    fig = px.area(
        df_long,
        x="Zeitpunkt",
        y="Wert",
        color="Quelle",
        title=title if title else None,
        template="plotly_white",
        color_discrete_map=color_map,
    )
    
    # Hover-Template anpassen: Nur Quelle und Wert, kein wiederholter Zeitstempel
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    fig.update_layout(
        xaxis_title="Zeitpunkt",
        yaxis_title="Erzeugung [MWh]",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
    )
    
    return fig


def create_line_plot(
    df: pd.DataFrame,
    y_column: str,
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """Erstellt einen Line Plot mit Füllung."""
    
    if "Zeitpunkt" not in df.columns or y_column not in df.columns:
        raise KeyError(f"Benötigte Spalten fehlen: Zeitpunkt, {y_column}")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df[y_column],
            mode="lines",
            line=dict(width=2, color="#1f77b4"),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.3)",
            name=y_column,
        )
    )
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeitpunkt",
        yaxis_title=y_column,
        hovermode="x unified",
        template="plotly_white",
        xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
        yaxis=dict(rangemode="tozero"),
    )
    
    return fig


def create_multi_line_chart(
    df: pd.DataFrame,
    y_columns: list[str] | None = None,
    title: str = "",
) -> go.Figure:
    """Erstellt ein Liniendiagramm mit mehreren Linien."""
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    if y_columns is None:
        y_columns = [col for col in df.columns if col != "Zeitpunkt"]
    
    fig = px.line(
        df,
        x="Zeitpunkt",
        y=y_columns,
        title=title if title else None,
        template="plotly_white"
    )
    
    fig.update_layout(
        xaxis_title="Zeitpunkt",
        yaxis_title="Wert",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_balance_plot(
    df: pd.DataFrame,
    generation_col: str,
    demand_col: str,
    title: str = "",
) -> go.Figure:
    """Erstellt einen Balance-Plot (Erzeugung - Verbrauch)."""
    
    required = ["Zeitpunkt", generation_col, demand_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Fehlende Spalten: {', '.join(missing)}")
    
    # Balance berechnen
    df_plot = df[["Zeitpunkt", generation_col, demand_col]].copy()
    df_plot["Balance"] = df_plot[demand_col] - df_plot[generation_col]
    df_plot["Überschuss"] = df_plot["Balance"].clip(lower=0)
    df_plot["Defizit"] = df_plot["Balance"].clip(upper=0)
    
    fig = go.Figure()
    
    # Defizit (rot)
    fig.add_trace(
        go.Scatter(
            x=df_plot["Zeitpunkt"],
            y=df_plot["Defizit"],
            fill="tozeroy",
            fillcolor="rgba(255, 0, 0, 0.4)",
            mode="none",
            name="Defizit",
        )
    )
    
    # Überschuss (grün)
    fig.add_trace(
        go.Scatter(
            x=df_plot["Zeitpunkt"],
            y=df_plot["Überschuss"],
            fill="tozeroy",
            fillcolor="rgba(0, 255, 0, 0.4)",
            mode="none",
            name="Überschuss",
        )
    )
    
    # Balance-Linie
    fig.add_trace(
        go.Scatter(
            x=df_plot["Zeitpunkt"],
            y=df_plot["Balance"],
            mode="lines",
            line=dict(color="black", width=1.5),
            name=f"{demand_col} - {generation_col}",
        )
    )
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeitpunkt",
        yaxis_title="Balance [MWh]",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")
    
    return fig


def create_renewable_histogram(
    df_generation: pd.DataFrame,
    df_demand: pd.DataFrame,
    title: str = "",
) -> go.Figure:
    """Erstellt ein Histogramm für den Anteil erneuerbarer Energien."""
    
    # Prüfe/berechne Gesamterzeugung Erneuerbare
    if "Gesamterzeugung Erneuerbare [MWh]" not in df_generation.columns:
        df_generation = gen.add_total_renewable_generation(df_generation.copy())
    
    if "Netzlast [MWh]" not in df_demand.columns:
        raise KeyError("Spalte 'Netzlast [MWh]' fehlt im Demand-DataFrame")
    
    # Kombiniere Daten
    df_combined = pd.DataFrame({
        "Erzeugung_EE": df_generation["Gesamterzeugung Erneuerbare [MWh]"],
        "Verbrauch": df_demand["Netzlast [MWh]"],
    }).dropna()
    
    # Berechne Anteil
    df_combined["EE_Anteil"] = 0.0
    mask = df_combined["Verbrauch"] > 0
    df_combined.loc[mask, "EE_Anteil"] = (
        df_combined.loc[mask, "Erzeugung_EE"] / df_combined.loc[mask, "Verbrauch"]
    ) * 100
    
    df_combined["EE_Anteil_Clipped"] = df_combined["EE_Anteil"].clip(0, 100.1)
    
    fig = px.histogram(
        df_combined,
        x="EE_Anteil_Clipped",
        nbins=11,
        title=title if title else None,
        template="plotly_white",
    )
    
    # Custom Tick Labels
    tick_vals = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 105]
    tick_text = ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", 
                 "60-70", "70-80", "80-90", "90-100", "100+"]
    
    fig.update_layout(
        xaxis_title="Anteil erneuerbarer Energien am Verbrauch (%)",
        yaxis_title="Anzahl 15-Minuten-Intervalle",
        xaxis=dict(tickvals=tick_vals, ticktext=tick_text),
        bargap=0.1,
    )
    
    return fig
