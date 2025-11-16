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
    sidebar.segmented_control("Bitte Wählen", ["Verbrauch", "Erzeugung"], key="dataset_mode", default="Erzeugung")

    dm = st.session_state.get("dm")
    cfg = st.session_state.get("cfg")

    if dm is None or cfg is None:
        sidebar.warning("DataManager/ConfigManager ist nicht initialisiert.")
        sidebar.button(
            "Datenmanager/ConfigManager laden",
            on_click=lambda: load_data_manager(),
            use_container_width=True,
        )
    else:
        sidebar.success("DataManager geladen.")
    
    st.session_state.dm
    edited_df = st.data_editor(st.session_state.dm.get(1), num_rows="dynamic")
    
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
        cfg_path = Path(__file__).parent / "config.json"
        cfg = ConfigManager(cfg_path)
        dm = DataManager(config_manager=cfg)
        dm.load_from_config()
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        st.success("DataManager erfolgreich geladen.")
    except Exception as e:
        st.error(f"Fehler beim Laden des DataManagers: {e}")
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
