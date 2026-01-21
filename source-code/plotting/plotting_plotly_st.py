"""
Streamlit-optimierte Plotly-Funktionen 
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from constants import ENERGY_SOURCES


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
    
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    # Unsichtbarer Trace für Gesamtsumme
    df['_Gesamterzeugung'] = df[colnames].sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["_Gesamterzeugung"],
            mode="lines",
            name="Gesamterzeugung",
            line=dict(color="rgba(0,0,0,0)", width=0),
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
    
    
    if not sector_columns:
        raise ValueError("Keine Sektorspalten im DataFrame gefunden")
    
    # Farben für Sektoren
    sector_colors = {
        "Haushalte [MWh]": "#FF6B6B",
        "Gewerbe [MWh]": "#1076C0",
        "Landwirtschaft [MWh]": "#FFBF1C",
        "E-Mobility [MWh]": "#439629",
        "Wärmepumpen [MWh]": "#9A12F5",
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
    
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )
    
    # Gesamtverbrauch
    if total_column in df.columns:
        gesamtverbrauch = df[total_column]
    else:
        gesamtverbrauch = df[sector_columns].sum(axis=1)
    
    # Unsichtbare Trace für Gesamtverbrauch
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=gesamtverbrauch,
            mode="lines",
            name="Gesamtverbrauch",
            line=dict(color="rgba(0,0,0,0)", width=0),
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
    
    # Negative (Defizit) in Rot
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["Defizit"],
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.5)",
            line=dict(color="rgb(239, 68, 68)", width=1),
            mode="lines",
            name="Defizit (Verbrauch > Erzeugung)",
            hovertemplate="<b>Defizit</b>: %{y:,.2f} MWh<extra></extra>"
        )
    )
    
    # Positive (Überschuss) in Grün
    fig.add_trace(
        go.Scatter(
            x=df["Zeitpunkt"],
            y=df["Überschuss"],
            fill="tozeroy",
            fillcolor="rgba(34, 197, 94, 0.5)",
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
    
    # Nulllinie stark
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
    
    # Energiequellen die angezeigt werden
    if energy_keys is None:
        energy_keys = list(ENERGY_SOURCES.keys())
    
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
    
    fig.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>"
    )

    # Linie für Gesamtlast
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
    
    # Sortiere Bilanz absteigend
    balance_sorted = df[balance_column].sort_values(ascending=False).reset_index(drop=True)
    
    # Erstelle Stunden-Achse
    hours = balance_sorted.index * 0.25
    fig = go.Figure()
    
    # Ohne Speicher
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=balance_sorted,
            mode="lines",
            name="Ohne Speicher",
            line=dict(color="rgb(59, 130, 246)", width=2),
            hovertemplate="<b>Ohne Speicher</b><br>Stunde: %{x:.1f}<br>Leistung: %{y:,.2f} MWh<extra></extra>"
        )
    )
    
    # Mit Speicher
    if rest_balance_column in df.columns:
        rest_balance_sorted = df[rest_balance_column].sort_values(ascending=False).reset_index(drop=True)
        
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=rest_balance_sorted,
                mode="lines",
                name="Mit Speicher",
                line=dict(color="rgb(16, 185, 129)", width=2),
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
    
    # Nulllinie stark
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
    
    if soc_columns is None:
        soc_columns = [col for col in df.columns if "SOC MWh" in col]
    
    if not soc_columns:
        raise ValueError("Keine SOC-Spalten im DataFrame gefunden")
    
    storage_colors = {
        "Batteriespeicher SOC MWh": "#f59e0b",
        "Pumpspeicher SOC MWh": "#3b82f6",
        "Wasserstoffspeicher SOC MWh": "#8b5cf6"
    }
   
    label_map = {}
    for col in soc_columns:
        label = col.replace(" SOC MWh", "")
        label_map[col] = label
    
    df_long = pd.melt(
        df[["Zeitpunkt"] + soc_columns],
        id_vars=["Zeitpunkt"],
        value_vars=soc_columns,
        var_name="Speicher",
        value_name="SOC"
    )
    df_long["Speicher_Label"] = df_long["Speicher"].map(label_map)
    
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
    
    # Überschüsse und Defizite sortieren
    df['Überschuss'] = df[balance_column].clip(lower=0)
    df['Defizit'] = df[balance_column].clip(upper=0).abs()
    
    # aufsummieren
    monthly_data = df.groupby(['Jahr', 'Monat', 'Monat_Name']).agg({
        'Überschuss': 'sum',
        'Defizit': 'sum'
    }).reset_index()
    
    monthly_data['Label'] = monthly_data['Monat_Name'] + ' ' + monthly_data['Jahr'].astype(str)
    
    fig = go.Figure()
    
    # Überschüs
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
    
    # Defizit
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
    
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    
    # Zeitfilter anwenden
    if date_from is not None:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to is not None:
        df = df[df['Zeitpunkt'] <= date_to]
    
    power_data = df[power_column]
    
    fig = go.Figure()
    
    # Positive Werte
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
    
    # Negative Werte
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


