import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from io_handler import load_data
from constants import ENERGY_SOURCES

# --- Konfiguration ---
INPUT_MODE = "Viertelstunde"  # oder "Stunde"

if INPUT_MODE == "Stunde":
    DATA_PATH = Path("raw-data/Realisierte_Erzeugung_2025_Jan-Juni_Stunde_test.csv")
    wth = pd.Timedelta(hours=1)
elif INPUT_MODE == "Viertelstunde":
    DATA_PATH = Path("raw-data/1.1.2020-16.10.2025--Realisierte_Erzeugung_202001010000_202510170000_Viertelstunde.csv")
    wth = pd.Timedelta(minutes=15)
else:
    raise ValueError("Ungültiger INPUT_MODE. Verwende 'Stunde' oder 'Viertelstunde'.")

# Reihenfolge und Auswahl der Energiequellen
ALL = ["KE", "BK", "SK", "EG", "SOK", "BIO", "PS", "WAS", "SOE", "WOF", "WON", "PV"]

DATE_START = "01.01.2024 00:00"
DATE_END = "02.01.2024 23:00"
ENERGY_SOURCE_KEYS = ALL
ONLY_SAVE_PLOT = False

# --- Daten laden ---
df = load_data(path=DATA_PATH, datatype="SMARD")

# Filterung nach Zeitraum
df_filtered = df[(df["Zeitpunkt"] >= DATE_START) & (df["Zeitpunkt"] <= DATE_END)]

# --- Vorbereitung für Stackplot ---
# Alle Spalten, die existieren und gebraucht werden
available_cols = [f"{ENERGY_SOURCES[k]['name']} [MWh]" for k in ENERGY_SOURCE_KEYS if f"{ENERGY_SOURCES[k]['name']} [MWh]" in df_filtered.columns]
labels = [ENERGY_SOURCES[k]["name"] for k in ENERGY_SOURCE_KEYS if f"{ENERGY_SOURCES[k]['name']} [MWh]" in df_filtered.columns]
colors = [ENERGY_SOURCES[k]["color"] for k in ENERGY_SOURCE_KEYS if f"{ENERGY_SOURCES[k]['name']} [MWh]" in df_filtered.columns]

if not available_cols:
    raise ValueError("Keine passenden Spalten im Datensatz gefunden – prüfe ENERGY_SOURCES oder Datei.")

# Stackplot erwartet ein 2D-Array (jede Zeile = Quelle)
data_matrix = [df_filtered[c].to_numpy(dtype=float) for c in available_cols]

# --- Plotten mit stackplot ---
fig, ax = plt.subplots(figsize=(20, 10))

ax.stackplot(
    df_filtered["Zeitpunkt"],
    *data_matrix,
    labels=labels,
    colors=colors,
)

ax.set_xlabel("Datum")
ax.set_ylabel("Erzeugung [MWh]")
ax.set_title(
    f"Stromerzeugung ({', '.join(labels)})\n{DATE_START} bis {DATE_END}"
)
ax.legend(loc="upper left", ncol=2, fontsize=9)
ax.grid(True)
fig.autofmt_xdate()

# --- Speichern oder Anzeigen ---
if ONLY_SAVE_PLOT:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path("output/test_plots")
    outdir.mkdir(parents=True, exist_ok=True)
    filename = outdir / f"plot_{INPUT_MODE}_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()
else:
    plt.show()
