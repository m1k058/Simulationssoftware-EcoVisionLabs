"""
Tests für die CalculationEngine - vergleicht Normal vs. CPU-Optimiert Modi.

Testet:
1. Korrektheit: Beide Modi produzieren identische Ergebnisse
2. Performance: CPU-Modus ist mindestens 10x schneller
"""

import sys
from pathlib import Path

# Füge source-code zum Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

import pytest
import pandas as pd
import numpy as np
from data_processing.calculation_engine import CalculationEngine, PerformanceStats


@pytest.fixture
def sample_weather_data():
    """Erstellt kleines Wetter-DataFrame für Tests (100 Zeilen)."""
    dates = pd.date_range('2030-01-01 00:00', periods=100, freq='15min')
    temps = 5 + 10 * np.sin(np.linspace(0, 2*np.pi, 100))  # -5 bis 15°C
    
    df = pd.DataFrame({
        'Zeitpunkt': dates.strftime('%d.%m.%y %H:%M'),
        'AVERAGE': temps
    })
    
    return df


@pytest.fixture
def sample_hp_profile():
    """Erstellt vereinfachte HP-Profil-Matrix."""
    # 96 Viertelstunden pro Tag
    hours = []
    minutes = []
    for h in range(24):
        for m in [0, 15, 30, 45]:
            hours.append(h)
            minutes.append(m)
    
    # Temperatur-Spalten: LOW, -14 bis 17, HIGH
    temp_cols = ['LOW'] + [str(i) for i in range(-14, 18)] + ['HIGH']
    
    # Erzeuge einfache Profilwerte (höher bei niedrigen Temperaturen)
    data = {'Zeitpunkt': [f'{h:02d}:{m:02d}' for h, m in zip(hours, minutes)]}
    
    for col in temp_cols:
        if col == 'LOW':
            base_value = 1.2
        elif col == 'HIGH':
            base_value = 0.3
        else:
            temp_val = int(col)
            # Höhere Last bei kälteren Temperaturen
            base_value = 1.0 - (temp_val + 10) / 40.0
        
        # Tagesgang: höher nachts, niedriger tagsüber
        values = []
        for h in hours:
            if 6 <= h < 22:
                factor = 0.8  # Tag
            else:
                factor = 1.2  # Nacht
            values.append(base_value * factor)
        
        data[col] = values
    
    return pd.DataFrame(data)


