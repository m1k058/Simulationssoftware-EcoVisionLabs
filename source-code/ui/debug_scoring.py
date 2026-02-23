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
    safety_tab, ecology_tab, economy_tab = st.tabs([
        "🛡️ Safety",
        "🌱 Ecology",
        "💰 Economy"
    ])
    
    # Speichere die eingegebenen Werte
    kpis = {}
    
    # ============== SAFETY ============== #
    with safety_tab:
        st.subheader("🛡️ Safety KPIs")
        st.markdown("Geben Sie die Werte für Safety-Indikatoren ein:")

        safety_kpis = {}
        safety_config = KPI_CONFIG['safety']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Adequacy Score
            kpi_cfg = safety_config['adequacy_score']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            safety_kpis['adequacy_score'] = st.number_input(
                "Wert (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.90,
                step=0.01,
                format="%.3f",
                key="sec_adequacy",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
            
        with col2:
            # Robustness Score
            kpi_cfg = safety_config['robustness_score']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            safety_kpis['robustness_score'] = st.number_input(
                "Wert (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.75,
                step=0.01,
                format="%.3f",
                key="sec_robustness",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
        
        # Dependency Score
        kpi_cfg = safety_config['dependency_score']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        safety_kpis['dependency_score'] = st.number_input(
            "Wert (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=0.95,
            step=0.01,
            format="%.3f",
            key="sec_dependency",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )

        # Composite (Anzeige)
        safety_composite = (safety_kpis['adequacy_score'] + safety_kpis['robustness_score'] + safety_kpis['dependency_score']) / 3.0
        st.info(f"📊 Safety Composite Score (gleichgewichtet): **{safety_composite:.3f}**")
        kpis['safety'] = safety_kpis
    
    # ============== ECOLOGY ============== #
    with ecology_tab:
        st.subheader("🌱 Ecology KPIs")
        st.markdown("Geben Sie die Werte für Ecology-Indikatoren ein:")
        
        ecology_kpis = {}
        ecology_config = KPI_CONFIG['ecology']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CO2 Score
            kpi_cfg = ecology_config['co2_score']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            ecology_kpis['co2_score'] = st.number_input(
                "Score (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.57,  # ≙ CO2 ≈ 170 g/kWh
                step=0.01,
                format="%.3f",
                key="eco_co2",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
            
        with col2:
            # Renewable Share
            kpi_cfg = ecology_config['renewable_share']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            ecology_kpis['renewable_share'] = st.number_input(
                "Score (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.85,
                step=0.01,
                format="%.3f",
                key="eco_renewable",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )
        
        # Curtailment Score
        kpi_cfg = ecology_config['curtailment_score']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        ecology_kpis['curtailment_score'] = st.number_input(
            "Score (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=0.80,
            step=0.01,
            format="%.3f",
            key="eco_curtailment",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )

        # Gewichteter Gesamt-Score (Anzeige)
        eco_composite = 0.60 * ecology_kpis['co2_score'] + 0.25 * ecology_kpis['renewable_share'] + 0.15 * ecology_kpis['curtailment_score']
        st.info(f"📊 Ecology Composite Score (60/25/15 %): **{eco_composite:.3f}**")
        kpis['ecology'] = ecology_kpis
        
        kpis['ecology'] = ecology_kpis
    
    # ============== ECONOMY ============== #
    with economy_tab:
        st.subheader("💰 Economy KPIs")
        st.markdown("Geben Sie die Werte für Economy-Indikatoren ein:")
        
        economy_kpis = {}
        economy_config = KPI_CONFIG['economy']['kpis']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # LCOE Index
            kpi_cfg = economy_config['lcoe_index']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            economy_kpis['lcoe_index'] = st.number_input(
                "Score (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.98,  # ≙ LCOE ≈ 8.6 ct/kWh
                step=0.01,
                format="%.3f",
                key="econ_lcoe",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )

        with col2:
            # Curtailment Econ Score
            kpi_cfg = economy_config['curtailment_econ_score']
            st.markdown(f"**{kpi_cfg['name']}**")
            st.caption(kpi_cfg['description'])
            economy_kpis['curtailment_econ_score'] = st.number_input(
                "Score (0–1)",
                min_value=0.0,
                max_value=1.0,
                value=0.88,
                step=0.01,
                format="%.3f",
                key="econ_curtailment",
                help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
            )

        # Storage Efficiency
        kpi_cfg = economy_config['storage_efficiency']
        st.markdown(f"**{kpi_cfg['name']}**")
        st.caption(kpi_cfg['description'])
        economy_kpis['storage_efficiency'] = st.number_input(
            "Score (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=0.65,
            step=0.01,
            format="%.3f",
            key="econ_storage",
            help=f"Best: {kpi_cfg['best']}, Worst: {kpi_cfg['worst']}"
        )

        # Gewichteter Gesamt-Score (Anzeige)
        composite = 0.40 * economy_kpis['lcoe_index'] + 0.35 * economy_kpis['curtailment_econ_score'] + 0.25 * economy_kpis['storage_efficiency']
        st.info(f"📊 Economy Composite Score (40/35/25 %): **{composite:.3f}**")
        kpis['economy'] = economy_kpis

        # Übergreifender Gesamt-Score
        overall = round(0.40 * safety_composite + 0.30 * eco_composite + 0.30 * composite, 4)
        kpis['safety_composite']  = round(safety_composite, 4)
        kpis['ecology_composite'] = round(eco_composite, 4)
        kpis['economy_composite'] = round(composite, 4)
        kpis['overall_score']     = overall
    
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
        
        overall_score = (
            0.40 * category_scores.get('safety', 0)
            + 0.30 * category_scores.get('ecology', 0)
            + 0.30 * category_scores.get('economy', 0)
        )
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
