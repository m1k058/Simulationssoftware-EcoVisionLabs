import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import os

def plotting():
        # Initialisiere die Basis für gestapelte Balken als Float-Array
    bottom = np.zeros(len(df_filtered), dtype=float)

    # das Plotten der Daten
    plt.figure(figsize=(20,10))

    for source in ENERGY_SOURCES:
        plt.bar(
            df_filtered["zeit"],
            df_filtered[source.value["col"]],
            width=wth,  # Angepassung der Breite
            align='center',
            color=source.value["color"],
            label=source.value["name"],
            bottom=bottom # Stapeln der Balken
        )
        # Addiere die aktuellen Werte zur Basis für den nächsten Balken
        # Verwende to_numpy(dtype=float) um sicherzustellen, dass wir ein float64-Array addieren
        bottom += df_filtered[source.value["col"]].to_numpy(dtype=float)

    plt.xlabel("Datum")
    plt.ylabel("Erzeugung [MWh]")
    plt.title("Stromerzeugung " + "+".join([source.name for source in ENERGY_SOURCES]) + " von " + DATE_START + " bis " + DATE_END)
    plt.legend()
    plt.grid(True)
    plt.gcf().autofmt_xdate()  # Datumsanzeige schräg stellen

    if ONLY_SAVE_PLOT:
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        sources_name = "+".join([source.name for source in ENERGY_SOURCES])
        outdir = os.path.join("output", "test_plots")
        os.makedirs(outdir, exist_ok=True)
        filename = os.path.join(outdir, f"plot_{sources_name}_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()
    else:
        plt.show()