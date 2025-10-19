import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import os
#from constants import EnergySourcesCalc as ES # Bei Verwendung der berechneten Auflösungen
from constants import EnergySourcesOG as ES # Bei Verwendung der Originalauflösungen

ALL = [ES.KE, ES.BK, ES.SK, ES.EG, ES.SOK, ES.BIO, ES.PS, ES.WAS, ES.SOE, ES.WOF, ES.WON, ES.PV]
RENEWABLE = [ES.SOE, ES.BIO, ES.WAS, ES.WOF, ES.WON, ES.PV]
LOW_CARBON = [ES.KE, ES.BIO, ES.WAS, ES.SOE, ES.WOF, ES.WON, ES.PV]
FOSSIL = [ES.BK, ES.SK, ES.EG, ES.SOK]
STORAGE = [ES.PS]

# DATA_PATH = r"raw-data\Realisierte_Erzeugung_2025_Jan-Juni_Stunde_test.csv" # Pfad zur CSV-Datei Stündliche Daten
DATA_PATH = r"raw-data\1.1.2020-16.10.2025--Realisierte_Erzeugung_202001010000_202510170000_Viertelstunde.csv" # Pfad zur CSV-Datei Viertelstündliche Daten

DATE_START = "04.01.2025 08:00" # Startdatum für die Filterung (MM.TT.JJJJ HH:MM)
DATE_END = "04.03.2025 08:00" # Enddatum für die Filterung (MM.TT.JJJJ HH:MM)
ENERGY_SOURCES = ALL  # Liste der Energiequellen
ONLY_SAVE_PLOT = False # Wenn True, wird der Plot gespeichert anstatt angezeigt zu werden

# Laden der CSV-Datei in ein DataFrame
df = pd.read_csv(DATA_PATH, sep=';')

# Start/End-Datum in datetime-Objekte umwandeln
df["Datum von"] = pd.to_datetime(df["Datum von"], format="%d.%m.%Y %H:%M")
df["Datum bis"] = pd.to_datetime(df["Datum bis"], format="%d.%m.%Y %H:%M")

# Berechnung der mittleren Zeit für jeden Eintrag
df["zeit"] = df["Datum von"] + (df["Datum bis"] - df["Datum von"]) / 2

# Filtern der Daten
df_filtered = df[(df["zeit"] >= DATE_START) & (df["zeit"] <= DATE_END)]


# Nur Quellen verwenden, deren Spalte existiert
valid_sources = []
missing = []
for source in ENERGY_SOURCES:
    col = source.value["col"]
    if col in df_filtered.columns:
        # Zuerst als string behandeln und Tausendertrennzeichen entfernen, Dezimal-Komma ersetzen
        s = df_filtered[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        # Sichere Umwandlung: nicht-konvertierbare Werte werden zu NaN, dann mit 0.0 ersetzt
        df_filtered.loc[:, col] = pd.to_numeric(s, errors='coerce').fillna(0.0).astype(float)
        valid_sources.append(source)
    else:
        missing.append(source)
if missing:
    print("Warnung: folgende Quellen fehlen in der CSV und werden übersprungen:", [m.name for m in missing])
ENERGY_SOURCES = valid_sources

# Initialisiere die Basis für gestapelte Balken als Float-Array
bottom = np.zeros(len(df_filtered), dtype=float)

# das Plotten der Daten
plt.figure(figsize=(20,10))
for source in ENERGY_SOURCES:
    plt.bar(
        df_filtered["zeit"],
        df_filtered[source.value["col"]],
        width=pd.Timedelta(hours=0.25),  # Angepasste Breite für Viertelstündliche Daten
        # width=pd.Timedelta(hours=1), # Angepasste Breite für Stündliche Daten
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
plt.title("Stündliche Stromerzeugung " + "+".join([source.name for source in ENERGY_SOURCES]) + " von " + DATE_START + " bis " + DATE_END)
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
