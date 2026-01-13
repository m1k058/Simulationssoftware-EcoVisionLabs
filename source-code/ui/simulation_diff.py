# Standard Bibliotheken
import streamlit as st 
import pandas as pd

# Eigene Imports
from data_processing.simulation_engine import SimulationEngine
import plotting.plotting_plotly_st as ply

# Manager Imports
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager


def diff_simulation_page() -> None:
    """
    Diff Mode Page: Zwei Szenarios laden, Inkremente eingeben, und alle interpolierten Szenarien simulieren.
    """
    st.title("Simulation (Diff Mode)")
    st.caption("Laden Sie zwei Szenarios und generieren Sie interpolierte Varianten für den Vergleich.")

    # Überprüfe ob DataManager, ConfigManager, ScenarioManager geladen sind
    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")
        return

    st.markdown("---")
    st.markdown("## Szenario-Paare und Inkremente")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Szenario 1 (Basis)**")
        uploaded_scenario_1 = st.file_uploader(
            "Lade Szenario 1 hoch",
            type=["yaml"],
            key="diff_file_upload_1"
        )
        if st.button("Szenario 1 laden", key="load_s1"):
            if uploaded_scenario_1:
                scenario_1 = st.session_state.sm.load_scenario(uploaded_scenario_1)
                st.session_state.diff_scenario_1_data = scenario_1
                st.success("✅ Szenario 1 geladen")
            else:
                st.warning("⚠️ Bitte wähle eine Datei aus")

        if "diff_scenario_1_data" in st.session_state and st.session_state.diff_scenario_1_data is not None:
            s1_meta = st.session_state.diff_scenario_1_data.get("metadata", {})
            st.info(f"✓ {s1_meta.get('name', 'Szenario 1')}")

    with col2:
        st.write("**Szenario 2 (Ziel)**")
        uploaded_scenario_2 = st.file_uploader(
            "Lade Szenario 2 hoch",
            type=["yaml"],
            key="diff_file_upload_2"
        )
        if st.button("Szenario 2 laden", key="load_s2"):
            if uploaded_scenario_2:
                scenario_2 = st.session_state.sm.load_scenario(uploaded_scenario_2)
                st.session_state.diff_scenario_2_data = scenario_2
                st.success("✅ Szenario 2 geladen")
            else:
                st.warning("⚠️ Bitte wähle eine Datei aus")

        if "diff_scenario_2_data" in st.session_state and st.session_state.diff_scenario_2_data is not None:
            s2_meta = st.session_state.diff_scenario_2_data.get("metadata", {})
            st.info(f"✓ {s2_meta.get('name', 'Szenario 2')}")

    st.markdown("---")
    st.markdown("## Inkremente")

    increments = st.slider(
        "Anzahl der Inkremente (1-8)",
        min_value=1,
        max_value=8,
        value=3,
        key="diff_increments"
    )

    st.write(f"Werden {increments + 2} Szenarien generiert (Szenario 1 + {increments} Inkremente + Szenario 2)")

    if ("diff_scenario_1_data" in st.session_state and st.session_state.diff_scenario_1_data is not None and
        "diff_scenario_2_data" in st.session_state and st.session_state.diff_scenario_2_data is not None):
        if st.button("Alle Szenarien simulieren", type="primary", key="run_diff_sim"):
            try:
                # Interpoliere alle Szenarien
                interpolated_scenarios = _interpolate_scenarios(
                    st.session_state.diff_scenario_1_data,
                    st.session_state.diff_scenario_2_data,
                    increments
                )

                # Simuliere alle
                st.session_state.diff_sim_results = {}
                progress_bar = st.progress(0)

                for idx, (inc_label, scenario) in enumerate(interpolated_scenarios.items()):
                    # Temporär Szenario in sm setzen
                    st.session_state.sm.current_scenario = scenario

                    engine = SimulationEngine(
                        st.session_state.cfg,
                        st.session_state.dm,
                        st.session_state.sm
                    )
                    results = engine.run_scenario()
                    st.session_state.diff_sim_results[inc_label] = results

                    progress = (idx + 1) / len(interpolated_scenarios)
                    progress_bar.progress(progress)

                st.success(f"✅ {len(interpolated_scenarios)} Szenarien simuliert!")
                
                # Zeige Vergleichstabelle mit interpolierten Werten
                st.markdown("---")
                st.subheader("📊 Interpolierte Szenario-Parameter")
                _display_interpolation_table(
                    st.session_state.diff_scenario_1_data,
                    st.session_state.diff_scenario_2_data,
                    interpolated_scenarios
                )

            except Exception as e:
                st.error(f"❌ Fehler: {e}")

        if "diff_sim_results" in st.session_state and st.session_state.diff_sim_results:
            st.markdown("---")
            st.subheader("📈 Parameter-Sättigungskurve")
            st.caption("KPI vs. Gesamtkapazität der Speicher (inkl. saisonaler Auswertung)")
            
            # Extrahiere KPIs (gesamt, Winter, Sommer) und Gesamtkapazität je Szenario
            saturation_sets = _extract_kpi_for_saturation(
                st.session_state.diff_sim_results,
                interpolated_scenarios
            )
            
            if saturation_sets and saturation_sets.get("all"):
                fig_saturation = ply.plot_parameter_saturation(
                    simulation_results=saturation_sets["all"],
                    parameter_name="Gesamtkapazität Speicher [MWh]",
                    kpi_name="Durchschnittliche Rest-Bilanz [MWh]",
                    title="KPI-Entwicklung (Gesamt)"
                )
                st.plotly_chart(fig_saturation, width='stretch')

            # Zeige Winter/Sommer nebeneinander
            if saturation_sets and (saturation_sets.get("winter") or saturation_sets.get("summer")):
                col_w, col_s = st.columns(2)
                if saturation_sets.get("winter"):
                    fig_w = ply.plot_parameter_saturation(
                        simulation_results=saturation_sets["winter"],
                        parameter_name="Gesamtkapazität Speicher [MWh]",
                        kpi_name="Durchschnittliche Rest-Bilanz [MWh]",
                        title="Winter (Dez–Feb)"
                    )
                    col_w.plotly_chart(fig_w, width='stretch')
                else:
                    col_w.info("Keine Winter-Daten")

                if saturation_sets.get("summer"):
                    fig_s = ply.plot_parameter_saturation(
                        simulation_results=saturation_sets["summer"],
                        parameter_name="Gesamtkapazität Speicher [MWh]",
                        kpi_name="Durchschnittliche Rest-Bilanz [MWh]",
                        title="Sommer (Jun–Aug)"
                    )
                    col_s.plotly_chart(fig_s, width='stretch')
                else:
                    col_s.info("Keine Sommer-Daten")
            
            st.markdown("---")
            st.subheader("Ergebnisse")

            # Auswahl welcher Increment/Jahr angezeigt werden soll
            inc_labels = sorted(list(st.session_state.diff_sim_results.keys()))
            sel_inc_str = st.selectbox(
                "Wähle ein Inkrement",
                inc_labels,
                key="diff_inc_select"
            )

            if sel_inc_str and sel_inc_str in st.session_state.diff_sim_results:
                results_inc = st.session_state.diff_sim_results[sel_inc_str]

                # Für jeden Jahr in den Ergebnissen Tabs mit Downloads
                for year in sorted(results_inc.keys()):
                    with st.expander(f"Jahr {year}", expanded=(year == sorted(results_inc.keys())[0])):
                        tab_con, tab_prod, tab_bal, tab_stor = st.tabs([
                            "Verbrauch", "Erzeugung", "Bilanz", "Speicher"
                        ])

                        with tab_con:
                            df = results_inc[year]["consumption"]
                            st.dataframe(df, width='stretch')
                            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                            st.download_button(
                                "Download Verbrauch CSV",
                                data=csv,
                                file_name=f"diff_{sel_inc_str}_verbrauch_{year}.csv",
                                mime="text/csv",
                                key=f"dl_con_{sel_inc_str}_{year}"
                            )

                        with tab_prod:
                            df = results_inc[year]["production"]
                            st.dataframe(df, width='stretch')
                            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                            st.download_button(
                                "Download Erzeugung CSV",
                                data=csv,
                                file_name=f"diff_{sel_inc_str}_erzeugung_{year}.csv",
                                mime="text/csv",
                                key=f"dl_prod_{sel_inc_str}_{year}"
                            )

                        with tab_bal:
                            df = results_inc[year]["balance"]
                            st.dataframe(df, width='stretch')
                            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                            st.download_button(
                                "Download Bilanz CSV",
                                data=csv,
                                file_name=f"diff_{sel_inc_str}_bilanz_{year}.csv",
                                mime="text/csv",
                                key=f"dl_bal_{sel_inc_str}_{year}"
                            )

                        with tab_stor:
                            df = results_inc[year]["storage"]
                            st.dataframe(df, width='stretch')
                            csv = df.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
                            st.download_button(
                                "Download Speicher CSV",
                                data=csv,
                                file_name=f"diff_{sel_inc_str}_speicher_{year}.csv",
                                mime="text/csv",
                                key=f"dl_stor_{sel_inc_str}_{year}"
                            )
    else:
        st.info("⚠️ Bitte lade beide Szenarios hoch, um zu beginnen.")


