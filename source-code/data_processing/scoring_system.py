"""
Fixed scoring system for energy simulation results.

Fixes:
1. Storage utilization based on balance BEFORE storage (not after)
2. Proper CO2 intensity calculation with correct reference values
3. Added safety bounds for all ratios
"""

from typing import Dict, Optional, Any
import pandas as pd


# ------------------------------- #
#           KONSTANTEN            #
# ------------------------------- #

CO2_FACTORS = {
    'gas': 490,  # gCO2/kWh
    'coal': 820,  # gCO2/kWh
    'biomass': 50,  # gCO2/kWh 
    'hydro': 5,   # gCO2/kWh 
}

CO2_REFERENCE = {
    'best': 0,      # g/kWh
    'worst': 1000,  # g/kWh
}

DEFAULT_VALUE_MAPPING = {
    # Last
    'total_load_mwh': {'df': 'Verbrauch', 'col': 'Gesamt [MWh]'},
    
    # Erzeugung
    'wind_onshore_mwh': {'df': 'Erzeugung', 'col': 'Wind Onshore [MWh]'},
    'wind_offshore_mwh': {'df': 'Erzeugung', 'col': 'Wind Offshore [MWh]'},
    'pv_mwh': {'df': 'Erzeugung', 'col': 'Photovoltaik [MWh]'},
    'biomass_mwh': {'df': 'Erzeugung', 'col': 'Biomasse [MWh]'},
    'hydro_mwh': {'df': 'Erzeugung', 'col': 'Wasserkraft [MWh]'},
    'gas_mwh': {'df': 'Erzeugung', 'col': 'Erdgas [MWh]'},
    
    # Speicher
    'battery_soc': {'df': 'Speicher', 'col': 'Batteriespeicher SOC MWh'},
    'battery_charged': {'df': 'Speicher', 'col': 'Batteriespeicher Geladene MWh'},
    'battery_discharged': {'df': 'Speicher', 'col': 'Batteriespeicher Entladene MWh'},
    'pumped_storage_soc': {'df': 'Speicher', 'col': 'Pumpspeicher SOC MWh'},
    'pumped_storage_charged': {'df': 'Speicher', 'col': 'Pumpspeicher Geladene MWh'},
    'pumped_storage_discharged': {'df': 'Speicher', 'col': 'Pumpspeicher Entladene MWh'},
    'h2_soc': {'df': 'Speicher', 'col': 'Wasserstoffspeicher SOC MWh'},
    'h2_charged': {'df': 'Speicher', 'col': 'Wasserstoffspeicher Geladene MWh'},
    'h2_discharged': {'df': 'Speicher', 'col': 'Wasserstoffspeicher Entladene MWh'},
    
    # Bilanz
    'balance_before_flex': {'df': 'Bilanz_vor_Flex', 'col': 'Rest Bilanz [MWh]'},
    'balance_after_flex': {'df': 'Bilanz_nach_Flex', 'col': 'Rest Bilanz [MWh]'},
    'production_total': {'df': 'Bilanz_nach_Flex', 'col': 'Produktion [MWh]'},
    'consumption_total': {'df': 'Bilanz_nach_Flex', 'col': 'Verbrauch [MWh]'},
}


# ------------------------------- #
#        WERTEXTRAKTION           #
# ------------------------------- #

def _get_value(
    results: Dict[str, pd.DataFrame],
    value_mapping: Dict[str, Dict[str, str]],
    var_name: str,
    agg_func: str = 'sum'
) -> Optional[Any]:
    """Extrahiert und aggregiert einen Wert aus den Ergebnis-DataFrames."""
    if var_name not in value_mapping:
        return None
    
    mapping = value_mapping[var_name]
    df_key = mapping['df']
    col_name = mapping['col']
    
    if df_key not in results or col_name not in results[df_key].columns:
        return None
    
    df = results[df_key]
    
    agg_functions = {
        'sum': lambda s: s.sum(),
        'max': lambda s: s.max(),
        'min': lambda s: s.min(),
        'mean': lambda s: s.mean(),
        'series': lambda s: s
    }
    
    return agg_functions.get(agg_func, lambda s: None)(df[col_name])


