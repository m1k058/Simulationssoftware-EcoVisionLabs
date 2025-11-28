import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import data_processing.simulation as sim
import data_processing.gen as gen
import data_processing.col as col
from data_manager import DataManager
from config_manager import ConfigManager
from pathlib import Path
import os
import sys
import time
from io import StringIO
import plotting.plotting_formated_st as pltf
import plotting.plotting_plotly_st as pltp
from constants import ENERGY_SOURCES
from data_processing import col, gen
import math

st.set_page_config(
    layout="wide", # Standard ist "centered"
    initial_sidebar_state="expanded",
    page_title="EcoVision Labs Simu",
    page_icon=":chart_with_upwards_trend:", # Emoji oder URL
)

# Session-state initialisieren (persistente Objekte über Reruns)
if "dm" not in st.session_state:
    st.session_state.dm = None
if "cfg" not in st.session_state:
    st.session_state.cfg = None
if "load_log" not in st.session_state:
    st.session_state.load_log = ""
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

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
        selected_date_from = pd.to_datetime(selected_date_from).replace(hour=0, minute=0, second=0, microsecond=0) # Uhrzeit auf 00:00 setzen
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
        selected_date_to = pd.to_datetime(selected_date_to).replace(hour=23, minute=59, second=59, microsecond=999999) # Uhrzeit auf 23:59 setzen
    else:
        left, right = sidebar.columns(2)
        selected_date_to = left.date_input("Datum bis", value=maxplot_date,
                                            format="DD.MM.YYYY", min_value=min_date,
                                            max_value=max_date)
        selected_time_to = right.time_input("Uhrzeit bis", value=pd.to_datetime("23:59").time())

    # Kombiniere Datum und Uhrzeit wenn gesetzt
    if st.session_state.set_time:
        selected_date_from = pd.to_datetime(f"{selected_date_from} {selected_time_from}")
        selected_date_to = pd.to_datetime(f"{selected_date_to} {selected_time_to}")
    
    # Filter DataFrame nach ausgewähltem Zeitraum
    df_filtered = df[
        (pd.to_datetime(df["Zeitpunkt"]) >= pd.to_datetime(selected_date_from)) &
        (pd.to_datetime(df["Zeitpunkt"]) <= pd.to_datetime(selected_date_to))
    ]
    date_diff = pd.to_datetime(selected_date_to) - pd.to_datetime(selected_date_from)
    plot_engine = st.selectbox("Wähle eine Plot Engine", options=["Altair", "Plotly", "Matplotlib"], index=1)
    
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

        if plot_engine == "Altair" and (date_diff <= pd.Timedelta(days=14)):
            st.warning("⚠️ Altair kann  nur einzelne linien und nicht stacks darstellen.")
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
        elif plot_engine == "Altair" and (date_diff > pd.Timedelta(days=14)):
            st.warning("⚠️ Altair kann  nur einzelne linien und nicht stacks darstellen.")
            st.warning("⚠️ Altair unterstützt nur Zeiträume bis zu 14 Tagen da der Ressourcenverbrauch sonst zu hoch ist.\n" +
            "\nBitte wähle einen kürzeren Zeitraum oder eine andere Plot Engine (empfohlen: Plotly).")

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
        # st.info("Verbrauchs-Daten können derzeit nur mit Matplotlib geplottet werden.")
        # plot_engine = "Matplotlib"

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
        
        elif plot_engine == "Plotly":
            fig = pltp.create_line_plot(
                df_filtered,
                y_axis="Netzlast [MWh]",
                title="Netzlast über die Zeit",
                description="Line Plot der Netzlast",
                darkmode=False,
            )
            st.plotly_chart(fig)
        
        elif plot_engine == "Altair":
            st.line_chart(
                df_filtered,
                x="Zeitpunkt",
                y="Netzlast [MWh]",
                x_label="Datum",
                y_label="MWh",
            )
        
        else:
            st.error("Unbekannte Plot Engine ausgewählt.")

        st.button("Zurück", on_click=set_mode, args=("main",))
    
    else:
        st.warning("Derzeit werden nur SMARD Erzeugungs- und Verbrauchs-Daten unterstützt.")
        st.button("Zurück", on_click=set_mode, args=("main",))


def show_standard_simulation() -> None:
    st.title("Simulation")
    st.caption("Werde schrittweise durch die Simulation geführt.")
    st.warning("🏗️ WARNUNG: Diese Funktion ist noch in der Entwicklung und dient nur Demonstrationszwecken.")
    sidebar = st.sidebar
    sidebar.title("Simulationseinstellungen")

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
        st.success(
            f"Simulation abgeschlossen für den Zeitraum :blue[***{jahr_von}***] bis :blue[***{jahr_bis}***] "
            f"mit Referenzjahr :blue[***{referenz_jahr}***] und Studie :green[***{studie_auswahl}***]."
        )
    st.button("Zurück", on_click=set_mode, args=("main",))


def set_step(step_index: int) -> None:
    """Setzt den aktuellen Simulationsschritt."""
    st.session_state.step_index = step_index


