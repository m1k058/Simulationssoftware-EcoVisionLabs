"""
Streamlit-optimierte Plotly-Funktionen 
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from constants import ENERGY_SOURCES, SOURCES_GROUPS


def create_generation_plot(
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
        # Fallback: nimm alle MWh-Spalten (ohne Gesamt) aus dem DF, um wenigstens etwas anzuzeigen
        fallback_cols = [c for c in df.columns if "[MWh]" in c and "Gesamt" not in c]
        if not fallback_cols:
            raise ValueError("Keine passenden Energiespalten im DataFrame gefunden")
        plot_data = [{
            "colname": c,
            "label": c.replace(" [MWh]", ""),
            "color": "#999999",
        } for c in fallback_cols]
        color_map = {item["label"]: item["color"] for item in plot_data}
    
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
    
    # Hover-Template anpassen
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    # Unsichtbare Trace für Gesamtsumme hinzufügen (nur im Hover sichtbar)
    df['_Gesamterzeugung'] = df[colnames].sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["_Gesamterzeugung"],
            mode="lines",
            name="Gesamterzeugung",
            line=dict(color="rgba(0,0,0,0)", width=0),  # Unsichtbar
            showlegend=True,
            hovertemplate="<b>Gesamterzeugung</b>: %{y:,.2f}<extra></extra>"
        )
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


def plot_parameter_saturation(
    simulation_results: list[dict] | pd.DataFrame,
    parameter_name: str,
    kpi_name: str,
    title: str = "Parameter-Saettigungskurve"
) -> go.Figure:
    """
    Erstellt eine Saettigungskurve fuer Parameter-Studien (z.B. Speichergroesse vs. Autarkie).
    
    Args:
        simulation_results: Liste von Dicts mit Keys wie 'scenario_label', 'parameter_value', 'kpi_value'
                           ODER DataFrame mit Spalten 'scenario_label', 'parameter_value', 'kpi_value'
        parameter_name: Name des Parameters fuer X-Achse (z.B. "Speichergroesse [MWh]")
        kpi_name: Name des KPI fuer Y-Achse (z.B. "Autarkie [%]")
        title: Plot-Titel
    
    Returns:
        Plotly Figure mit Liniendiagramm + Markern
    """
    # Konvertiere zu DataFrame falls noetig
    if isinstance(simulation_results, list):
        df = pd.DataFrame(simulation_results)
    else:
        df = simulation_results.copy()
    
    # Validierung
    required_cols = ['scenario_label', 'parameter_value', 'kpi_value']
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Spalte '{col}' fehlt im DataFrame. Benoetigt: {required_cols}")
    
    # Sortiere nach Parameter-Wert fuer saubere Linie
    df = df.sort_values('parameter_value')
    
    # Erstelle Figure
    fig = go.Figure()
    
    # Fuege Linie mit Markern hinzu
    fig.add_trace(go.Scatter(
        x=df['parameter_value'],
        y=df['kpi_value'],
        mode='lines+markers',
        name=kpi_name,
        line=dict(
            color='#1f77b4',  # Blau als Akzentfarbe
            width=3
        ),
        marker=dict(
            size=10,
            color='#1f77b4',
            line=dict(color='white', width=2)
        ),
        hovertemplate=(
            "<b>%{customdata}</b><br>" +
            f"{parameter_name}: %{{x:.2f}}<br>" +
            f"{kpi_name}: %{{y:.2f}}<br>" +
            "<extra></extra>"
        ),
        customdata=df['scenario_label']
    ))
    
    # Layout anpassen
    fig.update_layout(
        title=title,
        template="plotly_dark",
        xaxis_title=parameter_name,
        yaxis_title=kpi_name,
        hovermode="closest",
        showlegend=False,
        height=500,
        margin=dict(l=60, r=30, t=50, b=60),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.2)'
        )
    )
    
    return fig


def create_consumption_plot(
    df: pd.DataFrame,
    sector_columns: list[str] | None = None,
    total_column: str = "Gesamt [MWh]",
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """Erstellt einen kombinierten Plot für Verbrauchsdaten: Stacked Area für Sektoren + Linie für Gesamtverbrauch."""
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    # Bestimme Sektorspalten automatisch wenn nicht angegeben
    if sector_columns is None:
        # Alle Spalten außer Zeitpunkt und Gesamt
        sector_columns = [col for col in df.columns 
                         if col != "Zeitpunkt" and "Gesamt" not in col]
    
    if not sector_columns:
        raise ValueError("Keine Sektorspalten im DataFrame gefunden")
    
    # Farben für Sektoren
    sector_colors = {
        "Haushalte [MWh]": "#FF6B6B",
        "Gewerbe [MWh]": "#4ECDC4",
        "Landwirtschaft [MWh]": "#45B7D1",
    }
    
    # Stacked Area für Sektoren
    df_long = pd.melt(
        df[["Zeitpunkt"] + sector_columns],
        id_vars=["Zeitpunkt"],
        value_vars=sector_columns,
        var_name="Sektor",
        value_name="Wert"
    )
    
    fig = px.area(
        df_long,
        x="Zeitpunkt",
        y="Wert",
        color="Sektor",
        title=title if title else None,
        template="plotly_white",
        color_discrete_map=sector_colors,
    )
    
    # Hover-Template für Area anpassen
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    # Berechne Gesamtverbrauch
    if total_column in df.columns:
        gesamtverbrauch = df[total_column]
    else:
        gesamtverbrauch = df[sector_columns].sum(axis=1)
    
    # Unsichtbare Trace für Gesamtverbrauch (nur im Hover sichtbar)
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=gesamtverbrauch,
            mode="lines",
            name="Gesamtverbrauch",
            line=dict(color="rgba(0,0,0,0)", width=0),  # Unsichtbar
            showlegend=True,
            hovertemplate="<b>Gesamtverbrauch</b>: %{y:,.2f}<extra></extra>"
        )
    )
    
    fig.update_layout(
        xaxis_title="Zeitpunkt",
        yaxis_title="Verbrauch [MWh]",
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
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """Erstellt ein Liniendiagramm mit mehreren Linien."""
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    if y_columns is None:
        y_columns = [col for col in df.columns if col != "Zeitpunkt"]
    
    fig = px.line(
        df,
        x="Zeitpunkt",
        y=y_columns,
        title=title if title else None,
        template="plotly_white"
    )
    
    # Hover-Template anpassen
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
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
        # Inline-Berechnung statt gen.add_total_renewable_generation()
        shortcodes = SOURCES_GROUPS.get("Renewable", [])
        renewable_cols = [
            ENERGY_SOURCES[sc]["colname"]
            for sc in shortcodes
            if sc in ENERGY_SOURCES and ENERGY_SOURCES[sc]["colname"] in df_generation.columns
        ]
        df_generation["Gesamterzeugung Erneuerbare [MWh]"] = df_generation[renewable_cols].sum(axis=1)
    
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


def create_balance_area_plot(
    df: pd.DataFrame,
    balance_column: str = "Bilanz [MWh]",
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen Bilanz-Plot mit positiven Werten in grün und negativen Werten in rot.
    
    Args:
        df: DataFrame mit Zeitpunkt und Bilanzspalte
        balance_column: Name der Bilanzspalte (default: "Bilanz [MWh]")
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure
    """
    
    if "Zeitpunkt" not in df.columns or balance_column not in df.columns:
        raise KeyError(f"Benötigte Spalten fehlen: Zeitpunkt, {balance_column}")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    # Trenne positive und negative Werte
    df['Überschuss'] = df[balance_column].clip(lower=0)
    df['Defizit'] = df[balance_column].clip(upper=0)
    
    fig = go.Figure()
    
    # Negative Werte (Defizit) in Rot
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["Defizit"],
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.5)",  # Rot mit Transparenz
            line=dict(color="rgb(239, 68, 68)", width=1),
            mode="lines",
            name="Defizit (Verbrauch > Erzeugung)",
            hovertemplate="<b>Defizit</b>: %{y:,.2f} MWh<extra></extra>"
        )
    )
    
    # Positive Werte (Überschuss) in Grün
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["Überschuss"],
            fill="tozeroy",
            fillcolor="rgba(34, 197, 94, 0.5)",  # Grün mit Transparenz
            line=dict(color="rgb(34, 197, 94)", width=1),
            mode="lines",
            name="Überschuss (Erzeugung > Verbrauch)",
            hovertemplate="<b>Überschuss</b>: %{y:,.2f} MWh<extra></extra>"
        )
    )
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeitpunkt",
        yaxis_title="Bilanz [MWh]",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
    )
    
    # Nulllinie hinzufügen
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color="gray")
    
    return fig


