# Standard Bibliotheken
import streamlit as st 
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# Eigene Imports
from data_processing.simulation_engine import SimulationEngine
import plotting.plotting_plotly_st as ply
import plotting.economic_plots as econ_ply
# KPI-System Imports
from ui.kpi_dashboard import render_kpi_dashboard, normalize_storage_config


def standard_simulation_page() -> None:
    """Single Mode: Ein Szenario laden und simulieren"""
    st.title("Simulation (Single Mode)")
    st.caption("Laden Sie ein Szenario und führen Sie eine vollständige Simulation durch.")

    # -----------------------------------------#
    #          Szenario Laden Bereich          #
    # -----------------------------------------#

    # check IF DataManager, ConfigManager, ScenarioManager geladen sind
    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")
        return
    uploaded_file = st.file_uploader("Lade ein Szenario YAML Datei hoch", type=["yaml"], key="scenario_uploader")
    
    # Lade / Beispiel / Zurücksetzen Buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button(":material/upload_file: Datei laden", width='stretch'):
            if uploaded_file is not None:
                try:
                    st.session_state.sm.load_scenario(uploaded_file)
                    storage_config = st.session_state.sm.scenario_data.get("target_storage_capacities", {})
                    st.session_state.storage_config = normalize_storage_config(storage_config)
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
                example_path = Path(__file__).resolve().parent.parent.parent / "scenarios" / "Szenario_Beispiel_SW.yaml"
                if example_path.exists():
                    st.session_state.sm.load_scenario(example_path)
                    storage_config = st.session_state.sm.scenario_data.get("target_storage_capacities", {})
                    st.session_state.storage_config = normalize_storage_config(storage_config)
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
    
    # loaded Szenario check
    if st.session_state.sm.scenario_name is None:
        st.info("Bitte lade eine Szenario YAML Datei hoch, um fortzufahren.")

    # -----------------------------------------#
    #       Szenario Informationen Bereich     #
    # -----------------------------------------#

    # show geladenes Szenario
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
    
        with st.popover("📋 Szenario Daten"):
            st.subheader("Szenario Rohdaten")

            scenario = st.session_state.sm.scenario_data
            
            # available Jahre aus Szenario
            valid_years = scenario.get("metadata", {}).get("valid_for_years", [])
            selected_year = st.selectbox("Wähle das Simulationsjahr", valid_years)
            
            # Erzeugungskapazitäten
            gen_capacities = st.session_state.sm.get_generation_capacities(year=selected_year)
            load_demand = st.session_state.sm.get_load_demand(year=selected_year)
            storage_data = st.session_state.sm.scenario_data.get("target_storage_capacities", {})
            
            st.write(f"**Simulationsjahr: {selected_year}**")

            # Details in Tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Erzeugung", "Verbrauch", "Speicher", "Wärmepumpen", "E-Mobilität"])

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

                gen_data = st.session_state.sm.get_generation_capacities(year=selected_year)
                cap_df = {
                    "Technologie": list(gen_data.keys()),
                    "Kapazität [MW]": [v for v in gen_data.values() if isinstance(v, (int, float))]
                }
                if cap_df["Kapazität [MW]"]:
                    st.dataframe(cap_df)

            with tab2:
                st.subheader("Verbrauch nach Sektor")
                for sector, data in load_demand.items():
                    if isinstance(data, dict) and selected_year in data:
                        st.metric(f"{sector}", f"{data[selected_year]} TWh")

            with tab3:
                st.subheader("Speicher-Kapazitäten")
                if storage_data:
                    speicher = st.segmented_control(
                        "Speichertyp auswählen",
                        ["Batteriespeicher", "Pumpspeicher", "Wasserstoffspeicher"],
                        default="Batteriespeicher"
                    )
                    if speicher == "Batteriespeicher":
                        battery = storage_data.get("battery_storage", {}).get(selected_year, {})
                        if battery:
                            col_bat = st.columns(2)
                            with col_bat[0]:
                                st.metric("Kapazität", f"{battery.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{battery.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_bat[1]:
                                st.metric("Max. Entladeleistung", f"{battery.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{battery.get('initial_soc', 0):.1%}")
                    if speicher == "Pumpspeicher":
                        pumped = storage_data.get("pumped_hydro_storage", {}).get(selected_year, {})
                        if pumped:
                            col_pump = st.columns(2)
                            with col_pump[0]:
                                st.metric("Kapazität", f"{pumped.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{pumped.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_pump[1]:
                                st.metric("Max. Entladeleistung", f"{pumped.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{pumped.get('initial_soc', 0):.1%}")
                    if speicher == "Wasserstoffspeicher":
                        h2 = storage_data.get("h2_storage", {}).get(selected_year, {})
                        if h2:
                            col_h2 = st.columns(2)
                            with col_h2[0]:
                                st.metric("Kapazität", f"{h2.get('installed_capacity_mwh', 0):,.0f} MWh")
                                st.metric("Max. Ladeleistung", f"{h2.get('max_charge_power_mw', 0):,.0f} MW")
                            with col_h2[1]:
                                st.metric("Max. Entladeleistung", f"{h2.get('max_discharge_power_mw', 0):,.0f} MW")
                                st.metric("Initialer SOC", f"{h2.get('initial_soc', 0):.1%}")
                else:
                    st.info("Keine Speicherdaten im Szenario definiert.")

            with tab4:
                st.subheader("Wärmepumpen - Parameter")
                hp_params = st.session_state.sm.get_heat_pump_parameters(selected_year) if hasattr(st.session_state.sm, "get_heat_pump_parameters") else {}
                if hp_params:
                    col_hp = st.columns(2)
                    with col_hp[0]:
                        st.metric("Installierte Einheiten", f"{hp_params.get('installed_units', 0):,}")
                        st.metric("Jahreswärmebedarf/Einheit", f"{hp_params.get('annual_heat_demand_kwh', 0):,.0f} kWh")
                    with col_hp[1]:
                        st.metric("COP (Durchschnitt)", f"{hp_params.get('cop_avg', 0):.2f}")
                        st.metric("Zeitintervall dt", "0.25 h")
                    st.caption("Datenquellen")
                    st.write({
                        "Wetterdaten": hp_params.get("weather_data", "—"),
                        "Lastprofil-Matrix": hp_params.get("load_profile", "—"),
                    })
                else:
                    st.info("Keine Wärmepumpen-Parameter für das ausgewählte Jahr definiert.")

            with tab5:
                st.subheader("E-Mobilität - Parameter")
                em_params = st.session_state.sm.get_emobility_parameters(selected_year) if hasattr(st.session_state.sm, "get_emobility_parameters") else {}
                if em_params:
                    col_em1, col_em2 = st.columns(2)
                    with col_em1:
                        st.metric("Anteil E-Fahrzeuge", f"{em_params.get('s_EV', 0):.0%}")
                        st.metric("Gesamtanzahl PKW", f"{em_params.get('N_cars', 0):,}")
                        st.metric("Jahresfahrverbrauch/Fzg", f"{em_params.get('E_drive_car_year', 0):,.0f} kWh")
                        st.metric("Batteriekapazität/Fzg", f"{em_params.get('E_batt_car', 0):.0f} kWh")
                    with col_em2:
                        st.metric("Max. Anschlussquote", f"{em_params.get('plug_share_max', 0):.0%}")
                        st.metric("V2G-Teilnahmequote", f"{em_params.get('v2g_share', 0.3):.0%}", 
                                  help="Anteil der angeschlossenen Fahrzeuge, die ins Netz zurückspeisen")
                        st.metric("SOC min Tag/Nacht", f"{em_params.get('SOC_min_day', 0):.0%} / {em_params.get('SOC_min_night', 0):.0%}")
                        st.metric("SOC-Ziel Abfahrt", f"{em_params.get('SOC_target_depart', 0):.0%}")
                        st.metric("Abfahrt/Ankunft", f"{em_params.get('t_depart', '07:30')} / {em_params.get('t_arrive', '18:00')}")
                    
                    with st.expander("Dispatch-Schwellwerte"):
                        col_thr1, col_thr2 = st.columns(2)
                        with col_thr1:
                            st.metric("Schwellwert Überschuss", f"{em_params.get('thr_surplus', 0)/1000:.0f} MW")
                        with col_thr2:
                            st.metric("Schwellwert Defizit", f"{em_params.get('thr_deficit', 0)/1000:.0f} MW")
                else:
                    st.info("Keine E-Mobilitäts-Parameter für das ausgewählte Jahr definiert.")


        # -----------------------------------------#
        #       Simulation Ausführen Bereich       #
        # -----------------------------------------#
        
        
        st.subheader("Simulation ausführen")        

        if "fullSimResults" not in st.session_state:
            st.session_state.fullSimResults = {}
        
        # Excel-Cache
        if "excel_exports" not in st.session_state:
            st.session_state.excel_exports = {}

        if st.button("Simulation starten", type="primary"):
            try:
                # loading bar
                progress_container = st.container()
                progress_bar = progress_container.progress(0, "Initializing...")
                log_area = progress_container.empty()
                
                def on_simulation_progress(progress: int, message: str):
                    """Callback für Simulations-Progress."""
                    progress_bar.progress(min(progress, 100), message)
                    log_area.info(f"📊 {message}")
                
                engine = SimulationEngine(
                    st.session_state.cfg,
                    st.session_state.dm,
                    st.session_state.sm,
                    verbose=st.session_state.get("debug_mode", False),  # globaler Debug-Modus
                    calculation_mode="cpu_optimized",
                    progress_callback=on_simulation_progress
                )
                
                on_simulation_progress(2, "Starting simulation...")
                st.session_state.fullSimResults = engine.run_scenario()
                
                # cleanup nach vorheriger Simulation
                st.session_state.excel_exports = {}
                progress_container.empty()
                
            except Exception as e:
                st.error(f"❌ Fehler in der Simulation: {e}")
                import traceback
                st.code(traceback.format_exc())


        # -----------------------------------------#
        #           Simulations Ergebnisse         #        
        # -----------------------------------------#

        results = st.session_state.fullSimResults
        if results:
            years_available = sorted(list(results.keys()))
            sel_year_str = st.segmented_control(
                "Bitte Jahr auswählen",
                [str(y) for y in years_available],
                default=str(years_available[0]),
                selection_mode="single",
                key="fullsim_year_choice"
            )
            try:
                sel_year = int(sel_year_str)
            except Exception:
                sel_year = years_available[0]

            # Tabs mit Ergebnissen
            tab_con, tab_prod, tab_emob, tab_bal_pre, tab_stor, tab_bal_post, tab_econ = st.tabs([
                "Verbrauch",      # results[year]["consumption"]
                "Erzeugung",                # results[year]["production"]
                "E-Mobilität",              # results[year]["emobility"]
                "Bilanz (vor Speicher)",        # results[year]["balance_pre_flex"]
                "Speicher",                 # results[year]["balance_post_flex"]
                "Bilanz (nach Speicher)",       # results[year]["balance_post_flex"]
                "Wirtschaftlichkeit"        # results[year]["economics"]
            ])

            with tab_con:
                st.caption("Gesamt-Verbrauch nach Sektor")
                df = results[sel_year]["consumption"]
                st.dataframe(df, width='stretch')
                
                col1, col2, col3, col4 = st.columns(4)
                bdew_sum = 0
                if 'Haushalte [MWh]' in df.columns:
                    bdew_sum += df['Haushalte [MWh]'].sum()
                if 'Gewerbe [MWh]' in df.columns:
                    bdew_sum += df['Gewerbe [MWh]'].sum()
                if 'Landwirtschaft [MWh]' in df.columns:
                    bdew_sum += df['Landwirtschaft [MWh]'].sum()                
                wp_sum = df.get('Wärmepumpen [MWh]', pd.Series([0])).sum()
                emob_sum = df.get('E-Mobility [MWh]', pd.Series([0])).sum()
                total = df['Gesamt [MWh]'].sum() if 'Gesamt [MWh]' in df.columns else 0
                
                col1.metric("BDEW-Profil Simu", f"{bdew_sum / 1e6:.2f} TWh")
                col2.metric("Wärmepumpen Simu", f"{wp_sum / 1e6:.2f} TWh")
                col3.metric("E-Mobility Simu", f"{emob_sum / 1e6:.2f} TWh")
                col4.metric("GESAMT", f"{total / 1e6:.2f} TWh")
                
                csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Verbrauch CSV",
                    data=csv,
                    file_name=f"verbrauch_{sel_year}.csv",
                    mime="text/csv"
                )

            with tab_prod:
                df = results[sel_year]["production"]
                st.dataframe(df, width='stretch')
                csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Erzeugung CSV",
                    data=csv,
                    file_name=f"erzeugung_{sel_year}.csv",
                    mime="text/csv"
                )

            with tab_emob:
                st.caption("E-Mobilitäts-Flotte")
                df_em = results[sel_year].get("emobility")
                
                if df_em is not None and not df_em.empty:
                    st.dataframe(df_em, width='stretch')
                    
                    # Kennzahlen in 4 Spalten
                    col1, col2, col3, col4 = st.columns(4)
                    
                    total_drive = df_em['Fahrverbrauch [MWh]'].sum() if 'Fahrverbrauch [MWh]' in df_em.columns else 0
                    total_loss = df_em['Ladeverluste [MWh]'].sum() if 'Ladeverluste [MWh]' in df_em.columns else 0
                    total_em = df_em['Gesamt Verbrauch [MWh]'].sum() if 'Gesamt Verbrauch [MWh]' in df_em.columns else 0
                    n_ev = df_em['Anzahl Fahrzeuge'].iloc[0] if 'Anzahl Fahrzeuge' in df_em.columns and len(df_em) > 0 else 0
                    
                    col1.metric("Anzahl E-Fahrzeuge", f"{n_ev / 1e6:.2f} Mio")
                    col2.metric("Fahrverbrauch", f"{total_drive / 1e6:.2f} TWh")
                    col3.metric("Ladeverluste", f"{total_loss / 1e6:.2f} TWh")
                    col4.metric("GESAMT", f"{total_em / 1e6:.2f} TWh")
                    
                    csv = df_em.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                    st.download_button(
                        "Download E-Mobilität CSV",
                        data=csv,
                        file_name=f"emobility_{sel_year}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("⚠️ Keine E-Mobilitäts-Daten verfügbar. Stellen Sie sicher, dass E-Mobility-Parameter im Szenario definiert sind.")

            with tab_bal_pre:
                st.caption("Residuallast vor Speichern")
                df = results[sel_year]["balance_pre_flex"]
                
                display_cols = ['Zeitpunkt', 'Produktion [MWh]', 'Verbrauch [MWh]', 'Bilanz [MWh]']
                display_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[display_cols], width='stretch')
                
                surplus_hours = (df['Bilanz [MWh]'] > 0).sum() * 0.25 if 'Bilanz [MWh]' in df.columns else 0
                deficit_hours = (df['Bilanz [MWh]'] < 0).sum() * 0.25 if 'Bilanz [MWh]' in df.columns else 0
                autarkie = (surplus_hours / (surplus_hours + deficit_hours) * 100) if (surplus_hours + deficit_hours) > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Überschuss-Stunden", f"{surplus_hours:.0f} h")
                col2.metric("Defizit-Stunden", f"{deficit_hours:.0f} h")
                col3.metric("Autarkie (ohne Flex)", f"{autarkie:.1f}%")
                
                csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Bilanz (vor Flex) CSV",
                    data=csv,
                    file_name=f"bilanz_pre_flex_{sel_year}.csv",
                    mime="text/csv"
                )

            with tab_stor:
                st.caption("Speicher Ergebnisse")
                df = results[sel_year].get("storage")
                
                if df is not None and not df.empty:
                    st.dataframe(df, width='stretch')
                    
                    # Speicher daten
                    st.markdown("**Speicher-Statistiken:**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    if 'Batteriespeicher SOC MWh' in df.columns:
                        col1.metric("Batterie Max SOC", f"{df['Batteriespeicher SOC MWh'].max():,.0f} MWh")
                    
                    if 'Pumpspeicher SOC MWh' in df.columns:
                        col2.metric("Pumpe Max SOC", f"{df['Pumpspeicher SOC MWh'].max():,.0f} MWh")
                    
                    if 'Wasserstoffspeicher SOC MWh' in df.columns:
                        col3.metric("H2 Max SOC", f"{df['Wasserstoffspeicher SOC MWh'].max():,.0f} MWh")
                    
                    total_charged = 0
                    if 'Batteriespeicher Geladene MWh' in df.columns:
                        total_charged += df['Batteriespeicher Geladene MWh'].sum()
                    if 'Pumpspeicher Geladene MWh' in df.columns:
                        total_charged += df['Pumpspeicher Geladene MWh'].sum()
                    if 'Wasserstoffspeicher Geladene MWh' in df.columns:
                        total_charged += df['Wasserstoffspeicher Geladene MWh'].sum()
                    col4.metric("Gesamt geladen", f"{total_charged / 1e6:.2f} TWh")
                    
                    csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                    st.download_button(
                        "Download Speicher CSV",
                        data=csv,
                        file_name=f"speicher_{sel_year}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("⚠️ Keine Speicher-Daten verfügbar. Stellen Sie sicher, dass Speicher im Szenario definiert sind.")

            with tab_bal_post:
                st.caption("Residuallast nach Speichern")
                df = results[sel_year]["balance_post_flex"]
                df_pre = results[sel_year]["balance_pre_flex"]
                
                df_compact = pd.DataFrame()
                if 'Zeitpunkt' in df.columns:
                    df_compact['Zeitpunkt'] = df['Zeitpunkt']                
                if 'Bilanz [MWh]' in df_pre.columns:
                    df_compact['Bilanz (vor Flex) [MWh]'] = df_pre['Bilanz [MWh]'].values                
                if 'Rest Bilanz [MWh]' in df.columns:
                    df_compact['Rest Bilanz (nach Flex) [MWh]'] = df['Rest Bilanz [MWh]']                    
                    if 'Bilanz [MWh]' in df_pre.columns:
                        df_compact['Flexibilität genutzt [MWh]'] = df_pre['Bilanz [MWh]'].values - df['Rest Bilanz [MWh]'].values
                
                st.dataframe(df_compact, width='stretch')
                
                if 'Flexibilität genutzt [MWh]' in df_compact.columns:
                    flex_total = df_compact['Flexibilität genutzt [MWh]'].abs().sum()
                else:
                    flex_total = 0                    
                if 'Rest Bilanz [MWh]' in df.columns:
                    rest_deficit_hours = (df['Rest Bilanz [MWh]'] < 0).sum() * 0.25
                else:
                    rest_deficit_hours = 0                
                flex_coverage = (1 - rest_deficit_hours / 8760) * 100 if rest_deficit_hours < 8760 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Flexibilität genutzt", f"{flex_total / 1e6:.2f} TWh")
                col2.metric("Verbleibende Defizit-Stunden", f"{rest_deficit_hours:.0f} h")
                col3.metric("Flexibilitäts-Abdeckung", f"{flex_coverage:.1f}%")
                
                csv = df_compact.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Bilanz (nach Flex) CSV",
                    data=csv,
                    file_name=f"bilanz_post_flex_{sel_year}.csv",
                    mime="text/csv"
                )

            with tab_econ:
                st.subheader("Wirtschaftlichkeit - Rohe Werte")
                econ_data = results[sel_year].get("economics", {})
                if econ_data:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Jahr", f"{econ_data.get('year', 'N/A')}")
                    with col2:
                        st.metric("Investitionsbedarf", f"{econ_data.get('total_investment_bn', 0):.3f} Mrd. €")
                    with col3:
                        st.metric("Jährliche Kosten", f"{econ_data.get('total_annual_cost_bn', 0):.3f} Mrd. €/Jahr")
                    with col4:
                        st.metric("System LCOE", f"{econ_data.get('system_lco_e', 0):.3f} ct/kWh")

                    st.write("**Alle Werte (Raw Data):**")
                    st.json(econ_data)
                else:
                    st.info("Keine Wirtschaftlichkeitsdaten verfügbar.")
            
            # ----------------------------------------- #
            #            Zeitbereich Auswahl            #
            # ----------------------------------------- #

            st.markdown("---")
            st.subheader("Visualisierung")
            
            # Datumsauswahl für alle Diagramme
            st.markdown("#### Zeitraum-Auswahl für alle Diagramme")
            st.caption("Wählen Sie den anzuzeigenden Zeitraum - gilt für alle folgenden Plots")
            
            df_time_ref = results[sel_year]["consumption"]
            if "Zeitpunkt" not in df_time_ref.columns:
                st.error("Zeitpunkt-Spalte fehlt im DataFrame")
            else:
                df_time = pd.to_datetime(df_time_ref["Zeitpunkt"])
                min_date = df_time.min()
                max_date = df_time.max()
                year = min_date.year
                default_start = pd.Timestamp(year=year, month=5, day=1)
                default_end = pd.Timestamp(year=year, month=5, day=7)
                
                if default_start < min_date or default_start > max_date:
                    default_start = min_date
                    default_end = min_date + pd.Timedelta(days=7)
                    if default_end > max_date:
                        default_end = max_date
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    date_from_global = st.date_input(
                        "Von",
                        value=default_start.date(),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                        format="DD.MM.YYYY",
                        key=f"global_date_from_{sel_year}"
                    )
                with col2:
                    date_to_global = st.date_input(
                        "Bis",
                        value=default_end.date(),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                        format="DD.MM.YYYY",
                        key=f"global_date_to_{sel_year}"
                    )
                with col3:
                    show_full_year = st.button("📅 Ganzes Jahr anzeigen", key=f"full_year_global_{sel_year}")
                
                if show_full_year:
                    date_from_ts = min_date
                    date_to_ts = max_date
                else:
                    date_from_ts = pd.Timestamp(date_from_global)
                    date_to_ts = pd.Timestamp(date_to_global, hour=23, minute=59, second=59)

            # ----------------------------------------- #
            #       Verbrauchs und Erzeugungs Plots     #
            # ----------------------------------------- #
            
            with st.expander("📊 Verbrauchs und Erzeugungs Plots", expanded=False):

                st.markdown("### Verbrauchssimulation")
                st.caption("Stundliche Verbrauchswerte nach Sektor (Haushalte, Gewerbe, Landwirtschaft, E-Mobility)")
                fig_con = ply.create_consumption_plot(
                    results[sel_year]["consumption"],
                    sector_columns=[c for c in results[sel_year]["consumption"].columns if "[MWh]" in c and "Gesamt" not in c and "Zeitpunkt" not in c],
                    title="",
                    date_from=date_from_ts,
                    date_to=date_to_ts
                )
                st.plotly_chart(fig_con, key=f"consumption_{sel_year}")

                st.markdown("### Erzeugungssimulation")
                st.caption("Stundliche Erzeugungswerte nach Technologie (Wind, Solar, Biomasse, etc.)")
                
                # check nach verfügbarer Zeitreihe in DF
                df_prod = results[sel_year]["production"]
                prod_cols = [c for c in df_prod.columns if "[MWh]" in c and "Gesamt" not in c and "Zeitpunkt" not in c]
                
                if prod_cols and df_prod[prod_cols].sum().sum() > 0:
                    fig_gen = ply.create_generation_plot(
                        df_prod,
                        title="",
                        date_from=date_from_ts,
                        date_to=date_to_ts
                    )
                    st.plotly_chart(fig_gen, key=f"generation_{sel_year}")
                else:
                    st.warning("⚠️ Keine Erzeugungsdaten vorhanden. Bitte prüfen Sie, ob Ziel-Kapazitäten im Szenario definiert sind.")

            # ----------------------------------------- #
            #          E-Mobilität Dashboard            #
            # ----------------------------------------- #

            with st.expander("🚗 E-Mobilität Dashboard", expanded=False):
                st.markdown("### E-Mobilität Dashboard")
                
                df_emob_sim = results[sel_year].get("emobility")
                
                # check ob Spalten in DataFrame vorhanden sind
                if df_emob_sim is not None and not df_emob_sim.empty:
                    has_soc = 'EMobility SOC [MWh]' in df_emob_sim.columns
                    has_power = 'EMobility Power [MW]' in df_emob_sim.columns
                    has_charge = 'EMobility Charge [MWh]' in df_emob_sim.columns
                    has_discharge = 'EMobility Discharge [MWh]' in df_emob_sim.columns
                    has_drive = 'EMobility Drive [MWh]' in df_emob_sim.columns
                    has_time = 'Zeitpunkt' in df_emob_sim.columns
                    
                    if has_soc and has_time:
                        st.markdown("#### State of Charge (SOC) der EV-Flotte")
                        st.caption("Aggregierter Ladestand aller Elektrofahrzeuge über die Zeit")
                        
                        # Zeitraum filtern
                        df_filtered = df_emob_sim.copy()
                        if 'date_from_ts' in locals() and 'date_to_ts' in locals():
                            df_filtered['Zeitpunkt'] = pd.to_datetime(df_filtered['Zeitpunkt'])
                            df_filtered = df_filtered[
                                (df_filtered['Zeitpunkt'] >= date_from_ts) & 
                                (df_filtered['Zeitpunkt'] <= date_to_ts)
                            ]
                        
                        fig_ev_soc = ply.create_emobility_soc_plot(
                            df_filtered,
                            date_from=date_from_ts,
                            date_to=date_to_ts
                        )
                        st.plotly_chart(fig_ev_soc, width='stretch', key=f"ev_soc_{sel_year}")
                    
                    if has_power and has_time:
                        st.markdown("#### Lade-/Entladeleistung der EV-Flotte")
                        st.caption("Negative Werte = Laden aus Netz, Positive Werte = Rückspeisung ins Netz (V2G)")
                        
                        fig_ev_power = ply.create_emobility_power_plot(
                            df_filtered,
                            date_from=date_from_ts,
                            date_to=date_to_ts
                        )
                        st.plotly_chart(fig_ev_power, width='stretch', key=f"ev_power_{sel_year}")
                    
                    # Metriken zusätzlich
                    if has_charge or has_discharge or has_drive:
                        st.markdown("#### E-Mobility Energiebilanz")
                        col1, col2, col3 = st.columns(3)
                        if has_charge:
                            total_charge = df_emob_sim['EMobility Charge [MWh]'].sum()
                            col1.metric("Gesamt Geladen", f"{total_charge:,.0f} MWh")
                        if has_discharge:
                            total_discharge = df_emob_sim['EMobility Discharge [MWh]'].sum()
                            col2.metric("Gesamt Entladen (V2G)", f"{total_discharge:,.0f} MWh")
                        if has_drive:
                            total_drive = df_emob_sim['EMobility Drive [MWh]'].sum()
                            col3.metric("Fahrverbrauch", f"{total_drive:,.0f} MWh")
                    
                    if not has_time:
                        st.warning("⚠️ Zeitpunkt-Spalte fehlt im emobility DataFrame.")
                    elif not (has_soc or has_power):
                        st.warning("⚠️ E-Mobility Simulationsergebnisse nicht im emobility DataFrame gefunden.")
                else:
                    st.info("ℹ️ Keine E-Mobility-Daten in diesem Szenario vorhanden.")

            # ----------------------------------------- #
            #            Speicher und Bilanz            #
            # ----------------------------------------- #
            
            with st.expander("🔋 Speicher und Bilanz Plots", expanded=False):

                st.markdown("### Erzeugung vs. Verbrauch")
                st.caption("Direkter Vergleich: Erzeugung und Verbrauch im gleichen Zeitfenster")
                combo_df = results[sel_year]["production"].copy()
                combo_df["Skalierte Netzlast [MWh]"] = results[sel_year]["consumption"]["Gesamt [MWh]"]
                
                # Prüfe IF Daten vorhanden
                combo_prod_cols = [c for c in combo_df.columns if "[MWh]" in c and "Gesamt" not in c and "Zeitpunkt" not in c and "Netzlast" not in c]
                if combo_prod_cols and combo_df[combo_prod_cols].sum().sum() > 0:
                    fig_combo = ply.create_generation_with_load_plot(
                        df=combo_df,
                        title=" ",
                        date_from=date_from_ts,
                        date_to=date_to_ts
                    )
                    st.plotly_chart(fig_combo, key=f"combo_{sel_year}")
                else:
                    st.info("Erzeugung vs. Verbrauch nicht verfügbar - keine Erzeugungsdaten.")

                df_storage = results[sel_year].get("storage")
                df_balance_post = results[sel_year]["balance_post_flex"]
                df_balance_pre = results[sel_year]["balance_pre_flex"]
                df_balance_after_emob = results[sel_year].get("balance_after_emob", df_balance_pre)  # Fallback auf pre_flex
                
                if df_storage is not None and not df_storage.empty:
                    st.markdown("### Speichersimulation")
                    st.markdown("#### Geordnete Jahresdauerlinie (Residuallast)")
                    st.caption("Wirkung der Flexibilitäten: Bilanz ohne Flexibilitäten (Erzeugung - Verbrauch) vs. Bilanz nach E-Mobility V2G und Speichern")
                    
                    duration_plot_df = pd.DataFrame({
                        'Zeitpunkt': df_balance_pre['Zeitpunkt'],
                        'Bilanz [MWh]': df_balance_pre['Bilanz [MWh]'],
                        'Rest Bilanz [MWh]': df_balance_post['Rest Bilanz [MWh]']
                    })
                    
                    fig_duration = ply.create_duration_curve_plot(
                        duration_plot_df,
                        balance_column="Bilanz [MWh]",
                        rest_balance_column="Rest Bilanz [MWh]",
                        title=" "
                    )
                    st.plotly_chart(fig_duration, key=f"duration_{sel_year}")

                    st.markdown("#### State of Charge (SOC) der Speicher")
                    st.caption("Ladestand aller Speicher über die Zeit - Batterien, Pumpspeicher und H₂-Speicher")
                    
                    soc_plot_df = df_storage.copy()                    
                    fig_soc = ply.create_soc_stacked_plot(
                        soc_plot_df,
                        title=" ",
                        date_from=date_from_ts,
                        date_to=date_to_ts
                    )
                    st.plotly_chart(fig_soc, key=f"soc_{sel_year}")

                    st.markdown("---")
                    st.markdown("### Bilanz vor Speichern")
                    st.caption("Bilanz nach E-Mobility V2G und vor Speicher")
                    fig_bal_pre_storage = ply.create_balance_area_plot(
                        df_balance_after_emob,
                        title=" ",
                        date_from=date_from_ts,
                        date_to=date_to_ts
                    )
                    st.plotly_chart(fig_bal_pre_storage, key=f"balance_pre_storage_{sel_year}")

                    st.markdown("### Bilanz nach Speichern")
                    st.caption("Finale Bilanz nach Speicher")
                    fig_bal_post = ply.create_balance_area_plot(
                        df_balance_post,
                        "Rest Bilanz [MWh]",
                        title=" ",
                        date_from=date_from_ts,
                        date_to=date_to_ts
                    )
                    st.plotly_chart(fig_bal_post, key=f"balance_post_storage_{sel_year}")

            # ----------------------------------------- #
            #        Wirtschaftlichkeits-Dashboard      #
            # ----------------------------------------- #

            with st.expander("💰 Wirtschaftlichkeits-Dashboard", expanded=False):
                econ_series = [
                    results[y].get("economics")
                    for y in years_available
                    if results.get(y, {}).get("economics")
                ]
                if econ_series:
                    st.markdown("### Wirtschaftlichkeits-Dashboard")

                    # Wirtschaftlichkeits Trend
                    st.markdown("#### Investitions- und LCOE-Trend (Balken = Investition, Linie = LCOE)")
                    st.caption("LCOE: Levelized Cost of Electricity (Systemkosten pro erzeugter kWh)")
                    fig_econ = econ_ply.plot_economic_trends(econ_series)
                    st.plotly_chart(fig_econ, width='stretch', key=f"econ_trends_{sel_year}")

                    
                    col_cost, col_inv = st.columns(2)
                    
                    # Kostenaufteilung für simulierte Jahre
                    with col_cost:
                        st.markdown("#### Kostenaufschlüsselung (Mrd. €/Jahr)")
                        fig_cost = econ_ply.plot_cost_structure(econ_series)
                        st.plotly_chart(fig_cost, width='stretch', key=f"cost_structure_{sel_year}")
                    
                    # Investitionsmix für selcted year nach Technologie
                    with col_inv:
                        st.markdown(f"#### Investitionsmix {sel_year} (Mrd. €)")
                        econ_data = results[sel_year].get("economics", {})
                        if "investment_by_tech" in econ_data and econ_data["investment_by_tech"]:
                            fig_donut = econ_ply.plot_investment_donut(
                                econ_data["investment_by_tech"],
                                sel_year
                            )
                            st.plotly_chart(fig_donut, width='stretch', key=f"invest_donut_{sel_year}")
                        else:
                            st.info("Investitionsverteilung nach Technologie nicht verfügbar.")

            # ----------------------------------------- #
            #       Restbilanz "Was übrig bleibt"       #
            # ----------------------------------------- #

            with st.expander("📈 Zu Importierende Restbilanz", expanded=True):
                st.markdown("### Monatlich aufaddierte Restbilanz")
                st.caption("Zeigt die monatlich aufsummierte Restbilanz nach allen Flexibilitäten")
                
                df_balance_post = results[sel_year]["balance_post_flex"]                
                fig_monthly_balance = ply.create_monthly_balance_plot(
                    df_balance_post,
                    title=" ",
                )
                st.plotly_chart(fig_monthly_balance, key=f"monthly_balance_{sel_year}", width='stretch')
                
                # zusätzliche Kennzahlen
                total_surplus = df_balance_post[df_balance_post['Rest Bilanz [MWh]'] > 0]['Rest Bilanz [MWh]'].sum()
                total_deficit = df_balance_post[df_balance_post['Rest Bilanz [MWh]'] < 0]['Rest Bilanz [MWh]'].sum()
                yearly_sum = df_balance_post['Rest Bilanz [MWh]'].sum()
                
                col1, col2, col3 = st.columns(3, border=True)
                with col1:
                    col1.metric(":green[Gesamt Überschuss]", f"{total_surplus / 1e6:.2f} TWh")
                    st.write(":green[Summe aller Monate mit Energieüberschuss]: " \
                    "Diese sind für den Export oder weitere Speicherung verfügbar.")
                with col2:
                    col2.metric(":red[Gesamt Defizit]", f"{abs(total_deficit) / 1e6:.2f} TWh")
                    st.write(":red[Summe aller Monate mit Energiedefizit]: " \
                    "Diese müssen durch Wasserstoff/Gas Importe und/oder Strom Importe gedeckt werden.")
                with col3:
                    col3.metric("Jährliche Gesamtbilanz", f"{yearly_sum / 1e6:.2f} TWh")
                    st.write("Netto-Bilanz für das gesamte Jahr (Überschuss - Defizit)")

            # ----------------------------------------- #
            #          KPI-Scoring Dashboard            #
            # ----------------------------------------- #

            with st.expander("⚡ KPI-Scoring Dashboard", expanded=True):
                # Prüfe ob Storage vorhanden -> sonst ist keine KPI calc
                if "storage_config" not in st.session_state or not st.session_state.storage_config:
                    st.warning("⚠️ Storage-Konfiguration nicht verfügbar. Bitte laden Sie ein Szenario mit Speichern.")
                else:
                    render_kpi_dashboard(results, st.session_state.storage_config, sel_year)




            # ----------------------------------------- #
            #            Ergebnis-Downloads             #
            # ----------------------------------------- #           


            with st.expander("📥 Ergebnis-Downloads", expanded=False):
                st.subheader("Downloads")
                st.write("Die Erzeugung von Excel Datein dauert sehr lange. Die ZIP dauert entsprechend länger. \n :violet[TIPP: Benutze den instant CSV export oben!]")
                
                scenario_name = st.session_state.sm.scenario_data.get("metadata", {}).get("name", "Szenario")
                
                st.markdown("#### Excel-Export (einzelnes Jahr)")
                col_year_select, col_excel1, col_excel2 = st.columns([1, 1, 2])
    
                #jahr auswählen                
                with col_year_select:
                    excel_year = st.selectbox(
                        "Jahr wählen",
                        options=years_available,
                        index=years_available.index(sel_year) if sel_year in years_available else 0,
                        key="excel_year_selector"
                    )                
                excel_key = f"excel_{excel_year}"
                
                with col_excel1:
                    if st.button("Excel generieren", key=f"btn_gen_excel_{excel_year}", width='stretch'):
                        with st.spinner(f"Generiere Excel für {excel_year}..."):
                            try:
                                st.session_state.excel_exports[excel_key] = SimulationEngine.export_results_to_excel(results, excel_year)
                                st.success("✅ Excel generiert!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Fehler beim Excel-Export: {e}")
                
                with col_excel2:
                    if excel_key in st.session_state.excel_exports:
                        st.download_button(
                            "Download Jahresergebnisse (EXCEL)", 
                            data=st.session_state.excel_exports[excel_key],
                            file_name=f"Ergebnisse_{scenario_name}_{excel_year}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_excel_{excel_year}",
                            width='stretch'
                        )
                    else:
                        st.info("Bitte zuerst Excel generieren")

                # ZIP mit allen Jahren
                if len(years_available) > 1:
                    st.markdown("---")
                    st.markdown("#### ZIP-Export (alle Jahre)")
                    st.caption(f"Enthält Excel-Dateien für alle {len(years_available)} simulierten Jahre")
                    
                    zip_key = "excel_zip"
                    col_zip1, col_zip2 = st.columns([1, 3])
                    
                    with col_zip1:
                        if st.button("📦 ZIP generieren", key="btn_gen_zip", width='stretch'):
                            with st.spinner(f"Generiere ZIP mit allen {len(years_available)} Jahren... (optimiert mit Komprimierung)"):
                                try:
                                    st.session_state.excel_exports[zip_key] = SimulationEngine.export_results_to_zip(results)
                                    st.success("✅ ZIP generiert!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Fehler beim ZIP-Export: {e}")
                    
                    with col_zip2:
                        if zip_key in st.session_state.excel_exports:
                            st.download_button(
                                "Download alle Jahre", 
                                data=st.session_state.excel_exports[zip_key],
                                file_name=f"Ergebnisse_{scenario_name}_alle_jahre.zip",
                                mime="application/zip",
                                key="download_zip_all",
                                width='stretch'
                            )
                        else:
                            st.info("Bitte zuerst ZIP generieren")
