"""
Plotting functions for energy simulation KPI visualization.
"""

import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Optional


# ============================================================================
# CONFIGURATION
# ============================================================================

KPI_CONFIG = {
    'security': {
        'title': '🛡️ Security',
        'color': '#FF6B6B',
        'kpis': {
            'unserved_mwh': {
                'name': 'Unserved Energy Ratio',
                'description': 'Anteil ungedeckter Energie an Gesamtlast',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'max_unserved_mw': {
                'name': 'Max Unserved Power Ratio',
                'description': 'Maximale ungedeckte Leistung',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'deficit_h': {
                'name': 'Deficit Hours Ratio',
                'description': 'Anteil Stunden mit Defizit',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'h2_soc': {
                'name': 'H2 Storage Utilization',
                'description': 'Durchschnittlicher H2-Füllstand',
                'unit': '%',
                'format': '.2%',
                'worst': 0,
                'best': 1
            }
        }
    },
    'ecology': {
        'title': '🌱 Ecology',
        'color': '#4ECDC4',
        'kpis': {
            'co2_intensity': {
                'name': 'CO2 Intensity',
                'description': 'CO2-Emissionen vs. Worst Case',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'curtailment_mwh': {
                'name': 'Curtailment Ratio',
                'description': 'Abgeregelter Anteil erneuerbarer Energie',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'fossil_share': {
                'name': 'Fossil Share',
                'description': 'Anteil fossiler Erzeugung',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            }
        }
    },
    'economy': {
        'title': '💰 Economy',
        'color': '#95E1D3',
        'kpis': {
            'system_cost_index': {
                'name': 'System Cost (LCOE)',
                'description': 'Levelized Cost of Energy',
                'unit': 'ct/kWh',
                'format': '.2f',
                'worst': 100,
                'best': 0
            },
            'import_dependency': {
                'name': 'Import Dependency',
                'description': 'Anteil importierter Energie',
                'unit': '%',
                'format': '.2%',
                'worst': 1,
                'best': 0
            },
            'storage_utilization': {
                'name': 'Storage Utilization',
                'description': 'Speicherauslastung',
                'unit': '%',
                'format': '.2%',
                'worst': 0,
                'best': 1
            }
        }
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_kpi_score(value: float, worst: float, best: float) -> float:
    """
    Calculate a score (0-100) for a KPI value.
    
    Args:
        value: Current KPI value
        worst: Worst possible value
        best: Best possible value
    
    Returns:
        Score between 0 and 100 (100 = best)
    """
    lower_is_better = best < worst
    
    if lower_is_better:
        score = max(0, min(100, (1 - value / worst) * 100)) if worst > 0 else 100
    else:
        score = max(0, min(100, (value / best) * 100)) if best > 0 else 0
    
    return score


def _get_score_color(score: float) -> str:
    """
    Get color based on score value.
    
    Args:
        score: Score value (0-100)
    
    Returns:
        Hex color code
    """
    if score >= 80:
        return '#4CAF50'  # Green
    elif score >= 60:
        return '#FFC107'  # Yellow
    elif score >= 40:
        return '#FF9800'  # Orange
    else:
        return '#F44336'  # Red


def _format_kpi_value(value: float, kpi_config: Dict[str, Any]) -> str:
    """
    Format KPI value according to its configuration.
    
    Args:
        value: KPI value
        kpi_config: KPI configuration dict
    
    Returns:
        Formatted string
    """
    value_format = kpi_config.get('format', '.2f')
    unit = kpi_config.get('unit', '')
    
    if value_format == '.2%':
        return f'{value * 100:.2f}%'
    elif value_format == '.4f':
        return f'{value:.4f} {unit}'.strip()
    else:
        return f'{value:.2f} {unit}'.strip()


# ============================================================================
# PLOTTING FUNCTIONS
# ============================================================================

def create_gauge_chart(
    value: float,
    title: str,
    worst: float,
    best: float,
    height: int = 250
) -> go.Figure:
    """
    Create a gauge chart for a single KPI.
    
    Args:
        value: Current KPI value
        title: Chart title
        worst: Worst possible value
        best: Best possible value
        height: Chart height in pixels
    
    Returns:
        Plotly Figure object
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
    Create a radar chart comparing all three categories.
    
    Args:
        kpis: Dictionary with KPI results from get_score_and_kpis()
        height: Chart height in pixels
    
    Returns:
        Plotly Figure object
    """
    categories = []
    scores = []
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            # Calculate average score for category
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
    Create a bar chart for KPIs in a category.
    
    Args:
        kpis: Dictionary of KPI values
        category_config: Configuration for the category
        horizontal: If True, create horizontal bars
        height: Chart height in pixels (auto-calculated if None)
    
    Returns:
        Plotly Figure object
    """
    kpi_names = []
    kpi_values = []
    kpi_colors = []
    
    for kpi_name, kpi_value in kpis.items():
        kpi_config = category_config['kpis'].get(kpi_name, {})
        kpi_names.append(kpi_config.get('name', kpi_name))
        
        # Convert percentage values to 0-100 scale for display
        display_value = kpi_value * 100 if kpi_config.get('unit') == '%' else kpi_value
        kpi_values.append(display_value)
        
        # Calculate score and get color
        worst = kpi_config.get('worst', 1)
        best = kpi_config.get('best', 0)
        score = _calculate_kpi_score(kpi_value, worst, best)
        kpi_colors.append(_get_score_color(score))
    
    # Auto-calculate height if not provided
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
    Create a bar chart showing average scores for each category.
    
    Args:
        kpis: Dictionary with KPI results from get_score_and_kpis()
        height: Chart height in pixels
    
    Returns:
        Plotly Figure object
    """
    categories = []
    scores = []
    colors = []
    
    for category, config in KPI_CONFIG.items():
        if category in kpis:
            # Calculate average score for category
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
    category: str = 'security',
    height: int = 400
) -> go.Figure:
    """
    Create a comparison chart for multiple simulation runs.
    
    Args:
        kpis_list: List of KPI dictionaries to compare
        labels: Labels for each simulation run
        category: Category to compare ('security', 'ecology', 'economy')
        height: Chart height in pixels
    
    Returns:
        Plotly Figure object
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
        title=f'{category_config["title"]} Comparison',
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='', tickangle=-45),
        yaxis=dict(title='Value', gridcolor='lightgray'),
        font={'color': '#333', 'family': 'Arial'},
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig


def create_kpi_table(kpis: Dict[str, Dict[str, float]]) -> pd.DataFrame:
    """
    Create a detailed table of all KPIs.
    
    Args:
        kpis: Dictionary with KPI results from get_score_and_kpis()
    
    Returns:
        Pandas DataFrame with formatted KPI data
    """
    rows = []
    
    for category, category_kpis in kpis.items():
        if category == 'raw_values':
            continue
        
        category_config = KPI_CONFIG.get(category, {})
        
        for kpi_name, kpi_value in category_kpis.items():
            kpi_config = category_config.get('kpis', {}).get(kpi_name, {})
            
            # Calculate score
            worst = kpi_config.get('worst', 1)
            best = kpi_config.get('best', 0)
            score = _calculate_kpi_score(kpi_value, worst, best)
            
            # Format value
            formatted_value = _format_kpi_value(kpi_value, kpi_config)
            
            rows.append({
                'Category': category_config.get('title', category),
                'KPI': kpi_config.get('name', kpi_name),
                'Value': formatted_value,
                'Score': f'{score:.1f}',
                'Rating': '⭐' * (int(score / 20)),  # 0-5 stars
                'Description': kpi_config.get('description', '')
            })
    
    return pd.DataFrame(rows)


def get_category_scores(kpis: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Calculate average scores for each category.
    
    Args:
        kpis: Dictionary with KPI results from get_score_and_kpis()
    
    Returns:
        Dictionary mapping category names to average scores
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