def _extract_safety_values(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Dict[str, Dict[str, str]]
) -> Dict[str, float]:
    """Extrahiert Werte, die für Safety-KPIs benötigt werden."""
    values = {}
    
    # Gesamtstunden in der Simulation
    values['total_hours'] = round(len(results['Verbrauch']) * 0.25)
    
    # Nicht gedeckte Energie aus Bilanz nach Speciherung 
    balance = _get_value(results, value_mapping, 'balance_after_flex', 'series')
    if balance is not None:
        deficit_mask = balance < 0
        values['total_unserved_mwh'] = abs(balance[deficit_mask].sum())
        values['max_unserved_mw'] = abs(balance[deficit_mask].min()) * 4 if deficit_mask.any() else 0
        values['deficit_hours'] = deficit_mask.sum() * 0.25
    else:
        values['total_unserved_mwh'] = 0
        values['max_unserved_mw'] = 0
        values['deficit_hours'] = 0
    
    # Lastwerte
    values['total_load_mwh'] = _get_value(results, value_mapping, 'total_load_mwh', 'sum') or 0
    values['max_load_mw'] = (_get_value(results, value_mapping, 'total_load_mwh', 'max') or 0) * 4

    # Verfügbare gesicherte Leistung zum Zeitpunkt der Spitzenlast (für Robustness Score)
    load_series_raw = _get_value(results, value_mapping, 'total_load_mwh', 'series')
    prod_series_raw = _get_value(results, value_mapping, 'production_total', 'series')
    if load_series_raw is not None and prod_series_raw is not None:
        try:
            peak_idx = load_series_raw.idxmax()
            peak_prod_mwh = prod_series_raw.loc[peak_idx]
            storage_at_peak = 0
            for _key in ['battery_discharged', 'pumped_storage_discharged', 'h2_discharged']:
                _s = _get_value(results, value_mapping, _key, 'series')
                if _s is not None and peak_idx in _s.index:
                    storage_at_peak += _s.loc[peak_idx]
            values['available_power_at_peak_mw'] = (peak_prod_mwh + storage_at_peak) * 4
        except Exception:
            values['available_power_at_peak_mw'] = 0
    else:
        values['available_power_at_peak_mw'] = 0

    # H2 Speicher Kapazität und Winterdurchschnitt
    h2_soc_series = _get_value(results, value_mapping, 'h2_soc', 'series')
    year_str = str(year)
    
    if h2_soc_series is not None and 'h2_storage' in storage_config and year_str in storage_config['h2_storage']:
        h2_capacity = storage_config['h2_storage'][year_str]['installed_capacity_mwh']
        
        # Wintermonate: November (10), Dezember (11), Januar (0), Februar (1)
        try:
            if hasattr(results['Speicher'], 'index') and hasattr(results['Speicher'].index, 'month'):
                winter_mask = results['Speicher'].index.month.isin([11, 12, 1, 2])
                h2_winter_avg = h2_soc_series[winter_mask].mean()
            else:
                total_intervals = len(h2_soc_series)
                intervals_per_hour = 4
                
                nov_start = int(7320 * intervals_per_hour)
                dec_end = total_intervals
                jan_start = 0
                feb_end = int(1416 * intervals_per_hour)
                
                winter_data = pd.concat([
                    h2_soc_series.iloc[nov_start:dec_end],
                    h2_soc_series.iloc[jan_start:feb_end]
                ])
                h2_winter_avg = winter_data.mean()
        except Exception:
            h2_winter_avg = h2_soc_series.mean()
        
        values['h2_capacity_mwh'] = h2_capacity
        values['h2_winter_avg_mwh'] = h2_winter_avg
    else:
        values['h2_capacity_mwh'] = 0
        values['h2_winter_avg_mwh'] = 0
    
    return values


