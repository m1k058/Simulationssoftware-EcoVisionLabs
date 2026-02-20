"""
Plotting-Funktionen für KPI-Visualisierung.
Zentralisiertes Dashboard-Scoring (0-100 Punkte).
"""
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Optional

# ------------------------------ #
#         KONFIGURATION          #
# ------------------------------ #

KPI_CONFIG = {
    'security': {
        'title': '🛡️ Security',
        'color': '#FF6B6B',
        'kpis': {
            'energy_deficit_share': {'name': 'Unserved Energy Ratio', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0},
            'peak_deficit_ratio': {'name': 'Max Unserved Power Ratio', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0},
            'deficit_frequency': {'name': 'Deficit Hours Ratio', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0}
        }
    },
    'ecology': {
        'title': '🌱 Ecology',
        'color': '#4ECDC4',
        'kpis': {
            'co2_intensity': {'name': 'CO2 Intensity', 'unit': 'g/kWh', 'format': '.2f', 'worst': 1000, 'best': 0},
            'curtailment_share': {'name': 'Curtailment Ratio', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0},
            'fossil_share': {'name': 'Fossil Share', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0}
        }
    },
    'economy': {
        'title': '💰 Economy',
        'color': '#95E1D3',
        'kpis': {
            'system_cost_index': {'name': 'System Cost (LCOE)', 'unit': 'ct/kWh', 'format': '.2f', 'worst': 100, 'best': 0},
            'import_dependency': {'name': 'Import Dependency', 'unit': '%', 'format': '.2%', 'worst': 1, 'best': 0},
            'storage_utilization': {'name': 'Storage Utilization', 'unit': '%', 'format': '.2%', 'worst': 0, 'best': 1}
        }
    }
}


# ------------------------------ #
#        HILFSFUNKTIONEN         #
# ------------------------------ #

def _calculate_kpi_score(value: float, worst: float, best: float) -> float:
    """Berechnet einen normalisierten Score zwischen 0 und 100."""
    if worst == best:
        return 100 if value == best else 0
    normalized = (value - best) / (worst - best)
    score = (1 - normalized) * 100
    return max(0, min(100, score))


def _get_score_color(score: float) -> str:
    """Gibt Ampelfarben basierend auf dem Score zurück."""
    if score >= 80: return '#4CAF50'
    if score >= 60: return '#FFC107'
    if score >= 40: return '#FF9800'
    return '#F44336'


def _format_kpi_value(value: float, kpi_config: Dict[str, Any]) -> str:
    """Formatiert den KPI-Wert als String gemäß der Config."""
    value_format = kpi_config.get('format', '.2f')
    unit = kpi_config.get('unit', '')
    if value_format == '.2%':
        return f'{value * 100:.2f}%'
    return f'{value:{value_format}} {unit}'.strip()


# ------------------------------- #
#       PLOTTING FUNKTIONEN       #
# ------------------------------- #

