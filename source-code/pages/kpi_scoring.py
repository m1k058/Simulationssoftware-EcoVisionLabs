"""
KPI Scoring Dashboard - Energiesimulation Ergebnisse Bewertung.

Integriert nahtlos mit dem Simulation-Workflow und zieht Daten aus:
- st.session_state.fullSimResults (Simulationsergebnisse)
- st.session_state.sm.scenario_data["target_storage_capacities"] (Speicherkonfiguration)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from data_processing.scoring_system import get_score_and_kpis
from plotting.scoring_plots import (
    create_gauge_chart,
    create_category_radar_chart,
    create_kpi_bar_chart,
    create_kpi_table,
    get_category_scores,
    KPI_CONFIG
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def convert_results_to_scoring_format(results: Dict[int, Dict[str, Any]], year: int) -> Dict[str, Any]:
    """
    Convert simulation results to the format expected by scoring_system.
    
    Args:
        results: Full simulation results dictionary (indexed by year)
        year: Year to extract
    
    Returns:
        Dictionary in scoring_system format with renamed keys
    """
    if year not in results:
        raise ValueError(f"Year {year} not found in results")
    
    year_results = results[year]
    
    # Map simulation result keys to scoring system keys
    scoring_results = {
        'Verbrauch': year_results['consumption'],
        'Erzeugung': year_results['production'],
        'E-Mobility': year_results['emobility'],
        'Speicher': year_results['storage'],
        'Bilanz_vor_Flex': year_results['balance_pre_flex'],
        'Bilanz_nach_Flex': year_results['balance_post_flex'],
        'Wirtschaftlichkeit': year_results['economics']
    }
    
    return scoring_results


def get_storage_config(scenario_manager) -> Dict[str, Any]:
    """
    Extract storage configuration from scenario manager.
    
    Args:
        scenario_manager: ScenarioManager instance
    
    Returns:
        Storage configuration dictionary
    """
    if scenario_manager is None or scenario_manager.scenario_data is None:
        return {}
    
    return scenario_manager.scenario_data.get("target_storage_capacities", {})


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_kpi_overview(kpis: Dict[str, Any]):
    """Render the KPI overview section with radar chart and category scores."""
    st.header('📊 KPI Overview')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader('Category Comparison')
        radar_fig = create_category_radar_chart(kpis)
        st.plotly_chart(radar_fig, width='stretch')
    
    with col2:
        st.subheader('Category Scores')
        category_scores = get_category_scores(kpis)
        
        for category, score in category_scores.items():
            config = KPI_CONFIG[category]
            
            # Determine color based on score
            if score >= 80:
                delta_color = 'normal'
            elif score >= 60:
                delta_color = 'off'
            else:
                delta_color = 'inverse'
            
            st.metric(
                label=config['title'],
                value=f'{score:.1f} pts',
                delta=None,
                delta_color=delta_color
            )
        
        # Overall score
        overall_score = sum(category_scores.values()) / len(category_scores)
        st.markdown('---')
        st.metric(
            label='🎯 Overall Score',
            value=f'{overall_score:.1f} pts',
            delta=None
        )


def render_category_details(category: str, kpis: Dict[str, float], config: Dict[str, Any]):
    """Render detailed view for a single category."""
    st.subheader(f'{config["title"]} Details')
    
    # Gauge charts in columns
    num_kpis = len(kpis)
    cols = st.columns(min(num_kpis, 3))  # Max 3 columns
    
    for idx, (kpi_name, kpi_value) in enumerate(kpis.items()):
        kpi_config = config['kpis'].get(kpi_name, {})
        col_idx = idx % 3
        
        with cols[col_idx]:
            gauge_fig = create_gauge_chart(
                kpi_value,
                kpi_config.get('name', kpi_name),
                kpi_config.get('worst', 1),
                kpi_config.get('best', 0),
                height=250
            )
            st.plotly_chart(gauge_fig, width='stretch')
            
            # Show actual value
            value_format = kpi_config.get('format', '.2f')
            if value_format == '.2%':
                formatted_value = f'{kpi_value * 100:.2f}%'
            elif value_format == '.4f':
                formatted_value = f'{kpi_value:.4f} {kpi_config.get("unit", "")}'
            else:
                formatted_value = f'{kpi_value:.2f}'
            
            st.markdown(f'**Value:** {formatted_value}')
            st.caption(kpi_config.get('description', ''))
    
    # Bar chart
    st.markdown('---')
    st.subheader('KPI Values')
    bar_fig = create_kpi_bar_chart(kpis, config)
    st.plotly_chart(bar_fig, width='stretch')


def render_detailed_table(kpis: Dict[str, Any]):
    """Render detailed KPI table."""
    st.subheader('📋 Detailed KPI Table')
    df = create_kpi_table(kpis)
    
    # Style the dataframe
    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config={
            'Category': st.column_config.TextColumn('Category', width='small'),
            'KPI': st.column_config.TextColumn('KPI', width='medium'),
            'Value': st.column_config.TextColumn('Value', width='small'),
            'Score': st.column_config.NumberColumn('Score', width='small', format='%.1f'),
            'Rating': st.column_config.TextColumn('Rating', width='small'),
            'Description': st.column_config.TextColumn('Description', width='large')
        }
    )


def render_raw_values(kpis: Dict[str, Any]):
    """Render raw values for debugging."""
    st.subheader('🔧 Raw Values (Debug)')
    
    if 'raw_values' in kpis:
        # Group values by category
        security_vals = {k: v for k, v in kpis['raw_values'].items() 
                        if any(x in k for x in ['unserved', 'deficit', 'load', 'h2'])}
        ecology_vals = {k: v for k, v in kpis['raw_values'].items() 
                       if any(x in k for x in ['co2', 'renewable', 'fossil', 'curtailment'])}
        economy_vals = {k: v for k, v in kpis['raw_values'].items() 
                       if any(x in k for x in ['import', 'storage', 'lcoe', 'hours'])}
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('**Security Values**')
            st.json(security_vals)
        
        with col2:
            st.markdown('**Ecology Values**')
            st.json(ecology_vals)
        
        with col3:
            st.markdown('**Economy Values**')
            st.json(economy_vals)


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def display_kpi_dashboard(
    results: Dict[int, Dict[str, Any]],
    storage_config: Dict[str, Any],
    year: int
):
    """
    Main KPI dashboard display function.
    
    Args:
        results: Full simulation results (indexed by year)
        storage_config: Storage configuration from scenario
        year: Year to analyze
    """
    st.title('⚡ Energy Simulation KPI Dashboard')
    st.markdown(f'**Analysis Year:** {year}')
    st.markdown('---')
    
    # Convert results to scoring format
    try:
        scoring_results = convert_results_to_scoring_format(results, year)
    except ValueError as e:
        st.error(f'Error: {str(e)}')
        st.info(f'Available years: {list(results.keys())}')
        return
    
    # Calculate KPIs
    with st.spinner('Calculating KPIs...'):
        kpis = get_score_and_kpis(scoring_results, storage_config, year)
    
    # Overview Section
    render_kpi_overview(kpis)
    
    st.markdown('---')
    
    # Category Details in Tabs
    tabs = st.tabs([config['title'] for config in KPI_CONFIG.values()])
    
    for idx, (category, config) in enumerate(KPI_CONFIG.items()):
        with tabs[idx]:
            if category not in kpis:
                st.warning(f'No data available for {config["title"]}')
                continue
            
            render_category_details(category, kpis[category], config)
    
    st.markdown('---')
    
    # Additional Information
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander('📋 Detailed Table', expanded=False):
            render_detailed_table(kpis)
    
    with col2:
        with st.expander('🔧 Raw Values', expanded=False):
            render_raw_values(kpis)


# ============================================================================
# STREAMLIT APP - MAIN PAGE
# ============================================================================

def kpi_scoring_page() -> None:
    """Main KPI Scoring Page - zieht Daten aus session_state."""
    
    # Initialisiere fullSimResults wenn nicht vorhanden
    if 'fullSimResults' not in st.session_state:
        st.session_state.fullSimResults = {}
    
    # Überprüfe ob Simulationsergebnisse verfügbar sind
    if not st.session_state.fullSimResults:
        st.warning('❌ Keine Simulationsergebnisse verfügbar.')
        st.info('Bitte führen Sie zuerst eine Simulation auf der Seite "Simulation (Single Mode)" durch.')
        return
    
    results = st.session_state.fullSimResults
    years_available = sorted(list(results.keys()))
    
    # Hole Storage Configuration aus Szenario Manager
    storage_config = get_storage_config(st.session_state.sm)
    
    # Jahr-Auswahl
    st.sidebar.markdown("### 📅 KPI Analysis Settings")
    selected_year = st.sidebar.selectbox(
        'Select Year',
        options=years_available,
        index=0,
        help='Choose the year to analyze'
    )
    
    st.sidebar.markdown('---')
    
    # Info section
    with st.sidebar.expander('ℹ️ About KPI Categories', expanded=False):
        st.markdown("""
        **KPI Categories:**
        - 🛡️ **Security**: Versorgungssicherheit
        - 🌱 **Ecology**: Umweltauswirkungen  
        - 💰 **Economy**: Wirtschaftlichkeit
        
        **Score Range:**
        - 🟢 80-100: Excellent
        - 🟡 60-80: Good
        - 🟠 40-60: Moderate
        - 🔴 0-40: Poor
        """)
    
    # Display dashboard
    try:
        display_kpi_dashboard(results, storage_config, selected_year)
    except Exception as e:
        st.error(f'❌ Error processing KPI data: {str(e)}')
        with st.expander('Show Error Details'):
            st.exception(e)


if __name__ == '__main__':
    kpi_scoring_page()
