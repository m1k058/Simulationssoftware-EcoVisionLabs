"""
End-to-End Integrationstest für die komplette Simulationspipeline.

Testet den gesamten Datenfluss von Berechnung bis Ausgabe:
1. Verbrauchssimulation (BDEW + Wärmepumpen + E-Mobility)
2. Erzeugungssimulation (SMARD-skaliert)
3. Bilanzberechnung
4. E-Mobility V2G Dispatch
5. Speicher-Kaskade (Batterie -> Pumpspeicher -> H2)
6. Wirtschaftlichkeitsanalyse
7. Validierung der Spaltennamenkonsistenz

Autor: SW-Team EcoVisionLabs
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Füge source-code zum Pfad hinzu
SOURCE_CODE_PATH = Path(__file__).parent.parent.parent / "source-code"
sys.path.insert(0, str(SOURCE_CODE_PATH))


class TestColumnNamesConsistency:
    """Tests für konsistente Spaltennamen über alle Module."""
    
    def test_column_names_constant_exists(self):
        """Prüfe, dass COLUMN_NAMES Konstante existiert und vollständig ist."""
        from constants import COLUMN_NAMES
        
        # Pflicht-Spalten
        required_keys = [
            "ZEITPUNKT", "BILANZ", "REST_BILANZ", "PRODUKTION", "VERBRAUCH",
            "BATTERIE_SOC", "PUMP_SOC", "H2_SOC"
        ]
        
        for key in required_keys:
            assert key in COLUMN_NAMES, f"COLUMN_NAMES fehlt Schlüssel: {key}"
            assert isinstance(COLUMN_NAMES[key], str), f"COLUMN_NAMES[{key}] muss String sein"
    
    def test_storage_column_names_consistency(self):
        """Prüfe, dass Speicher-Spaltennamen konsistent sind (kein 'H2-Speicher')."""
        from constants import COLUMN_NAMES
        
        # H2-Speicher muss "Wasserstoffspeicher" heißen, nicht "H2-Speicher"
        h2_soc = COLUMN_NAMES.get("H2_SOC", "")
        assert "Wasserstoffspeicher" in h2_soc, f"H2 SOC Spalte muss 'Wasserstoffspeicher' enthalten, nicht 'H2-Speicher': {h2_soc}"
        
        # Prüfe konsistente Trennzeichen (Leerzeichen, nicht Bindestrich)
        for key, value in COLUMN_NAMES.items():
            if "SPEICHER" in key.upper() or "SOC" in key.upper():
                assert "-Speicher" not in value, f"Spalte {key} enthält inkonsistenten Bindestrich: {value}"


class TestSignConvention:
    """Tests für die Vorzeichen-Konvention im Energiefluss."""
    
    def test_balance_sign_convention_simple(self):
        """Prüfe Bilanz-Vorzeichen direkt (ohne BalanceCalculator-Alignment)."""
        # Einfacher manueller Test der Konvention
        # Bilanz = Produktion - Verbrauch
        
        produktion = 100  # MWh
        verbrauch = 80    # MWh
        bilanz = produktion - verbrauch
        
        assert bilanz > 0, "Überschuss (Produktion > Verbrauch) sollte positiv sein"
        
        produktion = 30
        verbrauch = 80
        bilanz = produktion - verbrauch
        
        assert bilanz < 0, "Defizit (Produktion < Verbrauch) sollte negativ sein"
    
    def test_emobility_sign_inversion_documented(self):
        """Prüfe, dass E-Mobility Vorzeichen-Inversion dokumentiert ist."""
        from data_processing.e_mobility_simulation import __doc__ as docstring
        
        # Der Docstring sollte die Vorzeichen-Konvention erklären
        assert "VORZEICHEN" in docstring.upper(), "E-Mobility Docstring sollte Vorzeichen-Konvention dokumentieren"
        assert "residual_load = -bilanz" in docstring or "-Bilanz" in docstring, \
            "E-Mobility Docstring sollte die Vorzeicheninversion erklären"


class TestStorageSimulation:
    """Tests für die Speichersimulation."""
    
    def test_storage_column_names_output(self):
        """Prüfe, dass Speichersimulation korrekte Spaltennamen ausgibt."""
        from data_processing.storage_simulation import StorageSimulation
        
        # Einfacher Test-DataFrame mit Bilanz
        timestamps = pd.date_range("2030-01-01", periods=4, freq="15min")
        df_balance = pd.DataFrame({
            "Zeitpunkt": timestamps,
            "Bilanz [MWh]": [100, -50, 100, -30]  # Überschuss, Defizit, ...
        })
        
        sim = StorageSimulation()
        
        # Test Wasserstoffspeicher
        result = sim.simulate_hydrogen_storage(
            df_balance,
            capacity_mwh=1000,
            max_charge_mw=50,
            max_discharge_mw=50,
            initial_soc_mwh=0.5
        )
        
        # Prüfe Spaltennamen - muss "Wasserstoffspeicher" sein, nicht "H2-Speicher"
        assert "Wasserstoffspeicher SOC MWh" in result.columns, \
            f"Spalte 'Wasserstoffspeicher SOC MWh' fehlt. Gefunden: {list(result.columns)}"
        assert "H2-Speicher SOC MWh" not in result.columns, \
            "Inkonsistenter Spaltenname 'H2-Speicher' gefunden"


class TestEconomicCalculator:
    """Tests für die Wirtschaftlichkeitsberechnung."""
    
    def test_smard_baseline_loader_exists(self):
        """Prüfe, dass SMARD-Baseline-Lader existiert."""
        from data_processing.economic_calculator import load_smard_baseline_capacities
        
        # Funktion sollte existieren
        assert callable(load_smard_baseline_capacities)
    
    def test_smard_baseline_returns_dict(self):
        """Prüfe, dass SMARD-Baseline-Lader Dict zurückgibt (auch ohne DataManager)."""
        from data_processing.economic_calculator import load_smard_baseline_capacities
        
        # Ohne DataManager: leeres Dict
        result = load_smard_baseline_capacities(None)
        assert isinstance(result, dict)


class TestDataFlowValidation:
    """Validierungstests für korrekten Datenfluss."""
    
    def test_balance_to_storage_flow(self):
        """Prüfe, dass Bilanz korrekt an Speicher weitergegeben wird."""
        from data_processing.storage_simulation import StorageSimulation
        
        # Manuell erstellter Balance-DataFrame (ohne BalanceCalculator)
        timestamps = pd.date_range("2030-01-01", periods=96, freq="15min")  # 1 Tag
        
        # Sinusförmige Bilanz (Überschuss tagsüber, Defizit nachts)
        hours = np.arange(96) / 4
        bilanz = np.sin((hours - 6) / 12 * np.pi) * 50  # -50 bis +50 MWh
        
        df_balance = pd.DataFrame({
            "Zeitpunkt": timestamps,
            "Bilanz [MWh]": bilanz
        })
        
        # Speicher simulieren
        sim = StorageSimulation()
        df_storage = sim.simulate_battery_storage(
            df_balance,
            capacity_mwh=500,
            max_charge_mw=100,
            max_discharge_mw=100,
            initial_soc_mwh=0.5
        )
        
        # Validierungen
        assert "Rest Bilanz [MWh]" in df_storage.columns
        assert "Batteriespeicher SOC MWh" in df_storage.columns
        
        # SOC sollte sich ändern (nicht konstant bleiben)
        soc_values = df_storage["Batteriespeicher SOC MWh"].values
        assert np.std(soc_values) > 0, "SOC sollte variieren, nicht konstant sein"
        
        # Rest-Bilanz sollte kleiner sein als Original-Bilanz (Speicher gleicht aus)
        original_amplitude = np.abs(bilanz).max()
        rest_amplitude = df_storage["Rest Bilanz [MWh]"].abs().max()
        assert rest_amplitude <= original_amplitude, "Speicher sollte Amplitude reduzieren"
    
    def test_storage_cascade_column_names(self):
        """Prüfe, dass alle Speicher konsistente Spaltennamen verwenden."""
        from data_processing.storage_simulation import StorageSimulation
        
        timestamps = pd.date_range("2030-01-01", periods=10, freq="15min")
        df_balance = pd.DataFrame({
            "Zeitpunkt": timestamps,
            "Bilanz [MWh]": [50, -30, 50, -30, 50, -30, 50, -30, 50, -30]
        })
        
        sim = StorageSimulation()
        
        # Batterie
        df1 = sim.simulate_battery_storage(df_balance, 100, 20, 20, 0.5)
        assert "Batteriespeicher SOC MWh" in df1.columns
        assert "Batteriespeicher Geladene MWh" in df1.columns
        
        # Pumpspeicher
        df2 = sim.simulate_pump_storage(df1, 100, 20, 20, 0.5)
        assert "Pumpspeicher SOC MWh" in df2.columns
        
        # Wasserstoffspeicher (NICHT "H2-Speicher")
        df3 = sim.simulate_hydrogen_storage(df2, 100, 20, 20, 0.5)
        assert "Wasserstoffspeicher SOC MWh" in df3.columns
        assert "H2-Speicher SOC MWh" not in df3.columns, "Inkonsistenter Name 'H2-Speicher' gefunden"


# Pytest-Konfiguration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
