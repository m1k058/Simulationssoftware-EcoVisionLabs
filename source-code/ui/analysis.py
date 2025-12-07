import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotting.plotting_formated_st as pltf
import plotting.plotting_plotly_st as pltp
from constants import ENERGY_SOURCES
from . import set_mode

def show_dataset_analysis() -> None:
    st.title("Dataset-Analyse")
    st.caption("Analysiere und visualisiere vorhandene Datensätze.")

    if st.session_state.dm is None or st.session_state.cfg is None:
        st.warning("DataManager/ConfigManager ist nicht initialisiert.")

    sidebar = st.sidebar
    sidebar.title("Einstellungen")
    selected_dataset_name = sidebar.selectbox("Wähle ein Dataframe", options=st.session_state.dm.list_dataset_names())
    df = st.session_state.dm.get(selected_dataset_name)
    df_id = st.session_state.dm.get_dataset_id(selected_dataset_name)
    datentyp = st.session_state.dm.metadata[df_id]["datatype"]

    sidebar.write(f"**Datentyp:** {datentyp}")
    # sidebar.write(f"**Zeitspanne verfügbar:** {df['Zeitpunkt'].min()} - {df['Zeitpunkt'].max()}")
    
    if datentyp == "SMARD":
        sidebar.markdown(
        "**Im Dataframe:** :green-badge[:material/trending_up: Erzeugungs Daten]"
        )
    elif datentyp == "SMARD-V":
        sidebar.markdown(
        "**Im Dataframe:** :red-badge[:material/trending_down: Verbrauchs Daten]"
        )
    elif datentyp == "CUST_PROG":
        sidebar.markdown(
        "**Im Dataframe:**  \n:green-badge[:material/trending_up: Erzeugungs Daten] :red-badge[:material/trending_down: Verbrauchs Daten]"
        )
    else:
        sidebar.write("**Im Dataframe:**")
        sidebar.warning("Unbekannter Datentyp. Möglicherweise nicht vollständig unterstützt.")

    

    sidebar.markdown("---\n ***Zeitraum auswählen***")

    # Verfügbarer Zeitraum im Dataset ermitteln
    try:
        min_date = pd.to_datetime(df["Zeitpunkt"].min())
        max_date = pd.to_datetime(df["Zeitpunkt"].max())
    except Exception as e:
        st.error(f"In diesem Dataframe gibt es keine: {e} und kann deshalb derzeit nicht analysiert werden.\nKontaktiere das Entwicklerteam um das Feature vorzuschlagen.")
        st.button("Zurück", on_click=set_mode, args=("main",))
        return
    
    sidebar.checkbox("Uhrzeit mit angeben", value=False, key="set_time")

    # Datum von
    if not st.session_state.set_time:
        selected_date_from = sidebar.date_input("Datum von", value=min_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
        selected_date_from = pd.to_datetime(selected_date_from).replace(hour=0, minute=0, second=0, microsecond=0) # Uhrzeit auf 00:00 setzen
    else:
        left, right = sidebar.columns(2)
        selected_date_from = left.date_input("Datum von", value=min_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
        selected_time_from = right.time_input("Uhrzeit von", value=pd.to_datetime("00:00").time())

    maxplot_date = pd.to_datetime(min_date)+ pd.Timedelta(days=1)

    # Datum bis
    min_date = pd.to_datetime(selected_date_from)
    if not st.session_state.set_time:
        selected_date_to = sidebar.date_input("Datum bis", value=maxplot_date,
                                                format="DD.MM.YYYY", min_value=min_date,
                                                max_value=max_date)
        selected_date_to = pd.to_datetime(selected_date_to).replace(hour=23, minute=59, second=59, microsecond=999999) # Uhrzeit auf 23:59 setzen
    else:
        left, right = sidebar.columns(2)
        selected_date_to = left.date_input("Datum bis", value=maxplot_date,
                                            format="DD.MM.YYYY", min_value=min_date,
                                            max_value=max_date)
        selected_time_to = right.time_input("Uhrzeit bis", value=pd.to_datetime("23:59").time())

    # Kombiniere Datum und Uhrzeit wenn gesetzt
    if st.session_state.set_time:
        selected_date_from = pd.to_datetime(f"{selected_date_from} {selected_time_from}")
        selected_date_to = pd.to_datetime(f"{selected_date_to} {selected_time_to}")
    
    # Filter DataFrame nach ausgewähltem Zeitraum
    df_filtered = df[
        (pd.to_datetime(df["Zeitpunkt"]) >= pd.to_datetime(selected_date_from)) &
        (pd.to_datetime(df["Zeitpunkt"]) <= pd.to_datetime(selected_date_to))
    ]
    date_diff = pd.to_datetime(selected_date_to) - pd.to_datetime(selected_date_from)
    plot_engine = st.selectbox("Wähle eine Plot Engine", options=["Altair", "Plotly", "Matplotlib"], index=1)
    
    if datentyp == "SMARD":
        # Optionen & Default aus Konstanten ableiten
        _energy_options = [src["colname"] for src in ENERGY_SOURCES.values()]
        _default_selection = [ENERGY_SOURCES["BIO"]["colname"], ENERGY_SOURCES["PV"]["colname"]]
        energiequellen = st.multiselect(
            "Energiequellen auswählen",
            options=_energy_options,
            default=_default_selection,
        )

        # Mapping für spätere Umwandlung der Auswahl in Shortcodes
        colname_to_code = {v["colname"]: k for k, v in ENERGY_SOURCES.items()}

        if plot_engine == "Altair" and (date_diff <= pd.Timedelta(days=14)):
            st.warning("⚠️ Altair kann  nur einzelne linien und nicht stacks darstellen.")
            if not energiequellen:
                st.info("Bitte mindestens eine Energiequelle auswählen.")
            else:
                # Farben passend zur Auswahl aus Konstanten ziehen
                colors = [ENERGY_SOURCES[colname_to_code[c]]["color"] for c in energiequellen]
                st.line_chart(
                    df_filtered,
                    x="Zeitpunkt",
                    y=energiequellen,
                    color=colors,
                    x_label="Datum",
                    y_label="MWh",
                )
        elif plot_engine == "Altair" and (date_diff > pd.Timedelta(days=14)):
            st.warning("⚠️ Altair kann  nur einzelne linien und nicht stacks darstellen.")
            st.warning("⚠️ Altair unterstützt nur Zeiträume bis zu 14 Tagen da der Ressourcenverbrauch sonst zu hoch ist.\n" +
            "\nBitte wähle einen kürzeren Zeitraum oder eine andere Plot Engine (empfohlen: Plotly).")

        elif plot_engine == "Plotly":
            # Nutze die Auswahl für den Plot (Shortcodes ableiten)
            energy_keys = [colname_to_code[c] for c in energiequellen] if energiequellen else ["BIO", "WON"]
            fig = pltp.create_stacked_bar_plot(
                df_filtered,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                description="Stacked Bar Plot der Energieerzeugung",
                darkmode=False,
            )
            st.plotly_chart(fig)
        
        elif plot_engine == "Matplotlib":
            energy_keys = [colname_to_code[c] for c in energiequellen] if energiequellen else ["BIO", "WON"]
            fig = pltf.create_stacked_bar_plot(
                df_filtered,
                energy_keys=energy_keys,
                title="Energieerzeugung",
                description="Stacked Bar Plot der Energieerzeugung",
                darkmode=False,
            )
            st.pyplot(fig)


        else:
            st.error("Unbekannte Plot Engine ausgewählt.")
        st.button("Zurück", on_click=set_mode, args=("main",))
    
    elif datentyp == "SMARD-V":
        # st.info("Verbrauchs-Daten können derzeit nur mit Matplotlib geplottet werden.")
        # plot_engine = "Matplotlib"

        if plot_engine == "Matplotlib":
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(pd.to_datetime(df_filtered["Zeitpunkt"]), df_filtered["Netzlast [MWh]"], color="blue", label="Netzlast (MWh)")
            ax.set_title("Netzlast über die Zeit")
            ax.set_xlabel("Datum")
            ax.set_ylabel("Netzlast (MWh)")
            ax.legend()
            ax.fill_between(pd.to_datetime(df_filtered["Zeitpunkt"]), df_filtered["Netzlast [MWh]"], color="blue", alpha=0.3)
            ax.set_ylim(bottom=0) 
            st.pyplot(fig)
        
        elif plot_engine == "Plotly":
            fig = pltp.create_line_plot(
                df_filtered,
                y_axis="Netzlast [MWh]",
                title="Netzlast über die Zeit",
                description="Line Plot der Netzlast",
                darkmode=False,
            )
            st.plotly_chart(fig)
        
        elif plot_engine == "Altair":
            st.line_chart(
                df_filtered,
                x="Zeitpunkt",
                y="Netzlast [MWh]",
                x_label="Datum",
                y_label="MWh",
            )
        
        else:
            st.error("Unbekannte Plot Engine ausgewählt.")

        st.button("Zurück", on_click=set_mode, args=("main",))
    
    else:
        st.warning("Derzeit werden nur SMARD Erzeugungs- und Verbrauchs-Daten unterstützt.")
        st.button("Zurück", on_click=set_mode, args=("main",))
