"""
Wärmepumpen-Simulationsmodul.
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_processing.simulation_logger import SimulationLogger


class HeatPumpSimulation:
    """
    Klasse zur Simulation des elektrischen Energiebedarfs von Wärmepumpen.
    """
    
    def __init__(self, logger: Optional[SimulationLogger] = None):
        """
        Initialisiert die Wärmepumpen-Simulation.
        
        Args:
            logger: Optional SimulationLogger für strukturiertes Logging
        """
        self.logger = logger
    
    def _prep_temp_df(self, df: pd.DataFrame, location: str = "AVERAGE") -> pd.DataFrame:
        """
        Bereitet das Wetter-DataFrame vor:
        - Konvertiert Zeitpunkt von 'DD.MM.YY HH:MM' zu DateTime
        - Wählt die angegebene Spalte aus
        - Interpoliert zu Viertelstunden
        
        Args:
            df: Wetterdaten-DataFrame
            location: Spaltenname für Temperaturdaten (z.B. "AVERAGE")
        
        Returns:
            Bereinigtes DataFrame mit Spalten ['Zeitpunkt', 'Temperatur [°C]']
        """
        df_local = df.copy()
        
        df_local['Zeitpunkt'] = pd.to_datetime(df_local['Zeitpunkt'], format='%d.%m.%y %H:%M')
        
        if location not in df_local.columns:
            raise ValueError(f"Spalte '{location}' nicht gefunden im Weather-DataFrame")
        
        df_local = df_local[['Zeitpunkt', location]].copy()
        df_local.columns = ['Zeitpunkt', 'Temperatur [°C]']
       
        df_local = df_local.dropna(subset=['Zeitpunkt', 'Temperatur [°C]'])
        
        # Sortiere nach Zeitpunkt
        df_local = df_local.sort_values('Zeitpunkt').reset_index(drop=True)
        
        return df_local
    
    def _get_hp_factor(
        self, 
        time_index: pd.Timestamp, 
        temp: float,
        hp_profile_matrix: pd.DataFrame
    ) -> float:
        """
        Gibt den Lastprofilfaktor für eine bestimmte Temperatur und Uhrzeit zurück.
        
        Args:
            time_index: DateTime Objekt mit Uhrzeit (0-23)
            temp: Außentemperatur in °C
            hp_profile_matrix: Matrix mit Lastprofilen
        
        Returns:
            Lastprofilfaktor
        
        Raises:
            KeyError: Wenn Spalte nicht in Matrix
        """
        t_lookup = int(round(temp))
        if t_lookup < -14:
            t_lookup = 'LOW'
        elif t_lookup >= 18:
            t_lookup = 'HIGH'
        
        t_col = str(t_lookup) if isinstance(t_lookup, int) else t_lookup
        
        row = hp_profile_matrix[
            (hp_profile_matrix['hour'] == time_index.hour) & 
            (hp_profile_matrix['minute'] == time_index.minute)
        ]
        
        if row.empty:
            raise KeyError(
                f"Matrix-Zeile nicht gefunden für Stunde={time_index.hour}, Minute={time_index.minute}"
            )
        
        if t_col not in row.columns:
            value_cols = [c for c in hp_profile_matrix.columns if c not in {'Zeitpunkt', 'hour', 'minute'}]
            raise KeyError(
                f"Temperaturspalte '{t_col}' nicht in Matrix gefunden. Verfügbare: {value_cols[:5]}"
            )
        
        factor = row.iloc[0][t_col]
        return float(factor)
    
    def simulate(
        self,
        weather_df: pd.DataFrame,
        hp_profile_matrix: pd.DataFrame,
        n_heatpumps: int,
        Q_th_a: float,
        COP_avg: float,
        dt: float,
        simu_jahr: int,
        debug: bool = False
    ) -> pd.DataFrame:
        """
        Simuliert den Energieverbrauch für Wärmepumpen basierend auf vorgegebenen Lastprofil und Parametern.
        
        Args:
            weather_df (pd.DataFrame): Wetterdaten mit Temperaturen
            hp_profile_matrix (pd.DataFrame): Matrix mit Lastprofilen für verschiedene Wetterlagen
            n_heatpumps (int): Anzahl der Wärmepumpen
            Q_th_a (float): Jahreswärmebedarf pro Wärmepumpe [kWh]
            COP_avg (float): Durchschnittlicher COP der Wärmepumpen
            dt (float): Zeitintervall in Stunden (z.B. 0.25 für 15 Minuten)
            simu_jahr (int): Simulationsjahr (z.B. 2030 oder 2045)
            debug (bool): Debug-Informationen ausgeben
        
        Returns:
            pd.DataFrame: DataFrame mit Spalten:
                - Zeitpunkt: DateTime-Index mit Viertelstunden-Auflösung
                - Wärmepumpen [MWh]: Verbrauch Wärmepumpen
        """
        if self.logger:
            self.logger.info(f"Simuliere {n_heatpumps:,} Wärmepumpen, "
                           f"Q_th={Q_th_a:.0f} kWh/WP, COP={COP_avg:.2f}")
        
        hp_profile_matrix.columns = hp_profile_matrix.columns.astype(str)
        
        hp_profile_matrix = hp_profile_matrix.copy()
        if 'Zeitpunkt' in hp_profile_matrix.columns:
            time_str = hp_profile_matrix['Zeitpunkt'].astype(str).str.split('-', n=1).str[0]
            parsed_time = pd.to_datetime(time_str, format='%H:%M', errors='coerce')
            hp_profile_matrix['hour'] = parsed_time.dt.hour
            hp_profile_matrix['minute'] = parsed_time.dt.minute
        else:
            hp_profile_matrix['hour'] = hp_profile_matrix.index
            hp_profile_matrix['minute'] = 0
        
        value_cols = [c for c in hp_profile_matrix.columns if c not in {'Zeitpunkt', 'hour', 'minute'}]
        for c in value_cols:
            hp_profile_matrix[c] = pd.to_numeric(
                hp_profile_matrix[c].astype(str).str.replace(',', '.'),
                errors='coerce'
            )
        
        df_weather = self._prep_temp_df(weather_df, location="AVERAGE")
        df_weather = df_weather.drop_duplicates(subset='Zeitpunkt', keep='first')
        df_weather = df_weather.sort_values('Zeitpunkt').reset_index(drop=True)
        
        weather_year = int(df_weather['Zeitpunkt'].dt.year.iloc[0])
        start = pd.Timestamp(f'{weather_year}-01-01 00:00')
        end = pd.Timestamp(f'{weather_year}-12-31 23:45')
        full_index = pd.date_range(start=start, end=end, freq='15min')
        df_full = pd.DataFrame({'Zeitpunkt': full_index})
        
        df_weather = df_full.merge(df_weather, on='Zeitpunkt', how='left')
        df_weather['Temperatur [°C]'] = df_weather['Temperatur [°C]'].ffill().bfill()
        
        df_weather['Zeitpunkt'] = df_weather['Zeitpunkt'].apply(lambda x: x.replace(year=simu_jahr))
        
        summe_lp_dt = 0.0
        for index, row in df_weather.iterrows():
            time = row['Zeitpunkt']
            temp = row['Temperatur [°C]']
            lp_faktor = self._get_hp_factor(time, temp, hp_profile_matrix)
            summe_lp_dt += lp_faktor * dt
        
        if summe_lp_dt <= 0:
            raise ValueError(f"Fehler: Normierungssumme summe_lp_dt={summe_lp_dt} ist nicht positiv!")
        
        f = Q_th_a / summe_lp_dt
        if debug:
            print(f"Normierungsfaktor f: {f:.2f} kW (Q_th_a={Q_th_a} kWh, summe={summe_lp_dt:.1f} h-äquiv)")
        
        ergebnisse = []
        
        for index, row in df_weather.iterrows():
            time = row['Zeitpunkt']
            temp = row['Temperatur [°C]']
            
            lp_wert = self._get_hp_factor(time, temp, hp_profile_matrix)
            
            p_th = lp_wert * f
            
            p_el = p_th / COP_avg
            
            p_el_ges = p_el * n_heatpumps
            
            ergebnisse.append({
                "Zeitpunkt": time,
                "Temperatur [°C]": temp,
                "P_th [kW]": p_th,
                "P_el [kW]": p_el,
                "P_el_ges [kW]": p_el_ges,
                "P_el_ges [MW]": p_el_ges / 1000
            })
        
        df_result = pd.DataFrame(ergebnisse)
        
        df_result['Wärmepumpen [MWh]'] = df_result['P_el_ges [MW]'] * dt
        
        df_result = df_result[['Zeitpunkt', 'Wärmepumpen [MWh]']]
        
        if debug:
            jahres_verbrauch_mwh = df_result['Wärmepumpen [MWh]'].sum()
            jahres_verbrauch_twh = jahres_verbrauch_mwh / 1e6
            target_twh = (Q_th_a * n_heatpumps) / (COP_avg * 1e6)
            print(f"Jahres-Stromverbrauch: {jahres_verbrauch_twh:.4f} TWh (Ziel: {target_twh:.4f} TWh)")
        
        return df_result
