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
import plotting.plotting_formated_st as pltf
import plotting.plotting_plotly_st as pltp
from constants import ENERGY_SOURCES

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
        st.header("Daten auswählen:")

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
            
        st.header("Verbrauch Simulieren:")

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
            "Verwende Verbrauchs-Lastprofile für Skalierung", 
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
            st.subheader("📊 Simulationsergebnis")
            
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
                    st.info(f"📅 Angezeigt: Winterwoche (13.-19. Feb) und Sommerwoche (3.-9. Juli) {st.session_state.sim_jahr}")
                
            except Exception as e:
                st.warning(f"⚠️ Fehler beim Filtern der Wochen: {e}. Zeige alle Daten.")
                df_plot = st.session_state.df_simulation_con
            
            # Plotly Visualisierung
            try:
                # Toggle zwischen Wochenansicht und Jahresansicht
                view_mode = st.radio(
                    "Ansicht wählen:",
                    ["📅 Zwei Wochen (Winter & Sommer)", "📊 Gesamtes Jahr"],
                    horizontal=True,
                    key="verbrauch_view_mode"
                )
                
                if view_mode == "📅 Zwei Wochen (Winter & Sommer)":
                    # Separiere Winter- und Sommerwoche für separate Plots
                    df_winter_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 2]
                    df_summer_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 7]
                    
                    # Zwei Spalten für Winter und Sommer
                    col_winter, col_summer = st.columns(2)
                    
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
                    
                else:  # Gesamtes Jahr
                    st.markdown("#### 📆 Verbrauch über das gesamte Jahr")
                    # Verwende vollständige Daten
                    df_full_year = st.session_state.df_simulation_con
                    
                    fig_year = pltp.create_line_plot(
                        df_full_year,
                        y_axis="Skalierte Netzlast [MWh]",
                        title=f"Verbrauchssimulation {st.session_state.sim_jahr} (Studie: {st.session_state.sim_studie_verbrauch})",
                        description=f"Skalierter Verbrauch basierend auf Referenzjahr {st.session_state.sim_referenz_jahr}",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_year, use_container_width=True)
                    
                    # Statistiken für das gesamte Jahr
                    df_stats = df_full_year
                
                # Zusätzliche Statistiken
                col1, col2, col3 = st.columns(3)
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
            st.info("ℹ️ Klicke auf 'Simulation starten' um die Verbrauchssimulation durchzuführen.")
            st.session_state.step_valid = False
    



    def erzeugung_simulieren():
        st.header("Erzeugung Simulieren:")
        
        # Finde Index der vorher ausgewählten Studie
        studie_index = 2
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
            st.subheader("📊 Erzeugungssimulation Ergebnis")
            
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
                    st.info(f"📅 Angezeigt: Winterwoche (13.-19. Feb) und Sommerwoche (3.-9. Juli) {st.session_state.sim_jahr}")
                
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
                    col_winter, col_summer = st.columns(2)
                    
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
                    col_metrics, col_pie = st.columns([1, 1])
                    
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
            st.info("ℹ️ Klicke auf 'Erzeugung simulieren' um die Erzeugungssimulation durchzuführen.")
            st.session_state.step_valid = False

    def defizite_ausgleichen():
        st.write("Defizite werden mit Speicher ausgeglichen...")
        st.success("Defizit-Ausgleich abgeschlossen.")
    
    def gesamt_validieren():
        st.write("Gesamtergebnisse werden validiert...")
        st.success("Gesamtvalidierung abgeschlossen.")

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
        defizite_ausgleichen()
    elif aktiver_schritt_index == 4:
        gesamt_validieren()
    elif aktiver_schritt_index == 5:
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


SIMULATION_SCHRITTE = [
    "Daten auswählen",
    "Verbrauch Simulieren",
    "Erzeugung Simulieren",
    "Defizite mit Speicher ausgleichen",
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
