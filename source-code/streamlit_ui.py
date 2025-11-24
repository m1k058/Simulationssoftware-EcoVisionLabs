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

st.set_page_config(
    layout="centered", # Standard ist "centered"
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
        st.header("4. Defizite Ausgleichen:")

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

            stats_df = pd.concat([winter_df, summer_df], ignore_index=True) if len(winter_df) + len(summer_df) > 0 else energie_bilanz

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
            def arrow_metric(title: str, value_num: float, unit: str, hours: int | None = None):
                is_positive = value_num >= 0
                arrow = "▲" if is_positive else "▼"
                color = "#0f8f35" if is_positive else "#d63030"
                sign_value = value_num if is_positive else -value_num  # zeige Betrag
                hours_html = f"<div style='font-size:0.65rem;opacity:0.75;'>Stunden: {hours}</div>" if hours is not None else ""
                html = f"""
                <div style='padding:10px 12px;'>
                  <div style='font-size:0.70rem;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;opacity:0.65;'>{title}</div>
                  <div style='font-size:1.3rem;font-weight:700;color:{color};display:flex;align-items:center;gap:6px;'>
                    <span style='font-size:1.1rem;'>{arrow}</span>{sign_value:,.0f} {unit}
                  </div>
                  {hours_html}
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)

            col_a, col_b, col_c, col_d = st.columns(4, gap="small", border=True)
            with col_a:
                st.metric("Gesamterzeugung", f"{total_prod/1_000_000:.2f} TWh")
            with col_b:
                st.metric("Gesamtverbrauch", f"{total_cons/1_000_000:.2f} TWh")
            with col_c:
                arrow_metric("Defizit Energie", -total_deficit, "MWh", deficit_hours)  # negativ -> roter Pfeil nach unten
            with col_d:
                arrow_metric("Überschuss Energie", total_surplus, "MWh", surplus_hours)  # positiv -> grüner Pfeil nach oben

            st.session_state.step_valid = True
        except Exception as e:
            st.warning(f"⚠️ Fehler bei Statistikberechnung: {e}")
            st.session_state.step_valid = False

    def speicher_simulieren():
        st.header("5. Speicher Simulieren:")

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

        # Erstelle Energiebilanz
        try:
            energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
            energie_bilanz = col.add_column_from_other_df(
                energie_bilanz,
                st.session_state.df_simulation_con,
                "Skalierte Netzlast [MWh]",
                "Skalierte Netzlast [MWh]",
            )
        except Exception as e:
            st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {e}")
            st.session_state.step_valid = False
            return

        # Zeiträume für Plots
        winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
        winter_end = winter_start + pd.Timedelta(days=7)
        summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
        summer_end = summer_start + pd.Timedelta(days=7)

        # Hilfsfunktion für SOC-Plots
        def show_storage_results(result_df, storage_name, winter_start, winter_end, summer_start, summer_end):
            st.markdown(f"### 📊 {storage_name} - Ergebnisse")
            
            # Filter für Winter und Sommer
            df_winter = result_df[
                (pd.to_datetime(result_df["Zeitpunkt"]) >= winter_start) &
                (pd.to_datetime(result_df["Zeitpunkt"]) < winter_end)
            ]
            df_summer = result_df[
                (pd.to_datetime(result_df["Zeitpunkt"]) >= summer_start) &
                (pd.to_datetime(result_df["Zeitpunkt"]) < summer_end)
            ]
            
            # SOC Plots
            col_w, col_s = st.columns(2, gap="small", border=True)
            with col_w:
                st.markdown("#### ❄️ Winter SOC")
                if len(df_winter) > 0:
                    fig_w = pltp.create_line_plot(
                        df_winter,
                        y_axis="SOC [MWh]",
                        title="",
                        description="",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_w, use_container_width=True)
                else:
                    st.warning("Keine Winterdaten")
            
            with col_s:
                st.markdown("#### ☀️ Sommer SOC")
                if len(df_summer) > 0:
                    fig_s = pltp.create_line_plot(
                        df_summer,
                        y_axis="SOC [MWh]",
                        title="",
                        description="",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_s, use_container_width=True)
                else:
                    st.warning("Keine Sommerdaten")
            
            # Statistiken
            total_charged = result_df["Charged [MWh]"].sum()
            total_discharged = result_df["Discharged [MWh]"].sum()
            remaining_surplus = result_df["Remaining Surplus [MWh]"].sum()
            remaining_deficit = result_df["Remaining Deficit [MWh]"].sum()
            
            col1, col2, col3, col4 = st.columns(4, gap="small")
            with col1:
                st.metric("Geladen", f"{total_charged/1_000:.0f} GWh")
            with col2:
                st.metric("Entladen", f"{total_discharged/1_000:.0f} GWh")
            with col3:
                st.metric("Rest-Überschuss", f"{remaining_surplus/1_000:.0f} GWh")
            with col4:
                st.metric("Rest-Defizit", f"{remaining_deficit/1_000:.0f} GWh")

        # Speicher-Konfiguration mit Tabs
        st.subheader("⚙️ Energiespeicher konfigurieren")
        
        storage_tabs = st.tabs(["🔋 Batterie (Kurzzeit)", "💧 Pumpspeicher (Mittelzeit)", "🔬 Wasserstoff (Langzeit)"])
        
        # Tab 1: Batteriespeicher
        with storage_tabs[0]:
            st.markdown("#### Batteriespeicher (Kurzzeitspeicher)")
            st.caption("Typische Speicherdauer: Stunden bis 1 Tag | Wirkungsgrad: ~90%")
            
            col1, col2 = st.columns(2)
            with col1:
                battery_capacity_mwh = st.number_input(
                    "Kapazität [MWh]",
                    min_value=1000.0,
                    max_value=100_000.0,
                    value=10_000.0,
                    step=1000.0,
                    key="battery_capacity"
                )
                battery_max_charge_mw = st.number_input(
                    "Max. Ladeleistung [MW]",
                    min_value=100.0,
                    max_value=10_000.0,
                    value=2_000.0,
                    step=100.0,
                    key="battery_charge_power"
                )
                battery_charge_eff = st.slider(
                    "Ladewirkungsgrad [%]",
                    min_value=80,
                    max_value=100,
                    value=95,
                    key="battery_charge_eff"
                ) / 100.0
            
            with col2:
                battery_initial_soc_pct = st.slider(
                    "Initial SOC [%]",
                    min_value=0,
                    max_value=100,
                    value=50,
                    key="battery_initial_soc"
                )
                battery_max_discharge_mw = st.number_input(
                    "Max. Entladeleistung [MW]",
                    min_value=100.0,
                    max_value=10_000.0,
                    value=2_000.0,
                    step=100.0,
                    key="battery_discharge_power"
                )
                battery_discharge_eff = st.slider(
                    "Entladewirkungsgrad [%]",
                    min_value=80,
                    max_value=100,
                    value=95,
                    key="battery_discharge_eff"
                ) / 100.0
            
            col3, col4 = st.columns(2)
            with col3:
                battery_min_soc_pct = st.slider(
                    "Min SOC [%] (Tiefentladungsschutz)",
                    min_value=0,
                    max_value=50,
                    value=10,
                    key="battery_min_soc"
                )
            with col4:
                battery_max_soc_pct = st.slider(
                    "Max SOC [%] (Schutz vor Überladung)",
                    min_value=50,
                    max_value=100,
                    value=100,
                    key="battery_max_soc"
                )
            
            battery_min_soc_mwh = (battery_min_soc_pct / 100.0) * battery_capacity_mwh
            battery_max_soc_mwh = (battery_max_soc_pct / 100.0) * battery_capacity_mwh
            battery_initial_soc_mwh = (battery_initial_soc_pct / 100.0) * battery_capacity_mwh
            
            battery_roundtrip = battery_charge_eff * battery_discharge_eff * 100
            st.info(f"ℹ️ Roundtrip-Wirkungsgrad: {battery_roundtrip:.1f}%")
            
            if st.button("🔋 Batteriespeicher simulieren", type="primary", use_container_width=True):
                with st.spinner("Batteriespeicher-Simulation läuft..."):
                    try:
                        if "storage_results" not in st.session_state:
                            st.session_state.storage_results = {}
                        
                        result_df = sim.apply_battery_storage(
                            energie_bilanz,
                            capacity_mwh=battery_capacity_mwh,
                            max_charge_power_mw=battery_max_charge_mw,
                            max_discharge_power_mw=battery_max_discharge_mw,
                            charge_efficiency=battery_charge_eff,
                            discharge_efficiency=battery_discharge_eff,
                            initial_soc=battery_initial_soc_mwh,
                            min_soc=battery_min_soc_mwh,
                            max_soc=battery_max_soc_mwh
                        )
                        
                        st.session_state.storage_results["battery"] = result_df
                        st.success("✅ Batteriespeicher-Simulation abgeschlossen")
                        st.session_state.step_valid = True
                        
                    except Exception as e:
                        st.error(f"❌ Fehler bei der Batteriesimulation: {e}")
                        st.session_state.step_valid = False
        
        # Tab 2: Pumpspeicher
        with storage_tabs[1]:
            st.markdown("#### Pumpspeicher (Mittelzeitspeicher)")
            st.caption("Typische Speicherdauer: Tage bis Wochen | Wirkungsgrad: ~75-85%")
            
            col1, col2 = st.columns(2)
            with col1:
                pumped_capacity_mwh = st.number_input(
                    "Kapazität [MWh]",
                    min_value=10_000.0,
                    max_value=500_000.0,
                    value=50_000.0,
                    step=5_000.0,
                    key="pumped_capacity"
                )
                pumped_max_charge_mw = st.number_input(
                    "Max. Pumpleistung [MW]",
                    min_value=100.0,
                    max_value=5_000.0,
                    value=1_500.0,
                    step=100.0,
                    key="pumped_charge_power"
                )
                pumped_charge_eff = st.slider(
                    "Pumpwirkungsgrad [%]",
                    min_value=75,
                    max_value=95,
                    value=85,
                    key="pumped_charge_eff"
                ) / 100.0
            
            with col2:
                pumped_initial_soc_pct = st.slider(
                    "Initial SOC [%]",
                    min_value=0,
                    max_value=100,
                    value=50,
                    key="pumped_initial_soc"
                )
                pumped_max_discharge_mw = st.number_input(
                    "Max. Turbinenleistung [MW]",
                    min_value=100.0,
                    max_value=5_000.0,
                    value=1_500.0,
                    step=100.0,
                    key="pumped_discharge_power"
                )
                pumped_discharge_eff = st.slider(
                    "Turbinenwirkungsgrad [%]",
                    min_value=80,
                    max_value=98,
                    value=90,
                    key="pumped_discharge_eff"
                ) / 100.0
            
            col3, col4 = st.columns(2)
            with col3:
                pumped_min_soc_pct = st.slider(
                    "Min SOC [%] (Totvolumen)",
                    min_value=0,
                    max_value=20,
                    value=5,
                    key="pumped_min_soc"
                )
            with col4:
                pumped_max_soc_pct = st.slider(
                    "Max SOC [%]",
                    min_value=80,
                    max_value=100,
                    value=100,
                    key="pumped_max_soc"
                )
            
            pumped_min_soc_mwh = (pumped_min_soc_pct / 100.0) * pumped_capacity_mwh
            pumped_max_soc_mwh = (pumped_max_soc_pct / 100.0) * pumped_capacity_mwh
            pumped_initial_soc_mwh = (pumped_initial_soc_pct / 100.0) * pumped_capacity_mwh
            
            pumped_roundtrip = pumped_charge_eff * pumped_discharge_eff * 100
            st.info(f"ℹ️ Roundtrip-Wirkungsgrad: {pumped_roundtrip:.1f}%")
            
            if st.button("💧 Pumpspeicher simulieren", type="primary", use_container_width=True):
                with st.spinner("Pumpspeicher-Simulation läuft..."):
                    try:
                        if "storage_results" not in st.session_state:
                            st.session_state.storage_results = {}
                        
                        # Nutze Ergebnis von Batterie falls vorhanden, sonst Ausgangsbilanz
                        input_df = st.session_state.storage_results.get("battery", energie_bilanz)
                        
                        result_df = sim.apply_pumped_hydro_storage(
                            input_df,
                            capacity_mwh=pumped_capacity_mwh,
                            max_charge_power_mw=pumped_max_charge_mw,
                            max_discharge_power_mw=pumped_max_discharge_mw,
                            charge_efficiency=pumped_charge_eff,
                            discharge_efficiency=pumped_discharge_eff,
                            initial_soc=pumped_initial_soc_mwh,
                            min_soc=pumped_min_soc_mwh,
                            max_soc=pumped_max_soc_mwh
                        )
                        
                        st.session_state.storage_results["pumped"] = result_df
                        st.success("✅ Pumpspeicher-Simulation abgeschlossen")
                        st.session_state.step_valid = True
                        
                    except Exception as e:
                        st.error(f"❌ Fehler bei der Pumpspeicher-Simulation: {e}")
                        st.session_state.step_valid = False
        
        # Tab 3: Wasserstoffspeicher
        with storage_tabs[2]:
            st.markdown("#### Wasserstoffspeicher (Langzeitspeicher)")
            st.caption("Typische Speicherdauer: Wochen bis Monate (saisonal) | Wirkungsgrad: ~35-40%")
            
            col1, col2 = st.columns(2)
            with col1:
                h2_capacity_mwh = st.number_input(
                    "Kapazität [MWh]",
                    min_value=100_000.0,
                    max_value=2_000_000.0,
                    value=500_000.0,
                    step=50_000.0,
                    key="h2_capacity"
                )
                h2_max_charge_mw = st.number_input(
                    "Max. Elektrolyseleistung [MW]",
                    min_value=100.0,
                    max_value=5_000.0,
                    value=1_000.0,
                    step=100.0,
                    key="h2_charge_power"
                )
                h2_charge_eff = st.slider(
                    "Elektrolyse-Wirkungsgrad [%]",
                    min_value=50,
                    max_value=80,
                    value=65,
                    key="h2_charge_eff"
                ) / 100.0
            
            with col2:
                h2_initial_soc_pct = st.slider(
                    "Initial SOC [%]",
                    min_value=0,
                    max_value=100,
                    value=0,
                    key="h2_initial_soc"
                )
                h2_max_discharge_mw = st.number_input(
                    "Max. Rückverstromungsleistung [MW]",
                    min_value=100.0,
                    max_value=5_000.0,
                    value=800.0,
                    step=100.0,
                    key="h2_discharge_power"
                )
                h2_discharge_eff = st.slider(
                    "Rückverstromungs-Wirkungsgrad [%]",
                    min_value=40,
                    max_value=70,
                    value=55,
                    key="h2_discharge_eff"
                ) / 100.0
            
            col3, col4 = st.columns(2)
            with col3:
                h2_min_soc_pct = st.slider(
                    "Min SOC [%]",
                    min_value=0,
                    max_value=10,
                    value=0,
                    key="h2_min_soc"
                )
            with col4:
                h2_max_soc_pct = st.slider(
                    "Max SOC [%]",
                    min_value=90,
                    max_value=100,
                    value=100,
                    key="h2_max_soc"
                )
            
            h2_min_soc_mwh = (h2_min_soc_pct / 100.0) * h2_capacity_mwh
            h2_max_soc_mwh = (h2_max_soc_pct / 100.0) * h2_capacity_mwh
            h2_initial_soc_mwh = (h2_initial_soc_pct / 100.0) * h2_capacity_mwh
            
            h2_roundtrip = h2_charge_eff * h2_discharge_eff * 100
            st.info(f"ℹ️ Roundtrip-Wirkungsgrad: {h2_roundtrip:.1f}%")
            st.warning("⚠️ Hinweis: Niedriger Wirkungsgrad ist typisch für H₂-Speicher (Elektrolyse + Rückverstromung)")
            
            if st.button("🔬 Wasserstoffspeicher simulieren", type="primary", use_container_width=True):
                with st.spinner("Wasserstoffspeicher-Simulation läuft..."):
                    try:
                        if "storage_results" not in st.session_state:
                            st.session_state.storage_results = {}
                        
                        # Nutze Ergebnis von Pumpspeicher oder Batterie falls vorhanden
                        input_df = st.session_state.storage_results.get(
                            "pumped", 
                            st.session_state.storage_results.get("battery", energie_bilanz)
                        )
                        
                        result_df = sim.apply_hydrogen_storage(
                            input_df,
                            capacity_mwh=h2_capacity_mwh,
                            max_charge_power_mw=h2_max_charge_mw,
                            max_discharge_power_mw=h2_max_discharge_mw,
                            charge_efficiency=h2_charge_eff,
                            discharge_efficiency=h2_discharge_eff,
                            initial_soc=h2_initial_soc_mwh,
                            min_soc=h2_min_soc_mwh,
                            max_soc=h2_max_soc_mwh
                        )
                        
                        st.session_state.storage_results["hydrogen"] = result_df
                        st.success("✅ Wasserstoffspeicher-Simulation abgeschlossen")
                        st.session_state.step_valid = True
                        
                    except Exception as e:
                        st.error(f"❌ Fehler bei der Wasserstoffspeicher-Simulation: {e}")
                        st.session_state.step_valid = False
        
        # Zeige Ergebnisse aller Speicher
        st.markdown("---")
        if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
            st.subheader("📊 Speicherergebnisse")
            
            if "battery" in st.session_state.storage_results:
                show_storage_results(
                    st.session_state.storage_results["battery"],
                    "🔋 Batteriespeicher",
                    winter_start,
                    winter_end,
                    summer_start,
                    summer_end
                )
                st.markdown("---")
            
            if "pumped" in st.session_state.storage_results:
                show_storage_results(
                    st.session_state.storage_results["pumped"],
                    "💧 Pumpspeicher",
                    winter_start,
                    winter_end,
                    summer_start,
                    summer_end
                )
                st.markdown("---")
            
            if "hydrogen" in st.session_state.storage_results:
                show_storage_results(
                    st.session_state.storage_results["hydrogen"],
                    "🔬 Wasserstoffspeicher",
                    winter_start,
                    winter_end,
                    summer_start,
                    summer_end
                )
            
            st.session_state.step_valid = True
        else:
            st.info("ℹ️ Keine Speichersimulation durchgeführt. Wähle einen Speichertyp aus und starte die Simulation.")
            st.session_state.step_valid = False
    
    def gesamt_validieren():
        st.header("6. 📋 Gesamtergebnisse & Zusammenfassung")
        
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
        st.subheader("⚡ Energiebilanz (ohne Speicher)")
        
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
            st.subheader("🔋 Speicher-Auswirkungen")
            
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
                    battery_charged = battery_df["Charged [MWh]"].sum()
                    battery_discharged = battery_df["Discharged [MWh]"].sum()
                    battery_losses = battery_charged - battery_discharged
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Geladen", f"{battery_charged/1_000:.0f} GWh")
                    with col2:
                        st.metric("Entladen", f"{battery_discharged/1_000:.0f} GWh")
                    with col3:
                        st.metric(
                            "Verluste",
                            f"{battery_losses/1_000:.0f} GWh",
                            delta=f"{(battery_losses/battery_charged*100):.1f}%",
                            delta_color="inverse"
                        )
                tab_idx += 1
            
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
                            f"{pumped_losses/1_000:.0f} GWh",
                            delta=f"{(pumped_losses/pumped_charged*100):.1f}%",
                            delta_color="inverse"
                        )
                tab_idx += 1
            
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
                            f"{h2_losses/1_000:.0f} GWh",
                            delta=f"{(h2_losses/h2_charged*100):.1f}%",
                            delta_color="inverse"
                        )
            
            # Verbesserungen durch Speicher (nutze letzten Speicher in der Kette)
            st.markdown("#### 📈 Gesamtverbesserung durch Speichersystem")
            
            # Nutze das letzte Ergebnis in der Kette
            final_result = None
            if "hydrogen" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["hydrogen"]
            elif "pumped" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["pumped"]
            elif "battery" in st.session_state.storage_results:
                final_result = st.session_state.storage_results["battery"]
            
            if final_result is not None:
                remaining_surplus_with_storage = final_result["Remaining Surplus [MWh]"].sum()
                remaining_deficit_with_storage = final_result["Remaining Deficit [MWh]"].sum()
                
                deficit_reduction = total_deficit - remaining_deficit_with_storage
                surplus_reduction = total_surplus - remaining_surplus_with_storage
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Defizit-Reduktion",
                        f"{deficit_reduction/1_000:.0f} GWh",
                        delta=f"{(deficit_reduction/total_deficit*100):.1f}%",
                        delta_color="normal"
                    )
                with col2:
                    st.metric(
                        "Verbleibendes Defizit",
                        f"{remaining_deficit_with_storage/1_000:.0f} GWh",
                        delta_color="inverse"
                    )
                with col3:
                    st.metric(
                        "Überschuss-Reduktion",
                        f"{surplus_reduction/1_000:.0f} GWh",
                        delta=f"{(surplus_reduction/total_surplus*100):.1f}%",
                        delta_color="normal"
                    )
                with col4:
                    st.metric(
                        "Verbleibender Überschuss",
                        f"{remaining_surplus_with_storage/1_000:.0f} GWh",
                        delta_color="inverse"
                    )
            
            st.markdown("---")
        
        # --- ABSCHNITT 4: Was muss noch getan werden? ---
        st.subheader("🎯 Handlungsbedarf")
        
        # Bestimme finalen Surplus/Deficit basierend auf aktiven Speichern
        if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
            # Nutze das letzte Ergebnis in der Speicherkette
            if "hydrogen" in st.session_state.storage_results:
                final_df = st.session_state.storage_results["hydrogen"]
            elif "pumped" in st.session_state.storage_results:
                final_df = st.session_state.storage_results["pumped"]
            else:
                final_df = st.session_state.storage_results["battery"]
            
            final_surplus = final_df["Remaining Surplus [MWh]"].sum()
            final_deficit = final_df["Remaining Deficit [MWh]"].sum()
        else:
            final_surplus = total_surplus
            final_deficit = total_deficit
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ⚠️ Abregelung notwendig")
            st.metric(
                "Überschuss muss abgeregelt werden",
                f"{final_surplus/1_000:.0f} GWh",
                help="Diese Energie kann nicht genutzt werden und muss abgeregelt werden."
            )
            if final_surplus > 0:
                abregelung_pct = (final_surplus / total_prod) * 100
                st.warning(f"💡 {abregelung_pct:.2f}% der Gesamterzeugung muss abgeregelt werden.")
        
        with col2:
            st.markdown("#### 🔌 Zusätzliche Erzeugung nötig")
            st.metric(
                "Defizit muss ausgeglichen werden",
                f"{final_deficit/1_000:.0f} GWh",
                help="Diese Energie fehlt und muss durch zusätzliche Erzeugung gedeckt werden."
            )
            if final_deficit > 0:
                deficit_pct = (final_deficit / total_cons) * 100
                st.warning(f"💡 {deficit_pct:.2f}% des Gesamtverbrauchs kann nicht gedeckt werden.")
        
        st.markdown("---")
        
        # --- ABSCHNITT 5: Empfehlungen ---
        st.subheader("💡 Empfehlungen")
        
        recommendations = []
        
        if final_deficit > 0:
            recommendations.append(
                f"🔴 **Zusätzliche Speicherkapazität**: {final_deficit/1_000:.0f} GWh Defizit erfordert mehr Speicher oder flexible Erzeugung."
            )
        
        if final_surplus > 1_000:  # > 1 GWh
            recommendations.append(
                f"🟡 **Power-to-X erwägen**: {final_surplus/1_000:.0f} GWh Überschuss könnte für Wasserstoff-Produktion genutzt werden."
            )
        
        if "storage_results" in st.session_state and "battery" in st.session_state.storage_results:
            battery_df = st.session_state.storage_results["battery"]
            avg_soc = battery_df["SOC [MWh]"].mean()
            capacity = st.session_state.get("battery_capacity", 10000)
            if avg_soc / capacity < 0.3:
                recommendations.append(
                    f"🟡 **Batteriespeicher unterausgelastet**: Durchschnittlicher SOC nur {(avg_soc/capacity*100):.1f}%. Kleinere Kapazität könnte ausreichen."
                )
        
        if "storage_results" in st.session_state and "pumped" in st.session_state.storage_results:
            pumped_df = st.session_state.storage_results["pumped"]
            avg_soc_pumped = pumped_df["SOC [MWh]"].mean()
            capacity_pumped = st.session_state.get("pumped_capacity", 50000)
            if avg_soc_pumped / capacity_pumped < 0.3:
                recommendations.append(
                    f"🟡 **Pumpspeicher unterausgelastet**: Durchschnittlicher SOC nur {(avg_soc_pumped/capacity_pumped*100):.1f}%."
                )
        
        if "storage_results" in st.session_state and "hydrogen" in st.session_state.storage_results:
            h2_df = st.session_state.storage_results["hydrogen"]
            h2_charged = h2_df["Charged [MWh]"].sum()
            h2_discharged = h2_df["Discharged [MWh]"].sum()
            if h2_charged > 0 and h2_discharged / h2_charged < 0.5:
                recommendations.append(
                    f"🟡 **Wasserstoffspeicher-Nutzung gering**: Nur {(h2_discharged/h2_charged*100):.1f}% des gespeicherten H₂ wird rückverstromt. Eventuell für Export/Industrie nutzen."
                )
        
        if total_surplus > total_deficit * 2:
            recommendations.append(
                "🟢 **Hoher Überschuss**: System produziert deutlich mehr als benötigt. Export oder zusätzliche Verbraucher erwägen."
            )
        
        if not recommendations:
            st.success("✅ Das System ist gut ausbalanciert. Keine kritischen Handlungsempfehlungen.")
        else:
            for rec in recommendations:
                st.markdown(rec)
        
        st.session_state.step_valid = True

    def ergebnisse_speichern():
        st.write("Ergebnisse werden gespeichert...")
        st.success("Ergebnisse erfolgreich gespeichert.")
    
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
    


SIMULATION_SCHRITTE = [
    "Daten auswählen",
    "Verbrauch Simulieren",
    "Erzeugung Simulieren",
    "Defizite anzeigen",
    "Speicher Simulieren",
    "Gesamt Ergebnisse validieren",
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
