"""
Scoring system for energy simulation results.

Calculates KPIs across three categories: Security, Ecology, and Economy.
"""

from typing import Dict, Optional, Any
import pandas as pd


# ============================================================================
# CONSTANTS
# ============================================================================

CO2_FACTORS = {
    'gas': 490,  # gCO2/kWh
    'coal': 820,  # gCO2/kWh
    'worst_case': 500  # gCO2/kWh - maximum today
}

DEFAULT_VALUE_MAPPING = {
    # Load/Demand
    'total_load_mwh': {'df': 'Verbrauch', 'col': 'Gesamt [MWh]'},
    
    # Generation
    'wind_onshore_mwh': {'df': 'Erzeugung', 'col': 'Wind Onshore [MWh]'},
    'wind_offshore_mwh': {'df': 'Erzeugung', 'col': 'Wind Offshore [MWh]'},
    'pv_mwh': {'df': 'Erzeugung', 'col': 'Photovoltaik [MWh]'},
    'biomass_mwh': {'df': 'Erzeugung', 'col': 'Biomasse [MWh]'},
    'hydro_mwh': {'df': 'Erzeugung', 'col': 'Wasserkraft [MWh]'},
    'gas_mwh': {'df': 'Erzeugung', 'col': 'Erdgas [MWh]'},
    
    # Storage
    'battery_soc': {'df': 'Speicher', 'col': 'Batteriespeicher SOC MWh'},
    'battery_charged': {'df': 'Speicher', 'col': 'Batteriespeicher Geladene MWh'},
    'battery_discharged': {'df': 'Speicher', 'col': 'Batteriespeicher Entladene MWh'},
    'pumped_storage_soc': {'df': 'Speicher', 'col': 'Pumpspeicher SOC MWh'},
    'pumped_storage_charged': {'df': 'Speicher', 'col': 'Pumpspeicher Geladene MWh'},
    'pumped_storage_discharged': {'df': 'Speicher', 'col': 'Pumpspeicher Entladene MWh'},
    'h2_soc': {'df': 'Speicher', 'col': 'Wasserstoffspeicher SOC MWh'},
    'h2_charged': {'df': 'Speicher', 'col': 'Wasserstoffspeicher Geladene MWh'},
    'h2_discharged': {'df': 'Speicher', 'col': 'Wasserstoffspeicher Entladene MWh'},
    
    # Balance
    'balance_after_flex': {'df': 'Bilanz_nach_Flex', 'col': 'Rest Bilanz [MWh]'},
    'production_total': {'df': 'Bilanz_nach_Flex', 'col': 'Produktion [MWh]'},
    'consumption_total': {'df': 'Bilanz_nach_Flex', 'col': 'Verbrauch [MWh]'},
}


# ============================================================================
# HELPER FUNCTIONS - DATA EXTRACTION
# ============================================================================

def _get_value(
    results: Dict[str, pd.DataFrame],
    value_mapping: Dict[str, Dict[str, str]],
    var_name: str,
    agg_func: str = 'sum'
) -> Optional[Any]:
    """
    Extract and aggregate a value from results DataFrames.
    
    Args:
        results: Dictionary of DataFrames
        value_mapping: Mapping of variable names to df/column locations
        var_name: Name of the variable to extract
        agg_func: Aggregation function ('sum', 'max', 'min', 'mean', 'series')
    
    Returns:
        Aggregated value or None if not found
    """
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
    """Extract values needed for security KPIs."""
    values = {}
    
    # Total hours in simulation - auf ganze Stunden runden
    values['total_hours'] = round(len(results['Verbrauch']) * 0.25)
    
    # Unserved energy from balance
    balance = _get_value(results, value_mapping, 'balance_after_flex', 'series')
    if balance is not None:
        deficit_mask = balance < 0
        values['total_unserved_mwh'] = abs(balance[deficit_mask].sum())
        values['max_unserved_mw'] = abs(balance[deficit_mask].min()) * 4
        values['deficit_hours'] = deficit_mask.sum() * 0.25
    else:
        values['total_unserved_mwh'] = 0
        values['max_unserved_mw'] = 0
        values['deficit_hours'] = 0
    
    # Load values
    values['total_load_mwh'] = _get_value(results, value_mapping, 'total_load_mwh', 'sum') or 0
    values['max_load_mw'] = (_get_value(results, value_mapping, 'total_load_mwh', 'max') or 0) * 4
    
    # H2 storage
    year_str = str(year)
    if 'h2_storage' in storage_config and year_str in storage_config['h2_storage']:
        values['h2_capacity_mwh'] = storage_config['h2_storage'][year_str]['installed_capacity_mwh']
        values['h2_soc_avg_mwh'] = _get_value(results, value_mapping, 'h2_soc', 'mean') or 0
    else:
        values['h2_capacity_mwh'] = 0
        values['h2_soc_avg_mwh'] = 0
    
    return values


