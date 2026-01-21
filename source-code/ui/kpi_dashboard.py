import pandas as pd
import streamlit as st

from data_processing.scoring_system import get_score_and_kpis
from plotting.scoring_plots import (
    create_gauge_chart,
    create_category_radar_chart,
    create_kpi_bar_chart,
    create_kpi_table,
    get_category_scores,
    KPI_CONFIG,
)


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

    df_time = pd.to_datetime(df["Zeitpunkt"])
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
        date_from = st.date_input(
            "Von",
            value=default_start.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            format="DD.MM.YYYY",
            key=f"date_from_{key_suffix}",
        )
    with col2:
        date_to = st.date_input(
            "Bis",
            value=default_end.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            format="DD.MM.YYYY",
            key=f"date_to_{key_suffix}",
        )
    with col3:
        hole_year = st.button(
            "Ganzes Jahr anzeigen",
            key=f"full_year_btn_{key_suffix}",
            on_click=lambda: None,
        )

    if hole_year:
        date_from_ts = min_date
        date_to_ts = max_date
    else:
        date_from_ts = pd.Timestamp(date_from)
        date_to_ts = pd.Timestamp(date_to, hour=23, minute=59, second=59)

    return date_from_ts, date_to_ts


def convert_results_to_scoring_format(results: dict, year: int) -> dict:
    """
    Konvertiert Simulationsergebnisse in das Format für das KPI-Scoring-System

    Args:
        results: Volles results Dictionary (indexiert nach Jahr)
        year: Zu extrahierendes Jahr

    Returns:
        Dictionary im Format für scoring_system.py
    """
    if year not in results:
        raise ValueError(f"Jahr {year} nicht in results gefunden")

    year_results = results[year]

    scoring_results = {
        "Verbrauch": year_results["consumption"],
        "Erzeugung": year_results["production"],
        "E-Mobility": year_results["emobility"],
        "Speicher": year_results["storage"],
        "Bilanz_vor_Flex": year_results["balance_pre_flex"],
        "Bilanz_nach_Flex": year_results["balance_post_flex"],
        "Wirtschaftlichkeit": year_results["economics"],
    }

    return scoring_results


def normalize_storage_config(storage_cfg: dict) -> dict:
    """Konvertiert Jahres-Keys in Strings für Scoring-System"""
    if not isinstance(storage_cfg, dict):
        return {}

    normalized = {}
    for stor_key, stor_val in storage_cfg.items():
        if not isinstance(stor_val, dict):
            normalized[stor_key] = stor_val
            continue
        normalized[stor_key] = {}
        for yr_key, cfg in stor_val.items():
            normalized[stor_key][str(yr_key)] = cfg
    return normalized


def render_kpi_overview(kpis: dict):
    """Rendert den KPI-Übersichts-Bereich"""

    st.subheader("📊 KPI Überblick")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Kategorie-Vergleich**")
        radar_fig = create_category_radar_chart(kpis)
        st.plotly_chart(radar_fig, width="stretch")

    with col2:
        st.markdown("**Kategorie-Scores**")
        category_scores = get_category_scores(kpis)

        for category, score in category_scores.items():
            config = KPI_CONFIG[category]

            if score >= 80:
                delta_color = "normal"
            elif score >= 60:
                delta_color = "off"
            else:
                delta_color = "inverse"

            st.metric(
                label=config["title"],
                value=f"{score:.1f} Punkte",
                delta=None,
                delta_color=delta_color,
            )

        overall_score = sum(category_scores.values()) / len(category_scores)
        st.markdown("---")
        st.metric(label="🎯 Gesamtscore", value=f"{overall_score:.1f} Punkte", delta=None)


def render_category_details(category: str, kpis: dict, config: dict):
    """Rendert Detailansicht für eine Kategorie."""
    st.subheader(f"{config['title']} Details")

    num_kpis = len(kpis)
    cols = st.columns(min(num_kpis, 3))

    for idx, (kpi_name, kpi_value) in enumerate(kpis.items()):
        kpi_config = config["kpis"].get(kpi_name, {})
        col_idx = idx % 3

        with cols[col_idx]:
            gauge_fig = create_gauge_chart(
                kpi_value,
                kpi_config.get("name", kpi_name),
                kpi_config.get("worst", 1),
                kpi_config.get("best", 0),
                height=250,
            )
            st.plotly_chart(gauge_fig, width="stretch")

            value_format = kpi_config.get("format", ".2f")
            if value_format == ".2%":
                formatted_value = f"{kpi_value * 100:.2f}%"
            elif value_format == ".4f":
                formatted_value = f"{kpi_value:.4f} {kpi_config.get('unit', '')}"
            else:
                formatted_value = f"{kpi_value:.2f}"

            st.markdown(f"**Wert:** {formatted_value}")
            st.caption(kpi_config.get("description", ""))

    st.markdown("---")
    st.subheader("KPI Werte")
    bar_fig = create_kpi_bar_chart(kpis, config)
    st.plotly_chart(bar_fig, width="stretch")


