import streamlit as st
from pathlib import Path
import traceback
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager


def load_data_manager(progress_callback=None) -> bool:
    """Lädt den DataManager und ConfigManager und speichert sie im Session-State.
    
    Args:
        progress_callback (callable, optional): Callback-Funktion für Fortschrittsaktualisierungen.
    
    Returns:
        bool: True wenn erfolgreich geladen, sonst False.
    """
        
    try:
        config_path = Path(__file__).parent.parent / "config.json"
        cfg = ConfigManager(config_path=config_path)
        dm = DataManager(config_manager=cfg, progress_callback=progress_callback)
        sm = ScenarioManager()
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        st.session_state.sm = sm
        return True
        
    except Exception as e:
        st.error(f"❌ LOAD DATA: Fehler beim Laden: {e}")
        print(traceback.format_exc())
        return False


def home_page() -> None:
    """Home-Page und Datenverwaltung."""
    
    st.title("Simulationssoftware EcoVision Labs")
    
    # Logo
    logo_path = Path(__file__).parent.parent.parent / "assets" / "logo.png"
    if logo_path.exists():
        st.logo(str(logo_path), size="large")
    is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

    st.subheader("Willkommen! ")
    st.write("Nutze die Navigation in der Seitenleiste oder die Buttons unten, um zu den verschiedenen Funktionen zu gelangen.")


    # Navigation
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Main Simulation", width='stretch', icon=":material/table_chart_view:"):
            st.switch_page(st.session_state.pages["simulation"])
    
    with col2:
        if st.button("Szenario Konfiguration", width='stretch', icon=":material/tune:"):
            st.switch_page(st.session_state.pages["scenario"])
    
    with col3:
        if st.button("Daten Analyse", width='stretch', icon=":material/area_chart:"):
            st.switch_page(st.session_state.pages["analysis"])

    st.markdown("---")
    st.subheader("Status:")    
    if is_loaded:
        st.success(":material/check: DataManager, ConfigManager, ScenarioManager sind geladen und bereit.")
    else:
        st.warning(":material/sync: Daten werden beim Start automatisch geladen...")
        st.info("Falls das Laden fehlgeschlagen ist, verwende den Button unten zum manuellen Neuladen.")

    # manual reload button
    if st.button(":material/refresh: Daten neu laden", width='stretch', type="secondary" if is_loaded else "primary"):
        with st.spinner("Datenmanager/ConfigManager/ScenarioManager laden..."):
            success = load_data_manager()
        if success:
            st.success("✅ DataManager, ConfigManager, ScenarioManager erfolgreich geladen!")
            st.rerun()
        else:
            st.error("❌ Laden fehlgeschlagen. Siehe Log/Console für Details.")
    elif is_loaded and st.session_state.debug_mode:
        # IF loaded und debug: log 
        with st.expander(":material/list: Geladene Datasets", expanded=False):
            try:
                datasets = st.session_state.dm.list_datasets()
                if datasets:
                    for i, ds in enumerate(datasets, start=1):
                        st.write(f"**{i}. {ds['Name']}** (ID: {ds['ID']}) - {ds['Rows']} Zeilen")
                else:
                    st.write("Keine Datasets geladen")
            except Exception as e:
                st.warning(f"Konnte Datasets nicht abrufen: {e}")
        
            # DEBUG Scoring Dashboard
            with st.expander("DEBUG: LEGACY MODE", expanded=False):
                render_debug_scoring_dashboard()
    
    # Globaler Debug-Schalter: steuert Logging in der gesamten App
    st.checkbox(
        ":material/bug_report: Debug Modus",
        value=st.session_state.get("debug_mode", False),
        key="debug_mode",
        help="Aktiviere detailliertes Logging und verbosen Modus in allen Simulationen."
    )


