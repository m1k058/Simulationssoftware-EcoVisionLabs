"""
Speichersimulations-Modul für verschiedene Speichertypen.

Dieses Modul kapselt die Logik für die Simulation von Energiespeichern:
- Batteriespeicher (Lithium-Ionen)
- Pumpspeicher (Pumped Hydro)
- Wasserstoffspeicher (H2 mit Elektrolyse/Rückverstromung)

Alle Speicher nutzen ein generisches Bucket-Modell mit konfigurierbaren Parametern.
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_processing.simulation_logger import SimulationLogger


class StorageSimulation:
    """
    Klasse zur Simulation verschiedener Energiespeichertypen.
    
    Implementiert ein generisches Bucket-Modell mit:
    - Kapazitätsgrenzen (min/max SOC)
    - Lade-/Entladeleistungsgrenzen
    - Wirkungsgraden für Laden/Entladen
    - Schutz vor Tiefentladung und Überladung
    """
    
    def __init__(self, logger: Optional[SimulationLogger] = None):
        """
        Initialisiert die Speichersimulation.
        
        Args:
            logger: Optional SimulationLogger für strukturiertes Logging
        """
        self.logger = logger
    
    def simulate_generic_storage(
        self,
        df_balance: pd.DataFrame,
        type_name: str,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        charge_efficiency: float,
        discharge_efficiency: float,
        initial_soc_mwh: float = 0.0,
        min_soc_mwh: float = 0.0,
        max_soc_mwh: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Simuliert einen generischen Energiespeicher mit Bucket-Modell.
        
        Flexible Speichersimulation für verschiedene Speichertypen (Batterie, Pumpspeicher, Wasserstoff).
        Iteriert durch alle Zeitschritte (Viertelstunden) und gleicht Überschüsse/Defizite
        mit dem Speicher aus. Berücksichtigt Kapazitätsgrenzen, Lade-/Entladeleistung,
        Wirkungsgrade und Min/Max SOC-Limits.
        
        Logik:
        - Überschuss (Balance > 0): Versuche zu laden (begrenzt durch max_charge_mw und verbleibende Kapazität bis max_soc_mwh)
        - Defizit (Balance < 0): Versuche zu entladen (begrenzt durch max_discharge_mw und verfügbare Energie über min_soc_mwh)
        - Wirkungsgrade werden beim Laden/Entladen angewendet
        
        Args:
            df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
            type_name: Name des Speichertyps (z.B. "Batteriespeicher", "Pumpspeicher", "Wasserstoffspeicher")
            capacity_mwh: Speicherkapazität in MWh
            max_charge_mw: Maximale Ladeleistung in MW
            max_discharge_mw: Maximale Entladeleistung in MW
            charge_efficiency: Ladewirkungsgrad (0.0-1.0)
            discharge_efficiency: Entladewirkungsgrad (0.0-1.0)
            initial_soc_mwh: Initialer Ladestand in MWh (Default: 0.0)
            min_soc_mwh: Minimaler SOC in MWh - Schutz vor Tiefentladung (Default: 0.0)
            max_soc_mwh: Maximaler SOC in MWh (Default: None = capacity_mwh)
        
        Returns:
            DataFrame mit Spalten:
            - 'Zeitpunkt': Zeitstempel
            - '{type_name}_SOC_MWh': Ladestand des Speichers pro Zeitschritt
            - '{type_name}_Charged_MWh': Geladene Energie pro Zeitschritt
            - '{type_name}_Discharged_MWh': Entladene Energie pro Zeitschritt
            - 'Rest_Balance_MWh': Restbilanz nach Speicheroperationen
        """
        
        if max_soc_mwh is None:
            max_soc_mwh = capacity_mwh
        
        # DataFrame kopieren und initiale Balance berechnen
        df = df_balance.copy()
        if 'Rest Bilanz [MWh]' not in df.columns:
            balance_series = df['Bilanz [MWh]']
        else:
            balance_series = df['Rest Bilanz [MWh]']
        
        # Initialisiere Arrays für Ergebnisse
        n = len(balance_series)
        soc = np.zeros(n)
        charged = np.zeros(n)  # Geladene Energie pro Zeitschritt
        discharged = np.zeros(n)  # Entladene Energie pro Zeitschritt
        
        current_soc = initial_soc_mwh
        dt = 0.25  # 15 Minuten
        
        # Konvertiere min/max SOC in absolute Werte
        max_charge_energy_per_step = max_charge_mw * dt
        max_discharge_energy_per_step = max_discharge_mw * dt
        
        # Iteriere durch alle Zeitschritte
        for i in range(n):
            bal = balance_series.iloc[i]
            
            if bal > 0:
                # Fall A: Überschuss - Versucht zu laden
                free_space = max_soc_mwh - current_soc
                max_grid_intake_by_capacity = free_space / charge_efficiency
                energy_in_from_grid = min(bal, max_charge_energy_per_step, max_grid_intake_by_capacity)
                
                # Berechne soc stand nach dem Laden
                current_soc += energy_in_from_grid * charge_efficiency
                charged[i] = energy_in_from_grid
                
            elif bal < 0:
                deficit = abs(bal)
                # Fall B: Defizit - Versucht zu entladen
                available_energy_above_min = current_soc - min_soc_mwh
                max_grid_output_by_power = max_discharge_energy_per_step
                max_grid_output_by_content = available_energy_above_min * discharge_efficiency
                energy_out_to_grid = min(deficit, max_grid_output_by_power, max_grid_output_by_content)
                
                # Berechne soc stand nach dem Entladen
                current_soc -= energy_out_to_grid / discharge_efficiency
                discharged[i] = energy_out_to_grid
                
            soc[i] = current_soc
        
        if 'Rest Bilanz [MWh]' not in df.columns:
            # Baue Ergebnis-DataFrame für das erste Mal
            result = pd.DataFrame({
                'Zeitpunkt': df_balance['Zeitpunkt'],
                f'{type_name} SOC MWh': soc,
                f'{type_name} Geladene MWh': charged,
                f'{type_name} Entladene MWh': discharged,
                # Restbilanz berechnen:
                # Ursprüngliche Balance - Geladen + Entladen
                f'Rest Bilanz [MWh]': balance_series - charged + discharged
            })
        else:
            # Nimm alle bestehenden Spalten aus df und füge die neuen Speicherwerte hinzu
            result = df.copy()
            # Füge die drei neuen Speicher-Spalten hinzu
            result[f'{type_name} SOC MWh'] = soc
            result[f'{type_name} Geladene MWh'] = charged
            result[f'{type_name} Entladene MWh'] = discharged
            # Überschreibe Rest Bilanz mit neu berechneter Bilanz
            result['Rest Bilanz [MWh]'] = balance_series - charged + discharged
        
        return result
    
    def simulate_battery_storage(
        self,
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
        """
        Simuliert einen Batteriespeicher mit typischen Parametern.
        
        Typische Eigenschaften:
        - Hoher Wirkungsgrad (95% Laden/Entladen)
        - Min SOC: 5% (Schutz vor Tiefentladung)
        - Max SOC: 95% (Schutz vor Überladung)
        
        Args:
            df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
            capacity_mwh: Speicherkapazität in MWh
            max_charge_mw: Maximale Ladeleistung in MW
            max_discharge_mw: Maximale Entladeleistung in MW
            initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
        
        Returns:
            DataFrame mit Simulationsergebnissen
        """
        # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
        initial_soc_absolute = initial_soc_mwh * capacity_mwh
        
        if self.logger:
            self.logger.info(f"Simuliere Batteriespeicher: {capacity_mwh:.0f} MWh, "
                           f"Lade: {max_charge_mw:.0f} MW, Entlade: {max_discharge_mw:.0f} MW")
        
        return self.simulate_generic_storage(
            df_balance,
            type_name="Batteriespeicher",
            capacity_mwh=capacity_mwh,
            max_charge_mw=max_charge_mw,
            max_discharge_mw=max_discharge_mw,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            initial_soc_mwh=initial_soc_absolute,
            min_soc_mwh=0.05 * capacity_mwh,
            max_soc_mwh=0.95 * capacity_mwh
        )
    
    def simulate_pump_storage(
        self,
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
        """
        Simuliert einen Pumpspeicher mit typischen Parametern.
        
        Typische Eigenschaften:
        - Mittlerer Wirkungsgrad (88% Laden/Entladen)
        - Min SOC: 0% (keine Tiefentladungsproblematik)
        - Max SOC: 100% (Oberbecken kann komplett gefüllt werden)
        
        Args:
            df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
            capacity_mwh: Speicherkapazität in MWh
            max_charge_mw: Maximale Ladeleistung in MW
            max_discharge_mw: Maximale Entladeleistung in MW
            initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
        
        Returns:
            DataFrame mit Simulationsergebnissen
        """
        # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
        initial_soc_absolute = initial_soc_mwh * capacity_mwh
        
        if self.logger:
            self.logger.info(f"Simuliere Pumpspeicher: {capacity_mwh:.0f} MWh, "
                           f"Lade: {max_charge_mw:.0f} MW, Entlade: {max_discharge_mw:.0f} MW")
        
        return self.simulate_generic_storage(
            df_balance,
            type_name="Pumpspeicher",
            capacity_mwh=capacity_mwh,
            max_charge_mw=max_charge_mw,
            max_discharge_mw=max_discharge_mw,
            charge_efficiency=0.88,
            discharge_efficiency=0.88,
            initial_soc_mwh=initial_soc_absolute,
            min_soc_mwh=0.0,
            max_soc_mwh=capacity_mwh
        )
    
    def simulate_hydrogen_storage(
        self,
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
        """
        Simuliert einen Wasserstoffspeicher mit typischen Parametern.
        
        Typische Eigenschaften:
        - Niedriger Wirkungsgrad (67% Elektrolyse, 58% Rückverstromung)
        - Min SOC: 0% (keine Tiefentladungsproblematik)
        - Max SOC: 100% (Kavernenspeicher kann komplett gefüllt werden)
        
        Args:
            df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
            capacity_mwh: Speicherkapazität in MWh
            max_charge_mw: Maximale Ladeleistung in MW (Elektrolyse-Leistung)
            max_discharge_mw: Maximale Entladeleistung in MW (Rückverstromungsleistung)
            initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
        
        Returns:
            DataFrame mit Simulationsergebnissen
        """
        # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
        initial_soc_absolute = initial_soc_mwh * capacity_mwh
        
        if self.logger:
            self.logger.info(f"Simuliere Wasserstoffspeicher: {capacity_mwh:.0f} MWh, "
                           f"Elektrolyse: {max_charge_mw:.0f} MW, Rückverstromung: {max_discharge_mw:.0f} MW")
        
        return self.simulate_generic_storage(
            df_balance,
            type_name="Wasserstoffspeicher",
            capacity_mwh=capacity_mwh,
            max_charge_mw=max_charge_mw,
            max_discharge_mw=max_discharge_mw,
            charge_efficiency=0.67,
            discharge_efficiency=0.58,
            initial_soc_mwh=initial_soc_absolute,
            min_soc_mwh=0.0,
            max_soc_mwh=capacity_mwh
        )