def create_gauge_chart(value: float, title: str, worst: float, best: float, height: int = 250) -> go.Figure:
    """Erstellt ein Tachometer-Diagramm für einen einzelnen Score."""
    score = _calculate_kpi_score(value, worst, best)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        title={'text': title, 'font': {'size': 16}},
        number={'suffix': ' pts', 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': _get_score_color(score)},
            'bgcolor': 'white', 'borderwidth': 2, 'bordercolor': 'gray',
            'steps': [
                {'range': [0, 40], 'color': '#FFEBEE'},
                {'range': [40, 60], 'color': '#FFF3E0'},
                {'range': [60, 80], 'color': '#FFF9C4'},
                {'range': [80, 100], 'color': '#E8F5E9'}
            ]
        }
    ))
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def create_category_radar_chart(kpis: Dict[str, Dict[str, float]], height: int = 400) -> go.Figure:
    """Erstellt ein Radar-Diagramm zum Vergleich der drei Hauptkategorien."""
    categories, scores = [], []
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            cat_scores = [
                _calculate_kpi_score(val, config['kpis'].get(kpi, {}).get('worst', 1), config['kpis'].get(kpi, {}).get('best', 0))
                for kpi, val in kpis[category].items()
            ]
            categories.append(config['title'])
            scores.append(sum(cat_scores) / len(cat_scores) if cat_scores else 0)
    
    fig = go.Figure(go.Scatterpolar(
        r=scores + [scores[0]] if scores else [], # Linie schließen
        theta=categories + [categories[0]] if categories else [],
        fill='toself', fillcolor='rgba(78, 205, 196, 0.3)',
        line=dict(color='rgba(78, 205, 196, 1)', width=3)
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False, height=height, margin=dict(l=80, r=80, t=80, b=80)
    )
    return fig


def create_kpi_table(kpis: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """Gibt eine fertig aufbereitete Tabelle aller KPIs für Streamlit zurück."""
    rows = []
    for category, category_kpis in kpis.items():
        if category == 'raw_values': continue
        
        category_config = KPI_CONFIG.get(category, {})
        for kpi_name, kpi_value in category_kpis.items():
            kpi_config = category_config.get('kpis', {}).get(kpi_name, {})
            score = _calculate_kpi_score(kpi_value, kpi_config.get('worst', 1), kpi_config.get('best', 0))
            
            rows.append({
                'Kategorie': category_config.get('title', category),
                'KPI': kpi_config.get('name', kpi_name),
                'Wert': _format_kpi_value(kpi_value, kpi_config),
                'Score': f'{score:.1f}',
                'Rating': '⭐' * max(1, int(score / 20))
            })
    return pd.DataFrame(rows)


def create_kpi_bar_chart(
    kpis: Dict[str, float],
    category_config: Dict[str, Any],
    horizontal: bool = True,
    height: Optional[int] = None
) -> go.Figure:
    """Bar-Diagramm für KPI-Werte in einer Kategorie."""
    kpi_names, kpi_values, kpi_colors = [], [], []
    for kpi_name, kpi_value in kpis.items():
        kpi_cfg = category_config['kpis'].get(kpi_name, {})
        kpi_names.append(kpi_cfg.get('name', kpi_name))
        display_value = kpi_value * 100 if kpi_cfg.get('unit') == '%' else kpi_value
        kpi_values.append(display_value)
        score = _calculate_kpi_score(kpi_value, kpi_cfg.get('worst', 1), kpi_cfg.get('best', 0))
        kpi_colors.append(_get_score_color(score))
    if height is None:
        height = max(200, len(kpi_names) * 60) if horizontal else 400
    if horizontal:
        fig = go.Figure(go.Bar(
            x=kpi_values, y=kpi_names, orientation='h',
            marker=dict(color=kpi_colors),
            text=[f'{v:.2f}' for v in kpi_values], textposition='outside'
        ))
    else:
        fig = go.Figure(go.Bar(
            x=kpi_names, y=kpi_values, orientation='v',
            marker=dict(color=kpi_colors),
            text=[f'{v:.2f}' for v in kpi_values], textposition='outside'
        ))
    fig.update_layout(
        height=height, margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Value' if horizontal else '', gridcolor='lightgray'),
        yaxis=dict(title='' if horizontal else 'Value', gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'}
    )
    return fig


def create_kpi_comparison_chart(
    kpis_list: list,
    labels: list,
    category: str = 'security',
    show_title: bool = False,
    height: int = 400
) -> go.Figure:
    """Vergleichsdiagramm für mehrere Simulationsläufe."""
    if category not in KPI_CONFIG:
        raise ValueError(f"Invalid category: {category}")
    category_config = KPI_CONFIG[category]
    kpi_names = list(category_config['kpis'].keys())
    fig = go.Figure()
    for kpis, label in zip(kpis_list, labels):
        if category not in kpis:
            continue
        values = [kpis[category].get(kpi, 0) for kpi in kpi_names]
        display_names = [category_config['kpis'][kpi]['name'] for kpi in kpi_names]
        fig.add_trace(go.Bar(
            name=label, x=display_names, y=values,
            text=[f'{v:.2f}' for v in values], textposition='outside'
        ))
    fig.update_layout(
        height=height, barmode='group',
        title=f'{category_config["title"]} Comparison' if show_title else '',
        margin=dict(l=100, r=20, t=10, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='', tickangle=-45),
        yaxis=dict(title='Value', gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'},
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1)
    )
    return fig


def get_category_scores(kpis: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Durchschnittliche Scores für jede Kategorie berechnen."""
    category_scores = {}
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            scores = []
            for kpi_name, kpi_value in kpis[category].items():
                kpi_cfg = config['kpis'].get(kpi_name, {})
                score = _calculate_kpi_score(kpi_value, kpi_cfg.get('worst', 1), kpi_cfg.get('best', 0))
                scores.append(score)
            category_scores[category] = sum(scores) / len(scores) if scores else 0
    return category_scores
