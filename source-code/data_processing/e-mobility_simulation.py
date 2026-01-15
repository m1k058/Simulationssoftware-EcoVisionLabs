"""
E-Mobilität Simulation - Vollständige Implementierung basierend auf Excel-Logik.

Dieses Modul implementiert eine V2G-fähige E-Auto-Flotten-Simulation mit:
- Zweistufiger Berechnung (Phase A: Profil-Vorberechnung, Phase B: Hauptsimulation)
- Korrekter Einheitenkonvertierung (MWh <-> kW)
- Vorzeichen-Konvention: negativ=Laden, positiv=Entladen
- Separaten Wirkungsgraden für Laden/Entladen
- Vorlade-Priorität vor Netz-Dispatch

Autor: SW-Team EcoVisionLabs
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class EVConfigParams:
    """
    Config-Parameter (konstant für alle Szenarien).
    Diese werden aus config.json geladen.
    """
    SOC0: float = 0.6              # Initialer State of Charge
    eta_ch: float = 0.95           # Ladewirkungsgrad
    eta_dis: float = 0.95          # Entladewirkungsgrad
    P_ch_car_max: float = 11.0     # Max. Ladeleistung pro Fahrzeug [kW]
    P_dis_car_max: float = 11.0    # Max. Entladeleistung pro Fahrzeug [kW]
    dt_h: float = 0.25             # Zeitschrittlänge [h] (15 Minuten)


@dataclass
class EVScenarioParams:
    """
    Szenario-Parameter (variieren pro Szenario).
    Diese werden aus der Szenario-YAML geladen.
    """
    s_EV: float = 0.9                      # Anteil E-Fahrzeuge
    N_cars: int = 5_000_000                # Gesamtanzahl Fahrzeuge
    E_drive_car_year: float = 2250.0       # Jahresfahrverbrauch pro Fahrzeug [kWh/a]
    E_batt_car: float = 50.0               # Batteriekapazität pro Fahrzeug [kWh]
    plug_share_max: float = 0.6            # Maximale Anschlussquote
    SOC_min_day: float = 0.4               # Min. SOC tagsüber
    SOC_min_night: float = 0.2             # Min. SOC nachts
    SOC_target_depart: float = 0.6         # Ziel-SOC bei Abfahrt
    t_depart: str = "07:30"                # Abfahrtszeit
    t_arrive: str = "18:00"                # Ankunftszeit
    thr_surplus: float = 200_000.0         # Schwellwert für Überschuss [kW] (200 MW)
    thr_deficit: float = 200_000.0         # Schwellwert für Defizit [kW] (200 MW)


def _time_str_to_decimal(time_str: str) -> float:
    """
    Konvertiert Zeit-String "HH:MM" in Dezimalzahl (0.0 bis <1.0).
    
    Beispiele:
        "07:30" -> 0.3125
        "18:00" -> 0.75
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return (hour + minute / 60.0) / 24.0


def _is_between_times_over_midnight(time_of_day: float, t_start: float, t_end: float) -> bool:
    """
    Prüft ob time_of_day zwischen t_start und t_end liegt.
    Funktioniert auch wenn der Zeitraum über Mitternacht geht.
    
    Args:
        time_of_day: Aktuelle Tageszeit als Dezimalzahl (0.0 - <1.0)
        t_start: Startzeit als Dezimalzahl
        t_end: Endzeit als Dezimalzahl
        
    Returns:
        True wenn time_of_day im Intervall liegt
    """
    if t_start <= t_end:
        # Normales Intervall (z.B. 08:00 - 18:00)
        return t_start <= time_of_day < t_end
    else:
        # Intervall über Mitternacht (z.B. 18:00 - 07:30)
        return time_of_day >= t_start or time_of_day < t_end


