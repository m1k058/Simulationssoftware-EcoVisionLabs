# Standard Bibliotheken
import streamlit as st 
import pandas as pd
from datetime import datetime

# Eigene Imports
from data_processing.simulation_engine import SimulationEngine
import plotting.plotting_plotly_st as ply
import plotting.economic_plots as econ_ply

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
    """Single Mode: Ein Szenario laden und simulieren."""
    st.set_page_config(layout="wide")
    st.title("Simulation (Single Mode)")
    st.caption("Laden Sie ein Szenario und führen Sie eine vollständige Simulation durch.")

    # Überprüfe ob DataManager, ConfigManager, ScenarioManager geladen sind
    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")
        return
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
            load_demand = st.session_state.sm.get_load_demand(year=selected_year)
            storage_data = st.session_state.sm.scenario_data.get("target_storage_capacities", {})
            
            st.write(f"**Simulationsjahr: {selected_year}**")

            # Detail-Ansichten (Erzeugung / Verbrauch / Speicher / Wärmepumpen / E-Mobilität)
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
                    # Neue Parameter-Struktur
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
                    
                    # Erweiterte Parameter in Expander
                    with st.expander("Dispatch-Schwellwerte"):
                        col_thr1, col_thr2 = st.columns(2)
                        with col_thr1:
                            st.metric("Schwellwert Überschuss", f"{em_params.get('thr_surplus', 0)/1000:.0f} MW")
                        with col_thr2:
                            st.metric("Schwellwert Defizit", f"{em_params.get('thr_deficit', 0)/1000:.0f} MW")
                else:
                    st.info("Keine E-Mobilitäts-Parameter für das ausgewählte Jahr definiert.")


        # ==============================================================
        # Ein-Knopf-Simulation: führt alle Schritte aus und zeigt DFs an
        # ==============================================================
        st.subheader("Simulation ausführen")

        # Modus-Auswahl für Wärmepumpen-Berechnung
        st.markdown("#### Berechnungsmodus")
        calculation_mode_display = st.radio(
            "Wählen Sie den Berechnungsmodus für Wärmepumpen:",
            ["Normal", "CPU-Beschleunigt (Numba)"],
            index=1,  # CPU-Beschleunigt als Standard
            horizontal=True
        )
        
        # Mapping von UI-Namen zu internen Modus-Namen
        mode_mapping = {
            "Normal": "normal",
            "CPU-Beschleunigt (Numba)": "cpu_optimized"
        }
        calculation_mode = mode_mapping[calculation_mode_display]
        

        if "fullSimResults" not in st.session_state:
            st.session_state.fullSimResults = {}
        
        # Initialisiere Excel-Cache
        if "excel_exports" not in st.session_state:
            st.session_state.excel_exports = {}

        if st.button("Simulation starten", type="primary"):
            try:
                engine = SimulationEngine(
                    st.session_state.cfg,
                    st.session_state.dm,
                    st.session_state.sm,
                    verbose=True,  # Debug-Modus aktiviert
                    calculation_mode=calculation_mode
                )
                st.session_state.fullSimResults = engine.run_scenario()
                
                # Lösche alte Excel-Exporte (neue Simulation = neue Daten)
                st.session_state.excel_exports = {}
                
                st.success("✅ Simulation abgeschlossen!")
            except Exception as e:
                st.error(f"❌ Fehler in der Simulation: {e}")

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

            # Tabs pro Ergebnis-DF - 7 TABS MIT E-MOBILITY
            tab_con, tab_prod, tab_emob, tab_bal_pre, tab_stor, tab_bal_post, tab_econ = st.tabs([
                "Verbrauch (+ E-Mob)",      # results[year]["consumption"]
                "Erzeugung",                # results[year]["production"]
                "E-Mobilität",              # results[year]["emobility"]  <- NEU!
                "Bilanz (vor Flex)",        # results[year]["balance_pre_flex"]
                "Speicher",                 # results[year]["balance_post_flex"] (nur Speicher-Spalten)
                "Bilanz (nach Flex)",       # results[year]["balance_post_flex"] (kompakt)
                "Wirtschaftlichkeit"        # results[year]["economics"]
            ])

            with tab_con:
                st.caption("Gesamt-Verbrauch: BDEW + Wärmepumpen + E-Mobilität")
                df = results[sel_year]["consumption"]
                st.dataframe(df, width='stretch')
                
                # Kennzahlen in 4 Spalten
                col1, col2, col3, col4 = st.columns(4)
                
                # BDEW-Summe
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
                
                col1.metric("BDEW", f"{bdew_sum / 1e6:.2f} TWh")
                col2.metric("Wärmepumpen", f"{wp_sum / 1e6:.2f} TWh")
                col3.metric("E-Mobility", f"{emob_sum / 1e6:.2f} TWh")
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
                st.caption("E-Mobilitäts-Flotte: Fahrverbrauch, Ladeverluste und Gesamtverbrauch")
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
                st.caption("Residuallast VOR Flexibilitäten (ohne Speicher/V2G)")
                df = results[sel_year]["balance_pre_flex"]
                
                # Kompakte Ansicht: nur relevante Spalten
                display_cols = ['Zeitpunkt', 'Produktion [MWh]', 'Verbrauch [MWh]', 'Bilanz [MWh]']
                display_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[display_cols], width='stretch')
                
                # Analyse
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
                st.caption("Speicher-Operationen (Batterie, Pumpspeicher, H2)")
                df = results[sel_year].get("storage")
                
                if df is not None and not df.empty:
                    st.dataframe(df, width='stretch')
                    
                    # Speicher-Kennzahlen
                    st.markdown("**Speicher-Statistiken:**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    # Batteriespeicher
                    if 'Batteriespeicher SOC MWh' in df.columns:
                        col1.metric("Batterie Max SOC", f"{df['Batteriespeicher SOC MWh'].max():,.0f} MWh")
                    
                    # Pumpspeicher
                    if 'Pumpspeicher SOC MWh' in df.columns:
                        col2.metric("Pumpe Max SOC", f"{df['Pumpspeicher SOC MWh'].max():,.0f} MWh")
                    
                    # H2-Speicher (Spaltenname: "Wasserstoffspeicher" für Konsistenz mit storage_simulation.py)
                    if 'Wasserstoffspeicher SOC MWh' in df.columns:
                        col3.metric("H2 Max SOC", f"{df['Wasserstoffspeicher SOC MWh'].max():,.0f} MWh")
                    
                    # Gesamt geladen
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
                st.caption("Final-Residuallast NACH allen Flexibilitäten")
                df = results[sel_year]["balance_post_flex"]
                df_pre = results[sel_year]["balance_pre_flex"]
                
                # Kompakte Ansicht: Original-Bilanz vs. Rest-Bilanz
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
                
                # Flexibilitäts-Effekt
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
                    # Nur Rohdaten und Kennzahlen anzeigen
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

            # Visualisierungen ZUERST (bevor Downloads generiert werden)
            st.markdown("---")
            st.subheader("Visualisierung")
            
            # ZENTRALER DATUMS-SELEKTOR FÜR ALLE PLOTS
            st.markdown("#### Zeitraum-Auswahl für alle Diagramme")
            st.caption("Wählen Sie den anzuzeigenden Zeitraum - gilt für alle folgenden Plots")
            
            # Verwende consumption DataFrame für Zeitbereich
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

            st.markdown("### Verbrauchssimulation")
            st.caption("Stundliche Verbrauchswerte nach Sektor (Haushalte, Gewerbe, Landwirtschaft, E-Mobility)")
            fig_con = ply.create_consumption_plot(
                results[sel_year]["consumption"],
                title="",
                date_from=date_from_ts,
                date_to=date_to_ts
            )
            st.plotly_chart(fig_con, key=f"consumption_{sel_year}")

            st.markdown("### Erzeugungssimulation")
            st.caption("Stundliche Erzeugungswerte nach Technologie (Wind, Solar, Biomasse, etc.)")
            
            # Prüfe ob Erzeugungsdaten vorhanden sind
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

            # E-Mobilität Plots
            st.markdown("---")
            st.markdown("### E-Mobilität Dashboard")
            
            # E-Mobility Simulationsergebnisse aus separatem emobility DataFrame
            df_emob_sim = results[sel_year].get("emobility")
            
            # Prüfe ob E-Mobility Simulationsdaten vorhanden sind
            if df_emob_sim is not None and not df_emob_sim.empty:
                # Prüfe ob die erwarteten Spalten vorhanden sind
                has_soc = 'EMobility SOC [MWh]' in df_emob_sim.columns
                has_power = 'EMobility Power [MW]' in df_emob_sim.columns
                has_charge = 'EMobility Charge [MWh]' in df_emob_sim.columns
                has_discharge = 'EMobility Discharge [MWh]' in df_emob_sim.columns
                has_drive = 'EMobility Drive [MWh]' in df_emob_sim.columns
                has_time = 'Zeitpunkt' in df_emob_sim.columns
                
                if has_soc and has_time:
                    st.markdown("#### State of Charge (SOC) der EV-Flotte")
                    st.caption("Aggregierter Ladestand aller Elektrofahrzeuge über die Zeit")
                    
                    # Nutze globalen Zeitraum-Filter
                    import plotly.graph_objects as go
                    df_filtered = df_emob_sim.copy()
                    
                    # Filtere nach globalem Zeitbereich
                    if 'date_from_ts' in locals() and 'date_to_ts' in locals():
                        df_filtered['Zeitpunkt'] = pd.to_datetime(df_filtered['Zeitpunkt'])
                        df_filtered = df_filtered[
                            (df_filtered['Zeitpunkt'] >= date_from_ts) & 
                            (df_filtered['Zeitpunkt'] <= date_to_ts)
                        ]
                    
                    # SOC Plot
                    fig_ev_soc = go.Figure()
                    fig_ev_soc.add_trace(go.Scatter(
                        x=df_filtered['Zeitpunkt'],
                        y=df_filtered['EMobility SOC [MWh]'],
                        mode='lines',
                        name='EV-Flotte SOC',
                        fill='tozeroy',
                        line=dict(color='#2ecc71', width=1),
                        fillcolor='rgba(46, 204, 113, 0.3)'
                    ))
                    fig_ev_soc.update_layout(
                        xaxis_title="Zeit",
                        yaxis_title="SOC [MWh]",
                        template="plotly_white",
                        height=400,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_ev_soc, width='stretch', key=f"ev_soc_{sel_year}")
                
                if has_power and has_time:
                    st.markdown("#### Lade-/Entladeleistung der EV-Flotte")
                    st.caption("Negative Werte = Laden aus Netz, Positive Werte = Rückspeisung ins Netz (V2G)")
                    
                    # Power Plot
                    fig_ev_power = go.Figure()
                    power_data = df_filtered['EMobility Power [MW]']
                    
                    # Positive Werte (Entladen/V2G) in Grün
                    fig_ev_power.add_trace(go.Scatter(
                        x=df_filtered['Zeitpunkt'],
                        y=power_data.clip(lower=0),
                        mode='lines',
                        name='V2G Rückspeisung',
                        fill='tozeroy',
                        line=dict(color='#27ae60', width=0.5),
                        fillcolor='rgba(39, 174, 96, 0.5)'
                    ))
                    
                    # Negative Werte (Laden) in Rot
                    fig_ev_power.add_trace(go.Scatter(
                        x=df_filtered['Zeitpunkt'],
                        y=power_data.clip(upper=0),
                        mode='lines',
                        name='Laden',
                        fill='tozeroy',
                        line=dict(color='#e74c3c', width=0.5),
                        fillcolor='rgba(231, 76, 60, 0.5)'
                    ))
                    
                    fig_ev_power.update_layout(
                        xaxis_title="Zeit",
                        yaxis_title="Leistung [MW]",
                        template="plotly_white",
                        height=400,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig_ev_power, width='stretch', key=f"ev_power_{sel_year}")
                
                # Optional: Zeige zusätzliche Metriken wenn verfügbar
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
                
                # Wenn wichtige Spalten fehlen, zeige Warnung
                if not has_time:
                    st.warning("⚠️ Zeitpunkt-Spalte fehlt im emobility DataFrame.")
                elif not (has_soc or has_power):
                    st.warning("⚠️ E-Mobility Simulationsergebnisse (SOC/Power) nicht im emobility DataFrame gefunden. Möglicherweise ist E-Mobility V2G nicht konfiguriert.")
            else:
                st.info("ℹ️ Keine E-Mobility-Daten in diesem Szenario vorhanden.")

            st.markdown("### Erzeugung vs. Verbrauch")
            st.caption("Direkter Vergleich: Erzeugung und Verbrauch im gleichen Zeitfenster")
            combo_df = results[sel_year]["production"].copy()
            combo_df["Skalierte Netzlast [MWh]"] = results[sel_year]["consumption"]["Gesamt [MWh]"]
            
            # Prüfe ob Erzeugungsdaten vorhanden sind
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

            # Speicher-Plots (wenn Speicher vorhanden)
            df_storage = results[sel_year].get("storage")
            df_balance_post = results[sel_year]["balance_post_flex"]
            df_balance_pre = results[sel_year]["balance_pre_flex"]
            df_balance_after_emob = results[sel_year].get("balance_after_emob", df_balance_pre)  # Fallback auf pre_flex
            
            if df_storage is not None and not df_storage.empty:
                st.markdown("### Speichersimulation")
                st.markdown("#### Geordnete Jahresdauerlinie (Residuallast)")
                st.caption("Wirkung der Flexibilitäten: Bilanz ohne Flexibilitäten (Erzeugung - Verbrauch) vs. Bilanz nach E-Mobility V2G und Speichern")
                
                # Kombiniere ursprüngliche Bilanz mit finaler Bilanz für Vergleich
                duration_plot_df = pd.DataFrame({
                    'Zeitpunkt': df_balance_pre['Zeitpunkt'],
                    'Bilanz [MWh]': df_balance_pre['Bilanz [MWh]'],  # Ursprüngliche Bilanz (Erzeugung - Verbrauch)
                    'Rest Bilanz [MWh]': df_balance_post['Rest Bilanz [MWh]']  # Nach ALLEN Flexibilitäten
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
                
                # Kombiniere Storage-Daten mit Zeitpunkt für SOC Plot
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
                st.caption("Bilanz nach E-Mobility V2G, aber VOR Speicher-Flexibilitäten (positiv = Überschuss, negativ = Defizit)")
                fig_bal_pre_storage = ply.create_balance_area_plot(
                    df_balance_after_emob,
                    title=" ",
                    date_from=date_from_ts,
                    date_to=date_to_ts
                )
                st.plotly_chart(fig_bal_pre_storage, key=f"balance_pre_storage_{sel_year}")

                st.markdown("### Bilanz nach Speichern")
                st.caption("Finale Bilanz nach E-Mobility V2G UND Speicher (positiv = Überschuss, negativ = Defizit)")
                fig_bal_post = ply.create_balance_area_plot(
                    df_balance_post,
                    title=" ",
                    date_from=date_from_ts,
                    date_to=date_to_ts
                )
                st.plotly_chart(fig_bal_post, key=f"balance_post_storage_{sel_year}")

            # Wirtschaftlichkeit über alle Jahre (Trend)
            econ_series = [
                results[y].get("economics")
                for y in years_available
                if results.get(y, {}).get("economics")
            ]
            if econ_series:
                st.markdown("---")
                st.markdown("### Wirtschaftlichkeits-Dashboard")
                st.markdown("#### Investitions- und LCOE-Trend (Balken = Investition, Linie = LCOE)")

                # Hauptgraph: Trend
                fig_econ = ply.plot_economic_trends(econ_series)
                st.plotly_chart(fig_econ, width='stretch', key=f"econ_trends_{sel_year}")

                # Nebendiagramme: Kostenaufschlüsselung und Investitionsmix
                col_cost, col_inv = st.columns(2)
                
                with col_cost:
                    st.markdown("#### Kostenaufschlüsselung (Mrd. €/Jahr)")
                    fig_cost = econ_ply.plot_cost_structure(econ_series)
                    st.plotly_chart(fig_cost, width='stretch', key=f"cost_structure_{sel_year}")
                
                with col_inv:
                    st.markdown(f"#### Investitionsmix {sel_year} (Mrd. €)")
                    # Investitionsverteilung pro Technologie für das aktuelle Jahr
                    econ_data = results[sel_year].get("economics", {})
                    if "investment_by_tech" in econ_data and econ_data["investment_by_tech"]:
                        fig_donut = econ_ply.plot_investment_donut(
                            econ_data["investment_by_tech"],
                            sel_year
                        )
                        st.plotly_chart(fig_donut, width='stretch', key=f"invest_donut_{sel_year}")
                    else:
                        st.info("Investitionsverteilung nach Technologie nicht verfügbar.")

            # Download-Buttons NACH den Visualisierungen (mit intelligentem Caching)
            st.markdown("---")
            st.subheader("Download")
            
            # Hole Szenario-Namen aus session_state
            scenario_name = st.session_state.sm.scenario_data.get("metadata", {}).get("name", "Szenario")
            
            # Excel für einzelnes Jahr (lazy loading mit Spinner)
            excel_key = f"excel_{sel_year}"
            if excel_key not in st.session_state.excel_exports:
                # Zeige Spinner während der Generierung
                with st.spinner(f"📊 Generiere Excel für {sel_year}..."):
                    st.session_state.excel_exports[excel_key] = SimulationEngine.export_results_to_excel(results, sel_year)
            
            st.download_button(
                "📥 Download Jahresergebnisse (EXCEL)", 
                data=st.session_state.excel_exports[excel_key],
                file_name=f"Ergebnisse_{scenario_name}_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_excel_{sel_year}"
            )

            # ZIP nur bei mehreren Jahren anzeigen
            if len(years_available) > 1:
                zip_key = "excel_zip"
                if zip_key not in st.session_state.excel_exports:
                    # Zeige Spinner während der Generierung
                    with st.spinner(f"📦 Generiere ZIP mit allen {len(years_available)} Jahren..."):
                        st.session_state.excel_exports[zip_key] = SimulationEngine.export_results_to_zip(results)
                
                st.download_button(
                    "📦 Download alle Jahre (ZIP mit EXCEL)", 
                    data=st.session_state.excel_exports[zip_key],
                    file_name=f"Ergebnisse_{scenario_name}_alle_jahre.zip",
                    mime="application/zip",
                    key="download_zip_all"
                )
