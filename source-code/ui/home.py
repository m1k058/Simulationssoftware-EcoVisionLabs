import streamlit as st
from pathlib import Path
import traceback
from data_manager import DataManager
from config_manager import ConfigManager
from . import set_mode

def load_data_manager() -> bool:
    """Lädt den DataManager und ConfigManager und speichert sie im Session-State.
    
    Returns:
        bool: True wenn erfolgreich geladen, sonst False.
    """
        
    try:
        # config.json is in source-code/, home.py is in source-code/ui/
        config_path = Path(__file__).parent.parent / "config.json"
        cfg = ConfigManager(config_path=config_path)
        dm = DataManager(config_manager=cfg)
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        return True
        
    except Exception as e:
        st.error(f"❌ LOAD DATA -> Fehler beim Laden: {e}")
        print(traceback.format_exc())
        return False

def show_main_menu() -> None:
    st.title("Simulationssoftware EcoVision Labs")

    # DataManager-Status anzeigen
    is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

    st.subheader("Wähle aus, was du machen möchtest:")
    left, middle1, middle2, right = st.columns(4)
    with left:
        st.button(
            "Dataset-Analyse",
            icon="📊",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("dataset",), 
            disabled=not is_loaded,
        )
    with middle1:
        st.button(
            "Szenario Konfiguration",
            icon="🛠️",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("scenario_generation",), 
            disabled=not is_loaded,
        )
    with middle2:
        st.button(
            "Standard Simulation",
            icon="🚀",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("standard",), 
            disabled=not is_loaded,
        )
    with right:
        st.button(
            "Step by Step Simulation",
            icon="⚙️",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("step",), 
            disabled=not is_loaded,
        )
    st.markdown("---")

    st.checkbox("Debug Modus", value=False, key="debug_mode")

    if not is_loaded:
        info_placeholder = st.empty()
        info_placeholder.info("ℹ️ DataManager/ConfigManager ist nicht initialisiert.")
        with st.spinner("Datenmanager/ConfigManager laden..."):
            success = load_data_manager()
        info_placeholder.empty()
        if success:
            # Sofort neu rendern, damit die Buttons freigeschaltet werden
            st.success("✅ DataManager erfolgreich geladen. Buttons werden freigeschaltet…")
            st.rerun()
        else:
            st.error("❌ Laden fehlgeschlagen. Siehe Log/Console für Details.")
    elif is_loaded and st.session_state.debug_mode:
        # Wenn geladen: Datasets anzeigen
        with st.expander("ℹ️ Geladene Datasets", expanded=False):
            try:
                datasets = st.session_state.dm.list_datasets()
                if datasets:
                    for i, ds in enumerate(datasets, start=1):
                        st.write(f"**{i}. {ds['Name']}** (ID: {ds['ID']}) - {ds['Rows']} Zeilen")
                else:
                    st.write("Keine Datasets geladen")
            except Exception as e:
                st.warning(f"Konnte Datasets nicht abrufen: {e}")
