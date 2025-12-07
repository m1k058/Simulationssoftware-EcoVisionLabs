import pandas as pd
from constants import ENERGY_SOURCES, SOURCES_GROUPS


def generate_generation_profile(smard_erzeugung_df: pd.DataFrame,smard_instaliert_df: pd.DataFrame, include_conv: bool = False) -> pd.DataFrame:
    """
    Generriert ein Erzeugungsprofil basierend auf SMARD-Daten. Standardmäßig werden nur erneuerbare Energien 
    berücksichtigt. Mit dem Parameter `include_conv` können auch konventionelle Kraftwerke einbezogen werden.
    Args:
        smard_erzeugung_df (pd.DataFrame): DataFrame mit Erzeugungsdaten für ein vollständiges Jahr.
        smard_instaliert_df (pd.DataFrame): DataFrame mit installierten Kapazitäten für ein vollständiges Jahr.
        include_conv (bool): Ob konventionelle Kraftwerke einbezogen werden sollen.
    
    Returns:
        pd.DataFrame: DataFrame mit dem generierten Erzeugungsprofil normiert auf Kapazitätsfaktoren (0 bis 1).
    """
    # Prüfe on gesammtes Jahr in den Daten vorhanden ist
    if smard_erzeugung_df.index.min().month != 1 or smard_erzeugung_df.index.max().month != 12:
        raise ValueError("SMARD-Daten müssen ein vollständiges Jahr abdecken.")
    
    # Filtere die relevanten Spalten
    if include_conv:
        relevant_sources = SOURCES_GROUPS["Renewable"] + SOURCES_GROUPS["Conventional"]
    else:
        relevant_sources = SOURCES_GROUPS["Renewable"]
    
    erzeugung_filterd_df = smard_erzeugung_df[[ENERGY_SOURCES[src]["colname"] for src in relevant_sources if src in ENERGY_SOURCES]].copy()
    installiert_filterd_df = smard_instaliert_df[[ENERGY_SOURCES[src]["colname"] for src in relevant_sources if src in ENERGY_SOURCES]].copy()

    # Capacity Factor berechnen: cf_i,t = P_ist_i,t / P_inst_i,t
    # P_ist_i,t: historische Erzeugung in MW zum Zeitpunkt t
    # P_inst_i,t: installierte Leistung in MW (konstant für das Jahr)
    # Ergebnis: dimensionsloser Wert zwischen 0 und 1
    
    # Da installierte Leistung nur eine Zeile hat, wird sie für alle Zeitschritte wiederholt
    # mittels Broadcasting bei der Division
    capacity_factor_df = erzeugung_filterd_df.div(installiert_filterd_df.iloc[0])
    
    # NaN-Werte auf 0 setzen (tritt auf wenn installierte Leistung = 0)
    capacity_factor_df = capacity_factor_df.fillna(0)
    
    # Werte auf [0, 1] begrenzen (Sicherheitscheck)
    capacity_factor_df = capacity_factor_df.clip(lower=0, upper=1)
    
    return capacity_factor_df