def render_debug_scoring_dashboard():
    """Rendert das Debug Scoring Dashboard mit direkter Score-Eingabe (0-100)."""
    from plotting.scoring_plots import (
        create_gauge_chart,
        create_category_radar_chart,
        create_kpi_bar_chart,
        create_kpi_table,
        get_category_scores,
        KPI_CONFIG,
    )
    
    st.warning("⚠️ **ACHTUNG:** Nur für Debug-Zwecke! Geben Sie Scores (0-100) ein, um das Dashboard zu testen.")
    
    st.markdown("---")
    st.subheader("🎯 Score-Eingabe (0-100)")
    
    # Initialisiere Scores Dictionary
    scores = {}
    
    # Tabs für die drei Kategorien
    security_tab, ecology_tab, economy_tab = st.tabs(["🛡️ Security", "🌱 Ecology", "💰 Economy"])
    
    # ============== SECURITY ============== #
    with security_tab:
        st.markdown("**Security Scores**")
        security_config = KPI_CONFIG['security']['kpis']
        security_scores = {}
        
        col1, col2, col3 = st.columns(3)
        
        kpi_list = list(security_config.items())
        for idx, (kpi_name, kpi_cfg) in enumerate(kpi_list):
            with [col1, col2, col3][idx % 3]:
                st.caption(f"**{kpi_cfg['name']}**")
                security_scores[kpi_name] = st.number_input(
                    "Score (0-100)",
                    min_value=0.0,
                    max_value=100.0,
                    value=80.0,
                    step=1.0,
                    key=f"sec_score_{kpi_name}",
                    help=kpi_cfg['description']
                )
        
        scores['security'] = security_scores
    
    # ============== ECOLOGY ============== #
    with ecology_tab:
        st.markdown("**Ecology Scores**")
        ecology_config = KPI_CONFIG['ecology']['kpis']
        ecology_scores = {}
        
        col1, col2, col3 = st.columns(3)
        
        kpi_list = list(ecology_config.items())
        for idx, (kpi_name, kpi_cfg) in enumerate(kpi_list):
            with [col1, col2, col3][idx % 3]:
                st.caption(f"**{kpi_cfg['name']}**")
                ecology_scores[kpi_name] = st.number_input(
                    "Score (0-100)",
                    min_value=0.0,
                    max_value=100.0,
                    value=75.0,
                    step=1.0,
                    key=f"eco_score_{kpi_name}",
                    help=kpi_cfg['description']
                )
        
        scores['ecology'] = ecology_scores
    
    # ============== ECONOMY ============== #
    with economy_tab:
        st.markdown("**Economy Scores**")
        economy_config = KPI_CONFIG['economy']['kpis']
        economy_scores = {}
        
        col1, col2, col3 = st.columns(3)
        
        kpi_list = list(economy_config.items())
        for idx, (kpi_name, kpi_cfg) in enumerate(kpi_list):
            with [col1, col2, col3][idx % 3]:
                st.caption(f"**{kpi_cfg['name']}**")
                economy_scores[kpi_name] = st.number_input(
                    "Score (0-100)",
                    min_value=0.0,
                    max_value=100.0,
                    value=70.0,
                    step=1.0,
                    key=f"econ_score_{kpi_name}",
                    help=kpi_cfg['description']
                )
        
        scores['economy'] = economy_scores
    
    # ============== DASHBOARD ============== #
    st.markdown("---")
    st.markdown("### 📊 Generiertes Scoring-Dashboard")
    st.caption("💡 Dashboard aktualisiert sich automatisch bei Eingabe-Änderungen")
    
    # KPI Überblick
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Kategorie-Vergleich**")
        # Berechne durchschnittliche Scores pro Kategorie für Radar
        category_avg_scores = {}
        for category, category_scores in scores.items():
            avg = sum(category_scores.values()) / len(category_scores) if category_scores else 0
            category_avg_scores[category] = avg
        
        # Erstelle Dummy-KPIs für Radar Chart (mit Scores statt tatsächlichen Werten)
        dummy_kpis = {}
        for category, config in KPI_CONFIG.items():
            dummy_kpis[category] = {}
            for kpi_name, kpi_cfg in config['kpis'].items():
                # Score direkt verwenden, aber als "Wert" der best=100, worst=0 hat
                score = scores[category][kpi_name]
                # Rück-berechne einen dummy Wert: bei Score 80 und worst=1,best=0 → value=0.2
                worst = kpi_cfg.get('worst', 1)
                best = kpi_cfg.get('best', 0)
                # score = (1 - (value - best)/(worst - best)) * 100
                # → (100 - score)/100 = (value - best)/(worst - best)
                # → value = best + (100 - score)/100 * (worst - best)
                dummy_value = best + (100 - score) / 100 * (worst - best)
                dummy_kpis[category][kpi_name] = dummy_value
        
        radar_fig = create_category_radar_chart(dummy_kpis)
        st.plotly_chart(radar_fig, width='stretch')
    
    with col2:
        st.markdown("**Kategorie-Scores**")
        
        for category in ['security', 'ecology', 'economy']:
            config = KPI_CONFIG[category]
            avg_score = sum(scores[category].values()) / len(scores[category]) if scores[category] else 0
            
            if avg_score >= 80:
                delta_color = "normal"
            elif avg_score >= 60:
                delta_color = "off"
            else:
                delta_color = "inverse"
            
            st.metric(
                label=config['title'],
                value=f"{avg_score:.1f} Punkte",
                delta=None,
                delta_color=delta_color
            )
        
        overall_score = sum(
            sum(cat_scores.values()) / len(cat_scores) 
            for cat_scores in scores.values()
        ) / 3
        st.markdown("---")
        st.metric(label="🎯 Gesamtscore", value=f"{overall_score:.1f} Punkte", delta=None)
    
    st.markdown("---")
    
    # Detail-Tabs
    detail_tabs = st.tabs([config['title'] for config in KPI_CONFIG.values()])
    
    for idx, (category, config) in enumerate(KPI_CONFIG.items()):
        with detail_tabs[idx]:
            st.subheader(f"{config['title']} Details")
            
            category_scores = scores[category]
            num_kpis = len(category_scores)
            cols = st.columns(min(num_kpis, 3))
            
            for kpi_idx, (kpi_name, score_value) in enumerate(category_scores.items()):
                kpi_config = config['kpis'].get(kpi_name, {})
                col_idx = kpi_idx % 3
                
                with cols[col_idx]:
                    # Erstelle Gauge mit Score
                    gauge_fig = create_gauge_chart(
                        score_value,  # Direkt der Score
                        kpi_config.get('name', kpi_name),
                        0,  # worst = 0 für Score
                        100,  # best = 100 für Score
                        height=250
                    )
                    st.plotly_chart(gauge_fig, width='stretch')
                    
                    st.markdown(f"**Score:** {score_value:.1f} / 100")
                    st.caption(kpi_config.get('description', ''))
            
            st.markdown("---")
            st.subheader("Score-Verteilung")
            
            # Bar Chart für Scores
            import plotly.graph_objects as go
            
            kpi_names = [config['kpis'][k]['name'] for k in category_scores.keys()]
            score_values = list(category_scores.values())
            colors = ['#4CAF50' if s >= 80 else '#FFC107' if s >= 60 else '#FF9800' if s >= 40 else '#F44336' for s in score_values]
            
            fig = go.Figure(go.Bar(
                x=score_values,
                y=kpi_names,
                orientation='h',
                marker=dict(color=colors),
                text=[f"{s:.1f}" for s in score_values],
                textposition='auto'
            ))
            
            fig.update_layout(
                xaxis_title="Score",
                xaxis=dict(range=[0, 100]),
                height=max(250, len(kpi_names) * 60),
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False
            )
            
            st.plotly_chart(fig, width='stretch')

