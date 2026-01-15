"""
Unit Tests für die E-Mobilität Simulation.

Testet die Kernfunktionalität der E-Mobility-Simulation gemäß Excel-Logik:
- EV-Profil-Generierung (Phase A)
- Hauptsimulation (Phase B)
- Einheiten-Konvertierung
- Vorzeichen-Konventionen
- Vorlade-Priorisierung
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Füge source-code zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "source-code"))

from data_processing.e_mobility_simulation import (
    EVConfigParams,
    EVScenarioParams,
    generate_ev_profile,
    simulate_emobility_fleet,
    validate_ev_results,
    _time_str_to_decimal,
    _is_between_times_over_midnight
)


class TestTimeConversion:
    """Tests für Zeit-Konvertierung."""
    
    def test_time_str_to_decimal_morning(self):
        """07:30 sollte 0.3125 ergeben."""
        result = _time_str_to_decimal("07:30")
        assert abs(result - 0.3125) < 1e-6
    
    def test_time_str_to_decimal_evening(self):
        """18:00 sollte 0.75 ergeben."""
        result = _time_str_to_decimal("18:00")
        assert abs(result - 0.75) < 1e-6
    
    def test_time_str_to_decimal_midnight(self):
        """00:00 sollte 0.0 ergeben."""
        result = _time_str_to_decimal("00:00")
        assert abs(result - 0.0) < 1e-6
    
    def test_is_between_times_normal(self):
        """Test für normales Zeitintervall (08:00 - 18:00)."""
        t_start = 8.0 / 24.0
        t_end = 18.0 / 24.0
        
        # 12:00 sollte drin sein
        assert _is_between_times_over_midnight(12.0 / 24.0, t_start, t_end) == True
        # 20:00 sollte nicht drin sein
        assert _is_between_times_over_midnight(20.0 / 24.0, t_start, t_end) == False
    
    def test_is_between_times_overnight(self):
        """Test für Zeitintervall über Mitternacht (18:00 - 07:30)."""
        t_start = 18.0 / 24.0
        t_end = 7.5 / 24.0
        
        # 22:00 sollte drin sein
        assert _is_between_times_over_midnight(22.0 / 24.0, t_start, t_end) == True
        # 02:00 sollte drin sein
        assert _is_between_times_over_midnight(2.0 / 24.0, t_start, t_end) == True
        # 12:00 sollte nicht drin sein
        assert _is_between_times_over_midnight(12.0 / 24.0, t_start, t_end) == False


class TestEVProfileGeneration:
    """Tests für die EV-Profil-Generierung (Phase A)."""
    
    @pytest.fixture
    def sample_timestamps(self):
        """Erstellt 96 Zeitstempel für einen Tag (15-Minuten-Intervalle)."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        return pd.Series(timestamps)
    
    @pytest.fixture
    def default_params(self):
        """Standard-Parameter für Tests."""
        return (
            EVScenarioParams(),
            EVConfigParams()
        )
    
    def test_profile_length(self, sample_timestamps, default_params):
        """Profil sollte gleiche Länge wie Timestamps haben."""
        scenario_params, config_params = default_params
        profile = generate_ev_profile(sample_timestamps, scenario_params, config_params)
        assert len(profile) == 96
    
    def test_plug_share_overnight(self, sample_timestamps, default_params):
        """plug_share sollte nachts (18:00-07:30) maximal sein."""
        scenario_params, config_params = default_params
        profile = generate_ev_profile(sample_timestamps, scenario_params, config_params)
        
        # 22:00 Uhr = Index 88
        assert profile.loc[88, 'plug_share'] == scenario_params.plug_share_max
        
        # 02:00 Uhr = Index 8
        assert profile.loc[8, 'plug_share'] == scenario_params.plug_share_max
    
    def test_plug_share_daytime(self, sample_timestamps, default_params):
        """plug_share sollte tagsüber (07:30-18:00) reduziert sein."""
        scenario_params, config_params = default_params
        profile = generate_ev_profile(sample_timestamps, scenario_params, config_params)
        
        # 12:00 Uhr = Index 48
        expected_min = 0.1 * scenario_params.plug_share_max
        assert profile.loc[48, 'plug_share'] == expected_min
    
    def test_preload_flag_before_departure(self, sample_timestamps, default_params):
        """preload_flag sollte 2h vor Abfahrt (05:30-07:30) gesetzt sein."""
        scenario_params, config_params = default_params
        profile = generate_ev_profile(sample_timestamps, scenario_params, config_params)
        
        # 06:00 Uhr = Index 24
        assert profile.loc[24, 'preload_flag'] == 1
        
        # 04:00 Uhr = Index 16 (vor Vorladezeit)
        assert profile.loc[16, 'preload_flag'] == 0
    
    def test_soc_target_during_preload(self, sample_timestamps, default_params):
        """soc_target sollte nur während Vorladezeit gesetzt sein."""
        scenario_params, config_params = default_params
        profile = generate_ev_profile(sample_timestamps, scenario_params, config_params)
        
        # Während Vorladezeit: soc_target = SOC_target_depart
        preload_indices = profile[profile['preload_flag'] == 1].index
        for idx in preload_indices:
            assert profile.loc[idx, 'soc_target_share'] == scenario_params.SOC_target_depart
        
        # Außerhalb Vorladezeit: soc_target = NaN
        non_preload_indices = profile[profile['preload_flag'] == 0].index
        assert profile.loc[non_preload_indices, 'soc_target_share'].isna().all()


