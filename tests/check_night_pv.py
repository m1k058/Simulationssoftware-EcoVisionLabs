
import pandas as pd
import sys
from pathlib import Path

# Add source-code to path
sys.path.insert(0, str(Path(__file__).parent.parent / "source-code"))

from config_manager import ConfigManager
from data_manager import DataManager
from scenario_manager import ScenarioManager
import data_processing.simulation as simu

def check_night_pv():
    print("Checking Night PV...")
    cfg = ConfigManager()
    dm = DataManager(cfg)
    sm = ScenarioManager()
    
    scenario_path = Path("scenarios/Szenario 2030/Agora 2030_1.0.yaml")
    sm.load_scenario(scenario_path)
    
    year = 2030
    results = simu.kobi(cfg, dm, sm, years=[year])
    df_prod = results[year]["production"]
    
    # Filter night hours
    night_mask = (df_prod["Zeitpunkt"].dt.hour < 4) | (df_prod["Zeitpunkt"].dt.hour > 22)
    night_df = df_prod[night_mask].copy()
    
    # Filter non-zero PV
    pv_night = night_df[night_df["Photovoltaik [MWh]"] > 0.1] # Filter noise
    
    if not pv_night.empty:
        print(f"Found {len(pv_night)} night-time intervals with PV > 0.1 MWh")
        print(pv_night[["Zeitpunkt", "Photovoltaik [MWh]"]].head(10))
        print("...")
        print(pv_night[["Zeitpunkt", "Photovoltaik [MWh]"]].tail(10))
    else:
        print("No significant night-time PV found.")

if __name__ == "__main__":
    check_night_pv()
