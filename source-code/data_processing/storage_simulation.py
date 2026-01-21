"""
Speichersimulations-Modul für verschiedene Speichertypen.

Dieses Modul kapselt die Logik für die Simulation von Energiespeichern:
- Batteriespeicher (Lithium-Ionen)
- Pumpspeicher (Pumped Hydro)
- Wasserstoffspeicher (H2 mit Elektrolyse/Rückverstromung)

Alle Speicher nutzen ein generisches Bucket-Modell mit konfigurierbaren Parametern.

=== SPALTENNAMEN-KONVENTION ===
Dieses Modul verwendet die zentralen COLUMN_NAMES aus constants.py.
Alle Speicher-Spalten folgen dem Muster: "{Speichertyp} {Metrik} MWh"
    - Batteriespeicher SOC MWh, Batteriespeicher Geladene MWh, ...
    - Pumpspeicher SOC MWh, Pumpspeicher Geladene MWh, ...
    - Wasserstoffspeicher SOC MWh, Wasserstoffspeicher Geladene MWh, ...
===============================
"""

import pandas as pd
import numpy as np
from typing import Optional
from data_processing.simulation_logger import SimulationLogger

# Import zentrale Spaltennamen (für Referenz, direkte Nutzung im generischen Modell nicht praktikabel)
try:
    from constants import COLUMN_NAMES
