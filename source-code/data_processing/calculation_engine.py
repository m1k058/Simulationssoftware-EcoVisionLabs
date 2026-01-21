"""
Berechnungs-Engine für Simulation.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class CalculationEngine:
    """
    Zentrale Berechnungs-Engine mit Multi-Modus Support.
    
    Unterstützte Modi:
    - "normal": Standard Python (langsam, aber stabil)
    - "cpu_optimized": Numba JIT mit Parallelisierung
    
    Usage:
        engine = CalculationEngine(mode="cpu_optimized")
        results = engine.calculate_heatpump_load(
            weather_df, hp_profile_matrix, n_heatpumps, Q_th_a, COP_avg, dt, simu_jahr
        )
    """
    
    VALID_MODES = ["normal", "cpu_optimized"]
    MODE_DISPLAY_NAMES = {
        "normal": "Normal",
        "cpu_optimized": "Numba",
    }
    
    def __init__(self, mode: str = "cpu_optimized"):
        """
        Initialisiert die Calculation Engine.
        
        Args:
            mode: Berechnungsmodus ("normal", "cpu_optimized")
        
        Raises:
            ValueError: Bei ungültigem Modus
            ImportError: Bei fehlenden Dependencies
        """
        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Ungültiger Modus '{mode}'. Erlaubt: {self.VALID_MODES}"
            )
        
        self.mode = mode
        self.mode_display = self.MODE_DISPLAY_NAMES[mode]
        
        # Validiere Dependencies
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """
        Prüft ob notwendige Pakete installiert sind.
        
        Raises:
            ImportError: Bei fehlenden Paketen mit Installations-Anweisung
        """
        if self.mode == "cpu_optimized":
            try:
                import numba
                from numba import jit, prange
                self.numba = numba
                self.jit = jit
                self.prange = prange
            except ImportError:
                raise ImportError(
                    "Numba ist nicht installiert."
                )
    
    def calculate_heatpump_load(
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
        Berechnet Wärmepumpen-Last mit gewähltem Modus.
        
        Args:
            weather_df: Wetterdaten mit Zeitpunkt und Temperatur
            hp_profile_matrix: Lastprofilmatrix (Stunde/Minute vs. Temperatur)
            n_heatpumps: Anzahl Wärmepumpen
            Q_th_a: Jahreswärmebedarf pro WP [kWh]
            COP_avg: Durchschnittlicher COP
            dt: Zeitschritt [h] (z.B. 0.25 für 15min)
            simu_jahr: Simulationsjahr
            debug: Debug-Ausgaben
        
        Returns:
            DataFrame mit Spalten ['Zeitpunkt', 'Wärmepumpen [MWh]']
        """
        
        if self.mode == "normal":
            df_result = self._calculate_normal(
                weather_df, hp_profile_matrix, n_heatpumps, 
                Q_th_a, COP_avg, dt, simu_jahr, debug
            )
        elif self.mode == "cpu_optimized":
            df_result = self._calculate_numba(
                weather_df, hp_profile_matrix, n_heatpumps,
                Q_th_a, COP_avg, dt, simu_jahr, debug
            )
        else:
            raise ValueError(f"Unbekannter Modus: {self.mode}")
        
        return df_result
    
    def _calculate_normal(
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
        Normale Berechnung
        
        Returns:
            DataFrame mit Spalten ['Zeitpunkt', 'Wärmepumpen [MWh]']
        """
        df_weather = self._prep_weather_data_simple(weather_df, simu_jahr)
        
        hp_matrix_prepared = self._prep_hp_profile_matrix(hp_profile_matrix)
        
        summe_lp_dt = 0.0
        for index, row in df_weather.iterrows():
            time = row['Zeitpunkt']
            temp = row['Temperatur [°C]']
            lp_faktor = self._get_hp_factor_simple(time, temp, hp_matrix_prepared)
            summe_lp_dt += lp_faktor * dt
        
        if summe_lp_dt <= 0:
            raise ValueError(f"Normierungssumme summe_lp_dt={summe_lp_dt} ist nicht positiv!")
        
        f = Q_th_a / summe_lp_dt
        
        if debug:
            print(f"[Normal] Normierungsfaktor f: {f:.2f} kW (Q_th_a={Q_th_a} kWh, summe={summe_lp_dt:.1f} h-äquiv)")
        
        results = []
        for index, row in df_weather.iterrows():
            time = row['Zeitpunkt']
            temp = row['Temperatur [°C]']
            
            lp_faktor = self._get_hp_factor_simple(time, temp, hp_matrix_prepared)
            p_th = lp_faktor * f 
            p_el = p_th / COP_avg  
            p_el_ges = p_el * n_heatpumps 
            p_el_ges_mw = p_el_ges / 1000.0
            energy_mwh = p_el_ges_mw * dt 
            
            results.append({
                'Zeitpunkt': time,
                'Wärmepumpen [MWh]': energy_mwh
            })
        
        df_result = pd.DataFrame(results)
        
        if debug:
            jahres_verbrauch_twh = df_result['Wärmepumpen [MWh]'].sum() / 1e6
            target_twh = (Q_th_a * n_heatpumps) / (COP_avg * 1e6)
            print(f"[Normal] Jahres-Stromverbrauch: {jahres_verbrauch_twh:.4f} TWh (Ziel: {target_twh:.4f} TWh)")
        
        return df_result
    
    def _prep_weather_data_simple(self, weather_df: pd.DataFrame, simu_jahr: int) -> pd.DataFrame:
        """
        Bereitet Wetterdaten vor - MIT vollständiger Jahr-Interpolation.
        
        Für Produktionsdaten: Interpoliert stündliche Daten auf 15-Minuten für ganzes Jahr.
        
        Returns:
            DataFrame mit Spalten ['Zeitpunkt', 'Temperatur [°C]'] auf 15-Min Basis
        """
        df_local = weather_df.copy()
        
        # Konvertiere Zeitpunkt
        if not pd.api.types.is_datetime64_any_dtype(df_local['Zeitpunkt']):
            df_local['Zeitpunkt'] = pd.to_datetime(df_local['Zeitpunkt'], format='%d.%m.%y %H:%M')
        
        location = "AVERAGE"
        if location not in df_local.columns:
            raise ValueError(f"Spalte '{location}' nicht gefunden")
        
        df_local = df_local[['Zeitpunkt', location]].copy()
        df_local.columns = ['Zeitpunkt', 'Temperatur [°C]']
        
        # Entferne Zeilen mit NaT oder NaN
        df_local = df_local.dropna(subset=['Zeitpunkt', 'Temperatur [°C]'])
        df_local = df_local.sort_values('Zeitpunkt').reset_index(drop=True)
        
        weather_year = int(df_local['Zeitpunkt'].dt.year.iloc[0])
        start = pd.Timestamp(f'{weather_year}-01-01 00:00')
        end = pd.Timestamp(f'{weather_year}-12-31 23:45')
        full_index = pd.date_range(start=start, end=end, freq='15min')
        df_full = pd.DataFrame({'Zeitpunkt': full_index})
        
        df_local = df_full.merge(df_local, on='Zeitpunkt', how='left')
        df_local['Temperatur [°C]'] = df_local['Temperatur [°C]'].ffill().bfill()
        
        df_local['Zeitpunkt'] = df_local['Zeitpunkt'].apply(lambda x: x.replace(year=simu_jahr))
        
        return df_local
    
    def _get_hp_factor_simple(
        self,
        time_index: pd.Timestamp,
        temp: float,
        hp_matrix: pd.DataFrame
    ) -> float:
        """
        Gibt Lastprofilfaktor für Temperatur und Uhrzeit zurück.
        
        Args:
            time_index: DateTime mit Uhrzeit
            temp: Außentemperatur [°C]
            hp_matrix: Vorbereitete Matrix mit hour/minute Spalten
        
        Returns:
            Lastprofilfaktor
        """
        # Temperatur-Mapping
        t_rounded = int(round(temp))
        if t_rounded < -14:
            t_col = 'LOW'
        elif t_rounded >= 18:
            t_col = 'HIGH'
        else:
            t_col = str(t_rounded)
        
        # Finde Zeile
        row = hp_matrix[
            (hp_matrix['hour'] == time_index.hour) & 
            (hp_matrix['minute'] == time_index.minute)
        ]
        
        if row.empty:
            raise KeyError(f"Matrix-Zeile nicht gefunden für Stunde={time_index.hour}, Minute={time_index.minute}")
        
        if t_col not in row.columns:
            raise KeyError(f"Temperaturspalte '{t_col}' nicht in Matrix gefunden")
        
        return float(row.iloc[0][t_col])
    
    def _calculate_numba(
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
        Numba-optimierte Berechnung
        
        Returns:
            DataFrame mit Spalten ['Zeitpunkt', 'Wärmepumpen [MWh]']
        """
        df_weather = self._prep_weather_data(weather_df, simu_jahr)
        
        hp_matrix_prepared = self._prep_hp_profile_matrix(hp_profile_matrix)
        
        temps = df_weather['Temperatur [°C]'].values
        hours = df_weather['Zeitpunkt'].dt.hour.values
        minutes = df_weather['Zeitpunkt'].dt.minute.values
        
        profile_array, _ = self._convert_profile_to_array(hp_matrix_prepared)
        
        hp_factors = _calculate_hp_factors_numba(
            temps, hours, minutes, profile_array
        )
        summe_lp_dt = _numba_sum_profile(hp_factors, dt)
        
        if summe_lp_dt <= 0:
            raise ValueError(f"Normierungssumme summe_lp_dt={summe_lp_dt} ist nicht positiv!")
        
        f = Q_th_a / summe_lp_dt
        
        if debug:
            print(f"[Numba] Normierungsfaktor f: {f:.2f} kW (Q_th_a={Q_th_a} kWh, summe={summe_lp_dt:.1f} h-äquiv)")
        
        power_mw = _numba_calculate_power(hp_factors, f, COP_avg, n_heatpumps)
        energy_mwh = power_mw * dt
        
        df_result = pd.DataFrame({
            'Zeitpunkt': df_weather['Zeitpunkt'],
            'Wärmepumpen [MWh]': energy_mwh
        })
        
        if debug:
            jahres_verbrauch_twh = energy_mwh.sum() / 1e6
            target_twh = (Q_th_a * n_heatpumps) / (COP_avg * 1e6)
            print(f"[Numba] Jahres-Stromverbrauch: {jahres_verbrauch_twh:.4f} TWh (Ziel: {target_twh:.4f} TWh)")
        
        return df_result
    
    def _prep_weather_data(self, weather_df: pd.DataFrame, simu_jahr: int) -> pd.DataFrame:
        """
        Bereitet Wetterdaten vor - mit vollständiger Jahr-Interpolation.
        
        Für Produktionsdaten: Interpoliert stündliche Daten auf 15-Minuten für ganzes Jahr.
        
        Returns:
            DataFrame mit Spalten ['Zeitpunkt', 'Temperatur [°C]'] auf 15-Min Basis
        """
        df_local = weather_df.copy()
        
        # Konvertiere Zeitpunkt falls nötig
        if not pd.api.types.is_datetime64_any_dtype(df_local['Zeitpunkt']):
            df_local['Zeitpunkt'] = pd.to_datetime(df_local['Zeitpunkt'], format='%d.%m.%y %H:%M')
        
        # Wähle AVERAGE Spalte
        location = "AVERAGE"
        if location not in df_local.columns:
            raise ValueError(f"Spalte '{location}' nicht gefunden")
        
        df_local = df_local[['Zeitpunkt', location]].copy()
        df_local.columns = ['Zeitpunkt', 'Temperatur [°C]']
        
        # Entferne Zeilen mit NaT oder NaN
        df_local = df_local.dropna(subset=['Zeitpunkt', 'Temperatur [°C]'])
        df_local = df_local.sort_values('Zeitpunkt').reset_index(drop=True)
        
        weather_year = int(df_local['Zeitpunkt'].dt.year.iloc[0])
        start = pd.Timestamp(f'{weather_year}-01-01 00:00')
        end = pd.Timestamp(f'{weather_year}-12-31 23:45')
        full_index = pd.date_range(start=start, end=end, freq='15min')
        df_full = pd.DataFrame({'Zeitpunkt': full_index})
        
        df_local = df_full.merge(df_local, on='Zeitpunkt', how='left')
        df_local['Temperatur [°C]'] = df_local['Temperatur [°C]'].ffill().bfill()
        
        df_local['Zeitpunkt'] = df_local['Zeitpunkt'].apply(lambda x: x.replace(year=simu_jahr))
        
        return df_local
    
    def _prep_hp_profile_matrix(self, hp_profile_matrix: pd.DataFrame) -> pd.DataFrame:
        """
        Bereitet HP-Profil-Matrix vor - analog zu HeatPumpSimulation.simulate.
        
        Returns:
            DataFrame mit hour/minute Spalten und numerischen Temperatur-Spalten
        """
        hp_matrix = hp_profile_matrix.copy()
        hp_matrix.columns = hp_matrix.columns.astype(str)
        
        if 'Zeitpunkt' in hp_matrix.columns:
            time_str = hp_matrix['Zeitpunkt'].astype(str).str.split('-', n=1).str[0]
            parsed_time = pd.to_datetime(time_str, format='%H:%M', errors='coerce')
            hp_matrix['hour'] = parsed_time.dt.hour
            hp_matrix['minute'] = parsed_time.dt.minute
        else:
            hp_matrix['hour'] = hp_matrix.index
            hp_matrix['minute'] = 0
        
        value_cols = [c for c in hp_matrix.columns if c not in {'Zeitpunkt', 'hour', 'minute'}]
        for c in value_cols:
            hp_matrix[c] = pd.to_numeric(
                hp_matrix[c].astype(str).str.replace(',', '.'),
                errors='coerce'
            )
        
        return hp_matrix
    
    def _convert_profile_to_array(self, hp_matrix: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Konvertiert Profil-Matrix zu NumPy Array für Numba.
        
        Erwartet Spalten-Reihenfolge: LOW, -14, -13, ..., 17, HIGH
        
        Returns:
            (profile_array, temp_columns):
                - profile_array: shape (96, 34) mit Profilwerten
                - temp_columns: Dummy (für Kompatibilität)
        """
        hp_matrix = hp_matrix.sort_values(['hour', 'minute']).reset_index(drop=True)
        
        # Temperatur-Spalten
        expected_cols = ['LOW'] + [str(i) for i in range(-14, 18)] + ['HIGH']
        
        available_temp_cols = [c for c in hp_matrix.columns if c not in {'Zeitpunkt', 'hour', 'minute'}]
        
        final_cols = []
        for col in expected_cols:
            if col in available_temp_cols:
                final_cols.append(col)
            else:
                hp_matrix[col] = 0.0
                final_cols.append(col)
        
        profile_array = hp_matrix[final_cols].values
        
        return profile_array, np.array(final_cols)


try:
    from numba import jit, prange
    
    @jit(nopython=True, parallel=True)
    def _calculate_hp_factors_numba(
        temps: np.ndarray,
        hours: np.ndarray,
        minutes: np.ndarray,
        profile_array: np.ndarray
    ) -> np.ndarray:
        """
        Berechnet HP-Faktoren mit Numba JIT - parallelisiert.
        
        Args:
            temps: Temperaturen (n,)
            hours: Stunden 0-23 (n,)
            minutes: Minuten 0/15/30/45 (n,)
            profile_array: (96, 34) - Spalten: LOW, -14..17, HIGH
        
        Returns:
            HP-Faktoren (n,)
        """
        n = len(temps)
        result = np.zeros(n)
        
        for i in prange(n):
            temp = temps[i]
            hour_val = hours[i]
            minute_val = minutes[i]
            
            hour_int = int(hour_val)
            minute_int = int(minute_val)
            
            row_idx = hour_int * 4 + (minute_int // 15)
            
            t_rounded = int(round(temp))
            
            if t_rounded < -14:
                col_idx = 0
            elif t_rounded >= 18:
                col_idx = 33
            else:
                col_idx = t_rounded + 15
            
            result[i] = profile_array[row_idx, col_idx]
        
        return result
    
    
    @jit(nopython=True)
    def _numba_sum_profile(factors: np.ndarray, dt: float) -> float:
        """Summiere Profilfaktoren * dt."""
        return np.sum(factors) * dt
    
    
    @jit(nopython=True, parallel=True)
    def _numba_calculate_power(
        factors: np.ndarray,
        f: float,
        COP_avg: float,
        n_heatpumps: int
    ) -> np.ndarray:
        """
        Berechnet elektrische Leistung in MW.
        
        Args:
            factors: HP-Faktoren (n,)
            f: Skalierungsfaktor [kW]
            COP_avg: COP
            n_heatpumps: Anzahl WP
        
        Returns:
            Leistung in MW (n,)
        """
        n = len(factors)
        result = np.zeros(n)
        
        for i in prange(n):
            p_th = factors[i] * f  # kW thermisch
            p_el = p_th / COP_avg  # kW elektrisch
            p_el_ges = p_el * n_heatpumps  # kW gesamt
            result[i] = p_el_ges / 1000.0  # MW
        
        return result

except ImportError:
    def _calculate_hp_factors_numba(*args, **kwargs):
        raise ImportError("Numba nicht installiert. Bitte 'pip install numba' ausführen.")
    
    def _numba_sum_profile(*args, **kwargs):
        raise ImportError("Numba nicht installiert. Bitte 'pip install numba' ausführen.")
    
    def _numba_calculate_power(*args, **kwargs):
        raise ImportError("Numba nicht installiert. Bitte 'pip install numba' ausführen.")
