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

        if "fullSimResults" not in st.session_state:
            st.session_state.fullSimResults = {}

        if st.button("Simulation starten", type="primary"):
            try:
                engine = SimulationEngine(
                    st.session_state.cfg,
                    st.session_state.dm,
                    st.session_state.sm,
                    verbose=True  # Debug-Modus aktiviert
                )
                st.session_state.fullSimResults = engine.run_scenario()
                st.success("Simulation abgeschlossen.")
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

            # Tabs pro Ergebnis-DF
            tab_con, tab_prod, tab_bal, tab_emob, tab_stor, tab_econ = st.tabs([
                "Verbrauch", "Erzeugung", "Bilanz", "E-Mobilität", "Speicher", "Wirtschaftlichkeit"
            ])

            with tab_con:
                df = results[sel_year]["consumption"]
                st.dataframe(df, width='stretch')
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

            with tab_bal:
                df = results[sel_year]["balance"]
                st.dataframe(df, width='stretch')
                csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Bilanz CSV",
                    data=csv,
                    file_name=f"bilanz_{sel_year}.csv",
                    mime="text/csv"
                )

            with tab_emob:
                df_bal = results[sel_year]["balance"]
                # Prüfe ob E-Mobility-Daten vorhanden sind
                if 'EMobility SOC [MWh]' in df_bal.columns:
                    st.subheader(":material/directions_car: E-Mobility Ergebnisse")
                    
                    # Kennzahlen in Spalten
                    em_col1, em_col2, em_col3, em_col4 = st.columns(4)
                    
                    with em_col1:
                        avg_soc = df_bal['EMobility SOC [MWh]'].mean()
                        st.metric(
                            "Ø SOC",
                            f"{avg_soc:,.0f} MWh"
                        )
                    
                    with em_col2:
                        total_charged = df_bal['EMobility Charge [MWh]'].sum()
                        st.metric(
                            "Gesamt geladen",
                            f"{total_charged:,.0f} MWh"
                        )
                    
                    with em_col3:
                        total_discharged = df_bal['EMobility Discharge [MWh]'].sum()
                        st.metric(
                            "Gesamt entladen",
                            f"{total_discharged:,.0f} MWh"
                        )
                    
                    with em_col4:
                        total_drive = df_bal['EMobility Drive [MWh]'].sum()
                        st.metric(
                            "Fahrverbrauch",
                            f"{total_drive:,.0f} MWh"
                        )
                    
                    # Zweite Zeile Kennzahlen
                    em_col5, em_col6, em_col7, em_col8 = st.columns(4)
                    
                    with em_col5:
                        if 'EMobility Power [MW]' in df_bal.columns:
                            max_charge = df_bal['EMobility Power [MW]'].min()
                            st.metric(
                                "Max. Ladeleistung",
                                f"{abs(max_charge):,.0f} MW"
                            )
                    
                    with em_col6:
                        if 'EMobility Power [MW]' in df_bal.columns:
                            max_discharge = df_bal['EMobility Power [MW]'].max()
                            st.metric(
                                "Max. Entladeleistung",
                                f"{max_discharge:,.0f} MW"
                            )
                    
                    with em_col7:
                        min_soc = df_bal['EMobility SOC [MWh]'].min()
                        st.metric(
                            "Min. SOC",
                            f"{min_soc:,.0f} MWh"
                        )
                    
                    with em_col8:
                        max_soc = df_bal['EMobility SOC [MWh]'].max()
                        st.metric(
                            "Max. SOC",
                            f"{max_soc:,.0f} MWh"
                        )
                    
                    # E-Mobility-Spalten als DataFrame anzeigen
                    em_columns = [col for col in df_bal.columns if 'EMobility' in col]
                    df_em_display = df_bal[em_columns].copy()
                    df_em_display.insert(0, 'Zeitpunkt', df_bal.index if 'Zeitpunkt' not in df_bal.columns else df_bal['Zeitpunkt'])
                    st.dataframe(df_em_display, width='stretch')
                    
                    csv_em = df_em_display.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                    st.download_button(
                        "Download E-Mobility CSV",
                        data=csv_em,
                        file_name=f"emobility_{sel_year}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Keine E-Mobility-Daten verfügbar. Stellen Sie sicher, dass E-Mobility-Parameter im Szenario definiert sind.")

            with tab_stor:
                df = results[sel_year]["storage"]
                st.dataframe(df, width='stretch')
                csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                st.download_button(
                    "Download Speicher CSV",
                    data=csv,
                    file_name=f"speicher_{sel_year}.csv",
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


            # Visualisierungen
            st.markdown("---")
            st.subheader("Visualisierung")

            st.markdown("### Verbrauchssimulation")
            st.caption("Stundliche Verbrauchswerte nach Sektor (Haushalte, Gewerbe, Landwirtschaft)")
            date_from_con, date_to_con = create_date_range_selector(
                results[sel_year]["consumption"],
                key_suffix=f"cons_{sel_year}"
            )
            fig_con = ply.create_consumption_plot(
                results[sel_year]["consumption"],
                title="",
                date_from=date_from_con,
                date_to=date_to_con
            )
            st.plotly_chart(fig_con)

            st.markdown("### Erzeugungssimulation")
            st.caption("Stundliche Erzeugungswerte nach Technologie (Wind, Solar, Biomasse, etc.)")
            
            # Prüfe ob Erzeugungsdaten vorhanden sind
            df_prod = results[sel_year]["production"]
            prod_cols = [c for c in df_prod.columns if "[MWh]" in c and "Gesamt" not in c and "Zeitpunkt" not in c]
            
            if prod_cols and df_prod[prod_cols].sum().sum() > 0:
                date_from_gen, date_to_gen = create_date_range_selector(
                    df_prod,
                    key_suffix=f"gen_{sel_year}"
                )
                fig_gen = ply.create_generation_plot(
                    df_prod,
                    title="",
                    date_from=date_from_gen,
                    date_to=date_to_gen
                )
                st.plotly_chart(fig_gen)
            else:
                st.warning("⚠️ Keine Erzeugungsdaten vorhanden. Bitte prüfen Sie, ob Ziel-Kapazitäten im Szenario definiert sind.")

            st.markdown("### Bilanzberechnung")
            st.caption("Bilanz zwischen Erzeugung und Verbrauch (positiv = Überschuss, negativ = Defizit)")
            date_from_bal, date_to_bal = create_date_range_selector(
                results[sel_year]["balance"],
                key_suffix=f"bal_{sel_year}"
            )
            fig_bal = ply.create_balance_area_plot(
                results[sel_year]["balance"],
                title=" ",
                date_from=date_from_bal,
                date_to=date_to_bal
            )
            st.plotly_chart(fig_bal)

            st.markdown("### Erzeugung vs. Verbrauch")
            st.caption("Direkter Vergleich: Erzeugung und Verbrauch im gleichen Zeitfenster")
            combo_df = results[sel_year]["production"].copy()
            combo_df["Skalierte Netzlast [MWh]"] = results[sel_year]["consumption"]["Gesamt [MWh]"]
            
            # Prüfe ob Erzeugungsdaten vorhanden sind
            combo_prod_cols = [c for c in combo_df.columns if "[MWh]" in c and "Gesamt" not in c and "Zeitpunkt" not in c and "Netzlast" not in c]
            if combo_prod_cols and combo_df[combo_prod_cols].sum().sum() > 0:
                date_from_combo, date_to_combo = create_date_range_selector(
                    combo_df,
                    key_suffix=f"combo_{sel_year}"
                )
                fig_combo = ply.create_generation_with_load_plot(
                    df=combo_df,
                    title=" ",
                    date_from=date_from_combo,
                    date_to=date_to_combo
                )
                st.plotly_chart(fig_combo)
            else:
                st.info("Erzeugung vs. Verbrauch nicht verfügbar - keine Erzeugungsdaten.")

            if not results[sel_year]["storage"].empty:
                stor_plot_df = results[sel_year]["storage"].copy()
                stor_plot_df['Bilanz [MWh]'] = results[sel_year]['balance']['Bilanz [MWh]']

                st.markdown("### Speichersimulation")
                st.markdown("#### Geordnete Jahresdauerlinie (Residuallast)")
                st.caption("Sortierte Bilanz über das Jahr - zeigt, wie oft und wie lange Defizite/Überschüsse auftreten")
                fig_duration = ply.create_duration_curve_plot(
                    stor_plot_df,
                    title=" "
                )
                st.plotly_chart(fig_duration)

                st.markdown("#### State of Charge (SOC) der Speicher")
                st.caption("Ladestand aller Speicher über die Zeit - Batterien, Pumpspeicher und H₂-Speicher")
                date_from_stor, date_to_stor = create_date_range_selector(
                    stor_plot_df,
                    key_suffix=f"stor_{sel_year}"
                )
                fig_soc = ply.create_soc_stacked_plot(
                    stor_plot_df,
                    title=" ",
                    date_from=date_from_stor,
                    date_to=date_to_stor
                )
                st.plotly_chart(fig_soc)

            # E-Mobility Visualisierung
            df_bal = results[sel_year]["balance"]
            if 'EMobility SOC [MWh]' in df_bal.columns:
                st.markdown("### E-Mobility (V2G) Simulation")
                
                # SOC-Verlauf der EV-Flotte
                st.markdown("#### State of Charge (SOC) der EV-Flotte")
                st.caption("Aggregierter Ladestand aller Elektrofahrzeuge über die Zeit")
                date_from_ev, date_to_ev = create_date_range_selector(
                    df_bal,
                    key_suffix=f"emob_{sel_year}"
                )
                
                # SOC Plot
                import plotly.graph_objects as go
                df_filtered = df_bal.copy()
                if date_from_ev and date_to_ev:
                    df_filtered = df_filtered[(df_filtered.index >= date_from_ev) & (df_filtered.index <= date_to_ev)]
                
                fig_ev_soc = go.Figure()
                fig_ev_soc.add_trace(go.Scatter(
                    x=df_filtered.index,
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
                st.plotly_chart(fig_ev_soc, use_container_width=True)
                
                # Lade-/Entladeleistung Plot
                if 'EMobility Power [MW]' in df_bal.columns:
                    st.markdown("#### Lade-/Entladeleistung der EV-Flotte")
                    st.caption("Negative Werte = Laden aus Netz, Positive Werte = Rückspeisung ins Netz (V2G)")
                    
                    fig_ev_power = go.Figure()
                    power_col = df_filtered['EMobility Power [MW]']
                    
                    # Positive Werte (Entladen/V2G) in Grün
                    fig_ev_power.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=power_col.clip(lower=0),
                        mode='lines',
                        name='V2G Rückspeisung',
                        fill='tozeroy',
                        line=dict(color='#27ae60', width=0.5),
                        fillcolor='rgba(39, 174, 96, 0.5)'
                    ))
                    
                    # Negative Werte (Laden) in Rot
                    fig_ev_power.add_trace(go.Scatter(
                        x=df_filtered.index,
                        y=power_col.clip(upper=0),
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
                    st.plotly_chart(fig_ev_power, use_container_width=True)

                # Wirtschaftlichkeit über alle Jahre (Trend) unterhalb der SOC-Grafiken
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
                    st.plotly_chart(fig_econ, width='stretch')
                    
                    # Nebendiagramme: Kostenaufschlüsselung und Investitionsmix
                    col_cost, col_inv = st.columns(2)
                    
                    with col_cost:
                        st.markdown("#### Kostenaufschlüsselung (Mrd. €/Jahr)")
                        fig_cost = econ_ply.plot_cost_structure(econ_series)
                        st.plotly_chart(fig_cost, width='stretch')
                    
                    with col_inv:
                        st.markdown(f"#### Investitionsmix {sel_year} (Mrd. €)")
                        # Investitionsverteilung pro Technologie für das aktuelle Jahr
                        econ_data = results[sel_year].get("economics", {})
                        if "investment_by_tech" in econ_data and econ_data["investment_by_tech"]:
                            fig_donut = econ_ply.plot_investment_donut(
                                econ_data["investment_by_tech"],
                                sel_year
                            )
                            st.plotly_chart(fig_donut, width='stretch')
                        else:
                            st.info("Investitionsverteilung nach Technologie nicht verfügbar.")


