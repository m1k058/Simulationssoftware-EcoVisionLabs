import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from constants import EnergySources as ES
from pathlib import Path


DATA_PATH = Path("raw-data") / "Realisierte_Erzeugung_2025_Jan-Juni_Stunde_test.csv" # Pfad zur CSV-Datei
DATE_START = "01.01.2025 08:00" # Startdatum für die Filterung (MM.TT.JJJJ HH:MM)
DATE_END = "01.05.2025 08:00" # Enddatum für die Filterung (MM.TT.JJJJ HH:MM)
ENGY_SRC0 = ES.SK # Energiequelle für Stapelung
ENGY_SRC1 = ES.BK # Energiequelle
ONLY_SAVE_PLOT = True # Wenn True, wird der Plot gespeichert anstatt angezeigt zu werden

# Laden der CSV-Datei in ein DataFrame
df = pd.read_csv(DATA_PATH, sep=';')

# Start/End-Datum in datetime-Objekte umwandeln
df["Datum von"] = pd.to_datetime(df["Datum von"], format="%d.%m.%Y %H:%M")
df["Datum bis"] = pd.to_datetime(df["Datum bis"], format="%d.%m.%Y %H:%M")

# Berechnung der mittleren Zeit für jeden Eintrag
df["zeit"] = df["Datum von"] + (df["Datum bis"] - df["Datum von"]) / 2

# Filtern der Daten
df_filtered = df[(df["zeit"] >= DATE_START) & (df["zeit"] <= DATE_END)]

# Konvertiere den String-Wert der .csv mit Komma in einen Float (deutsches Format zu US-Format (grrr!!! AMERIKANER!!!))
#df_filtered[ENGY_SRC0.value["col"]] = df_filtered[ENGY_SRC0.value["col"]].str.replace('.', '').str.replace(',', '.').astype(float)
#df_filtered[ENGY_SRC1.value["col"]] = df_filtered[ENGY_SRC1.value["col"]].str.replace('.', '').str.replace(',', '.').astype(float)

df_filtered.loc[:, ENGY_SRC0.value["col"]] = df_filtered[ENGY_SRC0.value["col"]].str.replace('.', '').str.replace(',', '.').astype(float)
df_filtered.loc[:, ENGY_SRC1.value["col"]] = df_filtered[ENGY_SRC1.value["col"]].str.replace('.', '').str.replace(',', '.').astype(float)


# das Plotten der Daten
plt.figure(figsize=(20,10))
plt.bar(
        df_filtered["zeit"],
        df_filtered[ENGY_SRC0.value["col"]],
        width=pd.Timedelta(hours=0.8),
        align='center',
        color=ENGY_SRC0.value["color"],
        label=ENGY_SRC0.value["name"],
        bottom=df_filtered[ENGY_SRC1.value["col"]] # Stapeln der Balken
)

plt.bar(
        df_filtered["zeit"],
        df_filtered[ENGY_SRC1.value["col"]],
        width=pd.Timedelta(hours=0.8),
        align='center',
        color=ENGY_SRC1.value["color"],
        label=ENGY_SRC1.value["name"]
)


plt.xlabel("Datum")
plt.ylabel("Erzeugung [MWh]")
plt.title("Stündliche Stromerzeugung " + ENGY_SRC0.value["name"] + " und " + ENGY_SRC1.value["name"] + " von " + DATE_START + " bis " + DATE_END)
plt.legend()
plt.grid(True)
plt.gcf().autofmt_xdate()  # Datumsanzeige schräg stellen

if ONLY_SAVE_PLOT:
    timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    filename = f"output/test_plots/plot_{ENGY_SRC0.name}+{ENGY_SRC1.name}_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()
else:
    plt.show()
