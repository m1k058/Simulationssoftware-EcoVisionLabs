"""
EcoVisionLabs - Analyse der Verteilung Erneuerbarer Energien
Visualisiert die zeitliche Verteilung des Anteils erneuerbarer Energien am Stromverbrauch
"""

import warnings
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing import (
    add_total_generation, 
    add_total_renewable_generation, 
    add_total_conventional_generation,
    add_column_from_other_df
)


def main():
    """Hauptfunktion: Lädt Daten, berechnet EE-Anteil und visualisiert die Verteilung"""
    try:
        # ============================================================
        # DATEN LADEN UND VORBEREITEN
        # ============================================================
        
        # Konfiguration und DataManager initialisieren
        cfg = ConfigManager(Path("source-code/config.json"))
        dm = DataManager(config_manager=cfg)

        # Datensätze laden
        genDf = dm.get(0)  # Erzeugungsdaten
        conDf = dm.get(3)  # Verbrauchsdaten
        
        # Spalten für Gesamt-Erzeugung hinzufügen
        add_total_renewable_generation(genDf)
        add_total_conventional_generation(genDf)
        add_total_generation(genDf)
        add_column_from_other_df(genDf, conDf, "Netzlast [MWh]")

        # ============================================================
        # ANTEIL ERNEUERBARER ENERGIEN BERECHNEN
        # ============================================================
        
        genDf["Anteil Erneuerbare"] = (
            genDf["Gesamterzeugung Erneuerbare [MWh]"] / genDf["Netzlast [MWh]"]
        )
        
        # Zeitpunkt zu datetime konvertieren und Jahr extrahieren
        genDf["Zeitpunkt_dt"] = pd.to_datetime(genDf["Zeitpunkt"], format="%d.%m.%Y %H:%M")
        genDf["Jahr"] = genDf["Zeitpunkt_dt"].dt.year
        
        # ============================================================
        # STATISTIKEN AUSGEBEN
        # ============================================================
        
        print(f"\nMax Anteil Erneuerbare: {genDf['Anteil Erneuerbare'].max():.2%}")
        print(f"Min Anteil Erneuerbare: {genDf['Anteil Erneuerbare'].min():.2%}")
        anzahl_ueber_100 = (genDf['Anteil Erneuerbare'] > 1.0).sum()
        print(f"Anzahl Werte über 100%: {anzahl_ueber_100}")
        
        # ============================================================
        # KATEGORISIERUNG IN PROZENT-BINS
        # ============================================================
        
        bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, float('inf')]
        labels = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%', 
                  '50-60%', '60-70%', '70-80%', '80-90%', '90-100%', '>100%']
        
        genDf["Anteil EE Kategorie"] = pd.cut(
            genDf["Anteil Erneuerbare"], 
            bins=bins, 
            labels=labels, 
            include_lowest=True, 
            right=False
        )
        
        # ============================================================
        # PIVOT-TABELLEN ERSTELLEN
        # ============================================================
        
        # Anzahl der Viertelstunden pro Kategorie und Jahr
        ee_verteilung = pd.crosstab(genDf["Anteil EE Kategorie"], genDf["Jahr"], dropna=False)
        
        print("\nVerteilung Anteil Erneuerbare Energien nach Jahr (Anzahl):")
        print(ee_verteilung)
        
        # Summe pro Jahr berechnen
        summe_pro_jahr = ee_verteilung.sum(axis=0)
        print("\n\nSumme Viertelstunden pro Jahr:")
        print(summe_pro_jahr)
        
        # Prozentuale Verteilung berechnen
        ee_verteilung_prozent = ee_verteilung.div(summe_pro_jahr, axis=1) * 100
        
        print("\n\nVerteilung Anteil Erneuerbare Energien nach Jahr (in %):")
        print(ee_verteilung_prozent.round(2))
        
        # ============================================================
        # VISUALISIERUNG: 100% STACKED BAR PLOT
        # ============================================================
        
        # Font-Manager aktualisieren
        fm.fontManager.__init__()
        
        # --- Design-Variablen ---
        DARKMODE = True
        
        # Farbschema
        if DARKMODE:
            COLOR_BG = "#1a1a1a"
            COLOR_BORDER = "#3B3B3B"
            COLOR_GRID = "#FFFFFF"
            COLOR_TEXT = "#FFFFFF"
        else:
            COLOR_BG = "#ffffff"
            COLOR_BORDER = "#3B3B3B"
            COLOR_GRID = "#000000"
            COLOR_TEXT = "#000000"
        
        # Schriftarten
        FONT_MAIN = 'Open Sans'
        FONT_WEIGHT_MAIN = 'normal'
        FONT_TITLE = 'Druk Wide Trial'
        
        # Matplotlib Standardeinstellungen
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': [FONT_MAIN, 'Arial'],
            'font.size': 16,
            'font.weight': FONT_WEIGHT_MAIN
        })

        # --- Figure und Axes erstellen ---
        fig, ax = plt.subplots(figsize=(16, 10), facecolor=COLOR_BG)
        ax.set_facecolor(COLOR_BG)
        
        # Daten für Plotting transponieren (Jahre auf x-Achse)
        ee_verteilung_prozent_T = ee_verteilung_prozent.T
        
        # --- Stacked Bar Plot ---
        ee_verteilung_prozent_T.plot(
            kind='bar',
            stacked=True,
            ax=ax,
            width=0.7,
            colormap='RdYlGn'
        )
        
        # --- Achsen-Labels ---
        ax.set_xlabel(
            'Jahr', 
            fontsize=16, 
            fontfamily=FONT_MAIN, 
            fontweight=FONT_WEIGHT_MAIN, 
            color=COLOR_TEXT
        )
        ax.set_ylabel(
            'Anteil der Zeit (%)', 
            fontsize=16, 
            fontfamily=FONT_MAIN, 
            fontweight=FONT_WEIGHT_MAIN, 
            color=COLOR_TEXT
        )

        # --- Titel ---
        ax.set_title(
            'Verteilung des Anteils Erneuerbarer Energien\nvon Jan 2015 bis Dez 2020', 
            fontsize=26, 
            fontweight='bold', 
            fontstyle='italic', 
            pad=60, 
            fontfamily=FONT_TITLE, 
            loc='left', 
            color=COLOR_TEXT
        )
        
        # --- Info-Box ---
        info_text = "100% = Ges. Zeit eines Jahres | Quelle: SMARD.de"
        fig.text(
            0.07, 0.88, info_text,
            fontsize=16,
            fontfamily=FONT_MAIN,
            fontweight=FONT_WEIGHT_MAIN,
            color=COLOR_TEXT,
            verticalalignment='top',
            bbox=dict(
                boxstyle='square,pad=0.6', 
                facecolor=COLOR_BG, 
                edgecolor=COLOR_BORDER, 
                linewidth=1.5
            )
        )
        
        # --- Legende ---
        legend = ax.legend(
            title='Anteil EE', 
            bbox_to_anchor=(1.05, 1), 
            loc='upper left', 
            fontsize=16, 
            facecolor=COLOR_BG, 
            edgecolor=COLOR_BORDER,
            prop={'family': FONT_MAIN, 'weight': FONT_WEIGHT_MAIN}
        )
        
        # Legende-Titel formatieren
        legend.get_title().set_fontfamily(FONT_TITLE)
        legend.get_title().set_fontweight('bold')
        legend.get_title().set_fontstyle('italic')
        legend.get_title().set_fontsize(18)
        legend.get_title().set_color(COLOR_TEXT)
        
        # Legende-Text formatieren
        for text in legend.get_texts():
            text.set_color(COLOR_TEXT)
        
        # --- Achsen-Styling ---
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.2, linestyle='--', color=COLOR_GRID)
        ax.set_xticklabels(
            ax.get_xticklabels(), 
            rotation=0, 
            color=COLOR_TEXT, 
            fontfamily=FONT_MAIN, 
            fontweight=FONT_WEIGHT_MAIN
        )
        ax.tick_params(axis='both', colors=COLOR_TEXT, which='both')
        
        # Y-Achsen-Labels formatieren
        for label in ax.get_yticklabels():
            label.set_fontfamily(FONT_MAIN)
            label.set_fontweight(FONT_WEIGHT_MAIN)
        
        # Rahmen (Spines) formatieren
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_BORDER)
            spine.set_linewidth(1.5)
        
        # --- Sternchen-Erklärung ---
        # plt.figtext(
        #     0.01, 0.01, 
        #     "* Daten bis Oktober 2025",
        #     ha="left",
        #     va="bottom",
        #     fontsize=14,
        #     fontfamily=FONT_MAIN,
        #     fontweight=FONT_WEIGHT_MAIN,
        #     color=COLOR_TEXT
        # )
        
        # --- Copyright ---
        plt.figtext(
            0.99, 0.01, 
            "© EcoVision Labs Team",
            ha="right",
            va="bottom",
            fontsize=14,
            fontfamily=FONT_MAIN,
            fontweight=FONT_WEIGHT_MAIN,
            color=COLOR_TEXT
        )
        
        # --- Plot anzeigen ---
        plt.tight_layout()
        plt.savefig('output/final_plots/Verteilung EE Anteil Jan2015-Dez2020_dark_HD.png', dpi=600)
        plt.show()
        

    # ============================================================
    # FEHLERBEHANDLUNG
    # ============================================================
    
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

