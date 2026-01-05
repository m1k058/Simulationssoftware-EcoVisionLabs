import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotting.plotting_formated_st as pltf
import plotting.plotting_plotly_st as pltp
from constants import ENERGY_SOURCES

def analysis_page() -> None:
    st.title("Dataset-Analyse")
    st.caption("Analysiere und vergleiche mehrere Datensätze stabil und übersichtlich.")

    # Frühzeitige Validierung der Session-State Objekte
    if getattr(st.session_state, "dm", None) is None or getattr(st.session_state, "cfg", None) is None:
        st.warning("DataManager/ConfigManager ist nicht initialisiert.")
        return

    sidebar = st.sidebar
    sidebar.title("Einstellungen")

    # Datensätze auswählen (mehrere möglich)
    try:
        all_names = st.session_state.dm.list_dataset_names() or []
    except Exception:
        all_names = []

    if not all_names:
        st.info("Keine Datensätze geladen. Bitte lade Daten im Home-Tab.")
        return

    selected_names = sidebar.multiselect(
        "Wähle ein oder mehrere DataFrames",
        options=all_names,
        default=all_names[:1],
        key="selected_datasets_analysis",
    )

    if not selected_names:
        st.info("Bitte mindestens ein DataFrame auswählen.")
        return

    # Sammle Metadaten und DataFrames
    datasets = []
    for name in selected_names:
        try:
            df = st.session_state.dm.get(name)
            df_id = st.session_state.dm.get_dataset_id(name)
            dtype = st.session_state.dm.metadata.get(df_id, {}).get("datatype", "UNKNOWN")
            datasets.append({"name": name, "df": df, "id": df_id, "datatype": dtype})
        except Exception as e:
            st.error(f"Fehler beim Laden von '{name}': {e}")

    # Falls aus irgendeinem Grund nichts gesammelt wurde
    if not datasets:
        st.warning("Es konnten keine gültigen DataFrames geladen werden.")
        return

    # Globalen Zeitraum über alle ausgewählten DataFrames bestimmen (Union)
    global_mins, global_maxs = [], []
    for d in datasets:
        if "Zeitpunkt" in d["df"].columns:
            s = pd.to_datetime(d["df"]["Zeitpunkt"], errors="coerce")
            if not s.dropna().empty:
                global_mins.append(s.min())
                global_maxs.append(s.max())
        else:
            st.warning(f"'{d['name']}' enthält keine Spalte 'Zeitpunkt' und wird übersprungen.")

    if not global_mins:
        st.error("Keines der ausgewählten DataFrames enthält eine gültige 'Zeitpunkt'-Spalte.")
        return

    min_date_total = min(global_mins)
    max_date_total = max(global_maxs)

    # Anzeige der inhaltlichen Typen-Zusammenfassung
    dtypes = {d["datatype"] for d in datasets}
    if len(dtypes) == 1:
        sidebar.write(f"**Datentyp(e):** {list(dtypes)[0]}")
    else:
        sidebar.write(f"**Datentyp(e):** gemischt ({', '.join(sorted(dtypes))})")

    # Badges-Hinweis
    sidebar.markdown("---\n ***Zeitraum & Anzeige***")
    sidebar.checkbox("Uhrzeit mit angeben", value=st.session_state.get("set_time", False), key="set_time")

    # Datum von
    if not st.session_state.get("set_time", False):
        selected_date_from = sidebar.date_input(
            "Datum von",
            value=min_date_total,
            format="DD.MM.YYYY",
            min_value=min_date_total,
            max_value=max_date_total,
            key="date_from_analysis",
        )
        selected_date_from = pd.to_datetime(selected_date_from).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        left, right = sidebar.columns(2)
        selected_date_from = left.date_input(
            "Datum von",
            value=min_date_total,
            format="DD.MM.YYYY",
            min_value=min_date_total,
            max_value=max_date_total,
            key="date_from_analysis",
        )
        selected_time_from = right.time_input("Uhrzeit von", value=pd.to_datetime("00:00").time(), key="time_from_analysis")

    # Vorschlagswert für "bis" (ein Tag nach Start)
    maxplot_date = pd.to_datetime(selected_date_from) + pd.Timedelta(days=1)

    # Datum bis (min ist immer Start)
    if not st.session_state.get("set_time", False):
        selected_date_to = sidebar.date_input(
            "Datum bis",
            value=min(maxplot_date, max_date_total),
            format="DD.MM.YYYY",
            min_value=pd.to_datetime(selected_date_from),
            max_value=max_date_total,
            key="date_to_analysis",
        )
        selected_date_to = pd.to_datetime(selected_date_to).replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        left, right = sidebar.columns(2)
        selected_date_to = left.date_input(
            "Datum bis",
            value=min(maxplot_date, max_date_total),
            format="DD.MM.YYYY",
            min_value=pd.to_datetime(selected_date_from),
            max_value=max_date_total,
            key="date_to_analysis",
        )
        selected_time_to = right.time_input("Uhrzeit bis", value=pd.to_datetime("23:59").time(), key="time_to_analysis")

    # Kombiniere Datum und Uhrzeit wenn gesetzt
    if st.session_state.get("set_time", False):
        selected_date_from = pd.to_datetime(f"{selected_date_from} {selected_time_from}")
        selected_date_to = pd.to_datetime(f"{selected_date_to} {selected_time_to}")

    # Plausibilitätscheck
    if pd.to_datetime(selected_date_from) > pd.to_datetime(selected_date_to):
        st.error("Das Startdatum liegt nach dem Enddatum. Bitte korrigieren.")
        return

    date_diff = pd.to_datetime(selected_date_to) - pd.to_datetime(selected_date_from)

    # Plot-Engine global auswählen (einheitliche Steuerung)
    plot_engine = sidebar.selectbox(
        "Plot Engine",
        options=["Altair", "Plotly", "Matplotlib"],
        index=1,
        key="plot_engine_analysis",
    )

    # Hilfsfunktionen
    def _energy_options_for_df(local_df: pd.DataFrame):
        opts = [src["colname"] for src in ENERGY_SOURCES.values() if src["colname"] in local_df.columns]
        default = [v["colname"] for k, v in ENERGY_SOURCES.items() if k in ("BIO", "PV") and v["colname"] in local_df.columns]
        return opts, default

    def _plot_generation(local_df: pd.DataFrame, energy_selection: list[str]):
        colname_to_code = {v["colname"]: k for k, v in ENERGY_SOURCES.items()}
        if plot_engine == "Altair":
            st.warning("⚠️ Altair kann nur einzelne Linien (keine Stacks) darstellen.")
            if date_diff > pd.Timedelta(days=14):
                st.warning("⚠️ Altair ist auf ≤ 14 Tage begrenzt. Bitte kürzeren Zeitraum oder Plotly nutzen.")
            else:
                if not energy_selection:
                    st.info("Bitte mindestens eine Energiequelle auswählen.")
                else:
                    colors = [ENERGY_SOURCES[colname_to_code[c]]["color"] for c in energy_selection if c in colname_to_code]
                    st.line_chart(
                        local_df,
                        x="Zeitpunkt",
                        y=energy_selection,
                        color=colors if colors else None,
                        x_label="Datum",
                        y_label="MWh",
                    )
        elif plot_engine == "Plotly":
            energy_keys = [colname_to_code[c] for c in energy_selection] if energy_selection else ["BIO", "WON"]
            fig = pltp.create_generation_plot(
                local_df,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                date_from=pd.to_datetime(selected_date_from),
                date_to=pd.to_datetime(selected_date_to)
            )
            st.plotly_chart(fig, width='stretch')
        elif plot_engine == "Matplotlib":
            energy_keys = [colname_to_code[c] for c in energy_selection] if energy_selection else ["BIO", "WON"]
            fig = pltf.create_stacked_bar_plot(
                local_df,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                description="Stacked Bar Plot der Energieerzeugung",
                darkmode=False
            )
            st.pyplot(fig, width='stretch')
        else:
            st.error("Unbekannte Plot Engine ausgewählt.")

    def _plot_consumption(local_df: pd.DataFrame):
        y_col = "Netzlast [MWh]"
        if y_col not in local_df.columns:
            st.warning("Es wurden keine Verbrauchsspalten gefunden (erwartet: 'Netzlast [MWh]').")
            return
        if plot_engine == "Matplotlib":
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(pd.to_datetime(local_df["Zeitpunkt"]), local_df[y_col], color="blue", label="Netzlast (MWh)")
            ax.set_title("Netzlast über die Zeit")
            ax.set_xlabel("Datum")
            ax.set_ylabel("Netzlast (MWh)")
            ax.legend()
            ax.fill_between(pd.to_datetime(local_df["Zeitpunkt"]), local_df[y_col], color="blue", alpha=0.3)
            ax.set_ylim(bottom=0)
            st.pyplot(fig)
        elif plot_engine == "Plotly":
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(local_df["Zeitpunkt"]),
                y=local_df[y_col],
                mode='lines',
                name='Netzlast',
                fill='tozeroy',
                line=dict(color='blue')
            ))
            fig.update_layout(
                title="Netzlast über die Zeit",
                xaxis_title="Datum",
                yaxis_title="Netzlast (MWh)",
                template="plotly_white",
                hovermode='x unified'
            )
            st.plotly_chart(fig, width='stretch')
        elif plot_engine == "Altair":
            st.line_chart(local_df, x="Zeitpunkt", y=y_col, x_label="Datum", y_label="MWh")
        else:
            st.error("Unbekannte Plot Engine ausgewählt.")

    # Hauptbereich: Tabs pro ausgewähltem DataFrame
    tabs = st.tabs([d["name"] for d in datasets])

    for tab, d in zip(tabs, datasets):
        with tab:
            df = d["df"]
            if "Zeitpunkt" not in df.columns:
                st.warning("Dieses DataFrame hat keine 'Zeitpunkt'-Spalte und kann nicht dargestellt werden.")
                continue

            # Filter nach globalem Zeitraum
            df_filtered = df[
                (pd.to_datetime(df["Zeitpunkt"], errors="coerce") >= pd.to_datetime(selected_date_from)) &
                (pd.to_datetime(df["Zeitpunkt"], errors="coerce") <= pd.to_datetime(selected_date_to))
            ].copy()

            # Info-Badges zum Inhalt
            if d["datatype"] == "SMARD":
                st.markdown("**Im Dataframe:** :green-badge[:material/trending_up: Erzeugungs Daten]")
            elif d["datatype"] == "SMARD-V":
                st.markdown("**Im Dataframe:** :red-badge[:material/trending_down: Verbrauchs Daten]")
            elif d["datatype"] == "CUST_PROG":
                st.markdown("**Im Dataframe:**  \n:green-badge[:material/trending_up: Erzeugungs Daten] :red-badge[:material/trending_down: Verbrauchs Daten]")
            else:
                st.write("**Im Dataframe:**")
                st.warning("Unbekannter Datentyp. Möglicherweise nicht vollständig unterstützt.")

            # Darstellung abhängig vom Typ bzw. vorhandenen Spalten
            has_generation_cols = any(src["colname"] in df_filtered.columns for src in ENERGY_SOURCES.values())
            has_consumption = "Netzlast [MWh]" in df_filtered.columns

            if d["datatype"] == "SMARD":
                opts, default = _energy_options_for_df(df_filtered)
                energiequellen = st.multiselect(
                    "Energiequellen auswählen",
                    options=opts,
                    default=default,
                    key=f"energies_{d['id']}",
                )
                _plot_generation(df_filtered, energiequellen)

            elif d["datatype"] == "SMARD-V":
                _plot_consumption(df_filtered)

            elif d["datatype"] == "CUST_PROG":
                # Zeige beide Bereiche, sofern vorhanden
                if has_generation_cols:
                    with st.expander("Erzeugung", expanded=True):
                        opts, default = _energy_options_for_df(df_filtered)
                        energiequellen = st.multiselect(
                            "Energiequellen auswählen",
                            options=opts,
                            default=default,
                            key=f"energies_{d['id']}_cust",
                        )
                        _plot_generation(df_filtered, energiequellen)
                if has_consumption:
                    with st.expander("Verbrauch", expanded=True):
                        _plot_consumption(df_filtered)
                if not has_generation_cols and not has_consumption:
                    st.info("Keine bekannten Spalten für Erzeugung oder Verbrauch gefunden.")
            else:
                # Fallback: versuche sinnvolle Darstellung
                if has_generation_cols:
                    opts, default = _energy_options_for_df(df_filtered)
                    energiequellen = st.multiselect(
                        "Energiequellen auswählen",
                        options=opts,
                        default=default,
                        key=f"energies_{d['id']}_fallback",
                    )
                    _plot_generation(df_filtered, energiequellen)
                elif has_consumption:
                    _plot_consumption(df_filtered)
                else:
                    st.warning("Derzeit werden nur SMARD Erzeugungs- und Verbrauchs-Daten unterstützt.")

