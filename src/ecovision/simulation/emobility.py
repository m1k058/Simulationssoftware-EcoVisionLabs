"""
E-Mobilität Simulation - Vollständige Implementierung basierend auf Excel-Logik.

Dieses Modul implementiert eine V2G-fähige E-Auto-Flotten-Simulation mit:
- Zweistufiger Berechnung (Phase A: Profil-Vorberechnung, Phase B: Hauptsimulation)
- Korrekter Einheitenkonvertierung (MWh <-> kW)
- Vorzeichen-Konvention: negativ=Laden, positiv=Entladen
- Separaten Wirkungsgraden für Laden/Entladen
- Vorlade-Priorität vor Netz-Dispatch

=== KRITISCHE VORZEICHEN-KONVENTION ===

Bilanz-Input (aus balance_calculator.py):
    Bilanz [MWh] = Produktion - Verbrauch
    Positiv (+) = Überschuss (mehr Erzeugung als Verbrauch)
    Negativ (-) = Defizit (mehr Verbrauch als Erzeugung)

Interne Konvertierung in diesem Modul:
    residual_load = -bilanz  # VORZEICHENINVERSION!
    
    residual_load > 0 = Defizit → Netz braucht Energie → V2G Entladung
    residual_load < 0 = Überschuss → Netz hat Überschuss → Laden möglich

Dispatch-Output:
    Dispatch > 0 = Entladung (V2G, Energie fließt INS Netz)
    Dispatch < 0 = Laden (Energie fließt AUS dem Netz)

=======================================

Autor: SW-Team EcoVisionLabs
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# GLOBALE KONSTANTEN
WORKPLACE_V2G_FACTOR = 0.15 # V2G-Faktor am Arbeitsplatz (nur 15% der Autos können V2G)


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
    v2g_share: float = 0.3                 # V2G-Teilnahmequote (Anteil der angeschlossenen Fahrzeuge, die ins Netz zurückspeisen)
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


def _skewed_gaussian(x: np.ndarray, mu: float, sig_left: float, sig_right: float) -> np.ndarray:
    """
    Berechnet einen 'schiefen' Gauß-Peak mit unterschiedlichen 
    Standardabweichungen links/rechts vom Maximum.
    
    Args:
        x: Zeitpunkte in Stunden (0..24)
        mu: Peak-Zeitpunkt (Stunde)
        sig_left: Sigma für Werte < mu
        sig_right: Sigma für Werte >= mu
        
    Returns:
        Array mit Werten (Höhe ca. 1.0 bei x=mu, abhängig von Normalisierung)
    """
    # np.where handhabt die Verzweigung elementweise
    sigma = np.where(x < mu, sig_left, sig_right)
    return np.exp( -0.5 * ((x - mu) / sigma)**2 )


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
    - preload_flag: Vorladezeit-Marker (letzten 2h vor Abfahrt)
    - soc_target: Ziel-SOC bei Abfahrt
    - time_to_depart_h: Verbleibende Zeit bis Abfahrt [Stunden]
    
    Args:
        timestamps: Pandas Series mit datetime-Objekten
        scenario_params: Szenario-Parameter
        config_params: Config-Parameter
        
    Returns:
        DataFrame mit allen EV-Profil-Spalten
    """
    # Zeit-Dezimalwerte vorberechnen
    t_depart_dec = _time_str_to_decimal(scenario_params.t_depart)
    t_arrive_dec = _time_str_to_decimal(scenario_params.t_arrive)
    
    # Vorlade-Startzeit: 2 Stunden vor Abfahrt (Safety-Window)
    t_preload_start_dec = t_depart_dec - (2.0 / 24.0)
    if t_preload_start_dec < 0:
        t_preload_start_dec += 1.0  # Über Mitternacht
    
    # Flotten-Parameter
    n_ev = scenario_params.s_EV * scenario_params.N_cars
    
    # Basis-Fahrleistung pro Jahr → pro Stunde
    # E_drive_car_year [kWh/a] → Leistung = E / 8760 [kW]
    base_drive_power_per_car = scenario_params.E_drive_car_year / 8760.0

    # -------------------------------------------------------------------------
    # NEUER ANSATZ (Skewed Gaussian): Realistischeres Fahrprofil mit Weekday/Weekend
    # -------------------------------------------------------------------------

    # Zeit-Vektor in Stunden (0..24) für Vektorisierung
    ts_hour = timestamps.dt.hour + timestamps.dt.minute / 60.0
    ts_vals = ts_hour.values  # numpy array für Performance
    
    # === FEIERTAGS- & WOCHENEND-LOGIK ===
    simu_jahr = timestamps.iloc[0].year
    
    # Feiertage ermitteln (BDEW-Definition via 'holidays')
    try:
        import holidays
        de_holidays = holidays.Germany(years=simu_jahr, language='de')
        feiertage_set = set(de_holidays.keys()) # für schnellen Lookup
        
        # Check ob Datum in Feiertagen (vektorisiert durch map)
        # Dates extrahieren
        dates = timestamps.dt.date
        is_holiday = dates.isin(feiertage_set).values
        
    except ImportError:
        # Fallback ohne Feiertage
        print("Warnung: Package 'holidays' nicht installiert. Nutze vereinfachte Logik.")
        is_holiday = np.zeros(len(timestamps), dtype=bool)

    # Wochenende (Samstag=5, Sonntag=6)
    is_weekend = (timestamps.dt.dayofweek >= 5).values

    # BDEW-Regel für Lastprofile: 24.12. und 31.12. gelten wie Samstage (also Leisure)
    # unabhängig vom Wochentag
    da = timestamps.dt.day.values
    mo = timestamps.dt.month.values
    is_heiligabend_silvester = (mo == 12) & ((da == 24) | (da == 31))
    
    # "Freizeit"-Tage (Wochenende oder Feiertag oder Heiligabend/Silvester)
    is_leisure_day = is_weekend | is_holiday | is_heiligabend_silvester
    
    # === 1. Aktivitäts-Profil generieren ===
    
    # A) WORKDAY Profil (Commute)
    # Morning Peak: 07:45 (7.75h) - Scharfer Anstieg, flacher Abfall
    peak_morning = _skewed_gaussian(ts_vals, mu=7.75, sig_left=1.5, sig_right=2.5)
    # Evening Peak: 17:15 (17.25h) - Flacher Anstieg, scharfer Abfall
    peak_evening = _skewed_gaussian(ts_vals, mu=17.25, sig_left=2.5, sig_right=2.0)
    
    # Gewichtung: Morgens (Pendeln) weniger stark, Abends (Pendeln + Einkaufen/Freizeit) stärker
    profile_workday = (peak_morning * 0.9) + (peak_evening * 1.1) + 0.1 # + Grundlast
    
    # B) LEISURE Profil (Wochenende/Feiertag)
    # Einfacher "Mittagspeak" für Ausflüge etc., breitere Verteilung
    # Peak um 13:00 (13.0h), sehr breit
    peak_leisure = _skewed_gaussian(ts_vals, mu=13.0, sig_left=5.0, sig_right=5.0)
    profile_leisure = (peak_leisure * 0.8) + 0.1 # Etwas flacher + Grundlast
    
    # C) Kombinieren basierend auf Tagestyp
    activity_profile = np.where(is_leisure_day, profile_leisure, profile_workday)
    
    # 2. Normalisierung des Fahrprofils auf Gesamtenergie
    # Gesamtes Integral der Aktivität über das Jahr (Summe * dt)
    # WICHTIG: config_params.dt_h verwenden statt hardcoded 0.25
    dt_h = config_params.dt_h
    total_activity_sum = np.sum(activity_profile) * dt_h
    
    if total_activity_sum == 0: total_activity_sum = 1.0 # Safety
    
    # Ziel-Energie der gesamten Flotte pro Jahr [kWh]
    target_energy_year = n_ev * scenario_params.E_drive_car_year
    
    # Skalierungsfaktor [kW pro Einheit Aktivität]
    # Sum(P_i * dt) = E_total -> P_scale * Sum(Activity * dt) = E_total
    power_scaling_factor = target_energy_year / total_activity_sum
    
    # Berechne drive_power [kW] für jeden Zeitschritt
    drive_power = activity_profile * power_scaling_factor
    
    # 3. Plug Share (Verfügbarkeit am Stecker)
    # Hängt invers von der Aktivität ab.
    # Bei maximaler Aktivität (Fahren) sind die wenigsten Autos am Stecker.
    # Annahme: Bei Peak-Activity sinkt Plug-Share auf Minimum (z.B. 10% der Max-Verfügbarkeit?).
    # Oder einfache Invertierung:
    # Wir nutzen eine weiche Invertierung: 
    # plug_share ~ plug_share_max * (1.0 - normalized_activity * 0.9)
    # So bleibt immer mind. 10% auch im Peak übrig (realistisch: Kurzzeitparker, etc.)
    
    act_min = np.min(activity_profile)
    act_max = np.max(activity_profile)
    # Normalisiere Aktivität auf 0..1
    if act_max > act_min:
        activity_norm = (activity_profile - act_min) / (act_max - act_min)
    else:
        activity_norm = np.zeros_like(activity_profile)
    
    # Invertiere für Plug-Availability
    # High Driving -> Low Plug
    plug_share_raw = 1.0 - (activity_norm * 0.9)  # Minimum 0.1
    # Safety Check: Limit auf 0.0 bis 1.0
    plug_share_raw = np.clip(plug_share_raw, 0.0, 1.0)
    plug_share = plug_share_raw * scenario_params.plug_share_max

    # 4. Zeit- und Status-abhängige Arrays (Vektorsisiert wo möglich)
    n = len(timestamps)
    soc_min = np.zeros(n)
    time_to_depart = np.zeros(n)
    preload_flag = np.zeros(n, dtype=int)
    soc_target = np.full(n, np.nan)
    
    # Umwandlung von time_of_day für Vergleiche
    time_of_day_series = ts_vals / 24.0

    # Bestimme, ob wir uns im "Driving Window" oder "Parking Window" befinden
    # Basierend auf t_depart/t_arrive (wie zuvor, aber nun logisch für Limits genutzt)
    # Vektorisierte Prüfung für 'is_driving_window'
    # Achtung: _is_between ist scalar. Wir bauens vektorisiert nach.
    
    if t_depart_dec < t_arrive_dec:
        # Tag: depart -> arrive
        is_driving_window = (time_of_day_series >= t_depart_dec) & (time_of_day_series < t_arrive_dec)
    else:
        # Tag (Fahren) über Mitternacht? Eher Nachtschicht.
        is_driving_window = (time_of_day_series >= t_depart_dec) | (time_of_day_series < t_arrive_dec)
    
    is_parking_window = ~is_driving_window
    
    # SOC Min Zuordnung (vectorized)
    soc_min[is_driving_window] = scenario_params.SOC_min_day
    soc_min[is_parking_window] = scenario_params.SOC_min_night
    
    # Preload Flag (2h vor t_depart)
    # Ist etwas komplexer vektorisiert, da t_depart fix ist.
    # Wir prüfen einfach, ob time_of_day im Fenster [t_preload_start, t_depart] ist
    if t_preload_start_dec < t_depart_dec:
        is_preload = (time_of_day_series >= t_preload_start_dec) & (time_of_day_series < t_depart_dec)
    else:
        # über Mitternacht
        is_preload = (time_of_day_series >= t_preload_start_dec) | (time_of_day_series < t_depart_dec)
        
    preload_flag[is_preload] = 1
    
    # Setze soc_target und time_to_depart (Loop der Einfachheit halber oder vector)
    # soc_target gilt, wenn plugged in. Wir setzen es pauschal dort, wo wir "parken" erwarten oder immer.
    # Das Original setzte es wenn 'is_plugged_in' (basierend auf Zeit).
    # Da plug_share nun probabilistisch ist, "simulieren" wir hier den Zustand eines "typischen" Autos
    # für die Logik-Steuerung (Preload, SOC Target).
    
    soc_target[is_parking_window] = scenario_params.SOC_target_depart
    
    # Time to depart calculation (Vektorsisiert)
    # Differenz t_depart - t_now
    diff = t_depart_dec - time_of_day_series
    # Korrektur für negative Werte (t_now > t_depart -> nächster Tag)
    # time to depart ist nur relevant VOR Abfahrt.
    # Wir addieren 1.0, wenn diff < 0
    diff[diff < 0] += 1.0
    time_to_depart = diff * 24.0
    # Wir setzen time_to_depart auf 0 während der Fahrzeit, damit Preload nicht triggered
    time_to_depart[is_driving_window] = 0.0

    # -------------------------------------------------------------------------
    # ENDE NEUER ANSATZ
    # -------------------------------------------------------------------------

    # DataFrame erstellen
    df_profile = pd.DataFrame({
        'Zeitpunkt': timestamps.values,
        'plug_share': plug_share,
        'drive_power_kw': drive_power,
        'soc_min_share': soc_min,
        'preload_flag': preload_flag,
        'soc_target_share': soc_target,
        'time_to_depart_h': time_to_depart,  # NEU
        'is_leisure_day': is_leisure_day  # WICHTIG für V2G-Logik
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
    time_to_depart_h = df_ev_profile['time_to_depart_h'].values
    
    # NEU: Freizeit-Flag extrahieren für V2G-Logik
    if 'is_leisure_day' in df_ev_profile.columns:
        is_leisure_day = df_ev_profile['is_leisure_day'].values
    else:
        # Fallback falls externes Profil ohne diese Spalte kommt (Default: Alles ist Arbeitstag)
        is_leisure_day = np.zeros(n, dtype=bool)
    
    # Bestimme Balance-Spalte und konvertiere zu kW
    # WICHTIG: Die Bilanz verwendet die Konvention:
    #   Bilanz = Erzeugung - Verbrauch
    #   Positiv = Überschuss (mehr Erzeugung als Verbrauch)
    #   Negativ = Defizit (weniger Erzeugung als Verbrauch)
    #
    # Für die E-Mobility-Simulation brauchen wir "Residuallast":
    #   Residuallast = Verbrauch - Erzeugung = -Bilanz
    #   Positiv = Defizit → V2G sollte einspeisen
    #   Negativ = Überschuss → Fahrzeuge sollten laden
    #
    # Daher: Vorzeichen der Bilanz umkehren!
    
    if 'Rest Bilanz [MWh]' in df_balance.columns:
        bilanz_mwh = df_balance['Rest Bilanz [MWh]'].values.copy()
    elif 'Bilanz [MWh]' in df_balance.columns:
        bilanz_mwh = df_balance['Bilanz [MWh]'].values.copy()
    else:
        raise ValueError("DataFrame muss 'Rest Bilanz [MWh]' oder 'Bilanz [MWh]' enthalten")
    
    # Konvertiere Bilanz zu Residuallast (Vorzeichen umkehren!)
    # Residuallast = -Bilanz
    residual_load_mwh = -bilanz_mwh
    
    # Konvertiere MWh (Energie pro Intervall) zu kW (Leistung)
    # P [kW] = E [MWh] * 1000 / dt [h]
    residual_load_kw = residual_load_mwh * 1000.0 / config_params.dt_h
    
    # Parameter extrahieren
    dt_h = config_params.dt_h            # Zeitschrittlänge [h]
    eta_ch = config_params.eta_ch      # Ladewirkungsgrad
    eta_dis = config_params.eta_dis    # Entladewirkungsgrad    
    SOC0 = config_params.SOC0          # Initialer SOC [0-1]    
    P_ch_car_max = config_params.P_ch_car_max   # Max. Ladeleistung pro Fahrzeug [kW]
    P_dis_car_max = config_params.P_dis_car_max  # Max. Entladeleistung pro Fahrzeug [kW]
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
    # V2G-Teilnahmequote extrahieren
    v2g_share = scenario_params.v2g_share
    
    # PHASE B: Setup für V2G-Logik
    # Pre-Calculation für Performance
    t_depart_dec = _time_str_to_decimal(scenario_params.t_depart)
    t_arrive_dec = _time_str_to_decimal(scenario_params.t_arrive)
    
    # Schnellzugriff auf Zeit für Loop (Vektorsisiert vorberechnen)
    # timestamps ist eine Series
    time_hours = timestamps.dt.hour.values
    time_minutes = timestamps.dt.minute.values
    time_dec_array = (time_hours + time_minutes / 60.0) / 24.0
    
    # BDEW-Regel auch hier sicherstellen (falls nicht über is_leisure_day übergeben)
    if 'is_leisure_day' not in df_ev_profile.columns:
        # Fallback calc
        sim_year = timestamps.iloc[0].year
        try:
            import holidays
            de_holidays = holidays.Germany(years=sim_year, language='de')
            feiertage_set = set(de_holidays.keys())
            idx_holiday = np.isin(timestamps.dt.date, list(feiertage_set))
        except ImportError:
            idx_holiday = np.zeros(n, dtype=bool)
            
        idx_weekend = (timestamps.dt.dayofweek >= 5).values
        
        # BDEW 24.12 / 31.12
        mo = timestamps.dt.month.values
        da = timestamps.dt.day.values
        idx_special = (mo == 12) & ((da == 24) | (da == 31))
        
        is_leisure_day = idx_weekend | idx_holiday | idx_special

    for i in range(n):
        # --- Initialisierung aus vorherigem Zeitschritt ---
        if i > 0:
            # Energie aus vorherigem Zeitschritt übernehmen und begrenzen
            energy = max(0, min(res_energy[i-1], capacity_kwh))
        
        # --- Abgeleitete Größen ---
        soc = energy / capacity_kwh
        
        # --- Leistungsgrenzen [kW] ---
        # Alle angeschlossenen Fahrzeuge können laden
        charge_limit = plug_share[i] * n_ev * P_ch_car_max
        
        # PHASE B: Realistische V2G-Limitierung
        # Bestimme ob Arbeitszeit (t_depart ... t_arrive)
        time_dec = time_dec_array[i]
        is_work_time = _is_between_times_over_midnight(time_dec, t_depart_dec, t_arrive_dec)
        
        # Prüfung: Ist es ein Arbeitstag? (Kein Wochenende, kein Feiertag)
        is_actual_workday = not is_leisure_day[i]
        
        # V2G-Share anpassen
        # Beschränkung gilt NUR an Arbeitstagen während der Arbeitszeit (Auto steht am Arbeitsplatz)
        if is_work_time and is_actual_workday:
            current_v2g_share = v2g_share * WORKPLACE_V2G_FACTOR
        else:
            # Freizeit, Wochenende, Nacht -> Volles V2G Potenzial
            current_v2g_share = v2g_share

        # Nur ein Teil der angeschlossenen Fahrzeuge speist ins Netz zurück (V2G)
        discharge_limit = plug_share[i] * n_ev * P_dis_car_max * current_v2g_share
        
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
        
        # =====================================================================
        # ADAPTIVE VORLADE-LOGIK (Option 2)
        # =====================================================================
        # Die Logik entscheidet dynamisch, ob eine Mindest-Ladeleistung nötig ist,
        # um den Ziel-SOC bis zur Abfahrt zu erreichen.
        # 
        # NORMALFALL: Netzdienliches Laden/Entladen
        # PRIORISIERUNG: Nur wenn der Ziel-SOC gefährdet ist
        # =====================================================================
        
        min_charge_power_needed = 0.0  # Mindestens benötigte Ladeleistung [kW]
        is_preload_priority = False    # Flag für Vorlade-Priorisierung
        
        if not np.isnan(soc_target_share[i]) and time_to_depart_h[i] > 0:
            # Fahrzeug ist angeschlossen und hat einen Ziel-SOC
            target_energy = soc_target_share[i] * capacity_kwh
            energy_deficit = max(0, target_energy - energy)
            
            if energy_deficit > 0:
                # Berechne benötigte Mindest-Ladeleistung über verbleibende Zeit
                # P_min = E_deficit / (t_remaining * eta_ch)
                remaining_hours = time_to_depart_h[i]
                
                # Mindestens ein Zeitschritt verbleibt
                remaining_hours = max(remaining_hours, dt_h)
                
                min_charge_power_needed = energy_deficit / (remaining_hours * eta_ch)
                
                # Priorisierung aktivieren, wenn:
                # 1. Im Safety-Window (letzten 2h) UND SOC unter Ziel, ODER
                # 2. Die benötigte Ladeleistung > 50% der verfügbaren Ladeleistung
                #    (früher eingreifen, um Spitzen zu vermeiden!)
                if preload_flag[i] == 1:
                    # Im Safety-Window: IMMER priorisieren wenn unter Ziel
                    is_preload_priority = True
                elif min_charge_power_needed > 0.5 * charge_limit:
                    # Außerhalb Safety-Window: Früher priorisieren um Spitzen zu vermeiden
                    is_preload_priority = True
        
        # =====================================================================
        # TATSÄCHLICHE LEISTUNG BERECHNEN (Adaptive Logik mit Mobilitätsgarantie)
        # =====================================================================
        
        # GRUNDREGEL: Die Mobilitätsgarantie (Ziel-SOC erreichen) hat IMMER Vorrang!
        # V2G ist nur erlaubt, wenn genug "Puffer" über dem Mindest-Ladepfad liegt.
        
        if is_preload_priority and min_charge_power_needed > 0:
            # PRIORITÄT 1: Vorlade-Priorisierung aktiv (Safety-Window oder kritischer SOC)
            # Lade mit der benötigten Mindestleistung
            actual_power = -min(charge_limit, min_charge_power_needed)
            
        elif min_charge_power_needed > 0:
            # PRIORITÄT 2: SOC ist unter Ziel-Pfad - MUSS laden!
            # Selbst wenn Netzdefizit: Mobilitätsgarantie geht vor
            # Lade mit der berechneten Mindestleistung (gleichmäßig über Zeit verteilt)
            actual_power = -min(charge_limit, min_charge_power_needed)
            
        elif dispatch_target > 0:
            # PRIORITÄT 3: Entladen bei Netzdefizit (V2G)
            # BEDINGUNG: Nur wenn SOC über Ziel (kein Ladebedarf)
            # ABER: Strenge Begrenzung um den Ziel-SOC zu garantieren!
            potential_discharge = min(dispatch_target, discharge_limit, available_discharge_power)
            
            # Prüfe: Ist V2G-Entladung überhaupt sicher möglich?
            if not np.isnan(soc_target_share[i]) and time_to_depart_h[i] > 0:
                target_energy = soc_target_share[i] * capacity_kwh
                remaining_hours = max(time_to_depart_h[i], dt_h)
                
                # V2G nur aus dem "Überschuss-Puffer" erlauben
                # Der Puffer ist die Energie ÜBER dem Mindest-Ladepfad.
                #
                # Mindest-Ladepfad: Um den Ziel-SOC gerade noch zu erreichen,
                # muss zu jedem Zeitpunkt ein Mindest-SOC vorhanden sein.
                # min_soc(t) = target_soc - (charge_power * remaining_time * eta)
                
                # Maximale Energiemenge, die noch geladen werden KÖNNTE
                max_chargeable = charge_limit * remaining_hours * eta_ch
                
                # Mindest-Energie, die jetzt vorhanden sein muss, um Ziel zu erreichen
                min_energy_required = target_energy - max_chargeable
                
                # Großzügige Sicherheitsmarge (70%), damit auch bei dauerhaftem
                # Netzdefizit genug Reserve bleibt und das Laden gleichmäßiger verteilt wird
                safety_margin = 0.70
                min_energy_with_safety = min_energy_required + safety_margin * target_energy
                
                # V2G-Budget: Energie über dem Mindest-Niveau mit Sicherheitsmarge
                v2g_budget_energy = max(0, energy - min_energy_with_safety)
                
                # V2G-Budget in Leistung umrechnen für diesen Zeitschritt
                v2g_budget_power = v2g_budget_energy / dt_h * eta_dis
                
                # Entladung auf V2G-Budget begrenzen
                allowed_discharge = min(potential_discharge, v2g_budget_power)
                
                if allowed_discharge > 0:
                    actual_power = allowed_discharge
                else:
                    # Kein V2G-Budget - halte SOC (nicht entladen, nicht laden)
                    actual_power = 0.0
            else:
                actual_power = potential_discharge
                
        elif dispatch_target < 0:
            # PRIORITÄT 3a: Laden bei Netzüberschuss
            # Nutze Überschuss, lade aber nicht mehr als nötig wenn schon voll genug
            actual_power = max(dispatch_target, -charge_limit)
            
        else:
            # PRIORITÄT 3b: Kein Netz-Signal
            # Wenn Mindest-Ladung nötig ist, lade mit Mindestleistung
            # Sonst: keine Aktion
            if min_charge_power_needed > 0:
                actual_power = -min(charge_limit, min_charge_power_needed)
            else:
                actual_power = 0.0
        
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
    
    # KRITISCH: Zurück zur Bilanz-Konvention!
    # Am Anfang wurde: residual_load = -bilanz
    # Daher muss am Ende: bilanz = -residual_load
    # 
    # Bilanz-Konvention (für nachgelagerte Speichermodule):
    #   Bilanz > 0 = Überschuss (Laden möglich)
    #   Bilanz < 0 = Defizit (Entladen möglich)
    rest_bilanz_mwh = -residual_load_new_mwh
    
    # Rest Bilanz aktualisieren oder erstellen
    if 'Rest Bilanz [MWh]' not in df_res.columns:
        df_res['Rest Bilanz [MWh]'] = df_res['Bilanz [MWh]']
    
    df_res['Rest Bilanz [MWh]'] = rest_bilanz_mwh
    
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