"""
EcoVisionLabs - Analyse der Verteilung Erneuerbarer Energien
Visualisiert die zeitliche Verteilung des Anteils erneuerbarer Energien am Stromverbrauch
"""

import warnings
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from errors import AppError, WarningMessage
from data_manager import DataManager
from config_manager import ConfigManager
from data_processing import (
    add_total_generation, 
    add_total_renewable_generation, 
    add_total_conventional_generation,
    add_column_from_other_df,
    add_energy_source_generation_sum,
    generate_df_with_col_sums,
    multiply_column
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
        genDf = dm.get(1)  # Erzeugungsdaten
        conDf = dm.get(2)  # Verbrauchsdaten
        
        # Spalten für Gesamt-Erzeugung hinzufügen
        add_total_renewable_generation(genDf)
        add_total_conventional_generation(genDf)
        add_total_generation(genDf)
        # Plot-DataFrame initialisieren und relevante Spalten übernehmen
        plotDF = pd.DataFrame(index=genDf.index)
        # Zeitachse übernehmen (io_handler setzt 'Zeitpunkt' bereits als datetime)
        if "Zeitpunkt" in genDf.columns:
            plotDF["Zeitpunkt"] = genDf["Zeitpunkt"].values
        # Werte übernehmen
        add_column_from_other_df(plotDF, genDf, "Gesamterzeugung [MWh]")
        add_column_from_other_df(plotDF, conDf, "Netzlast [MWh]")

        # ============================================================
        # DINGE BERECHNEN
        # ============================================================

        plotDF["Bilanz [MWh]"] = plotDF["Gesamterzeugung [MWh]"] - plotDF["Netzlast [MWh]"]

        # Jahr aus Zeitpunkt extrahieren (Zeitpunkt ist bereits datetime)
        if "Zeitpunkt" in plotDF.columns and pd.api.types.is_datetime64_any_dtype(plotDF["Zeitpunkt"]):
            plotDF["Jahr"] = plotDF["Zeitpunkt"].dt.year

        print(f"\nVerwende originale Auflösung: {len(plotDF)} Viertelstunden-Werte")

        # ============================================================
        # STATISTIKEN AUSGEBEN
        # ============================================================
        
        
        
        # ============================================================
        # KATEGORISIERUNG IN PROZENT-BINS (0-10%, 10-20%, ..., 90-100%, >100%)
        # ============================================================
        # Ensure the total renewable generation column is present in genDf
        # plotting functions in this repo expect the column name
        # 'Gesamterzeugung Erneuerbare [MWh]'. We'll add it to plotDF
        # so we can compute the Anteil Erneuerbare am Verbrauch.
        add_column_from_other_df(plotDF, genDf, 'Gesamterzeugung Erneuerbare [MWh]')

        # Compute Anteil Erneuerbare in percent: (Erneuerbare / Netzlast) * 100
        # Avoid division by zero and keep NaN where Netzlast is zero or missing.
        if 'Netzlast [MWh]' in plotDF.columns and 'Gesamterzeugung Erneuerbare [MWh]' in plotDF.columns:
            netz = plotDF['Netzlast [MWh]'].replace({0: np.nan})
            plotDF['Anteil Erneuerbare'] = (plotDF['Gesamterzeugung Erneuerbare [MWh]'] / netz) * 100
        else:
            raise ValueError("Required columns for computing Anteil Erneuerbare are missing: 'Netzlast [MWh]' or 'Gesamterzeugung Erneuerbare [MWh]'.")

        # Define decade-percent bins 0-10, 10-20, ..., 90-100 and a final >100 bin
        bins = list(range(0, 101, 10)) + [float('inf')]  # [0,10,20,...,100, inf]
        labels = [f"{i}-{i+10}%" for i in range(0,100,10)] + ['>100%']

        # Use right=True so intervals are (a, b] and include_lowest ensures 0 is included
        plotDF['Anteil EE Kategorie'] = pd.cut(plotDF['Anteil Erneuerbare'], bins=bins, labels=labels, include_lowest=True)

        # Crosstab / counts per category (overall and per year if Jahr available)
        ee_verteilung = pd.crosstab(plotDF['Anteil EE Kategorie'], plotDF.get('Jahr', pd.Series([], dtype='int')), dropna=False)

        print("\nVerteilung Anteil Erneuerbare Energien nach Jahr (Anzahl):")
        print(ee_verteilung)

        # Gesamtsumme über alle Jahre
        summe_pro_jahr = ee_verteilung.sum(axis=0)
        print("\n\nSumme Viertelstunden pro Jahr:")
        print(summe_pro_jahr)

        # Prozentuale Verteilung berechnen
        # handle division by zero for years with no entries
        with np.errstate(divide='ignore', invalid='ignore'):
            ee_verteilung_prozent = ee_verteilung.div(summe_pro_jahr.replace(0, np.nan), axis=1) * 100

        print("\n\nVerteilung Anteil Erneuerbare Energien nach Jahr (in %):")
        print(ee_verteilung_prozent.round(2))

        # --- Plot histogram (bar) similar to example image ---
        counts = plotDF['Anteil EE Kategorie'].value_counts(sort=False)
        counts = counts.reindex(labels, fill_value=0)

        # Ensure color and font variables are defined before plotting the histogram
        fm.fontManager.__init__()
        DARKMODE = False
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
        FONT_MAIN = 'Open Sans'
        FONT_WEIGHT_MAIN = 'normal'
        FONT_TITLE = 'Druk Wide Trial'
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': [FONT_MAIN, 'Arial'],
            'font.size': 16,
            'font.weight': FONT_WEIGHT_MAIN
        })

        fig_hist, ax_hist = plt.subplots(figsize=(10, 8), facecolor=COLOR_BG)
        ax_hist.set_facecolor(COLOR_BG)
        bar_colors = [color_ee]* (len(labels)-1) + ['#637CEF'] if 'color_ee' in locals() else ['#637CEF'] * len(labels)
        # Draw bars
        x_pos = np.arange(len(labels))
        ax_hist.bar(x_pos, counts.values, color='#637CEF', edgecolor=COLOR_BORDER)
        # Labels and title
        fig_hist.text(0.135, 0.85, "Jan 2020 - Okt 2025 | korrigierte Version | Quelle: SMARD.de", fontsize=16, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT, verticalalignment='top', bbox=dict(boxstyle='square,pad=0.6', facecolor=COLOR_BG, edgecolor=COLOR_BORDER, linewidth=1.5))
        ax_hist.set_xticks(x_pos)
        ax_hist.set_xticklabels(labels, rotation=45, ha='right', color=COLOR_TEXT, fontfamily=FONT_MAIN)
        ax_hist.set_ylabel('Anzahl 15-Minuten-Intervalle', fontsize=14, color=COLOR_TEXT, fontfamily=FONT_MAIN)
        ax_hist.set_xlabel('Anteil erneuerbarer Energien am Verbrauch (%)', fontsize=14, color=COLOR_TEXT, fontfamily=FONT_MAIN)
        ax_hist.set_title('Verteilung des EE-Anteils am\nStromverbrauch von 2020-2025', fontsize=26, fontweight='bold', fontstyle='italic', pad=60, fontfamily=FONT_TITLE, loc='left', color=COLOR_TEXT)
        ax_hist.yaxis.grid(True, linestyle='--', color=COLOR_GRID, alpha=0.5)
        for spine in ax_hist.spines.values():
            spine.set_edgecolor(COLOR_BORDER)
            spine.set_linewidth(1.2)
        for label in ax_hist.get_yticklabels():
            label.set_color(COLOR_TEXT)
            label.set_fontfamily(FONT_MAIN)
        plt.figtext(0.99, 0.001, "© EcoVision Labs Team", ha="right", va="bottom", fontsize=14, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT)

        plt.tight_layout()
        out_plot_dir = Path('output/final_plots')
        out_plot_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_plot_dir / 'Histogram_Anteil_Erneuerbare_Prozent_bins_.png', dpi=300, bbox_inches='tight')
        print(f"Plot gespeichert: {out_plot_dir / 'Histogram_Anteil_Erneuerbare_Prozent_bins_dark.png'}")
        plt.close(fig_hist)
        
        # ============================================================
        # STACKED BAR: Monatliche Erzeugung nach Quelle (EE grün, Rest grau)
        # ============================================================
        fm.fontManager.__init__()
        DARKMODE = False
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
        FONT_MAIN = 'Open Sans'
        FONT_WEIGHT_MAIN = 'normal'
        FONT_TITLE = 'Druk Wide Trial'
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': [FONT_MAIN, 'Arial'],
            'font.size': 16,
            'font.weight': FONT_WEIGHT_MAIN
        })
        from constants import ENERGY_SOURCES, SOURCES_GROUPS
        genDf_monat = genDf.copy()
        if not pd.api.types.is_datetime64_any_dtype(genDf_monat["Zeitpunkt"]):
            genDf_monat["Zeitpunkt"] = pd.to_datetime(genDf_monat["Zeitpunkt"])
        genDf_monat["Jahr"] = genDf_monat["Zeitpunkt"].dt.year
        genDf_monat["Monat"] = genDf_monat["Zeitpunkt"].dt.month
        group_cols = ["Jahr", "Monat"]
        all_sources = SOURCES_GROUPS["All"]
        erneuerbare = SOURCES_GROUPS["Renewable"]
        konventionelle = [s for s in all_sources if s not in erneuerbare and s in ENERGY_SOURCES]
        monat_df = genDf_monat.groupby(group_cols)[[ENERGY_SOURCES[s]["colname"] for s in all_sources if ENERGY_SOURCES[s]["colname"] in genDf_monat.columns]].sum().reset_index()
        monat_df["YYYY-MM"] = monat_df["Jahr"].astype(str) + "-" + monat_df["Monat"].astype(str).str.zfill(2)
        erneuerbare_cols = [ENERGY_SOURCES[s]["colname"] for s in erneuerbare if ENERGY_SOURCES[s]["colname"] in monat_df.columns]
        konv_cols = [ENERGY_SOURCES[s]["colname"] for s in konventionelle if ENERGY_SOURCES[s]["colname"] in monat_df.columns]
        x = monat_df["YYYY-MM"]
        # Summiere jeweils alle EE und alle Konventionellen, rechne in TWh um
        y_ee = monat_df[erneuerbare_cols].sum(axis=1) / 1e6  # TWh
        y_konv = monat_df[konv_cols].sum(axis=1) / 1e6       # TWh
        # Farben
        color_ee = "#4CAF50"  # grün
        color_konv = "#B0B0B0"  # grau
        # Stacked Bar Plot
        fig2, ax2 = plt.subplots(figsize=(18, 10), facecolor=COLOR_BG)
        ax2.set_facecolor(COLOR_BG)
        ax2.bar(x, y_ee, label="Erneuerbare", color=color_ee, width=0.8, align='center')
        ax2.bar(x, y_konv, bottom=y_ee, label="Konventionelle", color=color_konv, width=0.8, align='center')
        # Achsen-Labels
        ax2.set_xlabel("Monat", fontsize=16, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT)
        ax2.set_ylabel("Erzeugung [TWh]", fontsize=16, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT)
        # Titel
        ax2.set_title("Monatliche Stromerzeugung Jan 2020 - Okt 2025", fontsize=26, fontweight='bold', fontstyle='italic', pad=60, fontfamily=FONT_TITLE, loc='left', color=COLOR_TEXT)
        # X-Ticks: Nur Januar und Juni jedes Jahres
        monate = monat_df["Monat"].values
        jahre = monat_df["Jahr"].values
        xtick_idx = [i for i, (m, _) in enumerate(zip(monate, jahre)) if m in [1, 7]]
        ax2.set_xticks(xtick_idx)
        ax2.set_xticklabels([x.iloc[i] for i in xtick_idx], rotation=45, ha='right', color=COLOR_TEXT, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN)
        # Y-Gitterlinien gestichelt
        ax2.yaxis.grid(True, linestyle='--', color=COLOR_GRID, alpha=0.5)
        # Info-Box
        fig2.text(0.06, 0.90, "Quelle: SMARD.de", fontsize=16, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT, verticalalignment='top', bbox=dict(boxstyle='square,pad=0.6', facecolor=COLOR_BG, edgecolor=COLOR_BORDER, linewidth=1.5))
        # Y-Ticks Styling
        for label in ax2.get_yticklabels():
            label.set_fontfamily(FONT_MAIN)
            label.set_fontweight(FONT_WEIGHT_MAIN)
            label.set_color(COLOR_TEXT)
        # Rahmen
        for spine in ax2.spines.values():
            spine.set_edgecolor(COLOR_BORDER)
            spine.set_linewidth(1.5)
        # Legende
        legend = ax2.legend(
            title="Energiequellen",
            loc='upper right',
            bbox_to_anchor=(1, 1.18),  # etwas über dem Plot, rechtsbündig
            fontsize=16,
            facecolor=COLOR_BG,
            edgecolor=COLOR_BORDER,
            prop={'family': FONT_MAIN, 'weight': FONT_WEIGHT_MAIN}
        )
        legend.get_title().set_fontfamily(FONT_TITLE)
        legend.get_title().set_fontweight('bold')
        legend.get_title().set_fontstyle('italic')
        legend.get_title().set_fontsize(18)
        legend.get_title().set_color(COLOR_TEXT)
        for text in legend.get_texts():
            text.set_color(COLOR_TEXT)
        plt.figtext(0.99, 0.001, "© EcoVision Labs Team", ha="right", va="bottom", fontsize=14, fontfamily=FONT_MAIN, fontweight=FONT_WEIGHT_MAIN, color=COLOR_TEXT)
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)
        out_plot_dir = Path('output/final_plots')
        out_plot_dir.mkdir(parents=True, exist_ok=True)
        #plt.savefig(out_plot_dir / 'Monatliche_Erzeugung_EE_Konv_2020-2025_light.png', dpi=300, bbox_inches="tight")
       # print(f"Plot gespeichert: {out_plot_dir / 'Monatliche_Erzeugung_EE_Konv_2020-2025_dark.png'}")
        plt.close(fig2)

        

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