def generate_ev_profile(
    timestamps: pd.Series,
    scenario_params: EVScenarioParams,
    config_params: EVConfigParams
) -> pd.DataFrame:
    """
    PHASE A: Generiert das EV-Profil für alle Zeitschritte.
    
    Berechnet für jeden Zeitschritt:
    - plug_share: Angeschlossene Quote
    - drive_power: Fahrverbrauchsleistung [kW]
    - soc_min: Minimaler SOC
    - preload_flag: Vorladezeit-Marker
    - soc_target: Ziel-SOC (nur während Vorladezeit)
    
    Args:
        timestamps: Pandas Series mit datetime-Objekten
        scenario_params: Szenario-Parameter
        config_params: Config-Parameter
        
    Returns:
        DataFrame mit allen EV-Profil-Spalten
    """
    n = len(timestamps)
    
    # Zeit-Dezimalwerte vorberechnen
    t_depart_dec = _time_str_to_decimal(scenario_params.t_depart)
    t_arrive_dec = _time_str_to_decimal(scenario_params.t_arrive)
    
    # Vorlade-Startzeit: 2 Stunden vor Abfahrt
    t_preload_start_dec = t_depart_dec - (2.0 / 24.0)
    if t_preload_start_dec < 0:
        t_preload_start_dec += 1.0  # Über Mitternacht
    
    # Flotten-Parameter
    n_ev = scenario_params.s_EV * scenario_params.N_cars
    
    # Basis-Fahrleistung pro Jahr → pro Stunde
    # E_drive_car_year [kWh/a] → Leistung = E / 8760 [kW]
    base_drive_power_per_car = scenario_params.E_drive_car_year / 8760.0
    
    # Arrays initialisieren
    plug_share = np.zeros(n)
    drive_power = np.zeros(n)
    soc_min = np.zeros(n)
    preload_flag = np.zeros(n, dtype=int)
    soc_target = np.full(n, np.nan)
    
    for i in range(n):
        ts = timestamps.iloc[i]
        hour = ts.hour
        minute = ts.minute
        
        # Zeit als Dezimalzahl (0.0 - <1.0)
        time_of_day = (hour + minute / 60.0) / 24.0
        
        # 1. plug_share: Fahrzeuge sind zwischen t_arrive und t_depart angeschlossen
        # Zeitraum geht über Mitternacht (18:00 - 07:30)
        if _is_between_times_over_midnight(time_of_day, t_arrive_dec, t_depart_dec):
            plug_share[i] = scenario_params.plug_share_max
        else:
            plug_share[i] = 0.1 * scenario_params.plug_share_max
        
        # 2. drive_power: Fahrverbrauchsleistung [kW]
        # Tagsüber (7-19 Uhr) höher, nachts niedriger
        if 7 <= hour < 19:
            drive_factor = 1.3
        else:
            drive_factor = 0.2
        
        # Gesamte Fahrleistung der Flotte [kW]
        drive_power[i] = drive_factor * n_ev * base_drive_power_per_car
        
        # 3. soc_min: Minimaler SOC
        # Tagsüber (zwischen t_depart und t_arrive): SOC_min_day
        # Nachts: SOC_min_night
        if _is_between_times_over_midnight(time_of_day, t_depart_dec, t_arrive_dec):
            soc_min[i] = scenario_params.SOC_min_day
        else:
            soc_min[i] = scenario_params.SOC_min_night
        
        # 4. preload_flag: Vorladezeit-Marker
        # Vorladezeit: 2 Stunden vor t_depart bis t_depart
        if _is_between_times_over_midnight(time_of_day, t_preload_start_dec, t_depart_dec):
            preload_flag[i] = 1
            # 5. soc_target: Nur während Vorladezeit setzen
            soc_target[i] = scenario_params.SOC_target_depart
    
    # DataFrame erstellen
    df_profile = pd.DataFrame({
        'Zeitpunkt': timestamps.values,
        'plug_share': plug_share,
        'drive_power_kw': drive_power,
        'soc_min_share': soc_min,
        'preload_flag': preload_flag,
        'soc_target_share': soc_target
    })
    
    return df_profile