def _interpolate_scenarios(scenario_1: dict, scenario_2: dict, num_increments: int) -> dict:
    """
    Interpoliert linear zwischen zwei Szenarien für 2 + num_increments Szenarien.
    
    Args:
        scenario_1: Basis-Szenario
        scenario_2: Ziel-Szenario
        num_increments: Anzahl der interpolierten Inkremente zwischen den zwei Szenarien
    
    Returns:
        dict mit Keys "Szenario 1", "Inkrement 1", ..., "Inkrement num_increments", "Szenario 2"
        und Szenarios als Values
    """
    import copy
    import numpy as np

    result = {}
    
    # Füge zuerst das original Szenario 1 hinzu
    result["Szenario 1"] = copy.deepcopy(scenario_1)

    # Interpoliere die Inkremente dazwischen
    for increment in range(1, num_increments + 1):
        # Berechne Interpolationsfaktor zwischen den zwei Szenarien
        t = increment / (num_increments + 1)

        # Erstelle neues Szenario mit interpolierten Werten
        new_scenario = copy.deepcopy(scenario_1)

        # Kopiere Metadaten aber update Name
        new_scenario["metadata"] = copy.deepcopy(scenario_1.get("metadata", {}))
        s1_name = scenario_1.get("metadata", {}).get("name", "Szenario 1")
        s2_name = scenario_2.get("metadata", {}).get("name", "Szenario 2")
        new_scenario["metadata"]["name"] = f"Inkrement {increment} ({s1_name} → {s2_name})"

        # Interpoliere Verbrauchswerte
        load_1 = scenario_1.get("target_load_demand_twh", {})
        load_2 = scenario_2.get("target_load_demand_twh", {})
        new_load = copy.deepcopy(load_1)

        for sector in load_1.keys():
            if isinstance(load_1[sector], dict) and sector in load_2:
                for year_key in load_1[sector].keys():
                    if year_key in load_2[sector]:
                        v1 = load_1[sector][year_key]
                        v2 = load_2[sector][year_key]
                        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                            new_load[sector][year_key] = v1 + (v2 - v1) * t

        new_scenario["target_load_demand_twh"] = new_load

        # Interpoliere Erzeugungskapazitäten
        gen_1 = scenario_1.get("target_generation_capacities_mw", {})
        gen_2 = scenario_2.get("target_generation_capacities_mw", {})
        new_gen = copy.deepcopy(gen_1)

        for tech in gen_1.keys():
            if isinstance(gen_1[tech], dict) and tech in gen_2:
                for year_key in gen_1[tech].keys():
                    if year_key in gen_2[tech]:
                        v1 = gen_1[tech][year_key]
                        v2 = gen_2[tech][year_key]
                        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                            new_gen[tech][year_key] = v1 + (v2 - v1) * t

        new_scenario["target_generation_capacities_mw"] = new_gen

        # Speicher interpolieren (optional, kopiere von Szenario 1)
        if "target_storage_capacities" in scenario_1:
            stor_1 = scenario_1.get("target_storage_capacities", {})
            stor_2 = scenario_2.get("target_storage_capacities", {})
            new_stor = copy.deepcopy(stor_1)

            for storage_type in stor_1.keys():
                if isinstance(stor_1[storage_type], dict) and storage_type in stor_2:
                    for year_key in stor_1[storage_type].keys():
                        if year_key in stor_2[storage_type]:
                            for param in stor_1[storage_type][year_key].keys():
                                v1 = stor_1[storage_type][year_key][param]
                                v2 = stor_2[storage_type][year_key].get(param, v1)
                                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                                    new_stor[storage_type][year_key][param] = v1 + (v2 - v1) * t

            new_scenario["target_storage_capacities"] = new_stor

        # Wetterprofile kopieren (keine Interpolation nötig, nimm von Szenario 1)
        if "weather_generation_profiles" in scenario_1:
            new_scenario["weather_generation_profiles"] = copy.deepcopy(
                scenario_1.get("weather_generation_profiles", {})
            )

        result[f"Inkrement {increment}"] = new_scenario
    
    # Füge am Ende das original Szenario 2 hinzu
    result["Szenario 2"] = copy.deepcopy(scenario_2)

    return result