def _extract_ecology_values(
    results: Dict[str, pd.DataFrame],
    value_mapping: Dict[str, Dict[str, str]]
) -> Dict[str, float]:
    """Extrahiere Werte, die für ökologische KPIs benötigt werden."""
    values = {}
    
    # Individuelle Erzeugungsarten
    sources = {
        'wind_onshore': _get_value(results, value_mapping, 'wind_onshore_mwh', 'sum') or 0,
        'wind_offshore': _get_value(results, value_mapping, 'wind_offshore_mwh', 'sum') or 0,
        'pv': _get_value(results, value_mapping, 'pv_mwh', 'sum') or 0,
        'biomass': _get_value(results, value_mapping, 'biomass_mwh', 'sum') or 0,
        'hydro': _get_value(results, value_mapping, 'hydro_mwh', 'sum') or 0,
        'gas': _get_value(results, value_mapping, 'gas_mwh', 'sum') or 0,
    }
    
    # Erneuerbare Erzeugung (Wind + PV)
    values['renewable_generation_mwh'] = (
        sources['wind_onshore'] + sources['wind_offshore'] + sources['pv']
    )

    # Fossil-freier Anteil: (Gesamt - Fossil) / Gesamt  → inkl. Biomasse, Wasser, Wind, PV
    # Wird als Renewable Share (Fossil-Free Degree) verwendet.
    values['fossil_generation_mwh'] = sources['gas']
    
    # Gesamterzeugung
    values['total_generation_mwh'] = _get_value(results, value_mapping, 'production_total', 'sum') or 0

    if values['total_generation_mwh'] == 0:
        values['total_generation_mwh'] = sum(sources.values())
    
    # Abschaltung aus dem Saldo NACH Speicher
    balance = _get_value(results, value_mapping, 'balance_after_flex', 'series')
    if balance is not None:
        values['curtailment_mwh'] = balance[balance > 0].sum()
    else:
        values['curtailment_mwh'] = 0
    
    # CO2-Emissionsberechnung
    total_co2_kg = (
        sources['gas'] * 1000 * CO2_FACTORS['gas'] / 1000 +
        sources['biomass'] * 1000 * CO2_FACTORS['biomass'] / 1000 +
        sources['hydro'] * 1000 * CO2_FACTORS['hydro'] / 1000
    )
    
    # CO2-Intensität in g/kWh
    total_generation_kwh = values['total_generation_mwh'] * 1000
    values['co2_intensity_g_per_kwh'] = (
        (total_co2_kg * 1000) / total_generation_kwh if total_generation_kwh > 0 else 0
    )
    
    return values


def _extract_economy_values(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Dict[str, Dict[str, str]],
    unserved_mwh: float
) -> Dict[str, float]:
    """Extrahiere Werte, die für wirtschaftliche KPIs benötigt werden."""
    values = {}
    
    values['import_mwh'] = unserved_mwh
    
    # FIXED: Berechne Speicherbedarf aus dem Saldo VOR Speicher
    balance_before = _get_value(results, value_mapping, 'balance_before_flex', 'series')
    
    if balance_before is not None:
        surplus_energy = balance_before[balance_before > 0].sum()
        deficit_energy = abs(balance_before[balance_before < 0].sum())
        values['storage_need_mwh'] = min(surplus_energy, deficit_energy)
    else:
        balance_after = _get_value(results, value_mapping, 'balance_after_flex', 'series')
        if balance_after is not None:
            surplus_energy = balance_after[balance_after > 0].sum()
            deficit_energy = abs(balance_after[balance_after < 0].sum())
            storage_total = 0
            for key in ['battery_discharged', 'pumped_storage_discharged', 'h2_discharged']:
                storage_total += _get_value(results, value_mapping, key, 'sum') or 0
            values['storage_need_mwh'] = min(surplus_energy, deficit_energy) + storage_total
        else:
            values['storage_need_mwh'] = 0
    
    storage_mapping = {
        'battery_storage': ('battery_charged', 'battery_discharged'),
        'pumped_hydro_storage': ('pumped_storage_charged', 'pumped_storage_discharged'),
        'h2_storage': ('h2_charged', 'h2_discharged')
    }
    
    total_charged = 0
    total_discharged = 0
    
    for storage_key, (charged_key, discharged_key) in storage_mapping.items():
        total_charged += _get_value(results, value_mapping, charged_key, 'sum') or 0
        total_discharged += _get_value(results, value_mapping, discharged_key, 'sum') or 0
    
    values['storage_charged_mwh'] = total_charged
    values['storage_discharged_mwh'] = total_discharged
    
    values['useful_storage_throughput_mwh'] = min(total_charged, total_discharged)
    
    # LCOE
    if 'Wirtschaftlichkeit' in results and isinstance(results['Wirtschaftlichkeit'], dict):
        values['system_lcoe'] = results['Wirtschaftlichkeit'].get('system_lco_e')
    else:
        values['system_lcoe'] = None
    
    return values

    # ------------------------------------------ # 
    #      Hilfsfunktionen - KPI-Berechnung      #
    # ------------------------------------------ #

