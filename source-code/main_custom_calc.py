"""
EcoVisionLabs - Analyse der Verteilung Erneuerbarer Energien
Visualisiert die zeitliche Verteilung des Anteils erneuerbarer Energien am Stromverbrauch
"""

import locale
import os
import warnings
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime
from pathlib import Path

from errors import AppError, WarningMessage, DataProcessingError
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing import gen, col
from io_handler import save_data
import data_processing.simulation as sim

try:
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
except locale.Error:
    # Fallback für andere Systeme (z.B. Windows)
    locale.setlocale(locale.LC_ALL, 'German_Germany.1252')


def main():
    """Hauptfunktion: Lädt Daten, berechnet EE-Anteil und visualisiert die Verteilung"""
    try:
        # ============================================================
        # DATEN LADEN UND VORBEREITEN
        # ============================================================
        
        # Konfiguration und DataManager initialisieren
        cfg = ConfigManager(Path("source-code/config.json"))
        dm = DataManager(config_manager=cfg)

        print("\n ---------- DATEN EINGELADEN ---------- \n\n")

        # Datensätze laden
        genDf = dm.get(1)  # Erzeugungsdaten
        conDf = dm.get(2)  # Verbrauchsdaten
        # Prognosedaten: config.json uses id 4 for Prognosedaten_Studien
        progDf = dm.get(4) # Prognosedaten

        # ============================================================
        # Wähle Daten
        # ============================================================

        prog_dat_studie = 'Agora'   # 'Agora' | 'BDI - Klimapfade 2.0' | 'dena - KN100' | 'BMWK - LFS TN-Strom'
                                    # 'Ariadne - REMIND-Mix' | 'Ariadne - REMod-Mix' | 'Ariadne - TIMES PanEU-Mix'
        ref_jahr = 2023             # Referenzjahr im Verbrauchsdatensatz
        simu_jahr_von = 2026            # Simulationsjahr von
        simu_jahr_bis = 2030            # Simulationsjahr bis
        use_load_profile = True     # Lastprofil S25 verwenden (empfohlen für realistische Lastkurven)
                                    # True = Lastprofil S25 mit realistischen Tages-/Monatsschwankungen
                                    # False = Einfache lineare Skalierung (alte Methode)


        # ============================================================

        df_simulation = sim.calc_scaled_consumption_multiyear(conDf, progDf,
                                            prog_dat_studie, simu_jahr_von, simu_jahr_bis,
                                            ref_jahr=ref_jahr, use_load_profile=use_load_profile)
        
        
        #vorbereitung des Dateinamens mit Zeitstempel
        timestamp = datetime.now().strftime("%d%m%Y_%H%M")
        outdir = Path("output") / "csv"
        outdir.mkdir(parents=True, exist_ok=True)
        if use_load_profile:
            lp = "mit_lastprofil"
        else:
            lp = ""
        filename = outdir / f"Skalierte_Netzlast_{lp}_{simu_jahr_von}-{simu_jahr_bis} (ref-{ref_jahr}, studie-{prog_dat_studie})_{timestamp}.csv"

        # Schreibe die CSV in die Datei (pandas akzeptiert Path-Objekte)
        if df_simulation.to_csv(filename, index=False, sep=';', encoding='utf-8', decimal=',') is None:
            print(f"\n{filename} gespeichert unter {outdir}\n")
        else:
            raise RuntimeError(f"Fehler beim Speichern der Datei {filename}")

    
    except AppError as e:
        print(f"\n{e}")

    except WarningMessage as w:
        warnings.warn(str(w), WarningMessage)

    except Exception as e:
        print(f"\nUnexpected error ({type(e).__name__}): {e}")

    finally:
        print("\nProgram finished.\n")


if __name__ == "__main__":
    main()

