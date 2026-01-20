# 🔋 Energiespeicher-Simulation V2.0
## Intelligente Multi-Speicher-Koordination mit saisonaler Optimierung

**Version:** 2.0  
**Datum:** Januar 2026  
**Autor:** Energiesystem-Simulation

---

## 📋 Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Designprinzipien](#designprinzipien)
3. [Speicher-Charakteristika](#speicher-charakteristika)
4. [Simulationsablauf](#simulationsablauf)
5. [Event-Charakterisierung](#event-charakterisierung)
6. [Saisonale Strategien](#saisonale-strategien)
7. [Dispatch-Algorithmus](#dispatch-algorithmus)
8. [SOC-Management](#soc-management)
9. [Mathematische Formeln](#mathematische-formeln)
10. [Konfigurationsparameter](#konfigurationsparameter)

---

## 🎯 Übersicht

### Motivation

Die neue Speicher-Logik ersetzt die bisherige **sequenzielle Kaskade** durch ein **paralleles, intelligentes Dispatch-System**. Ziel ist die optimale Nutzung verschiedener Speichertechnologien entsprechend ihrer physikalischen und wirtschaftlichen Eigenschaften.

### Kernkonzept

```
┌─────────────────────────────────────────────────────────┐
│  ALTE LOGIK (Kaskade)                                  │
│  Bilanz → Batterie → Pumpspeicher → H2 → Rest          │
│  ❌ Ineffizient (Umladeverluste bis 44%)               │
│  ❌ Batterie blockiert andere Speicher                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  NEUE LOGIK (Parallel + Intelligent)                   │
│                                                         │
│         ┌─────────────┐                                │
│         │   Bilanz    │                                │
│         └──────┬──────┘                                │
│                │                                        │
│       ┌────────┼────────┐                             │
│       │        │        │                             │
│   ┌───▼───┐ ┌─▼──┐ ┌──▼───┐                         │
│   │Battery│ │Pump│ │  H2  │                          │
│   └───────┘ └────┘ └──────┘                          │
│   Peaks    Tages-  Saisonal                           │
│   <2h      zyklen  >24h                               │
│                                                         │
│  ✅ Direkt-Routing zu optimalem Speicher              │
│  ✅ Parallele Nutzung möglich                         │
│  ✅ Minimale Umladeverluste                           │
└─────────────────────────────────────────────────────────┘
```

### Hauptmerkmale

- ✅ **Zeitskalen-basierte Zuordnung**: Jeder Speicher für seine optimale Dauer
- ✅ **Saisonale Intelligenz**: Sommer-Fill + Winter-Dispatch für H2
- ✅ **Paralleler Betrieb**: Mehrere Speicher können gleichzeitig agieren
- ✅ **Verlustminimierung**: Direkt-Routing statt Umladeketten
- ✅ **Batterie-Glättung**: Auch H2-Must-Run wird geglättet

---

## 🏗️ Designprinzipien

### 1. Hierarchie nach Zeitskalen

| Speichertyp | Optimale Dauer | Zyklen/Jahr | Hauptzweck |
|-------------|---------------|-------------|------------|
| **Batterie** | Sekunden - 2h | 200-500 | Peak-Shaving, Frequenzregelung |
| **Pumpspeicher** | 2h - 24h | 50-200 | Tag/Nacht-Ausgleich |
| **Wasserstoff** | Tage - Monate | 1-5 | Saisonale Speicherung |

### 2. Verlustminimierung

```
❌ SCHLECHT: Überschuss → Batterie (95%) → Pump (88%) → H2 (67%)
            Gesamt: 56% = 44% Verlust!

✅ GUT:     Überschuss → Direkt H2 (67%)
            Gesamt: 67% = 33% Verlust
```

**Regel:** Langzeit-Überschüsse gehen DIREKT zu H2, nicht über Zwischenspeicher!

### 3. Wirtschaftliche Optimierung

- **Batterie**: Teuer (CAPEX) → Nur für hochwertige Anwendungen (Peaks)
- **Pumpspeicher**: Mittlere Kosten → Tages-Zyklen
- **H2**: Günstig pro kWh → Langzeitspeicherung trotz niedriger Effizienz

### 4. Must-Run-Glättung

```
Sommer-Must-Run (konstant 100 MW):
├─ Ohne Glättung: Konstante 100 MW aus Grid
│  → Blockiert Flexibilität
│
└─ Mit Batterie-Glättung:
   ├─ H2 lädt weiter 100 MW (aus Batterie/Pump/Grid)
   └─ Batterie puffert Schwankungen
       → Grid sieht geglättete Last
```

---

## 🔋 Speicher-Charakteristika

### Batteriespeicher (Lithium-Ionen)

**Technische Parameter:**
```yaml
capacity_mwh: 2000          # 2 GWh typisch
max_charge_mw: 500          # C-Rate ~0.25
max_discharge_mw: 500       # Symmetrisch
charge_efficiency: 0.95     # 95%
discharge_efficiency: 0.95  # 95%
round_trip: 0.90            # 90% (0.95 * 0.95)

soc_min: 0.20              # 20% (Lebensdauer)
soc_max: 0.80              # 80% (Lebensdauer)
initial_soc: 0.50          # 50% Start
```

**Betriebsstrategie:**
- **Primär**: Events < 2 Stunden
- **Sekundär**: Glättung von Must-Run H2
- **SOC-Ziel**: 40-60% (maximale Flexibilität)
- **Zyklen**: 200-500/Jahr → ~5000 über Lebensdauer (10 Jahre)

**Kostenstruktur:**
- CAPEX: ~300-500 €/kWh → 600-1000 M€ für 2 GWh
- OPEX: ~2% CAPEX/Jahr
- Lebensdauer: 10-15 Jahre

---

### Pumpspeicher (Pumped Hydro)

**Technische Parameter:**
```yaml
capacity_mwh: 8000          # 8 GWh typisch (z.B. Goldisthal)
max_charge_mw: 1000         # Pumpleistung
max_discharge_mw: 1200      # Turbinenleistung (oft > Pump)
charge_efficiency: 0.88     # 88%
discharge_efficiency: 0.88  # 88%
round_trip: 0.77            # 77% (0.88 * 0.88)

soc_min: 0.10              # 10% (Oberbecken nie leer)
soc_max: 0.90              # 90% (Hochwasserschutz)
initial_soc: 0.50          # 50% Start
```

**Betriebsstrategie:**
- **Primär**: Events 2-24 Stunden
- **Sekundär**: Unterstützung bei Langzeit-Events
- **SOC-Ziel**: 40-60% (Tages-Zyklen)
- **Zyklen**: 50-200/Jahr

**Kostenstruktur:**
- CAPEX: ~50-150 €/kWh → 400-1200 M€ für 8 GWh
- OPEX: ~1% CAPEX/Jahr
- Lebensdauer: 80-100 Jahre

---

### Wasserstoffspeicher (Elektrolyse + Kavernenspeicher + Fuel Cell)

**Technische Parameter:**
```yaml
capacity_mwh: 50_000        # 50 TWh (saisonal)
max_charge_mw: 2000         # Elektrolyse-Leistung
max_discharge_mw: 1500      # Fuel Cell / Gasturbine
charge_efficiency: 0.67     # 67% (Elektrolyse)
discharge_efficiency: 0.58  # 58% (Rückverstromung)
round_trip: 0.39            # 39% (0.67 * 0.58)

soc_min: 0.10              # 10% (Reserve)
soc_max: 0.95              # 95% (Technisches Limit)
initial_soc: 0.30          # 30% Start (Winter-Ende)

# Saisonale Parameter
summer_target_soc: 0.80    # 80% bis 1. November
summer_reserve_ratio: 0.20 # 20% für Sommer-Peaks
winter_baseload_mode: true # Konstante Entladung
```

**Betriebsstrategie:**

#### Sommer (1. Mai - 31. Oktober):
1. **Must-Run Ladung**: Erreiche 80% SOC bis 1. November
2. **Reserve (20%)**: Für Sommer-Defizite verfügbar
3. **Opportunistisch**: Nutze Langzeit-Überschüsse (>24h)
4. **Keine Rückverstromung** (außer Reserve-Nutzung)

#### Winter (1. November - 30. April):
1. **Baseload-Discharge**: Konstante Leistung über gesamten Winter
2. **Boost-Modus**: +30% bei extremen Defiziten möglich
3. **SOC-Erhaltung**: Plane für gesamte Winter-Saison

**Kostenstruktur:**
- CAPEX Elektrolyse: ~500-800 €/kW
- CAPEX Speicher: ~1-5 €/kWh (Kaverne)
- CAPEX Fuel Cell: ~800-1500 €/kW
- OPEX: ~3% CAPEX/Jahr
- Lebensdauer: 20-30 Jahre (Elektrolyse/FC), 50+ Jahre (Kaverne)

---

## 🔄 Simulationsablauf

### Gesamtarchitektur

```python
for timestep in year:  # 35040 Schritte (15-min)
    
    # PHASE 1: Event-Charakterisierung
    event_type, magnitude = characterize_event(balance, history)
    
    # PHASE 2: Saisonale Priorisierung
    season = get_season(timestamp)
    h2_must_run = calculate_h2_must_run(season, soc, target)
    
    # PHASE 3: Paralleler Dispatch
    dispatch_plan = create_dispatch_plan(
        event_type, season, balance, h2_must_run
    )
    
    # PHASE 4: Physikalische Ausführung
    for storage in [battery, pump, h2]:
        storage.execute(dispatch_plan[storage])
        storage.update_soc()
        storage.check_limits()
    
    # PHASE 5: Rest-Bilanz
    rest_balance = balance - sum(all_charges) + sum(all_discharges)
```

### Datenfluss

```
INPUT:  df_balance['Rest Bilanz [MWh]']
        ↓
┌───────────────────────────────────┐
│ Rolling Window Analysis (8 steps) │
│ → event_type, peak_duration       │
└───────────────┬───────────────────┘
                ↓
┌───────────────────────────────────┐
│ Seasonal Logic                    │
│ → h2_must_run, baseload           │
└───────────────┬───────────────────┘
                ↓
┌───────────────────────────────────┐
│ Dispatch Calculator               │
│ → battery_charge, pump_charge,    │
│   h2_charge, h2_discharge          │
└───────────────┬───────────────────┘
                ↓
┌───────────────────────────────────┐
│ SOC Update (alle Speicher)        │
│ → neue SOCs, Limits-Check          │
└───────────────┬───────────────────┘
                ↓
OUTPUT: rest_balance, soc_arrays, charge/discharge_arrays
```

---

## 🔍 Event-Charakterisierung

### Algorithmus

```python
def characterize_event(balance, history, threshold_ignore=50):
    """
    Analysiert Art und Dauer eines Bilanz-Events.
    
    Returns:
        event_type: 'SHORT_PEAK' | 'MEDIUM_SWING' | 'LONG_SURPLUS' | 'IGNORE'
        magnitude: float (MWh)
        duration_estimate: float (Stunden)
    """
    
    # 1. Magnitude Check
    if abs(balance) < threshold_ignore:
        return 'IGNORE', 0.0, 0.0
    
    # 2. Rolling Window Analysis (letzte 8 Steps = 2h)
    window = history[-8:]  # 8 * 15min = 2h
    
    # 3. Gleiches Vorzeichen?
    same_sign = all(x * balance > 0 for x in window)
    
    if not same_sign:
        # Hochfrequente Schwankung
        return 'SHORT_PEAK', abs(balance), 0.5
    
    # 4. Kontinuität prüfen (wie lange schon?)
    duration_steps = 0
    for i in range(len(history)-1, -1, -1):
        if history[i] * balance > 0:  # Gleiches Vorzeichen
            duration_steps += 1
        else:
            break
    
    duration_hours = duration_steps * 0.25
    
    # 5. Klassifikation
    if duration_hours < 2.0:
        return 'SHORT_PEAK', abs(balance), duration_hours
    elif duration_hours < 24.0:
        return 'MEDIUM_SWING', abs(balance), duration_hours
    else:
        return 'LONG_SURPLUS', abs(balance), duration_hours
```

### Schwellwerte

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| `threshold_ignore` | 50 MWh | Events unter 50 MWh werden ignoriert |
| `short_threshold` | 2.0 h | Grenze Short ↔ Medium |
| `medium_threshold` | 24.0 h | Grenze Medium ↔ Long |
| `window_size` | 8 Steps | 2 Stunden Rückblick |

### Beispiele

```
# BEISPIEL 1: Kurzer Peak
Zeitpunkt: 14:00
Balance: [+200, -50, +300, +150, -100, +400, +350, +500]
         └────────────── 2h Window ──────────────┘
Analyse: Hochfrequente Schwankung
→ Event: SHORT_PEAK, 500 MWh, ~0.5h

# BEISPIEL 2: Tag/Nacht-Wechsel
Zeitpunkt: 20:00
Balance: [+800, +750, +900, +850, +820, +880, +900, +920]
         └────────────── Konstant positiv ──────────────┘
Duration: 6 Stunden gleiches Vorzeichen
→ Event: MEDIUM_SWING, 920 MWh, 6.0h

# BEISPIEL 3: Mehrtägiger Überschuss
Zeitpunkt: 15.07. 10:00
Balance: Seit 72h durchgehend +500 bis +1500 MWh
→ Event: LONG_SURPLUS, 1200 MWh, 72h
```

---

## 🌞❄️ Saisonale Strategien

### Sommer-Strategie (1. Mai - 31. Oktober)

#### Ziel
Erreiche **80% SOC** (40 TWh bei 50 TWh Kapazität) bis **1. November**

#### Must-Run Berechnung

```python
def calculate_h2_must_run_summer(current_date, current_soc, target_soc, h2_capacity):
    """
    Berechnet erforderliche Must-Run Ladeleistung für H2 im Sommer.
    """
    
    # 1. Tage bis Winter
    winter_start = datetime(current_date.year, 11, 1)
    days_remaining = (winter_start - current_date).days
    
    if days_remaining <= 0:
        return 0.0  # Bereits Winter
    
    # 2. Fehlende Energie
    missing_energy_mwh = max(0, target_soc - current_soc)
    
    # 3. Tägliche Rate
    daily_charge_mwh = missing_energy_mwh / days_remaining
    
    # 4. Kontinuierliche Leistung (MW)
    # 24h * dt_per_hour = Schritte pro Tag
    steps_per_day = 96  # 24h * 4 (15-min)
    must_run_per_step_mwh = daily_charge_mwh / steps_per_day
    must_run_power_mw = must_run_per_step_mwh / 0.25  # dt = 0.25h
    
    return must_run_power_mw
```

**Beispiel:**
```
Datum: 15. Juli
Tage bis 1. Nov: 108 Tage
Current SOC: 15 TWh (30%)
Target SOC: 40 TWh (80%)
Missing: 25 TWh = 25_000_000 MWh

Daily: 25_000_000 / 108 = 231,481 MWh/Tag
Per Step: 231,481 / 96 = 2,411 MWh
Power: 2,411 / 0.25 = 9,645 MW

→ Must-Run: ~9.6 GW kontinuierlich
```

#### Reserve-Management (20%)

```python
# 20% der H2-Kapazität = 10 TWh für Sommer-Defizite
h2_summer_reserve_mwh = h2_capacity * 0.20

# Verfügbare Entladung im Sommer (nur aus Reserve)
if current_soc > target_soc:
    # Schon über Ziel → volle Reserve nutzbar
    available_discharge = h2_summer_reserve_mwh
else:
    # Unter Ziel → keine Entladung (nur Must-Run laden)
    available_discharge = 0.0
```

#### Opportunistische Ladung

```python
# Nach Must-Run: Restliche Kapazität für Langzeit-Überschüsse
h2_opportunistic_capacity = h2_max_charge_mw - must_run_power_mw

if event_type == 'LONG_SURPLUS' and h2_opportunistic_capacity > 0:
    # Nutze verfügbare Kapazität
    h2_charge_opportunistic = min(
        balance_remaining,
        h2_opportunistic_capacity * dt,
        (h2_capacity * 0.95 - current_soc) / 0.67  # Max SOC 95%
    )
```

---

### Winter-Strategie (1. November - 30. April)

#### Baseload-Berechnung

```python
def calculate_h2_baseload_winter(winter_start_soc, h2_capacity, winter_duration_days=180):
    """
    Berechnet konstante Baseload-Leistung für Winter.
    
    Strategie: Ersten 3 Monate höhere Last, dann reduziert.
    → Erhält Reserve für späten Winter / Dunkelflaute
    """
    
    # 1. Nutzbare Energie (90% des SOC)
    usable_energy_mwh = winter_start_soc * 0.90
    
    # 2. Verteilung: 60% erste 90 Tage, 40% zweite 90 Tage
    first_period_energy = usable_energy_mwh * 0.60  # Nov-Jan
    second_period_energy = usable_energy_mwh * 0.40  # Feb-Apr
    
    # 3. Leistung berechnen (chemische Energie → elektrisch)
    # P_el = E_chem * eta_discharge / time
    
    first_period_hours = 90 * 24
    second_period_hours = 90 * 24
    
    baseload_first_mw = (first_period_energy * 0.58) / first_period_hours
    baseload_second_mw = (second_period_energy * 0.58) / second_period_hours
    
    return {
        'nov_jan': baseload_first_mw,
        'feb_apr': baseload_second_mw
    }
```

**Beispiel:**
```
Winter-Start SOC: 40 TWh (80%)
Nutzbar: 36 TWh (90% von 40)

Erste 90 Tage: 21.6 TWh → 21_600_000 MWh
Elektrisch: 21_600_000 * 0.58 = 12_528_000 MWh
Stunden: 2160h
→ Baseload Nov-Jan: 5,800 MW

Zweite 90 Tage: 14.4 TWh → 14_400_000 MWh
Elektrisch: 14_400_000 * 0.58 = 8_352_000 MWh
→ Baseload Feb-Apr: 3,867 MW
```

**Begründung der Strategie:**
- ✅ Höhere Last in Nov-Jan → Ausnutzung hoher Nachfrage
- ✅ Reserve für Feb-Apr → Sicherheit bei Dunkelflaute
- ✅ Verhindert komplette Entleerung
- ✅ Glatter Übergang zu Sommer-Aufladung

#### Boost-Modus (Extremsituationen)

```python
# Bei extremen Defiziten: Temporäre Erhöhung um 30%
if balance < -5000:  # > 5 GWh Defizit
    boost_factor = 1.30
    max_h2_discharge = baseload * boost_factor
else:
    max_h2_discharge = baseload
```

---

## ⚡ Dispatch-Algorithmus

### Haupt-Dispatch-Funktion

```python
def dispatch_storage_parallel(
    balance_mwh,
    event_type,
    season,
    battery,
    pump,
    h2,
    h2_must_run_mw=0.0
):
    """
    Paralleler Dispatch aller Speicher basierend auf Event-Typ und Saison.
    
    Returns:
        dispatch_plan = {
            'battery': {'charge': float, 'discharge': float},
            'pump': {'charge': float, 'discharge': float},
            'h2': {'charge': float, 'discharge': float},
            'rest_balance': float
        }
    """
    
    dt = 0.25  # 15 Minuten
    balance_remaining = balance_mwh
    
    # Initialize dispatch
    dispatch = {
        'battery': {'charge': 0.0, 'discharge': 0.0},
        'pump': {'charge': 0.0, 'discharge': 0.0},
        'h2': {'charge': 0.0, 'discharge': 0.0}
    }
    
    # ═══════════════════════════════════════════════════════
    # SCHRITT 1: H2 MUST-RUN (hat immer Vorrang)
    # ═══════════════════════════════════════════════════════
    if h2_must_run_mw > 0:
        h2_must_run_energy = h2_must_run_mw * dt
        
        # H2 muss laden, unabhängig von Bilanz
        dispatch['h2']['charge'] += h2_must_run_energy
        balance_remaining -= h2_must_run_energy
        
        # BATTERIE-GLÄTTUNG für Must-Run
        if abs(balance_remaining) < abs(balance_mwh) * 0.5:
            # Must-Run hat Bilanz verschlechtert → Batterie glättet
            battery_smoothing = min(
                abs(balance_remaining) * 0.3,  # 30% Glättung
                battery.get_free_capacity(dt),
                battery.max_charge_mw * dt
            )
            if balance_remaining < 0:
                # Must-Run erzeugte Defizit → Batterie entlädt
                dispatch['battery']['discharge'] += battery_smoothing
                balance_remaining += battery_smoothing
    
    # ═══════════════════════════════════════════════════════
    # SCHRITT 2: HAUPT-DISPATCH basierend auf Event-Typ
    # ═══════════════════════════════════════════════════════
    
    if balance_remaining > 0:
        # ─────────────────────────────────────────────────
        # ÜBERSCHUSS-FALL
        # ─────────────────────────────────────────────────
        
        if event_type == 'SHORT_PEAK':
            # Batterie: 90%, Pump: 10%
            dispatch_short_peak_surplus(dispatch, balance_remaining, battery, pump, dt)
            
        elif event_type == 'MEDIUM_SWING':
            # Pump: 70%, Batterie: 20%, H2: 10%
            dispatch_medium_swing_surplus(dispatch, balance_remaining, battery, pump, h2, season, dt)
            
        elif event_type == 'LONG_SURPLUS':
            # H2: 80%, Pump: 20%
            dispatch_long_surplus(dispatch, balance_remaining, pump, h2, dt)
    
    else:
        # ─────────────────────────────────────────────────
        # DEFIZIT-FALL
        # ─────────────────────────────────────────────────
        deficit = abs(balance_remaining)
        
        if event_type == 'SHORT_PEAK':
            # Batterie: 95%, Pump: 5%
            dispatch_short_peak_deficit(dispatch, deficit, battery, pump, dt)
            
        elif event_type == 'MEDIUM_SWING':
            # Pump: 60%, Batterie: 30%, H2: 10% (Winter)
            dispatch_medium_swing_deficit(dispatch, deficit, battery, pump, h2, season, dt)
            
        elif event_type == 'LONG_SURPLUS':  # Eigentlich Long Deficit
            if season == 'WINTER':
                # H2 Baseload: 70%, Pump: 20%, Battery: 10%
                dispatch_long_deficit_winter(dispatch, deficit, battery, pump, h2, dt)
            else:
                # Sommer: H2-Reserve nutzen (falls vorhanden)
                dispatch_long_deficit_summer(dispatch, deficit, pump, h2, dt)
    
    # ═══════════════════════════════════════════════════════
    # SCHRITT 3: REST-BILANZ BERECHNEN
    # ═══════════════════════════════════════════════════════
    total_charged = sum(s['charge'] for s in dispatch.values())
    total_discharged = sum(s['discharge'] for s in dispatch.values())
    
    dispatch['rest_balance'] = balance_mwh - total_charged + total_discharged
    
    return dispatch
```

### Spezifische Dispatch-Funktionen

#### Short Peak Surplus (< 2h, Überschuss)

```python
def dispatch_short_peak_surplus(dispatch, balance, battery, pump, dt):
    """Batterie: 90%, Pumpspeicher: 10%"""
    
    # 1. Batterie (Hauptlast)
    battery_target = balance * 0.90
    battery_actual = min(
        battery_target,
        battery.get_free_capacity(dt),
        battery.max_charge_mw * dt
    )
    dispatch['battery']['charge'] += battery_actual
    
    # 2. Pumpspeicher (Unterstützung)
    remaining = balance - battery_actual
    pump_target = min(remaining, balance * 0.10)
    pump_actual = min(
        pump_target,
        pump.get_free_capacity(dt),
        pump.max_charge_mw * dt
    )
    dispatch['pump']['charge'] += pump_actual
```

#### Medium Swing Surplus (2-24h, Überschuss)

```python
def dispatch_medium_swing_surplus(dispatch, balance, battery, pump, h2, season, dt):
    """Pumpspeicher: 70%, Batterie: 20%, H2: 10%"""
    
    # 1. Pumpspeicher (Hauptlast)
    pump_target = balance * 0.70
    pump_actual = min(
        pump_target,
        pump.get_free_capacity(dt),
        pump.max_charge_mw * dt
    )
    dispatch['pump']['charge'] += pump_actual
    remaining = balance - pump_actual
    
    # 2. Batterie (Glättung)
    battery_target = min(remaining, balance * 0.20)
    battery_actual = min(
        battery_target,
        battery.get_free_capacity(dt),
        battery.max_charge_mw * dt
    )
    dispatch['battery']['charge'] += battery_actual
    remaining -= battery_actual
    
    # 3. H2 (Opportunistisch, nur wenn noch Kapazität)
    if remaining > 0