except ImportError:
    COLUMN_NAMES = {}  # Fallback falls constants nicht verfügbar


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
        Simuliert einen Wasserstoffspeicher mit saisonaler "Sommer-Fill"-Strategie.
        
        Implementiert die IPJ Speicherlogik:
        - Sommer (01.05. - 01.11.): Phase FILL
            - Ziel: 80% SOC am 01.11.
            - Must-Run Elektrolyse wenn nötig (P_el_req)
            - Keine Rückverstromung
            - Nimmt Überschüsse auf
        - Winter (Sonst): Phase DISPATCH
            - Normale Speicherfunktion (Laden bei Überschuss, Entladen bei Defizit)
        
        Parameter:
            capacity_mwh: Maximale Kapazität (E_H2_max)
            max_charge_mw: Max. Elektrolyseleistung (P_el_max)
            max_discharge_mw: Max. Rückverstromung (P_fc_max)
        """
        # --- Parameter Setup ---
        # Wirkungsgrade gemäß Methoden-Docstring (67% / 58%) oder IPJ Logik
        ETA_EL = 0.67  # charge_efficiency (Strom -> H2)
        ETA_FC = 0.58  # discharge_efficiency (H2 -> Strom)
        SOC_TARGET_RATIO = 0.80  # 80% Ziel
        
        # Konvertiere initial_soc
        initial_soc_absolute = initial_soc_mwh * capacity_mwh
        
        target_soc_mwh = capacity_mwh * SOC_TARGET_RATIO
        
        # Daten vorbereiten
        if 'Rest Bilanz [MWh]' in df_balance.columns:
            balance_series = df_balance['Rest Bilanz [MWh]'].values
        else:
            balance_series = df_balance['Bilanz [MWh]'].values
            
        timestamps = df_balance['Zeitpunkt']
        n = len(balance_series)
        dt = 0.25  # 15 min
        
        # Ergebnis-Arrays
        soc = np.zeros(n)
        charged = np.zeros(n)      # MWh_in (Stromaufnahme)
        discharged = np.zeros(n)   # MWh_out (Stromabgabe)
        p_must_run = np.zeros(n)   # Logging für Must-Run Anteil
        
        current_soc = initial_soc_absolute
        
        if self.logger:
            self.logger.info(f"Simuliere H2-Speicher (IPJ-Logik): {capacity_mwh:.0f} MWh, "
                           f"Ziel 01.11.: {target_soc_mwh:.0f} MWh")

        # --- Simulation ---
        for i in range(n):
            ts = timestamps.iloc[i]
            bal = balance_series[i] # +Surplus, -Deficit
            
            # 1. Bestimme Phase & Zeit bis Winter
            # Sommer: Mai (5) bis Okt (10) inkl. -> < 1.11.
            is_summer = (ts.month >= 5) and (ts.month < 11)
            
            p_el_actual = 0.0 # MW (Positiv = Verbrauch/Laden)
            p_fc_actual = 0.0 # MW (Positiv = Erzeugung/Entladen)
            
            if is_summer:
                # === PHASE FILL ===
                
                # a) Berechne Restzeit bis 1.11. des aktuellen Jahres
                # Konstruiere Ziel-Datum: 1. Nov dieses Jahres
                t_winter_start = pd.Timestamp(year=ts.year, month=11, day=1)
                
                # Differenz in Stunden
                delta_t = t_winter_start - ts
                t_rem_h = delta_t.total_seconds() / 3600.0
                
                # Safety: falls wir genau drauf oder drüber sind (sollte durch is_summer gefangen sein, aber sicher ist sicher)
                if t_rem_h < dt:
                    t_rem_h = dt
                
                # b) Erforderliche Must-Run Leistung
                # Wieviel fehlt noch zum Ziel?
                e_missing = max(0.0, target_soc_mwh - current_soc)
                
                # Benötigte H2-Ladeleistung (Output der Elektrolyse, also chemisch)
                # SOC_delta = P_el_input * ETA * time
                # Wir berechnen P_el_req (Input Strom)
                # P_el_req * ETA * t_rem = E_missing
                # -> P_el_req = E_missing / (t_rem * ETA)
                
                p_el_req = e_missing / (t_rem_h * ETA_EL)
                
                # Begrenzung auf installierte Leistung
                p_el_must = min(p_el_req, max_charge_mw)
                
                # c) Integration in Bilanz (als Last)
                # Load_eff = Load + P_must -> Bal_eff = Bal - P_must
                bal_eff = bal - (p_el_must * dt) # MWh Bilanz minus Must-Run Energie
                
                # d) Dispatching (Sommer-Logik)
                
                if bal_eff > 0:
                    # -- ÜBERSCHUSS FALL --
                    
                    surplus_mwh = bal_eff
                    surplus_mw = surplus_mwh / dt
                    
                    # Freie Ladekapazität (Leistung)
                    p_el_free_cap = max_charge_mw - p_el_must
                    
                    # Freie Speicherkapazität (Energie) bis voll (100%, nicht nur 80%)
                    e_space_chem = capacity_mwh - current_soc

                    
                    # Wir berechnen die ZUSÄTZLICHE Leistung:
                    p_el_add = min(p_el_free_cap, surplus_mw)
                    

                    
                    p_el_actual = p_el_must + p_el_add
                    p_fc_actual = 0.0 # Keine Rückverstromung im Sommer
                    
                else:
                    # -- DEFIZIT FALL --
                    # Wir haben durch Must-Run das Defizit ggf. vergrößert oder erzeugt.
                    # H2 hilft NICHT aus (P_fc = 0).
                    # Der Speicher LÄDT stur mit Must-Run (oder weniger wenn voll).
                    
                    p_el_actual = p_el_must
                    p_fc_actual = 0.0
                
            else:
                # === PHASE DISPATCH (Winter) ===
                # Ganz normale Speicherlogik: Bal > 0 Laden, Bal < 0 Entladen
                
                if bal > 0:
                    # Überschuss -> Laden
                    surplus_mw = bal / dt
                    p_el_actual = min(surplus_mw, max_charge_mw)
                    p_fc_actual = 0.0
                else:
                    # Defizit -> Entladen
                    deficit_mw = abs(bal) / dt
                    p_el_actual = 0.0
                    p_fc_actual = min(deficit_mw, max_discharge_mw)

            # --- Physik-Update (Generic Bucket Limit) ---
            
            # 1. Energie Input (Strom)
            e_in_el = p_el_actual * dt
            # 2. Energie Output (Strom)
            e_out_el = p_fc_actual * dt
            
            # 3. SOC Änderung (Chemisch)
            # SOC_new = SOC + (In * Eta_In) - (Out / Eta_Out)
            delta_soc = (e_in_el * ETA_EL) - (e_out_el / ETA_FC)
            
            next_soc = current_soc + delta_soc
            
            # 4. Limits Check (Überlauf/Unterlauf)
            # Wenn next_soc > Cap: Ladeleistung reduzieren
            if next_soc > capacity_mwh:
                overflow = next_soc - capacity_mwh
                # Reduziere Input
                # overflow ist chemisch -> e_in_reduced = e_in - overflow / ETA
                reduce_in = overflow / ETA_EL
                e_in_el -= reduce_in
                # Korrigiere next_soc
                next_soc = capacity_mwh
                
            # Wenn next_soc < 0: Entladeleistung reduzieren
            if next_soc < 0.0:
                underflow = 0.0 - next_soc # positiv
                # Reduziere Output
                # underflow ist chemisch -> e_out_reduced = e_out - underflow * ETA_FC 
                # (Moment: Out/Eta = Chem. Also Out_chem = Out_el / Eta_el_out?? Nein)
                # Formel oben: Out_chem = e_out_el / ETA_FC
                # Wir müssen Out_chem um 'underflow' verringern.
                reduce_out_chem = underflow
                reduce_out_el = reduce_out_chem * ETA_FC
                e_out_el -= reduce_out_el
                
                next_soc = 0.0
                
            # Speichern für nächsten Step
            current_soc = next_soc
            
            soc[i] = current_soc
            charged[i] = e_in_el
            discharged[i] = e_out_el
            if is_summer:
                 p_must_run[i] = p_el_must if 'p_el_must' in locals() else 0.0
        
        # --- Ergebnis DataFrame ---
        df_res = df_balance.copy()
        
        type_name = "Wasserstoffspeicher"
        df_res[f'{type_name} SOC MWh'] = soc
        df_res[f'{type_name} Geladene MWh'] = charged
        df_res[f'{type_name} Entladene MWh'] = discharged
        
        # Bilanz Update
        # Rest = Alt - Geladen + Entladen
        # (Geladen = Verbrauch, Entladen = Erzeugung)
        
        # Achtung: balance_series war die Input-Bilanz.
        # Wenn wir "Must-Run" machen, sinkt die Bilanz (wird negativer).
        # Wir müssen sicherstellen, dass wir konsistent zur Input-Series rechnen.
        df_res['Rest Bilanz [MWh]'] = balance_series - charged + discharged
        
        return df_res

