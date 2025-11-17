import streamlit as st
import pandas as pd
import data_processing.simulation as sim
from data_manager import DataManager
from config_manager import ConfigManager
from pathlib import Path

# Session-state initialisieren (persistente Objekte über Reruns)
if "dm" not in st.session_state:
    st.session_state.dm = None
if "cfg" not in st.session_state:
    st.session_state.cfg = None

# --- Navigation helpers ---
def set_mode(new_mode: str) -> None:
    st.session_state.mode = new_mode


def show_main_menu() -> None:
    st.title("Simulationssoftware EcoVision Labs")
    st.subheader("Wähle aus, was du machen möchtest:")
    left, middle, right = st.columns(3)
    with left:
        st.button(
            "Dataset-Analyse",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("dataset",),
        )
    with middle:
        st.button(
            "Eigene Simulation",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("custom",),
        )
    with right:
        st.button(
            "Standard Simulation",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("standard",),
        )


def show_dataset_analysis() -> None:
    st.title("Dataset-Analyse")
    st.caption("Analysiere und visualisiere vorhandene Datensätze.")

    sidebar = st.sidebar
    sidebar.title("Einstellungen")

    if st.session_state.dm is None or st.session_state.cfg is None:
        sidebar.warning("DataManager/ConfigManager ist nicht initialisiert.")
        sidebar.button(
            "Datenmanager/ConfigManager laden",
            on_click=lambda: load_data_manager(),
            use_container_width=True,
        )
        st.info("Bitte lade zuerst den DataManager über die Seitenleiste.")
    else:
        sidebar.success("DataManager geladen.")
        
        # Debug-Informationen anzeigen
        with st.expander("🐛 Debug Informationen", expanded=False):
            st.write("**DataManager Infos:**")
            st.write(f"- Anzahl geladener DataFrames: {len(st.session_state.dm.dataframes)}")
            st.write(f"- DataFrame IDs: {list(st.session_state.dm.dataframes.keys())}")
            
            st.write("\n**Metadata:**")
            for ds_id, meta in st.session_state.dm.metadata.items():
                st.write(f"ID {ds_id}: {meta}")
            
            st.write("\n**Config Dataframes:**")
            for df_cfg in st.session_state.cfg.get_dataframes():
                st.write(f"- ID {df_cfg['id']}: {df_cfg['name']}")
                st.write(f"  Path: {df_cfg['path']}")
                st.write(f"  Exists: {df_cfg['path'].exists()}")
        
        # Liste verfügbarer Datasets anzeigen
        datasets = st.session_state.dm.list_datasets()
        
        if not datasets:
            st.warning("Keine Datasets verfügbar.")
            st.info("Prüfe die Debug-Informationen oben, um zu sehen, warum keine Datasets geladen wurden.")
        else:
            # Dataset-Auswahl
            dataset_options = {f"{ds['Name']} (ID: {ds['ID']})": ds['ID'] for ds in datasets}
            selected_dataset_name = sidebar.selectbox(
                "Wähle einen Dataset",
                options=list(dataset_options.keys())
            )
            selected_dataset_id = dataset_options[selected_dataset_name]
            
            # Zeige Dataset-Info
            selected_info = next(ds for ds in datasets if ds['ID'] == selected_dataset_id)
            st.info(f"**Dataset:** {selected_info['Name']} | **Zeilen:** {selected_info['Rows']} | **Typ:** {selected_info['Datatype']}")
            
            # Data Editor anzeigen
            edited_df = st.data_editor(
                st.session_state.dm.get(selected_dataset_id), 
                num_rows="dynamic",
                use_container_width=True
            )
    
    st.button("Zurück", on_click=set_mode, args=("main",))


