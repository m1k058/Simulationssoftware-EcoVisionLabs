import streamlit as st 
from data_manager import DataManager
from config_manager import ConfigManager

# Eigene Imports
import data_processing.generation_profile as genPro

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

    # dataframe auswählen
    selected_dataset_name = st.selectbox("Wähle ein Dataframe", options=st.session_state.dm.list_dataset_names())
    df_erzeugung = st.session_state.dm.get(selected_dataset_name)
    
    # nach zeit filtern
    df_idx = df_erzeugung.set_index("Zeitpunkt")
    df_oneYear = df_idx.loc['2023']

    genPro.generate_generation_profile()



    # genPro.generate_generation_profile()
    

