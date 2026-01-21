import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

# --- IMPORT DER ECHTEN SIMULATIONS-LOGIK ---
import sys
import os

# Ermittle den absoluten Pfad zum 'source-code' Verzeichnis
# (Das Skript liegt in source-code/plotting, wir wollen nach source-code)
current_dir = os.path.dirname(os.path.abspath(__file__))
source_code_dir = os.path.dirname(current_dir)
if source_code_dir not in sys.path:
    sys.path.append(source_code_dir)

try:
    from data_processing.e_mobility_simulation import (
        generate_ev_profile, 
        EVScenarioParams, 
        EVConfigParams,
        WORKPLACE_V2G_FACTOR
    )
except ImportError as e:
    print(f"Fehler beim Import: {e}")
    print(f"Versuchter Pfad: {source_code_dir}")
    sys.exit(1) 

def plot_simulation_logic():
    # 1. Parameter initialisieren (Nimmt automatisch die Defaults aus der Klasse!)
    # Wir nutzen die Defaults aus e_mobility_simulation.py, damit Änderungen dort direkt wirken.
    scen_params = EVScenarioParams() 
    config_params = EVConfigParams() # Nimmt Defaults (11kW, etc.)

    # 2. Zeitachse generieren (1 Tag, 15 min Auflösung)
    # Wir nehmen einen Wochentag (Montag, 2030-01-07)
    dates = pd.date_range(start="2030-01-07 00:00", end="2030-01-07 23:45", freq="15min")
    timestamps = pd.Series(dates)

    # 3. ECHTE Profil-Generierung aufrufen
    # Das holt dir exakt die Kurve inkl. deiner 0.9/1.1 Gewichte aus dem Code
    df_profile = generate_ev_profile(timestamps, scen_params, config_params)

    # 4. Daten extrahieren
    t_hours = df_profile['Zeitpunkt'].dt.hour + df_profile['Zeitpunkt'].dt.minute / 60.0
    
    # Fahrprofil (normiert für Optik)
    drive_power = df_profile['drive_power_kw']
    # Normierung auf 0..1 für den Hintergrund-Plot
    drive_norm = (drive_power - drive_power.min()) / (drive_power.max() - drive_power.min())

    # 5. V2G-Logik nachbilden (für Visualisierung)
    # Die Workplace-Logik steckt in 'simulate_emobility_fleet' (Loop), 
    # daher rechnen wir sie hier kurz nach für den Plot.
    
    # Basis: Plug Share aus dem Profil
    plug_share = df_profile['plug_share'] # Das ist schon inkl. plug_share_max
    
    # Zeiten aus Params
    t_dep_val = int(scen_params.t_depart.split(":")[0]) + int(scen_params.t_depart.split(":")[1])/60
    t_arr_val = int(scen_params.t_arrive.split(":")[0]) + int(scen_params.t_arrive.split(":")[1])/60
    
    # Arbeitszeit-Check
    is_work_time = (t_hours >= t_dep_val) & (t_hours < t_arr_val)
    
    # V2G Kapazität berechnen
    # Formel: N * Share * P_max * Faktor
    n_ev = scen_params.N_cars * scen_params.s_EV
    p_max_mw = config_params.P_dis_car_max / 1000.0 # in MW
    
    # V2G Share Array
    current_v2g_share = np.full(len(timestamps), scen_params.v2g_share)
    # Apply Workplace Factor
    current_v2g_share[is_work_time] *= WORKPLACE_V2G_FACTOR
    
    # Finale Leistung [GW]
    v2g_power_gw = (plug_share * n_ev * p_max_mw * current_v2g_share) / 1000.0
    
    # Ladeleistung (V1G) zum Vergleich [GW]
    # Hier gilt der volle plug_share (kein V2G-Faktor)
    charge_power_gw = (plug_share * n_ev * p_max_mw) / 1000.0

    # --- 6. PLOT ---
    fig, ax1 = plt.subplots(figsize=(12, 7))

    # Hintergrund: Fahr-Aktivität
    ax1.fill_between(t_hours, 0, drive_norm, color='red', alpha=0.1, label='Fahr-Aktivität (aus Simulation)')
    ax1.plot(t_hours, drive_norm, 'r-', linewidth=1.5)
    ax1.set_ylabel('Aktivitäts-Index (Normiert)', color='red', fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='red')
    ax1.set_xlabel('Uhrzeit [h]', fontweight='bold')
    ax1.set_xlim(0, 24)
    ax1.set_ylim(bottom=0) # Erzwinge Nullpunkt an der x-Achse für korrekte Ausrichtung
    ax1.set_xticks(np.arange(0, 25, 2))
    ax1.grid(True, alpha=0.3)

    # V2 Achse: Leistung
    ax2 = ax1.twinx()
    # V1G (Laden)
    ax2.plot(t_hours, charge_power_gw, 'g--', linewidth=2, label='Max. Lade-Leistung (V1G) [GW]')
    # V2G (Entladen)
    ax2.plot(t_hours, v2g_power_gw, 'b-', linewidth=3, label=f'Max. V2G-Leistung [GW] (Faktor {WORKPLACE_V2G_FACTOR})')
    
    # Fülle den Bereich zwischen V1G und V2G, um den "Verlust" durch Workplace-Restriktion zu zeigen
    ax2.fill_between(t_hours, v2g_power_gw, charge_power_gw, color='gray', alpha=0.1, hatch='///', label='Gesperrt durch Workplace-Faktor')

    ax2.set_ylabel('Verfügbare Flotten-Leistung [GW]', color='navy', fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='navy')
    ax2.set_ylim(bottom=0)

    # Info-Box mit den AUTOMATISCH gezogenen Werten
    info_str = (
        f"PARAMETER (Auto-Import):\n"
        f"Autos: {scen_params.N_cars/1e6:.1f} Mio\n"
        f"Anschlussquote: {scen_params.plug_share_max*100:.0f}%\n"
        f"V2G-Bereitschaft: {scen_params.v2g_share*100:.0f}%\n"
        f"Workplace-Faktor: {WORKPLACE_V2G_FACTOR*100:.0f}%\n"
        f"Arbeitszeit: {scen_params.t_depart} - {scen_params.t_arrive}"
    )
    plt.text(0.02, 0.98, info_str, transform=ax1.transAxes, 
             bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray'), va='top', fontsize=10)

    # Titel
    plt.title('Live-Check: E-Mobilitäts-Logik & Profile', fontsize=14, pad=20)
    
    # Legende
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    plot_simulation_logic()