class TestMainSimulation:
    """Tests für die Hauptsimulation (Phase B)."""
    
    @pytest.fixture
    def sample_balance_df(self):
        """Erstellt ein Test-Balance-DataFrame für einen Tag."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        
        # Konstante Residuallast von 0 (neutral)
        df = pd.DataFrame({
            'Zeitpunkt': timestamps,
            'Rest Bilanz [MWh]': np.zeros(96)
        })
        return df
    
    @pytest.fixture
    def surplus_balance_df(self):
        """Erstellt DataFrame mit konstantem Überschuss (sollte Laden auslösen)."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        
        # -300 MW Überschuss (in MWh: -300 * 0.25 = -75 MWh pro Intervall)
        df = pd.DataFrame({
            'Zeitpunkt': timestamps,
            'Rest Bilanz [MWh]': np.full(96, -75.0)
        })
        return df
    
    @pytest.fixture
    def deficit_balance_df(self):
        """Erstellt DataFrame mit konstantem Defizit (sollte Entladen auslösen)."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        
        # +300 MW Defizit (in MWh: +300 * 0.25 = +75 MWh pro Intervall)
        df = pd.DataFrame({
            'Zeitpunkt': timestamps,
            'Rest Bilanz [MWh]': np.full(96, 75.0)
        })
        return df
    
    def test_simulation_output_columns(self, sample_balance_df):
        """Simulation sollte alle erwarteten Spalten erzeugen."""
        result = simulate_emobility_fleet(sample_balance_df)
        
        expected_columns = [
            'EMobility SOC [MWh]',
            'EMobility Charge [MWh]',
            'EMobility Discharge [MWh]',
            'EMobility Drive [MWh]',
            'EMobility Power [MW]',
            'Rest Bilanz [MWh]'
        ]
        
        for col in expected_columns:
            assert col in result.columns, f"Spalte {col} fehlt"
    
    def test_soc_within_bounds(self, sample_balance_df):
        """SOC sollte immer zwischen 0 und Kapazität bleiben."""
        scenario_params = EVScenarioParams(N_cars=1_000_000)
        result = simulate_emobility_fleet(sample_balance_df, scenario_params=scenario_params)
        
        capacity_mwh = scenario_params.s_EV * scenario_params.N_cars * scenario_params.E_batt_car / 1000.0
        
        assert (result['EMobility SOC [MWh]'] >= -1e-6).all(), "SOC unter 0"
        assert (result['EMobility SOC [MWh]'] <= capacity_mwh * 1.001).all(), "SOC über Kapazität"
    
    def test_charging_on_surplus(self, surplus_balance_df):
        """Bei Überschuss sollte geladen werden (negativ)."""
        scenario_params = EVScenarioParams(
            thr_surplus=200_000.0,
            thr_deficit=200_000.0
        )
        result = simulate_emobility_fleet(surplus_balance_df, scenario_params=scenario_params)
        
        # Geladene Energie sollte > 0 sein
        total_charged = result['EMobility Charge [MWh]'].sum()
        assert total_charged > 0, "Es sollte bei Überschuss geladen werden"
    
    def test_discharging_on_deficit(self, deficit_balance_df):
        """Bei Defizit sollte entladen werden (positiv)."""
        scenario_params = EVScenarioParams(
            thr_surplus=200_000.0,
            thr_deficit=200_000.0,
            SOC_min_day=0.1,  # Niedriger Min-SOC für mehr Entladekapazität
            SOC_min_night=0.1
        )
        config_params = EVConfigParams(SOC0=0.9)  # Hoher Start-SOC
        
        result = simulate_emobility_fleet(
            deficit_balance_df, 
            scenario_params=scenario_params,
            config_params=config_params
        )
        
        # Entladene Energie sollte > 0 sein
        total_discharged = result['EMobility Discharge [MWh]'].sum()
        assert total_discharged > 0, "Es sollte bei Defizit entladen werden"
    
    def test_driving_consumption(self, sample_balance_df):
        """Fahrverbrauch sollte immer positiv sein."""
        result = simulate_emobility_fleet(sample_balance_df)
        
        total_drive = result['EMobility Drive [MWh]'].sum()
        assert total_drive > 0, "Fahrverbrauch sollte > 0 sein"


class TestPreloadPriority:
    """Tests für die Vorlade-Priorisierung."""
    
    @pytest.fixture
    def morning_deficit_df(self):
        """DataFrame mit Defizit am Morgen (05:00-08:00)."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        
        residual = []
        for ts in timestamps:
            if 5 <= ts.hour < 8:
                # Defizit am Morgen (normalerweise würde entladen)
                residual.append(75.0)
            else:
                residual.append(0.0)
        
        df = pd.DataFrame({
            'Zeitpunkt': timestamps,
            'Rest Bilanz [MWh]': residual
        })
        return df
    
    def test_preload_overrides_deficit(self, morning_deficit_df):
        """Vorladen sollte Priorität vor Entladen haben."""
        scenario_params = EVScenarioParams(
            t_depart="07:30",
            SOC_target_depart=0.8
        )
        config_params = EVConfigParams(SOC0=0.3)  # Niedriger Start-SOC
        
        result = simulate_emobility_fleet(
            morning_deficit_df,
            scenario_params=scenario_params,
            config_params=config_params
        )
        
        # Während der Vorladezeit (05:30-07:30) sollte trotz Defizit geladen werden
        preload_start = datetime(2030, 6, 15, 5, 30)
        preload_end = datetime(2030, 6, 15, 7, 30)
        
        preload_mask = (
            (result['Zeitpunkt'] >= preload_start) & 
            (result['Zeitpunkt'] < preload_end)
        )
        
        preload_rows = result[preload_mask]
        
        # Power sollte negativ sein (Laden) oder 0, aber nicht positiv (Entladen)
        # Da Vorladen Priorität hat
        charged_during_preload = preload_rows['EMobility Charge [MWh]'].sum()
        discharged_during_preload = preload_rows['EMobility Discharge [MWh]'].sum()
        
        assert charged_during_preload > discharged_during_preload, \
            "Vorladen sollte Priorität vor Entladen haben"


class TestValidation:
    """Tests für die Validierungsfunktion."""
    
    def test_validation_passes_on_valid_data(self):
        """Validierung sollte bei korrekten Daten bestehen."""
        start = datetime(2030, 6, 15, 0, 0)
        timestamps = [start + timedelta(minutes=15*i) for i in range(96)]
        
        df = pd.DataFrame({
            'Zeitpunkt': timestamps,
            'Rest Bilanz [MWh]': np.zeros(96)
        })
        
        result = simulate_emobility_fleet(df)
        
        scenario_params = EVScenarioParams()
        n_ev = scenario_params.s_EV * scenario_params.N_cars
        capacity_mwh = n_ev * scenario_params.E_batt_car / 1000.0
        
        checks = validate_ev_results(result, capacity_mwh)
        
        assert all(checks.values()), "Alle Validierungen sollten bestehen"


# Pytest Entry Point
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
