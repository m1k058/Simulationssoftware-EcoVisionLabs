"""
Streamlit-optimierte Plotly-Funktionen für hochauflösende Zeitreihen.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ecovision.config.constants import ENERGY_SOURCES


# --- HILFSFUNKTIONEN ---

def _filter_time(df: pd.DataFrame, date_from: pd.Timestamp | None, date_to: pd.Timestamp | None) -> pd.DataFrame:
    """Zentrale Hilfsfunktion zum Filtern der Zeitreihen."""
    if "Zeitpunkt" not in df.columns:
        raise KeyError("Spalte 'Zeitpunkt' fehlt im DataFrame")
    
    df = df.copy()
    df['Zeitpunkt'] = pd.to_datetime(df['Zeitpunkt'])
    if date_from:
        df = df[df['Zeitpunkt'] >= date_from]
    if date_to:
        df = df[df['Zeitpunkt'] <= date_to]
    return df

def _apply_default_layout(fig: go.Figure, df: pd.DataFrame, yaxis_title: str, title: str = "") -> None:
    """Zentrale Layout-Konfiguration für alle Zeitreihen-Plots."""
    fig.update_layout(
        title=title if title else None,
        xaxis_title="Zeitpunkt",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(range=[df["Zeitpunkt"].min(), df["Zeitpunkt"].max()])
    )


# --- PLOT FUNKTIONEN ---

def create_generation_plot(
    df: pd.DataFrame, energy_keys: list[str] | None = None,
    title: str = "", date_from: pd.Timestamp | None = None, date_to: pd.Timestamp | None = None
) -> go.Figure:
    df = _filter_time(df, date_from, date_to)
    energy_keys = energy_keys or list(ENERGY_SOURCES.keys())
    
    plot_data = [
        {"colname": source.get("colname"), "label": source.get("name", k), "color": source.get("color", "#ccc")}
        for k, source in ENERGY_SOURCES.items() if k in energy_keys and source.get("colname") in df.columns
    ]
    
    if not plot_data:
        raise ValueError("Keine passenden Energiespalten im DataFrame gefunden")
    
    colnames = [item["colname"] for item in plot_data]
    df_long = pd.melt(df, id_vars=["Zeitpunkt"], value_vars=colnames, var_name="Spalte", value_name="Wert")
    df_long["Quelle"] = df_long["Spalte"].map({item["colname"]: item["label"] for item in plot_data})
    
    fig = px.area(
        df_long, x="Zeitpunkt", y="Wert", color="Quelle",
        color_discrete_map={item["label"]: item["color"] for item in plot_data}
    )
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>")
    
    # Gesamterzeugung als unsichtbare Trace
    fig.add_trace(go.Scatter(
        x=df["Zeitpunkt"], y=df[colnames].sum(axis=1), mode="lines", name="Gesamterzeugung",
        line=dict(color="rgba(0,0,0,0)", width=0), hovertemplate="<b>Gesamterzeugung</b>: %{y:,.2f}<extra></extra>"
    ))
    
    _apply_default_layout(fig, df, "Erzeugung [MWh]", title)
    return fig


def create_consumption_plot(
    df: pd.DataFrame, sector_columns: list[str], total_column: str = "Gesamt [MWh]",
    title: str = "", date_from: pd.Timestamp | None = None, date_to: pd.Timestamp | None = None
) -> go.Figure:
    df = _filter_time(df, date_from, date_to)
    if not sector_columns:
        raise ValueError("Keine Sektorspalten angegeben.")
    
    sector_colors = {
        "Haushalte [MWh]": "#FF6B6B", "Gewerbe [MWh]": "#1076C0",
        "Landwirtschaft [MWh]": "#FFBF1C", "E-Mobility [MWh]": "#439629", "Wärmepumpen [MWh]": "#9A12F5"
    }
    
    df_long = pd.melt(df, id_vars=["Zeitpunkt"], value_vars=sector_columns, var_name="Sektor", value_name="Wert")
    fig = px.area(df_long, x="Zeitpunkt", y="Wert", color="Sektor", color_discrete_map=sector_colors)
    fig.update_traces(hovertemplate="<b>%{fullData.name}</b>: %{y:,.2f}<extra></extra>")
    
    gesamtverbrauch = df[total_column] if total_column in df.columns else df[sector_columns].sum(axis=1)
    fig.add_trace(go.Scatter(
        x=df["Zeitpunkt"], y=gesamtverbrauch, mode="lines", name="Gesamtverbrauch",
        line=dict(color="rgba(0,0,0,0)", width=0), hovertemplate="<b>Gesamtverbrauch</b>: %{y:,.2f}<extra></extra>"
    ))
    
    _apply_default_layout(fig, df, "Verbrauch [MWh]", title)
    return fig


def create_balance_area_plot(
    df: pd.DataFrame, balance_column: str = "Bilanz [MWh]",
    title: str = "", date_from: pd.Timestamp | None = None, date_to: pd.Timestamp | None = None
) -> go.Figure:
    df = _filter_time(df, date_from, date_to)
    if balance_column not in df.columns: raise KeyError(f"Spalte '{balance_column}' fehlt.")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Zeitpunkt"], y=df[balance_column].clip(upper=0),
        fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.5)", line=dict(color="rgb(239, 68, 68)", width=1),
        name="Defizit (Verbrauch > Erzeugung)", hovertemplate="<b>Defizit</b>: %{y:,.2f} MWh<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df["Zeitpunkt"], y=df[balance_column].clip(lower=0),
        fill="tozeroy", fillcolor="rgba(34, 197, 94, 0.5)", line=dict(color="rgb(34, 197, 94)", width=1),
        name="Überschuss (Erzeugung > Verbrauch)", hovertemplate="<b>Überschuss</b>: %{y:,.2f} MWh<extra></extra>"
    ))
    
    _apply_default_layout(fig, df, "Bilanz [MWh]", title)
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color="gray")
    return fig


def create_duration_curve_plot(
    df: pd.DataFrame, balance_column: str = "Bilanz [MWh]", rest_balance_column: str = "Rest Bilanz [MWh]", title: str = ""
) -> go.Figure:
    if balance_column not in df.columns: raise KeyError(f"Spalte '{balance_column}' fehlt")
    
    hours = df.index * 0.25
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=hours, y=df[balance_column].sort_values(ascending=False).reset_index(drop=True),
        mode="lines", name="Ohne Speicher", line=dict(color="rgb(59, 130, 246)", width=2),
        hovertemplate="<b>Ohne Speicher</b><br>Stunde: %{x:.1f}<br>Leistung: %{y:,.2f} MWh<extra></extra>"
    ))
    
    if rest_balance_column in df.columns:
        fig.add_trace(go.Scatter(
            x=hours, y=df[rest_balance_column].sort_values(ascending=False).reset_index(drop=True),
            mode="lines", name="Mit Speicher", line=dict(color="rgb(16, 185, 129)", width=2),
            hovertemplate="<b>Mit Speicher</b><br>Stunde: %{x:.1f}<br>Leistung: %{y:,.2f} MWh<extra></extra>"
        ))
    
    fig.update_layout(
        title=title if title else None, template="plotly_white", hovermode="x unified",
        xaxis_title="Stunden des Jahres", yaxis_title="Residuallast [MWh]",
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.add_hline(y=0, line_width=1.5, line_dash="dash", line_color="gray")
    return fig


def create_monthly_balance_plot(
    df: pd.DataFrame, balance_column: str = "Rest Bilanz [MWh]",
    title: str = "", date_from: pd.Timestamp | None = None, date_to: pd.Timestamp | None = None
) -> go.Figure:
    df = _filter_time(df, date_from, date_to)
    
    df['Monat_Name'] = df['Zeitpunkt'].dt.strftime('%B %Y')
    
    monthly_data = df.groupby(['Monat_Name'], sort=False).agg({
        balance_column: [('Überschuss', lambda x: x[x > 0].sum()), ('Defizit', lambda x: x[x < 0].abs().sum())]
    }).reset_index()
    monthly_data.columns = ['Label', 'Überschuss', 'Defizit']
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_data['Label'], y=monthly_data['Überschuss'], name='Überschuss',
        marker_color='rgba(34, 197, 94, 0.8)',
        hovertemplate="<b>%{x}</b><br>Überschuss: %{y:,.0f} MWh<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=monthly_data['Label'], y=monthly_data['Defizit'], name='Defizit',
        marker_color='rgba(239, 68, 68, 0.8)',
        hovertemplate="<b>%{x}</b><br>Defizit: %{y:,.0f} MWh<extra></extra>"
    ))
    
    fig.update_layout(
        title=title if title else None, barmode='group', template="plotly_white", hovermode="x unified",
        xaxis_title="Monat", yaxis_title="Monatliche Bilanz [MWh]", xaxis=dict(tickangle=-45),
        margin=dict(l=40, r=40, t=40, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig