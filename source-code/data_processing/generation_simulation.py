"""
Erzeugungssimulation für Energiesystem-Szenarien.

Dieses Modul simuliert die Energieerzeugung basierend auf SMARD-Daten und 
Ziel-Kapazitäten. Es berechnet Kapazitätsfaktoren aus historischen Daten und 
skaliert diese auf die gewünschten installierten Leistungen.
"""

import pandas as pd
from typing import Dict
from config_manager import ConfigManager
from constants import ENERGY_SOURCES, SOURCES_GROUPS


def _generate_generation_profile(
    smard_erzeugung_df: pd.DataFrame,
    smard_instaliert_df: pd.DataFrame, 
    include_conv: bool = False
) -> pd.DataFrame:
    """
    Generiert ein Erzeugungsprofil basierend auf SMARD-Daten.
    
    Berechnet Kapazitätsfaktoren (0-1) aus historischen Erzeugungsdaten und 
    installierten Kapazitäten. Standardmäßig werden nur erneuerbare Energien 
    berücksichtigt, mit include_conv auch konventionelle Kraftwerke.
    
    Args:
        smard_erzeugung_df: DataFrame mit SMARD Erzeugungsdaten für ein Jahr
        smard_instaliert_df: DataFrame mit installierten Kapazitäten für ein Jahr
        include_conv: Ob konventionelle Kraftwerke einbezogen werden sollen
    
    Returns:
        DataFrame mit Kapazitätsfaktoren (0 bis 1) für alle Technologien
    """
    # Prüfe ob gesamtes Jahr in den Daten vorhanden ist
    if smard_erzeugung_df.index.min().month != 1 or smard_erzeugung_df.index.max().month != 12:
        raise ValueError("SMARD-Daten müssen ein vollständiges Jahr abdecken.")
    
    # Filtere die relevanten Spalten
    if include_conv:
        relevant_sources = SOURCES_GROUPS["Renewable"] + SOURCES_GROUPS["Conventional"]
    else:
        relevant_sources = SOURCES_GROUPS["Renewable"]
    
    # Erstelle Mapping zwischen MWh und MW Spalten
    erzeugung_cols = [ENERGY_SOURCES[src]["colname"] for src in relevant_sources if src in ENERGY_SOURCES]
    installiert_cols = [ENERGY_SOURCES[src]["colname_MW"] for src in relevant_sources if src in ENERGY_SOURCES]
    
    erzeugung_filterd_df = smard_erzeugung_df[erzeugung_cols].copy()
    installiert_filterd_df = smard_instaliert_df[installiert_cols].copy()

    # Capacity Factor berechnen: cf_i,t = P_ist_i,t / P_inst_i,t
    # P_ist_i,t: historische Erzeugung in MW zum Zeitpunkt t
    # P_inst_i,t: installierte Leistung in MW (konstant für das Jahr)
    # Ergebnis: dimensionsloser Wert zwischen 0 und 1
    
    # Rename installiert columns to match erzeugung columns for alignment
    col_mapping = {installiert_cols[i]: erzeugung_cols[i] for i in range(len(erzeugung_cols))}
    installiert_filterd_df = installiert_filterd_df.rename(columns=col_mapping)
    
    # Extrahiere das Jahr aus den Erzeugungsdaten
    jahr = erzeugung_filterd_df.index[0].year
    
    # Finde die passende Zeile mit der installierten Leistung für dieses Jahr
    if 'Jahr' in smard_instaliert_df.columns:
        installiert_jahr_row = smard_instaliert_df[smard_instaliert_df['Jahr'] == jahr]
        if installiert_jahr_row.empty:
            raise ValueError(f"Keine installierten Leistungsdaten für Jahr {jahr} gefunden.")
        installiert_werte = installiert_jahr_row[installiert_cols].iloc[0]
    else:
        # Nutze Index (Zeitpunkt) - finde Eintrag für das Jahr
        installiert_jahr_row = smard_instaliert_df[smard_instaliert_df.index.year == jahr]
        if installiert_jahr_row.empty:
            raise ValueError(f"Keine installierten Leistungsdaten für Jahr {jahr} gefunden.")
        installiert_werte = installiert_jahr_row[installiert_cols].iloc[0]
    
    # Rename für Alignment
    installiert_werte.index = [col_mapping[col] for col in installiert_werte.index]
    
    # Konvertiere MWh zu MW (Viertelstunden: * 4)
    erzeugung_mw_df = erzeugung_filterd_df * 4
    capacity_factor_df = erzeugung_mw_df.div(installiert_werte)
    
    # NaN-Werte auf 0 setzen (tritt auf wenn installierte Leistung = 0)
    capacity_factor_df = capacity_factor_df.fillna(0)
    
    # Werte auf [0, 1] begrenzen (Sicherheitscheck)
    capacity_factor_df = capacity_factor_df.clip(lower=0, upper=1)
    
    return capacity_factor_df