def _extract_ecology_values(
    results: Dict[str, pd.DataFrame],
    value_mapping: Dict[str, Dict[str, str]]
) -> Dict[str, float]:
    """Extract values needed for ecology KPIs."""
    values = {}
    
    # Renewable generation
    renewable_sources = ['wind_onshore_mwh', 'wind_offshore_mwh', 'pv_mwh', 'biomass_mwh', 'hydro_mwh']
    values['renewable_generation_mwh'] = sum(
        _get_value(results, value_mapping, source, 'sum') or 0
        for source in renewable_sources
    )
    
    # Fossil generation
    values['fossil_generation_mwh'] = _get_value(results, value_mapping, 'gas_mwh', 'sum') or 0
    
    # Total generation
    values['total_generation_mwh'] = _get_value(results, value_mapping, 'production_total', 'sum') or 0
    
    # Fallback: Falls production_total nicht verfügbar, berechne aus Komponenten
    if values['total_generation_mwh'] == 0:
        values['total_generation_mwh'] = values['renewable_generation_mwh'] + values['fossil_generation_mwh']
    
    # Curtailment
    balance = _get_value(results, value_mapping, 'balance_after_flex', 'series')
    if balance is not None:
        values['curtailment_mwh'] = balance[balance > 0].sum()
    else:
        values['curtailment_mwh'] = 0
    
    # CO2 emissions (MWh * 1000 * gCO2/kWh / 1_000_000 = tons)
    values['total_co2_tons'] = (
        values['fossil_generation_mwh'] * 1000 * CO2_FACTORS['gas'] / 1_000_000
    )
    
    # Get total load for worst case calculation
    total_load = _get_value(results, value_mapping, 'total_load_mwh', 'sum') or 0
    values['worst_case_co2_tons'] = (
        total_load * 1000 * CO2_FACTORS['worst_case'] / 1_000_000
    )
    
    return values


def _extract_economy_values(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Dict[str, Dict[str, str]],
    unserved_mwh: float
) -> Dict[str, float]:
    """Extract values needed for economy KPIs."""
    values = {}
    
    # Import equals unserved energy
    values['import_mwh'] = unserved_mwh
    
    # Storage throughput and capacity
    storage_mapping = {
        'battery_storage': ('battery_charged', 'battery_discharged'),
        'pumped_hydro_storage': ('pumped_storage_charged', 'pumped_storage_discharged'),
        'h2_storage': ('h2_charged', 'h2_discharged')
    }
    
    total_charged = 0
    total_discharged = 0
    total_charge_capacity_mw = 0
    
    year_str = str(year)
    for storage_key, (charged_key, discharged_key) in storage_mapping.items():
        # Get capacity from config
        if storage_key in storage_config and year_str in storage_config[storage_key]:
            config = storage_config[storage_key][year_str]
            total_charge_capacity_mw += config['max_charge_power_mw']
        
        # Get actual charged/discharged
        total_charged += _get_value(results, value_mapping, charged_key, 'sum') or 0
        total_discharged += _get_value(results, value_mapping, discharged_key, 'sum') or 0
    
    values['storage_charged_mwh'] = total_charged
    values['storage_discharged_mwh'] = total_discharged
    values['storage_total_throughput_mwh'] = total_charged + total_discharged
    values['storage_charge_capacity_mw'] = total_charge_capacity_mw
    
    # LCOE from Wirtschaftlichkeit
    if 'Wirtschaftlichkeit' in results and isinstance(results['Wirtschaftlichkeit'], dict):
        values['system_lcoe'] = results['Wirtschaftlichkeit'].get('system_lco_e')
    else:
        values['system_lcoe'] = None
    
    return values


