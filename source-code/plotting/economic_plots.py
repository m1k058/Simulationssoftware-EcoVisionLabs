"""
Wirtschaftliche Visualisierungen für das Consulting-Dashboard
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any


def plot_cost_structure(results_list: List[Dict[str, Any]]) -> go.Figure:
    """
    Erstellt ein Stacked Bar Chart für die Kostenaufschlüsselung über die Jahre.
    
    Args:
        results_list: Liste von Dictionaries mit Ergebnissen pro Jahr.
                     Erforderliche Keys: 'year', 'total_annual_cost_bn'
                     Optional: 'capex_annual_bn', 'opex_fix_bn', 'opex_var_bn'
    
    Returns:
        Plotly Figure mit gestapeltem Balkendiagramm.
    """
    if not results_list:
        return go.Figure()
    
    df = pd.DataFrame(results_list)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df = df.sort_values("year")
    
    # Wenn detaillierte Kostenaufteilung nicht vorhanden, nutze Dummy-Aufteilung
    # Annahme: 40% CAPEX, 25% Fixed OpEx, 35% Variable Kosten (durchschnittliche Anteile)
    if "capex_annual_bn" not in df.columns:
        df["capex_annual_bn"] = df["total_annual_cost_bn"] * 0.40
    if "opex_fix_bn" not in df.columns:
        df["opex_fix_bn"] = df["total_annual_cost_bn"] * 0.25
    if "opex_var_bn" not in df.columns:
        df["opex_var_bn"] = df["total_annual_cost_bn"] * 0.35
    
    fig = go.Figure()
    
    # Farben für die Kostenkomponenten
    colors = {
        "Kapitalkosten (CAPEX)": "#1f4b99",      # Dunkelblau
        "Fixe Betriebskosten": "#7fa6d1",        # Hellblau
        "Variable Kosten (Brennstoff/CO2)": "#e4572e"  # Orange/Rot
    }
    
    # Stacks hinzufügen
    fig.add_trace(go.Bar(
        x=df["year"],
        y=df["capex_annual_bn"],
        name="Kapitalkosten (CAPEX)",
        marker_color=colors["Kapitalkosten (CAPEX)"],
        hovertemplate="Jahr %{x}<br>CAPEX: %{y:,.3f} Mrd. €<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        x=df["year"],
        y=df["opex_fix_bn"],
        name="Fixe Betriebskosten",
        marker_color=colors["Fixe Betriebskosten"],
        hovertemplate="Jahr %{x}<br>Fixed OpEx: %{y:,.3f} Mrd. €<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        x=df["year"],
        y=df["opex_var_bn"],
        name="Variable Kosten (Brennstoff/CO2)",
        marker_color=colors["Variable Kosten (Brennstoff/CO2)"],
        hovertemplate="Jahr %{x}<br>Variable OpEx: %{y:,.3f} Mrd. €<extra></extra>",
    ))
    
    fig.update_layout(
        barmode="stack",
        template="plotly_white",
        xaxis_title="Jahr",
        yaxis_title="Kosten (Mrd. €/Jahr)",
        title="Kostenaufschlüsselung nach Komponenten",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(l=60, r=60, t=60, b=80),
        height=500,
        hovermode="x unified",
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)")
    
    return fig


def plot_investment_donut(investment_dict: Dict[str, float], year: int) -> go.Figure:
    """
    Erstellt ein Donut Chart für die Investitionsverteilung nach Technologie.
    
    Args:
        investment_dict: Dictionary der Form {'Photovoltaik': 50.0, 'Wind_Onshore': 120.0, ...}
                        Werte in Mrd. €
        year: Das Simulationsjahr (für Titel).
    
    Returns:
        Plotly Donut Figure.
    """
    if not investment_dict:
        return go.Figure()
    
    # Filtere Null- und Negativwerte
    filtered = {k: v for k, v in investment_dict.items() if v > 0}
    
    if not filtered:
        return go.Figure()
    
    # Mapping: Tech-IDs zu Labels
    label_map = {
        'Photovoltaik': 'Photovoltaik',
        'Wind_Onshore': 'Wind Onshore',
        'Wind_Offshore': 'Wind Offshore',
        'Biomasse': 'Biomasse',
        'Wasserkraft': 'Wasserkraft',
        'Erdgas': 'Erdgas',
        'Steinkohle': 'Steinkohle',
        'Braunkohle': 'Braunkohle',
        'Kernenergie': 'Kernenergie'
    }
    
    # Farben für Technologien (Konsistenz mit anderen Charts)
    tech_colors = {
        'Photovoltaik': '#FFD700',           # Gold
        'Wind_Onshore': '#007F78',           # Dunkelgrün
        'Wind_Offshore': '#00BFFF',          # Hellblau
        'Biomasse': '#00A51B',               # Dunkelgrün
        'Wasserkraft': '#1E90FF',            # Blau
        'Erdgas': '#5D5D5D',                 # Grau
        'Steinkohle': '#1F1F1F',             # Dunkelgrau
        'Braunkohle': '#774400',             # Braun
        'Kernenergie': '#800080'             # Lila
    }
    
    labels = [label_map.get(k, k) for k in filtered.keys()]
    values = list(filtered.values())
    colors = [tech_colors.get(k, '#cccccc') for k in filtered.keys()]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,  # Donut-Loch
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textposition="inside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Investition: %{value:,.2f} Mrd. €<br>Anteil: %{percent}<extra></extra>",
    )])
    
    fig.update_layout(
        title=f"Investitions-Mix {year}",
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(size=11)
        ),
        margin=dict(l=60, r=150, t=60, b=60),
        height=500,
    )
    
    return fig
