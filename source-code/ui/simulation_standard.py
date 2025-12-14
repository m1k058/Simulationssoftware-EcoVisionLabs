import streamlit as st 
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager
import pandas as pd

# Eigene Imports
import data_processing.generation_profile as genPro
import data_processing.simulation as simu
import data_processing.col as col

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
    st.warning("🏗️ WARNUNG: Diese Funktion ist noch in der Entwicklung.")

    ## ================================== ##
    ##                                    ##
    ##          SIMULATION HIER           ##
    ##                                    ##
    ##              @Julian               ##
    ##                                    ##      
    ## ================================== ##

    st.markdown("---")

    ## =================================== ##
    ##       Erzeugung Simulation          ##
    ## =================================== ##

    st.markdown("## Erzeugungssimulation")

    # Session keys müssen erhalten bleiben, sonst verschwinden die Ergebnisse nach jedem UI-Refresh
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
        tab1, tab2 = st.tabs(["Tabelle und Download", "Visuelle Darstellung"])


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
            # Einfache visuelle Darstellung (z. B. Linienplot, falls Zeitreihen vorhanden)
            try:
                False
            except Exception:
                st.write("Visualisierung wird später ergänzt.")