def show_custom_simulation() -> None:
    st.title("Eigene Simulation")
    st.caption("Führe eine Simulation mit benutzerdefinierten Parametern durch.")

    sidebar = st.sidebar
    sidebar.title("Simulationseinstellungen")
    if sidebar.button("← Zurück zum Menü", use_container_width=True):
        set_mode("main")

    jahr_von = sidebar.number_input("Simulationsjahr von", min_value=2026, max_value=2050, value=2031)
    jahr_bis = sidebar.number_input("Simulationsjahr bis", min_value=2026, max_value=2050, value=2045)
    referenz_jahr = sidebar.number_input("Referenzjahr aus SMARD Daten", min_value=2020, max_value=2025, value=2023)
    studie_optionen = [
        "Agora",
        "BDI - Klimapfade 2.0",
        "dena - KN100",
        "BMWK - LFS TN-Strom",
        "Ariadne - REMIND-Mix",
        "Ariadne - REMod-Mix",
        "Ariadne - TIMES PanEU-Mix",
    ]
    studie_auswahl = sidebar.selectbox("Wähle eine Studie", studie_optionen)

    if st.button("Simulation starten", type="primary"):
        st.write("Simulation wird durchgeführt...")
        # Beispiel: Hier würde die Simulationsfunktion aufgerufen werden
        st.success(
            f"Simulation abgeschlossen für den Zeitraum :blue[***{jahr_von}***] bis :blue[***{jahr_bis}***] "
            f"mit Referenzjahr :blue[***{referenz_jahr}***] und Studie :green[***{studie_auswahl}***]."
        )


def show_standard_simulation() -> None:
    st.title("Standard Simulation")
    st.caption("Starte eine Simulation mit Standardparametern.")

    sidebar = st.sidebar
    sidebar.title("Schnellstart")
    if sidebar.button("← Zurück zum Menü", use_container_width=True):
        set_mode("main")

    # Feste (beispielhafte) Standardwerte
    jahr_von = 2030
    jahr_bis = 2040
    referenz_jahr = 2023
    studie_auswahl = "Agora"

    st.info(
        f"Es werden Standardwerte verwendet: Zeitraum {jahr_von}-{jahr_bis}, "
        f"Referenzjahr {referenz_jahr}, Studie {studie_auswahl}."
    )
    if st.button("Standard-Simulation starten", type="primary"):
        st.write("Standardsimulation wird durchgeführt...")
        # Beispiel: Hier würde die Standard-Simulationsfunktion aufgerufen werden
        st.success(
            f"Standard-Simulation abgeschlossen für {jahr_von}-{jahr_bis} (Ref {referenz_jahr}) – Studie {studie_auswahl}."
        )

def load_data_manager() -> None:
    try:
        # Get the project root (parent of source-code)
        project_root = Path(__file__).parent.parent
        cfg_path = Path(__file__).parent / "config.json"
        
        st.info(f"📂 Project Root: {project_root}")
        st.info(f"📄 Config Path: {cfg_path}")
        
        cfg = ConfigManager(cfg_path)
        
        # Resolve relative paths in config to absolute paths from project root
        for df_cfg in cfg.config.get("DATAFRAMES", []):
            if "path" in df_cfg and not df_cfg["path"].is_absolute():
                original_path = df_cfg["path"]
                df_cfg["path"] = project_root / df_cfg["path"]
                st.write(f"Resolved: {original_path} → {df_cfg['path']}")
        
        dm = DataManager(config_manager=cfg)
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        
        # Zeige Lade-Ergebnisse
        datasets = dm.list_datasets()
        if datasets:
            st.success(f"✅ DataManager erfolgreich geladen. {len(datasets)} Datasets verfügbar.")
        else:
            st.warning("⚠️ DataManager geladen, aber keine Datasets wurden geladen. Prüfe die Pfade!")
            
    except Exception as e:
        st.error(f"❌ Fehler beim Laden des DataManagers: {e}")
        import traceback
        st.code(traceback.format_exc())
        return


# --- App entrypoint ---
if "mode" not in st.session_state:
    st.session_state.mode = "main"

mode = st.session_state.mode

if mode == "main":
    show_main_menu()
elif mode == "dataset":
    show_dataset_analysis()
elif mode == "custom":
    show_custom_simulation()
elif mode == "standard":
    show_standard_simulation()
else:
    show_main_menu()
