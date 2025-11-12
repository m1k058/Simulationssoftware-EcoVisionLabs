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

        # ============================================================
        # Wähle Daten
        # ============================================================

        prog_dat_studie = 'Agora'
        prog_dat_jahr = 2035
        ref_jahr = 2023
        simu_jahr = 2030
        # ============================================================

        # nach jahr im Verbrauchsdatensatz suchen
        ist_ref_jahr_vorhanden = (conDf['Zeitpunkt'].dt.year == ref_jahr).any()

        # Ziehe ein Referenzjahr aus der den Dataframe
        if ist_ref_jahr_vorhanden:
            df_refJahr = conDf[(conDf["Zeitpunkt"] >= f"01.01.{ref_jahr} 00:00") & (conDf["Zeitpunkt"] <= f"31.12.{ref_jahr} 23:59")]
        else:
            print(f"Referenzjahr {ref_jahr} nicht im Verbrauchsdatensatz gefunden.")
        
        # Berechne die Gesammtenergie im Referenzjahr
        Gesamtenergie_RefJahr = col.get_column_total(df_refJahr, "Netzlast [MWh]") / 1000000  # in TWh

        formatierte_zahl = locale.format_string("%.8f", Gesamtenergie_RefJahr, grouping=True)
        print(f"Gesamter Energieverbrauch im Referenzjahr: {formatierte_zahl} [TWh]\n")

        # Hol Ziel-Wert aus Prognosedaten (robuste Auswahl + klare Fehlermeldung)
        sel = progDf.loc[(progDf['Jahr'] == prog_dat_jahr) & (progDf['Studie'] == prog_dat_studie), 'Bruttostromverbrauch [TWh]']
        if sel.empty:
            print(f"Keine Prognose-Zeile gefunden für Studie='{prog_dat_studie}' und Jahr={prog_dat_jahr}")
        try:
            zielWert_Studie = float(sel.iat[0])
        except Exception as e:
            print(f"Fehler beim Lesen des Zielwerts aus Prognosedaten: {e}")

        formatierte_zahl = locale.format_string("%.8f", zielWert_Studie, grouping=True)
        print(f"Gesamter Energieverbrauch im Prognosejahr: {formatierte_zahl} [TWh]\n")

        # Berechne Gesamtenergie Simualtionjahr (interpoliert, falls nötig)
        if simu_jahr != prog_dat_jahr:
            Gesamtenergie_simu_jahr = np.interp(simu_jahr, [ref_jahr, prog_dat_jahr], [Gesamtenergie_RefJahr, zielWert_Studie])
        else:
            Gesamtenergie_simu_jahr = zielWert_Studie

        formatierte_zahl = locale.format_string("%.8f", Gesamtenergie_simu_jahr, grouping=True)
        print(f"Gesamter Energieverbrauch im Simulationsjahr: {formatierte_zahl} [TWh]\n")
        
        # Berechne den Skalierungsfaktor
        faktor = zielWert_Studie / Gesamtenergie_simu_jahr

        formatierte_zahl = locale.format_string("%.14f", faktor, grouping=True)
        print(f"Berechneter Faktor: {formatierte_zahl}\n")

        # Skaliere den Energieverbrauch im Referenzjahr mit dem Faktor
        jahr_offset = simu_jahr - ref_jahr
        df_simulation = pd.DataFrame({
            'Datum von': pd.to_datetime(df_refJahr['Datum von']) + pd.DateOffset(years=jahr_offset),
            'Datum bis': pd.to_datetime(df_refJahr['Datum bis']) + pd.DateOffset(years=jahr_offset),
            'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=jahr_offset),
            'Skalierter Netzlast [MWh]': df_refJahr['Netzlast [MWh]'] * faktor
            })
        
        col.show_first_rows(df_simulation)

        #vorbereitung des Dateinamens mit Zeitstempel
        timestamp = datetime.now().strftime("%d%m%Y_%H%M")
        outdir = Path("output") / "csv"
        outdir.mkdir(parents=True, exist_ok=True)
        filename = outdir / f"Skalierte_Netzlast_{simu_jahr} (ref-{ref_jahr}, prog-{prog_dat_jahr}, studie-{prog_dat_studie})_{timestamp}.csv"

        # Schreibe die CSV in die Datei (pandas akzeptiert Path-Objekte)
        if df_simulation.to_csv(filename, index=False, sep=';', encoding='utf-8', decimal=',') is None:
            print(f"\n{filename} gespeichert unter {outdir}\n")
        else:
            print(f"Fehler beim Speichern der Datei {filename}")

    
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

