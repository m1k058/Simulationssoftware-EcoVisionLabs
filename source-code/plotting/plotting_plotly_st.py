"""
Streamlit-optimierte Plotly-Funktionen 
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from constants import ENERGY_SOURCES
from data_processing import gen


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


def plot_economic_trends(results_list: list[dict]) -> go.Figure:
    """
    Erstellt einen Kombi-Plot (Bar & Line) für die wirtschaftliche Entwicklung.

    Args:
        results_list: Liste von Dictionaries mit den Ergebnissen pro Jahr.

    Returns:
        Plotly Figure mit Primär-Bars (Investitionen) und Sekundär-Linie (LCOE).
    """
    if not results_list:
        return go.Figure()

    df = pd.DataFrame(results_list)

    # Sanity: notwendige Spalten sicherstellen
    required = ["year", "total_investment_bn", "system_lco_e"]
    for col in required:
        if col not in df.columns:
            raise KeyError(f"Spalte '{col}' fehlt für den Economic-Trend-Plot.")

    # Sortierung und Typ-Korrektur
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df = df.sort_values("year")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Primärachse: Investitionen als Balken
    fig.add_trace(
        go.Bar(
            x=df["year"],
            y=df["total_investment_bn"],
            name="Investitionsbedarf (Mrd. €)",
            marker_color="#1f4b99",  # Modernes Dunkelblau
            opacity=0.9,
            hovertemplate="Jahr %{x}<br>Investitionen: %{y:,.2f} Mrd. €<extra></extra>",
        ),
        secondary_y=False,
    )

    # Sekundärachse: LCOE als Linie
    fig.add_trace(
        go.Scatter(
            x=df["year"],
            y=df["system_lco_e"],
            mode="lines+markers",
            name="LCOE (ct/kWh)",
            line=dict(color="#e4572e", width=3),  # Auffälliges Rot/Orange
            marker=dict(size=8, color="#e4572e", line=dict(color="white", width=1)),
            hovertemplate="Jahr %{x}<br>LCOE: %{y:,.2f} ct/kWh<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        template="plotly_white",
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=60, t=60, b=60),
        height=500,
        xaxis_title="Jahr",
        yaxis_title="Investitionen (Mrd. €)",
        yaxis2_title="LCOE (ct/kWh)",
        hovermode="x unified",
        bargap=0.15,
    )

    # Grid nur auf primärer Achse
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)", secondary_y=False)
    fig.update_yaxes(showgrid=False, secondary_y=True)

    return fig
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