def create_generation_with_load_plot(
    df: pd.DataFrame,
    load_column: str = "Skalierte Netzlast [MWh]",
    energy_keys: list[str] | None = None,
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen kombinierten Plot mit gestapelter Erzeugung und Gesamtlast als Linie.
    
    Args:
        df: DataFrame mit Zeitpunkt, Erzeugungsspalten und Lastspalte
        load_column: Name der Lastspalte (default: "Skalierte Netzlast [MWh]")
        energy_keys: Liste der Energiequellen-Keys (default: alle aus ENERGY_SOURCES)
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure
    """
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    if load_column not in df.columns:
        raise KeyError(f"Lastspalte '{load_column}' fehlt im DataFrame")
    
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
    
    # Plot erstellen (Stacked Area)
    fig = px.area(
        df_long,
        x="Zeitpunkt",
        y="Wert",
        color="Quelle",
        title=title if title else None,
        template="plotly_white",
        color_discrete_map=color_map,
    )
    
    # Hover-Template für Area anpassen
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    # Gesamtlast als Linie hinzufügen
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df[load_column],
            mode="lines",
            name="Gesamtlast",
            line=dict(color="#bd2b3a", width=1.5, dash="solid"),
            hovertemplate="<b>Gesamtlast</b>: %{y:,.2f}<extra></extra>"
        )
    )
    
    fig.update_layout(
        xaxis_title="Zeitpunkt",
        yaxis_title="Leistung [MWh]",
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


def create_duration_curve_plot(
    df: pd.DataFrame,
    balance_column: str = "Bilanz [MWh]",
    rest_balance_column: str = "Rest Bilanz [MWh]",
    title: str = "",
) -> go.Figure:
    """
    Erstellt eine geordnete Jahresdauerlinie der Residuallast.
    
    Zeigt zwei Linien:
    - Ohne Speicher: Originale Bilanz (sortiert)
    - Mit Speicher: Rest Bilanz nach Speicheroperationen (sortiert)
    
    Args:
        df: DataFrame mit Bilanzspalten
        balance_column: Name der Original-Bilanzspalte
        rest_balance_column: Name der Rest-Bilanzspalte nach Speichern
        title: Plot-Titel
    
    Returns:
        Plotly Figure mit Dauerlinie
    """
    
    if balance_column not in df.columns:
        raise KeyError(f"Spalte '{balance_column}' fehlt im DataFrame")
    
    # Sortiere Bilanz absteigend (höchste Werte zuerst)
    balance_sorted = df[balance_column].sort_values(ascending=False).reset_index(drop=True)
    
    # Erstelle Stunden-Achse (15min = 0.25h)
    hours = balance_sorted.index * 0.25
    
    fig = go.Figure()
    
    # Linie für "Ohne Speicher"
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=balance_sorted,
            mode="lines",
            name="Ohne Speicher",
            line=dict(color="rgb(59, 130, 246)", width=2),  # Blau
            hovertemplate="<b>Ohne Speicher</b><br>Stunde: %{x:.1f}<br>Leistung: %{y:,.2f} MWh<extra></extra>"
        )
    )
    
    # Linie für "Mit Speicher" (falls vorhanden)
    if rest_balance_column in df.columns:
        rest_balance_sorted = df[rest_balance_column].sort_values(ascending=False).reset_index(drop=True)
        
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=rest_balance_sorted,
                mode="lines",
                name="Mit Speicher",
                line=dict(color="rgb(16, 185, 129)", width=2),  # Grün
                hovertemplate="<b>Mit Speicher</b><br>Stunde: %{x:.1f}<br>Leistung: %{y:,.2f} MWh<extra></extra>"
            )
        )
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Stunden des Jahres",
        yaxis_title="Residuallast [MWh]",
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
    
    # Nulllinie hinzufügen
    fig.add_hline(y=0, line_width=1.5, line_dash="dash", line_color="gray")
    
    return fig


def create_soc_stacked_plot(
    df: pd.DataFrame,
    soc_columns: list[str] | None = None,
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen Stacked Area Plot für State of Charge (SOC) der Speicher.
    
    Args:
        df: DataFrame mit Zeitpunkt und SOC-Spalten
        soc_columns: Liste der SOC-Spaltennamen (z.B. ["Batteriespeicher SOC MWh", ...])
                    Falls None, werden automatisch alle "*SOC MWh" Spalten verwendet
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure mit gestapelten SOC-Kurven
    """
    
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    # Zeitfilter anwenden
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    # Automatische Erkennung der SOC-Spalten
    if soc_columns is None:
        soc_columns = [col for col in df.columns if "SOC MWh" in col]
    
    if not soc_columns:
        raise ValueError("Keine SOC-Spalten im DataFrame gefunden")
    
    # Farben für die Speicher
    storage_colors = {
        "Batteriespeicher SOC MWh": "#f59e0b",  # Orange
        "Pumpspeicher SOC MWh": "#3b82f6",      # Blau
        "Wasserstoffspeicher SOC MWh": "#8b5cf6"  # Lila
    }
    
    # Bereite Namen für bessere Darstellung vor
    label_map = {}
    for col in soc_columns:
        # Entferne " SOC MWh" für saubere Labels
        label = col.replace(" SOC MWh", "")
        label_map[col] = label
    
    # Daten in Long-Format umwandeln
    df_long = pd.melt(
        df[["Zeitpunkt"] + soc_columns],
        id_vars=["Zeitpunkt"],
        value_vars=soc_columns,
        var_name="Speicher",
        value_name="SOC"
    )
    df_long["Speicher_Label"] = df_long["Speicher"].map(label_map)
    
    # Erstelle Farbzuordnung mit Labels
    color_map = {label_map[col]: storage_colors.get(col, "#cccccc") for col in soc_columns}
    
    # Plot erstellen
    fig = px.area(
        df_long,
        x="Zeitpunkt",
        y="SOC",
        color="Speicher_Label",
        title=title if title else None,
        template="plotly_white",
        color_discrete_map=color_map,
    )
    
    # Hover-Template anpassen
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f} MWh<extra></extra>"
    )
    
    fig.update_layout(
        xaxis_title="Zeitpunkt",
        yaxis_title="State of Charge [MWh]",
        hovermode="x unified",
        legend=dict(
            title="Speicher",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()]),
    )
    
    return fig


