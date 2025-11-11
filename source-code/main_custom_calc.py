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
from matplotlib.colors import TwoSlopeNorm

from errors import AppError, WarningMessage, DataProcessingError
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing import gen, col
from io_handler import save_data_excel

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
        progDf = dm.get(3) # Prognosedaten

        # Ziehe ein Referenzjahr aus der den Dataframe
        df_refJahr = conDf[(conDf["Zeitpunkt"] >= "01.01.2023 00:00") & (conDf["Zeitpunkt"] <= "31.12.2023 23:59")]
        
        Gesammtenergie_RefJahr = col.sum_all(df_refJahr)

        formatierte_zahl = locale.format_string("%.2f", Gesammtenergie_RefJahr, grouping=True)

        print(f"Gesamter Energieverbrauch im Referenzjahr: {formatierte_zahl} [TWh]")

    
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