def _safe_ratio(numerator: float, denominator: float, max_value: float = None) -> float:
    """
    Berechnet das Verhältnis sicher mit optionaler Begrenzung.
    
    Args:
        numerator: Zähler des Verhältnisses
        denominator: Nenner des Verhältnisses
        max_value: Optionaler Maximalwert zur Begrenzung
    
    Returns:
        Verhältnis, begrenzt auf max_value falls angegeben
    """
    if denominator <= 0:
        return 0.0
    
    ratio = numerator / denominator
    
    if max_value is not None:
        ratio = min(ratio, max_value)
    
    return ratio


def _calculate_safety_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Safety-Scores aus extrahierten Werten.

    Alle drei Scores liegen im Bereich [0, 1] – höher ist besser.
    """
    # A. Adequacy Score: Anteil der Stunden die das System OHNE Import/Reserve deckt
    # Normierung auf Gesamtstunden der Simulation (kein fixer Grenzwert nötig).
    # Interpretation: "In X% der Jahresstunden reichen EE + Speicher + (historisches) Gas allein."
    # Score = 1.0 → kein Defizit, Score = 0.0 → jede Stunde Defizit
    # Das Gas in der Simulation ist ein historisches Profil, kein dispatchable Backup –
    # verbleibendes Defizit entspricht dem Bedarf an Importen / Reservekraftwerken.
    total_hours = values.get('total_hours', 8760)
    adequacy_score = 1.0 - min(1.0, values['deficit_hours'] / total_hours)

    # B. Robustness Score: Verfügbare gesicherte Leistung / Spitzenlast
    # Kalibriert für autarken Betrieb (VOR Importen / Reservekraftwerken):
    #   100 % Deckung = Score 0.75 (sehr gut ohne Netzverbund)
    #   ≥110 % Deckung = Score 1.0 (Sicherheitsreserve vorhanden)
    #   <100 % linear von 0.0 bis 0.75
    cap_ratio = _safe_ratio(values['available_power_at_peak_mw'], values['max_load_mw'])
    if cap_ratio >= 1.1:
        robustness_score = 1.0
    elif cap_ratio >= 1.0:
        robustness_score = 0.75 + (cap_ratio - 1.0) / 0.1 * 0.25
    else:
        robustness_score = cap_ratio * 0.75

    # C. Dependency Score: 1 - (Netto-Importe / Gesamtverbrauch)
    # Hohe Autarkie = hoher Score
    dependency_score = 1.0 - _safe_ratio(
        values['total_unserved_mwh'],
        values['total_load_mwh'],
        max_value=1.0
    )

    safety_composite = (adequacy_score + robustness_score + dependency_score) / 3.0

    return {
        'adequacy_score':   max(0.0, adequacy_score),
        'robustness_score': max(0.0, min(1.0, robustness_score)),
        'dependency_score': max(0.0, dependency_score),
        'safety_composite': round(max(0.0, min(1.0, safety_composite)), 4),
    }


def _calculate_ecology_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Ökologie-Scores aus extrahierten Werten.

    Alle drei Komponenten liegen in [0, 1] – höher ist besser.
    Gewichtung: CO2-Intensität 60 %, Renewable Share 25 %, Curtailment 15 %.
    """
    CO2_WORST = 400.0   # g/kWh: ab hier Score 0.0  (typischer fossiler Mix)
    CURT_WORST = 0.40   # 40 % Abregelung = Score 0.0

    # A. CO2-Score (60 %): 1 − min(1, CO2 / 400 g/kWh)
    co2_score = 1.0 - min(1.0, values['co2_intensity_g_per_kwh'] / CO2_WORST)

    # B. Renewable Share / Fossil-Free Degree (25 %):  (Gesamt − Fossil) / Gesamt
    total_gen = values['total_generation_mwh']
    fossil     = values['fossil_generation_mwh']
    renewable_share = _safe_ratio(max(0.0, total_gen - fossil), total_gen, max_value=1.0)

    # C. Curtailment Score (15 %): 1 − min(1, Abregelungsquote / 0.40)
    curtailment_ratio = _safe_ratio(
        values['curtailment_mwh'],
        values['renewable_generation_mwh'],
        max_value=CURT_WORST
    )
    curtailment_score = 1.0 - curtailment_ratio / CURT_WORST

    # Gewichteter Gesamt-Score
    ecology_composite = 0.60 * co2_score + 0.25 * renewable_share + 0.15 * curtailment_score

    return {
        'co2_score':          round(max(0.0, co2_score), 4),
        'renewable_share':    round(max(0.0, min(1.0, renewable_share)), 4),
        'curtailment_score':  round(max(0.0, min(1.0, curtailment_score)), 4),
        'ecology_composite':  round(max(0.0, min(1.0, ecology_composite)), 4),
    }