def create_monthly_balance_plot(
    df: pd.DataFrame,
    balance_column: str = "Rest Bilanz [MWh]",
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen grouped Bar-Plot für monatlich getrennte Überschüsse und Defizite.
    
    Args:
        df: DataFrame mit Zeitpunkt und Bilanzspalte
        balance_column: Name der Bilanzspalte (default: "Rest Bilanz [MWh]")
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure mit gruppiertem Balkendiagramm für monatliche Überschüsse und Defizite
    """
    
    if "Zeitpunkt" not in df.columns or balance_column not in df.columns:
        raise KeyError(f"Benötigte Spalten fehlen: Zeitpunkt, {balance_column}")
    
    # Kopie erstellen und Zeitpunkt konvertieren
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    
    # Zeitfilter anwenden
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    # Extrahiere Jahr und Monat
    df['Jahr'] = df['Zeitpunkt'].dt.year
    df['Monat'] = df['Zeitpunkt'].dt.month
    df['Monat_Name'] = df['Zeitpunkt'].dt.strftime('%B')
    
    # Berechne Überschüsse und Defizite separat
    df['Überschuss'] = df[balance_column].clip(lower=0)  # Nur positive Werte
    df['Defizit'] = df[balance_column].clip(upper=0).abs()  # Nur negative Werte, als positive Darstellung
    
    # Aufsummieren pro Monat
    monthly_data = df.groupby(['Jahr', 'Monat', 'Monat_Name']).agg({
        'Überschuss': 'sum',
        'Defizit': 'sum'
    }).reset_index()
    
    monthly_data['Label'] = monthly_data['Monat_Name'] + ' ' + monthly_data['Jahr'].astype(str)
    
    fig = go.Figure()
    
    # Überschüsse (grün)
    fig.add_trace(
        go.Bar(
            x=monthly_data['Label'],
            y=monthly_data['Überschuss'],
            name='Überschuss',
            marker=dict(color='rgba(34, 197, 94, 0.8)'),  # Grün
            text=monthly_data['Überschuss'].apply(lambda x: f"{x/1e3:.1f}" if x > 0 else ""),
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>Überschuss: %{y:,.0f} MWh<extra></extra>",
        )
    )
    
    # Defizite (rot)
    fig.add_trace(
        go.Bar(
            x=monthly_data['Label'],
            y=monthly_data['Defizit'],
            name='Defizit',
            marker=dict(color='rgba(239, 68, 68, 0.8)'),  # Rot
            text=monthly_data['Defizit'].apply(lambda x: f"{x/1e3:.1f}" if x > 0 else ""),
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>Defizit: %{y:,.0f} MWh<extra></extra>",
        )
    )
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Monat",
        yaxis_title="Monatliche Bilanz [MWh]",
        barmode='group',
        hovermode="x unified",
        template="plotly_white",
        xaxis=dict(tickangle=-45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    return fig


def create_emobility_soc_plot(
    df: pd.DataFrame,
    soc_column: str = "EMobility SOC [MWh]",
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen gefüllten Linienplot für E-Mobility State of Charge (SOC).
    
    Args:
        df: DataFrame mit Zeitpunkt und SOC-Spalte
        soc_column: Name der SOC-Spalte (default: "EMobility SOC [MWh]")
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure mit SOC-Linie
    """
    
    if "Zeitpunkt" not in df.columns or soc_column not in df.columns:
        raise KeyError(f"Benötigte Spalten fehlen: Zeitpunkt, {soc_column}")
    
    # Kopie erstellen und Zeitpunkt konvertieren
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    
    # Zeitfilter anwenden
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Zeitpunkt'],
        y=df[soc_column],
        mode='lines',
        name='EV-Flotte SOC',
        fill='tozeroy',
        line=dict(color='#2ecc71', width=1),
        fillcolor='rgba(46, 204, 113, 0.3)',
        hovertemplate="<b>%{x|%d.%m.%Y %H:%M}</b><br>SOC: %{y:,.0f} MWh<extra></extra>"
    ))
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeit",
        yaxis_title="SOC [MWh]",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig


