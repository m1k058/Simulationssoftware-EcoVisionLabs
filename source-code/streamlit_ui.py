import streamlit as st

from ui.home import home_page
from ui.analysis import analysis_page
from ui.simulation_standard import standard_simulation_page
from ui.simulation_diff import diff_simulation_page
from ui.scenario_generation import scenario_generation_page


st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title="EcoVision Labs Simu",
    page_icon=":chart_with_upwards_trend:",
)


def ensure_base_session_state() -> None:
    """Stellt die zentralen Session-State Variablen bereit."""
    defaults = {
        "dm": None,
        "cfg": None,
        "load_log": "",
        "debug_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    ensure_base_session_state()

    # Definiere die Navigation mit st.Page Objekten (ohne Step-by-Step Simulation)
    
    # Erstelle Page-Objekte
    page_home = st.Page(home_page, title="Home", icon=":material/home:", default=True)
    page_simulation = st.Page(standard_simulation_page, title="Simulation (Single Mode)", icon=":material/table_chart_view:")
    page_diff_simulation = st.Page(diff_simulation_page, title="Simulation (Diff Mode)", icon=":material/balance:")
    page_scenario = st.Page(scenario_generation_page, title="Szenario Konfiguration", icon=":material/tune:")
    page_analysis = st.Page(analysis_page, title="Daten Analyse", icon=":material/area_chart:")
    
    # Speichere Page-Objekte im session_state für Navigation
    st.session_state.pages = {
        "home": page_home,
        "simulation": page_simulation,
        "diff_simulation": page_diff_simulation,
        "scenario": page_scenario,
        "analysis": page_analysis,
    }
    
    pages = {
        "Hauptseiten": [
            page_home,
            page_simulation,
            page_diff_simulation,
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
