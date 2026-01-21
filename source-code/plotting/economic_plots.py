"""
Wirtschaftliche Visualisierungen für das Wirtschafts-Dashboard
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
    
    # hardcoded defaulkt wenn fehkt
    # 40% capex, 25% Fixed opex, 35% Variable Kosten
    if "capex_annual_bn" not in df.columns:
        df["capex_annual_bn"] = df["total_annual_cost_bn"] * 0.40
    if "opex_fix_bn" not in df.columns:
        df["opex_fix_bn"] = df["total_annual_cost_bn"] * 0.25
    if "opex_var_bn" not in df.columns:
        df["opex_var_bn"] = df["total_annual_cost_bn"] * 0.35
    
    fig = go.Figure()
    
    # Farben für die Kostenkomponenten
    colors = {
        "Kapitalkosten (CAPEX)": "#1f4b99",
        "Fixe Betriebskosten": "#7fa6d1",
        "Variable Kosten (Brennstoff/CO2)": "#e4572e"
    }
    
    x_vals = df["year"].astype(int).astype(str)

    fig.add_trace(go.Bar(
        x=x_vals,
        y=df["capex_annual_bn"],
        name="Kapitalkosten (CAPEX)",
        marker_color=colors["Kapitalkosten (CAPEX)"],
        hovertemplate="Jahr %{x}<br>CAPEX: %{y:,.3f} Mrd. €<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        x=x_vals,
        y=df["opex_fix_bn"],
        name="Fixe Betriebskosten",
        marker_color=colors["Fixe Betriebskosten"],
        hovertemplate="Jahr %{x}<br>Fixed OpEx: %{y:,.3f} Mrd. €<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        x=x_vals,
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
        title="",
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

    fig.update_xaxes(type="category")
    
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
    
    filtered = {k: v for k, v in investment_dict.items() if v > 0}
    
    if not filtered:
        return go.Figure()
    
    # Mapping
    label_map = {
        'Photovoltaik': 'Photovoltaik',
        'Wind_Onshore': 'Wind Onshore',
        'Wind_Offshore': 'Wind Offshore',
        'Biomasse': 'Biomasse',
        'Wasserkraft': 'Wasserkraft',
        'Erdgas': 'Erdgas',
        'Steinkohle': 'Steinkohle',
        'Braunkohle': 'Braunkohle',
        'Kernenergie': 'Kernenergie',
        'Elektrolyseur': 'Elektrolyseur',
        'H2_Elektrifizierung': 'H₂-Elektrifizierung',
        'Batteriespeicher': 'Batteriespeicher',
        'Pumpspeicher': 'Pumpspeicher',
        'Wasserstoffspeicher': 'H₂-Speicher'
    }
    
    # Farben für Technologien fixed
    tech_colors = {
        'Photovoltaik': '#FFD700',       
        'Wind Onshore': '#007F78',         
        'Wind Offshore': '#00BFFF',         
        'Biomasse': '#00A51B',              
        'Wasserkraft': '#1E90FF',     
        'Erdgas': '#5D5D5D',           
        'Steinkohle': '#1F1F1F',           
        'Braunkohle': '#774400',         
        'Kernenergie': '#800080',     
        'Elektrolyseur': '#FF6B6B',  
        'H2_Elektrifizierung': '#FF8A65',  
        'Batteriespeicher': '#4CAF50',  
        'Pumpspeicher': '#2196F3',   
        'Wasserstoffspeicher': '#9C27B0'
    }
    
    labels = [label_map.get(k, k) for k in filtered.keys()]
    values = list(filtered.values())
    colors = [tech_colors.get(k, '#cccccc') for k in filtered.keys()]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textposition="inside",
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Investition: %{value:,.2f} Mrd. €<br>Anteil: %{percent}<extra></extra>",
    )])
    
    fig.update_layout(
        title="",
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

    required = ["year", "total_investment_bn", "system_lco_e"]
    for col in required:
        if col not in df.columns:
            raise KeyError(f"Spalte '{col}' fehlt für den Economic-Trend-Plot.")

    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df = df.sort_values("year")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df["year"],
            y=df["total_investment_bn"],
            name="Investitionsbedarf (Mrd. €)",
            marker_color="#1f4b99",
            opacity=0.9,
            hovertemplate="Jahr %{x}<br>Investitionen: %{y:,.2f} Mrd. €<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df["year"],
            y=df["system_lco_e"],
            mode="lines+markers",
            name="LCOE (ct/kWh)",
            line=dict(color="#e4572e", width=3),
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
        title="",
    )

    fig.update_xaxes(dtick=1)

    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.1)", secondary_y=False)
    fig.update_yaxes(showgrid=False, secondary_y=True)

    return fig