def simulate_production(
    cfg: ConfigManager,
    smardGeneration: pd.DataFrame,
    smardCapacity: pd.DataFrame,
    capacity_dict: Dict,
    wind_on_weather: str,
    wind_off_weather: str,
    pv_weather: str,
    simu_jahr: int
) -> pd.DataFrame:
    """
    Simuliert die Energieproduktion für alle Technologien basierend auf SMARD-Daten
    und Ziel-installierten Leistungen für ein Simulationsjahr.
    
    Die Funktion:
    1. Lädt SMARD-Referenzjahre basierend auf Wetterprofilen (good/average/bad)
    2. Generiert Kapazitätsfaktoren aus historischen Daten
    3. Skaliert auf Ziel-Kapazitäten für das Simulationsjahr
    4. Passt an Schaltjahre/Normaljahre an
    
    Args:
        cfg: ConfigManager Instanz
        smardGeneration: DataFrame mit SMARD Erzeugungsdaten (MWh, Viertelstunden)
        smardCapacity: DataFrame mit installierten Kapazitäten im Referenzjahr
        capacity_dict: Dictionary mit Ziel-Kapazitäten pro Technologie und Jahr
                      {"Photovoltaik": {"2030": 150000, "2045": 385000}, ...} [MW]
        wind_on_weather: Weather-Profil für Wind Onshore ("good", "average", "bad")
        wind_off_weather: Weather-Profil für Wind Offshore ("good", "average", "bad")
        pv_weather: Weather-Profil für Photovoltaik ("good", "average", "bad")
        simu_jahr: Das Zieljahr für die Simulation
    
    Returns:
        DataFrame mit skalierter Energieproduktion [MWh] für alle Technologien
        Spalten: Zeitpunkt, Wind Onshore [MWh], Wind Offshore [MWh], 
                Photovoltaik [MWh], Biomasse [MWh], etc.
    """

    # Suche Referenzjahre für das Filtern der SMARD-Daten basierend auf Wetterprofil
    windOn_smard_ref_jahr = cfg.get_generation_year("Wind_Onshore", wind_on_weather)
    windOff_smard_ref_jahr = cfg.get_generation_year("Wind_Offshore", wind_off_weather)
    pv_smard_ref_jahr = cfg.get_generation_year("Photovoltaik", pv_weather)
    ref_jahr = cfg.config["GENERATION_SIMULATION"]["optimal_reference_years_by_technology"]["default"]

    # Bereite SMARD-Daten vor (setze Zeitpunkt als Index)
    smardGeneration = smardGeneration.set_index("Zeitpunkt")
    smardGeneration.index = pd.to_datetime(smardGeneration.index)

    # Filtere Referenzjahre aus SMARD-Daten
    df_windOn_ref = smardGeneration.loc[str(windOn_smard_ref_jahr)].copy()
    df_windOff_ref = smardGeneration.loc[str(windOff_smard_ref_jahr)].copy()
    df_pv_ref = smardGeneration.loc[str(pv_smard_ref_jahr)].copy()
    df_ref = smardGeneration.loc[str(ref_jahr)].copy()

    df_windOn_refCap = smardCapacity[smardCapacity["Jahr"] == windOn_smard_ref_jahr]
    df_windOff_refCap = smardCapacity[smardCapacity["Jahr"] == windOff_smard_ref_jahr]
    df_pv_refCap = smardCapacity[smardCapacity["Jahr"] == pv_smard_ref_jahr]
    df_refCap = smardCapacity[smardCapacity["Jahr"] == ref_jahr]

    # Generiere Kapazitätsfaktor-Profile für alle Technologien
    df_windOn_Profile = _generate_generation_profile(df_windOn_ref, df_windOn_refCap, False)
    df_windOff_Profile = _generate_generation_profile(df_windOff_ref, df_windOff_refCap, False)
    df_pv_Profile = _generate_generation_profile(df_pv_ref, df_pv_refCap, False)
    df_other_Profile = _generate_generation_profile(df_ref, df_refCap, True)
    
    # Erstelle Ziel-Zeitindex für das Simulationsjahr
    start_date = pd.Timestamp(year=simu_jahr, month=1, day=1)
    end_date = pd.Timestamp(year=simu_jahr, month=12, day=31, hour=23, minute=45)
    target_time_index = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Funktion zum Anpassen der Profile auf Zieljahr-Länge (Schaltjahr-Handling)
    def align_profile_to_target_year(df_profile, target_index):
        """Passt ein Profil an die Länge des Zieljahres an (kürzt oder wiederholt)."""
        profile_len = len(df_profile)
        target_len = len(target_index)
        
        if profile_len == target_len:
            return df_profile
        elif profile_len > target_len:
            # Schaltjahr-Profil auf Normaljahr kürzen
            return df_profile.iloc[:target_len].copy()
        else:
            # Normaljahr-Profil auf Schaltjahr erweitern (letzten Tag wiederholen)
            repeat_data = df_profile.iloc[-96:].copy()  # 96 Viertelstunden = 24h
            df_extended = pd.concat([df_profile, repeat_data], ignore_index=True)
            return df_extended.iloc[:target_len].copy()
    
    # Profile auf Zieljahr-Länge anpassen
    df_windOn_Profile = align_profile_to_target_year(df_windOn_Profile, target_time_index)
    df_windOff_Profile = align_profile_to_target_year(df_windOff_Profile, target_time_index)
    df_pv_Profile = align_profile_to_target_year(df_pv_Profile, target_time_index)
    df_other_Profile = align_profile_to_target_year(df_other_Profile, target_time_index)
    
    # Simuliere Produktion für alle Technologien durch Skalierung auf Ziel-Kapazitäten
    target_year_str = str(simu_jahr)
    target_year_int = int(simu_jahr)
    
    # Initialisiere Ergebnis-DataFrame
    df_result = pd.DataFrame({'Zeitpunkt': target_time_index})
    
    # Verarbeitungsfaktor: 0.25 für Viertelstunden (CF * Kapazität_MW * 0.25h = Energie_MWh)
    quarter_hour_factor = 0.25
    
    # 1. Wind Onshore
    if 'Wind_Onshore' in capacity_dict:
        target_capacity = capacity_dict['Wind_Onshore'].get(target_year_str, 
                         capacity_dict['Wind_Onshore'].get(target_year_int, 0))
        if target_capacity > 0:
            # Suche nach passender Spalte (verschiedene Namensformate)
            possible_cols = ['Wind Onshore [MWh]', 'Wind_Onshore [MWh]', 'Wind Onshore', 'Wind_Onshore', 'Onshore [MWh]']
            wind_on_col = None
            for col in possible_cols:
                if col in df_windOn_Profile.columns:
                    wind_on_col = col
                    break
            
            if wind_on_col:
                df_result['Wind Onshore [MWh]'] = (
                    df_windOn_Profile[wind_on_col].values * target_capacity * quarter_hour_factor
                )
    
    # 2. Wind Offshore
    if 'Wind_Offshore' in capacity_dict:
        target_capacity = capacity_dict['Wind_Offshore'].get(target_year_str,
                         capacity_dict['Wind_Offshore'].get(target_year_int, 0))
        if target_capacity > 0:
            possible_cols = ['Wind Offshore [MWh]', 'Wind_Offshore [MWh]', 'Wind Offshore', 'Wind_Offshore', 'Offshore [MWh]']
            wind_off_col = None
            for col in possible_cols:
                if col in df_windOff_Profile.columns:
                    wind_off_col = col
                    break
            
            if wind_off_col:
                df_result['Wind Offshore [MWh]'] = (
                    df_windOff_Profile[wind_off_col].values * target_capacity * quarter_hour_factor
                )
    
    # 3. Photovoltaik
    if 'Photovoltaik' in capacity_dict:
        target_capacity = capacity_dict['Photovoltaik'].get(target_year_str,
                         capacity_dict['Photovoltaik'].get(target_year_int, 0))
        if target_capacity > 0:
            possible_cols = ['Photovoltaik [MWh]', 'PV [MWh]', 'Photovoltaik', 'Solar [MWh]']
            pv_col = None
            for col in possible_cols:
                if col in df_pv_Profile.columns:
                    pv_col = col
                    break
            
            if pv_col:
                df_result['Photovoltaik [MWh]'] = (
                    df_pv_Profile[pv_col].values * target_capacity * quarter_hour_factor
                )
    
    # 4. Alle anderen Technologien (konventionelle + Biomasse/Wasser)
    other_technologies = [
        'Biomasse', 'Wasserkraft', 'Erdgas', 'Steinkohle', 'Braunkohle', 
        'Kernenergie', 'Sonstige Erneuerbare'
    ]
    
    for tech in other_technologies:
        tech_col_name = f'{tech} [MWh]'
        if tech in capacity_dict and tech_col_name in df_other_Profile.columns:
            target_capacity = capacity_dict[tech].get(target_year_str,
                             capacity_dict[tech].get(target_year_int, 0))
            if target_capacity > 0:
                df_result[tech_col_name] = (
                    df_other_Profile[tech_col_name].values * target_capacity * quarter_hour_factor
                )
    
    # Setze das Jahr in der Zeitpunkt-Spalte auf das Simulationsjahr
    df_result['Zeitpunkt'] = pd.to_datetime(df_result['Zeitpunkt'])
    df_result['Zeitpunkt'] = df_result['Zeitpunkt'].apply(lambda x: x.replace(year=simu_jahr))
    
    return df_result
