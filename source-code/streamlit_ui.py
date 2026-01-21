import streamlit as st

from ui.home import home_page, load_data_manager
from ui.analysis import analysis_page
from ui.simulation_standard import standard_simulation_page
from ui.simulation_diff import diff_simulation_page
from ui.simulation_comparison import comparison_simulation_page
from ui.scenario_generation import scenario_generation_page
from ui.debug_scoring import debug_scoring_page


st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="EcoVision Labs Simu",
    page_icon=":chart_with_upwards_trend:",
)


def ensure_base_session_state() -> None:
    """Stellt die zentralen Session-State Variablen bereit und lädt Daten automatisch."""
    defaults = {
        "dm": None,
        "cfg": None,
        "sm": None,
        "load_log": "",
        "debug_mode": False,
        "auto_load_attempted": False,
        "loading_in_progress": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Automatisches Laden der Daten beim ersten Start
    if not st.session_state.auto_load_attempted and not st.session_state.loading_in_progress:
        st.session_state.auto_load_attempted = True
        st.session_state.loading_in_progress = True
        
        if st.session_state.dm is None:
            # Zeige Loading-Screen
            st.markdown("""
                <style>
                    [data-testid="stSidebar"] { display: none; }
                    [data-testid="stMainBlockContainer"] { padding: 0; }
                </style>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("<br>" * 3, unsafe_allow_html=True)
                st.markdown("""
                    <div style="text-align: center;">
                        <h1>⚙️ Initializing EcoVision Labs</h1>
                        <p style="font-size: 16px; color: #888;">Loading configuration and datasets...</p>
                    </div>
                """, unsafe_allow_html=True)
                
                progress_placeholder = st.empty()
                log_placeholder = st.empty()
                dataset_placeholder = st.empty()
                
                # Progress 1
                progress_placeholder.progress(10, "Loading ConfigManager...")
                log_placeholder.info("📄 Loading ConfigManager...")
                
                # Progress 2
                progress_placeholder.progress(20, "Loading ScenarioManager...")
                log_placeholder.info("📋 Loading ScenarioManager...")
                
                # Callback für Dataset-Progress
                def on_dataset_loaded(current: int, total: int, name: str):
                    progress = 20 + int((current / total) * 70) if total > 0 else 20
                    progress_placeholder.progress(progress, f"Loading {current}/{total} datasets...")
                    dataset_placeholder.caption(f"📊 Loading: **{name}**")
                
                # Load Data mit Callback
                success = load_data_manager(progress_callback=on_dataset_loaded)
                
                if success:
                    progress_placeholder.progress(100, "Complete!")
                    log_placeholder.success("✅ All components loaded successfully!")
                    dataset_placeholder.caption("✅ All datasets loaded!")
                    import time
                    time.sleep(0.3)
                    st.rerun()
                else:
                    log_placeholder.error("❌ Loading failed")
                    st.stop()


def main() -> None:
    ensure_base_session_state()

    # Definiere die Navigation mit st.Page Objekten (ohne Step-by-Step Simulation)
    
    # Erstelle Page-Objekte
    page_home = st.Page(home_page, title="Home", icon=":material/home:", default=True)
    page_simulation = st.Page(standard_simulation_page, title="Simulation (Single Mode)", icon=":material/table_chart_view:")
    page_diff_simulation = st.Page(diff_simulation_page, title="Simulation (Diff Mode)", icon=":material/balance:")
    page_comparison_simulation = st.Page(comparison_simulation_page, title="Simulation (Vergleich)", icon=":material/compare_arrows:")
    page_scenario = st.Page(scenario_generation_page, title="Szenario Konfiguration", icon=":material/tune:")
    page_analysis = st.Page(analysis_page, title="Daten Analyse", icon=":material/area_chart:")
    
    # Debug-Seite nur im DEBUG-Modus
    page_debug_scoring = st.Page(debug_scoring_page, title="⚠️ Nur im Notfall benutzen!", icon=":material/warning:")
    
    # Speichere Page-Objekte im session_state für Navigation (inkl. Debug-Seite für direkten Zugriff)
    st.session_state.pages = {
        "home": page_home,
        "simulation": page_simulation,
        "diff_simulation": page_diff_simulation,
        "comparison_simulation": page_comparison_simulation,
        "scenario": page_scenario,
        "analysis": page_analysis,
        "debug_scoring": page_debug_scoring,  # Immer verfügbar für direkten Zugriff
    }
    
    # Baue das pages Dictionary
    pages = {
        "Hauptseiten": [
            page_home,
            page_simulation,
            page_diff_simulation,
            page_comparison_simulation,
            page_scenario,
            page_analysis,
        ]
    }

    # Nutze st.navigation für die Navigation
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs the module, so execute immediately.
    main()
