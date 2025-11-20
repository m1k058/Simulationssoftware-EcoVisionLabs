import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import data_processing.simulation as sim
from data_manager import DataManager
from config_manager import ConfigManager
from pathlib import Path
import os
import sys
import time
from io import StringIO
import plotting_formated_st as pltf
import plotting_plotly_st as pltp
from constants import ENERGY_SOURCES


# Session-state initialisieren (persistente Objekte über Reruns)
if "dm" not in st.session_state:
    st.session_state.dm = None
if "cfg" not in st.session_state:
    st.session_state.cfg = None
if "load_log" not in st.session_state:
    st.session_state.load_log = ""

# --- Navigation helpers ---
def set_mode(new_mode: str) -> None:
    st.session_state.mode = new_mode


def show_main_menu() -> None:
    st.title("Simulationssoftware EcoVision Labs")

    # DataManager-Status anzeigen
    is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

    st.subheader("Wähle aus, was du machen möchtest:")
    left, middle, right = st.columns(3)
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
    with middle:
        st.button(
            "Eigene Simulation",
            icon="⚙️",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("custom",), 
            disabled=not is_loaded,
        )
    with right:
        st.button(
            "Standard Simulation",
            icon="🚀",
            type="primary",
            use_container_width=True,
            on_click=set_mode,
            args=("standard",), 
            disabled=not is_loaded,
        )
    st.markdown("---")
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
    else:
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
    
    


