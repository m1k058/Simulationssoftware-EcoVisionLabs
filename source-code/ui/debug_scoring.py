"""
Debug-Seite für manuelles Scoring-Dashboard Testing.
Nur im DEBUG-Modus verfügbar.
"""

import streamlit as st
from plotting.scoring_plots import (
    create_gauge_chart,
    create_category_radar_chart,
    create_kpi_bar_chart,
    create_kpi_table,
    get_category_scores,
    KPI_CONFIG,
)


def debug_scoring_page():
    """
    Debug-Seite für manuelles Eingeben von KPI-Werten.
    Nur im DEBUG-Modus verfügbar!
    """
    st.title("⚠️ Nur im Notfall benutzen!")
    
    st.warning("""
    **ACHTUNG:** Diese Seite ist nur für Debug-Zwecke gedacht!
    
    Hier können Sie manuell KPI-Werte eingeben und das Scoring-Dashboard testen,
    ohne eine vollständige Simulation durchführen zu müssen.
    """)
    
    st.markdown("---")
    
    # Tabs für die drei Kategorien
    security_tab, ecology_tab, economy_tab = st.tabs([
        "🛡️ Security",
        "🌱 Ecology", 
        "💰 Economy"
    ])
    
    # Speichere die eingegebenen Werte
    kpis = {}
    
    # ============== SECURITY ============== #
    with security_tab:
        st.subheader("🛡️ Security KPIs")
        st.markdown("Geben Sie die Werte für Security-Indikatoren ein:")
        
        security_kpis = {}
        security_config = KPI_CONFIG['security']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Energy Deficit Share
            kpi_cfg = security_config['energy_deficit_share']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            security_kpis['energy_deficit_share'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=1.0,
                value=0.05,
                step=0.01,
                format="%.4f",
                key="sec_energy_deficit",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
            
        with col2:
            # Peak Deficit Ratio
            kpi_cfg = security_config['peak_deficit_ratio']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            security_kpis['peak_deficit_ratio'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=1.0,
                value=0.10,
                step=0.01,
                format="%.4f",
                key="sec_peak_deficit",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
        
        # Deficit Frequency
        kpi_cfg = security_config['deficit_frequency']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        security_kpis['deficit_frequency'] = st.number_input(
            f"Wert ({kpi_cfg['unit']})",
            min_value=0.0,
            max_value=1.0,
            value=0.02,
            step=0.01,
            format="%.4f",
            key="sec_deficit_freq",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )
        
        kpis['security'] = security_kpis
    
    # ============== ECOLOGY ============== #
    with ecology_tab:
        st.subheader("🌱 Ecology KPIs")
        st.markdown("Geben Sie die Werte für Ecology-Indikatoren ein:")
        
        ecology_kpis = {}
        ecology_config = KPI_CONFIG['ecology']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CO2 Intensity
            kpi_cfg = ecology_config['co2_intensity']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            ecology_kpis['co2_intensity'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=1000.0,
                value=150.0,
                step=10.0,
                format="%.2f",
                key="eco_co2",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
            
        with col2:
            # Curtailment Share
            kpi_cfg = ecology_config['curtailment_share']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            ecology_kpis['curtailment_share'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=1.0,
                value=0.08,
                step=0.01,
                format="%.4f",
                key="eco_curtailment",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
        
        # Fossil Share
        kpi_cfg = ecology_config['fossil_share']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        ecology_kpis['fossil_share'] = st.number_input(
            f"Wert ({kpi_cfg['unit']})",
            min_value=0.0,
            max_value=1.0,
            value=0.15,
            step=0.01,
            format="%.4f",
            key="eco_fossil",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )
        
        kpis['ecology'] = ecology_kpis
    
    # ============== ECONOMY ============== #
    with economy_tab:
        st.subheader("💰 Economy KPIs")
        st.markdown("Geben Sie die Werte für Economy-Indikatoren ein:")
        
        economy_kpis = {}
        economy_config = KPI_CONFIG['economy']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # System Cost Index
            kpi_cfg = economy_config['system_cost_index']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            economy_kpis['system_cost_index'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=100.0,
                value=8.5,
                step=0.5,
                format="%.2f",
                key="econ_cost",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
            
        with col2:
            # Import Dependency
            kpi_cfg = economy_config['import_dependency']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            economy_kpis['import_dependency'] = st.number_input(
                f"Wert ({kpi_cfg['unit']})",
                min_value=0.0,
                max_value=1.0,
                value=0.12,
                step=0.01,
                format="%.4f",
                key="econ_import",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
        
        # Storage Utilization
        kpi_cfg = economy_config['storage_utilization']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        economy_kpis['storage_utilization'] = st.number_input(
            f"Wert ({kpi_cfg['unit']})",
            min_value=0.0,
            max_value=1.0,
            value=0.65,
            step=0.01,
            format="%.4f",
            key="econ_storage",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )
        
        kpis['economy'] = economy_kpis
    
    # ============== DASHBOARD ============== #
    st.markdown("---")
    st.markdown("---")
    
    st.header("📊 Generiertes Scoring-Dashboard")
    st.caption("💡 Das Dashboard wird automatisch aktualisiert, wenn Sie die Werte oben ändern.")
    
    # KPI Überblick
    st.subheader("📊 KPI Überblick")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Kategorie-Vergleich**")
        radar_fig = create_category_radar_chart(kpis)
        st.plotly_chart(radar_fig, width='stretch')
    
    with col2:
        st.markdown("**Kategorie-Scores**")
        category_scores = get_category_scores(kpis)
        
        for category, score in category_scores.items():
            config = KPI_CONFIG[category]
            
            if score >= 80:
                delta_color = "normal"
            elif score >= 60:
                delta_color = "off"
            else:
                delta_color = "inverse"
            
            st.metric(
                label=config['title'],
                value=f"{score:.1f} Punkte",
                delta=None,
                delta_color=delta_color
            )
        
        overall_score = sum(category_scores.values()) / len(category_scores)
        st.markdown("---")
        st.metric(
            label="🎯 Gesamtscore",
            value=f"{overall_score:.1f} Punkte",
            delta=None
        )
    
    st.markdown("---")
    
    # Detail-Tabs
    detail_tabs = st.tabs([config['title'] for config in KPI_CONFIG.values()])
    
    for idx, (category, config) in enumerate(KPI_CONFIG.items()):
        with detail_tabs[idx]:
            st.subheader(f"{config['title']} Details")
            
            category_kpis = kpis[category]
            num_kpis = len(category_kpis)
            cols = st.columns(min(num_kpis, 3))
            
            for kpi_idx, (kpi_name, kpi_value) in enumerate(category_kpis.items()):
                kpi_config = config['kpis'].get(kpi_name, {})
                col_idx = kpi_idx % 3
                
                with cols[col_idx]:
                    gauge_fig = create_gauge_chart(
                        kpi_value,
                        kpi_config.get('name', kpi_name),
                        kpi_config.get('worst', 1),
                        kpi_config.get('best', 0),
                        height=250
                    )
                    st.plotly_chart(gauge_fig, width='stretch')
                    
                    value_format = kpi_config.get('format', '.2f')
                    if value_format == '.2%':
                        formatted_value = f"{kpi_value * 100:.2f}%"
                    elif value_format == '.4f':
                        formatted_value = f"{kpi_value:.4f} {kpi_config.get('unit', '')}"
                    else:
                        formatted_value = f"{kpi_value:.2f}"
                    
                    st.markdown(f"**Wert:** {formatted_value}")
                    st.caption(kpi_config.get('description', ''))
            
            st.markdown("---")
            st.subheader("KPI Werte")
            bar_fig = create_kpi_bar_chart(category_kpis, config)
            st.plotly_chart(bar_fig, width='stretch')
    
    st.markdown("---")
    
    # Detaillierte Tabelle
    with st.expander("📋 Detaillierte Tabelle", expanded=False):
        st.subheader("📋 Detaillierte KPI-Tabelle")
        df = create_kpi_table(kpis)
        
        st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            column_config={
                "Category": st.column_config.TextColumn("Kategorie", width="small"),
                "KPI": st.column_config.TextColumn("KPI", width="medium"),
                "Value": st.column_config.TextColumn("Wert", width="small"),
                "Score": st.column_config.NumberColumn("Score", width="small", format="%.1f"),
                "Rating": st.column_config.TextColumn("Bewertung", width="small"),
                "Description": st.column_config.TextColumn("Beschreibung", width="large"),
            }
        )
