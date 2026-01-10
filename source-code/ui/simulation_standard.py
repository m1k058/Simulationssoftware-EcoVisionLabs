# Standard Bibliotheken
import streamlit as st 
import pandas as pd
from datetime import datetime

# Eigene Imports
import data_processing.generation_profile as genPro
import data_processing.simulation as simu
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
                    col_em = st.columns(2)
                    with col_em[0]:
                        st.metric("Installierte Einheiten", f"{em_params.get('installed_units', 0):,}")
                        st.metric("Jahresverbrauch/Einheit", f"{em_params.get('annual_consumption_kwh', 0):,.0f} kWh")
                    with col_em[1]:
                        st.metric("Lastprofil", em_params.get("load_profile", "—"))
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
                st.session_state.fullSimResults = simu.kobi(
                    st.session_state.cfg,
                    st.session_state.dm,
                    st.session_state.sm
                )
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
            tab_con, tab_prod, tab_bal, tab_stor, tab_econ = st.tabs([
                "Verbrauch", "Erzeugung", "Bilanz", "Speicher", "Wirtschaftlichkeit"
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
            date_from_gen, date_to_gen = create_date_range_selector(
                results[sel_year]["production"],
                key_suffix=f"gen_{sel_year}"
            )
            fig_gen = ply.create_generation_plot(
                results[sel_year]["production"],
                title="",
                date_from=date_from_gen,
                date_to=date_to_gen
            )
            st.plotly_chart(fig_gen)

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


