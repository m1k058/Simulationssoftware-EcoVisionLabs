import streamlit as st

from ui.home import home_page
from ui.analysis import analysis_page
from ui.simulation_standard import standard_simulation_page
from ui.step_simulation.step_pages import (
    step_1_daten_auswaehlen,
    step_2_verbrauch_simulieren,
    step_3_erzeugung_simulieren,
    step_4_defizite_anzeigen,
    step_5_speicher_simulieren,
    step_6_gesamt_validieren,
    step_7_ergebnisse_speichern,
)
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

    # Definiere die Navigation mit st.Page Objekten und Unterseiten
    # ALLE Step-Pages sind immer in der Liste, aber nur verfügbare sind anklickbar
    
    # Erstelle Page-Objekte
    page_home = st.Page(home_page, title="Home", icon=":material/home:", default=True)
    page_simulation = st.Page(standard_simulation_page, title="Main Simulation", icon=":material/table_chart_view:")
    page_scenario = st.Page(scenario_generation_page, title="Szenario Konfiguration", icon=":material/tune:")
    page_analysis = st.Page(analysis_page, title="Daten Analyse", icon=":material/area_chart:")
    
    # Speichere Page-Objekte im session_state für Navigation
    st.session_state.pages = {
        "home": page_home,
        "simulation": page_simulation,
        "scenario": page_scenario,
        "analysis": page_analysis,
    }
    
    pages = {
        "Hauptseiten": [
            page_home,
            page_simulation,
            page_scenario,
            page_analysis,
        ],
        "Step by Step Simulation": [
            st.Page(step_1_daten_auswaehlen, title="Step 1: Daten auswählen", icon="1️⃣"),
            st.Page(step_2_verbrauch_simulieren, title="Step 2: Verbrauch", icon="2️⃣"),
            st.Page(step_3_erzeugung_simulieren, title="Step 3: Erzeugung", icon="3️⃣"),
            st.Page(step_4_defizite_anzeigen, title="Step 4: Defizite", icon="4️⃣"),
            st.Page(step_5_speicher_simulieren, title="Step 5: Speicher", icon="5️⃣"),
            st.Page(step_6_gesamt_validieren, title="Step 6: Ergebnisse", icon="6️⃣"),
            st.Page(step_7_ergebnisse_speichern, title="Step 7: Speichern", icon="7️⃣"),
        ],
    }

    # Nutze st.navigation für die Navigation
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs the module, so execute immediately.
    main()
