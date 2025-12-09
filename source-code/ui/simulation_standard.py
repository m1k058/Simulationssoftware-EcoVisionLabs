import streamlit as st 
from data_manager import DataManager
from config_manager import ConfigManager

# Eigene Imports
import data_processing.generation_profile as genPro
import data_processing.simulation as simu
import data_processing.col as col

def standard_simulation_page() -> None:
    st.title("Simulation")
    st.caption("Eine Vollständige Simulation basierend auf vordefinierten Studien und Parametern.")
    st.warning("🏗️ WARNUNG: Diese Funktion ist noch in der Entwicklung und dient nur Demonstrationszwecken.")
    sidebar = st.sidebar
    
    # Überprüfe ob DataManager und ConfigManager geladen sind
    if st.session_state.dm is None or st.session_state.cfg is None:
        st.warning("DataManager/ConfigManager ist nicht initialisiert.")

    ## =================================== ##
    ##       Verbrauch Simulation          ##
    ## =================================== ##




    ## =================================== ##
    ##       Erzeugung Simulation          ##
    ## =================================== ##
    st.subheader("Erzeugungssimulation")

    # dataframes auswählen
    df_erzeugung = st.session_state.dm.get("SMARD_2020-2025_Erzeugung")
    df_instErzeugung = st.session_state.dm.get("SMARD_Installierte Leistung 2020-2025")
    
    # nach zeit filtern
    df_idx = df_erzeugung.set_index("Zeitpunkt")
    df_oneYear = df_idx.loc['2024']

    st.dataframe(df_oneYear)
    st.dataframe(df_instErzeugung)

    df_genProfile = None

    if st.button("Berechnen"):
        df_genProfile = genPro.generate_generation_profile(df_oneYear, df_instErzeugung, True)

    st.dataframe(df_genProfile)
    