def show_dataset_analysis() -> None:
    st.title("Dataset-Analyse")
    st.caption("Analysiere und visualisiere vorhandene Datensätze.")

    if st.session_state.dm is None or st.session_state.cfg is None:
        st.warning("DataManager/ConfigManager ist nicht initialisiert.")

    sidebar = st.sidebar
    sidebar.title("Einstellungen")
    selected_dataset_name = sidebar.selectbox("Wähle ein Dataframe", options=st.session_state.dm.list_dataset_names())
    df = st.session_state.dm.get(selected_dataset_name)
    df_id = st.session_state.dm.get_dataset_id(selected_dataset_name)
    datentyp = st.session_state.dm.metadata[df_id]["datatype"]

    sidebar.write(f"**Datentyp:** {datentyp}")
    # sidebar.write(f"**Zeitspanne verfügbar:** {df['Zeitpunkt'].min()} - {df['Zeitpunkt'].max()}")
    
    if datentyp == "SMARD":
        sidebar.markdown(
        "**Im Dataframe:** :green-badge[:material/trending_up: Erzeugungs Daten]"
        )
    elif datentyp == "SMARD-V":
        sidebar.markdown(
        "**Im Dataframe:** :red-badge[:material/trending_down: Verbrauchs Daten]"
        )
    elif datentyp == "CUST_PROG":
        sidebar.markdown(
        "**Im Dataframe:**  \n:green-badge[:material/trending_up: Erzeugungs Daten] :red-badge[:material/trending_down: Verbrauchs Daten]"
        )
    else:
        sidebar.write("**Im Dataframe:**")
        sidebar.warning("Unbekannter Datentyp. Möglicherweise nicht vollständig unterstützt.")

    

    sidebar.markdown("---\n ***Zeitraum auswählen***")

    # Verfügbarer Zeitraum im Dataset ermitteln
    try:
        min_date = pd.to_datetime(df["Zeitpunkt"].min())
        max_date = pd.to_datetime(df["Zeitpunkt"].max())
    except Exception as e:
        st.error(f"In diesem Dataframe gibt es keine: {e} und kann deshalb derzeit nicht analysiert werden.\nKontaktiere das Entwicklerteam um das Feature vorzuschlagen.")
        st.button("Zurück", on_click=set_mode, args=("main",))
        return
    
    sidebar.checkbox("Uhrzeit mit angeben", value=False, key="set_time")

    # Datum von
    if not st.session_state.set_time:
        selected_date_from = sidebar.date_input("Datum von", value=min_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
    else:
        left, right = sidebar.columns(2)
        selected_date_from = left.date_input("Datum von", value=min_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
        selected_time_from = right.time_input("Uhrzeit von", value=pd.to_datetime("00:00").time())

    maxplot_date = pd.to_datetime(min_date)+ pd.Timedelta(days=1)
    # Datum bis
    min_date = pd.to_datetime(selected_date_from)
    if not st.session_state.set_time:
        selected_date_to = sidebar.date_input("Datum bis", value=maxplot_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
    else:
        left, right = sidebar.columns(2)
        selected_date_to = left.date_input("Datum bis", value=maxplot_date,
                                            format="DD.MM.YYYY", min_value=min_date,
                                            max_value=max_date)
        selected_time_to = right.time_input("Uhrzeit bis", value=pd.to_datetime("23:59").time())

    
    # Filter DataFrame nach ausgewähltem Zeitraum
    df_filtered = df[
        (pd.to_datetime(df["Zeitpunkt"]) >= pd.to_datetime(selected_date_from)) &
        (pd.to_datetime(df["Zeitpunkt"]) <= pd.to_datetime(selected_date_to))
    ]
    date_diff = pd.to_datetime(selected_date_to) - pd.to_datetime(selected_date_from)
    plot_engine = st.selectbox("Wähle eine Plot Engine", options=["Altair", "Plotly", "Matplotlib", "streamlit-echarts"])
    
    if datentyp == "SMARD":
        # Optionen & Default aus Konstanten ableiten
        _energy_options = [src["colname"] for src in ENERGY_SOURCES.values()]
        _default_selection = [ENERGY_SOURCES["BIO"]["colname"], ENERGY_SOURCES["PV"]["colname"]]
        energiequellen = st.multiselect(
            "Energiequellen auswählen",
            options=_energy_options,
            default=_default_selection,
        )

        # Mapping für spätere Umwandlung der Auswahl in Shortcodes
        colname_to_code = {v["colname"]: k for k, v in ENERGY_SOURCES.items()}

        if plot_engine == "Altair" and (date_diff <= pd.Timedelta(days=7)):
            if not energiequellen:
                st.info("Bitte mindestens eine Energiequelle auswählen.")
            else:
                # Farben passend zur Auswahl aus Konstanten ziehen
                colors = [ENERGY_SOURCES[colname_to_code[c]]["color"] for c in energiequellen]
                st.line_chart(
                    df_filtered,
                    x="Zeitpunkt",
                    y=energiequellen,
                    color=colors,
                    x_label="Datum",
                    y_label="MWh",
                )
        elif plot_engine == "Altair" and (date_diff > pd.Timedelta(days=7)):
            st.warning("⚠️ Altair unterstützt nur Zeiträume bis zu 7 Tagen da der Ressourcenverbrauch sonst zu hoch ist.\n\nBitte wähle einen kürzeren Zeitraum oder eine andere Plot Engine (empfohlen: Plotly).")

        elif plot_engine == "Plotly":
            # Nutze die Auswahl für den Plot (Shortcodes ableiten)
            energy_keys = [colname_to_code[c] for c in energiequellen] if energiequellen else ["BIO", "WON"]
            fig = pltp.create_stacked_bar_plot(
                df_filtered,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                description="Stacked Bar Plot der Energieerzeugung",
                darkmode=False,
            )
            st.plotly_chart(fig)
        
        elif plot_engine == "Matplotlib":
            energy_keys = [colname_to_code[c] for c in energiequellen] if energiequellen else ["BIO", "WON"]
            fig = pltf.create_stacked_bar_plot(
                df_filtered,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                description="Stacked Bar Plot der Energieerzeugung",
                darkmode=False,
            )
            st.pyplot(fig)


        else:
            st.error("Unbekannte Plot Engine ausgewählt.")
        st.button("Zurück", on_click=set_mode, args=("main",))
    
    elif datentyp == "SMARD-V":
        st.info("Verbrauchs-Daten können derzeit nur mit Matplotlib geplottet werden.")
        plot_engine = "Matplotlib"

        if plot_engine == "Matplotlib":
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(pd.to_datetime(df_filtered["Zeitpunkt"]), df_filtered["Netzlast [MWh]"], color="blue", label="Netzlast (MWh)")
            ax.set_title("Netzlast über die Zeit")
            ax.set_xlabel("Datum")
            ax.set_ylabel("Netzlast (MWh)")
            ax.legend()
            ax.fill_between(pd.to_datetime(df_filtered["Zeitpunkt"]), df_filtered["Netzlast [MWh]"], color="blue", alpha=0.3)
            ax.set_ylim(bottom=0) 
            st.pyplot(fig)
        st.button("Zurück", on_click=set_mode, args=("main",))
    
    else:
        st.warning("Derzeit werden nur SMARD Erzeugungs- und Verbrauchs-Daten unterstützt.")
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

def load_data_manager() -> bool:
    """Lädt den DataManager und ConfigManager und speichert sie im Session-State.
    
    Returns:
        bool: True wenn erfolgreich geladen, sonst False.
    """
        
    try:
        
        cfg = ConfigManager(Path("config.json"))
        dm = DataManager(config_manager=cfg)
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        return True
        
    except Exception as e:
        st.error(f"❌ Fehler beim Laden: {e}")
        import traceback
        print(traceback.format_exc())
        return False


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