def show_step_simulation() -> None:
    st.title("Step by Step Simulation")
    st.caption("Werde schrittweise durch die Simulation geführt.")
    st.markdown("---")
    # st.warning("🏗️ WARNUNG: Diese Funktion ist noch in der Entwicklung.")

    # Initialisiere step_index im session_state falls noch nicht vorhanden
    if "step_index" not in st.session_state:
        st.session_state.step_index = 0
    
    # Initialisiere Validierungsstatus für jeden Schritt
    if "step_valid" not in st.session_state:
        st.session_state.step_valid = True
    
    # Initialisiere Simulationsdaten im Session State
    if "sim_datei_verbrauch" not in st.session_state:
        st.session_state.sim_datei_verbrauch = None
    if "sim_datei_erzeugung" not in st.session_state:
        st.session_state.sim_datei_erzeugung = None
    if "sim_studie_verbrauch" not in st.session_state:
        st.session_state.sim_studie_verbrauch = None
    if "sim_studie_erzeugung" not in st.session_state:
        st.session_state.sim_studie_erzeugung = None
    if "sim_jahr" not in st.session_state:
        st.session_state.sim_jahr = 2030
    if "sim_referenz_jahr" not in st.session_state:
        st.session_state.sim_referenz_jahr = 2023
    if "sim_verbrauch_lastprofile" not in st.session_state:
        st.session_state.sim_verbrauch_lastprofile = False
    if "df_simulation_con" not in st.session_state:
        st.session_state.df_simulation_con = None
    if "df_simulation_prod" not in st.session_state:
        st.session_state.df_simulation_prod = None
    if "energie_bilanz" not in st.session_state:
        st.session_state.energie_bilanz = None

    aktiver_schritt_index = st.session_state.step_index

    sidebar = st.sidebar
    sidebar.title("Simulationsfortschritt")
    sidebar.markdown(render_checklist(aktiver_schritt_index), unsafe_allow_html=True)

    # Zugelassene Datein:
    zugelassene_dateien_verbrauch = [
        "SMARD_2015-2020_Verbrauch",
        "SMARD_2020-2025_Verbrauch"
    ]
    zugelassene_dateien_erzeugung = [
        "SMARD_2015-2020_Erzeugung",
        "SMARD_2020-2025_Erzeugung"
    ]

    # Zugelassene Studien:
    studie_optionen = [
        "Agora",
        "BDI - Klimapfade 2.0",
        "dena - KN100",
        "BMWK - LFS TN-Strom",
        "Ariadne - REMIND-Mix",
        "Ariadne - REMod-Mix",
        "Ariadne - TIMES PanEU-Mix",
    ]

    def daten_auswaehlen():
        st.header("1. Daten auswählen:")

        is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

        if is_loaded:
            st.write("Wähle die Daten für die Simulation aus.")
            
            # Reset Validierung zu Beginn
            st.session_state.step_valid = True
            
            # Finde Index der vorher ausgewählten Verbrauchsdatei
            dataset_names = st.session_state.dm.list_dataset_names()
            verbrauch_index = 2
            if st.session_state.sim_datei_verbrauch in dataset_names:
                verbrauch_index = dataset_names.index(st.session_state.sim_datei_verbrauch)
            
            st.session_state.sim_datei_verbrauch = st.selectbox(
                "Verbrauchdatei auswählen", 
                options=dataset_names, 
                index=verbrauch_index,
                key="selectbox_verbrauch"
            )
            if st.session_state.sim_datei_verbrauch not in zugelassene_dateien_verbrauch:
                st.warning("⚠️ Diese Datei ist keine Verbrauchsdatei aus SMARD.")
                st.session_state.step_valid = False
            
            # Finde Index der vorher ausgewählten Erzeugungsdatei
            erzeugung_index = 1
            if st.session_state.sim_datei_erzeugung in dataset_names:
                erzeugung_index = dataset_names.index(st.session_state.sim_datei_erzeugung)
            
            st.session_state.sim_datei_erzeugung = st.selectbox(
                "Erzeugungsdatei auswählen", 
                options=dataset_names, 
                index=erzeugung_index,
                key="selectbox_erzeugung"
            )
            if st.session_state.sim_datei_erzeugung not in zugelassene_dateien_erzeugung:
                st.warning("⚠️ Diese Datei ist keine Erzeugungsdatei aus SMARD.")
                st.session_state.step_valid = False
            
            # Jahresauswahl basierend auf verfügbaren Daten
            if st.session_state.step_valid:
                try:
                    # Lade beide DataFrames
                    df_verbrauch = st.session_state.dm.get(st.session_state.sim_datei_verbrauch)
                    df_erzeugung = st.session_state.dm.get(st.session_state.sim_datei_erzeugung)
                    
                    # Extrahiere verfügbare Jahre aus beiden Datasets
                    jahre_verbrauch = set(pd.to_datetime(df_verbrauch["Zeitpunkt"]).dt.year.unique())
                    jahre_erzeugung = set(pd.to_datetime(df_erzeugung["Zeitpunkt"]).dt.year.unique())
                    
                    # Nur Jahre die in beiden vorhanden sind
                    verfuegbare_jahre = sorted(jahre_verbrauch & jahre_erzeugung)
                    
                    if verfuegbare_jahre:
                        # Finde Index des vorher ausgewählten Referenzjahres
                        ref_index = len(verfuegbare_jahre) - 1
                        if st.session_state.sim_referenz_jahr in verfuegbare_jahre:
                            ref_index = verfuegbare_jahre.index(st.session_state.sim_referenz_jahr)
                        
                        st.session_state.sim_referenz_jahr = st.selectbox(
                            "Referenzjahr auswählen", 
                            options=verfuegbare_jahre,
                            index=ref_index,
                            key="selectbox_referenzjahr"
                        )
                        st.info(f"ℹ️ Verfügbare Jahre: {min(verfuegbare_jahre)} - {max(verfuegbare_jahre)}")
                    else:
                        st.error("❌ Keine übereinstimmenden Jahre in beiden Datensätzen gefunden.")
                        st.session_state.step_valid = False
                        
                except Exception as e:
                    st.error(f"❌ Fehler beim Ermitteln verfügbarer Jahre: {e}")
                    st.session_state.step_valid = False
            
            # Simulationsjahr auswählen (2026-2050)
            simjahre = list(range(2026, 2051))
            sim_index = simjahre.index(st.session_state.sim_jahr) if st.session_state.sim_jahr in simjahre else 4
            
            st.session_state.sim_jahr = st.selectbox(
                "Simulationsjahr", 
                options=simjahre,
                index=sim_index,
                key="selectbox_simjahr"
            )
            
            if st.session_state.step_valid:
                st.success("✅ Alle Eingaben sind korrekt")
    
        else:
            st.warning("DataManager/ConfigManager ist nicht initialisiert. " \
            "Bitte lade die Daten und Konfiguration zuerst im Hauptmenü.")
            st.session_state.step_valid = False

    def verbrauch_simulieren():
            
        st.header("2. Verbrauch Simulieren:")

        # Finde Index der vorher ausgewählten Studie
        studie_index = 0
        if st.session_state.sim_studie_verbrauch in studie_optionen:
            studie_index = studie_optionen.index(st.session_state.sim_studie_verbrauch)
        
        st.session_state.sim_studie_verbrauch = st.selectbox(
            "Studie der Verbrauchsprognose auswählen", 
            options=studie_optionen, 
            index=studie_index,
            key="selectbox_studie_verbrauch"
        )
        st.session_state.sim_verbrauch_lastprofile = st.checkbox(
            "Verwende Verbrauchs-Lastprofile für Skalierung :orange[[EXPERIMENTELL]]", 
            value=st.session_state.sim_verbrauch_lastprofile,
            key="checkbox_lastprofile"
        )

        # Run Button für die Simulation
        if st.button("Simulation starten", type="primary", use_container_width=True):
            if st.session_state.sim_datei_verbrauch:
                with st.spinner("Simulation läuft..."):
                    try:
                        st.session_state.df_simulation_con = sim.calc_scaled_consumption(
                            st.session_state.dm.get(st.session_state.dm.get_dataset_id(st.session_state.sim_datei_verbrauch)),
                            st.session_state.dm.get("Erzeugungs/Verbrauchs Prognose Daten"), 
                            st.session_state.sim_studie_verbrauch, 
                            st.session_state.sim_jahr, 
                            st.session_state.sim_jahr,
                            st.session_state.sim_referenz_jahr,
                            use_load_profile=st.session_state.sim_verbrauch_lastprofile)
                        st.success("✅ Verbrauchssimulation abgeschlossen")
                        st.session_state.step_valid = True
                    except Exception as e:
                        st.error(f"❌ Fehler bei der Simulation: {e}")
                        st.session_state.step_valid = False
            else:
                st.error("❌ Keine Verbrauchsdatei ausgewählt. Gehe zurück zu Schritt 1.")
                st.session_state.step_valid = False
        
        # Zeige Plot wenn Simulation abgeschlossen
        if st.session_state.df_simulation_con is not None and len(st.session_state.df_simulation_con) > 0:
            st.markdown("---")
            st.subheader(":chart_with_upwards_trend: Simulationsergebnis")
            
            # Filtere auf zwei Standardwochen: Winterwoche (13. Feb) und Sommerwoche (3. Juli)
            try:
                df_full = st.session_state.df_simulation_con.copy()
                
                # Winterwoche: 13. Feb (KW 7) - 7 Tage ab 13. Feb
                winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
                winter_end = winter_start + pd.Timedelta(days=7)
                
                # Sommerwoche: 3. Juli (KW 27) - 7 Tage ab 3. Juli
                summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
                summer_end = summer_start + pd.Timedelta(days=7)
                
                # Filtere DataFrame
                df_winter = df_full[
                    (pd.to_datetime(df_full["Zeitpunkt"]) >= winter_start) & 
                    (pd.to_datetime(df_full["Zeitpunkt"]) < winter_end)
                ]
                df_summer = df_full[
                    (pd.to_datetime(df_full["Zeitpunkt"]) >= summer_start) & 
                    (pd.to_datetime(df_full["Zeitpunkt"]) < summer_end)
                ]
                
                # Kombiniere beide Wochen
                df_zwei_wochen = pd.concat([df_winter, df_summer], ignore_index=True)
                
                if len(df_zwei_wochen) == 0:
                    st.warning("⚠️ Keine Daten für die Standardwochen gefunden.")
                    df_plot = df_full
                else:
                    df_plot = df_zwei_wochen
                
            except Exception as e:
                st.warning(f"⚠️ Fehler beim Filtern der Wochen: {e}. Zeige alle Daten.")
                df_plot = st.session_state.df_simulation_con
            
            # Plotly Visualisierung
            try:
                # Toggle zwischen Wochenansicht und Jahresansicht
                view_mode = st.segmented_control(
                    label="Ansicht wählen:",
                    options=[
                        "📅 Zwei Wochen (Winter & Sommer)", 
                        "📊 Gesamtes Jahr"
                    ],
                    key="verbrauch_view_mode",
                    default="📅 Zwei Wochen (Winter & Sommer)"
                )
                
                if view_mode == "📅 Zwei Wochen (Winter & Sommer)":
                    # Separiere Winter- und Sommerwoche für separate Plots
                    df_winter_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 2]
                    df_summer_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 7]
                    
                    # Zwei Spalten für Winter und Sommer
                    col_winter, col_summer = st.columns(2, width="stretch", border=True, gap="small")
                    
                    with col_winter:
                        st.markdown("#### ❄️ Winterwoche (13.-19. Feb)")
                        if len(df_winter_plot) > 0:
                            fig_winter = pltp.create_line_plot(
                                df_winter_plot,
                                y_axis="Skalierte Netzlast [MWh]",
                                title="",
                                description="",
                                darkmode=False,
                            )
                            st.plotly_chart(fig_winter, use_container_width=True)
                        else:
                            st.warning("⚠️ Keine Winterdaten")
                    
                    with col_summer:
                        st.markdown("#### ☀️ Sommerwoche (3.-9. Juli)")
                        if len(df_summer_plot) > 0:
                            fig_summer = pltp.create_line_plot(
                                df_summer_plot,
                                y_axis="Skalierte Netzlast [MWh]",
                                title="",
                                description="",
                                darkmode=False,
                            )
                            st.plotly_chart(fig_summer, use_container_width=True)
                        else:
                            st.warning("⚠️ Keine Sommerdaten")
                    
                    # Statistiken für zwei Wochen
                    df_stats = df_plot
                    
                else:
                    # Verwende vollständige Daten
                    df_full_year = st.session_state.df_simulation_con
                    
                    col1 = st.columns(1, width="stretch", border=True)
                    with col1[0]:
                        st.markdown("### :calendar: Verbrauch über das gesamte Jahr")
                        fig_year = pltp.create_line_plot(
                            df_full_year,
                            y_axis="Skalierte Netzlast [MWh]",
                            title="",
                            description="",
                            darkmode=False,
                        )
                        st.plotly_chart(fig_year, use_container_width=True, width="stretch")
                    
                    # Statistiken für das gesamte Jahr
                    df_stats = df_full_year
                
                # Zusätzliche Statistiken
                col1, col2, col3 = st.columns(3, border=True, gap="small")
                with col1:
                    total_consumption = df_stats["Skalierte Netzlast [MWh]"].sum() / 1_000_000
                    st.metric("Gesamtverbrauch", f"{total_consumption:.2f} TWh")
                with col2:
                    avg_consumption = df_stats["Skalierte Netzlast [MWh]"].mean()
                    st.metric("Durchschn. Verbrauch", f"{avg_consumption:.2f} MWh")
                with col3:
                    max_consumption = df_stats["Skalierte Netzlast [MWh]"].max()
                    st.metric("Spitzenlast", f"{max_consumption:.2f} MWh")
                
                # Validierung: DataFrame ist gefüllt
                st.session_state.step_valid = True
            except Exception as e:
                st.error(f"❌ Fehler bei der Visualisierung: {e}")
                st.session_state.step_valid = False
        else:
            st.session_state.step_valid = False

    def erzeugung_simulieren():
        st.header("3. Erzeugung Simulieren:")
        
        # Finde Index der vorher ausgewählten Studie
        studie_index = 0
        if st.session_state.sim_studie_erzeugung in studie_optionen:
            studie_index = studie_optionen.index(st.session_state.sim_studie_erzeugung)
        
        st.session_state.sim_studie_erzeugung = st.selectbox(
            "Studie der Erzeugungsprognose auswählen", 
            options=studie_optionen, 
            index=studie_index,
            key="selectbox_studie_erzeugung"
        )
        
        # Run Button für die Simulation
        if st.button("🚀 Erzeugung simulieren", type="primary", use_container_width=True):
            if st.session_state.sim_datei_erzeugung:
                with st.spinner("Erzeugungssimulation läuft..."):
                    try:
                        st.session_state.df_simulation_prod = sim.calc_scaled_production(
                            st.session_state.dm.get(st.session_state.dm.get_dataset_id(st.session_state.sim_datei_erzeugung)),
                            st.session_state.dm.get("Erzeugungs/Verbrauchs Prognose Daten"), 
                            st.session_state.sim_studie_erzeugung, 
                            st.session_state.sim_jahr,
                            ref_jahr=st.session_state.sim_referenz_jahr
                        )
                        st.success("✅ Erzeugungssimulation abgeschlossen")
                        st.session_state.step_valid = True
                    except Exception as e:
                        st.error(f"❌ Fehler bei der Erzeugungssimulation: {e}")
                        st.session_state.step_valid = False
            else:
                st.error("❌ Keine Erzeugungsdatei ausgewählt. Gehe zurück zu Schritt 1.")
                st.session_state.step_valid = False
        
        # Zeige Plot wenn Simulation abgeschlossen
        if st.session_state.df_simulation_prod is not None and len(st.session_state.df_simulation_prod) > 0:
            st.markdown("---")
            st.subheader(":chart_with_upwards_trend: Erzeugungssimulation Ergebnis")
            
            # Filtere auf zwei Standardwochen: Winterwoche (13. Feb) und Sommerwoche (3. Juli)
            try:
                df_full = st.session_state.df_simulation_prod.copy()
                
                # Winterwoche: 13. Feb (KW 7) - 7 Tage ab 13. Feb
                winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
                winter_end = winter_start + pd.Timedelta(days=7)
                
                # Sommerwoche: 3. Juli (KW 27) - 7 Tage ab 3. Juli
                summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
                summer_end = summer_start + pd.Timedelta(days=7)
                
                # Filtere DataFrame
                df_winter = df_full[
                    (pd.to_datetime(df_full["Zeitpunkt"]) >= winter_start) & 
                    (pd.to_datetime(df_full["Zeitpunkt"]) < winter_end)
                ]
                df_summer = df_full[
                    (pd.to_datetime(df_full["Zeitpunkt"]) >= summer_start) & 
                    (pd.to_datetime(df_full["Zeitpunkt"]) < summer_end)
                ]
                
                # Kombiniere beide Wochen
                df_zwei_wochen = pd.concat([df_winter, df_summer], ignore_index=True)
                
                if len(df_zwei_wochen) == 0:
                    st.warning("⚠️ Keine Daten für die Standardwochen gefunden.")
                    df_plot = df_full
                else:
                    df_plot = df_zwei_wochen
                
            except Exception as e:
                st.warning(f"⚠️ Fehler beim Filtern der Wochen: {e}. Zeige alle Daten.")
                df_plot = st.session_state.df_simulation_prod
            
            # Plotly Visualisierung - Stacked Bar Plot
            try:
                # Verwende alle verfügbaren Energiequellen
                available_energy_keys = []
                for key, source in ENERGY_SOURCES.items():
                    if source["colname"] in df_plot.columns:
                        available_energy_keys.append(key)
                
                if available_energy_keys:
                    # Separiere Winter- und Sommerwoche für separate Plots
                    df_winter_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 2]
                    df_summer_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 7]
                    
                    # Zwei Spalten für Winter und Sommer
                    col_winter, col_summer = st.columns(2, border=True, gap="small")
                    
                    with col_winter:
                        st.markdown("#### ❄️ Winterwoche (13.-19. Feb)")
                        if len(df_winter_plot) > 0:
                            fig_winter = pltp.create_stacked_bar_plot(
                                df_winter_plot,
                                energy_keys=available_energy_keys,
                                title="",
                                description="",
                                darkmode=False,
                            )
                            st.plotly_chart(fig_winter, use_container_width=True)
                        else:
                            st.warning("⚠️ Keine Winterdaten")
                    
                    with col_summer:
                        st.markdown("#### ☀️ Sommerwoche (3.-9. Juli)")
                        if len(df_summer_plot) > 0:
                            fig_summer = pltp.create_stacked_bar_plot(
                                df_summer_plot,
                                energy_keys=available_energy_keys,
                                title="",
                                description="",
                                darkmode=False,
                            )
                            st.plotly_chart(fig_summer, use_container_width=True)
                        else:
                            st.warning("⚠️ Keine Sommerdaten")
                    
                    # Zusätzliche Statistiken mit Kreisdiagramm
                    st.markdown("### 📈 Statistiken")
                    
                    # Berechne Gesamterzeugung über alle Energiequellen
                    total_production = 0
                    renewable_production = 0
                    
                    for key in available_energy_keys:
                        colname = ENERGY_SOURCES[key]["colname"]
                        if colname in df_plot.columns:
                            production = df_plot[colname].sum()
                            total_production += production
                            # Prüfe ob erneuerbar
                            if key in ["BIO", "WAS", "WOF", "WON", "PV", "SOE"]:
                                renewable_production += production
                    
                    # 2 Spalten: Links Metriken untereinander, Rechts Kreisdiagramm
                    col_metrics, col_pie = st.columns([1, 1], border=True, gap="small")
                    
                    with col_metrics:
                        st.metric("Gesamterzeugung", f"{total_production / 1_000_000:.2f} TWh")
                        st.metric("Durchschn. Erzeugung", f"{total_production / len(df_plot):.2f} MWh")
                        # Finde Spitzenlast über alle Quellen
                        row_sums = df_plot[[ENERGY_SOURCES[k]["colname"] for k in available_energy_keys]].sum(axis=1)
                        st.metric("Spitzenerzeugung", f"{row_sums.max():.2f} MWh")
                    
                    with col_pie:
                        # Kreisdiagramm für Anteil Erneuerbare
                        renewable_percentage = (renewable_production / total_production * 100) if total_production > 0 else 0
                        conventional_percentage = 100 - renewable_percentage
                        
                        import plotly.graph_objects as go
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=['Erneuerbare', 'Konventionelle'],
                            values=[renewable_percentage, conventional_percentage],
                            marker=dict(colors=['#00A51B', '#5D5D5D']),
                            hole=0.4,
                            textinfo='label+percent',
                            textposition='inside'
                        )])
                        fig_pie.update_layout(
                            title="Anteil Erneuerbare",
                            showlegend=False,
                            height=300,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Validierung: DataFrame ist gefüllt
                    st.session_state.step_valid = True
                else:
                    st.warning("⚠️ Keine bekannten Energiequellen im Ergebnis gefunden.")
                    st.session_state.step_valid = False
                    
            except Exception as e:
                st.error(f"❌ Fehler bei der Visualisierung: {e}")
                st.session_state.step_valid = False
        else:
            st.session_state.step_valid = False

    def defizite_anzeigen():
        st.header("4. Defizite anzeigen:")

        # Vorbedingungen prüfen
        if (
            st.session_state.df_simulation_con is None
            or st.session_state.df_simulation_prod is None
            or len(st.session_state.df_simulation_con) == 0
            or len(st.session_state.df_simulation_prod) == 0
        ):
            st.warning("⚠️ Verbrauchs- oder Erzeugungsdaten fehlen. Bitte zuerst Schritte 2 und 3 ausführen.")
            st.session_state.step_valid = False
            return

        try:
            # Gesamterzeugung hinzufügen
            energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
            # Verbrauch hinzufügen
            energie_bilanz = col.add_column_from_other_df(
                energie_bilanz,
                st.session_state.df_simulation_con,
                "Skalierte Netzlast [MWh]",
                "Skalierte Netzlast [MWh]",
            )
            # Speichere im Session State
            st.session_state.energie_bilanz = energie_bilanz
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {e}")
            st.session_state.step_valid = False
            return

        # Toggle für Ansicht
        view_mode = st.segmented_control(
            label="Zeitraum:",
            options=["📅 Zwei Wochen (Winter & Sommer)", "📊 Gesamtes Jahr"],
            key="bilanz_view_mode",
            default="📅 Zwei Wochen (Winter & Sommer)"
        )

        stats_df = energie_bilanz  # Default für Jahresansicht

        if view_mode == "📅 Zwei Wochen (Winter & Sommer)":
            # Zeiträume definieren (gleiche Definition wie vorherige Schritte)
            winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
            winter_end = winter_start + pd.Timedelta(days=7)
            summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
            summer_end = summer_start + pd.Timedelta(days=7)

            winter_df = energie_bilanz[
                (pd.to_datetime(energie_bilanz["Zeitpunkt"]) >= winter_start)
                & (pd.to_datetime(energie_bilanz["Zeitpunkt"]) < winter_end)
            ]
            summer_df = energie_bilanz[
                (pd.to_datetime(energie_bilanz["Zeitpunkt"]) >= summer_start)
                & (pd.to_datetime(energie_bilanz["Zeitpunkt"]) < summer_end)
            ]

            stats_df = energie_bilanz

            col_winter, col_summer = st.columns(2, gap="small", border=True)

            with col_winter:
                st.markdown("#### ❄️ Winter (13.–19. Feb)")
                if len(winter_df) > 0:
                    fig_winter = pltp.create_balance_plot(
                        winter_df,
                        "Skalierte Netzlast [MWh]",
                        "Gesamterzeugung [MWh]",
                        "",
                        "",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_winter, use_container_width=True)
                else:
                    st.warning("Keine Winterdaten verfügbar.")

            with col_summer:
                st.markdown("#### ☀️ Sommer (3.–9. Juli)")
                if len(summer_df) > 0:
                    fig_summer = pltp.create_balance_plot(
                        summer_df,
                        "Skalierte Netzlast [MWh]",
                        "Gesamterzeugung [MWh]",
                        "",
                        "",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_summer, use_container_width=True)
                else:
                    st.warning("Keine Sommerdaten verfügbar.")
        else:
            # Gesamtjahres-Plot
            fig_year = pltp.create_balance_plot(
                energie_bilanz,
                "Skalierte Netzlast [MWh]",
                "Gesamterzeugung [MWh]",
                "",
                "",
                darkmode=False,
            )
            st.plotly_chart(fig_year, use_container_width=True)

        # Statistiken berechnen auf Basis der aktuell betrachteten Daten (stats_df)
        try:
            balance_series = stats_df["Gesamterzeugung [MWh]"].values - stats_df["Skalierte Netzlast [MWh]"].values
            total_prod = stats_df["Gesamterzeugung [MWh]"].sum()
            total_cons = stats_df["Skalierte Netzlast [MWh]"].sum()
            deficit_hours = (balance_series < 0).sum()
            surplus_hours = (balance_series >= 0).sum()
            total_deficit = (-balance_series[balance_series < 0]).sum()
            total_surplus = balance_series[balance_series > 0].sum()

            # Hilfsfunktion für rote/grüne Zahl mit Pfeil
            def arrow_metric(title: str, value_num: float, unit: str):
                is_positive = value_num >= 0
                arrow = "▲" if is_positive else "▼"
                color = "#0f8f35" if is_positive else "#d63030"
                sign_value = value_num if is_positive else -value_num  # zeige Betrag
                
                html = f"""
                <div style='padding:0px 2px;'>
                  <div style='font-size:0.75rem;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;opacity:0.65;'>{title}</div>
                  <div style='font-size:2rem;font-weight:700;color:{color};display:flex;align-items:center;gap:6px;'>
                    <span style='font-size:1.7rem;'>{arrow}</span>{sign_value:,.0f} {unit}                 
                """
                st.markdown(html, unsafe_allow_html=True)

            st.space("medium")
            st.write(f"### Zusammenfassung der Energiebilanz in {st.session_state.sim_jahr}:")

            col_a, col_b, col_c, col_d = st.columns(4, gap="small", border=True)
            with col_a:
                st.metric("Gesamterzeugung", f"{total_prod/1_000_000:.2f} TWh")
            with col_b:
                st.metric("Gesamtverbrauch", f"{total_cons/1_000_000:.2f} TWh")
            with col_c:
                arrow_metric("Defizit Energie", -total_deficit, "MWh")  # negativ -> roter Pfeil nach unten
            with col_d:
                arrow_metric("Überschuss Energie", total_surplus, "MWh")  # positiv -> grüner Pfeil nach oben

            col_e, col_f = st.columns(2)
            with col_e:
                if total_deficit > total_surplus:
                    st.warning("#### Warnung\nEnergie Defizit zu hoch um von Speicher ausgeglichen zu werden!")
                else:
                    st.empty()
                
            with col_f:
                col_g, col_h = st.columns(2, gap="small", border=True)
                with col_g:
                    st.metric("Stunden mit Defizit", f"{deficit_hours} h")
                with col_h:
                    st.metric("Stunden mit Überschuss", f"{surplus_hours} h")

            st.session_state.step_valid = True
        except Exception as e:
            st.warning(f"⚠️ Fehler bei Statistikberechnung: {e}")
            st.session_state.step_valid = False
    
    def speicher_simulieren():
        st.header("5. Speicher Simulation:")

        # Prüfe ob Energiebilanz vorhanden
        if (
            st.session_state.df_simulation_con is None
            or st.session_state.df_simulation_prod is None
            or len(st.session_state.df_simulation_con) == 0
            or len(st.session_state.df_simulation_prod) == 0
        ):
            st.warning("⚠️ Verbrauchs- oder Erzeugungsdaten fehlen. Bitte zuerst Schritte 2 und 3 ausführen.")
            st.session_state.step_valid = False
            return

        # Erstelle Energiebilanz für die Simulation
        try:
            # Basis-Bilanz erstellen
            energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
            energie_bilanz = col.add_column_from_other_df(
                energie_bilanz,
                st.session_state.df_simulation_con,
                "Skalierte Netzlast [MWh]",
                "Skalierte Netzlast [MWh]",
            )
            # Berechne initiale Balance für Visualisierung
            energie_bilanz['Initial_Balance'] = energie_bilanz['Gesamterzeugung [MWh]'] - energie_bilanz['Skalierte Netzlast [MWh]']
            # Speichere im Session State
            st.session_state.energie_bilanz = energie_bilanz
            
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {e}")
            st.session_state.step_valid = False
            return

        # --- 1. Status Quo Visualisierung (Vor Speicher) ---
        st.subheader("Bilanz Dashboard")
        
        # Berechne Summen für das Chart
        initial_surplus = energie_bilanz[energie_bilanz['Initial_Balance'] > 0]['Initial_Balance'].sum() / 1e6
        initial_deficit = energie_bilanz[energie_bilanz['Initial_Balance'] < 0]['Initial_Balance'].sum() / 1e6
        
        import altair as alt
        
        # Initialisiere Speicherwerte mit 0 (werden überschrieben falls Simulation vorhanden)
        batterie_charged_twh = 0.0
        pumpspeicher_charged_twh = 0.0
        wasserstoff_charged_twh = 0.0
        
        # Initialisiere remaining Werte mit initialen Werten (werden später ggf. angepasst)
        st.session_state.remaining_deficit_twh = initial_deficit
        st.session_state.remaining_surplus_twh = initial_surplus
        
        if "storage_results" in st.session_state:
            if "battery" in st.session_state.storage_results:
                batterie_charged_twh = st.session_state.storage_results["battery"]["Batteriespeicher_Charged_MWh"].sum() / 1e6
                batterie_discharged_twh = st.session_state.storage_results["battery"]["Batteriespeicher_Discharged_MWh"].sum() / 1e6
            else:
                batterie_charged_twh, batterie_discharged_twh = 0.0, 0.0
                
            if "pumped" in st.session_state.storage_results:
                pumpspeicher_charged_twh = st.session_state.storage_results["pumped"]["Pumpspeicher_Charged_MWh"].sum() / 1e6
                pumpspeicher_discharged_twh = st.session_state.storage_results["pumped"]["Pumpspeicher_Discharged_MWh"].sum() / 1e6
            else:
                pumpspeicher_charged_twh, pumpspeicher_discharged_twh = 0.0, 0.0
                
            if "hydrogen" in st.session_state.storage_results:
                wasserstoff_charged_twh = st.session_state.storage_results["hydrogen"]["Wasserstoffspeicher_Charged_MWh"].sum() / 1e6
                wasserstoff_discharged_twh = st.session_state.storage_results["hydrogen"]["Wasserstoffspeicher_Discharged_MWh"].sum() / 1e6
            else:
                wasserstoff_charged_twh, wasserstoff_discharged_twh = 0.0, 0.0

            kompensierte_defizite_twh = batterie_discharged_twh + pumpspeicher_discharged_twh + wasserstoff_discharged_twh
            lade_energie_genutzt_twh = batterie_charged_twh + pumpspeicher_charged_twh + wasserstoff_charged_twh
        else:
            kompensierte_defizite_twh = 0.0
            lade_energie_genutzt_twh = 0.0

        st.session_state.remaining_deficit_twh = initial_deficit + kompensierte_defizite_twh
        st.session_state.remaining_surplus_twh = initial_surplus - lade_energie_genutzt_twh
        
        # Daten für das Diagramm (Reihenfolge: Bilanz oben, dann Speicher)
        data = pd.DataFrame({
            'Werte': [st.session_state.remaining_deficit_twh, st.session_state.remaining_surplus_twh, 
                      batterie_charged_twh, 
                      pumpspeicher_charged_twh, wasserstoff_charged_twh],
            'Label': ['Bilanz', 'Bilanz', 'Batteriespeicher', 'Pumpspeicher', 'Wasserstoffspeicher'],
            'MeineFarbe': ['#d32f2f', '#388e3c', "#19d2c6", "#0330ab", "#8013ae"],
            'Sortierung': [1, 1, 2, 3, 4]  # Für korrekte Sortierung
        })

        max_wert = max(abs(initial_deficit), abs(initial_surplus))
        limit = math.ceil(max_wert / 10) * 10
        grenze = limit * 1.1  # Etwas Puffer

        # 1. Basis-Chart definieren (Datenquelle für beide Layer)
        base = alt.Chart(data).encode(
            y=alt.Y('Label:N', 
                    title=None,
                    sort=alt.EncodingSortField(field='Sortierung', order='ascending'),
                    axis=alt.Axis(labelFontSize=14, labelFontWeight='bold', labelLimit=200))
        )

        # 2. Die Balken
        bars = base.mark_bar().encode(
            x=alt.X('Werte:Q', 
                    title='Energie [TWh]',
                    scale=alt.Scale(domain=[-grenze, grenze]),
                    axis=alt.Axis(values=list(range(-limit, limit + 10, 10)), 
                                  titleFontSize=14, 
                                  labelFontSize=12)
            ),
            color=alt.Color('MeineFarbe:N', scale=None, legend=None)
        ).properties(
            height=200,  # Mehr Höhe für bessere Lesbarkeit
            padding={'left': 10, 'right': 10, 'top': 10, 'bottom': 10}
        )

        st.altair_chart(bars, use_container_width=True)

        st.markdown("---")

        # --- 2. Speicher Konfiguration & Simulation ---
        st.subheader("Energiespeicher simulieren")
        
        # Zeiträume für Detail-Plots definieren
        winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
        winter_end = winter_start + pd.Timedelta(days=7)
        summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
        summer_end = summer_start + pd.Timedelta(days=7)

        # Hilfsfunktion für Ergebnis-Anzeige
        def show_storage_results(result_df, storage_name, initial_surplus_val, initial_deficit_val):
            st.markdown(f"### Ergebnisse: {storage_name}")
            
            # Berechne Restwerte (TWh)
            # Surplus ist positiv, Deficit ist negativ im DataFrame 'Rest_Balance_MWh'
            # Wir summieren nur die jeweiligen Teile
            
            # Korrektur: Initial values müssen TWh sein, wenn wir hier mit TWh rechnen, oder MWh.
            # Oben haben wir MWh -> TWh umgerechnet für Plot.
            # Hier rechnen wir am besten alles in TWh um für Konsistenz.
            
            initial_surplus_twh = initial_surplus_val # Ist schon TWh
            initial_deficit_twh = initial_deficit_val # Ist schon TWh (negativ)
            
            # Rest ausrechnen
            rest_surplus_mwh = result_df["Rest_Balance_MWh"][result_df["Rest_Balance_MWh"] > 0].sum()
            rest_deficit_mwh = result_df["Rest_Balance_MWh"][result_df["Rest_Balance_MWh"] < 0].sum()
            
            rest_surplus_twh = rest_surplus_mwh / 1e6
            rest_deficit_twh = rest_deficit_mwh / 1e6 # Ist negativ
            
            # Berechne genutzte/gedeckte Anteile (Differenz)
            # Surplus: War 100, ist 80 -> 20 genutzt (gespeichert)
            used_surplus_twh = initial_surplus_twh - rest_surplus_twh
            
            # Deficit: War -100, ist -80 -> 20 gedeckt (aus Speicher)
            # Achtung Vorzeichen: -100 - (-80) = -20. Wir wollen aber positive Menge "gedeckt"
            # covered_deficit_twh = abs(initial_deficit_twh) - abs(rest_deficit_twh)
            covered_deficit_twh = abs(initial_deficit_twh) - abs(rest_deficit_twh)

            # 1. Zeile: Die wichtigsten KPIs farbig
            c1, c2, c3, c4 = st.columns(4)
            
            # Prozentuale Änderung
            surplus_change = ((rest_surplus_twh - initial_surplus_twh) / initial_surplus_twh * 100) if initial_surplus_twh != 0 else 0
            deficit_change = ((abs(rest_deficit_twh) - abs(initial_deficit_twh)) / abs(initial_deficit_twh) * 100) if initial_deficit_twh != 0 else 0

            c1.metric("Gespeicherter Überschuss", f"{used_surplus_twh:.2f} TWh", f"Netto-Ersparnis", delta_color="normal")
            c2.metric("Gedecktes Defizit", f"{covered_deficit_twh:.2f} TWh", f"Versorgungssicherheit", delta_color="normal")
            c3.metric("Verbleibender Überschuss", f"{rest_surplus_twh:.2f} TWh", f"{surplus_change:.1f}%", delta_color="off")
            c4.metric("Verbleibendes Defizit", f"{abs(rest_deficit_twh):.2f} TWh", f"{deficit_change:.1f}%", delta_color="inverse")
            
            # 2. Zeile: Detail-Plots (Winter/Sommer SOC)
            soc_col_name = f"{storage_name}_SOC_MWh"
            if soc_col_name not in result_df.columns:
                 soc_cols = [c for c in result_df.columns if "SOC" in c]
                 if soc_cols: soc_col_name = soc_cols[0]
            
            df_winter = result_df[(pd.to_datetime(result_df["Zeitpunkt"]) >= winter_start) & (pd.to_datetime(result_df["Zeitpunkt"]) < winter_end)]
            df_summer = result_df[(pd.to_datetime(result_df["Zeitpunkt"]) >= summer_start) & (pd.to_datetime(result_df["Zeitpunkt"]) < summer_end)]
            
            col_w, col_s = st.columns(2, gap="small", border=True)
            with col_w:
                st.markdown("#### ❄️ Winter SOC")
                if len(df_winter) > 0:
                    fig_w = pltp.create_line_plot(df_winter, y_axis=soc_col_name, title="", description="", darkmode=False)
                    st.plotly_chart(fig_w, use_container_width=True)
                else: st.warning("Keine Winterdaten")
            with col_s:
                st.markdown("#### ☀️ Sommer SOC")
                if len(df_summer) > 0:
                    fig_s = pltp.create_line_plot(df_summer, y_axis=soc_col_name, title="", description="", darkmode=False)
                    st.plotly_chart(fig_s, use_container_width=True)
                else: st.warning("Keine Sommerdaten")


        # Tabs für die Speicher-Typen
        storage_tabs = st.tabs(["🔋 Batterie (Kurzzeit)", "🚧 Pumpspeicher :orange[[IN ENTWICKLUNG]]", "🚧 Wasserstoff :orange[[IN ENTWICKLUNG]]"], )
        
        # --- TAB 1: BATTERIE ---
        with storage_tabs[0]:
            st.caption("Ideal für Tagesausgleich (PV-Überschuss in die Nacht). Hoher Wirkungsgrad.")
            
            st.segmented_control(label="Modus wählen:", options=["Basic", "Erweitert"], key="bat_args_mode", default=["Basic"])

            c1, c2 = st.columns(2)
            e1, e2 = c1.columns(2)
            bat_cap = e1.number_input("Kapazität [MWh]", 1000.0, 500_000.0, 50_000.0, step=1000.0, key="bat_cap")
            bat_soc_init_pct = e2.slider("Anfangs-SOC [%]", 0, 100, 50, key="bat_soc_init") / 100
            if st.session_state.bat_args_mode == "Basic":
                bat_power = c2.number_input("Leistung [MW] (Laden und Entladen)", 100.0, 50_000.0, 10_000.0, step=100.0, key="bat_pow")
            else:
                d1, d2 = c2.columns(2)
                bat_power_cha = d1.number_input("Lade Leistung [MW]", 100.0, 200_000.0, 10_000.0, step=100.0, key="bat_pow_cha")
                bat_power_dis = d2.number_input("Entlade Leistung [MW]", 100.0, 200_000.0, 10_000.0, step=100.0, key="bat_pow_dis")

            if st.session_state.bat_args_mode == "Erweitert":
                c3, c4 = st.columns(2)
                bat_eff_cha = c3.slider("Ladewirkungsgrad [%]", 80, 100, 95, key="bat_eff_cha") / 100
                bat_eff_dis = c4.slider("Entladewirkungsgrad [%]", 80, 100, 95, key="bat_eff_dis") / 100
            
            # additional advanced calculations
                bat_init_soc_mwh = bat_cap * bat_soc_init_pct

            else:
                bat_power_cha = bat_power
                bat_power_dis = bat_power
                bat_eff_cha = 0.95
                bat_eff_dis = 0.95
                bat_init_soc_mwh = bat_cap * 0.5

            
            st.markdown("---")
            if st.button("Simulation starten (Batterie)", type="primary", key="btn_bat"):
                with st.spinner("Simuliere Batterie..."):
                    res_bat = sim.simulate_storage_generic(
                        df_balance=energie_bilanz,
                        type_name="Batteriespeicher",
                        capacity_mwh=bat_cap,
                        max_charge_mw=bat_power_cha,
                        max_discharge_mw=bat_power_dis,
                        charge_efficiency=bat_eff_cha,
                        discharge_efficiency=bat_eff_dis,
                        initial_soc_mwh=bat_init_soc_mwh,
                        min_soc_mwh=0.0
                    )
                    st.session_state.storage_results = st.session_state.get("storage_results", {})
                    st.session_state.storage_results["battery"] = res_bat
                    st.session_state.step_valid = True
                    st.success("✅ Batterie simuliert!")
                    st.rerun()

            if "storage_results" in st.session_state and "battery" in st.session_state.storage_results:
                show_storage_results(st.session_state.storage_results["battery"], "Batteriespeicher", initial_surplus, initial_deficit)

        # --- TAB 2: PUMPSPEICHER ---
        with storage_tabs[1]:
            if True:
                st.warning("🚧 Pumpspeicher-Simulation ist derzeit in Entwicklung und noch nicht verfügbar.")
            else:
                st.markdown("#### 💧 Pumpspeicher")
                st.caption("Bewährte Technologie für Wochenausgleich. Begrenzte Ausbaumöglichkeiten in DE.")
                
                with st.expander("⚙️ Parameter anpassen", expanded=True):
                    c1, c2 = st.columns(2)
                    ps_cap = c1.number_input("Kapazität [MWh]", 10_000.0, 1_000_000.0, 40_000.0, step=5000.0, key="ps_cap")
                    ps_power = c2.number_input("Leistung (Pumpen/Turbinieren) [MW]", 100.0, 20_000.0, 6_000.0, step=100.0, key="ps_pow")
                    c3, c4 = st.columns(2)
                    ps_eff_ch = c3.slider("Pumpwirkungsgrad [%]", 70, 95, 88, key="ps_eff_ch") / 100
                    ps_eff_dis = c4.slider("Turbinenwirkungsgrad [%]", 70, 95, 88, key="ps_eff_dis") / 100

                if st.button("Simulation starten (Pumpspeicher)", type="primary", key="btn_ps"):
                    with st.spinner("Simuliere Pumpspeicher..."):
                        input_df = energie_bilanz.copy()
                        if "battery" in st.session_state.storage_results:
                            prev_res = st.session_state.storage_results["battery"]
                            # Wir nutzen die Rest-Balance (Achtung: MWh)
                            # simulate_storage_generic erwartet 'Gesamterzeugung' und 'Skalierte Netzlast' zur Differenzbildung.
                            # Hack: Wir setzen 'Gesamterzeugung' = Rest_Balance und 'Skalierte Netzlast' = 0.
                            input_df['Gesamterzeugung [MWh]'] = prev_res['Rest_Balance_MWh']
                            input_df['Skalierte Netzlast [MWh]'] = 0
                        
                        res_ps = sim.simulate_storage_generic(
                            df_balance=input_df,
                            type_name="Pumpspeicher",
                            capacity_mwh=ps_cap,
                            max_charge_mw=ps_power,
                            max_discharge_mw=ps_power,
                            charge_efficiency=ps_eff_ch,
                            discharge_efficiency=ps_eff_dis,
                            initial_soc_mwh=ps_cap*0.5,
                            min_soc_mwh=0.0
                        )
                        st.session_state.storage_results = st.session_state.get("storage_results", {})
                        st.session_state.storage_results["pumped"] = res_ps
                        st.session_state.step_valid = True
                        st.success("✅ Pumpspeicher simuliert!")
                        st.rerun()

                if "storage_results" in st.session_state and "pumped" in st.session_state.storage_results:
                    show_storage_results(st.session_state.storage_results["pumped"], "Pumpspeicher", initial_surplus, initial_deficit)

        # --- TAB 3: WASSERSTOFF ---
        with storage_tabs[2]:
            if True:
                st.warning("🚧 Wasserstoff-Speicher-Simulation ist derzeit in Entwicklung und noch nicht verfügbar.")
            else:
                st.markdown("#### 🔬 Wasserstoffspeicher (Power-to-Gas)")
                st.caption("Saisonaler Speicher. Geringer Wirkungsgrad, aber riesige Kapazität möglich.")
                
                with st.expander("⚙️ Parameter anpassen", expanded=True):
                    c1, c2 = st.columns(2)
                    h2_cap = c1.number_input("Kapazität (Kavernen) [MWh]", 100_000.0, 50_000_000.0, 1_000_000.0, step=100_000.0, key="h2_cap")
                    c3, c4 = st.columns(2)
                    h2_ely = c3.number_input("Elektrolyse-Leistung [MW]", 100.0, 100_000.0, 5_000.0, step=100.0, key="h2_ely")
                    h2_fc = c4.number_input("Rückverstromung (H2-Kraftwerk) [MW]", 100.0, 100_000.0, 5_000.0, step=100.0, key="h2_fc")
                    c5, c6 = st.columns(2)
                    h2_eff_ch = c5.slider("Elektrolyse-Wirkungsgrad [%]", 50, 80, 65, key="h2_eff_ch") / 100
                    h2_eff_dis = c6.slider("Rückverstromungs-Wirkungsgrad [%]", 30, 70, 50, key="h2_eff_dis") / 100

                if st.button("Simulation starten (Wasserstoff)", type="primary", key="btn_h2"):
                    with st.spinner("Simuliere Wasserstoff..."):
                        input_df = energie_bilanz.copy()
                        # Priorität: Pumpspeicher > Batterie > Original
                        if "pumped" in st.session_state.storage_results:
                            prev_res = st.session_state.storage_results["pumped"]
                            input_df['Gesamterzeugung [MWh]'] = prev_res['Rest_Balance_MWh']
                            input_df['Skalierte Netzlast [MWh]'] = 0
                        elif "battery" in st.session_state.storage_results:
                            prev_res = st.session_state.storage_results["battery"]
                            input_df['Gesamterzeugung [MWh]'] = prev_res['Rest_Balance_MWh']
                            input_df['Skalierte Netzlast [MWh]'] = 0
                        
                        res_h2 = sim.simulate_storage_generic(
                            df_balance=input_df,
                            type_name="Wasserstoffspeicher",
                            capacity_mwh=h2_cap,
                            max_charge_mw=h2_ely,
                            max_discharge_mw=h2_fc,
                            charge_efficiency=h2_eff_ch,
                            discharge_efficiency=h2_eff_dis,
                            initial_soc_mwh=0.0,
                            min_soc_mwh=0.0
                        )
                        st.session_state.storage_results = st.session_state.get("storage_results", {})
                        st.session_state.storage_results["hydrogen"] = res_h2
                        st.session_state.step_valid = True
                        st.success("✅ Wasserstoff simuliert!")
                        st.rerun()

                if "storage_results" in st.session_state and "hydrogen" in st.session_state.storage_results:
                    show_storage_results(st.session_state.storage_results["hydrogen"], "Wasserstoffspeicher", initial_surplus, initial_deficit)
            
    def gesamt_validieren():
        st.header("6. Gesamtergebnisse")
        
        # Prüfe ob alle notwendigen Daten vorhanden sind
        if (
            st.session_state.df_simulation_con is None
            or st.session_state.df_simulation_prod is None
        ):
            st.warning("⚠️ Simulationsdaten fehlen. Bitte führe die vorherigen Schritte aus.")
            st.session_state.step_valid = False
            return
        
        # Erstelle Energiebilanz
        try:
            energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
            energie_bilanz = col.add_column_from_other_df(
                energie_bilanz,
                st.session_state.df_simulation_con,
                "Skalierte Netzlast [MWh]",
                "Skalierte Netzlast [MWh]",
            )
            # Speichere im Session State
            st.session_state.energie_bilanz = energie_bilanz
            balance = energie_bilanz["Gesamterzeugung [MWh]"] - energie_bilanz["Skalierte Netzlast [MWh]"]
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {e}")
            st.session_state.step_valid = False
            return
        
        # --- ABSCHNITT 1: Simulationsübersicht ---
        st.subheader("🎯 Simulationsübersicht")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Simulationsjahr", st.session_state.sim_jahr)
        with col2:
            st.metric("Referenzjahr", st.session_state.sim_referenz_jahr)
        with col3:
            st.metric("Studie (Verbrauch)", st.session_state.sim_studie_verbrauch or "-")
        with col4:
            st.metric("Studie (Erzeugung)", st.session_state.sim_studie_erzeugung or "-")
        
        st.markdown("---")
        
        # --- ABSCHNITT 2: Energiebilanz ohne Speicher ---
        st.subheader("Energiebilanz (ohne Speicher)")
        
        total_prod = energie_bilanz["Gesamterzeugung [MWh]"].sum()
        total_cons = energie_bilanz["Skalierte Netzlast [MWh]"].sum()
        
        # Defizit/Überschuss-Stunden
        deficit_mask = balance < 0
        surplus_mask = balance > 0
        deficit_hours = deficit_mask.sum()
        surplus_hours = surplus_mask.sum()
        
        total_deficit = (-balance[deficit_mask]).sum()
        total_surplus = balance[surplus_mask].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Gesamterzeugung", f"{total_prod/1_000_000:.2f} TWh")
        with col2:
            st.metric("Gesamtverbrauch", f"{total_cons/1_000_000:.2f} TWh")
        with col3:
            st.metric(
                "Defizit-Energie",
                f"{total_deficit/1_000:.0f} GWh",
                delta=f"{deficit_hours} Stunden",
                delta_color="inverse"
            )
        with col4:
            st.metric(
                "Überschuss-Energie",
                f"{total_surplus/1_000:.0f} GWh",
                delta=f"{surplus_hours} Stunden",
                delta_color="normal"
            )
        
        st.markdown("---")
        
        # --- ABSCHNITT 3: Speicher-Auswirkungen ---
        if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
            st.subheader("Speicher-Auswirkungen")
            
            # Zeige Statistiken für jeden aktiven Speicher
            storage_tabs = []
            if "battery" in st.session_state.storage_results:
                storage_tabs.append("🔋 Batterie")
            if "pumped" in st.session_state.storage_results:
                storage_tabs.append("💧 Pumpspeicher")
            if "hydrogen" in st.session_state.storage_results:
                storage_tabs.append("🔬 Wasserstoff")
            
            storage_display_tabs = st.tabs(storage_tabs)
            
            tab_idx = 0
            if "battery" in st.session_state.storage_results:
                with storage_display_tabs[tab_idx]:
                    battery_df = st.session_state.storage_results["battery"]
                    battery_charged = battery_df["Batteriespeicher_Charged_MWh"].sum()
                    battery_discharged = battery_df["Batteriespeicher_Discharged_MWh"].sum()
                    battery_losses = battery_discharged - battery_charged
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Geladen", f"{battery_charged/1_000:.0f} GWh")
                    with col2:
                        st.metric("Entladen", f"{battery_discharged/1_000:.0f} GWh")
                    with col3:
                        st.metric(
                            "Verluste",
                            f"{abs(battery_losses)/1_000:.0f} GWh",
                            delta=f"{(battery_losses/battery_charged*100):.1f}%",
                        )
                tab_idx += 1
            
            # ===================================================
            # NEEDS FIX MS4
            # ===================================================

            if "pumped" in st.session_state.storage_results:
                with storage_display_tabs[tab_idx]:
                    pumped_df = st.session_state.storage_results["pumped"]
                    pumped_charged = pumped_df["Charged [MWh]"].sum()
                    pumped_discharged = pumped_df["Discharged [MWh]"].sum()
                    pumped_losses = pumped_charged - pumped_discharged
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Gepumpt", f"{pumped_charged/1_000:.0f} GWh")
                    with col2:
                        st.metric("Turbiniert", f"{pumped_discharged/1_000:.0f} GWh")
                    with col3:
                        st.metric(
                            "Verluste",
                            f"{abs(pumped_losses)/1_000:.0f} GWh",
                            delta=f"{(abs(pumped_losses)/pumped_charged*100):.1f}%",
                            delta_color="inverse"
                        )
                tab_idx += 1
            
            # ===================================================
            # NEEDS FIX MS4
            # ===================================================

            if "hydrogen" in st.session_state.storage_results:
                with storage_display_tabs[tab_idx]:
                    h2_df = st.session_state.storage_results["hydrogen"]
                    h2_charged = h2_df["Charged [MWh]"].sum()
                    h2_discharged = h2_df["Discharged [MWh]"].sum()
                    h2_losses = h2_charged - h2_discharged
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Elektrolysiert", f"{h2_charged/1_000:.0f} GWh")
                    with col2:
                        st.metric("Rückverstromt", f"{h2_discharged/1_000:.0f} GWh")
                    with col3:
                        st.metric(
                            "Verluste",
                            f"{abs(h2_losses)/1_000:.0f} GWh",
                            delta=f"{(abs(h2_losses)/h2_charged*100):.1f}%",
                            delta_color="inverse"
                        )
            
            # Verbesserungen durch Speicher (nutze letzten Speicher in der Kette)
            st.markdown("### Gesamtverbesserung durch Speichersystem")
            
            # Nutze das letzte Ergebnis in der Kette
            final_result = None
            if "hydrogen" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["hydrogen"]
            elif "pumped" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["pumped"]
            elif "battery" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["battery"]
            
            if final_result is not None:
                
                deficit_reduction = total_deficit - abs(final_result["Rest_Balance_MWh"][final_result["Rest_Balance_MWh"] < 0].sum())
                surplus_reduction = total_surplus - final_result["Rest_Balance_MWh"][final_result["Rest_Balance_MWh"] > 0].sum()
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Defizit-Reduktion",
                        f"{deficit_reduction/1_000:.0f} GWh",
                        delta=f"{-(deficit_reduction/total_deficit*100):.1f}%",
                        delta_color="inverse"
                    )
                with col2:
                    st.metric(
                        "Verbleibendes Defizit",
                        f"{abs(st.session_state.remaining_deficit_twh)*1_000:.0f} GWh",
                        delta_color="inverse"
                    )
                with col3:
                    st.metric(
                        "Überschuss-Reduktion",
                        f"{surplus_reduction/1_000:.0f} GWh",
                        delta=f"{-(surplus_reduction/total_surplus*100):.1f}%",
                        delta_color="inverse"
                    )
                with col4:
                    st.metric(
                        "Verbleibender Überschuss",
                        f"{st.session_state.remaining_surplus_twh*1_000:.0f} GWh",
                        delta_color="inverse"
                    )
            
            st.markdown("---")
        
        # --- ABSCHNITT 4: Was muss noch getan werden? ---
        st.subheader("Handlungsbedarf")
        
        # Bestimme finalen Surplus/Deficit basierend auf aktiven Speichern
        if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
            # Nutze das letzte Ergebnis in der Speicherkette
            if "hydrogen" in st.session_state.storage_results:
                final_df = st.session_state.storage_results["hydrogen"]
            elif "pumped" in st.session_state.storage_results:
                final_df = st.session_state.storage_results["pumped"]
            else:
                final_df = st.session_state.storage_results["battery"]
            
            final_surplus = st.session_state.remaining_surplus_twh * 1e6  # in MWh
            final_deficit = st.session_state.remaining_deficit_twh * 1e6  # in MWh
        else:
            final_surplus = total_surplus
            final_deficit = total_deficit
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### :orange[Abregelung oder Export notwendig]")
            st.metric(
                "Überschuss muss abgeregelt/exportiert werden",
                f"{final_surplus/1_000:.0f} GWh",
                help="Diese Energie kann nicht genutzt werden und muss abgeregelt oder exportiert werden."
            )
            if final_surplus > 0:
                abregelung_pct = (final_surplus / total_prod) * 100
                st.warning(f"💡 {abregelung_pct:.2f}% der Gesamterzeugung muss abgeregelt oder exportiert werden.")
        
        with col2:
            st.markdown("#### :blue[Zusätzliche Energie nötig]")
            st.metric(
                "Defizit muss ausgeglichen werden",
                f"{final_deficit/1_000:.0f} GWh",
                help="Diese Energie fehlt und muss durch zusätzliche Erzeugung oder Import gedeckt werden."
            )
            if final_deficit < 0:
                deficit_pct = (abs(final_deficit) / total_cons) * 100
                st.warning(f"💡 {deficit_pct:.2f}% des Gesamtverbrauchs kann nicht gedeckt werden.")
        
        st.session_state.step_valid = True

    def ergebnisse_speichern():
        st.title("7. Ergebnisse speichern")

        @st.cache_data
        def convert_for_download_csv(df):
            return df.to_csv().encode("utf-8")
        

        if  "df_simulation_prod" in st.session_state:            
            st.subheader("Produktions Simulation Ergebnisse: ")
            st.dataframe(st.session_state.df_simulation_prod.head())
            csv_prod = convert_for_download_csv(st.session_state.df_simulation_prod)
            st.download_button("Download CSV", data=csv_prod, file_name="produktions_simulation.csv", mime="text/csv", type="primary")            
            st.markdown("---")
        if  "df_simulation_con" in st.session_state:            
            st.subheader("Verbrauchs Simulation Ergebnisse: ")
            st.dataframe(st.session_state.df_simulation_con.head())
            csv_con = convert_for_download_csv(st.session_state.df_simulation_con)
            st.download_button("Download CSV", data=csv_con, file_name="verbrauchs_simulation.csv", mime="text/csv", type="primary")            
            st.markdown("---")
        if  False:            
            st.subheader("Energiebilanz Ergebnisse: ")
            st.dataframe(st.session_state.energie_bilanz.head())
            csv_eb = convert_for_download_csv(st.session_state.energie_bilanz)
            st.download_button("Download CSV", data=csv_eb, file_name="energiebilanz.csv", mime="text/csv", type="primary")            
            st.markdown("---")
        if  "storage_results" in st.session_state:            
            for storage_type, storage_df in st.session_state.storage_results.items():
                st.subheader(f"{storage_type.capitalize()} Speicher Simulation Ergebnisse: ")
                st.dataframe(storage_df.head())
                csv_storage = convert_for_download_csv(storage_df)
                st.download_button("Download CSV", data=csv_storage, file_name=f"{storage_type}_speicher_simulation.csv", mime="text/csv", type="primary")            
                st.markdown("---")
        
        st.markdown("## Simulation abgeschlossen!")
        if st.button("Fertig", type="primary", ):
            st.balloons()
            
    
    # Zeige den aktuellen Schritt an
    if aktiver_schritt_index == 0:
        daten_auswaehlen()
    elif aktiver_schritt_index == 1:
        verbrauch_simulieren()
    elif aktiver_schritt_index == 2:
        erzeugung_simulieren()
    elif aktiver_schritt_index == 3:
        defizite_anzeigen()
    elif aktiver_schritt_index == 4:
        speicher_simulieren()
    elif aktiver_schritt_index == 5:
        gesamt_validieren()
    elif aktiver_schritt_index == 6:
        ergebnisse_speichern()
    else:
        st.error("Unbekannter Simulationsschritt. Versuche die App neu zu starten.")

    # Navigation Buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if aktiver_schritt_index > 0:
            st.button("⬅️ Zurück", on_click=set_step, args=(aktiver_schritt_index - 1,), use_container_width=True)
        else:
            st.button("⬅️ Zurück", disabled=True, use_container_width=True)
    
    with col2:
        st.button("Hauptmenü", on_click=set_mode, args=("main",), use_container_width=True)
    
    with col3:
        if aktiver_schritt_index < len(SIMULATION_SCHRITTE) - 1:
            # Weiter-Button nur aktivieren wenn der aktuelle Schritt valid ist
            if st.session_state.step_valid:
                st.button("Weiter ➡️", on_click=set_step, args=(aktiver_schritt_index + 1,), use_container_width=True, type="primary")
            else:
                st.button("Weiter ➡️", disabled=True, use_container_width=True)
        else:
            st.button("✅ Fertig", on_click=set_mode, args=("main",), use_container_width=True, type="primary")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("Simulation zurücksetzen", on_click=reset_step_simulation, use_container_width=True, type="secondary",)


