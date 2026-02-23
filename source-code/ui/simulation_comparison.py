import io

import pandas as pd
import streamlit as st

from config_manager import ConfigManager
from data_manager import DataManager
from data_processing.scoring_system import get_score_and_kpis
from data_processing.simulation_engine import SimulationEngine
from plotting.scoring_plots import KPI_CONFIG, create_kpi_comparison_chart, get_category_scores
from scenario_manager import ScenarioManager
from ui.kpi_dashboard import (
    convert_results_to_scoring_format,
    normalize_storage_config,
    render_kpi_dashboard,
)


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _get_non_base_years(scenario: dict, results: dict) -> list[int]:
    """Nicht-Basisjahre aus valid_for_years ermitteln."""
    valid_years = scenario.get("metadata", {}).get("valid_for_years", [])
    if valid_years:
        sorted_valid = sorted(int(y) for y in valid_years)
        base_year = sorted_valid[0]
    else:
        sorted_valid = sorted(int(y) for y in results.keys())
        base_year = sorted_valid[0] if sorted_valid else 2025

    return [y for y in sorted_valid if y != base_year and y in results]


def _compute_row(
    scenario_name: str,
    year: int,
    results: dict,
    storage_cfg: dict,
) -> dict | None:
    """KPI-Zeile für (Szenario, Jahr) berechnen. None bei Fehler."""
    try:
        scoring_results = convert_results_to_scoring_format(results, year)
        kpis = get_score_and_kpis(scoring_results, storage_cfg, year)
    except Exception:
        return None

    safety = kpis.get("safety", {})
    ecology = kpis.get("ecology", {})
    economy = kpis.get("economy", {})
    cat_scores = get_category_scores(kpis)

    overall_score = (
        0.40 * cat_scores.get("safety", 0)
        + 0.30 * cat_scores.get("ecology", 0)
        + 0.30 * cat_scores.get("economy", 0)
    )

    # Gesamtkosten aus Economics-Dict
    econ = results.get(year, {}).get("economics", {})
    total_expense_bn = econ.get("total_annual_cost_bn") if isinstance(econ, dict) else None

    return {
        "Szenario": scenario_name,
        "Jahr": year,
        "Autarker Stundenanteil": round(safety.get("adequacy_score", 0.0) * 100, 2),
        "Robustness Score": round(safety.get("robustness_score", 0.0) * 100, 2),
        "Dependency Score": round(safety.get("dependency_score", 0.0) * 100, 2),
        "CO2 Score": round(ecology.get("co2_score", 0.0) * 100, 2),
        "Renewable Score": round(ecology.get("renewable_share", 0.0) * 100, 2),
        "Curtailment Score": round(ecology.get("curtailment_score", 0.0) * 100, 2),
        "LCOE Index": round(economy.get("lcoe_index", 0.0) * 100, 2),
        "Curtailment Econ Score": round(economy.get("curtailment_econ_score", 0.0) * 100, 2),
        "Storage Efficiency": round(economy.get("storage_efficiency", 0.0) * 100, 2),
        "Economy Score": round(cat_scores.get("economy", 0.0), 2),
        "Safety Score": round(cat_scores.get("safety", 0.0), 2),
        "Ecology Score": round(cat_scores.get("ecology", 0.0), 2),
        "Total Score": round(overall_score, 2),
        "Total Expense [Mrd. €/a]": round(total_expense_bn, 4) if total_expense_bn is not None else None,
    }


# ── Hauptseite ───────────────────────────────────────────────────────────────

