"""
Debug-Test: Warum ist die Entladung bei v2g_share=0.5 und v2g_share=1.0 gleich?
"""
import sys
import os
sys.path.insert(0, 'source-code')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.e_mobility_simulation import (
    EVScenarioParams,
    EVConfigParams,
    simulate_emobility_fleet,
)

def debug_v2g_share():
    """Detaillierte Analyse der V2G-Logik."""
    
    # Erstelle Testdaten mit starkem Defizit nachts
    n_steps = 96
    start_time = datetime(2030, 6, 15, 0, 0)
    timestamps = [start_time + timedelta(minutes=15*i) for i in range(n_steps)]
    
    df = pd.DataFrame({
        'Zeitpunkt': timestamps,
        'Rest Bilanz [MWh]': [0.0] * n_steps
    })
    
    # Starkes Defizit nur nachts (18:00 - 07:00)
    for i in range(n_steps):
        hour = (i * 15) // 60
        if hour >= 18 or hour < 7:
            df.loc[i, 'Rest Bilanz [MWh]'] = 500.0  # 500 MWh = 2000 MW Defizit
    
    config = EVConfigParams()
    
    # Basis-Parameter
    base_params = {
        's_EV': 0.5,
        'N_cars': 10_000_000,
        'plug_share_max': 0.6,
        'thr_deficit': 100_000.0,  # 100 MW Schwelle
        'thr_surplus': 100_000.0,
    }
    
    print("="*70)
    print("DEBUG: V2G-Share Analyse")
    print("="*70)
    
    # Berechne erwartete Werte
    n_ev = base_params['s_EV'] * base_params['N_cars']  # 5 Mio
    plug_share = base_params['plug_share_max']  # 0.6
    P_dis_max = config.P_dis_car_max  # 11 kW
    
    print(f"\nFlotte:")
    print(f"  n_ev = {n_ev:,.0f}")
    print(f"  plug_share_max = {plug_share}")
    print(f"  P_dis_car_max = {P_dis_max} kW")
    
    for v2g in [1.0, 0.5, 0.3, 0.0]:
        print(f"\n--- v2g_share = {v2g} ---")
        
        # Erwartetes discharge_limit
        discharge_limit = plug_share * n_ev * P_dis_max * v2g
        print(f"  Erwartetes discharge_limit: {discharge_limit:,.0f} kW = {discharge_limit/1000:,.0f} MW")
        
        scenario = EVScenarioParams(**base_params, v2g_share=v2g)
        result = simulate_emobility_fleet(df.copy(), scenario, config)
        
        # Analysiere Ergebnisse nachts
        result['hour'] = result['Zeitpunkt'].dt.hour
        night_data = result[(result['hour'] >= 18) | (result['hour'] < 7)]
        
        max_power = result['EMobility Power [MW]'].max()
        total_discharge = result['EMobility Discharge [MWh]'].sum()
        
        print(f"  Tatsächliche max. Entladeleistung: {max_power*1000:,.0f} kW = {max_power:,.0f} MW")
        print(f"  Gesamte Entladung: {total_discharge:,.2f} MWh")
        
        # Prüfe einige Zeitschritte im Detail
        print(f"\n  Stichprobe Zeitschritte (nachts mit Defizit):")
        sample_indices = [72, 73, 74, 75]  # 18:00-19:00
        for idx in sample_indices:
            row = result.iloc[idx]
            print(f"    {row['Zeitpunkt']}: Power={row['EMobility Power [MW]']:.1f} MW, "
                  f"Discharge={row['EMobility Discharge [MWh]']:.2f} MWh, "
                  f"Charge={row['EMobility Charge [MWh]']:.2f} MWh")

if __name__ == "__main__":
    debug_v2g_share()