def reset_step_simulation():
    """Setzt die Step-Simulation zurück."""
    if "step_index" in st.session_state:
        del st.session_state.step_index
    if "step_valid" in st.session_state:
        del st.session_state.step_valid
    if "sim_datei_verbrauch" in st.session_state:
        del st.session_state.sim_datei_verbrauch
    if "sim_datei_erzeugung" in st.session_state:
        del st.session_state.sim_datei_erzeugung
    if "sim_studie_verbrauch" in st.session_state:
        del st.session_state.sim_studie_verbrauch
    if "sim_studie_erzeugung" in st.session_state:
        del st.session_state.sim_studie_erzeugung
    if "sim_jahr" in st.session_state:
        del st.session_state.sim_jahr
    if "sim_referenz_jahr" in st.session_state:
        del st.session_state.sim_referenz_jahr
    if "sim_verbrauch_lastprofile" in st.session_state:
        del st.session_state.sim_verbrauch_lastprofile
    if "df_simulation_con" in st.session_state:
        del st.session_state.df_simulation_con
    if "df_simulation_prod" in st.session_state:
        del st.session_state.df_simulation_prod
    if "energie_bilanz" in st.session_state:
        del st.session_state.energie_bilanz
    if "storage_results" in st.session_state:
        del st.session_state.storage_results
    if "remaining_surplus_twh" in st.session_state:
        del st.session_state.remaining_surplus_twh
    if "remaining_deficit_twh" in st.session_state:
        del st.session_state.remaining_deficit_twh
    if "bat_args_mode" in st.session_state:
        del st.session_state.bat_args_mode
    

