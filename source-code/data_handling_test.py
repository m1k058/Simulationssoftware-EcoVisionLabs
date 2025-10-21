import pandas as pd

def read_csv(data_path, start_date, end_date):
    # Laden der CSV-Datei in ein DataFrame
    df = pd.read_csv(DATA_PATH=data_path, sep=';')

    # Start/End-Datum in datetime-Objekte umwandeln
    df["Datum von"] = pd.to_datetime(df["Datum von"], format="%d.%m.%Y %H:%M")
    df["Datum bis"] = pd.to_datetime(df["Datum bis"], format="%d.%m.%Y %H:%M")

    # Berechnung der mittleren Zeit für jeden Eintrag
    df["zeit"] = df["Datum von"] + (df["Datum bis"] - df["Datum von"]) / 2

    data = df[(df["zeit"] >= start_date) & (df["zeit"] <= end_date)]# Filtern der Daten
    return data