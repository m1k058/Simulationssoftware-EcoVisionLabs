"""
Plotting funktionen für KPI-Visualisierung.
"""

import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Optional


# ------------------------------ #
#         KONFIGURATION          #
# ------------------------------ #

# Gewichtung Gesamtscore: Safety 40 %, Ecology 30 %, Economy 30 %
# Gewichtung innerhalb Safety: gleichgewichtet (je 1/3)
# Gewichtung innerhalb Ecology: CO2 60 %, Renewable 25 %, Curtailment 15 %
# Gewichtung innerhalb Economy: LCOE 40 %, Curtailment 35 %, Storage 25 %

KPI_CONFIG = {
    'safety': {
        'title': '🛡️ Safety',
        'color': '#FF6B6B',
        'category_weight': 0.40,  # Anteil am Gesamtscore
        'kpis': {
            'adequacy_score': {
                'name': 'Adequacy Score',
                'description': 'Autarker Stundenanteil: 1 − (Defizit-Stunden / Jahresstunden) – Anteil der Stunden ohne Import-/Reservebedarf',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 1/3,  # Intra-Kategorie-Gewicht
            },
            'robustness_score': {
                'name': 'Robustness Score',
                'description': 'Gesicherte Leistung / Spitzenlast (0.75 @ 100 %, 1.0 @ ≥110 %)',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 1/3,
            },
            'dependency_score': {
                'name': 'Dependency Score',
                'description': '1 − (Nicht gedeckte Energie / Gesamtverbrauch)',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 1/3,
            }
        }
    },
    'ecology': {
        'title': '🌱 Ecology',
        'color': '#4ECDC4',
        'category_weight': 0.30,
        'kpis': {
            'co2_score': {
                'name': 'CO2 Score',
                'description': '1 − min(1, CO2-Intensität / 400 g/kWh)',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.60,
            },
            'renewable_share': {
                'name': 'Renewable Share',
                'description': 'Fossil-Free Degree: (Gesamt − Fossil) / Gesamt',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.25,
            },
            'curtailment_score': {
                'name': 'Curtailment Score',
                'description': '1 − (Abregelungsquote / 40 %)',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.15,
            }
        }
    },
    'economy': {
        'title': '💰 Economy',
        'color': '#95E1D3',
        'category_weight': 0.30,
        'kpis': {
            'lcoe_index': {
                'name': 'LCOE Index',
                'description': '1 − (LCOE − 8 ct/kWh) / (40 − 8), Ziel 0.08–0.40 €/kWh',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.40,
            },
            'curtailment_econ_score': {
                'name': 'Curtailment Econ Score',
                'description': '1 − (Abregelungsanteil / 35 %), wirtschaftlicher Verlust durch verschwendete EE-Erzeugung',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.35,
            },
            'storage_efficiency': {
                'name': 'Storage Efficiency',
                'description': 'Nützlicher Speicherdurchsatz / Speicherbedarf',
                'unit': '',
                'format': '.3f',
                'worst': 0,
                'best': 1,
                'weight': 0.25,
            }
        }
    }
}


# ------------------------------ #
#        HILFSFUNKTIONEN         #
# ------------------------------ #

def _calculate_kpi_score(value: float, worst: float, best: float) -> float:
    """
        Score zwischen 0 und 100 basierend auf Wert, schlechtestem und bestem Wert berechnen.
    
        Examples:
        - co2_intensity: Wert=173, worst=1000, best=0 → score≈83
        - deficit_share: Wert=0.1, worst=1, best=0 → score=90
    """

    # division durch null verhindern
    if worst == best:
        return 100 if value == best else 0
    
    # Min-Max Normalisierung  +  invertieren
    normalized = (value - best) / (worst - best)
    score = (1 - normalized) * 100
    
    return max(0, min(100, score))


def _get_score_color(score: float) -> str:
    """
    Farbe basierend auf Score-Wert erhalten.
    
    Args:
        score: Score-Wert (0-100)
    
    Returns:
        Hex-Farbcode
    """
    if score >= 80:
        return '#4CAF50'
    elif score >= 60:
        return '#FFC107'
    elif score >= 40:
        return '#FF9800'
    else:
        return '#F44336'


def _format_kpi_value(value: float, kpi_config: Dict[str, Any]) -> str:
    """
    KPI-Wert gemäß seiner Konfiguration formatieren.
    
    Args:
        value: KPI-Wert
        kpi_config: KPI-Konfigurations-Dict
    
    Returns:
        Formatierter String
    """
    value_format = kpi_config.get('format', '.2f')
    unit = kpi_config.get('unit', '')
    
    if value_format == '.2%':
        return f'{value * 100:.2f}%'
    elif value_format == '.4f':
        return f'{value:.4f} {unit}'.strip()
    else:
        return f'{value:.2f} {unit}'.strip()


# ------------------------------- #
#       PLOTTING FUNKTIONEN       #
# ------------------------------- #

