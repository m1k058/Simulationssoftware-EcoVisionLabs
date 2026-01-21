# Standard Bibliotheken
import streamlit as st 
import pandas as pd

# Eigene Imports
from data_processing.simulation_engine import SimulationEngine
import plotting.plotting_plotly_st as ply
from ui.kpi_dashboard import convert_results_to_scoring_format, normalize_storage_config
from data_processing.scoring_system import get_score_and_kpis
from plotting.scoring_plots import get_category_scores, KPI_CONFIG

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
                # Interpoliere Szenarien
                interpolated_scenarios = _interpolate_scenarios(
                    st.session_state.diff_scenario_1_data,
                    st.session_state.diff_scenario_2_data,
                    increments
                )
                st.session_state.diff_interpolated_scenarios = interpolated_scenarios

                # Simuliere
                st.session_state.diff_sim_results = {}
                progress_bar = st.progress(0)

                for idx, (inc_label, scenario) in enumerate(interpolated_scenarios.items()):
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
            interpolated_scenarios = st.session_state.get("diff_interpolated_scenarios", {})
            st.markdown("---")
            st.subheader("📊 KPI Score Vergleich")

            rows = []

            def _inc_sort(label: str) -> tuple:
                if label == "Szenario 1":
                    return (0, 0)
                if label.startswith("Inkrement "):
                    try:
                        num = int(label.split("Inkrement ")[-1])
                    except Exception:
                        num = 999
                    return (1, num)
                if label == "Szenario 2":
                    return (2, 0)
                return (3, label)

            inc_labels = sorted(list(st.session_state.diff_sim_results.keys()), key=_inc_sort)

            # gemeinsame Jahre
            common_years = None
            for inc_label in inc_labels:
                year_keys = st.session_state.diff_sim_results.get(inc_label, {}).keys()
                year_set = {int(y) for y in year_keys}
                common_years = year_set if common_years is None else common_years & year_set
            common_years = sorted(common_years) if common_years else []

            if not common_years:
                st.info("Keine gemeinsamen Jahre in den Simulationsergebnissen gefunden.")
                return

            selected_year = st.selectbox(
                "Jahr für KPI-Vergleich auswählen",
                options=common_years,
                index=0,
                key="diff_kpi_year_select",
            )

            for inc_label in inc_labels:
                results_inc = st.session_state.diff_sim_results.get(inc_label)
                if not results_inc:
                    continue

                storage_cfg_raw = interpolated_scenarios.get(inc_label, {}).get("target_storage_capacities", {})
                storage_cfg = normalize_storage_config(storage_cfg_raw)
                if not storage_cfg:
                    continue

                try:
                    if selected_year not in results_inc:
                        st.warning(f"⚠️ {inc_label}: Jahr {selected_year} fehlt in den Ergebnissen.")
                        continue
                    scoring_results = convert_results_to_scoring_format(results_inc, selected_year)
                    kpis = get_score_and_kpis(scoring_results, storage_cfg, selected_year)
                    category_scores = get_category_scores(kpis)
                    overall_score = sum(category_scores.values()) / len(category_scores)
                    row = {
                        "Szenario": inc_label,
                        "Jahr": selected_year,
                        "Gesamtscore": round(overall_score, 1),
                    }
                    for cat_key, cat_score in category_scores.items():
                        row[KPI_CONFIG[cat_key]["title"]] = round(cat_score, 1)
                    rows.append(row)
                except Exception as exc:
                    st.warning(f"⚠️ Score für {inc_label} nicht berechenbar: {exc}")

            if rows:
                df_scores = pd.DataFrame(rows)
                st.dataframe(df_scores, width='stretch', hide_index=True)
            else:
                st.info("Keine KPI-Scores verfügbar. Prüfe Speicher-Konfigurationen und Simulationsergebnisse.")
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
   
    result["Szenario 1"] = copy.deepcopy(scenario_1)

    # Interpoliere Inkremente 
    for increment in range(1, num_increments + 1):
        t = increment / (num_increments + 1)

        new_scenario = copy.deepcopy(scenario_1)

        new_scenario["metadata"] = copy.deepcopy(scenario_1.get("metadata", {}))
        s1_name = scenario_1.get("metadata", {}).get("name", "Szenario 1")
        s2_name = scenario_2.get("metadata", {}).get("name", "Szenario 2")
        new_scenario["metadata"]["name"] = f"Inkrement {increment} ({s1_name} → {s2_name})"

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

        if "weather_generation_profiles" in scenario_1:
            new_scenario["weather_generation_profiles"] = copy.deepcopy(
                scenario_1.get("weather_generation_profiles", {})
            )

        result[f"Inkrement {increment}"] = new_scenario
    
    result["Szenario 2"] = copy.deepcopy(scenario_2)

    return result


def _display_interpolation_table(scenario_1: dict, scenario_2: dict, interpolated_scenarios: dict) -> None:
    """
    Zeigt eine Tabelle mit den interpolierten Szenario-Parametern
    Markiert Zeilen die sich zwischen Szenario 1 und Szenario 2 geändert haben
    """
    import pandas as pd
    data_rows = []
    
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
                        
                        for inc_label, scenario in sorted(interpolated_scenarios.items()):
                            if inc_label.startswith("Inkrement"):
                                inc_val = scenario.get("target_load_demand_twh", {}).get(sector, {}).get(year_key, 0)
                                row[inc_label] = round(inc_val, 2)
                        
                        row["Szenario 2"] = round(v2, 2)
                        row["_changed"] = v1 != v2
                        data_rows.append(row)
    
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
                        
                        for inc_label, scenario in sorted(interpolated_scenarios.items()):
                            if inc_label.startswith("Inkrement"):
                                inc_val = scenario.get("target_generation_capacities_mw", {}).get(tech, {}).get(year_key, 0)
                                row[inc_label] = round(inc_val, 0)
                        
                        row["Szenario 2"] = round(v2, 0)
                        row["_changed"] = v1 != v2
                        data_rows.append(row)
    
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
                                
                                for inc_label, scenario in sorted(interpolated_scenarios.items()):
                                    if inc_label.startswith("Inkrement"):
                                        inc_val = scenario.get("target_storage_capacities", {}).get(storage_type, {}).get(year_key, {}).get(param, 0)
                                        row[inc_label] = round(inc_val, 2)
                                
                                row["Szenario 2"] = round(v2, 2)
                                row["_changed"] = v1 != v2
                                data_rows.append(row)
    
    if data_rows:
        df_comparison = pd.DataFrame(data_rows)
        
        display_df = df_comparison.drop("_changed", axis=1)
        
        styled_df = display_df.style.apply(
            lambda row: ["background-color: #ffdb3b; color: black"] * len(row) if df_comparison.loc[row.name, "_changed"] else [""] * len(row),
            axis=1
        )
        
        st.dataframe(styled_df, width='stretch', hide_index=True)
    else:
        st.info("Keine vergleichbaren Parameter gefunden")

