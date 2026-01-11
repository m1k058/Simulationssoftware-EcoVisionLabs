from pathlib import Path
import pandas as pd
import yaml

# Dateiname deiner Excel
# INPUT_FILE = 'Logik E-Mobilität.xlsx'
INPUT_FILE = Path(__file__).parent / 'Logik E-Mobilität.xlsx'

def extract_data():
    print("--- 1. Extrahiere Parameter für YAML ---")
    # Parameter laden
    try:
        df_params = pd.read_excel(INPUT_FILE, sheet_name='00_Params_EV', header=None, index_col=1)
        params = df_params[2].to_dict() # Werte aus Spalte C (Index 2)

        # Mapping auf deine Projekt-Konventionen (snake_case)
        yaml_config = {
            "emobility": {
                "active": True,
                "n_cars": int(params.get('N_cars', 5000000)),
                "battery_capacity_kwh": float(params.get('E_batt_car', 50)),
                "charging_power_kw": float(params.get('P_ch_car_max', 11)),
                "efficiency": float(params.get('eta_ch', 0.95)),
                "soc_limits": {
                    "min_day": float(params.get('SOC_min_day', 0.4)),
                    "min_night": float(params.get('SOC_min_night', 0.2)),
                    "target_morning": float(params.get('SOC_target_depart', 0.6))
                },
                "grid_thresholds_mw": {
                    "surplus": -200.0,  # Excel Logik war negativ = Überschuss
                    "deficit": 200.0
                }
            }
        }

        print("\nKopiere diesen Block in deine Szenario-YAML oder config.json:")
        print(yaml.dump(yaml_config, default_flow_style=False))

    except Exception as e:
        print(f"Fehler bei Parametern: {e}")

    print("\n--- 2. Extrahiere Profile für CSV ---")
    try:
        # Simulationsdaten laden
        df_sim = pd.read_excel(INPUT_FILE, sheet_name='EV_V2_Sim')

        # Wir brauchen nur die INPUTS, nicht die Ergebnisse der Excel
        # Mapping: Excel-Name -> Dein Projekt-Stil
        df_export = pd.DataFrame()
        df_export['Zeitpunkt'] = df_sim['Zeitpunkt']
        df_export['plug_share'] = df_sim['angeschl. Quote']
        df_export['consumption_driving_kw'] = df_sim['Fahrverbrauchsleistung'] # Wichtig: Einheit klären
        df_export['soc_min_share'] = df_sim['SOC_min']  # Dynamisches Minimum (Tag/Nacht) aus Excel

        # Speichern in raw-data Ordner (oder wo deine Profile liegen)
        # Pfad relativ zum Skript anpassen (zwei Ebenen hoch zu source-code, dann zu raw-data)
        output_path = Path(__file__).parent.parent.parent.parent / "raw-data"
        output_csv = output_path / "emobility_profile_S2030.csv"
        
        # Sicherstellen, dass Verzeichnis existiert
        output_path.mkdir(parents=True, exist_ok=True)
        
        df_export.to_csv(output_csv, index=False)
        print(f"Datei gespeichert: {output_csv}")

    except Exception as e:
        print(f"Fehler bei Profilen: {e}")

if __name__ == "__main__":
    extract_data()