def create_gauge_chart(
    value: float,
    title: str,
    worst: float,
    best: float,
    height: int = 250
) -> go.Figure:
    """
    Erstelle ein Gauge-Diagramm für eine einzelne KPI.
    
    Args:
        value: Aktueller KPI-Wert
        title: Diagrammtitel
        worst: Schlechtestmöglicher Wert
        best: Bestmöglicher Wert
        height: Diagrammhöhe in Pixeln
    
    Returns:
        Plotly Figure objekt
    """
    score = _calculate_kpi_score(value, worst, best)
    color = _get_score_color(score)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': title, 'font': {'size': 16}},
        number={'suffix': ' pts', 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': 'gray',
            'steps': [
                {'range': [0, 40], 'color': '#FFEBEE'},
                {'range': [40, 60], 'color': '#FFF3E0'},
                {'range': [60, 80], 'color': '#FFF9C4'},
                {'range': [80, 100], 'color': '#E8F5E9'}
            ]
        }
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#333', 'family': 'Arial'}
    )
    
    return fig


def create_category_radar_chart(
    kpis: Dict[str, Dict[str, float]],
    height: int = 400
) -> go.Figure:
    """
    Erstelle ein Radar-Diagramm, das alle drei Kategorien vergleicht.
    
    Args:
        kpis: Dictionary mit KPI-Ergebnissen von get_score_and_kpis()
        height: Diagrammhöhe in Pixeln
    
    Returns:
        Plotly Figure objekt
    """
    categories = []
    scores = []
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            # durchschnittlichen Score für Kategorie berechnen
            category_scores = []
            for kpi_name, kpi_value in kpis[category].items():
                kpi_config = config['kpis'].get(kpi_name, {})
                worst = kpi_config.get('worst', 1)
                best = kpi_config.get('best', 0)
                
                score = _calculate_kpi_score(kpi_value, worst, best)
                category_scores.append(score)
            
            categories.append(config['title'])
            avg_score = sum(category_scores) / len(category_scores) if category_scores else 0
            scores.append(avg_score)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        fillcolor='rgba(78, 205, 196, 0.3)',
        line=dict(color='rgba(78, 205, 196, 1)', width=3),
        name='Performance'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=12),
                gridcolor='lightgray'
            ),
            angularaxis=dict(
                tickfont=dict(size=14, color='#333')
            )
        ),
        showlegend=False,
        height=height,
        margin=dict(l=80, r=80, t=80, b=80),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#333', 'family': 'Arial'}
    )
    
    return fig


