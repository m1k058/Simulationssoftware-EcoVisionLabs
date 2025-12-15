# Standard Bibliotheken
import streamlit as st 
import pandas as pd
from datetime import datetime

# Eigene Imports
import data_processing.generation_profile as genPro
import data_processing.simulation as simu
import data_processing.col as col
import plotting.plotting_plotly_st as ply

# Manager Imports
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager


def create_date_range_selector(df: pd.DataFrame, key_suffix: str = "") -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Erstellt Zeitauswahl-Felder basierend auf den verfügbaren Daten im DataFrame.
    
    Args:
        df: DataFrame mit 'Zeitpunkt' Spalte
        key_suffix: Suffix für eindeutige Streamlit Keys
    
    Returns:
        Tuple mit (date_from, date_to) als pd.Timestamp
    """
    if "Zeitpunkt" not in df.columns:
        raise KeyError("DataFrame benötigt 'Zeitpunkt' Spalte")
    
    # Zeitpunkt konvertieren und Min/Max ermitteln
    df_time = pd.to_datetime(df["Zeitpunkt"])
    min_date = df_time.min()
    max_date = df_time.max()
    
    # Standard: 01. Mai - 07. Mai (oder erste verfügbare Woche)
    year = min_date.year
    default_start = pd.Timestamp(year=year, month=5, day=1)
    default_end = pd.Timestamp(year=year, month=5, day=7)
    
    # Falls Mai nicht im Datensatz, nimm erste Woche der verfügbaren Daten
    if default_start < min_date or default_start > max_date:
        default_start = min_date
        default_end = min_date + pd.Timedelta(days=7)
        if default_end > max_date:
            default_end = max_date
    
    # Zeitauswahl UI
    col1, col2, col3 = st.columns(3)
    with col1:
        date_from = st.date_input(
            "Von",
            value=default_start.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            format="DD.MM.YYYY",
            key=f"date_from_{key_suffix}"
        )
    with col2:
        date_to = st.date_input(
            "Bis",
            value=default_end.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            format="DD.MM.YYYY",
            key=f"date_to_{key_suffix}"
        )
    with col3:
        holeYear = st.button("Ganzes Jahr anzeigen", key=f"full_year_btn_{key_suffix}", on_click=lambda: None)
    
    # Konvertiere zu Timestamp (bis enthält den ganzen Tag)
    if holeYear:
        date_from_ts = min_date
        date_to_ts = max_date
    else:
        date_from_ts = pd.Timestamp(date_from)
        date_to_ts = pd.Timestamp(date_to, hour=23, minute=59, second=59)
    
    return date_from_ts, date_to_ts


def standard_simulation_page() -> None:
    st.title("Simulation")
    st.caption("Eine Vollständige Simulation basierend auf vordefinierten Studien und Parametern.")
    sidebar = st.sidebar
    
    # Überprüfe ob DataManager, ConfigManager, ScenarioManager geladen sind
    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")

    ## =================================== ##
    ##          Szenario Auswahl           ##
    ## =================================== ##

    # öffne Datei-Uploader für Szenario YAML
    st.subheader("Szenario Auswahl")
    uploaded_file = st.file_uploader("Lade ein Szenario YAML Datei hoch", type=["yaml"], key="scenario_uploader")
    
    # Buttons unter dem Uploader
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button(":material/upload_file: Datei laden", width='stretch'):
            if uploaded_file is not None:
                try:
                    st.session_state.sm.load_scenario(uploaded_file)
                    st.success("✅ Szenario erfolgreich geladen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler beim Laden: {e}")
            else:
                st.warning("⚠️ Bitte wähle zuerst eine Datei aus.")
    
    with col_btn2:
        if st.button(":material/assignment: Beispiel laden", width='stretch'):
            try:
                from pathlib import Path
                # Scenarios folder is at project root, not in source-code
                example_path = Path(__file__).resolve().parent.parent.parent / "scenarios" / "Szenario_Beispiel_SW.yaml"
                if example_path.exists():
                    st.session_state.sm.load_scenario(example_path)
                    st.success("✅ Beispiel-Szenario geladen!")
                    st.rerun()
                else:
                    st.error(f"❌ Beispieldatei nicht gefunden: {example_path}")
            except Exception as e:
                st.error(f"❌ Fehler beim Laden des Beispiels: {e}")
    
    with col_btn3:
        if st.button(":material/undo: Zurücksetzen", width='stretch'):
            st.session_state.sm.current_scenario = {}
            st.session_state.sm.current_path = None
            st.success("✅ Datei gelöscht!")
            st.rerun()
    
    # Info wenn kein Szenario geladen ist
    if st.session_state.sm.scenario_name is None:
        st.info("Bitte lade eine Szenario YAML Datei hoch, um fortzufahren.")

    # Zeige die geladenen Szenarien an
    if st.session_state.sm is not None and st.session_state.sm.scenario_name is not None:
        metadata = st.session_state.sm.scenario_data.get("metadata", {})
        years = metadata.get("valid_for_years", [])
        with st.container(border=True):
            st.markdown("## Szenario Informationen")
            st.markdown(f"**Name:** :blue[{st.session_state.sm.scenario_name}]")
            st.markdown(f"**Beschreibung:** :blue[{st.session_state.sm.scenario_description}]")
            st.markdown(f"**Version:** :blue[{metadata.get('version', 'N/A')}]")
            st.markdown(f"**Autor:** :blue[{metadata.get('author', 'N/A')}]")
            st.markdown(
                f"**Gültig für Jahre:** :blue[{', '.join(map(str, years)) if isinstance(years, (list, tuple)) else years}]"
            )

        # Szenario Daten anzeigen    
        with st.popover("Szenario Daten"):
            st.subheader("Szenario Rohdaten")

            # Szenario-Daten abrufen
            scenario = st.session_state.sm.scenario_data
            
            # Verfügbare Jahre aus dem Szenario
            valid_years = scenario.get("metadata", {}).get("valid_for_years", [])
            selected_year = st.selectbox("Wähle das Simulationsjahr", valid_years)
            
            # Erzeugungskapazitäten für das ausgewählte Jahr
            gen_capacities = st.session_state.sm.get_generation_capacities(year=selected_year)
            
            # Verbrauchsdaten für das ausgewählte Jahr
            load_demand = st.session_state.sm.get_load_demand(year=selected_year)
            
            st.write(f"**Simulationsjahr: {selected_year}**")

            # Tabs für verschiedene Ansichten
            tab1, tab2, tab3 = st.tabs(["Erzeugung", "Verbrauch", "Speicher"])
            
            with tab1:
                st.subheader("Installierte Erzeugungskapazitäten")
                col_cap = st.columns(2)
                with col_cap[0]:
                    pv = st.session_state.sm.get_generation_capacities("Photovoltaik", selected_year)
                    st.metric("Photovoltaik", f"{pv:,} MW" if isinstance(pv, (int, float)) else "N/A")
                    
                    wind_on = st.session_state.sm.get_generation_capacities("Wind_Onshore", selected_year)
                    st.metric("Wind Onshore", f"{wind_on:,} MW" if isinstance(wind_on, (int, float)) else "N/A")
                    
                    wind_off = st.session_state.sm.get_generation_capacities("Wind_Offshore", selected_year)
                    st.metric("Wind Offshore", f"{wind_off:,} MW" if isinstance(wind_off, (int, float)) else "N/A")

                    bio = st.session_state.sm.get_generation_capacities("Biomasse", selected_year)
                    st.metric("Biomasse", f"{bio:,} MW" if isinstance(bio, (int, float)) else "N/A")
                    
                    hydro = st.session_state.sm.get_generation_capacities("Wasserkraft", selected_year)
                    st.metric("Wasserkraft", f"{hydro:,} MW" if isinstance(hydro, (int, float)) else "N/A")

                with col_cap[1]:
                    
                    gas = st.session_state.sm.get_generation_capacities("Erdgas", selected_year)
                    st.metric("Erdgas", f"{gas:,} MW" if isinstance(gas, (int, float)) else "N/A")

                    hard_coal = st.session_state.sm.get_generation_capacities("Steinkohle", selected_year)
                    st.metric("Steinkohle", f"{hard_coal:,} MW" if isinstance(hard_coal, (int, float)) else "N/A")
                    
                    lignite = st.session_state.sm.get_generation_capacities("Braunkohle", selected_year)
                    st.metric("Braunkohle", f"{lignite:,} MW" if isinstance(lignite, (int, float)) else "N/A")
                    
                    nuclear = st.session_state.sm.get_generation_capacities("Kernenergie", selected_year)
                    st.metric("Kernenergie", f"{nuclear:,} MW" if isinstance(nuclear, (int, float)) else "N/A")
                    
                
                # DataFrame für Tabelle
                gen_data = st.session_state.sm.get_generation_capacities(year=selected_year)
                cap_df = {
                    "Technologie": list(gen_data.keys()),
                    "Kapazität [MW]": [v for v in gen_data.values() if isinstance(v, (int, float))]
                }
                if cap_df["Kapazität [MW]"]:  # Nur anzeigen wenn Daten vorhanden
                    st.dataframe(cap_df)
            
            with tab2:
                st.subheader("Verbrauch nach Sektor")
                for sector, data in load_demand.items():
                    if isinstance(data, dict) and selected_year in data:
                        st.metric(f"{sector}", f"{data[selected_year]} TWh")
            
            with tab3:
                st.subheader("Speicher-Kapazitäten")
                
                # Hole Speicherdaten aus dem Szenario
                storage_data = st.session_state.sm.scenario_data.get("target_storage_capacities", {})
                
                if storage_data:
                    speicher = st.segmented_control("Speichertyp auswählen", ["Batteriespeicher", "Pumpspeicher", "Wasserstoffspeicher"], default="Batteriespeicher")
                    
                    # Batteriespeicher
                    if speicher == "Batteriespeicher":
                        battery = storage_data.get("battery_storage", {}).get(selected_year, {})
                        if battery:
                            st.markdown("#### 🔋 Batteriespeicher")
                            col_bat = st.columns(2)
                            with col_bat[0]:
                                st.metric("Kapazität", f"{battery.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{battery.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_bat[1]:
                                st.metric("Max. Entladeleistung", f"{battery.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{battery.get('initial_soc', 0):.1%}")
                    
                    # Pumpspeicher
                    if speicher == "Pumpspeicher":
                        pumped = storage_data.get("pumped_hydro_storage", {}).get(selected_year, {})
                        if pumped:
                            st.markdown("#### 💧 Pumpspeicher")
                            col_pump = st.columns(2)
                            with col_pump[0]:
                                st.metric("Kapazität", f"{pumped.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{pumped.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_pump[1]:
                                st.metric("Max. Entladeleistung", f"{pumped.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{pumped.get('initial_soc', 0):.1%}")
                    
                    # Wasserstoffspeicher
                    if speicher == "Wasserstoffspeicher":
                        h2 = storage_data.get("h2_storage", {}).get(selected_year, {})
                        if h2:
                            st.markdown("#### 🔵 Wasserstoffspeicher")
                            col_h2 = st.columns(2)
                            with col_h2[0]:
                                st.metric("Kapazität", f"{h2.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{h2.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_h2[1]:
                                st.metric("Max. Entladeleistung", f"{h2.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{h2.get('initial_soc', 0):.1%}")
                else:
                    st.info("Keine Speicherdaten im Szenario definiert.")

        # Szenario Rohdaten anzeigen    
        with st.popover("Szenario Rohdaten"):
            st.subheader("Szenario Rohdaten")
            st.json(st.session_state.sm.scenario_data)

    st.markdown("---")

    ## =================================== ##
    ##       Verbrauch Simulation          ##
    ## =================================== ##

    st.markdown("## Verbrauchssimulation")

    # Session keys müssen erhalten bleiben
    if "simuConRUN" not in st.session_state:
        st.session_state.simuConRUN = 0
    if "resultsConSim" not in st.session_state:
        st.session_state.resultsConSim = {}

    if st.button("Verbrauchssimulation starten"):

        # Verbrauchsprofile holen
        last_H = st.session_state.dm.get(st.session_state.sm.scenario_data
                                         ["target_load_demand_twh"]["Haushalt_Basis"]["load_profile"])
        last_G = st.session_state.dm.get(st.session_state.sm.scenario_data
                                         ["target_load_demand_twh"]["Gewerbe_Basis"]["load_profile"])
        last_L = st.session_state.dm.get(st.session_state.sm.scenario_data
                                         ["target_load_demand_twh"]["Landwirtschaft_Basis"]["load_profile"])
        
        # Verbrauch Zielwerte holen
        targets = st.session_state.sm.scenario_data["target_load_demand_twh"]

        # Simulation ausführen und Ergebnisse speichern
        st.session_state.resultsConSim = {}
        for year in years:
            df_res = simu.simulate_consumption(
                lastH=last_H, 
                lastG=last_G, 
                lastL=last_L,
                lastZielH=targets["Haushalt_Basis"][year], 
                lastZielG=targets["Gewerbe_Basis"][year], 
                lastZielL=targets["Landwirtschaft_Basis"][year],
                simu_jahr=year
            )
            st.session_state.resultsConSim[year] = df_res
            st.session_state.simuConRUN = 1

    if st.session_state.simuConRUN >= 1:    
        # Anzeige der Ergebnisse Tabele/visuell
        tab1, tab2 = st.tabs(["Tabelle und Download", "Visuelle Darstellung"], default="Visuelle Darstellung")

        # Tabs erstellen und DataFrames anzeigen
        with tab1:
            selected_year_con_tab1 = st.segmented_control(
                "Bitte Jahr auswählen",
                [str(year) for year in years],
                default=str(years[0]),
                selection_mode="single",
                key="segmented_year_con_table"
            )
            try:
                selected_year_con = int(selected_year_con_tab1)
            except (ValueError, TypeError):
                selected_year_con = years[0]

            st.subheader(f"Verbrauchssimulation {selected_year_con}")
            st.dataframe(st.session_state.resultsConSim[selected_year_con], width='stretch')
            # Konvertiere zu CSV mit ; als Separator und , als Dezimalzeichen
            csv_data = st.session_state.resultsConSim[selected_year_con].to_csv(
                index=False,
                sep=';',
                decimal=','
            ).encode('utf-8')
            st.download_button(
                label="Download als CSV",
                data=csv_data,
                file_name=f'verbrauchssimulation_{selected_year_con}.csv',
                mime='text/csv'
            )

        with tab2:
            selected_year_con_tab2 = st.segmented_control(
                "Bitte Jahr auswählen",
                [str(year) for year in years],
                default=str(years[0]),
                selection_mode="single",
                key="segmented_year_con_viz"
            )
            try:
                selected_year_con_viz = int(selected_year_con_tab2)
            except (ValueError, TypeError):
                selected_year_con_viz = years[0]
            
            st.subheader(f"Visuelle Darstellung {selected_year_con_viz}")

            plot_df = st.session_state.resultsConSim[selected_year_con_viz]

            # Zeitauswahl mit Helper-Funktion
            date_from_con, date_to_con = create_date_range_selector(plot_df, key_suffix=f"consumption_{selected_year_con_viz}")

            fig = ply.create_consumption_plot(
                plot_df,
                title="",
                date_from=date_from_con,
                date_to=date_to_con
            )
            st.plotly_chart(fig)





    st.markdown("---")

    ## =================================== ##
    ##       Erzeugung Simulation          ##
    ## =================================== ##

    st.markdown("## Erzeugungssimulation")

    # Session keys müssen erhalten bleiben
    if "simuGenRUN" not in st.session_state:
        st.session_state.simuGenRUN = 0
    if "resultsGenSim" not in st.session_state:
        st.session_state.resultsGenSim = {}

    if st.button("Erzeugungssimulation starten"):
        
        # Lade die SMARD Daten
        smard_generation_2020 = st.session_state.dm.get("SMARD_2020-2025_Erzeugung")
        smard_generation_2015 = st.session_state.dm.get("SMARD_2015-2019_Erzeugung")

        smard_installed_2020 = st.session_state.dm.get("SMARD_Installierte Leistung 2020-2025")
        smard_installed_2015 = st.session_state.dm.get("SMARD_Installierte Leistung 2015-2019")

        # Verbinde die SMARD Daten
        smard_generation = pd.concat([smard_generation_2015, smard_generation_2020])
        smard_installed = pd.concat([smard_installed_2015, smard_installed_2020])

        # Ziel Kapazitäten aus dem Szenario
        target_capacities = st.session_state.sm.get_generation_capacities()

        # weather_profiles rausholen
        profile = st.session_state.sm.scenario_data.get("weather_generation_profiles", {})

        
        # Simulation ausführen und Ergebnisse speichern
        st.session_state.resultsGenSim = {}
        for year in years:
            df_res = simu.simulate_production(
                st.session_state.cfg,
                smard_generation,
                smard_installed,
                target_capacities,
                profile[year]["Wind_Onshore"],
                profile[year]["Wind_Offshore"],
                profile[year]["Photovoltaik"],
                year
            )
            st.session_state.resultsGenSim[year] = df_res
            st.session_state.simuGenRUN = 1


    if st.session_state.simuGenRUN >= 1:    
        # Anzeige der Ergebnisse Tabele/visuell
        tab1, tab2 = st.tabs(["Tabelle und Download", "Visuelle Darstellung"], default="Visuelle Darstellung")


        # Tabs erstellen und DataFrames anzeigen
        with tab1:
            selected_year_tab1 = st.segmented_control(
                "Bitte Jahr auswählen",
                [str(year) for year in years],
                default=str(years[0]),
                selection_mode="single",
                key="segmented_year_table"
            )
            # Konvertiere die Auswahl zurück zu int (falls Jahre als int vorliegen)
            try:
                selected_year = int(selected_year_tab1)
            except (ValueError, TypeError):
                selected_year = years[0]

            st.subheader(f"Erzeugungssimulation {selected_year}")
            st.dataframe(st.session_state.resultsGenSim[selected_year], width='stretch')
            # Konvertiere zu CSV mit ; als Separator und , als Dezimalzeichen
            csv_data = st.session_state.resultsGenSim[selected_year].to_csv(
                index=False,
                sep=';',
                decimal=','
            ).encode('utf-8')
            st.download_button(
                label="Download als CSV",
                data=csv_data,
                file_name=f'erzeugungssimulation_{selected_year}.csv',
                mime='text/csv'
            )

        with tab2:
            selected_year_tab2 = st.segmented_control(
                "Bitte Jahr auswählen",
                [str(year) for year in years],
                default=str(years[0]),
                selection_mode="single",
                key="segmented_year_viz"
            )
            try:
                selected_year_viz = int(selected_year_tab2)
            except (ValueError, TypeError):
                selected_year_viz = years[0]
            st.subheader(f"Visuelle Darstellung {selected_year_viz}")

            plot_df = st.session_state.resultsGenSim[selected_year_viz]

            # Zeitauswahl mit Helper-Funktion
            date_from_gen, date_to_gen = create_date_range_selector(plot_df, key_suffix=f"generation_{selected_year_viz}")


            fig = ply.create_generation_plot(
                    plot_df,
                    title="",
                    date_from=date_from_gen,
                    date_to=date_to_gen)
            st.plotly_chart(fig)
    

    ## =================================== ##
    ##          Bilanz Berechnung          ##
    ## =================================== ##
    st.markdown("[Zur Verbrauchssimulation](#verbrauchssimulation)")

    st.markdown("---")
    st.markdown("## Bilanz Berechnung")

    if st.session_state.simuGenRUN <= 0 or st.session_state.simuConRUN <= 0:
        st.info("Bitte führe zuerst die Verbrauchs- und Erzeugungssimulationen durch.")
    else:
        if st.button("Bilanz Berechnung starten"):
            # Bilanz Berechnung
            st.session_state.resultsBalanceSim = {}
            for year in years:
                df_gen = st.session_state.resultsGenSim[year]
                df_con = st.session_state.resultsConSim[year]
                df_balance = simu.calc_balance(df_gen, df_con, year)
                st.session_state.resultsBalanceSim[year] = df_balance

        if "resultsBalanceSim" in st.session_state and st.session_state.resultsBalanceSim:
            # Anzeige der Ergebnisse Tabele/visuell
            tab1, tab2 = st.tabs(["Tabelle und Download", "Visuelle Darstellung"], default="Visuelle Darstellung")

            # Tabs erstellen und DataFrames anzeigen
            with tab1:
                selected_year_bal_tab1 = st.segmented_control(
                    "Bitte Jahr auswählen",
                    [str(year) for year in years],
                    default=str(years[0]),
                    selection_mode="single",
                    key="segmented_year_bal_table"
                )
                try:
                    selected_year_bal = int(selected_year_bal_tab1)
                except (ValueError, TypeError):
                    selected_year_bal = years[0]

                st.subheader(f"Bilanz {selected_year_bal}")
                st.dataframe(st.session_state.resultsBalanceSim[selected_year_bal], width='stretch')
                # Konvertiere zu CSV mit ; als Separator und , als Dezimalzeichen
                csv_data = st.session_state.resultsBalanceSim[selected_year_bal].to_csv(
                    index=False,
                    sep=';',
                    decimal=','
                ).encode('utf-8')
                st.download_button(
                    label="Download als CSV",
                    data=csv_data,
                    file_name=f'bilanz_{selected_year_bal}.csv',
                    mime='text/csv'
                )

            with tab2:
                selected_year_bal_tab2 = st.segmented_control(
                    "Bitte Jahr auswählen",
                    [str(year) for year in years],
                    default=str(years[0]),
                    selection_mode="single",
                    key="segmented_year_bal_viz"
                )
                try:
                    selected_year_bal_viz = int(selected_year_bal_tab2)
                except (ValueError, TypeError):
                    selected_year_bal_viz = years[0]
                
                st.subheader(f"Visuelle Darstellung Bilanz {selected_year_bal_viz}")

                bal_plot_df = st.session_state.resultsBalanceSim[selected_year_bal_viz]

                # Zeitauswahl mit Helper-Funktion
                date_from_bal, date_to_bal = create_date_range_selector(bal_plot_df, key_suffix=f"balance_{selected_year_bal_viz}")

                fig = ply.create_balance_area_plot(
                        bal_plot_df,
                        title=" ",
                        date_from=date_from_bal,
                        date_to=date_to_bal)
                st.plotly_chart(fig)

    ## =================================== ##
    ##             Gen X Con               ##
    ## =================================== ##
    st.markdown("[Zur Verbrauchssimulation](#verbrauchssimulation) | [Zur Erzeugungssimulation](#erzeugungssimulation)")

    st.markdown("---")
    st.markdown("## Erzeugung X Verbrauch")

    coolViz = st.session_state.resultsGenSim[years[0]].copy()
    coolViz["Skalierte Netzlast [MWh]"] = st.session_state.resultsConSim[years[0]]["Gesamt [MWh]"]
    
    date_from_cool, date_to_cool = create_date_range_selector(coolViz, key_suffix=f"coolviz_{years[0]}")

    fig = ply.create_generation_with_load_plot(
        df=coolViz,
        title=" ",
        date_from=date_from_cool,
        date_to=date_to_cool)
    st.plotly_chart(fig)


    ## =================================== ##
    ##         Speicher Berechnung         ##
    ## =================================== ##

    st.markdown("[Zur Verbrauchssimulation](#verbrauchssimulation) | [Zur Erzeugungssimulation](#erzeugungssimulation) | [Zur Bilanzberechnung](#bilanz-berechnung)")
    st.markdown("---")
    st.markdown("## Speicher Berechnung")

    if st.session_state.simuGenRUN <= 0 or st.session_state.simuConRUN <= 0:
        st.info("Bitte führe zuerst die Verbrauchs- und Erzeugungssimulationen durch.")
    else:

        # Session keys müssen erhalten bleiben
        if "simuStorRUN" not in st.session_state:
            st.session_state.simuStorRUN = 0
        if "resultsStorSim" not in st.session_state:
            st.session_state.resultsStorSim = {}

        if st.button("Speichersimulation starten"):
            
            # Stelle sicher, dass resultsStorSim ein Dictionary ist
            if not isinstance(st.session_state.resultsStorSim, dict):
                st.session_state.resultsStorSim = {}

            for year in years:

                df_balance = st.session_state.resultsBalanceSim[year].copy()
                
                # Hole Speicher-Konfigurationen für das spezifische Jahr
                try:
                    battery_config = st.session_state.sm.get_storage_capacities("battery_storage", year)
                    pumped_config = st.session_state.sm.get_storage_capacities("pumped_hydro_storage", year)
                    h2_config = st.session_state.sm.get_storage_capacities("h2_storage", year)
                except Exception as e:
                    st.error(f"❌ Fehler beim Laden der Speicher-Konfiguration für Jahr {year}: {e}")
                    continue

                # Batteriesimulation
                try:
                    result_battery = simu.simulate_battery_storage(
                        df_balance,
                        battery_config["installed_capacity_mwh"],
                        battery_config["max_charge_power_mw"],
                        battery_config["max_discharge_power_mw"],
                        battery_config["initial_soc"]
                    )
                    st.session_state.simuStorRUN += 1
                except Exception as e:
                    st.error(f"❌ Fehler bei der Batteriesimulation für Jahr {year}: {e}")
                    continue
                
                # Pumpspeichersimulation
                try:
                    result_pump = simu.simulate_pump_storage(
                        result_battery,
                        pumped_config["installed_capacity_mwh"],
                        pumped_config["max_charge_power_mw"],
                        pumped_config["max_discharge_power_mw"],
                        pumped_config["initial_soc"]
                    )
                    st.session_state.simuStorRUN += 1
                except Exception as e:
                    st.error(f"❌ Fehler bei der Pumpspeichersimulation für Jahr {year}: {e}")
                    continue
                
                # Wasserstoffspeichersimulation
                try:
                    result_h2 = simu.simulate_hydrogen_storage(
                        result_pump,
                        h2_config["installed_capacity_mwh"],
                        h2_config["max_charge_power_mw"],
                        h2_config["max_discharge_power_mw"],
                        h2_config["initial_soc"]
                    )
                    st.session_state.simuStorRUN += 1
                    # Speichere finales Ergebnis im Dictionary
                    st.session_state.resultsStorSim[year] = result_h2
                except Exception as e:
                    st.error(f"❌ Fehler bei der Wasserstoffspeichersimulation für Jahr {year}: {e}")
                    continue

        if st.session_state.simuStorRUN >= 1:
            # Anzeige der Ergebnisse Tabele/visuell
            tab1, tab2 = st.tabs(["Tabelle und Download", "Visuelle Darstellung"])

            # Tabs erstellen und DataFrames anzeigen
            with tab1:
                selected_year_stor_tab1 = st.segmented_control(
                    "Bitte Jahr auswählen",
                    [str(year) for year in years],
                    default=str(years[0]),
                    selection_mode="single",
                    key="segmented_year_stor_table"
                )
                try:
                    selected_year_stor = int(selected_year_stor_tab1)
                except (ValueError, TypeError):
                    selected_year_stor = years[0]

                st.subheader(f"Speichersimulation {selected_year_stor}")
                st.dataframe(st.session_state.resultsStorSim[selected_year_stor], width='stretch')
                # Konvertiere zu CSV mit ; als Separator und , als Dezimalzeichen
                csv_data = st.session_state.resultsStorSim[selected_year_stor].to_csv(
                    index=False,
                    sep=';',
                    decimal=','
                ).encode('utf-8')
                st.download_button(
                    label="Download als CSV",
                    data=csv_data,
                    file_name=f'speichersimulation_{selected_year_stor}.csv',
                    mime='text/csv'
                )

            with tab2:
                selected_year_stor_tab2 = st.segmented_control(
                    "Bitte Jahr auswählen",
                    [str(year) for year in years],
                    default=str(years[0]),
                    selection_mode="single",
                    key="segmented_year_stor_viz"
                )
                try:
                    selected_year_stor_viz = int(selected_year_stor_tab2)
                except (ValueError, TypeError):
                    selected_year_stor_viz = years[0]
                
                st.subheader(f"Visuelle Darstellung Speichersimulation {selected_year_stor_viz}")

                stor_plot_df = st.session_state.resultsStorSim[selected_year_stor_viz]
                bal_plot_df = st.session_state.resultsBalanceSim[selected_year_stor_viz]
                stor_plot_df['Bilanz [MWh]'] = bal_plot_df['Bilanz [MWh]']
                

                # Zeitauswahl mit Helper-Funktion
                date_from_stor, date_to_stor = create_date_range_selector(stor_plot_df, key_suffix=f"storage_{selected_year_stor_viz}")

                # 1. Geordnete Jahresdauerlinie der Residuallast
                st.markdown("### Geordnete Jahresdauerlinie der Residuallast")
                st.caption("Zeigt die sortierte Bilanz über das Jahr - mit und ohne Speicher")
                fig_duration = ply.create_duration_curve_plot(
                    stor_plot_df,
                    title=" "
                )
                st.plotly_chart(fig_duration)

                # 2. State of Charge (SOC) - Stacked Area
                st.markdown("### State of Charge (SOC) der Speicher")
                st.caption("Zeigt den Ladestand aller Speicher über die Zeit")
                fig_soc = ply.create_soc_stacked_plot(
                    stor_plot_df,
                    title=" ",
                    date_from=date_from_stor,
                    date_to=date_to_stor
                )
                st.plotly_chart(fig_soc)