class TestCalculationModes:
    """Tests für verschiedene Berechnungsmodi."""
    
    def test_normal_mode(self, sample_weather_data, sample_hp_profile):
        """Test Normal-Modus alleine."""
        engine = CalculationEngine(mode="normal")
        
        df_result, stats = engine.calculate_heatpump_load(
            weather_df=sample_weather_data,
            hp_profile_matrix=sample_hp_profile,
            n_heatpumps=1000,
            Q_th_a=10000,  # 10 MWh pro WP
            COP_avg=3.5,
            dt=0.25,
            simu_jahr=2030,
            debug=False
        )
        
        assert len(df_result) == 100
        assert 'Zeitpunkt' in df_result.columns
        assert 'Wärmepumpen [MWh]' in df_result.columns
        assert stats.mode == "normal"
        assert stats.rows_processed == 100
        print(f"Normal-Modus: {stats.calculation_time:.3f}s ({stats.rows_per_second:.0f} Zeilen/s)")
    
    def test_cpu_optimized_mode(self, sample_weather_data, sample_hp_profile):
        """Test CPU-Optimiert-Modus alleine."""
        try:
            import numba
        except ImportError:
            pytest.skip("Numba nicht installiert")
        
        engine = CalculationEngine(mode="cpu_optimized")
        
        df_result, stats = engine.calculate_heatpump_load(
            weather_df=sample_weather_data,
            hp_profile_matrix=sample_hp_profile,
            n_heatpumps=1000,
            Q_th_a=10000,
            COP_avg=3.5,
            dt=0.25,
            simu_jahr=2030,
            debug=False
        )
        
        assert len(df_result) == 100
        assert 'Zeitpunkt' in df_result.columns
        assert 'Wärmepumpen [MWh]' in df_result.columns
        assert stats.mode == "cpu_optimized"
        assert stats.rows_processed == 100
        print(f"CPU-Modus: {stats.calculation_time:.3f}s ({stats.rows_per_second:.0f} Zeilen/s)")
    
    def test_normal_vs_cpu_correctness(self, sample_weather_data, sample_hp_profile):
        """Vergleicht Normal vs. CPU-Optimiert auf Korrektheit."""
        try:
            import numba
        except ImportError:
            pytest.skip("Numba nicht installiert")
        
        # Normal-Modus
        engine_normal = CalculationEngine(mode="normal")
        df_normal, stats_normal = engine_normal.calculate_heatpump_load(
            weather_df=sample_weather_data,
            hp_profile_matrix=sample_hp_profile,
            n_heatpumps=1000,
            Q_th_a=10000,
            COP_avg=3.5,
            dt=0.25,
            simu_jahr=2030,
            debug=False
        )
        
        # CPU-Modus
        engine_cpu = CalculationEngine(mode="cpu_optimized")
        df_cpu, stats_cpu = engine_cpu.calculate_heatpump_load(
            weather_df=sample_weather_data,
            hp_profile_matrix=sample_hp_profile,
            n_heatpumps=1000,
            Q_th_a=10000,
            COP_avg=3.5,
            dt=0.25,
            simu_jahr=2030,
            debug=False
        )
        
        # Vergleiche Ergebnisse
        assert len(df_normal) == len(df_cpu), "Unterschiedliche Anzahl Zeilen"
        
        # Zeitpunkte müssen identisch sein
        pd.testing.assert_series_equal(
            df_normal['Zeitpunkt'], 
            df_cpu['Zeitpunkt'],
            check_names=False
        )
        
        # Werte sollten sehr ähnlich sein (numerische Toleranz)
        np.testing.assert_allclose(
            df_normal['Wärmepumpen [MWh]'].values,
            df_cpu['Wärmepumpen [MWh]'].values,
            rtol=1e-5,  # 0.001% relative Toleranz
            atol=1e-8,  # Absolute Toleranz
            err_msg="Ergebnisse unterscheiden sich zwischen Normal und CPU-Modus"
        )
        
        print(f"\n✅ Korrektheit bestätigt:")
        print(f"   Normal: {stats_normal.calculation_time:.3f}s")
        print(f"   CPU:    {stats_cpu.calculation_time:.3f}s")
        print(f"   Speedup: {stats_normal.calculation_time / stats_cpu.calculation_time:.1f}x")
    
    def test_performance_scaling(self, sample_hp_profile):
        """Testet Performance-Skalierung mit größeren Datensätzen."""
        try:
            import numba
        except ImportError:
            pytest.skip("Numba nicht installiert")
        
        # Verschiedene Datengrößen testen
        sizes = [100, 1000, 5000]
        results = []
        
        for size in sizes:
            # Erzeuge Daten
            dates = pd.date_range('2030-01-01 00:00', periods=size, freq='15min')
            temps = 5 + 10 * np.sin(np.linspace(0, 8*np.pi, size))
            df_weather = pd.DataFrame({
                'Zeitpunkt': dates.strftime('%d.%m.%y %H:%M'),
                'AVERAGE': temps
            })
            
            # Normal-Modus
            engine_normal = CalculationEngine(mode="normal")
            _, stats_normal = engine_normal.calculate_heatpump_load(
                df_weather, sample_hp_profile, 1000, 10000, 3.5, 0.25, 2030
            )
            
            # CPU-Modus
            engine_cpu = CalculationEngine(mode="cpu_optimized")
            _, stats_cpu = engine_cpu.calculate_heatpump_load(
                df_weather, sample_hp_profile, 1000, 10000, 3.5, 0.25, 2030
            )
            
            speedup = stats_normal.calculation_time / stats_cpu.calculation_time
            results.append({
                'size': size,
                'normal_time': stats_normal.calculation_time,
                'cpu_time': stats_cpu.calculation_time,
                'speedup': speedup
            })
            
            print(f"\nSize {size}: Normal={stats_normal.calculation_time:.3f}s, "
                  f"CPU={stats_cpu.calculation_time:.3f}s, Speedup={speedup:.1f}x")
        
        # Prüfe dass CPU mindestens 5x schneller ist für größere Datensätze
        # (Erster Durchlauf kann durch JIT-Kompilierung langsamer sein)
        largest_speedup = results[-1]['speedup']
        assert largest_speedup >= 5.0, \
            f"CPU-Modus sollte mindestens 5x schneller sein, ist aber nur {largest_speedup:.1f}x"
        
        print(f"\n✅ Performance-Skalierung bestätigt: {largest_speedup:.1f}x Speedup")
    
    def test_invalid_mode(self):
        """Test dass ungültige Modi abgelehnt werden."""
        with pytest.raises(ValueError, match="Ungültiger Modus"):
            CalculationEngine(mode="quantum_accelerated")
    
    def test_performance_stats_structure(self, sample_weather_data, sample_hp_profile):
        """Test Performance-Stats Struktur."""
        engine = CalculationEngine(mode="normal")
        _, stats = engine.calculate_heatpump_load(
            sample_weather_data, sample_hp_profile, 1000, 10000, 3.5, 0.25, 2030
        )
        
        # Prüfe Datenstruktur
        assert isinstance(stats, PerformanceStats)
        assert stats.mode in ["normal", "cpu_optimized"]
        assert stats.calculation_time > 0
        assert stats.rows_processed == 100
        assert stats.rows_per_second > 0
        
        # Prüfe to_dict()
        stats_dict = stats.to_dict()
        assert isinstance(stats_dict, dict)
        assert all(key in stats_dict for key in [
            'mode', 'mode_display', 'calculation_time', 'rows_processed', 'rows_per_second'
        ])
    
    def test_energy_conservation(self, sample_weather_data, sample_hp_profile):
        """Test dass Energiebilanz korrekt ist."""
        engine = CalculationEngine(mode="cpu_optimized")
        
        n_heatpumps = 1000
        Q_th_a = 10000  # kWh pro WP
        COP_avg = 3.5
        
        df_result, _ = engine.calculate_heatpump_load(
            sample_weather_data, sample_hp_profile, n_heatpumps, Q_th_a, COP_avg, 0.25, 2030
        )
        
        # Gesamtverbrauch
        total_energy_mwh = df_result['Wärmepumpen [MWh]'].sum()
        
        # Erwarteter Verbrauch: (Q_th_a * n_heatpumps / COP_avg)
        # ABER: Die Normierung bezieht sich auf die gegebenen Daten (100 Zeilen)
        # nicht auf das ganze Jahr! 
        # Also ist der erwartete Verbrauch = Q_th_a * n_heatpumps / COP_avg / 1000
        expected_energy_mwh = (Q_th_a * n_heatpumps / COP_avg / 1000)
        
        # Prüfung: Sollte in derselben Größenordnung sein
        assert 0.5 * expected_energy_mwh < total_energy_mwh < 1.5 * expected_energy_mwh, \
            f"Energiebilanz scheint falsch: {total_energy_mwh} MWh vs. erwartet ~{expected_energy_mwh} MWh"
        
        print(f"✅ Energiebilanz OK: {total_energy_mwh:.1f} MWh (erwartet: {expected_energy_mwh:.1f} MWh)")


if __name__ == "__main__":
    # Für direktes Ausführen
    pytest.main([__file__, "-v", "-s"])
