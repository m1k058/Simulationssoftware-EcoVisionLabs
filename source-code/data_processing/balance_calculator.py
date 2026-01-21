"""
Bilanz-Berechnungsmodul für Energiesysteme.
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_processing.simulation_logger import SimulationLogger

try:
    from constants import COLUMN_NAMES
    COL_ZEITPUNKT = COLUMN_NAMES.get("ZEITPUNKT", "Zeitpunkt")
    COL_BILANZ = COLUMN_NAMES.get("BILANZ", "Bilanz [MWh]")
    COL_REST_BILANZ = COLUMN_NAMES.get("REST_BILANZ", "Rest Bilanz [MWh]")
    COL_PRODUKTION = COLUMN_NAMES.get("PRODUKTION", "Produktion [MWh]")
    COL_VERBRAUCH = COLUMN_NAMES.get("VERBRAUCH", "Verbrauch [MWh]")
    COL_GESAMT_VERBRAUCH = COLUMN_NAMES.get("GESAMT_VERBRAUCH", "Gesamt [MWh]")
except ImportError:
    COL_ZEITPUNKT = "Zeitpunkt"
    COL_BILANZ = "Bilanz [MWh]"
    COL_REST_BILANZ = "Rest Bilanz [MWh]"
    COL_PRODUKTION = "Produktion [MWh]"
    COL_VERBRAUCH = "Verbrauch [MWh]"
    COL_GESAMT_VERBRAUCH = "Gesamt [MWh]"


class BalanceCalculator:
    """
    Klasse zur Berechnung der Energiebilanz zwischen Erzeugung und Verbrauch.
    
    Funktionalität:
    - Bilanzberechnung (Erzeugung - Verbrauch) pro Zeitschritt
    - Berechnung von Metriken (Überschuss, Defizit, Autarkiegrad, etc.)
    """
    
    def __init__(self, logger: Optional[SimulationLogger] = None):
        """
        Initialisiert den BalanceCalculator.
        
        Args:
            logger: Optional SimulationLogger für Logging
        """
        self.logger = logger
    
    def _align_to_quarter_hour(
        self, 
        df: pd.DataFrame, 
        simu_jahr: int, 
        label: str
    ) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
        """
        Bringt ein DataFrame auf das vollständige 15-Minuten-Raster
        
        Args:
            df: DataFrame mit Zeitstempel-Spalte 'Zeitpunkt'
            simu_jahr: Simulationsjahr (z.B. 2030)
            label: Beschreibung für Fehlermeldungen (z.B. "Produktion", "Verbrauch")
        
        Returns:
            Tuple aus (aligned DataFrame, target DatetimeIndex)
        
        """
        if "Zeitpunkt" not in df.columns:
            raise KeyError(f"{label}: Spalte 'Zeitpunkt' fehlt.")
        
        df_local = df.copy()
        df_local["Zeitpunkt"] = pd.to_datetime(df_local["Zeitpunkt"])
        df_local = df_local.sort_values("Zeitpunkt").drop_duplicates(subset="Zeitpunkt", keep="last")
        
        start = pd.Timestamp(f"{simu_jahr}-01-01 00:00:00")
        end = pd.Timestamp(f"{simu_jahr}-12-31 23:45:00")
        target_index = pd.date_range(start=start, end=end, freq="15min")
        
        aligned = df_local.set_index("Zeitpunkt").reindex(target_index)
        
        if aligned.isnull().any().any():
            missing = aligned.isnull().all(axis=1).sum()
            raise ValueError(
                f"{label}: {missing} Viertelstunden fehlen im Jahr {simu_jahr}; "
                f"Eingabedaten sind lückenhaft."
            )
        
        return aligned, target_index
    
    def calculate_balance(
        self, 
        simProd: pd.DataFrame, 
        simCons: pd.DataFrame, 
        simu_jahr: int
    ) -> pd.DataFrame:
        """
        Berechnet die Bilanz (Erzeugung - Verbrauch) je 15-Minuten-Zeitschritt
        
        Args:
            simProd: DataFrame mit Erzeugungsdaten (Spalten: 'Zeitpunkt', '{Technologie} [MWh]', ...)
            simCons: DataFrame mit Verbrauchsdaten (Spalten: 'Zeitpunkt', '{Sektor} [MWh]', ...)
            simu_jahr: Simulationsjahr (z.B. 2030 oder 2045)
        
        Returns:
            DataFrame mit Spalten:
            - 'Zeitpunkt': Zeitstempel (15-Minuten-Auflösung)
            - 'Produktion [MWh]': Gesamterzeugung
            - 'Verbrauch [MWh]': Gesamtverbrauch
            - 'Bilanz [MWh]': Differenz 
        """
        if self.logger:
            self.logger.info(f"Berechne Bilanz für Jahr {simu_jahr}")
        
        prod_aligned, target_index = self._align_to_quarter_hour(simProd, simu_jahr, "Produktion")
        cons_aligned, _ = self._align_to_quarter_hour(simCons, simu_jahr, "Verbrauch")
        
        if "Gesamt [MWh]" in cons_aligned.columns:
            cons_sum = cons_aligned["Gesamt [MWh]"]
        else:
            cons_sum = cons_aligned.select_dtypes(include=[np.number]).sum(axis=1)
        
        prod_sum = prod_aligned.select_dtypes(include=[np.number]).sum(axis=1)
        
        bilanz = prod_sum - cons_sum
        
        df_bilanz = pd.DataFrame({
            "Zeitpunkt": target_index,
            "Produktion [MWh]": prod_sum.values,
            "Verbrauch [MWh]": cons_sum.values,
            "Bilanz [MWh]": bilanz.values
        })
        
        if self.logger:
            ueberschuss = (bilanz > 0).sum() / len(bilanz) * 100
            self.logger.info(f"Bilanz: {ueberschuss:.1f}% Zeitschritte mit Überschuss")
        
        return df_bilanz
    
    def analyze_balance(self, df_balance: pd.DataFrame) -> dict:
        """
        Analysiert die Bilanz und berechnet wichtige Metriken
        
        Args:
            df_balance: DataFrame mit Spalten ['Zeitpunkt', 'Produktion [MWh]', 'Verbrauch [MWh]', 'Bilanz [MWh]']
        
        Returns:
            Dictionary mit Metriken:
            - total_production_twh: Gesamterzeugung [TWh]
            - total_consumption_twh: Gesamtverbrauch [TWh]
            - total_surplus_twh: Summe aller Überschüsse [TWh]
            - total_deficit_twh: Summe aller Defizite [TWh]
            - surplus_hours: Anzahl Stunden mit Überschuss
            - deficit_hours: Anzahl Stunden mit Defizit
            - autarkie_grad: Autarkiegrad [%]
            - max_surplus_mw: Maximaler Überschuss [MW]
            - max_deficit_mw: Maximales Defizit [MW]
        """
        bilanz = df_balance['Bilanz [MWh]']
        prod = df_balance['Produktion [MWh]']
        cons = df_balance['Verbrauch [MWh]']
        
        # Zeitschritte mit Überschuss/Defizit
        surplus_mask = bilanz > 0
        deficit_mask = bilanz < 0
        
        metrics = {
            'total_production_twh': prod.sum() / 1e6,
            'total_consumption_twh': cons.sum() / 1e6,
            'total_surplus_twh': bilanz[surplus_mask].sum() / 1e6,
            'total_deficit_twh': abs(bilanz[deficit_mask].sum()) / 1e6,
            'surplus_hours': surplus_mask.sum() * 0.25,
            'deficit_hours': deficit_mask.sum() * 0.25,
            'autarkie_grad': (surplus_mask.sum() / len(bilanz) * 100) if len(bilanz) > 0 else 0.0,
            'max_surplus_mw': bilanz.max() * 4,
            'max_deficit_mw': abs(bilanz.min()) * 4,
        }
        
        return metrics
    
    def calculate_residual_load(self, df_balance: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet die Residuallast nach Speichern
        
        Args:
            df_balance: DataFrame mit Bilanz (und optional 'Rest Bilanz [MWh]')
        
        Returns:
            DataFrame mit zusätzlicher Spalte 'Residuallast [MWh]'
        """
        df_result = df_balance.copy()
        
        if 'Rest Bilanz [MWh]' in df_result.columns:
            df_result['Residuallast [MWh]'] = df_result['Rest Bilanz [MWh]']
        else:
            df_result['Residuallast [MWh]'] = df_result['Bilanz [MWh]']
        
        return df_result
