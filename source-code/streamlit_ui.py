import streamlit as st

from ui import set_mode
from ui.home import show_main_menu
from ui.analysis import show_dataset_analysis
from ui.simulation_standard import show_standard_simulation
from ui.step_simulation.main import show_step_simulation
from ui.scenario_generation import show_scenario_generation


st.set_page_config(
    layout="wide",
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
        "mode": "main",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    ensure_base_session_state()

    mode = st.session_state.mode
    if mode == "main":
        show_main_menu()
    elif mode == "dataset":
        show_dataset_analysis()
    elif mode == "scenario_generation":
        show_scenario_generation()
    elif mode == "standard":
        show_standard_simulation()
    elif mode == "step":
        show_step_simulation()
    else:
        show_main_menu()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs the module, so execute immediately.
    main()
