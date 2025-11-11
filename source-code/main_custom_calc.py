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

        # Ziehe ein Referenzjahr aus der den Dataframe
        df_refJahr = conDf[(conDf["Zeitpunkt"] >= "01.01.2023 00:00") & (conDf["Zeitpunkt"] <= "31.12.2023 23:59")]
        
        # Berechne die Gesammtenergie im Referenzjahr
        Gesamtenergie_RefJahr = col.get_column_total(df_refJahr, "Netzlast [MWh]") / 1_000_000  # in TWh

        formatierte_zahl = locale.format_string("%.2f", Gesamtenergie_RefJahr, grouping=True)

        print(f"Gesamter Energieverbrauch im Referenzjahr: {formatierte_zahl} [TWh]")

        # --- Vorbereitung Prognosedaten: Spalten säubern und Typen sicherstellen
        progDf.columns = progDf.columns.str.strip()
        if 'Studie' in progDf.columns:
            progDf['Studie'] = progDf['Studie'].astype(str).str.strip()
        else:
            raise DataProcessingError("Prognosedaten enthalten keine Spalte 'Studie'.")

        if 'Jahr' in progDf.columns:
            # Falls Jahr als String eingelesen wurde, sauber nach Int konvertieren
            progDf['Jahr'] = pd.to_numeric(progDf['Jahr'], errors='coerce').astype('Int64')
        else:
            raise DataProcessingError("Prognosedaten enthalten keine Spalte 'Jahr'.")

        # Hol Ziel-Wert aus Prognosedaten (robuste Auswahl + klare Fehlermeldung)
        sel = progDf.loc[(progDf['Jahr'] == 2035) & (progDf['Studie'] == 'Agora'), 'Bruttostromverbrauch [TWh]']
        if sel.empty:
            raise DataProcessingError("Keine Prognose-Zeile gefunden für Studie='Agora' und Jahr=2035")
        try:
            zielWert_Studie = float(sel.iat[0])
        except Exception as e:
            raise DataProcessingError(f"Fehler beim Lesen des Zielwerts aus Prognosedaten: {e}")

        # Faktor berechnen
        faktor = zielWert_Studie / Gesamtenergie_RefJahr

        # Skaliere den Energieverbrauch im Referenzjahr mit dem Faktor
        df_simulation = pd.DataFrame({
            'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=12),
            'Skalierter Netzlast [MWh]': df_refJahr['Netzlast [MWh]'] * faktor
            })
        
        # Anzeige der ersten Zeilen des skalierten DataFrames
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        # Erstelle Ausgabeordner (Verzeichnis) und Dateinamen korrekt
        outdir = Path("output") / "csv"
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / f"Skalierte_Netzlast_2035_{timestamp}.csv"

        # Schreibe die CSV in die Datei (pandas akzeptiert Path-Objekte)
        df_simulation.to_csv(filename, index=False, sep=';', encoding='utf-8')
        print(f"\n{filename} gespeichert unter {outdir}\n")

    
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