def comparison_simulation_page() -> None:
    """Szenario-Vergleichsseite."""
    st.title("Simulation (Szenario Vergleich)")
    st.caption("Laden Sie 2–10 Szenarien und vergleichen Sie deren KPI-Scores.")

    if st.session_state.dm is None or st.session_state.cfg is None or st.session_state.sm is None:
        st.warning("DataManager/ConfigManager/ScenarioManager ist nicht initialisiert.")
        return

    st.markdown("---")
    st.markdown("## Szenarien laden")

    num_scenarios = st.slider(
        "Anzahl der Szenarien zum Vergleich (2–10)",
        min_value=2,
        max_value=10,
        value=2,
        key="comparison_num_scenarios",
    )

    for i in range(1, num_scenarios + 1):
        col1, col2 = st.columns([3, 1])
        with col1:
            uploaded = st.file_uploader(
                f"Szenario {i}",
                type=["yaml"],
                key=f"comp_file_upload_{i}",
            )
        with col2:
            if st.button("Laden", key=f"comp_load_btn_{i}", width="stretch"):
                if uploaded:
                    try:
                        scenario = st.session_state.sm.load_scenario(uploaded)
                        st.session_state[f"comp_scenario_{i}"] = scenario
                        st.success(f"✅ Szenario {i} geladen")
                    except Exception as e:
                        st.error(f"❌ Fehler beim Laden: {e}")
                else:
                    st.warning("⚠️ Bitte wähle eine Datei aus")

        if f"comp_scenario_{i}" in st.session_state:
            meta = st.session_state[f"comp_scenario_{i}"].get("metadata", {})
            st.info(f"✓ {meta.get('name', f'Szenario {i}')}")

    all_loaded = all(f"comp_scenario_{i}" in st.session_state for i in range(1, num_scenarios + 1))

    if not all_loaded:
        st.info(f"⚠️ Bitte lade alle {num_scenarios} Szenarien hoch, um zu beginnen.")
        return

    st.markdown("---")

    if st.button("Alle Szenarien simulieren", type="primary", key="run_comparison_sim"):
        st.session_state.comparison_results = {}
        progress_bar = st.progress(0)
        try:
            for idx in range(1, num_scenarios + 1):
                scenario = st.session_state[f"comp_scenario_{idx}"]
                scenario_name = scenario.get("metadata", {}).get("name", f"Szenario {idx}")
                st.session_state.sm.current_scenario = scenario
                engine = SimulationEngine(
                    st.session_state.cfg,
                    st.session_state.dm,
                    st.session_state.sm,
                )
                results = engine.run_scenario()
                st.session_state.comparison_results[scenario_name] = {
                    "results": results,
                    "scenario": scenario,
                }
                progress_bar.progress(idx / num_scenarios)
            st.success(f"✅ {num_scenarios} Szenarien simuliert!")
        except Exception as e:
            st.error(f"❌ Fehler: {e}")

    if "comparison_results" not in st.session_state or not st.session_state.comparison_results:
        return

    results_dict = st.session_state.comparison_results

    # ── Excel-Export ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📥 Excel-Export")

    excel_rows: list[dict] = []
    for scenario_name, data in results_dict.items():
        res = data["results"]
        scenario = data["scenario"]
        storage_cfg = normalize_storage_config(scenario.get("target_storage_capacities", {}))
        non_base_years = _get_non_base_years(scenario, res)

        if not non_base_years:
            # Fallback: alle Jahre außer erstem
            all_yrs = sorted(int(y) for y in res.keys())
            non_base_years = all_yrs[1:] if len(all_yrs) > 1 else all_yrs

        for yr in non_base_years:
            row = _compute_row(scenario_name, yr, res, storage_cfg)
            if row:
                excel_rows.append(row)
            else:
                excel_rows.append({"Szenario": scenario_name, "Jahr": yr, "Fehler": "Berechnung fehlgeschlagen"})

    if excel_rows:
        df_export = pd.DataFrame(excel_rows)
        st.dataframe(df_export, width='stretch', hide_index=True)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_export.to_excel(writer, sheet_name="Szenario Vergleich", index=False)
        buf.seek(0)
        st.download_button(
            label="📥 Excel herunterladen",
            data=buf,
            file_name="szenario_vergleich.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_comparison_excel",
        )

    # ── KPI-Vergleichstabelle ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 KPI Score Vergleich")

    common_years = None
    for data in results_dict.values():
        year_set = {int(y) for y in data["results"].keys()}
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

    rows: list[dict] = []
    all_kpis_list: list[dict] = []
    scenario_labels: list[str] = []

    for scenario_name in sorted(results_dict.keys()):
        data = results_dict[scenario_name]
        res = data["results"]
        scenario = data["scenario"]
        storage_cfg = normalize_storage_config(scenario.get("target_storage_capacities", {}))

        if not storage_cfg:
            st.warning(f"⚠️ {scenario_name}: Keine Speicher-Konfiguration gefunden.")
            continue
        if selected_year not in res:
            st.warning(f"⚠️ {scenario_name}: Jahr {selected_year} fehlt in den Ergebnissen.")
            continue

        try:
            scoring_results = convert_results_to_scoring_format(res, selected_year)
            kpis = get_score_and_kpis(scoring_results, storage_cfg, selected_year)
            category_scores = get_category_scores(kpis)
            overall_score = (
                0.40 * category_scores.get("safety", 0)
                + 0.30 * category_scores.get("ecology", 0)
                + 0.30 * category_scores.get("economy", 0)
            )
            row = {
                "Szenario": scenario_name,
                "Jahr": selected_year,
                "Gesamtscore": round(overall_score, 1),
            }
            for cat_key, cat_score in category_scores.items():
                row[KPI_CONFIG[cat_key]["title"]] = round(cat_score, 1)
            rows.append(row)
            all_kpis_list.append(kpis)
            scenario_labels.append(scenario_name)
        except Exception as exc:
            st.warning(f"⚠️ Score für {scenario_name} nicht berechenbar: {exc}")

    if rows:
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

        if all_kpis_list:
            st.markdown("---")
            st.subheader("📊 KPI Detail Vergleich")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("#### 🛡️ Safety")
                try:
                    st.plotly_chart(
                        create_kpi_comparison_chart(all_kpis_list, scenario_labels, category="safety", height=450, show_title=False),
                        width='stretch',
                    )
                except Exception as e:
                    st.warning(f"⚠️ Safety Chart: {e}")
            with col2:
                st.markdown("#### 🌱 Ecology")
                try:
                    st.plotly_chart(
                        create_kpi_comparison_chart(all_kpis_list, scenario_labels, category="ecology", height=450, show_title=False),
                        width='stretch',
                    )
                except Exception as e:
                    st.warning(f"⚠️ Ecology Chart: {e}")
            with col3:
                st.markdown("#### 💰 Economy")
                try:
                    st.plotly_chart(
                        create_kpi_comparison_chart(all_kpis_list, scenario_labels, category="economy", height=450, show_title=False),
                        width='stretch',
                    )
                except Exception as e:
                    st.warning(f"⚠️ Economy Chart: {e}")
    else:
        st.info("Keine KPI-Scores verfügbar. Prüfe Speicher-Konfigurationen und Simulationsergebnisse.")

    # ── KPI-Dashboard je Szenario ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 KPI Dashboard je Szenario")

    for scenario_name in sorted(results_dict.keys()):
        data = results_dict[scenario_name]
        res = data["results"]
        scenario = data["scenario"]
        storage_cfg_raw = scenario.get("target_storage_capacities", {})
        storage_cfg = normalize_storage_config(storage_cfg_raw)

        with st.expander(f"📊 {scenario_name}", expanded=False):
            if not storage_cfg:
                st.warning("Keine Speicher-Konfiguration gefunden – Dashboard eingeschränkt.")
            available_years = sorted(int(y) for y in res.keys())
            default_year = available_years[-1] if available_years else selected_year
            render_kpi_dashboard(
                results=res,
                storage_config=storage_cfg,
                year=default_year,
                key_suffix=scenario_name.replace(" ", "_"),
            )