def _display_interpolation_table(scenario_1: dict, scenario_2: dict, interpolated_scenarios: dict) -> None:
    """
    Zeigt eine Tabelle mit den interpolierten Szenario-Parametern
    Markiert Zeilen die sich zwischen Szenario 1 und Szenario 2 geändert haben
    """
    import pandas as pd
    
    # Sammle Werte
    data_rows = []
    
    # Verbrauch (target_load_demand_twh)
    load_1 = scenario_1.get("target_load_demand_twh", {})
    load_2 = scenario_2.get("target_load_demand_twh", {})
    
    for sector in load_1.keys():
        if isinstance(load_1.get(sector), dict) and sector in load_2:
            for year_key in load_1[sector].keys():
                if year_key in load_2[sector]:
                    v1 = load_1[sector].get(year_key, 0)
                    v2 = load_2[sector].get(year_key, 0)
                    
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                        row = {"Parameter": f"Verbrauch: {sector} ({year_key})", "Szenario 1": round(v1, 2)}
                        
                        # Füge Inkremente hinzu
                        for inc_label, scenario in sorted(interpolated_scenarios.items()):
                            if inc_label.startswith("Inkrement"):
                                inc_val = scenario.get("target_load_demand_twh", {}).get(sector, {}).get(year_key, 0)
                                row[inc_label] = round(inc_val, 2)
                        
                        row["Szenario 2"] = round(v2, 2)
                        row["_changed"] = v1 != v2
                        data_rows.append(row)
    
    # Erzeugungskapazitäten (target_generation_capacities_mw)
    gen_1 = scenario_1.get("target_generation_capacities_mw", {})
    gen_2 = scenario_2.get("target_generation_capacities_mw", {})
    
    for tech in gen_1.keys():
        if isinstance(gen_1.get(tech), dict) and tech in gen_2:
            for year_key in gen_1[tech].keys():
                if year_key in gen_2[tech]:
                    v1 = gen_1[tech].get(year_key, 0)
                    v2 = gen_2[tech].get(year_key, 0)
                    
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                        row = {"Parameter": f"Kapazität: {tech} ({year_key})", "Szenario 1": round(v1, 0)}
                        
                        # Füge Inkremente hinzu
                        for inc_label, scenario in sorted(interpolated_scenarios.items()):
                            if inc_label.startswith("Inkrement"):
                                inc_val = scenario.get("target_generation_capacities_mw", {}).get(tech, {}).get(year_key, 0)
                                row[inc_label] = round(inc_val, 0)
                        
                        row["Szenario 2"] = round(v2, 0)
                        row["_changed"] = v1 != v2
                        data_rows.append(row)
    
    # Speicherkapazitäten (target_storage_capacities)
    if "target_storage_capacities" in scenario_1:
        stor_1 = scenario_1.get("target_storage_capacities", {})
        stor_2 = scenario_2.get("target_storage_capacities", {})
        
        for storage_type in stor_1.keys():
            if isinstance(stor_1.get(storage_type), dict) and storage_type in stor_2:
                for year_key in stor_1[storage_type].keys():
                    if year_key in stor_2[storage_type]:
                        for param in stor_1[storage_type][year_key].keys():
                            v1 = stor_1[storage_type][year_key].get(param, 0)
                            v2 = stor_2[storage_type][year_key].get(param, 0)
                            
                            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                                row = {"Parameter": f"Speicher: {storage_type} - {param} ({year_key})", "Szenario 1": round(v1, 2)}
                                
                                # Füge Inkremente hinzu
                                for inc_label, scenario in sorted(interpolated_scenarios.items()):
                                    if inc_label.startswith("Inkrement"):
                                        inc_val = scenario.get("target_storage_capacities", {}).get(storage_type, {}).get(year_key, {}).get(param, 0)
                                        row[inc_label] = round(inc_val, 2)
                                
                                row["Szenario 2"] = round(v2, 2)
                                row["_changed"] = v1 != v2
                                data_rows.append(row)
    
    if data_rows:
        df_comparison = pd.DataFrame(data_rows)
        
        # Entferne die _changed Spalte vor der Anzeige
        display_df = df_comparison.drop("_changed", axis=1)
        
        # Wende Styling an - markiere Zeilen die sich verändert haben
        styled_df = display_df.style.apply(
            lambda row: ["background-color: #ffdb3b; color: black"] * len(row) if df_comparison.loc[row.name, "_changed"] else [""] * len(row),
            axis=1
        )
        
        st.dataframe(styled_df, width='stretch', hide_index=True)
    else:
        st.info("Keine vergleichbaren Parameter gefunden")