def _calculate_economy_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Wirtschafts-Scores aus extrahierten Werten.

    Alle drei Komponenten liegen in [0, 1] – höher ist besser.
    Gewichtung: LCOE 40 %, Import-Quote 35 %, Speichereffizienz 25 %.
    """
    LCOE_BEST_CT  =  8.0   # ct/kWh ≙ 0.08 €/kWh → Score 1.0
    LCOE_WORST_CT = 40.0   # ct/kWh ≙ 0.40 €/kWh → Score 0.0
    CURT_ECON_WORST = 0.35  # 35 % Abregelung = Score 0.0 (wirtschaftlicher Verlust)

    # A. LCOE Index (40 %): 1 − (LCOE − Best) / (Worst − Best)
    # Wenn LCOE nicht berechnet wurde (None), neutraler Score 0.5 statt künstlich 1.0.
    lcoe_raw = values.get('system_lcoe')
    if lcoe_raw is None:
        lcoe_index = 0.5  # Datenlage unbekannt → neutral
    else:
        lcoe_index = 1.0 - (lcoe_raw - LCOE_BEST_CT) / (LCOE_WORST_CT - LCOE_BEST_CT)
        lcoe_index = max(0.0, min(1.0, lcoe_index))

    # B. Curtailment Score (35 %): wirtschaftlicher Verlust durch Abregelung
    # Ersetzt den redundanten Import-Score (der identisch mit dependency_score in Safety wäre).
    # Curtailment = verschwendete EE-Investitionen, je höher, desto schlechter die Wirtschaftlichkeit.
    curtailment_econ_ratio = _safe_ratio(
        values.get('curtailment_mwh', 0),
        values.get('total_generation_mwh', 1),
        max_value=CURT_ECON_WORST
    )
    curtailment_econ_score = 1.0 - curtailment_econ_ratio / CURT_ECON_WORST

    # C. Speichereffizienz (25 %): nützlicher Durchsatz / Speicherbedarf, auf [0, 1] begrenzt
    storage_efficiency = min(1.0, _safe_ratio(
        values['useful_storage_throughput_mwh'],
        values['storage_need_mwh']
    ))

    # Gewichteter Gesamt-Score
    economy_composite = 0.40 * lcoe_index + 0.35 * curtailment_econ_score + 0.25 * storage_efficiency

    return {
        'lcoe_index':              lcoe_index,
        'curtailment_econ_score':  round(max(0.0, min(1.0, curtailment_econ_score)), 4),
        'storage_efficiency':      storage_efficiency,
        'economy_composite':       round(max(0.0, min(1.0, economy_composite)), 4),
    }


# ------------------------------- #
#       HAUPTFUNKTIONEN           #
# ------------------------------- #

def get_score_and_kpis(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Calculate scoring and KPIs based on simulation results.
    
    Returns KPIs:
    
    Safety (all 0-1 scores, higher = better):
    - adequacy_score:   1 - (deficit_hours / total_hours)  [Anteil autark gedeckter Stunden]
    - robustness_score: gesicherte Leistung / Spitzenlast  (0.5 @ 100%, 1.0 @ 120%)
    - dependency_score: 1 - (Netto-Importe / Gesamtverbrauch)    - safety_composite: Durchschnitt der drei Safety-Scores

    Overall:
    - overall_score: 0.40 * safety_composite + 0.30 * ecology_composite + 0.30 * economy_composite    
    Ecology (all 0-1 scores, higher = better):
    - co2_score:         1 − min(1, CO2 [g/kWh] / 400)  (60 %)
    - renewable_share:   (Gesamt − Fossil) / Gesamt  (25 %)
    - curtailment_score: 1 − (Abregelungsquote / 0.40)  (15 %)
    - ecology_composite: gewichteter Gesamt-Score (60 / 25 / 15 %)
    
    Economy (all 0-1 scores, higher = better):
    - lcoe_index:              1 − (LCOE [ct/kWh] − 8) / (40 − 8)  [Target 0.08–0.40 €/kWh]; neutral 0.5 wenn kein LCOE verfügbar
    - curtailment_econ_score:  1 − (Abregelungsanteil / 35 %), wirtschaftlicher Verlust durch EE-Abregelung  (35 %)
    - storage_efficiency:      nützlicher Speicherdurchsatz / Speicherbedarf  (25 %)
    - economy_composite:       gewichteter Gesamt-Score (40 / 35 / 25 %)
    """
    # Use default mapping if none provided
    mapping = value_mapping or DEFAULT_VALUE_MAPPING
    
    # Extract values by category
    safety_values = _extract_safety_values(results, storage_config, year, mapping)
    ecology_values = _extract_ecology_values(results, mapping)
    economy_values = _extract_economy_values(
        results,
        storage_config,
        year,
        mapping,
        safety_values['total_unserved_mwh']
    )

    all_values = {**safety_values, **ecology_values, **economy_values}

    # Calculate KPIs
    safety_kpis  = _calculate_safety_kpis(all_values)
    ecology_kpis = _calculate_ecology_kpis(all_values)
    economy_kpis = _calculate_economy_kpis(all_values)

    # Composite-Werte aus Sub-Dicts herausnehmen (Top-Level-Keys)
    safety_composite  = safety_kpis.pop('safety_composite')
    ecology_composite = ecology_kpis.pop('ecology_composite')
    economy_composite = economy_kpis.pop('economy_composite')

    # Gesamt-Score: Safety 40 %, Ecology 30 %, Economy 30 %
    overall_score = round(
        0.40 * safety_composite
        + 0.30 * ecology_composite
        + 0.30 * economy_composite,
        4
    )

    kpis = {
        'safety':             safety_kpis,
        'ecology':            ecology_kpis,
        'economy':            economy_kpis,
        'safety_composite':   safety_composite,
        'ecology_composite':  ecology_composite,
        'economy_composite':  economy_composite,
        'overall_score':      overall_score,
        'raw_values':         all_values
    }

    return kpis