def render_detailed_table(kpis: dict):
    """Rendert detaillierte KPI-Tabelle."""
    st.subheader("📋 Detaillierte KPI-Tabelle")
    df = create_kpi_table(kpis)

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Category": st.column_config.TextColumn("Kategorie", width="small"),
            "KPI": st.column_config.TextColumn("KPI", width="medium"),
            "Value": st.column_config.TextColumn("Wert", width="small"),
            "Score": st.column_config.NumberColumn("Score", width="small", format="%.1f"),
            "Rating": st.column_config.TextColumn("Bewertung", width="small"),
            "Description": st.column_config.TextColumn("Beschreibung", width="large"),
        },
    )

    if st.session_state.get("debug_mode"):
        with st.expander("🔧 Raw Data (Debug)", expanded=False):
            st.subheader("Rohwerte nach Kategorie")

            if "raw_values" in kpis:
                security_vals = {
                    k: v
                    for k, v in kpis["raw_values"].items()
                    if any(x in k.lower() for x in ["unserved", "deficit", "load", "h2", "security", "autarkie"])
                }
                ecology_vals = {
                    k: v
                    for k, v in kpis["raw_values"].items()
                    if any(x in k.lower() for x in ["co2", "renewable", "fossil", "curtailment", "ecology", "generation", "total_generation"])
                }
                economy_vals = {
                    k: v
                    for k, v in kpis["raw_values"].items()
                    if any(x in k.lower() for x in ["import", "storage", "lcoe", "hours", "economy", "cost"])
                }

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Security Values**")
                    st.json(security_vals)

                with col2:
                    st.markdown("**Ecology Values**")
                    st.json(ecology_vals)

                with col3:
                    st.markdown("**Economy Values**")
                    st.json(economy_vals)
            else:
                st.info("Keine Raw Values verfügbar")


def render_kpi_dashboard(results: dict, storage_config: dict, year: int, key_suffix: str = ""):
    """
    Rendert das vollständige KPI-Dashboard.

    Args:
        results: Simulationsergebnis Dictionary (indexiert nach Jahr)
        storage_config: Speicherkonfiguration aus Szenario
        year: Zu analysierendes Jahr
    """
    st.markdown("### ⚡ KPI-Dashboard")

    available_years = sorted([int(y) for y in results.keys()])

    if len(available_years) > 1:
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_year = st.selectbox(
                "📅 Jahr auswählen",
                options=available_years,
                index=available_years.index(year) if year in available_years else 0,
                key=f"kpi_year_selector_{key_suffix}",
                help="Wählen Sie ein Jahr für die KPI-Analyse",
            )
        with col2:
            st.caption(f"**Analyse für Jahr:** {selected_year}")
    else:
        selected_year = year
        st.caption(f"Analyse für Jahr: {selected_year}")

    st.warning(
        ":material/warning: Das Jahr muss hier für den Score ausgewählt werden. Die Auswahl für die Plots oben gilt hier nicht."
    )

    st.markdown("---")

    try:
        scoring_results = convert_results_to_scoring_format(results, selected_year)
    except ValueError as e:
        st.error(f"❌ Fehler: {str(e)}")
        st.info(f"Verfügbare Jahre: {available_years}")
        return

    with st.spinner(f"Berechne KPIs für {selected_year}..."):
        kpis = get_score_and_kpis(scoring_results, storage_config, selected_year)

    render_kpi_overview(kpis)

    st.markdown("---")

    tabs = st.tabs([config["title"] for config in KPI_CONFIG.values()])

    for idx, (category, config) in enumerate(KPI_CONFIG.items()):
        with tabs[idx]:
            if category not in kpis:
                st.warning(f"Keine Daten für {config['title']} verfügbar")
                continue

            render_category_details(category, kpis[category], config)

    st.markdown("---")

    with st.expander("📋 Detaillierte Tabelle"):
        render_detailed_table(kpis)
