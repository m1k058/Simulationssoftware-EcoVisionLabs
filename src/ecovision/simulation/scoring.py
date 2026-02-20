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


def _extract_security_values(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Dict[str, Dict[str, str]]
) -> Dict[str, float]:
    """Extrahiert Werte, die für Sicherheits-KPIs benötigt werden."""
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
    
    # Erneuerbare Erzeugung
    values['renewable_generation_mwh'] = (
        sources['wind_onshore'] + sources['wind_offshore'] + sources['pv']
    )
    
    # Fossile Erzeugung
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


def _calculate_security_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Sicherheits-KPIs aus extrahierten Werten."""
    return {
        # Anteil der nicht gedeckten Energie (0-100%)
        'energy_deficit_share': _safe_ratio(
            values['total_unserved_mwh'], 
            values['total_load_mwh'],
            max_value=1.0
        ),
        
        # Schlimmster Moment (0-100%)
        'peak_deficit_ratio': _safe_ratio(
            values['max_unserved_mw'], 
            values['max_load_mw'],
            max_value=1.0
        ),
        
        # Anteil der Stunden mit Defizit (0-100%)
        'deficit_frequency': _safe_ratio(
            values['deficit_hours'], 
            values['total_hours'],
            max_value=1.0 
        ),
    }


def _calculate_ecology_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Ökologie-KPIs aus extrahierten Werten."""
    return {
        # CO2-Intensität in g/kWh
        'co2_intensity': values['co2_intensity_g_per_kwh'],
        
        # Anteil abgeregelter erneuerbarer Energie (0-40%)
        'curtailment_share': _safe_ratio(
            values['curtailment_mwh'], 
            values['renewable_generation_mwh'],
            max_value=0.4
        ),
        
        # Anteil fossiler Erzeugung (0-100%)
        'fossil_share': _safe_ratio(
            values['fossil_generation_mwh'], 
            values['total_generation_mwh'],
            max_value=1.0
        )
    }


def _calculate_economy_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Berechnet Wirtschafts-KPIs aus extrahierten Werten."""
    total_load = values.get('total_load_mwh', 0)
    
    storage_util_raw = _safe_ratio(
        values['useful_storage_throughput_mwh'], 
        values['storage_need_mwh']
    )
    
    storage_utilization = min(storage_util_raw, 1.2)
    
    return {
        'system_cost_index': values['system_lcoe'] if values['system_lcoe'] is not None else 0,
        
        'import_dependency': _safe_ratio(
            values['import_mwh'], 
            total_load,
            max_value=1.0
        ),
        
        'storage_utilization': storage_utilization
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
    
    Security (all 0-1 ratios):
    - energy_deficit_share: Total unmet energy / total demand
    - peak_deficit_ratio: Max unmet power / peak demand
    - deficit_frequency: Hours with deficit / total hours
    
    Ecology:
    - co2_intensity: Actual g CO2/kWh (0-1000 range)
    - curtailment_share: Curtailed / renewable generation (0-0.4)
    - fossil_share: Fossil / total generation (0-1)
    
    Economy:
    - system_cost_index: LCOE in ct/kWh
    - import_dependency: Imports / total demand (0-1)
    - storage_utilization: Useful throughput / storage need (0-1.2)
    """
    # Use default mapping if none provided
    mapping = value_mapping or DEFAULT_VALUE_MAPPING
    
    # Extract values by category
    security_values = _extract_security_values(results, storage_config, year, mapping)
    ecology_values = _extract_ecology_values(results, mapping)
    economy_values = _extract_economy_values(
        results, 
        storage_config, 
        year, 
        mapping,
        security_values['total_unserved_mwh']
    )
    
    all_values = {**security_values, **ecology_values, **economy_values}
    
    # Calculate KPIs
    kpis = {
        'security': _calculate_security_kpis(all_values),
        'ecology': _calculate_ecology_kpis(all_values),
        'economy': _calculate_economy_kpis(all_values),
        'raw_values': all_values
    }
    
    return kpis