# ============================================================================
# HELPER FUNCTIONS - KPI CALCULATION
# ============================================================================

def _safe_ratio(numerator: float, denominator: float) -> float:
    """Calculate ratio safely, returning 0 if denominator is 0."""
    return numerator / denominator if denominator > 0 else 0


def _calculate_security_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Calculate security KPIs from extracted values."""
    return {
        'unserved_mwh': _safe_ratio(values['total_unserved_mwh'], values['total_load_mwh']),
        'max_unserved_mw': _safe_ratio(values['max_unserved_mw'], values['max_load_mw']),
        'deficit_h': _safe_ratio(values['deficit_hours'], values['total_hours']),
        'h2_soc': _safe_ratio(values['h2_soc_avg_mwh'], values['h2_capacity_mwh'])
    }


def _calculate_ecology_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Calculate ecology KPIs from extracted values."""
    return {
        'co2_intensity': _safe_ratio(values['total_co2_tons'], values['worst_case_co2_tons']),
        'curtailment_mwh': _safe_ratio(values['curtailment_mwh'], values['renewable_generation_mwh']),
        'fossil_share': _safe_ratio(values['fossil_generation_mwh'], values['total_generation_mwh'])
    }


def _calculate_economy_kpis(values: Dict[str, float]) -> Dict[str, float]:
    """Calculate economy KPIs from extracted values."""
    # Get total load for import dependency
    # Note: This should be passed in values dict
    total_load = values.get('total_load_mwh', 0)
    
    # Storage utilization: throughput / max possible throughput
    max_possible_throughput = values['storage_charge_capacity_mw'] * values.get('total_hours', 0)
    
    return {
        'system_cost_index': values['system_lcoe'] if values['system_lcoe'] is not None else 0,
        'import_dependency': _safe_ratio(values['import_mwh'], total_load),
        'storage_utilization': _safe_ratio(values['storage_total_throughput_mwh'], max_possible_throughput)
    }


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def get_score_and_kpis(
    results: Dict[str, pd.DataFrame],
    storage_config: Dict[str, Any],
    year: int,
    value_mapping: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Calculate scoring and KPIs based on simulation results.
    
    Args:
        results: Simulation results with DataFrames:
            - 'Verbrauch': Consumption data
            - 'Erzeugung': Generation data
            - 'E-Mobility': E-Mobility data
            - 'Speicher': Storage data
            - 'Bilanz_vor_Flex': Balance before flexibility
            - 'Bilanz_nach_Flex': Balance after flexibility
            - 'Wirtschaftlichkeit': Economic metrics (dict)
        storage_config: Storage capacities from YAML configuration
        year: Simulation year (e.g. 2030, 2045)
        value_mapping: Optional custom mapping for value extraction
    
    Returns:
        Dictionary containing:
            - 'security': Security KPIs
            - 'ecology': Ecology KPIs
            - 'economy': Economy KPIs
            - 'raw_values': All extracted values for debugging
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
    
    # Combine all values
    all_values = {**security_values, **ecology_values, **economy_values}
    
    # Calculate KPIs
    kpis = {
        'security': _calculate_security_kpis(all_values),
        'ecology': _calculate_ecology_kpis(all_values),
        'economy': _calculate_economy_kpis(all_values),
        'raw_values': all_values
    }
    
    return kpis