def create_kpi_bar_chart(
    kpis: Dict[str, float],
    category_config: Dict[str, Any],
    horizontal: bool = True,
    height: Optional[int] = None
) -> go.Figure:
    """
    Bar diagramm für KPI-Werte in einer Kategorie erstellen.
    
    Args:
        kpis: Dictionary mit KPI-Werten
        category_config: Konfiguration für die Kategorie
        horizontal: Wenn True, erstelle horizontale Balken
        height: Diagrammhöhe in Pixeln (automatisch berechnet, wenn None)
    
    Returns:
        Plotly Figure objekt
    """
    kpi_names = []
    kpi_values = []
    kpi_colors = []
    
    for kpi_name, kpi_value in kpis.items():
        kpi_config = category_config['kpis'].get(kpi_name, {})
        kpi_names.append(kpi_config.get('name', kpi_name))
        
        display_value = kpi_value * 100 if kpi_config.get('unit') == '%' else kpi_value
        kpi_values.append(display_value)
        
        worst = kpi_config.get('worst', 1)
        best = kpi_config.get('best', 0)
        score = _calculate_kpi_score(kpi_value, worst, best)
        kpi_colors.append(_get_score_color(score))
    
    if height is None:
        height = max(200, len(kpi_names) * 60) if horizontal else 400
    
    if horizontal:
        fig = go.Figure(go.Bar(
            x=kpi_values,
            y=kpi_names,
            orientation='h',
            marker=dict(color=kpi_colors),
            text=[f'{v:.2f}' for v in kpi_values],
            textposition='outside'
        ))
    else:
        fig = go.Figure(go.Bar(
            x=kpi_names,
            y=kpi_values,
            orientation='v',
            marker=dict(color=kpi_colors),
            text=[f'{v:.2f}' for v in kpi_values],
            textposition='outside'
        ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Value' if horizontal else '', gridcolor='lightgray'),
        yaxis=dict(title='' if horizontal else 'Value', gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'}
    )
    
    return fig


def create_category_score_bars(
    kpis: Dict[str, Dict[str, float]],
    height: int = 300
) -> go.Figure:
    """
    Balkendiagramm mit durchschnittlichen Scores für jede Kategorie erstellen.
    
    Args:
        kpis: Dictionary mit KPI-Ergebnissen von get_score_and_kpis()
        height: Diagrammhöhe in Pixeln
    
    Returns:
        Plotly Figure objekt
    """
    categories = []
    scores = []
    colors = []
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            category_scores = []
            for kpi_name, kpi_value in kpis[category].items():
                kpi_config = config['kpis'].get(kpi_name, {})
                worst = kpi_config.get('worst', 1)
                best = kpi_config.get('best', 0)
                
                score = _calculate_kpi_score(kpi_value, worst, best)
                category_scores.append(score)
            
            avg_score = sum(category_scores) / len(category_scores) if category_scores else 0
            
            categories.append(config['title'])
            scores.append(avg_score)
            colors.append(_get_score_color(avg_score))
    
    fig = go.Figure(go.Bar(
        x=categories,
        y=scores,
        marker=dict(color=colors),
        text=[f'{s:.1f} pts' for s in scores],
        textposition='outside'
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='', tickfont=dict(size=14)),
        yaxis=dict(title='Score', range=[0, 110], gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'},
        showlegend=False
    )
    
    return fig


def create_kpi_comparison_chart(
    kpis_list: list[Dict[str, Dict[str, float]]],
    labels: list[str],
    category: str = 'safety',
        show_title: bool = False,
    height: int = 400
) -> go.Figure:
    """
    Vergleichsdiagramm für mehrere Simulationsläufe erstellen.
    
    Args:
        kpis_list: Liste von KPI-Dictionaries zum Vergleichen
        labels: Bezeichnungen für jeden Simulationslauf
        category: Kategorie zum Vergleichen ('safety', 'ecology', 'economy')
        height: Diagrammhöhe in Pixeln
    
    Returns:
        Plotly Figure objekt
    """
    if category not in KPI_CONFIG:
        raise ValueError(f"Invalid category: {category}")
    
    category_config = KPI_CONFIG[category]
    kpi_names = list(category_config['kpis'].keys())
    
    fig = go.Figure()
    
    for idx, (kpis, label) in enumerate(zip(kpis_list, labels)):
        if category not in kpis:
            continue
        
        values = [kpis[category].get(kpi, 0) for kpi in kpi_names]
        display_names = [category_config['kpis'][kpi]['name'] for kpi in kpi_names]
        
        fig.add_trace(go.Bar(
            name=label,
            x=display_names,
            y=values,
            text=[f'{v:.2f}' for v in values],
            textposition='outside'
        ))
    
    fig.update_layout(
        height=height,
        barmode='group',
        title=f'{category_config["title"]} Comparison' if show_title else '',
        margin=dict(l=100, r=20, t=10, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='', tickangle=-45),
        yaxis=dict(title='Value', gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'},
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.05,
            xanchor='right',
            x=1
        )
    )
    
    return fig


def create_kpi_table(kpis: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Detaillierte Tabelle aller KPIs erstellen.
    
    Args:
        kpis: Dictionary mit KPI-Ergebnissen von get_score_and_kpis()
    
    Returns:
        Pandas DataFrame mit formatierten KPI-Daten
    """
    rows = []
    
    for category, category_kpis in kpis.items():
        if category == 'raw_values':
            continue
        if not isinstance(category_kpis, dict):
            continue
        
        category_config = KPI_CONFIG.get(category, {})
        cat_weight = category_config.get('category_weight', 0.0)
        
        for kpi_name, kpi_value in category_kpis.items():
            kpi_config = category_config.get('kpis', {}).get(kpi_name, {})
            
            worst = kpi_config.get('worst', 1)
            best = kpi_config.get('best', 0)
            score = _calculate_kpi_score(kpi_value, worst, best)
            
            formatted_value = _format_kpi_value(kpi_value, kpi_config)
            
            kpi_weight = kpi_config.get('weight', 0.0)
            overall_contribution = cat_weight * kpi_weight * 100  # in %
            weight_str = f"{kpi_weight * 100:.0f} % (∑ {overall_contribution:.1f} % Gesamt)"
            
            rows.append({
                'Kategorie': category_config.get('title', category),
                'KPI': kpi_config.get('name', kpi_name),
                'Wert': formatted_value,
                'Score (0–100)': f'{score:.1f}',
                'Gewichtung': weight_str,
                'Bewertung': '⭐' * (int(score / 20)),
                'Beschreibung': kpi_config.get('description', '')
            })
    
    return pd.DataFrame(rows)


def get_category_scores(kpis: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Durchschnittliche Scores für jede Kategorie berechnen.
    
    Args:
        kpis: Dictionary mit KPI-Ergebnissen von get_score_and_kpis()
    
    Returns:
        Dictionary mit durchschnittlichen Scores pro Kategorie
    """
    category_scores = {}
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            scores = []
            for kpi_name, kpi_value in kpis[category].items():
                kpi_config = config['kpis'].get(kpi_name, {})
                worst = kpi_config.get('worst', 1)
                best = kpi_config.get('best', 0)
                score = _calculate_kpi_score(kpi_value, worst, best)
                scores.append(score)
            
            category_scores[category] = sum(scores) / len(scores) if scores else 0
    
    return category_scores