import streamlit as st
import pandas as pd

from data_processing.simulation_engine import SimulationEngine
from ui.kpi_dashboard import convert_results_to_scoring_format, normalize_storage_config
from data_processing.scoring_system import get_score_and_kpis
from plotting.scoring_plots import get_category_scores, KPI_CONFIG, create_kpi_comparison_chart

# Manager Imports
from data_manager import DataManager
from config_manager import ConfigManager
from scenario_manager import ScenarioManager


def comparison_simulation_page() -> None:
    """
    Szenario Vergleich Page: Mehrere Szenarien laden und vergleichen.
    """
    st.title("Simulation (Szenario Vergleich)")
    st.caption("Laden Sie 2–5 Szenarien und vergleichen Sie deren KPI-Scores.")

    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")
        return

    st.markdown("---")
    st.markdown("## Szenarios laden")

    # Anzahl wählen
    num_scenarios = st.slider(
        "Anzahl der Szenarien zum Vergleich (2-5)",
        min_value=2,
        max_value=5,
        value=2,
        key="comparison_num_scenarios"
    )

    # File Uploader
    scenario_data = {}
    for i in range(1, num_scenarios + 1):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded = st.file_uploader(
                f"Szenario {i}",
                type=["yaml"],
                key=f"comp_file_upload_{i}"
            )
        
        with col2:
            if st.button(f"Laden", key=f"comp_load_btn_{i}", width='stretch'):
                if uploaded:
                    try:
                        scenario = st.session_state.sm.load_scenario(uploaded)
                        st.session_state[f"comp_scenario_{i}"] = scenario
                        st.success(f"✅ Szenario {i} geladen")
                    except Exception as e:
                        st.error(f"❌ Fehler beim Laden: {e}")
                else:
                    st.warning(f"⚠️ Bitte wähle eine Datei aus")

        if f"comp_scenario_{i}" in st.session_state:
            scenario = st.session_state[f"comp_scenario_{i}"]
            meta = scenario.get("metadata", {})
            st.info(f"✓ {meta.get('name', f'Szenario {i}')}")

    # check IF Szenarien
    all_loaded = all(f"comp_scenario_{i}" in st.session_state for i in range(1, num_scenarios + 1))

    if all_loaded:
        st.markdown("---")
        
        if st.button("Alle Szenarien simulieren", type="primary", key="run_comparison_sim"):
            try:
                # Simuliere
                st.session_state.comparison_results = {}
                progress_bar = st.progress(0)

                for idx in range(1, num_scenarios + 1):
                    scenario = st.session_state[f"comp_scenario_{idx}"]
                    scenario_name = scenario.get("metadata", {}).get("name", f"Szenario {idx}")

                    st.session_state.sm.current_scenario = scenario

                    engine = SimulationEngine(
                        st.session_state.cfg,
                        st.session_state.dm,
                        st.session_state.sm
                    )
                    results = engine.run_scenario()
                    st.session_state.comparison_results[scenario_name] = {
                        "results": results,
                        "scenario": scenario
                    }

                    progress = idx / num_scenarios
                    progress_bar.progress(progress)

                st.success(f"✅ {num_scenarios} Szenarien simuliert!")

            except Exception as e:
                st.error(f"❌ Fehler: {e}")

        # Vergleichstabelle
        if "comparison_results" in st.session_state and st.session_state.comparison_results:
            st.markdown("---")
            st.subheader("📊 KPI Score Vergleich")

            results_dict = st.session_state.comparison_results
            
            # gemeinsame Jahre
            common_years = None
            for scenario_name, data in results_dict.items():
                year_keys = data["results"].keys()
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
                key="comparison_kpi_year_select",
            )

            rows = []
            all_kpis_list = []
            scenario_labels = []
            
            for scenario_name in sorted(results_dict.keys()):
                data = results_dict[scenario_name]
                results_inc = data["results"]
                scenario = data["scenario"]

                storage_cfg_raw = scenario.get("target_storage_capacities", {})
                storage_cfg = normalize_storage_config(storage_cfg_raw)
                
                if not storage_cfg:
                    st.warning(f"⚠️ {scenario_name}: Keine Speicher-Konfiguration gefunden. KPI-Score eventuell unvollständig.")
                    continue

                try:
                    if selected_year not in results_inc:
                        st.warning(f"⚠️ {scenario_name}: Jahr {selected_year} fehlt in den Ergebnissen.")
                        continue
                    
                    scoring_results = convert_results_to_scoring_format(results_inc, selected_year)
                    kpis = get_score_and_kpis(scoring_results, storage_cfg, selected_year)
                    category_scores = get_category_scores(kpis)
                    overall_score = sum(category_scores.values()) / len(category_scores)
                    
                    row = {
                        "Szenario": scenario_name,
                        "Jahr": selected_year,
                        "Gesamtscore": round(overall_score, 1),
                    }
                    for cat_key, cat_score in category_scores.items():
                        row[KPI_CONFIG[cat_key]["title"]] = round(cat_score, 1)
                    rows.append(row)
                    
                    # Für Vergleichscharts sammeln
                    all_kpis_list.append(kpis)
                    scenario_labels.append(scenario_name)
                except Exception as exc:
                    st.warning(f"⚠️ Score für {scenario_name} nicht berechenbar: {exc}")

            if rows:
                df_scores = pd.DataFrame(rows)
                st.dataframe(df_scores, width='stretch', hide_index=True)
                
                # Vergleichscharts für alle 3 Kategorien
                if all_kpis_list:
                    st.markdown("---")
                    st.subheader("📊 KPI Detail Vergleich")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("#### 🛡️ Security")
                        try:
                            fig_security = create_kpi_comparison_chart(
                                all_kpis_list, 
                                scenario_labels, 
                                category='security',
                                height=450,
                                show_title=False
                            )
                            st.plotly_chart(fig_security, width='stretch')
                        except Exception as e:
                            st.warning(f"⚠️ Security Chart: {e}")
                                            
                    
                    with col2:
                        st.markdown("#### 🌱 Ecology")
                        try:
                            fig_ecology = create_kpi_comparison_chart(
                                all_kpis_list, 
                                scenario_labels, 
                                category='ecology',
                                height=450,
                                show_title=False
                            )
                            st.plotly_chart(fig_ecology, width='stretch')
                        except Exception as e:
                            st.warning(f"⚠️ Ecology Chart: {e}")
                    
                    with col3:
                                                
                        try:
                            st.markdown("#### 💰 Economy")
                            fig_economy = create_kpi_comparison_chart(
                                all_kpis_list, 
                                scenario_labels, 
                                category='economy',
                                height=450,
                                show_title=False
                            )
                            st.plotly_chart(fig_economy, width='stretch')
                        except Exception as e:
                            st.warning(f"⚠️ Economy Chart: {e}")
            else:
                st.info("Keine KPI-Scores verfügbar. Prüfe Speicher-Konfigurationen und Simulationsergebnisse.")
    else:
        st.info(f"⚠️ Bitte lade alle {num_scenarios} Szenarien hoch, um zu beginnen.")
