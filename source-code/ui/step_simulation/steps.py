import math
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import data_processing.simulation as sim
import data_processing.gen as gen
import data_processing.col as col
import plotting.plotting_formated_st as pltf
import plotting.plotting_plotly_st as pltp
from constants import ENERGY_SOURCES

ZUGELASSENE_DATEIEN_VERBRAUCH = [
    "SMARD_2015-2020_Verbrauch",
    "SMARD_2020-2025_Verbrauch",
]

ZUGELASSENE_DATEIEN_ERZEUGUNG = [
    "SMARD_2015-2020_Erzeugung",
    "SMARD_2020-2025_Erzeugung",
]

STUDIE_OPTIONEN = [
    "Agora",
    "BDI - Klimapfade 2.0",
    "dena - KN100",
    "BMWK - LFS TN-Strom",
    "Ariadne - REMIND-Mix",
    "Ariadne - REMod-Mix",
    "Ariadne - TIMES PanEU-Mix",
]


def ensure_step_state() -> None:
    """Initialisiert benötigte Session-State Variablen für die Step-Simulation."""
    defaults = {
        "step_index": 0,
        "step_valid": True,
        "sim_datei_verbrauch": None,
        "sim_datei_erzeugung": None,
        "sim_studie_verbrauch": None,
        "sim_studie_erzeugung": None,
        "sim_jahr": 2030,
        "sim_referenz_jahr": 2023,
        "sim_verbrauch_lastprofile": False,
        "df_simulation_con": None,
        "df_simulation_prod": None,
        "energie_bilanz": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_step(step_index: int) -> None:
    st.session_state.step_index = step_index


def reset_step_simulation() -> None:
    """Setzt die Step-Simulation zurück."""
    keys_to_reset = [
        "step_index",
        "step_valid",
        "sim_datei_verbrauch",
        "sim_datei_erzeugung",
        "sim_studie_verbrauch",
        "sim_studie_erzeugung",
        "sim_jahr",
        "sim_referenz_jahr",
        "sim_verbrauch_lastprofile",
        "df_simulation_con",
        "df_simulation_prod",
        "energie_bilanz",
        "storage_results",
        "remaining_surplus_twh",
        "remaining_deficit_twh",
        "bat_args_mode",
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]


def daten_auswaehlen() -> None:
    st.header("1. Daten auswählen:")

    is_loaded = st.session_state.dm is not None and st.session_state.cfg is not None

    if is_loaded:
        st.write("Wähle die Daten für die Simulation aus.")
        st.session_state.step_valid = True

        dataset_names = st.session_state.dm.list_dataset_names()
        verbrauch_index = 2
        if st.session_state.sim_datei_verbrauch in dataset_names:
            verbrauch_index = dataset_names.index(st.session_state.sim_datei_verbrauch)

        st.session_state.sim_datei_verbrauch = st.selectbox(
            "Verbrauchdatei auswählen",
            options=dataset_names,
            index=verbrauch_index,
            key="selectbox_verbrauch",
        )
        if st.session_state.sim_datei_verbrauch not in ZUGELASSENE_DATEIEN_VERBRAUCH:
            st.warning("⚠️ Diese Datei ist keine Verbrauchsdatei aus SMARD.")
            st.session_state.step_valid = False

        erzeugung_index = 1
        if st.session_state.sim_datei_erzeugung in dataset_names:
            erzeugung_index = dataset_names.index(st.session_state.sim_datei_erzeugung)

        st.session_state.sim_datei_erzeugung = st.selectbox(
            "Erzeugungsdatei auswählen",
            options=dataset_names,
            index=erzeugung_index,
            key="selectbox_erzeugung",
        )
        if st.session_state.sim_datei_erzeugung not in ZUGELASSENE_DATEIEN_ERZEUGUNG:
            st.warning("⚠️ Diese Datei ist keine Erzeugungsdatei aus SMARD.")
            st.session_state.step_valid = False

        if st.session_state.step_valid:
            try:
                df_verbrauch = st.session_state.dm.get(st.session_state.sim_datei_verbrauch)
                df_erzeugung = st.session_state.dm.get(st.session_state.sim_datei_erzeugung)

                jahre_verbrauch = set(pd.to_datetime(df_verbrauch["Zeitpunkt"]).dt.year.unique())
                jahre_erzeugung = set(pd.to_datetime(df_erzeugung["Zeitpunkt"]).dt.year.unique())
                verfuegbare_jahre = sorted(jahre_verbrauch & jahre_erzeugung)

                if verfuegbare_jahre:
                    ref_index = len(verfuegbare_jahre) - 1
                    if st.session_state.sim_referenz_jahr in verfuegbare_jahre:
                        ref_index = verfuegbare_jahre.index(st.session_state.sim_referenz_jahr)

                    st.session_state.sim_referenz_jahr = st.selectbox(
                        "Referenzjahr auswählen",
                        options=verfuegbare_jahre,
                        index=ref_index,
                        key="selectbox_referenzjahr",
                    )
                    st.info(f"ℹ️ Verfügbare Jahre: {min(verfuegbare_jahre)} - {max(verfuegbare_jahre)}")
                else:
                    st.error("❌ Keine übereinstimmenden Jahre in beiden Datensätzen gefunden.")
                    st.session_state.step_valid = False

            except Exception as exc:
                st.error(f"❌ Fehler beim Ermitteln verfügbarer Jahre: {exc}")
                st.session_state.step_valid = False

        simjahre = list(range(2026, 2051))
        sim_index = simjahre.index(st.session_state.sim_jahr) if st.session_state.sim_jahr in simjahre else 4

        st.session_state.sim_jahr = st.selectbox(
            "Simulationsjahr",
            options=simjahre,
            index=sim_index,
            key="selectbox_simjahr",
        )

        if st.session_state.step_valid:
            st.success("✅ Alle Eingaben sind korrekt")

    else:
        st.warning(
            "DataManager/ConfigManager ist nicht initialisiert. Bitte lade die Daten und Konfiguration zuerst im Hauptmenü."
        )
        st.session_state.step_valid = False


def verbrauch_simulieren() -> None:
    st.header("2. Verbrauch Simulieren:")

    studie_index = 0
    if st.session_state.sim_studie_verbrauch in STUDIE_OPTIONEN:
        studie_index = STUDIE_OPTIONEN.index(st.session_state.sim_studie_verbrauch)

    st.session_state.sim_studie_verbrauch = st.selectbox(
        "Studie der Verbrauchsprognose auswählen",
        options=STUDIE_OPTIONEN,
        index=studie_index,
        key="selectbox_studie_verbrauch",
    )
    st.session_state.sim_verbrauch_lastprofile = st.checkbox(
        "Verwende Verbrauchs-Lastprofile für Skalierung :orange[[EXPERIMENTELL]]",
        value=st.session_state.sim_verbrauch_lastprofile,
        key="checkbox_lastprofile",
    )

    if st.button("Simulation starten", type="primary", use_container_width=True):
        if st.session_state.sim_datei_verbrauch:
            with st.spinner("Simulation läuft..."):
                try:
                    st.session_state.df_simulation_con = sim.calc_scaled_consumption(
                        st.session_state.dm.get(
                            st.session_state.dm.get_dataset_id(st.session_state.sim_datei_verbrauch)
                        ),
                        st.session_state.dm.get("Erzeugungs/Verbrauchs Prognose Daten"),
                        st.session_state.sim_studie_verbrauch,
                        st.session_state.sim_jahr,
                        st.session_state.sim_jahr,
                        st.session_state.sim_referenz_jahr,
                        use_load_profile=st.session_state.sim_verbrauch_lastprofile,
                    )
                    st.success("✅ Verbrauchssimulation abgeschlossen")
                    st.session_state.step_valid = True
                except Exception as exc:
                    st.error(f"❌ Fehler bei der Simulation: {exc}")
                    st.session_state.step_valid = False
        else:
            st.error("❌ Keine Verbrauchsdatei ausgewählt. Gehe zurück zu Schritt 1.")
            st.session_state.step_valid = False

    if st.session_state.df_simulation_con is not None and len(st.session_state.df_simulation_con) > 0:
        st.markdown("---")
        st.subheader(":chart_with_upwards_trend: Simulationsergebnis")

        try:
            df_full = st.session_state.df_simulation_con.copy()
            winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
            winter_end = winter_start + pd.Timedelta(days=7)
            summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
            summer_end = summer_start + pd.Timedelta(days=7)

            df_winter = df_full[
                (pd.to_datetime(df_full["Zeitpunkt"]) >= winter_start)
                & (pd.to_datetime(df_full["Zeitpunkt"]) < winter_end)
            ]
            df_summer = df_full[
                (pd.to_datetime(df_full["Zeitpunkt"]) >= summer_start)
                & (pd.to_datetime(df_full["Zeitpunkt"]) < summer_end)
            ]

            df_zwei_wochen = pd.concat([df_winter, df_summer], ignore_index=True)
            df_plot = df_zwei_wochen if len(df_zwei_wochen) > 0 else df_full
        except Exception as exc:
            st.warning(f"⚠️ Fehler beim Filtern der Wochen: {exc}. Zeige alle Daten.")
            df_plot = st.session_state.df_simulation_con

        try:
            view_mode = st.segmented_control(
                label="Ansicht wählen:",
                options=["📅 Zwei Wochen (Winter & Sommer)", "📊 Gesamtes Jahr"],
                key="verbrauch_view_mode",
                default="📅 Zwei Wochen (Winter & Sommer)",
            )

            if view_mode == "📅 Zwei Wochen (Winter & Sommer)":
                df_winter_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 2]
                df_summer_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 7]

                col_winter, col_summer = st.columns(2, width="stretch", border=True, gap="small")

                with col_winter:
                    st.markdown("#### ❄️ Winterwoche (13.-19. Feb)")
                    if len(df_winter_plot) > 0:
                        fig_winter = pltp.create_line_plot(
                            df_winter_plot,
                            y_axis="Skalierte Netzlast [MWh]",
                            title="",
                            description="",
                            darkmode=False,
                        )
                        st.plotly_chart(fig_winter, use_container_width=True)
                    else:
                        st.warning("⚠️ Keine Winterdaten")

                with col_summer:
                    st.markdown("#### ☀️ Sommerwoche (3.-9. Juli)")
                    if len(df_summer_plot) > 0:
                        fig_summer = pltp.create_line_plot(
                            df_summer_plot,
                            y_axis="Skalierte Netzlast [MWh]",
                            title="",
                            description="",
                            darkmode=False,
                        )
                        st.plotly_chart(fig_summer, use_container_width=True)
                    else:
                        st.warning("⚠️ Keine Sommerdaten")

                df_stats = df_plot

            else:
                df_full_year = st.session_state.df_simulation_con
                col1 = st.columns(1, width="stretch", border=True)
                with col1[0]:
                    st.markdown("### :calendar: Verbrauch über das gesamte Jahr")
                    fig_year = pltp.create_line_plot(
                        df_full_year,
                        y_axis="Skalierte Netzlast [MWh]",
                        title="",
                        description="",
                        darkmode=False,
                    )
                    st.plotly_chart(fig_year, use_container_width=True, width="stretch")
                df_stats = df_full_year

            col1, col2, col3 = st.columns(3, border=True, gap="small")
            with col1:
                total_consumption = df_stats["Skalierte Netzlast [MWh]"].sum() / 1_000_000
                st.metric("Gesamtverbrauch", f"{total_consumption:.2f} TWh")
            with col2:
                avg_consumption = df_stats["Skalierte Netzlast [MWh]"].mean()
                st.metric("Durchschn. Verbrauch", f"{avg_consumption:.2f} MWh")
            with col3:
                max_consumption = df_stats["Skalierte Netzlast [MWh]"].max()
                st.metric("Spitzenlast", f"{max_consumption:.2f} MWh")

            st.session_state.step_valid = True
        except Exception as exc:
            st.error(f"❌ Fehler bei der Visualisierung: {exc}")
            st.session_state.step_valid = False
    else:
        st.session_state.step_valid = False