def _extract_kpi_for_saturation(diff_sim_results: dict, interpolated_scenarios: dict) -> list[dict]:
    """
    Extrahiert KPI-Werte aus den Simulationsergebnissen für die Sättigungskurve.
    
    Args:
        diff_sim_results: Dict mit Simulationsergebnissen pro Szenario
        interpolated_scenarios: Dict mit interpolierten Szenarien
    
    Returns:
        Dict mit Keys 'all', 'winter', 'summer' und jeweiligen Listen aus
        Dicts: 'scenario_label', 'parameter_value', 'kpi_value'
    """
    import pandas as pd
    import numpy as np
    
    data_all = []
    data_winter = []
    data_summer = []
    winter_months = {12, 1, 2}
    summer_months = {6, 7, 8}
    
    # Definiere Sortierung für korrekte Reihenfolge
    scenario_order = ["Szenario 1"] + [f"Inkrement {i}" for i in range(1, 100)] + ["Szenario 2"]
    
    for idx, (scenario_label, results) in enumerate(sorted(
        diff_sim_results.items(), 
        key=lambda x: scenario_order.index(x[0]) if x[0] in scenario_order else 999
    )):
        scenario = interpolated_scenarios.get(scenario_label)
        param_value = _compute_total_storage_capacity(scenario) if scenario else idx

        kpi_all = []
        kpi_winter = []
        kpi_summer = []

        for year, year_results in results.items():
            # Quelle: bevorzugt storage Rest Bilanz, sonst original balance
            df_source = None
            col_name = None
            if "storage" in year_results and "Rest Bilanz [MWh]" in year_results["storage"].columns:
                df_source = year_results["storage"]
                col_name = "Rest Bilanz [MWh]"
            elif "balance" in year_results and "Bilanz [MWh]" in year_results["balance"].columns:
                df_source = year_results["balance"]
                col_name = "Bilanz [MWh]"

            if df_source is None or col_name is None:
                continue

            series = df_source[col_name]

            # Full year
            kpi_all.append(series.mean())

            # Winter (Dez/Jan/Feb) und Sommer (Jun/Jul/Aug) falls Zeitpunkt vorhanden
            if "Zeitpunkt" in df_source.columns:
                ts = pd.to_datetime(df_source["Zeitpunkt"])
                winter_mask = ts.dt.month.isin(winter_months)
                summer_mask = ts.dt.month.isin(summer_months)
                if winter_mask.any():
                    kpi_winter.append(series[winter_mask].mean())
                if summer_mask.any():
                    kpi_summer.append(series[summer_mask].mean())

        if kpi_all:
            data_all.append({
                "scenario_label": scenario_label,
                "parameter_value": param_value,
                "kpi_value": float(np.mean(kpi_all))
            })
        if kpi_winter:
            data_winter.append({
                "scenario_label": scenario_label,
                "parameter_value": param_value,
                "kpi_value": float(np.mean(kpi_winter))
            })
        if kpi_summer:
            data_summer.append({
                "scenario_label": scenario_label,
                "parameter_value": param_value,
                "kpi_value": float(np.mean(kpi_summer))
            })
    
    return {
        "all": data_all,
        "winter": data_winter,
        "summer": data_summer,
    }


def _compute_total_storage_capacity(scenario: dict | None) -> float:
    """Summiert installierte Speicher-Kapazitäten (MWh) über alle Speicherarten.
    Nimmt den jüngsten Jahrgang pro Speicherart, falls mehrere Jahre vorhanden sind.
    """
    if not scenario:
        return 0.0

    storage = scenario.get("target_storage_capacities", {})
    total = 0.0

    for storage_type, per_year in storage.items():
        if not isinstance(per_year, dict):
            continue
        # Wähle den jüngsten Jahrgang, dann installierte Kapazität
        years = sorted([y for y in per_year.keys() if str(y).isdigit()], key=lambda x: int(x))
        if not years:
            continue
        latest_year = years[-1]
        attrs = per_year.get(latest_year, {})
        cap = attrs.get("installed_capacity_mwh") or attrs.get("installed_capacity_MWh")
        if isinstance(cap, (int, float)):
            total += cap

    return float(total)
