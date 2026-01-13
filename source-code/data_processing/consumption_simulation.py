"""
Verbrauchssimulation für Energiesystem-Szenarien.

Dieses Modul simuliert den Energieverbrauch basierend auf BDEW-Standardlastprofilen
(Haushalte H25, Gewerbe G25, Landwirtschaft L25) und integriert Wärmepumpen-Last.
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_processing.heat_pump_simulation import HeatPumpSimulation


def simulate_consumption_BDEW(
    lastH: pd.DataFrame, 
    lastG: pd.DataFrame, 
    lastL: pd.DataFrame, 
    lastZielH: float, 
    lastZielG: float, 
    lastZielL: float, 
    simu_jahr: int
) -> pd.DataFrame:
    """
    Simuliert den Energieverbrauch basierend auf BDEW-Standardlastprofilen.
    
    Die Funktion:
    1. Lädt BDEW-Standardlastprofile (H25 Haushalte, G25 Gewerbe, L25 Landwirtschaft)
    2. Erstellt einen vollständigen Jahresverlauf mit Tagestypen (WT/SA/FT)
    3. Wendet Dynamisierungsfaktor für Haushalte an (saisonale Variation)
    4. Skaliert Profile auf Jahres-Zielwerte
    5. Gibt Viertelstunden-Zeitreihe zurück
    
    Args:
        lastH: BDEW H25-Lastprofil (Haushalte)
        lastG: BDEW G25-Lastprofil (Gewerbe)
        lastL: BDEW L25-Lastprofil (Landwirtschaft)
        lastZielH: Ziel-Jahresverbrauch Haushalte [TWh]
        lastZielG: Ziel-Jahresverbrauch Gewerbe [TWh]
        lastZielL: Ziel-Jahresverbrauch Landwirtschaft [TWh]
        simu_jahr: Simulationsjahr (z.B. 2030 oder 2045)
        
    Returns:
        DataFrame mit Spalten:
        - Zeitpunkt: DateTime-Index (Viertelstunden-Auflösung)
        - Haushalte [MWh], Gewerbe [MWh], Landwirtschaft [MWh]
        - Gesamt [MWh]: Summe aller Sektoren
    """
    
    def _prepare_load_profile(df: pd.DataFrame) -> pd.DataFrame:
        """Bereitet BDEW-Lastprofil vor: Komma -> Punkt, numerische Konvertierung."""
        df = df.copy()
        
        # Ersetze Kommas durch Punkte in value_kWh
        if 'value_kWh' in df.columns:
            if df['value_kWh'].dtype == 'object':
                df['value_kWh'] = df['value_kWh'].astype(str).str.replace(',', '.')
            df['value_kWh'] = pd.to_numeric(df['value_kWh'], errors='coerce')
        
        # Konvertiere timestamp zu Datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Konvertiere month zu int
        if 'month' in df.columns:
            df['month'] = pd.to_numeric(df['month'], errors='coerce').astype('Int64')
        
        return df
    
    # Vorbereiten der drei Lastprofile
    lastH = _prepare_load_profile(lastH)
    lastG = _prepare_load_profile(lastG)
    lastL = _prepare_load_profile(lastL)
    
    # Erstelle vollständigen Jahreskalender
    start_date = pd.Timestamp(f'{simu_jahr}-01-01 00:00:00')
    end_date = pd.Timestamp(f'{simu_jahr}-12-31 23:45:00')
    zeitpunkte = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Basis-DataFrame mit Zeitinformationen
    df_result = pd.DataFrame({'Zeitpunkt': zeitpunkte})
    df_result['month'] = df_result['Zeitpunkt'].dt.month
    df_result['weekday'] = df_result['Zeitpunkt'].dt.weekday  # 0=Montag, 6=Sonntag
    df_result['day'] = df_result['Zeitpunkt'].dt.day
    
    # Deutsche Feiertage für das Simulationsjahr (BDEW-Definition)
    try:
        import holidays
        # Bundeseinheitliche Feiertage (9 Tage)
        de_holidays = holidays.Germany(years=simu_jahr, language='de')
        feiertage = [pd.Timestamp(date) for date in de_holidays.keys()]
    except ImportError:
        # Fallback: Feste Feiertage (ohne bewegliche Feiertage)
        print("Warnung: Package 'holidays' nicht verfügbar. Bewegliche Feiertage fehlen!")
        feiertage = [
            pd.Timestamp(f'{simu_jahr}-01-01'),  # Neujahr
            pd.Timestamp(f'{simu_jahr}-05-01'),  # Tag der Arbeit
            pd.Timestamp(f'{simu_jahr}-10-03'),  # Tag der Deutschen Einheit
            pd.Timestamp(f'{simu_jahr}-12-25'),  # 1. Weihnachtstag
            pd.Timestamp(f'{simu_jahr}-12-26'),  # 2. Weihnachtstag
        ]
    
    # Bestimme Tagestyp (WT=Werktag, SA=Samstag, FT=Feiertag/Sonntag)
    def _get_day_type(row):
        date = row['Zeitpunkt'].date()
        is_holiday = pd.Timestamp(date) in feiertage
        is_sunday = row['weekday'] == 6
        
        # BDEW-Regel: 24.12. und 31.12. gelten als Samstag
        is_heiligabend_silvester = (row['month'] == 12) and (row['day'] in [24, 31])
        
        if is_holiday or is_sunday:
            return 'FT'
        elif row['weekday'] == 5 or is_heiligabend_silvester:
            return 'SA'
        else:
            return 'WT'
    
    df_result['day_type'] = df_result.apply(_get_day_type, axis=1)
    
    # Funktion zum Mappen von Lastprofilwerten auf Zeitpunkte
    def _map_load_profile(df_result: pd.DataFrame, df_profile: pd.DataFrame, sector_name: str) -> pd.Series:
        """Ordnet jedem Zeitpunkt den passenden Lastprofilwert zu (via merge)."""
        df_work = df_result.copy()
        df_work['hour'] = df_work['Zeitpunkt'].dt.hour
        df_work['minute'] = df_work['Zeitpunkt'].dt.minute
        
        df_prof = df_profile.copy()
        df_prof['hour'] = df_prof['timestamp'].dt.hour
        df_prof['minute'] = df_prof['timestamp'].dt.minute
        
        # Merge basierend auf Monat, Tagestyp, Stunde, Minute
        df_merged = df_work.merge(
            df_prof[['month', 'day_type', 'hour', 'minute', 'value_kWh']],
            on=['month', 'day_type', 'hour', 'minute'],
            how='left'
        )
        
        # Fehlende Werte mit 0 füllen
        if df_merged['value_kWh'].isna().sum() > 0:
            df_merged['value_kWh'].fillna(0.0, inplace=True)
        
        return df_merged['value_kWh']
    
    # Mappe Lastprofile auf Jahreskalender
    df_result['Haushalte_kWh'] = _map_load_profile(df_result, lastH, 'Haushalte')
    
    # Dynamisierung für Haushalte (H25) - Saisonaler Faktor
    # Formel: f(t) = -3,92E-10*t^4 + 3,20E-7*t^3 - 7,02E-5*t^2 + 2,10E-3*t + 1,24
    # t = Tag des Jahres (1-365/366)
    t = df_result['Zeitpunkt'].dt.dayofyear.astype(float)
    
    dyn_faktor = (
        -3.92e-10 * t**4 + 
        3.20e-7 * t**3 - 
        7.02e-5 * t**2 + 
        2.10e-3 * t + 
        1.24
    )
    
    dyn_faktor = dyn_faktor.round(4)
    df_result['Haushalte_kWh'] = (df_result['Haushalte_kWh'] * dyn_faktor).round(3)
    
    df_result['Gewerbe_kWh'] = _map_load_profile(df_result, lastG, 'Gewerbe')
    df_result['Landwirtschaft_kWh'] = _map_load_profile(df_result, lastL, 'Landwirtschaft')
    
    # Berechne Skalierungsfaktoren (Jahressumme Profil -> Zielwert)
    sum_H_kWh = df_result['Haushalte_kWh'].sum()
    sum_G_kWh = df_result['Gewerbe_kWh'].sum()
    sum_L_kWh = df_result['Landwirtschaft_kWh'].sum()
    
    # Konvertiere Zielwerte TWh -> kWh
    ziel_H_kWh = lastZielH * 1e9
    ziel_G_kWh = lastZielG * 1e9
    ziel_L_kWh = lastZielL * 1e9
    
    # Skalierungsfaktoren
    faktor_H = ziel_H_kWh / sum_H_kWh if sum_H_kWh > 0 else 0
    faktor_G = ziel_G_kWh / sum_G_kWh if sum_G_kWh > 0 else 0
    faktor_L = ziel_L_kWh / sum_L_kWh if sum_L_kWh > 0 else 0
    
    # Skaliere und konvertiere zu MWh
    df_result['Haushalte [MWh]'] = df_result['Haushalte_kWh'] * faktor_H / 1000.0
    df_result['Gewerbe [MWh]'] = df_result['Gewerbe_kWh'] * faktor_G / 1000.0
    df_result['Landwirtschaft [MWh]'] = df_result['Landwirtschaft_kWh'] * faktor_L / 1000.0
    
    # Gesamtverbrauch
    df_result['Gesamt [MWh]'] = (
        df_result['Haushalte [MWh]'] + 
        df_result['Gewerbe [MWh]'] + 
        df_result['Landwirtschaft [MWh]']
    )
    
    # Bereinige DataFrame - nur finale Spalten
    df_result = df_result[[
        'Zeitpunkt',
        'Haushalte [MWh]',
        'Gewerbe [MWh]',
        'Landwirtschaft [MWh]',
        'Gesamt [MWh]'
    ]]
    
    return df_result


def simulate_consumption_all(
    lastH: pd.DataFrame,
    lastG: pd.DataFrame,
    lastL: pd.DataFrame,
    wetter_df: Optional[pd.DataFrame],
    hp_profile_matrix: Optional[pd.DataFrame],
    lastZielH: float,
    lastZielG: float,
    lastZielL: float,
    anzahl_heatpumps: int,
    Q_th_a: float,
    COP_avg: float,
    dt: float,
    simu_jahr: int,
    debug: bool = False
) -> pd.DataFrame:
    """
    Simuliert den gesamten Energieverbrauch (BDEW + Wärmepumpen) für ein Jahr.
    
    Diese Funktion kombiniert:
    1. BDEW-Verbrauch (Haushalte, Gewerbe, Landwirtschaft)
    2. Wärmepumpen-Verbrauch (temperaturabhängig)
    
    Args:
        lastH: BDEW H25-Lastprofil (Haushalte)
        lastG: BDEW G25-Lastprofil (Gewerbe)
        lastL: BDEW L25-Lastprofil (Landwirtschaft)
        wetter_df: Wetterdaten für Wärmepumpen (stündliche Temperatur)
        hp_profile_matrix: Matrix mit WP-Lastprofilen (96 Viertelstunden × 34 Temp.-Bins)
        lastZielH: Ziel-Jahresverbrauch Haushalte [TWh]
        lastZielG: Ziel-Jahresverbrauch Gewerbe [TWh]
        lastZielL: Ziel-Jahresverbrauch Landwirtschaft [TWh]
        anzahl_heatpumps: Anzahl der Wärmepumpen
        Q_th_a: Jahreswärmebedarf pro WP [kWh]
        COP_avg: Durchschnittlicher COP der Wärmepumpen
        dt: Zeitintervall [h] (z.B. 0.25 für Viertelstunden)
        simu_jahr: Simulationsjahr (z.B. 2030 oder 2045)
        debug: Debug-Informationen ausgeben
        
    Returns:
        DataFrame mit Spalten:
        - Zeitpunkt, Haushalte [MWh], Gewerbe [MWh], Landwirtschaft [MWh]
        - Wärmepumpen [MWh], Gesamt [MWh]
    """
    
    # 1. Simuliere BDEW-Verbrauch
    df_bdew = simulate_consumption_BDEW(
        lastH, lastG, lastL,
        lastZielH, lastZielG, lastZielL,
        simu_jahr
    )
    
    # 2. Simuliere Wärmepumpen (optional)
    df_result = df_bdew.copy()
    
    if wetter_df is not None and hp_profile_matrix is not None and anzahl_heatpumps > 0:
        try:
            hp_sim = HeatPumpSimulation()
            df_heatpump = hp_sim.simulate(
                wetter_df,
                hp_profile_matrix,
                anzahl_heatpumps,
                Q_th_a,
                COP_avg,
                dt,
                simu_jahr,
                debug=debug
            )
            
            # Merge mit BDEW-Daten
            df_result = df_result.merge(df_heatpump, on='Zeitpunkt', how='outer')
            df_result['Wärmepumpen [MWh]'] = df_result['Wärmepumpen [MWh]'].fillna(0.0)
            
        except Exception as e:
            if debug:
                print(f"Warnung: Wärmepumpen-Simulation fehlgeschlagen: {e}")
            df_result['Wärmepumpen [MWh]'] = 0.0
    else:
        # Keine Wärmepumpen konfiguriert
        df_result['Wärmepumpen [MWh]'] = 0.0
    
    # 3. Berechne Gesamtverbrauch
    mwh_cols = [col for col in df_result.columns if '[MWh]' in col and col != 'Gesamt [MWh]']
    if mwh_cols:
        df_result['Gesamt [MWh]'] = df_result[mwh_cols].sum(axis=1)
    
    return df_result