def simulate_emobility_fleet(
    df_balance: pd.DataFrame,
    scenario_params: EVScenarioParams = None,
    config_params: EVConfigParams = None,
    df_ev_profile: pd.DataFrame = None
) -> pd.DataFrame:
    """
    PHASE B: Hauptsimulation der E-Auto-Flotte mit V2G-Funktionalität.
    
    Simuliert zeitschrittweise:
    1. Fahrverbrauch (unabhängig vom Netz)
    2. Dispatch-Sollwert basierend auf Residuallast
    3. Vorlade-Priorisierung
    4. Tatsächliche Lade-/Entladeleistung
    5. Energiebilanz-Update
    
    VORZEICHEN-KONVENTION:
    - Negativ = Laden (Energieaufnahme aus Netz)
    - Positiv = Entladen (Energieabgabe ins Netz)
    
    EINHEITEN:
    - Residuallast kommt in MWh → wird intern in kW konvertiert
    - Alle internen Berechnungen in kW und kWh
    - Ergebnis-Residuallast zurück in MWh
    
    Args:
        df_balance: DataFrame mit 'Rest Bilanz [MWh]' oder 'Bilanz [MWh]'
                   und 'Zeitpunkt' Spalte
        scenario_params: Szenario-Parameter (EVScenarioParams)
        config_params: Config-Parameter (EVConfigParams)
        df_ev_profile: Optional - Vorberechnetes EV-Profil aus Phase A
                      Wenn None, wird es automatisch generiert
    
    Returns:
        DataFrame mit Original-Daten + EV-Simulation-Ergebnissen
        Neue Spalten:
        - 'EMobility SOC [MWh]': Batteriespeicher-Inhalt
        - 'EMobility Charge [MWh]': Geladene Energie (positiv)
        - 'EMobility Discharge [MWh]': Entladene Energie (positiv)
        - 'EMobility Drive [MWh]': Fahrverbrauch
        - 'EMobility Power [MW]': Leistung (neg=Laden, pos=Entladen)
        - 'Rest Bilanz [MWh]': Aktualisierte Residuallast
    """
    # Default-Parameter wenn nicht übergeben
    if scenario_params is None:
        scenario_params = EVScenarioParams()
    if config_params is None:
        config_params = EVConfigParams()
    
    # Flotten-Konstanten berechnen
    n_ev = scenario_params.s_EV * scenario_params.N_cars
    capacity_kwh = n_ev * scenario_params.E_batt_car  # Gesamtkapazität [kWh]
    
    if capacity_kwh <= 0:
        # Keine E-Autos → DataFrame unverändert zurückgeben
        return df_balance.copy()
    
    capacity_mwh = capacity_kwh / 1000.0
    
    # Extrahiere Timestamps
    if 'Zeitpunkt' in df_balance.columns:
        timestamps = df_balance['Zeitpunkt']
    else:
        raise ValueError("DataFrame muss 'Zeitpunkt' Spalte enthalten")
    
    n = len(df_balance)
    
    # EV-Profil generieren falls nicht übergeben
    if df_ev_profile is None:
        df_ev_profile = generate_ev_profile(timestamps, scenario_params, config_params)
    
    # Profil-Daten extrahieren
    plug_share = df_ev_profile['plug_share'].values
    drive_power_kw = df_ev_profile['drive_power_kw'].values
    soc_min_share = df_ev_profile['soc_min_share'].values
    preload_flag = df_ev_profile['preload_flag'].values
    soc_target_share = df_ev_profile['soc_target_share'].values
    
    # Bestimme Balance-Spalte und konvertiere zu kW
    # WICHTIG: Residuallast kommt in MWh pro Viertelstunde
    # Konvertierung: MWh/0.25h → kW: * 1000 / dt_h = * 4000
    if 'Rest Bilanz [MWh]' in df_balance.columns:
        residual_load_mwh = df_balance['Rest Bilanz [MWh]'].values.copy()
    elif 'Bilanz [MWh]' in df_balance.columns:
        residual_load_mwh = df_balance['Bilanz [MWh]'].values.copy()
    else:
        raise ValueError("DataFrame muss 'Rest Bilanz [MWh]' oder 'Bilanz [MWh]' enthalten")
    
    # Konvertiere MWh (Energie pro Intervall) zu kW (Leistung)
    # P [kW] = E [MWh] * 1000 / dt [h]
    residual_load_kw = residual_load_mwh * 1000.0 / config_params.dt_h
    
    # Parameter extrahieren
    dt_h = config_params.dt_h
    eta_ch = config_params.eta_ch
    eta_dis = config_params.eta_dis
    SOC0 = config_params.SOC0
    P_ch_car_max = config_params.P_ch_car_max
    P_dis_car_max = config_params.P_dis_car_max
    thr_surplus = scenario_params.thr_surplus  # kW
    thr_deficit = scenario_params.thr_deficit  # kW
    
    # Initialer Energieinhalt
    energy = SOC0 * capacity_kwh  # [kWh]
    
    # Ergebnis-Arrays
    res_energy = np.zeros(n)       # Energie [kWh]
    res_soc = np.zeros(n)          # SOC [0-1]
    res_actual_power = np.zeros(n) # Leistung [kW] (neg=Laden, pos=Entladen)
    res_charge = np.zeros(n)       # Geladene Energie [kWh]
    res_discharge = np.zeros(n)    # Entladene Energie [kWh]
    res_drive = np.zeros(n)        # Fahrverbrauch [kWh]
    
    # =====================================================================
    # HAUPTSIMULATION - Zeitschrittweise Iteration
    # =====================================================================
    for i in range(n):
        # --- Initialisierung aus vorherigem Zeitschritt ---
        if i > 0:
            # Energie aus vorherigem Zeitschritt übernehmen und begrenzen
            energy = max(0, min(res_energy[i-1], capacity_kwh))
        
        # --- Abgeleitete Größen ---
        soc = energy / capacity_kwh
        
        # --- Leistungsgrenzen [kW] ---
        charge_limit = plug_share[i] * n_ev * P_ch_car_max
        discharge_limit = plug_share[i] * n_ev * P_dis_car_max
        
        # --- Residuallast [kW] ---
        res_load = residual_load_kw[i]
        
        # --- Dispatch-Sollwert berechnen ---
        # Negativ = Laden, Positiv = Entladen
        if res_load < -thr_surplus:
            # Überschuss im Netz → Laden (negativ)
            dispatch_target = -min(abs(res_load), charge_limit)
        elif res_load > thr_deficit:
            # Defizit im Netz → Entladen (positiv)
            dispatch_target = min(res_load, discharge_limit)
        else:
            dispatch_target = 0.0
        
        # --- Verfügbare Kapazitäten ---
        # Überschuss-Energie (über soc_min hinaus) [kWh]
        surplus_energy = max(0, energy - soc_min_share[i] * capacity_kwh)
        
        # Verfügbare Entladeleistung [kW]
        # Berücksichtigt Wirkungsgrad bei Entladung
        available_discharge_power = (surplus_energy * eta_dis) / dt_h
        
        # Vorlade-Energie und -Leistung berechnen
        preload_energy_needed = 0.0
        preload_power_needed = 0.0
        
        if not np.isnan(soc_target_share[i]) and preload_flag[i] == 1:
            target_energy = soc_target_share[i] * capacity_kwh
            preload_energy_needed = max(0, target_energy - energy)
            if preload_energy_needed > 0:
                # Benötigte Ladeleistung [kW]
                preload_power_needed = preload_energy_needed / (dt_h * eta_ch)
        
        # --- Tatsächliche Leistung (3-Stufen-Priorisierung) ---
        if preload_energy_needed > 0:
            # PRIORITÄT 1: Vorladen hat Vorrang
            actual_power = -min(charge_limit, preload_power_needed)
        elif dispatch_target > 0:
            # PRIORITÄT 2: Entladen bei Netzdefizit
            actual_power = min(dispatch_target, discharge_limit, available_discharge_power)
        else:
            # PRIORITÄT 3: Laden oder 0
            actual_power = max(dispatch_target, -charge_limit)
        
        # --- Energiebilanz berechnen ---
        # Fahrverbrauch [kWh]
        drive_consumption = drive_power_kw[i] * dt_h
        
        # Energie aus Laden (actual_power < 0)
        energy_charged = max(0, -actual_power) * dt_h * eta_ch
        
        # Energie für Entladen (actual_power > 0)
        energy_discharged = max(0, actual_power) * dt_h / eta_dis
        
        # Neuer Energieinhalt [kWh]
        energy_new = energy + energy_charged - energy_discharged - drive_consumption
        
        # Sicherheitsbegrenzung
        energy_new = max(0, min(energy_new, capacity_kwh))
        
        # --- Ergebnisse speichern ---
        res_energy[i] = energy_new
        res_soc[i] = energy_new / capacity_kwh
        res_actual_power[i] = actual_power
        res_charge[i] = energy_charged
        res_discharge[i] = energy_discharged
        res_drive[i] = drive_consumption
    
    # =====================================================================
    # ERGEBNIS-DATAFRAME ERSTELLEN
    # =====================================================================
    df_res = df_balance.copy()
    
    # Neue Spalten hinzufügen (in MWh für Konsistenz)
    df_res['EMobility SOC [MWh]'] = res_energy / 1000.0
    df_res['EMobility Charge [MWh]'] = res_charge / 1000.0
    df_res['EMobility Discharge [MWh]'] = res_discharge / 1000.0
    df_res['EMobility Drive [MWh]'] = res_drive / 1000.0
    df_res['EMobility Power [MW]'] = res_actual_power / 1000.0
    
    # Aktualisierte Residuallast berechnen
    # Neue Residuallast = Alte Residuallast - actual_power
    # (bei Laden sinkt Residuallast, bei Entladen steigt sie)
    residual_load_new_kw = residual_load_kw - res_actual_power
    
    # Zurück in MWh konvertieren
    residual_load_new_mwh = residual_load_new_kw * config_params.dt_h / 1000.0
    
    # Rest Bilanz aktualisieren oder erstellen
    if 'Rest Bilanz [MWh]' not in df_res.columns:
        df_res['Rest Bilanz [MWh]'] = df_res['Bilanz [MWh]']
    
    df_res['Rest Bilanz [MWh]'] = residual_load_new_mwh
    
    return df_res