def create_emobility_power_plot(
    df: pd.DataFrame,
    power_column: str = "EMobility Power [MW]",
    title: str = "",
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> go.Figure:
    """
    Erstellt einen Split-Plot für E-Mobility Lade-/Entladeleistung.
    
    Positive Werte = V2G Rückspeisung (grün)
    Negative Werte = Laden aus Netz (rot)
    
    Args:
        df: DataFrame mit Zeitpunkt und Power-Spalte
        power_column: Name der Power-Spalte (default: "EMobility Power [MW]")
        title: Plot-Titel
        date_from: Startdatum für Filterung
        date_to: Enddatum für Filterung
    
    Returns:
        Plotly Figure mit gestacktem Lade-/Entladediagramm
    """
    
    if "Zeitpunkt" not in df.columns or power_column not in df.columns:
        raise KeyError(f"Benötigte Spalten fehlen: Zeitpunkt, {power_column}")
    
    # Kopie erstellen und Zeitpunkt konvertieren
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    
    # Zeitfilter anwenden
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    power_data = df[power_column]
    
    fig = go.Figure()
    
    # Positive Werte (Entladen/V2G) in Grün
    fig.add_trace(go.Scatter(
        x=df['Zeitpunkt'],
        y=power_data.clip(lower=0),
        mode='lines',
        name='V2G Rückspeisung',
        fill='tozeroy',
        line=dict(color='#27ae60', width=0.5),
        fillcolor='rgba(39, 174, 96, 0.5)',
        hovertemplate="<b>%{x|%d.%m.%Y %H:%M}</b><br>V2G: %{y:,.2f} MW<extra></extra>"
    ))
    
    # Negative Werte (Laden) in Rot
    fig.add_trace(go.Scatter(
        x=df['Zeitpunkt'],
        y=power_data.clip(upper=0),
        mode='lines',
        name='Laden',
        fill='tozeroy',
        line=dict(color='#e74c3c', width=0.5),
        fillcolor='rgba(231, 76, 60, 0.5)',
        hovertemplate="<b>%{x|%d.%m.%Y %H:%M}</b><br>Laden: %{y:,.2f} MW<extra></extra>"
    ))
    
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeit",
        yaxis_title="Leistung [MW]",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    
    return fig


