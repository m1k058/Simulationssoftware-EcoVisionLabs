import streamlit as st
from pathlib import Path
import traceback
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager


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
        sm = ScenarioManager()
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        st.session_state.sm = sm
        return True
        
    except Exception as e:
        st.error(f"❌ LOAD DATA -> Fehler beim Laden: {e}")
        print(traceback.format_exc())
        return False


def home_page() -> None:
    """Home-Page - Willkommen und Datenverwaltung."""
    st.title("Simulationssoftware EcoVision Labs")
    st.logo("assets/logo.png", size="large")

    # DataManager-Status anzeigen
    is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

    st.subheader("Willkommen! ")
    st.write("Nutze die Navigation in der Seitenleiste oder die Buttons unten, um zu den verschiedenen Funktionen zu gelangen.")


    # Navigation zu den Hauptseiten
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Main Simulation", use_container_width=True, icon=":material/table_chart_view:"):
            st.switch_page(st.session_state.pages["simulation"])
    
    with col2:
        if st.button("Szenario Konfiguration", use_container_width=True, icon=":material/tune:"):
            st.switch_page(st.session_state.pages["scenario"])
    
    with col3:
        if st.button("Daten Analyse", use_container_width=True, icon=":material/area_chart:"):
            st.switch_page(st.session_state.pages["analysis"])

    st.markdown("---")
    st.subheader("Status:")
    
    if is_loaded:
        st.success(":material/check: DataManager, ConfigManager, ScenarioManager sind geladen.")
    else:
        st.info(":material/info: DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")

    st.checkbox(":material/bug_report: Debug Modus", value=False, key="debug_mode")

    if not is_loaded:
        if st.button(":material/drive_folder_upload: Daten laden", use_container_width=True, type="primary"):
            with st.spinner("Datenmanager/ConfigManager/ScenarioManager laden..."):
                success = load_data_manager()
            if success:
                st.success("✅ DataManager, ConfigManager, ScenarioManager erfolgreich geladen!")
                st.rerun()
            else:
                st.error("❌ Laden fehlgeschlagen. Siehe Log/Console für Details.")
    elif is_loaded and st.session_state.debug_mode:
        # Wenn geladen: Datasets anzeigen
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


