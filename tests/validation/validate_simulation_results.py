
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add source-code to path
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

from config_manager import ConfigManager
from data_manager import DataManager
from scenario_manager import ScenarioManager
import data_processing.simulation as simu

def validate_results():
    print("=== STARTING VALIDATION RUN ===")
    
    # 1. Setup Managers
    print("Initializing Managers...")
    try:
        cfg = ConfigManager()
        dm = DataManager(cfg)
        sm = ScenarioManager()
    except Exception as e:
        print(f"FATAL: Could not initialize managers: {e}")
        return

    # 2. Load Scenario
    scenario_path = Path("scenarios/Szenario 2030/Agora 2030_1.0.yaml")
    if not scenario_path.exists():
        print(f"FATAL: Scenario file not found at {scenario_path}")
        return
    
    print(f"Loading scenario: {scenario_path}")
    sm.load_scenario(scenario_path)
    
    # 3. Run Simulation for 2030
    year = 2030
    print(f"Running simulation for year {year}...")
    try:
        results = simu.kobi(cfg, dm, sm, years=[year])
        data = results[year]
    except Exception as e:
        print(f"FATAL: Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Analyze Consumption
    print("\n--- ANALYZING CONSUMPTION ---")
    df_cons = data["consumption"]
    
    # Check 1: Totals vs Targets
    targets = sm.scenario_data["target_load_demand_twh"]
    target_h = targets["Haushalt_Basis"][year]
    target_g = targets["Gewerbe_Basis"][year]
    target_l = targets["Landwirtschaft_Basis"][year]
    target_total = target_h + target_g + target_l
    
    actual_h = df_cons["Haushalte [MWh]"].sum() / 1e6
    actual_g = df_cons["Gewerbe [MWh]"].sum() / 1e6
    actual_l = df_cons["Landwirtschaft [MWh]"].sum() / 1e6
    actual_total = df_cons["Gesamt [MWh]"].sum() / 1e6
    
    print(f"Target Total: {target_total:.4f} TWh | Actual Total: {actual_total:.4f} TWh")
    print(f"  Haushalte: Target {target_h:.2f} | Actual {actual_h:.4f} (Diff: {actual_h-target_h:.6f})")
    print(f"  Gewerbe:   Target {target_g:.2f} | Actual {actual_g:.4f} (Diff: {actual_g-target_g:.6f})")
    print(f"  Landwirt.: Target {target_l:.2f} | Actual {actual_l:.4f} (Diff: {actual_l-target_l:.6f})")
    
    if abs(actual_total - target_total) > 0.01:
        print("❌ WARNING: Significant deviation in total consumption!")
    else:
        print("✅ Consumption totals match targets.")

    # Check 2: Plausibility
    if (df_cons.select_dtypes(include=np.number) < 0).any().any():
        print("❌ CRITICAL: Negative values found in consumption!")
    else:
        print("✅ No negative consumption values.")
        
    # Check 3: Profile shape (simple check)
    # Summer vs Winter (Winter should be higher generally for households)
    winter_mean = df_cons[df_cons["Zeitpunkt"].dt.month.isin([1, 2, 12])]["Haushalte [MWh]"].mean()
    summer_mean = df_cons[df_cons["Zeitpunkt"].dt.month.isin([6, 7, 8])]["Haushalte [MWh]"].mean()
    print(f"  Winter Mean (H): {winter_mean:.2f} MWh | Summer Mean (H): {summer_mean:.2f} MWh")
    if winter_mean > summer_mean:
        print("✅ Seasonality check passed (Winter > Summer).")
    else:
        print("⚠️ WARNING: Summer consumption higher than Winter! This is unusual for standard household profiles (H0).")
        print("   Possible causes: ")
        print("   1. Raw data in 'BDEW-Standardlastprofile-H25.csv' might be inverted or incorrect.")
        print("   2. The profile 'H25' might specifically model cooling loads (unlikely for standard BDEW).")
        print("   3. Dynamization (which usually boosts winter) is disabled.")

    # Check 4: Smoothness / Jumps
    # Calculate day-to-day difference of daily sums
    daily_sum = df_cons.groupby(df_cons["Zeitpunkt"].dt.date)["Haushalte [MWh]"].sum()
    daily_diff = daily_sum.diff().abs()
    max_diff = daily_diff.max()
    max_diff_date = daily_diff.idxmax()
    mean_daily = daily_sum.mean()
    
    print(f"  Max Day-to-Day Jump: {max_diff:.2f} MWh ({(max_diff/mean_daily)*100:.1f}% of mean daily consumption)")
    print(f"  Jump occurred on: {max_diff_date}")
    
    if (max_diff/mean_daily) > 0.5:
        print("⚠️ WARNING: Very large jump in daily consumption detected!")

    # 5. Analyze Production
    print("\n--- ANALYZING PRODUCTION ---")
    df_prod = data["production"]
    
    # Check 1: No negatives
    prod_cols = [c for c in df_prod.columns if "[MWh]" in c]
    if (df_prod[prod_cols] < 0).any().any():
        print("❌ CRITICAL: Negative values found in production!")
    else:
        print("✅ No negative production values.")

    # Check 2: Capacity Factors Plausibility
    # PV should be 0 at night
    night_pv = df_prod[ (df_prod["Zeitpunkt"].dt.hour < 4) | (df_prod["Zeitpunkt"].dt.hour > 22) ]["Photovoltaik [MWh]"].sum()
    print(f"  Night-time PV Production: {night_pv:.4f} MWh")
    if night_pv > 1.0: # Allow small floating point errors
        print("❌ WARNING: Significant PV production at night!")
    else:
        print("✅ PV Night check passed.")

    # 6. Analyze Balance
    print("\n--- ANALYZING BALANCE ---")
    df_bal = data["balance"]
    
    # Check consistency
    # Re-calculate balance
    calc_bal = df_bal["Produktion [MWh]"] - df_bal["Verbrauch [MWh]"]
    diff = (df_bal["Bilanz [MWh]"] - calc_bal).abs().max()
    print(f"  Max deviation in balance calculation: {diff:.10f}")
    if diff < 1e-9:
        print("✅ Balance calculation consistent.")
    else:
        print("❌ CRITICAL: Balance calculation mismatch!")

    # 7. Analyze Storage
    print("\n--- ANALYZING STORAGE ---")
    df_stor = data["storage"] # This is the final result (H2 storage df which contains previous steps usually?)
    # Wait, simulate_hydrogen_storage returns a DF. Does it contain previous storage columns?
    # Looking at simulate_storage_generic:
    # "Nimm alle bestehenden Spalten aus df und füge die neuen Speicherwerte hinzu"
    # So yes, it should accumulate.
    
    storage_types = ["Batteriespeicher", "Pumpspeicher", "Wasserstoffspeicher"]
    
    for stype in storage_types:
        soc_col = f"{stype} SOC MWh"
        if soc_col in df_stor.columns:
            print(f"  Checking {stype}...")
            soc = df_stor[soc_col]
            
            # Check Min/Max SOC
            min_soc = soc.min()
            max_soc = soc.max()
            
            # Get capacity from scenario to verify limits
            cap_data = sm.get_storage_capacities("battery_storage" if "Batterie" in stype else "pumped_hydro_storage" if "Pump" in stype else "h2_storage", year)
            installed_cap = cap_data["installed_capacity_mwh"]
            
            print(f"    SOC Range: {min_soc:.2f} - {max_soc:.2f} MWh (Capacity: {installed_cap})")
            
            if min_soc < -1e-6:
                print(f"❌ CRITICAL: Negative SOC in {stype}!")
            elif max_soc > installed_cap + 1e-6:
                print(f"❌ CRITICAL: SOC exceeds capacity in {stype}!")
            else:
                print(f"✅ SOC limits respected for {stype}.")
                
            # Check Activity
            charged = df_stor[f"{stype} Geladene MWh"].sum()
            discharged = df_stor[f"{stype} Entladene MWh"].sum()
            print(f"    Total Charged: {charged:.2f} MWh | Total Discharged: {discharged:.2f} MWh")
            if charged == 0 and discharged == 0:
                print(f"⚠️ WARNING: {stype} was never used!")
        else:
            print(f"⚠️ {stype} columns not found in result.")

    print("\n=== VALIDATION COMPLETE ===")

if __name__ == "__main__":
    validate_results()