def validate_ev_results(df_results: pd.DataFrame, capacity_mwh: float) -> Dict[str, bool]:
    """
    Validiert die EV-Simulationsergebnisse auf physikalische Plausibilität.
    
    Args:
        df_results: DataFrame mit EV-Simulation-Ergebnissen
        capacity_mwh: Gesamtkapazität der Flotte [MWh]
        
    Returns:
        Dictionary mit Prüfungsergebnissen
    """
    checks = {}
    
    # SOC in [0, capacity]
    soc = df_results['EMobility SOC [MWh]']
    checks["SOC >= 0"] = (soc >= -1e-6).all()
    checks["SOC <= Kapazität"] = (soc <= capacity_mwh * 1.001).all()
    
    # Keine NaN-Werte
    ev_columns = [col for col in df_results.columns if col.startswith('EMobility')]
    checks["Keine NaN-Werte"] = not df_results[ev_columns].isnull().any().any()
    
    # Charge und Discharge nicht negativ
    checks["Charge >= 0"] = (df_results['EMobility Charge [MWh]'] >= -1e-9).all()
    checks["Discharge >= 0"] = (df_results['EMobility Discharge [MWh]'] >= -1e-9).all()
    
    # Ausgabe
    print("\n=== EV-Simulation Validierung ===")
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
    
    return checks