SIMULATION_SCHRITTE = [
    "Daten auswählen",
    "Verbrauch Simulieren",
    "Erzeugung Simulieren",
    "Defizite anzeigen",
    "Speicher Simulieren",
    "Gesamt Ergebnisse",
    "Ergebnisse speichern"
]

def render_checklist(aktiver_schritt_index):
    """Generiert die Checkliste mit Emojis und HTML-Farben."""
    
    checklist_html = ""
    
    for i, schritt in enumerate(SIMULATION_SCHRITTE):
        
        if i < aktiver_schritt_index:
            # Zustand 1: ABGESCHLOSSEN
            line = f"✅ <span style='color: #28a745;'>{schritt}</span>"
            
        elif i == aktiver_schritt_index:
            # Zustand 2: AKTIV 
            line = f"➡️ **{schritt}**"
            
        else:
            # Zustand 3: AUSSTEHEND
            line = f"⬜ <span style='color: #6c757d;'>{schritt}</span>"
            
        # Füge einen Zeilenumbruch (<br>) hinzu, damit die Liste vertikal bleibt.
        checklist_html += f"{line} <br>\n\n"

    return checklist_html


def load_data_manager() -> bool:
    """Lädt den DataManager und ConfigManager und speichert sie im Session-State.
    
    Returns:
        bool: True wenn erfolgreich geladen, sonst False.
    """
        
    try:
        config_path = Path(__file__).parent / "config.json"
        cfg = ConfigManager(config_path=config_path)
        dm = DataManager(config_manager=cfg)
        
        st.session_state.cfg = cfg
        st.session_state.dm = dm
        return True
        
    except Exception as e:
        st.error(f"❌ LOAD DATA -> Fehler beim Laden: {e}")
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
elif mode == "standard":
    show_standard_simulation()
elif mode == "step":
    show_step_simulation()
else:
    show_main_menu()
