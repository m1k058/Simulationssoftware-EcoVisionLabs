def simulate_emobility_fleet(
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
    Simuliert eine E-Auto-Flotte mit V2G-Funktionalität.
    
    Die Logik umfasst:
    - Fahrverbrauch (Entladung unabhängig vom Netz)
    - Verfügbarkeit (Plug-Share)
    - 'Morgens voll'-Regel (Target SOC um 07:30)
    - Netz-Dienlichkeit (Laden bei Überschuss, Entladen bei Defizit)

    Args:
        df_balance: DataFrame mit 'Rest Bilanz [MWh]' (positiv = Überschuss, negativ = Defizit)
        df_ev_profile: DataFrame mit 'plug_share' (0-1) und 'consumption_driving_kw' (kW/Auto)
        n_cars: Anzahl der Fahrzeuge
        battery_capacity_kwh: Kapazität pro Fahrzeug in kWh
        charging_power_kw: Ladeleistung pro Fahrzeug in kW
        soc_config: Dict mit 'min_day', 'min_night', 'target_morning'
        grid_config: Dict mit 'surplus', 'deficit'
    """
    
    if soc_config is None: soc_config = {}
    if grid_config is None: grid_config = {}

    # 1. Parameter berechnen
    total_capacity_mwh = (n_cars * battery_capacity_kwh) / 1000.0
    if total_capacity_mwh <= 0:
        # Fallback wenn keine Autos da sind, einfach df zurückgeben
        return df_balance.copy()

    # Initial SOC: 50%
    current_soc = 0.5 * total_capacity_mwh
    
    # Zeitauflösung (Viertelstunden)
    dt = 0.25 
    
    # Grid Thresholds (Hysterese)
    # Default: Surplus > 200 MW -> Laden, Deficit < -200 MW -> Entladen
    GRID_UPPER_THRESHOLD = float(grid_config.get("surplus", 200.0)) 
    GRID_LOWER_THRESHOLD = float(grid_config.get("deficit", -200.0)) 
    
    # Constraints
    # Defaults: Tag 40%, Nacht 20%, Morgen-Ziel 60%
    min_share_day = float(soc_config.get("min_day", 0.4))
    min_share_night = float(soc_config.get("min_night", 0.2))
    target_share_morning = float(soc_config.get("target_morning", 0.6))

    MIN_SOC_DAY = min_share_day * total_capacity_mwh      
    MIN_SOC_NIGHT = min_share_night * total_capacity_mwh    
    TARGET_SOC_MORNING = target_share_morning * total_capacity_mwh 
    
    # Arrays für Ergebnisse
    n = len(df_balance)
    res_soc = np.zeros(n)
    res_charge = np.zeros(n)
    res_discharge = np.zeros(n)
    res_driving_drain = np.zeros(n)
    
    # Bestimme Balance-Spalte
    if 'Rest Bilanz [MWh]' in df_balance.columns:
        balance = df_balance['Rest Bilanz [MWh]'].values
    else:
        balance = df_balance['Bilanz [MWh]'].values
        
    timestamps = df_balance['Zeitpunkt']
    
    # Profil-Daten extrahieren
    plug_share = df_ev_profile['plug_share'].values
    driving_drain_kw = df_ev_profile['consumption_driving_kw'].values
    
    # SOC Min Profil (wenn vorhanden)
    has_soc_min_profile = False
    soc_min_profile = None
    if 'soc_min_share' in df_ev_profile.columns:
        # Fehlende Werte mit 0.2 (Nacht) auffüllen
        soc_min_profile = df_ev_profile['soc_min_share'].fillna(0.2).values
        has_soc_min_profile = True
    
    # Sicherstellen, dass die Längen übereinstimmen
    if len(plug_share) != n:
        print(f"Warnung: EV-Profil Länge {len(plug_share)} != Balance Länge {n}. Schneide ab oder fülle auf.")
        # Wir nehmen das Minimum
        loop_len = min(n, len(plug_share))
        plug_share = plug_share[:loop_len]
        driving_drain_kw = driving_drain_kw[:loop_len]
        if has_soc_min_profile:
             soc_min_profile = soc_min_profile[:loop_len]
    else:
        loop_len = n

    # ITERATION
    for i in range(loop_len):
        ts = timestamps.iloc[i]
        hour = ts.hour
        is_day = 6 <= hour < 22
        
        # 1. Fahrverbrauch abziehen (Passiv)
        # ACHTUNG: Analyse der Daten hat gezeigt, dass 'consumption_driving_kw' im Profil
        # bereits die SUMME für die Flotte (5 Mio Autos) ist (Werte ~230.000 bis 1.500.000).
        # Unsere Logic oben war: driving_drain_kw * n_cars / 1000.
        # Wenn wir das machen, multiplizieren wir FLOTTE * FLOTTE -> FALSCH.
        
        # Wir müssen den Wert aus der CSV auf "pro Auto" normalisieren ODER n_cars ignorieren.
        # Da wir skalieren wollen (n_cars in YAML variabel), müssen wir den Basis-Wert (für 5 Mio Autos)
        # auf 1 Auto runterrechnen.
        
        # Basis aus Excel Params: N_cars = 5.000.000
        # Das Profil wurde für diese 5 Mio erstellt.
        BASE_CARS_PROFILE = 5000000.0
        
        # Leistung pro Auto [kW] = (Profil_Wert_Gesamt [kW? oder W?]) / 5.000.000
        # Profil Werte sind ~230.000 bis 1.5 Mio. 
        # 1.500.000 / 5.000.000 = 0.3 kW -> Plausibel für Durchschnittslast beim Fahren.
        
        # Also: Profil ist kW für die GESAMTE Basis-Flotte.
        kw_per_car = driving_drain_kw[i] / BASE_CARS_PROFILE
        
        # Jetzt hochskalieren auf aktuelle Szenario-Flotte
        drain_mwh = (kw_per_car * n_cars / 1000.0) * dt
        
        # SOC Update durch Fahren
        current_soc -= drain_mwh
        if current_soc < 0: current_soc = 0 # Fallback
        res_driving_drain[i] = drain_mwh
        
        # 2. Verfügbare V2G Leistung berechnen
        # Nur Autos am Stecker können laden/entladen
        n_plugged = n_cars * plug_share[i]
        max_power_mw = (n_plugged * charging_power_kw) / 1000.0
        
        max_energy_step = max_power_mw * dt
        
        # 3. SOC Limits bestimmen
        if has_soc_min_profile:
            # Nutze Profilwert (0.2...0.4...)
            min_limit = soc_min_profile[i] * total_capacity_mwh
        else:
            # Fallback auf Uhrzeit-Logik
            min_limit = MIN_SOC_DAY if is_day else MIN_SOC_NIGHT
        
        # MORGEN-ZIEL LOGIK (Priorität 1):
        # Wenn Zeit zwischen 05:00 und 07:30 und SOC < Target -> Zwangsladen
        force_charge = False
        if 5 <= hour < 8 and current_soc < TARGET_SOC_MORNING:
             force_charge = True

        actual_charge = 0.0
        actual_discharge = 0.0
        
        grid_val = balance[i] # + = Überschuss, - = Defizit

        if force_charge:
            # Muss laden, egal was das Netz sagt (behandelt wie Last)
            needed = TARGET_SOC_MORNING - current_soc
            # Lade so viel wie möglich/nötig
            possible = min(needed / efficiency, max_energy_step)
            actual_charge = possible
            current_soc += actual_charge * efficiency
            
        else:
            # Normaler V2G Betrieb
            
            if grid_val > GRID_UPPER_THRESHOLD:
                # ÜBERSCHUSS -> LADEN
                
                # Wie viel Platz ist noch im Akku?
                space_avail = total_capacity_mwh - current_soc
                if space_avail > 0:
                    # Netzangebot begrenzen auf max Ladeleistung
                    power_avail = min(grid_val * dt, max_energy_step) # MWh im Step
                    
                    # Tatsächlich laden (begrenzt durch Kapazität)
                    loadable = min(power_avail, space_avail / efficiency)
                    
                    actual_charge = loadable
                    current_soc += actual_charge * efficiency
                
            elif grid_val < GRID_LOWER_THRESHOLD:
                # DEFIZIT -> ENTLADEN
                
                # Wie viel Energie ist über Min-Limit verfügbar?
                energy_avail = current_soc - min_limit
                
                if energy_avail > 0:
                    # Netzbedarf (positiver Wert des Defizits)
                    grid_need = abs(grid_val) * dt # MWh
                    
                    # Begrenzen auf Wechselrichter-Leistung
                    discharge_power_limit = min(grid_need, max_energy_step)
                    
                    # Tatsächlich entladen (begrenzt durch vorhandene Energie - Effizienz hier bei Entnahme aus Akku)
                    # Wir nehmen an: Wir wollen X ins Netz speisen. Dafür müssen wir X aus dem Akku holen (bei V2G meist bidirektional, Effizienz in beide Richtungen)
                    # Hier modelliert als: Energie im Akku sinkt. Ins Netz geht Energie * efficiency (oder / efficiency?)
                    # Übliche Konvention in diesem Code: efficiency applied to charge. Discharge efficiency oft auch < 1.
                    # Wir nutzen efficiency Parameter für beides (0.95 -> 0.95 beim Laden, 0.95 beim Entladen)
                    
                    # Energie die ins Netz geht:
                    unloadable_grid = min(discharge_power_limit, energy_avail * efficiency)
                    
                    actual_discharge = unloadable_grid
                    # SOC sinkt
                    current_soc -= actual_discharge / efficiency

        res_soc[i] = current_soc
        res_charge[i] = actual_charge
        res_discharge[i] = actual_discharge

    # Ergebnis zusammenbauen
    # Kopiere existierenden DataFrame um Metadaten zu behalten
    df_res = df_balance.copy()
    
    # Neue Spalten
    df_res['EMobility SOC [MWh]'] = res_soc
    df_res['EMobility Charge [MWh]'] = res_charge
    df_res['EMobility Discharge [MWh]'] = res_discharge
    df_res['EMobility Drive [MWh]'] = res_driving_drain
    
    # Neue Restbilanz:
    # Alt (Rest Bilanz ist in Variable balance, die Werte im DF sind noch 'Bilanz [MWh]' oder 'Rest...')
    if 'Rest Bilanz [MWh]' not in df_res.columns:
        df_res['Rest Bilanz [MWh]'] = df_res['Bilanz [MWh]']
        
    df_res['Rest Bilanz [MWh]'] = df_res['Rest Bilanz [MWh]'] + res_discharge - res_charge
    
    return df_res