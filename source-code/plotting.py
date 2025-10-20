def plotBarStacked(df, energy_sources, date_start, date_end, only_save_plot=False):
    """
    Erstellt ein gestapeltes Balkendiagramm für die angegebenen Energiequellen
    über den spezifizierten Zeitraum.

    Parameter:
    - df: Pandas DataFrame mit den Daten
    - energy_sources: Liste der Energiequellen (Enum)
    - date_start: Startdatum als String (Format: "DD.MM.YYYY HH:MM")
    - date_end: Enddatum als String (Format: "DD.MM.YYYY HH:MM")
    - only_save_plot: Wenn True, wird der Plot gespeichert anstatt angezeigt zu werden
    """
    import matplotlib.pyplot as plt
    import pandas as pd
    from datetime import datetime
    import numpy as np

    # Konvertiere die Datumsstrings in datetime-Objekte
    start_dt = datetime.strptime(date_start, "%d.%m.%Y %H:%M")
    end_dt = datetime.strptime(date_end, "%d.%m.%Y %H:%M")

    # Filtere das DataFrame nach dem angegebenen Zeitraum
    df['zeit'] = pd.to_datetime(df['zeit'], format="%d.%m.%Y %H:%M")
    df_filtered = df[(df['zeit'] >= start_dt) & (df['zeit'] <= end_dt)]

    # Erstelle das gestapelte Balkendiagramm
    plt.figure(figsize=(20, 10))
    bottom = None
    wth = 0.03  # Breite der Balken

    # Initialisiere die Basis für gestapelte Balken als Float-Array
    bottom = np.zeros(len(df_filtered), dtype=float)

    # das Plotten der Daten
    plt.figure(figsize=(20,10))

    for source in energy_sources:
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
    plt.title("Stromerzeugung " + "+".join([source.name for source in energy_sources]) + " von " + date_start + " bis " + date_end)
    plt.legend()
    plt.grid(True)
    plt.gcf().autofmt_xdate()  # Datumsanzeige schräg stellen

    ## HEIR SAVE OR SHOW PLOT MACHEN ##