# =============================================================================
# LEGACY-KOMPATIBILITÄT: Alte Funktion mit neuem Interface wrappen
# =============================================================================

def simulate_emobility_fleet_legacy(
    df_balance: pd.DataFrame,
    df_ev_profile: pd.DataFrame,
    n_cars: int,
    battery_capacity_kwh: float,
    charging_power_kw: float,
    efficiency: float = 0.95,
    soc_config: dict = None,
    grid_config: dict = None
) -> pd.DataFrame:
    """
    LEGACY-Wrapper für Rückwärtskompatibilität.
    
    Übersetzt alte Parameter in neue EVScenarioParams/EVConfigParams.
    """
    if soc_config is None:
        soc_config = {}
    if grid_config is None:
        grid_config = {}
    
    # Config-Parameter aus alten Werten
    config_params = EVConfigParams(
        SOC0=0.6,
        eta_ch=efficiency,
        eta_dis=efficiency,
        P_ch_car_max=charging_power_kw,
        P_dis_car_max=charging_power_kw,
        dt_h=0.25
    )
    
    # Szenario-Parameter aus alten Werten
    scenario_params = EVScenarioParams(
        s_EV=1.0,  # Legacy: Alle Autos sind EVs
        N_cars=n_cars,
        E_drive_car_year=2250.0,
        E_batt_car=battery_capacity_kwh,
        plug_share_max=0.6,
        SOC_min_day=float(soc_config.get("min_day", 0.4)),
        SOC_min_night=float(soc_config.get("min_night", 0.2)),
        SOC_target_depart=float(soc_config.get("target_morning", 0.6)),
        t_depart="07:30",
        t_arrive="18:00",
        # Thresholds: Legacy nutzte MWh, neu ist kW
        # Legacy: surplus=200 (MWh) → kW: 200 * 1000 / 0.25 = 800000
        # ABER: Die alten Thresholds waren vermutlich schon in MW gedacht
        thr_surplus=float(grid_config.get("surplus", 200.0)) * 1000.0,
        thr_deficit=abs(float(grid_config.get("deficit", -200.0))) * 1000.0
    )
    
    return simulate_emobility_fleet(
        df_balance=df_balance,
        scenario_params=scenario_params,
        config_params=config_params,
        df_ev_profile=df_ev_profile
    )