def erzeugung_simulieren() -> None:
    st.header("3. Erzeugung Simulieren:")

    studie_index = 0
    if st.session_state.sim_studie_erzeugung in STUDIE_OPTIONEN:
        studie_index = STUDIE_OPTIONEN.index(st.session_state.sim_studie_erzeugung)

    st.session_state.sim_studie_erzeugung = st.selectbox(
        "Studie der Erzeugungsprognose auswählen",
        options=STUDIE_OPTIONEN,
        index=studie_index,
        key="selectbox_studie_erzeugung",
    )

    if st.button("🚀 Erzeugung simulieren", type="primary", use_container_width=True):
        if st.session_state.sim_datei_erzeugung:
            with st.spinner("Erzeugungssimulation läuft..."):
                try:
                    st.session_state.df_simulation_prod = sim.calc_scaled_production(
                        st.session_state.dm.get(
                            st.session_state.dm.get_dataset_id(st.session_state.sim_datei_erzeugung)
                        ),
                        st.session_state.dm.get("Erzeugungs/Verbrauchs Prognose Daten"),
                        st.session_state.sim_studie_erzeugung,
                        st.session_state.sim_jahr,
                        ref_jahr=st.session_state.sim_referenz_jahr,
                    )
                    st.success("✅ Erzeugungssimulation abgeschlossen")
                    st.session_state.step_valid = True
                except Exception as exc:
                    st.error(f"❌ Fehler bei der Erzeugungssimulation: {exc}")
                    st.session_state.step_valid = False
        else:
            st.error("❌ Keine Erzeugungsdatei ausgewählt. Gehe zurück zu Schritt 1.")
            st.session_state.step_valid = False

    if st.session_state.df_simulation_prod is not None and len(st.session_state.df_simulation_prod) > 0:
        st.markdown("---")
        st.subheader(":chart_with_upwards_trend: Erzeugungssimulation Ergebnis")

        try:
            df_full = st.session_state.df_simulation_prod.copy()
            winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
            winter_end = winter_start + pd.Timedelta(days=7)
            summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
            summer_end = summer_start + pd.Timedelta(days=7)

            df_winter = df_full[
                (pd.to_datetime(df_full["Zeitpunkt"]) >= winter_start)
                & (pd.to_datetime(df_full["Zeitpunkt"]) < winter_end)
            ]
            df_summer = df_full[
                (pd.to_datetime(df_full["Zeitpunkt"]) >= summer_start)
                & (pd.to_datetime(df_full["Zeitpunkt"]) < summer_end)
            ]

            df_zwei_wochen = pd.concat([df_winter, df_summer], ignore_index=True)
            df_plot = df_zwei_wochen if len(df_zwei_wochen) > 0 else df_full
        except Exception as exc:
            st.warning(f"⚠️ Fehler beim Filtern der Wochen: {exc}. Zeige alle Daten.")
            df_plot = st.session_state.df_simulation_prod

        try:
            available_energy_keys = []
            for key, source in ENERGY_SOURCES.items():
                if source["colname"] in df_plot.columns:
                    available_energy_keys.append(key)

            if available_energy_keys:
                df_winter_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 2]
                df_summer_plot = df_plot[pd.to_datetime(df_plot["Zeitpunkt"]).dt.month == 7]

                col_winter, col_summer = st.columns(2, border=True, gap="small")

                with col_winter:
                    st.markdown("#### ❄️ Winterwoche (13.-19. Feb)")
                    if len(df_winter_plot) > 0:
                        fig_winter = pltp.create_stacked_bar_plot(
                            df_winter_plot,
                            energy_keys=available_energy_keys,
                            title="",
                            description="",
                            darkmode=False,
                        )
                        st.plotly_chart(fig_winter, use_container_width=True)
                    else:
                        st.warning("⚠️ Keine Winterdaten")

                with col_summer:
                    st.markdown("#### ☀️ Sommerwoche (3.-9. Juli)")
                    if len(df_summer_plot) > 0:
                        fig_summer = pltp.create_stacked_bar_plot(
                            df_summer_plot,
                            energy_keys=available_energy_keys,
                            title="",
                            description="",
                            darkmode=False,
                        )
                        st.plotly_chart(fig_summer, use_container_width=True)
                    else:
                        st.warning("⚠️ Keine Sommerdaten")

                st.markdown("### 📈 Statistiken")

                total_production = 0
                renewable_production = 0

                for key in available_energy_keys:
                    colname = ENERGY_SOURCES[key]["colname"]
                    if colname in df_plot.columns:
                        production = df_plot[colname].sum()
                        total_production += production
                        if key in ["BIO", "WAS", "WOF", "WON", "PV", "SOE"]:
                            renewable_production += production

                col_metrics, col_pie = st.columns([1, 1], border=True, gap="small")

                with col_metrics:
                    st.metric("Gesamterzeugung", f"{total_production / 1_000_000:.2f} TWh")
                    st.metric("Durchschn. Erzeugung", f"{total_production / len(df_plot):.2f} MWh")
                    row_sums = df_plot[[ENERGY_SOURCES[k]["colname"] for k in available_energy_keys]].sum(axis=1)
                    st.metric("Spitzenerzeugung", f"{row_sums.max():.2f} MWh")

                with col_pie:
                    from plotly import graph_objects as go

                    renewable_percentage = (renewable_production / total_production * 100) if total_production > 0 else 0
                    conventional_percentage = 100 - renewable_percentage

                    fig_pie = go.Figure(
                        data=[
                            go.Pie(
                                labels=["Erneuerbare", "Konventionelle"],
                                values=[renewable_percentage, conventional_percentage],
                                marker=dict(colors=["#00A51B", "#5D5D5D"]),
                                hole=0.4,
                                textinfo="label+percent",
                                textposition="inside",
                            )
                        ]
                    )
                    fig_pie.update_layout(
                        title="Anteil Erneuerbare",
                        showlegend=False,
                        height=300,
                        margin=dict(l=20, r=20, t=40, b=20),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.session_state.step_valid = True
            else:
                st.warning("⚠️ Keine bekannten Energiequellen im Ergebnis gefunden.")
                st.session_state.step_valid = False

        except Exception as exc:
            st.error(f"❌ Fehler bei der Visualisierung: {exc}")
            st.session_state.step_valid = False
    else:
        st.session_state.step_valid = False


def defizite_anzeigen() -> None:
    st.header("4. Defizite anzeigen:")

    if (
        st.session_state.df_simulation_con is None
        or st.session_state.df_simulation_prod is None
        or len(st.session_state.df_simulation_con) == 0
        or len(st.session_state.df_simulation_prod) == 0
    ):
        st.warning("⚠️ Verbrauchs- oder Erzeugungsdaten fehlen. Bitte zuerst Schritte 2 und 3 ausführen.")
        st.session_state.step_valid = False
        return

    try:
        energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
        energie_bilanz = col.add_column_from_other_df(
            energie_bilanz,
            st.session_state.df_simulation_con,
            "Skalierte Netzlast [MWh]",
            "Skalierte Netzlast [MWh]",
        )
        st.session_state.energie_bilanz = energie_bilanz
    except Exception as exc:
        st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {exc}")
        st.session_state.step_valid = False
        return

    view_mode = st.segmented_control(
        label="Zeitraum:",
        options=["📅 Zwei Wochen (Winter & Sommer)", "📊 Gesamtes Jahr"],
        key="bilanz_view_mode",
        default="📅 Zwei Wochen (Winter & Sommer)",
    )

    stats_df = energie_bilanz

    if view_mode == "📅 Zwei Wochen (Winter & Sommer)":
        winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
        winter_end = winter_start + pd.Timedelta(days=7)
        summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
        summer_end = summer_start + pd.Timedelta(days=7)

        winter_df = energie_bilanz[
            (pd.to_datetime(energie_bilanz["Zeitpunkt"]) >= winter_start)
            & (pd.to_datetime(energie_bilanz["Zeitpunkt"]) < winter_end)
        ]
        summer_df = energie_bilanz[
            (pd.to_datetime(energie_bilanz["Zeitpunkt"]) >= summer_start)
            & (pd.to_datetime(energie_bilanz["Zeitpunkt"]) < summer_end)
        ]

        col_winter, col_summer = st.columns(2, gap="small", border=True)

        with col_winter:
            st.markdown("#### ❄️ Winter (13.–19. Feb)")
            if len(winter_df) > 0:
                fig_winter = pltp.create_balance_plot(
                    winter_df,
                    "Skalierte Netzlast [MWh]",
                    "Gesamterzeugung [MWh]",
                    "",
                    "",
                    darkmode=False,
                )
                st.plotly_chart(fig_winter, use_container_width=True)
            else:
                st.warning("Keine Winterdaten verfügbar.")

        with col_summer:
            st.markdown("#### ☀️ Sommer (3.–9. Juli)")
            if len(summer_df) > 0:
                fig_summer = pltp.create_balance_plot(
                    summer_df,
                    "Skalierte Netzlast [MWh]",
                    "Gesamterzeugung [MWh]",
                    "",
                    "",
                    darkmode=False,
                )
                st.plotly_chart(fig_summer, use_container_width=True)
            else:
                st.warning("Keine Sommerdaten verfügbar.")
    else:
        fig_year = pltp.create_balance_plot(
            energie_bilanz,
            "Skalierte Netzlast [MWh]",
            "Gesamterzeugung [MWh]",
            "",
            "",
            darkmode=False,
        )
        st.plotly_chart(fig_year, use_container_width=True)

    try:
        balance_series = stats_df["Gesamterzeugung [MWh]"].values - stats_df["Skalierte Netzlast [MWh]"].values
        total_prod = stats_df["Gesamterzeugung [MWh]"].sum()
        total_cons = stats_df["Skalierte Netzlast [MWh]"].sum()
        deficit_hours = (balance_series < 0).sum()
        surplus_hours = (balance_series >= 0).sum()
        total_deficit = (-balance_series[balance_series < 0]).sum()
        total_surplus = balance_series[balance_series > 0].sum()

        def arrow_metric(title: str, value_num: float, unit: str) -> None:
            is_positive = value_num >= 0
            arrow = "▲" if is_positive else "▼"
            color = "#0f8f35" if is_positive else "#d63030"
            sign_value = value_num if is_positive else -value_num

            html = f"""
            <div style='padding:0px 2px;'>
              <div style='font-size:0.75rem;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;opacity:0.65;'>{title}</div>
              <div style='font-size:2rem;font-weight:700;color:{color};display:flex;align-items:center;gap:6px;'>
                <span style='font-size:1.7rem;'>{arrow}</span>{sign_value:,.0f} {unit}
            """
            st.markdown(html, unsafe_allow_html=True)

        st.space("medium")
        st.write(f"### Zusammenfassung der Energiebilanz in {st.session_state.sim_jahr}:")

        col_a, col_b, col_c, col_d = st.columns(4, gap="small", border=True)
        with col_a:
            st.metric("Gesamterzeugung", f"{total_prod/1_000_000:.2f} TWh")
        with col_b:
            st.metric("Gesamtverbrauch", f"{total_cons/1_000_000:.2f} TWh")
        with col_c:
            arrow_metric("Defizit Energie", -total_deficit, "MWh")
        with col_d:
            arrow_metric("Überschuss Energie", total_surplus, "MWh")

        col_e, col_f = st.columns(2)
        with col_e:
            if total_deficit > total_surplus:
                st.warning("#### Warnung\nEnergie Defizit zu hoch um von Speicher ausgeglichen zu werden!")
            else:
                st.empty()

        with col_f:
            col_g, col_h = st.columns(2, gap="small", border=True)
            with col_g:
                st.metric("Stunden mit Defizit", f"{deficit_hours} h")
            with col_h:
                st.metric("Stunden mit Überschuss", f"{surplus_hours} h")

        st.session_state.step_valid = True
    except Exception as exc:
        st.warning(f"⚠️ Fehler bei Statistikberechnung: {exc}")
        st.session_state.step_valid = False


def speicher_simulieren() -> None:
    st.header("5. Speicher Simulation:")

    if (
        st.session_state.df_simulation_con is None
        or st.session_state.df_simulation_prod is None
        or len(st.session_state.df_simulation_con) == 0
        or len(st.session_state.df_simulation_prod) == 0
    ):
        st.warning("⚠️ Verbrauchs- oder Erzeugungsdaten fehlen. Bitte zuerst Schritte 2 und 3 ausführen.")
        st.session_state.step_valid = False
        return

    try:
        energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
        energie_bilanz = col.add_column_from_other_df(
            energie_bilanz,
            st.session_state.df_simulation_con,
            "Skalierte Netzlast [MWh]",
            "Skalierte Netzlast [MWh]",
        )
        energie_bilanz["Initial_Balance"] = (
            energie_bilanz["Gesamterzeugung [MWh]"] - energie_bilanz["Skalierte Netzlast [MWh]"]
        )
        st.session_state.energie_bilanz = energie_bilanz

    except Exception as exc:
        st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {exc}")
        st.session_state.step_valid = False
        return

    st.subheader("Bilanz Dashboard")

    initial_surplus = energie_bilanz[energie_bilanz["Initial_Balance"] > 0]["Initial_Balance"].sum() / 1e6
    initial_deficit = energie_bilanz[energie_bilanz["Initial_Balance"] < 0]["Initial_Balance"].sum() / 1e6

    batterie_charged_twh = 0.0
    pumpspeicher_charged_twh = 0.0
    wasserstoff_charged_twh = 0.0

    st.session_state.remaining_deficit_twh = initial_deficit
    st.session_state.remaining_surplus_twh = initial_surplus

    if "storage_results" in st.session_state:
        if "battery" in st.session_state.storage_results:
            batterie_charged_twh = st.session_state.storage_results["battery"]["Batteriespeicher_Charged_MWh"].sum() / 1e6
            batterie_discharged_twh = st.session_state.storage_results["battery"]["Batteriespeicher_Discharged_MWh"].sum() / 1e6
        else:
            batterie_charged_twh, batterie_discharged_twh = 0.0, 0.0

        if "pumped" in st.session_state.storage_results:
            pumpspeicher_charged_twh = st.session_state.storage_results["pumped"]["Pumpspeicher_Charged_MWh"].sum() / 1e6
            pumpspeicher_discharged_twh = st.session_state.storage_results["pumped"]["Pumpspeicher_Discharged_MWh"].sum() / 1e6
        else:
            pumpspeicher_charged_twh, pumpspeicher_discharged_twh = 0.0, 0.0

        if "hydrogen" in st.session_state.storage_results:
            wasserstoff_charged_twh = st.session_state.storage_results["hydrogen"]["Wasserstoffspeicher_Charged_MWh"].sum() / 1e6
            wasserstoff_discharged_twh = st.session_state.storage_results["hydrogen"]["Wasserstoffspeicher_Discharged_MWh"].sum() / 1e6
        else:
            wasserstoff_charged_twh, wasserstoff_discharged_twh = 0.0, 0.0

        kompensierte_defizite_twh = batterie_discharged_twh + pumpspeicher_discharged_twh + wasserstoff_discharged_twh
        lade_energie_genutzt_twh = batterie_charged_twh + pumpspeicher_charged_twh + wasserstoff_charged_twh
    else:
        kompensierte_defizite_twh = 0.0
        lade_energie_genutzt_twh = 0.0

    st.session_state.remaining_deficit_twh = initial_deficit + kompensierte_defizite_twh
    st.session_state.remaining_surplus_twh = initial_surplus - lade_energie_genutzt_twh

    data = pd.DataFrame(
        {
            "Werte": [
                st.session_state.remaining_deficit_twh,
                st.session_state.remaining_surplus_twh,
                batterie_charged_twh,
                pumpspeicher_charged_twh,
                wasserstoff_charged_twh,
            ],
            "Label": [
                "Bilanz",
                "Bilanz",
                "Batteriespeicher",
                "Pumpspeicher",
                "Wasserstoffspeicher",
            ],
            "MeineFarbe": ["#d32f2f", "#388e3c", "#19d2c6", "#0330ab", "#8013ae"],
            "Sortierung": [1, 1, 2, 3, 4],
        }
    )

    max_wert = max(abs(initial_deficit), abs(initial_surplus))
    limit = math.ceil(max_wert / 10) * 10
    grenze = limit * 1.1

    base = alt.Chart(data).encode(
        y=alt.Y(
            "Label:N",
            title=None,
            sort=alt.EncodingSortField(field="Sortierung", order="ascending"),
            axis=alt.Axis(labelFontSize=14, labelFontWeight="bold", labelLimit=200),
        )
    )

    bars = base.mark_bar().encode(
        x=alt.X(
            "Werte:Q",
            title="Energie [TWh]",
            scale=alt.Scale(domain=[-grenze, grenze]),
            axis=alt.Axis(values=list(range(-limit, limit + 10, 10)), titleFontSize=14, labelFontSize=12),
        ),
        color=alt.Color("MeineFarbe:N", scale=None, legend=None),
    ).properties(height=200, padding={"left": 10, "right": 10, "top": 10, "bottom": 10})

    st.altair_chart(bars, use_container_width=True)

    st.markdown("---")
    st.subheader("Energiespeicher simulieren")

    winter_start = pd.to_datetime(f"{st.session_state.sim_jahr}-02-13")
    winter_end = winter_start + pd.Timedelta(days=7)
    summer_start = pd.to_datetime(f"{st.session_state.sim_jahr}-07-03")
    summer_end = summer_start + pd.Timedelta(days=7)

    def show_storage_results(result_df: pd.DataFrame, storage_name: str, initial_surplus_val: float, initial_deficit_val: float) -> None:
        st.markdown(f"### Ergebnisse: {storage_name}")

        initial_surplus_twh = initial_surplus_val
        initial_deficit_twh = initial_deficit_val

        rest_surplus_mwh = result_df["Rest_Balance_MWh"][result_df["Rest_Balance_MWh"] > 0].sum()
        rest_deficit_mwh = result_df["Rest_Balance_MWh"][result_df["Rest_Balance_MWh"] < 0].sum()

        rest_surplus_twh = rest_surplus_mwh / 1e6
        rest_deficit_twh = rest_deficit_mwh / 1e6

        used_surplus_twh = initial_surplus_twh - rest_surplus_twh
        covered_deficit_twh = abs(initial_deficit_twh) - abs(rest_deficit_twh)

        c1, c2, c3, c4 = st.columns(4)

        surplus_change = ((rest_surplus_twh - initial_surplus_twh) / initial_surplus_twh * 100) if initial_surplus_twh != 0 else 0
        deficit_change = ((abs(rest_deficit_twh) - abs(initial_deficit_twh)) / abs(initial_deficit_twh) * 100) if initial_deficit_twh != 0 else 0

        c1.metric("Gespeicherter Überschuss", f"{used_surplus_twh:.2f} TWh", "Netto-Ersparnis", delta_color="normal")
        c2.metric("Gedecktes Defizit", f"{covered_deficit_twh:.2f} TWh", "Versorgungssicherheit", delta_color="normal")
        c3.metric("Verbleibender Überschuss", f"{rest_surplus_twh:.2f} TWh", f"{surplus_change:.1f}%", delta_color="off")
        c4.metric("Verbleibendes Defizit", f"{abs(rest_deficit_twh):.2f} TWh", f"{deficit_change:.1f}%", delta_color="inverse")

        soc_col_name = f"{storage_name}_SOC_MWh"
        if soc_col_name not in result_df.columns:
            soc_cols = [c for c in result_df.columns if "SOC" in c]
            if soc_cols:
                soc_col_name = soc_cols[0]

        df_winter = result_df[
            (pd.to_datetime(result_df["Zeitpunkt"]) >= winter_start)
            & (pd.to_datetime(result_df["Zeitpunkt"]) < winter_end)
        ]
        df_summer = result_df[
            (pd.to_datetime(result_df["Zeitpunkt"]) >= summer_start)
            & (pd.to_datetime(result_df["Zeitpunkt"]) < summer_end)
        ]

        col_w, col_s = st.columns(2, gap="small", border=True)
        with col_w:
            st.markdown("#### ❄️ Winter SOC")
            if len(df_winter) > 0:
                fig_w = pltp.create_line_plot(df_winter, y_axis=soc_col_name, title="", description="", darkmode=False)
                st.plotly_chart(fig_w, use_container_width=True)
            else:
                st.warning("Keine Winterdaten")
        with col_s:
            st.markdown("#### ☀️ Sommer SOC")
            if len(df_summer) > 0:
                fig_s = pltp.create_line_plot(df_summer, y_axis=soc_col_name, title="", description="", darkmode=False)
                st.plotly_chart(fig_s, use_container_width=True)
            else:
                st.warning("Keine Sommerdaten")

    storage_tabs = st.tabs(
        [
            "🔋 Batterie (Kurzzeit)",
            "🚧 Pumpspeicher :orange[[IN ENTWICKLUNG]]",
            "🚧 Wasserstoff :orange[[IN ENTWICKLUNG]]",
        ]
    )

    with storage_tabs[0]:
        st.caption("Ideal für Tagesausgleich (PV-Überschuss in die Nacht). Hoher Wirkungsgrad.")

        st.segmented_control(
            label="Modus wählen:", options=["Basic", "Erweitert"], key="bat_args_mode", default=["Basic"]
        )

        c1, c2 = st.columns(2)
        e1, e2 = c1.columns(2)
        bat_cap = e1.number_input("Kapazität [MWh]", 1000.0, 500_000.0, 50_000.0, step=1000.0, key="bat_cap")
        bat_soc_init_pct = e2.slider("Anfangs-SOC [%]", 0, 100, 50, key="bat_soc_init") / 100
        if st.session_state.bat_args_mode == "Basic":
            bat_power = c2.number_input(
                "Leistung [MW] (Laden und Entladen)", 100.0, 50_000.0, 10_000.0, step=100.0, key="bat_pow"
            )
        else:
            d1, d2 = c2.columns(2)
            bat_power_cha = d1.number_input("Lade Leistung [MW]", 100.0, 200_000.0, 10_000.0, step=100.0, key="bat_pow_cha")
            bat_power_dis = d2.number_input("Entlade Leistung [MW]", 100.0, 200_000.0, 10_000.0, step=100.0, key="bat_pow_dis")

        if st.session_state.bat_args_mode == "Erweitert":
            c3, c4 = st.columns(2)
            bat_eff_cha = c3.slider("Ladewirkungsgrad [%]", 80, 100, 95, key="bat_eff_cha") / 100
            bat_eff_dis = c4.slider("Entladewirkungsgrad [%]", 80, 100, 95, key="bat_eff_dis") / 100
            bat_init_soc_mwh = bat_cap * bat_soc_init_pct
        else:
            bat_power_cha = bat_power
            bat_power_dis = bat_power
            bat_eff_cha = 0.95
            bat_eff_dis = 0.95
            bat_init_soc_mwh = bat_cap * 0.5

        st.markdown("---")
        if st.button("Simulation starten (Batterie)", type="primary", key="btn_bat"):
            with st.spinner("Simuliere Batterie..."):
                res_bat = sim.simulate_storage_generic(
                    df_balance=energie_bilanz,
                    type_name="Batteriespeicher",
                    capacity_mwh=bat_cap,
                    max_charge_mw=bat_power_cha,
                    max_discharge_mw=bat_power_dis,
                    charge_efficiency=bat_eff_cha,
                    discharge_efficiency=bat_eff_dis,
                    initial_soc_mwh=bat_init_soc_mwh,
                    min_soc_mwh=0.0,
                )
                st.session_state.storage_results = st.session_state.get("storage_results", {})
                st.session_state.storage_results["battery"] = res_bat
                st.session_state.step_valid = True
                st.success("✅ Batterie simuliert!")
                st.rerun()

        if "storage_results" in st.session_state and "battery" in st.session_state.storage_results:
            show_storage_results(st.session_state.storage_results["battery"], "Batteriespeicher", initial_surplus, initial_deficit)

    with storage_tabs[1]:
        st.warning("🚧 Pumpspeicher-Simulation ist derzeit in Entwicklung und noch nicht verfügbar.")

    with storage_tabs[2]:
        st.warning("🚧 Wasserstoff-Speicher-Simulation ist derzeit in Entwicklung und noch nicht verfügbar.")



def gesamt_validieren() -> None:
    st.header("6. Gesamtergebnisse")

    if st.session_state.df_simulation_con is None or st.session_state.df_simulation_prod is None:
        st.warning("⚠️ Simulationsdaten fehlen. Bitte führe die vorherigen Schritte aus.")
        st.session_state.step_valid = False
        return

    try:
        energie_bilanz = gen.add_total_generation(st.session_state.df_simulation_prod.copy())
        energie_bilanz = col.add_column_from_other_df(
            energie_bilanz,
            st.session_state.df_simulation_con,
            "Skalierte Netzlast [MWh]",
            "Skalierte Netzlast [MWh]",
        )
        st.session_state.energie_bilanz = energie_bilanz
        balance = energie_bilanz["Gesamterzeugung [MWh]"] - energie_bilanz["Skalierte Netzlast [MWh]"]
    except Exception as exc:
        st.error(f"❌ Fehler beim Erstellen der Energiebilanz: {exc}")
        st.session_state.step_valid = False
        return

    st.subheader("🎯 Simulationsübersicht")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Simulationsjahr", st.session_state.sim_jahr)
    with col2:
        st.metric("Referenzjahr", st.session_state.sim_referenz_jahr)
    with col3:
        st.metric("Studie (Verbrauch)", st.session_state.sim_studie_verbrauch or "-")
    with col4:
        st.metric("Studie (Erzeugung)", st.session_state.sim_studie_erzeugung or "-")

    st.markdown("---")

    st.subheader("Energiebilanz (ohne Speicher)")

    total_prod = energie_bilanz["Gesamterzeugung [MWh]"].sum()
    total_cons = energie_bilanz["Skalierte Netzlast [MWh]"].sum()

    deficit_mask = balance < 0
    surplus_mask = balance > 0
    deficit_hours = deficit_mask.sum()
    surplus_hours = surplus_mask.sum()

    total_deficit = (-balance[deficit_mask]).sum()
    total_surplus = balance[surplus_mask].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Gesamterzeugung", f"{total_prod/1_000_000:.2f} TWh")
    with col2:
        st.metric("Gesamtverbrauch", f"{total_cons/1_000_000:.2f} TWh")
    with col3:
        st.metric("Defizit-Energie", f"{total_deficit/1_000:.0f} GWh", delta=f"{deficit_hours} Stunden", delta_color="inverse")
    with col4:
        st.metric("Überschuss-Energie", f"{total_surplus/1_000:.0f} GWh", delta=f"{surplus_hours} Stunden", delta_color="normal")

    st.markdown("---")

    if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
        st.subheader("Speicher-Auswirkungen")

        storage_tabs = []
        if "battery" in st.session_state.storage_results:
            storage_tabs.append("🔋 Batterie")
        if "pumped" in st.session_state.storage_results:
            storage_tabs.append("💧 Pumpspeicher")
        if "hydrogen" in st.session_state.storage_results:
            storage_tabs.append("🔬 Wasserstoff")

        storage_display_tabs = st.tabs(storage_tabs)
        tab_idx = 0
        if "battery" in st.session_state.storage_results:
            with storage_display_tabs[tab_idx]:
                battery_df = st.session_state.storage_results["battery"]
                battery_charged = battery_df["Batteriespeicher_Charged_MWh"].sum()
                battery_discharged = battery_df["Batteriespeicher_Discharged_MWh"].sum()
                battery_losses = battery_discharged - battery_charged

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Geladen", f"{battery_charged/1_000:.0f} GWh")
                with col2:
                    st.metric("Entladen", f"{battery_discharged/1_000:.0f} GWh")
                with col3:
                    st.metric("Verluste", f"{abs(battery_losses)/1_000:.0f} GWh", delta=f"{(battery_losses/battery_charged*100):.1f}%")
            tab_idx += 1

        if "pumped" in st.session_state.storage_results:
            with storage_display_tabs[tab_idx]:
                pumped_df = st.session_state.storage_results["pumped"]
                pumped_charged = pumped_df["Charged [MWh]"].sum()
                pumped_discharged = pumped_df["Discharged [MWh]"].sum()
                pumped_losses = pumped_charged - pumped_discharged

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Gepumpt", f"{pumped_charged/1_000:.0f} GWh")
                with col2:
                    st.metric("Turbiniert", f"{pumped_discharged/1_000:.0f} GWh")
                with col3:
                    st.metric(
                        "Verluste",
                        f"{abs(pumped_losses)/1_000:.0f} GWh",
                        delta=f"{(abs(pumped_losses)/pumped_charged*100):.1f}%",
                        delta_color="inverse",
                    )
            tab_idx += 1

        if "hydrogen" in st.session_state.storage_results:
            with storage_display_tabs[tab_idx]:
                h2_df = st.session_state.storage_results["hydrogen"]
                h2_charged = h2_df["Charged [MWh]"].sum()
                h2_discharged = h2_df["Discharged [MWh]"].sum()
                h2_losses = h2_charged - h2_discharged

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Elektrolysiert", f"{h2_charged/1_000:.0f} GWh")
                with col2:
                    st.metric("Rückverstromt", f"{h2_discharged/1_000:.0f} GWh")
                with col3:
                    st.metric(
                        "Verluste",
                        f"{abs(h2_losses)/1_000:.0f} GWh",
                        delta=f"{(abs(h2_losses)/h2_charged*100):.1f}%",
                        delta_color="inverse",
                    )

        st.markdown("### Gesamtverbesserung durch Speichersystem")

        final_result = None
        if "hydrogen" in st.session_state.storage_results:
            final_result = st.session_state.storage_results["hydrogen"]
        elif "pumped" in st.session_state.storage_results:
            final_result = st.session_state.storage_results["pumped"]
        elif "battery" in st.session_state.storage_results:
            final_result = st.session_state.storage_results["battery"]

        if final_result is not None:
            deficit_reduction = total_deficit - abs(final_result["Rest_Balance_MWh"][final_result["Rest_Balance_MWh"] < 0].sum())
            surplus_reduction = total_surplus - final_result["Rest_Balance_MWh"][final_result["Rest_Balance_MWh"] > 0].sum()

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Defizit-Reduktion", f"{deficit_reduction/1_000:.0f} GWh", delta=f"{-(deficit_reduction/total_deficit*100):.1f}%", delta_color="inverse")
            with col2:
                st.metric("Verbleibendes Defizit", f"{abs(st.session_state.remaining_deficit_twh)*1_000:.0f} GWh", delta_color="inverse")
            with col3:
                st.metric("Überschuss-Reduktion", f"{surplus_reduction/1_000:.0f} GWh", delta=f"{-(surplus_reduction/total_surplus*100):.1f}%", delta_color="inverse")
            with col4:
                st.metric("Verbleibender Überschuss", f"{st.session_state.remaining_surplus_twh*1_000:.0f} GWh", delta_color="inverse")

        st.markdown("---")

    st.subheader("Handlungsbedarf")

    if "storage_results" in st.session_state and len(st.session_state.storage_results) > 0:
        if "hydrogen" in st.session_state.storage_results:
            final_df = st.session_state.storage_results["hydrogen"]
        elif "pumped" in st.session_state.storage_results:
            final_df = st.session_state.storage_results["pumped"]
        else:
            final_df = st.session_state.storage_results["battery"]

        final_surplus = st.session_state.remaining_surplus_twh * 1e6
        final_deficit = st.session_state.remaining_deficit_twh * 1e6
    else:
        final_surplus = total_surplus
        final_deficit = total_deficit

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### :orange[Abregelung oder Export notwendig]")
        st.metric(
            "Überschuss muss abgeregelt/exportiert werden",
            f"{final_surplus/1_000:.0f} GWh",
            help="Diese Energie kann nicht genutzt werden und muss abgeregelt oder exportiert werden.",
        )
        if final_surplus > 0:
            abregelung_pct = (final_surplus / total_prod) * 100
            st.warning(f"💡 {abregelung_pct:.2f}% der Gesamterzeugung muss abgeregelt oder exportiert werden.")

    with col2:
        st.markdown("#### :blue[Zusätzliche Energie nötig]")
        st.metric(
            "Defizit muss ausgeglichen werden",
            f"{final_deficit/1_000:.0f} GWh",
            help="Diese Energie fehlt und muss durch zusätzliche Erzeugung oder Import gedeckt werden.",
        )
        if final_deficit < 0:
            deficit_pct = (abs(final_deficit) / total_cons) * 100
            st.warning(f"💡 {deficit_pct:.2f}% des Gesamtverbrauchs kann nicht gedeckt werden.")

    st.session_state.step_valid = True


def ergebnisse_speichern() -> None:
    st.title("7. Ergebnisse speichern")

    @st.cache_data
    def convert_for_download_csv(df: pd.DataFrame) -> bytes:
        return df.to_csv().encode("utf-8")

    if "df_simulation_prod" in st.session_state:
        st.subheader("Produktions Simulation Ergebnisse: ")
        st.dataframe(st.session_state.df_simulation_prod.head())
        csv_prod = convert_for_download_csv(st.session_state.df_simulation_prod)
        st.download_button(
            "Download CSV",
            data=csv_prod,
            file_name="produktions_simulation.csv",
            mime="text/csv",
            type="primary",
        )
        st.markdown("---")
    if "df_simulation_con" in st.session_state:
        st.subheader("Verbrauchs Simulation Ergebnisse: ")
        st.dataframe(st.session_state.df_simulation_con.head())
        csv_con = convert_for_download_csv(st.session_state.df_simulation_con)
        st.download_button(
            "Download CSV",
            data=csv_con,
            file_name="verbrauchs_simulation.csv",
            mime="text/csv",
            type="primary",
        )
        st.markdown("---")
    if "storage_results" in st.session_state:
        for storage_type, storage_df in st.session_state.storage_results.items():
            st.subheader(f"{storage_type.capitalize()} Speicher Simulation Ergebnisse: ")
            st.dataframe(storage_df.head())
            csv_storage = convert_for_download_csv(storage_df)
            st.download_button(
                "Download CSV",
                data=csv_storage,
                file_name=f"{storage_type}_speicher_simulation.csv",
                mime="text/csv",
                type="primary",
            )
            st.markdown("---")

    st.markdown("## Simulation abgeschlossen!")
    if st.button("Fertig", type="primary"):
        st.balloons()
        
