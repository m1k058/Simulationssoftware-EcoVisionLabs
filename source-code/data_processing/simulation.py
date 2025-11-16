import pandas as pd
import numpy as np
import data_processing.col as col
import data_processing.gen as gen
import locale
from typing import List, Optional

def aggregate_production_yearly(produDf: pd.DataFrame, year_col: str = "Zeitpunkt") -> pd.DataFrame:
    """
    Aggregiert die Erzeugungsdaten (in MWh) aus "produDf" auf Jahresbasis und
    bildet TWh-Summen je Energiequelle, kompatibel zu den Spalten in "energie_spalte".

    Regeln/Mapping:
    - Sonstige [TWh] = (Sonstige Erneuerbare [MWh] + Sonstige Konventionelle [MWh]) / 1e6
    - Speicher [TWh] = (Pumpspeicher [MWh]) / 1e6
    - Wasserstoff [TWh] und Abfall [TWh] existieren in produDf nicht -> 0
    - Alle übrigen 1:1 von [MWh] -> [TWh] (geteilt durch 1e6)

    Erwartete Standard-Spalten in produDf (SMARD-Erzeugung):
    - Biomasse [MWh], Wasserkraft [MWh], Wind Offshore [MWh], Wind Onshore [MWh], Photovoltaik [MWh],
      Sonstige Erneuerbare [MWh], Kernenergie [MWh], Braunkohle [MWh], Steinkohle [MWh], Erdgas [MWh],
      Pumpspeicher [MWh]

    Args:
        produDf: Erzeugungs-DataFrame mit Viertelstunden/Stundenwerten in MWh und Zeitspalte 'Zeitpunkt'.
        year_col: Name der Zeitspalte (Default: 'Zeitpunkt').

    Returns:
        DataFrame mit Spalten: 'Jahr' und den TWh-Spalten
        ["Biomasse [TWh]", "Wasserkraft [TWh]", "Wind Offshore [TWh]", "Wind Onshore [TWh]",
         "Photovoltaik [TWh]", "Wasserstoff [TWh]", "Kernenergie [TWh]", "Braunkohle [TWh]",
         "Steinkohle [TWh]", "Erdgas [TWh]", "Sonstige [TWh]", "Speicher [TWh]", "Abfall [TWh]"]
    """
    if year_col not in produDf.columns:
        raise ValueError(f"Zeitspalte '{year_col}' nicht in produDf gefunden.")

    # Stelle sicher, dass year_col datetime ist
    # Prüfe robust auf datetime-Typen (pandas-Helper vermeidet dtype-Probleme)
    if not pd.api.types.is_datetime64_any_dtype(produDf[year_col]):
        try:
            produDf = produDf.copy()
            produDf[year_col] = pd.to_datetime(produDf[year_col])
        except Exception as e:
            raise ValueError(f"Spalte '{year_col}' konnte nicht in datetime konvertiert werden: {e}")

    # Zielspaltenreihenfolge (kompatibel zu progDf/energie_spalte)
    target_cols = [
        "Biomasse [TWh]", "Wasserkraft [TWh]", "Wind Offshore [TWh]", "Wind Onshore [TWh]",
        "Photovoltaik [TWh]", "Wasserstoff [TWh]", "Kernenergie [TWh]", "Braunkohle [TWh]",
        "Steinkohle [TWh]", "Erdgas [TWh]", "Sonstige [TWh]", "Speicher [TWh]", "Abfall [TWh]"
    ]

    # 1) Jahresaggregation in MWh (nur numerische MWh-Spalten summieren)
    mwh_cols = [c for c in produDf.columns if c.endswith("[MWh]")]
    df_year = produDf.assign(Jahr=produDf[year_col].dt.year).groupby("Jahr")[mwh_cols].sum().reset_index()

    # 2) Mapping MWh -> TWh (einschließlich Sonderfälle)
    def get_col(df: pd.DataFrame, name: str) -> pd.Series:
        return df[name] if name in df.columns else pd.Series(0.0, index=df.index)

    # Speicher-Spalten ermitteln
    storage_candidates = ["Pumpspeicher [MWh]"]

    result = pd.DataFrame({"Jahr": df_year["Jahr"]})

    # 1:1 Mappings
    simple_map = {
        "Biomasse [TWh]": "Biomasse [MWh]",
        "Wasserkraft [TWh]": "Wasserkraft [MWh]",
        "Wind Offshore [TWh]": "Wind Offshore [MWh]",
        "Wind Onshore [TWh]": "Wind Onshore [MWh]",
        "Photovoltaik [TWh]": "Photovoltaik [MWh]",
        "Kernenergie [TWh]": "Kernenergie [MWh]",
        "Braunkohle [TWh]": "Braunkohle [MWh]",
        "Steinkohle [TWh]": "Steinkohle [MWh]",
        "Erdgas [TWh]": "Erdgas [MWh]",
    }

    for twh, mwh in simple_map.items():
        result[twh] = get_col(df_year, mwh) / 1_000_000.0

    # Sonstige = Sonstige Erneuerbare + Sonstige Konventionelle
    sonstige_mwh = get_col(df_year, "Sonstige Erneuerbare [MWh]") + get_col(df_year, "Sonstige Konventionelle [MWh]")
    result["Sonstige [TWh]"] = sonstige_mwh / 1_000_000.0

    # Speicher = Pumpspeicher + weitere Speicher-Spalten
    speicher_mwh = pd.Series(0.0, index=df_year.index)
    for c in storage_candidates:
        speicher_mwh = speicher_mwh.add(get_col(df_year, c), fill_value=0.0)
    result["Speicher [TWh]"] = speicher_mwh / 1_000_000.0

    # Nicht vorhandene Kategorien explizit auf 0 setzen
    result["Wasserstoff [TWh]"] = 0.0
    result["Abfall [TWh]"] = 0.0

    # Spaltenreihenfolge vereinheitlichen
    result = result[["Jahr"] + target_cols]

    return result

def calc_scaled_consumption_multiyear(conDf: pd.DataFrame, progDf: pd.DataFrame,
                            prog_dat_studie: str, simu_jahr_start: int, simu_jahr_ende: int,
                            ref_jahr: int = 2023, prog_dat_jahr: int = -1) -> pd.DataFrame:
    """
    Skaliert den Energieverbrauch eines Referenzjahres basierend auf Prognosedaten für mehrere
    Simulationsjahre und eine ausgewählte Studie.
    
    Args:
        conDf: DataFrame mit Verbrauchsdaten, muss eine Spalte 'Netzlast [MWh]' und 'Zeitpunkt' enthalten.
        progDf: DataFrame mit Prognosedaten, muss Spalten 'Jahr', 'Studie' und 'Bruttostromverbrauch [TWh]' enthalten.
        prog_dat_studie: Die Studie, aus der der Zielwert entnommen wird.
        ('Agora' | 'BDI - Klimapfade 2.0' | 'dena - KN100' | 'BMWK - LFS TN-Strom' | 'Ariadne - REMIND-Mix' | 'Ariadne - REMod-Mix' | 'Ariadne - TIMES PanEU-Mix')         
        simu_jahr_start: Das Startjahr der Simulation.
        simu_jahr_ende: Das Endjahr der Simulation.
        prog_dat_jahr: Das Jahr der Prognose (default: -1 für automatische Auswahl).
        ref_jahr: Das Referenzjahr im Verbrauchsdatensatz (default: 2023).
        
    Returns:
        DataFrame mit skaliertem Energieverbrauch für die Simulationsjahre.
    """
    df_list = []
    for simu_jahr in range(simu_jahr_start, simu_jahr_ende + 1):
        df_scaled = calc_scaled_consumption(conDf, progDf,
                                            prog_dat_studie, simu_jahr, prog_dat_jahr,
                                            ref_jahr)
        df_list.append(df_scaled)
    
    return pd.concat(df_list).reset_index(drop=True)

def calc_scaled_consumption(conDf: pd.DataFrame, progDf: pd.DataFrame,
                            prog_dat_studie: str, simu_jahr: int, prog_dat_jahr: int = -1,
                            ref_jahr: int = 2023) -> pd.DataFrame:
    """
    Skaliert den Energieverbrauch eines Referenzjahres basierend auf Prognosedaten für ein
    Simulationsjahr und eine ausgewählte Studie.
    
    Args:
        conDf: DataFrame mit Verbrauchsdaten, muss eine Spalte 'Netzlast [MWh]' und 'Zeitpunkt' enthalten.
        progDf: DataFrame mit Prognosedaten, muss Spalten 'Jahr', 'Studie' und 'Bruttostromverbrauch [TWh]' enthalten.
        prog_dat_studie: Die Studie, aus der der Zielwert entnommen wird.
        ('Agora' | 'BDI - Klimapfade 2.0' | 'dena - KN100' | 'BMWK - LFS TN-Strom' | 'Ariadne - REMIND-Mix' | 'Ariadne - REMod-Mix' | 'Ariadne - TIMES PanEU-Mix')         
        prog_dat_jahr: Das Jahr der Prognose.
        ref_jahr: Das Referenzjahr im Verbrauchsdatensatz.
        simu_jahr: Das Simulationsjahr, für das der Verbrauch skaliert werden soll.
        
    Returns:
        DataFrame mit skaliertem Energieverbrauch für das Simulationsjahr.
    """

    # nach jahr im Verbrauchsdatensatz suchen
    ist_ref_jahr_vorhanden = (conDf['Zeitpunkt'].dt.year == ref_jahr).any()

    # Ziehe ein Referenzjahr aus der den Dataframe
    if ist_ref_jahr_vorhanden:
        df_refJahr = conDf[(conDf["Zeitpunkt"] >= f"01.01.{ref_jahr} 00:00") & (conDf["Zeitpunkt"] <= f"31.12.{ref_jahr} 23:59")]
    else:
        raise ValueError(f"Referenzjahr {ref_jahr} nicht im Verbrauchsdatensatz gefunden.")
    
    # Berechne die Gesammtenergie im Referenzjahr
    Gesamtenergie_RefJahr = col.get_column_total(df_refJahr, "Netzlast [MWh]") / 1000000  # in TWh

    formatierte_zahl = locale.format_string("%.8f", Gesamtenergie_RefJahr, grouping=True)
    print(f"Gesamter Energieverbrauch im Referenzjahr: {formatierte_zahl} [TWh]\n")

    # Bestimme verfügbare Prognosejahre für die gewählte Studie und wähle das passende Jahr
    # Filter: Jahre mit Wert 0 oder NaN werden als nicht vorhanden behandelt
    studie_data = progDf.loc[progDf['Studie'] == prog_dat_studie].copy()
    studie_data = studie_data.dropna(subset=['Jahr', 'Bruttostromverbrauch [TWh]'])
    studie_data = studie_data[studie_data['Bruttostromverbrauch [TWh]'] != 0]
    
    available_years = studie_data['Jahr'].unique()
    if len(available_years) == 0:
        raise ValueError(f"Keine Prognose-Daten für Studie='{prog_dat_studie}' gefunden (alle Jahre sind leer oder 0).")
    # Normiere auf int und sortiere
    try:
        available_years = np.array(sorted([int(y) for y in available_years]))
    except Exception:
        raise ValueError(f"Prognose-Daten enthalten ungültige Jahreswerte für Studie='{prog_dat_studie}'.")

    # Wenn kein bestimmtes prog_dat_jahr übergeben wurde (Standard -1), wähle das nächstgrößere >= simu_jahr
    if prog_dat_jahr is None or int(prog_dat_jahr) < 0:
        ge_years = available_years[available_years >= simu_jahr]
        if ge_years.size > 0:
            prog_dat_jahr_used = int(ge_years.min())
        else:
            # Kein Jahr >= simu_jahr vorhanden, nehme das größte verfügbare (kleiner als simu_jahr)
            prog_dat_jahr_used = int(available_years.max())
    else:
        prog_dat_jahr_used = int(prog_dat_jahr)

    # Finde, ob es ein Jahr im Datensatz gibt, das kleiner als simu_jahr ist; falls ja, speichere das größte davon
    smaller_years = available_years[available_years < simu_jahr]
    if smaller_years.size > 0:
        prog_dat_jahr_kleiner = int(smaller_years.max())
    else:
        prog_dat_jahr_kleiner = None

    print(f"Verfügbare Prognosejahre für Studie '{prog_dat_studie}': {available_years.tolist()}")
    print(f"Ausgewähltes Prognosejahr für die weitere Verarbeitung: {prog_dat_jahr_used}")
    if prog_dat_jahr_kleiner is not None:
        print(f"Größtes Prognosejahr < Simulationsjahr ({simu_jahr}): {prog_dat_jahr_kleiner} (in Variable 'prog_dat_jahr_kleiner' gespeichert)")

    # Hol Ziel-Wert aus Prognosedaten (robuste Auswahl + klare Fehlermeldung)
    sel = progDf.loc[(progDf['Jahr'] == prog_dat_jahr_used) & (progDf['Studie'] == prog_dat_studie), 'Bruttostromverbrauch [TWh]']
    if sel.empty:
        raise ValueError(f"Keine Prognose-Zeile gefunden für Studie='{prog_dat_studie}' und Jahr={prog_dat_jahr_used}")        
    try:
        zielWert_Studie = float(sel.iat[0])
    except Exception as e:
        raise ValueError(f"Fehler beim Lesen des Zielwerts aus Prognosedaten: {e}")
    # Wert 0 sollte bereits herausgefiltert sein, aber zur Sicherheit prüfen
    if zielWert_Studie == 0:
        raise ValueError(f"Prognose-Zeile gefunden, aber der Wert ist 0 für Studie='{prog_dat_studie}' und Jahr={prog_dat_jahr_used} (sollte bereits gefiltert sein)")

    formatierte_zahl = locale.format_string("%.8f", zielWert_Studie, grouping=True)
    print(f"Gesamter Energieverbrauch im Prognosejahr: {formatierte_zahl} [TWh]\n")

    # Berechne Gesamtenergie Simualtionjahr (interpoliert, falls nötig)
    # Vergleiche mit dem tatsächlich verwendeten Prognosejahr (prog_dat_jahr_used),
    # nicht mit dem Funktionsparameter prog_dat_jahr (kann -1 sein).
    if simu_jahr != prog_dat_jahr_used:
        if smaller_years.size > 0 and prog_dat_jahr_kleiner != prog_dat_jahr_used:
            # Interpoliere zwischen dem kleineren Jahr und dem gewählten prog_dat_jahr_used
            sel_kleiner = progDf.loc[(progDf['Jahr'] == prog_dat_jahr_kleiner) & (progDf['Studie'] == prog_dat_studie), 'Bruttostromverbrauch [TWh]']
            if sel_kleiner.empty:
                raise ValueError(f"Keine Prognose-Zeile gefunden für Studie='{prog_dat_studie}' und Jahr={prog_dat_jahr_kleiner}")        
            try:
                zielWert_Studie_kleiner = float(sel_kleiner.iat[0])
            except Exception as e:
                raise ValueError(f"Fehler beim Lesen des Zielwerts aus Prognosedaten: {e}")
            # Wert 0 sollte bereits herausgefiltert sein, aber zur Sicherheit prüfen
            if zielWert_Studie_kleiner == 0:
                raise ValueError(f"Prognose-Zeile gefunden, aber der Wert ist 0 für Studie='{prog_dat_studie}' und Jahr={prog_dat_jahr_kleiner} (sollte bereits gefiltert sein)")
            # Nutze explizit float numpy-arrays, damit keine None/Typ-Konflikte entstehen
            Gesamtenergie_ziel_jahr = np.interp(
                float(simu_jahr),
                np.array([prog_dat_jahr_kleiner, prog_dat_jahr_used], dtype=float),
                np.array([zielWert_Studie_kleiner, zielWert_Studie], dtype=float),
            )
        else:
            # Wenn kein kleineres Jahr verfügbar ist, interpoliere zwischen Referenzjahr
            # und dem tatsächlich ausgewählten Prognosejahr (prog_dat_jahr_used).
            Gesamtenergie_ziel_jahr = np.interp(
                float(simu_jahr),
                np.array([ref_jahr, prog_dat_jahr_used], dtype=float),
                np.array([Gesamtenergie_RefJahr, zielWert_Studie], dtype=float),
            )
    else:
        Gesamtenergie_ziel_jahr = zielWert_Studie

    formatierte_zahl = locale.format_string("%.8f", Gesamtenergie_ziel_jahr, grouping=True)
    print(f"Gesamter Energieverbrauch im Simulationsjahr: {formatierte_zahl} [TWh]\n")
    
    # Berechne den Skalierungsfaktor
    faktor = Gesamtenergie_ziel_jahr /  Gesamtenergie_RefJahr

    formatierte_zahl = locale.format_string("%.14f", faktor, grouping=True)
    print(f"Berechneter Faktor: {formatierte_zahl}\n")

    # Skaliere den Energieverbrauch im Referenzjahr mit dem Faktor
    jahr_offset = simu_jahr - ref_jahr
    df_simu = pd.DataFrame({
        'Datum von': pd.to_datetime(df_refJahr['Datum von']) + pd.DateOffset(years=jahr_offset),
        'Datum bis': pd.to_datetime(df_refJahr['Datum bis']) + pd.DateOffset(years=jahr_offset),
        'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=jahr_offset),
        'Skalierter Netzlast [MWh]': df_refJahr['Netzlast [MWh]'] * faktor
        })
    col.show_first_rows(df_simu)
    return df_simu

def calc_scaled_production_multiyear(produDf: pd.DataFrame, progDf: pd.DataFrame,
                            prod_dat_studie: str, simu_jahr_start: int, simu_jahr_ende: int,
                            ref_jahr: int = 2023, prod_dat_jahr: int = -1) -> pd.DataFrame:
    """
    Skaliert die Energieproduktion eines Referenzjahres basierend auf Prognosedaten für mehrere
    Simulationsjahre und eine ausgewählte Studie - **pro Energiequelle separat**.
    
    Args:
        produDf: DataFrame mit Erzeugungsdaten (MWh) und 'Zeitpunkt'.
        progDf: DataFrame mit Prognosedaten (einzelne Energiequellen-Spalten in TWh).
        prod_dat_studie: Die Studie, aus der der Zielwert entnommen wird.
        ('Agora' | 'BDI - Klimapfade 2.0' | 'dena - KN100' | 'BMWK - LFS TN-Strom' | 'Ariadne - REMIND-Mix' | 'Ariadne - REMod-Mix' | 'Ariadne - TIMES PanEU-Mix')         
        simu_jahr_start: Das Startjahr der Simulation.
        simu_jahr_ende: Das Endjahr der Simulation.
        prod_dat_jahr: Das Jahr der Prognose (default: -1 für automatische Auswahl).
        ref_jahr: Das Referenzjahr im Produktionsdatensatz (default: 2023).
        
    Returns:
        DataFrame mit skalierter Energieproduktion für die Simulationsjahre (alle Viertelstundenwerte).
    """
    df_list = []
    for simu_jahr in range(simu_jahr_start, simu_jahr_ende + 1):
        df_scaled = calc_scaled_production(produDf, progDf,
                                            prod_dat_studie, simu_jahr, ref_jahr,
                                            prod_dat_jahr)
        df_list.append(df_scaled)
    
    return pd.concat(df_list).reset_index(drop=True)

def calc_scaled_production(produDf: pd.DataFrame, progDf: pd.DataFrame,
                            prod_dat_studie: str, simu_jahr: int,
                            ref_jahr: int = 2023, prod_dat_jahr: int = -1) -> pd.DataFrame:
    """
    Skaliert die Energieproduktion eines Referenzjahres basierend auf Prognosedaten für ein
    Simulationsjahr und eine ausgewählte Studie - **pro Energiequelle separat**.
    
    Vorgehen:
    - Referenzjahr im Produktionsdatensatz bestimmen und pro Energiequelle die Jahressumme (TWh) berechnen.
    - Für jede Energiequelle aus progDf (Studie + Jahr) die Zielwerte [TWh] wählen (ggf. interpoliert).
    - Pro Energiequelle einen eigenen Skalierungsfaktor = Ziel / Referenz bestimmen.
    - Alle Viertelstundenwerte der jeweiligen Quelle mit ihrem Faktor skalieren und auf simu_jahr datumsversetzen.
    
    Args:
        produDf: DataFrame mit Erzeugungsdaten (MWh) und 'Zeitpunkt'.
        progDf: DataFrame mit Prognosedaten (einzelne Energiequellen-Spalten in TWh).
        prod_dat_studie: Name der Studie.
        simu_jahr: Simulationsjahr.
        prod_dat_jahr: Gewünschtes Prognosejahr (oder -1 für automatische Wahl).
        ref_jahr: Referenzjahr im Produktionsdatensatz.
        
    Returns:
        DataFrame mit allen Viertelstundenwerten für das Simulationsjahr (Datum von, Datum bis, Zeitpunkt + alle MWh-Spalten skaliert).
    """

    # 1) Referenzjahr herausschneiden
    ist_ref_jahr_vorhanden = (produDf['Zeitpunkt'].dt.year == ref_jahr).any()
    if not ist_ref_jahr_vorhanden:
        raise ValueError(f"Referenzjahr {ref_jahr} nicht im Produktionsdatensatz gefunden.")

    df_refJahr = produDf[(produDf["Zeitpunkt"] >= f"01.01.{ref_jahr} 00:00") & (produDf["Zeitpunkt"] <= f"31.12.{ref_jahr} 23:59")].copy()

    # 2) Verfügbare Prognosejahre ermitteln
    # Wir nutzen eine beliebige TWh-Spalte, um Jahre zu finden - nehmen wir 'Biomasse [TWh]' als Beispiel
    test_col = 'Biomasse [TWh]' if 'Biomasse [TWh]' in progDf.columns else progDf.columns[progDf.columns.str.contains(r'\[TWh\]', regex=True)][0]
    
    studie_data = progDf.loc[progDf['Studie'] == prod_dat_studie].copy()
    studie_data = studie_data.dropna(subset=['Jahr', test_col])
    
    available_years = studie_data['Jahr'].unique()
    if len(available_years) == 0:
        raise ValueError(f"Keine Prognose-Daten für Studie='{prod_dat_studie}' gefunden.")
    try:
        available_years = np.array(sorted([int(y) for y in available_years]))
    except Exception:
        raise ValueError(f"Prognose-Daten enthalten ungültige Jahreswerte für Studie='{prod_dat_studie}'.")

    if prod_dat_jahr is None or int(prod_dat_jahr) < 0:
        ge_years = available_years[available_years >= simu_jahr]
        if ge_years.size > 0:
            prod_dat_jahr_used = int(ge_years.min())
        else:
            prod_dat_jahr_used = int(available_years.max())
    else:
        prod_dat_jahr_used = int(prod_dat_jahr)

    smaller_years = available_years[available_years < simu_jahr]
    prod_dat_jahr_kleiner = int(smaller_years.max()) if smaller_years.size > 0 else None

    print(f"Verfügbare Prognosejahre für Studie '{prod_dat_studie}': {available_years.tolist()}")
    print(f"Ausgewähltes Produktions-Prognosejahr: {prod_dat_jahr_used}")
    if prod_dat_jahr_kleiner is not None:
        print(f"Größtes Prognosejahr < Simulationsjahr ({simu_jahr}): {prod_dat_jahr_kleiner}\n")

    # 3) Mapping produDf (MWh) <-> progDf (TWh) - einzelne Energiequellen
    # produDf hat z.B. "Biomasse [MWh]", "Sonstige Erneuerbare [MWh]", "Sonstige Konventionelle [MWh]", "Pumpspeicher [MWh]"
    # progDf hat "Biomasse [TWh]", "Sonstige [TWh]", "Speicher [TWh]", "Wasserstoff [TWh]", "Abfall [TWh]"
    
    # Definiere Mapping für 1:1-Quellen (produDf -> progDf):
    source_mapping = {
        "Biomasse [MWh]": "Biomasse [TWh]",
        "Wasserkraft [MWh]": "Wasserkraft [TWh]",
        "Wind Offshore [MWh]": "Wind Offshore [TWh]",
        "Wind Onshore [MWh]": "Wind Onshore [TWh]",
        "Photovoltaik [MWh]": "Photovoltaik [TWh]",
        "Kernenergie [MWh]": "Kernenergie [TWh]",
        "Braunkohle [MWh]": "Braunkohle [TWh]",
        "Steinkohle [MWh]": "Steinkohle [TWh]",
        "Erdgas [MWh]": "Erdgas [TWh]",
    }

    # Sonderfälle:
    # - "Sonstige Erneuerbare [MWh]" + "Sonstige Konventionelle [MWh]" -> "Sonstige [TWh]"
    # - "Pumpspeicher [MWh]" bleibt unverändert (Faktor = 1.0)
    # - "Wasserstoff [TWh]" aus progDf wird als neue "Wasserstoff [MWh]" Spalte hinzugefügt
    # - Zusätzlicher Speicher (Differenz zwischen progDf["Speicher [TWh]"] und Pumpspeicher) wird als "Kurz-/Langzeitspeicher [MWh]" verteilt
    # - Abfall: existiert in produDf nicht -> wird ignoriert

    def get_prog_value(prog_col: str) -> float:
        """Holt Wert aus progDf für prod_dat_jahr_used (ggf. interpoliert)"""
        sel = progDf.loc[(progDf['Jahr'] == prod_dat_jahr_used) & (progDf['Studie'] == prod_dat_studie), prog_col]
        if sel.empty or pd.isna(sel.iat[0]):
            return 0.0
        val_used = float(sel.iat[0])
        
        # Interpolation falls simu_jahr != prod_dat_jahr_used
        if simu_jahr != prod_dat_jahr_used:
            if smaller_years.size > 0 and prod_dat_jahr_kleiner is not None and prod_dat_jahr_kleiner != prod_dat_jahr_used:
                sel_kleiner = progDf.loc[(progDf['Jahr'] == prod_dat_jahr_kleiner) & (progDf['Studie'] == prod_dat_studie), prog_col]
                if not sel_kleiner.empty and not pd.isna(sel_kleiner.iat[0]):
                    val_kleiner = float(sel_kleiner.iat[0])
                    return np.interp(float(simu_jahr),
                                   np.array([prod_dat_jahr_kleiner, prod_dat_jahr_used], dtype=float),
                                   np.array([val_kleiner, val_used], dtype=float))
            # Fallback: Interpolation ref_jahr <-> prod_dat_jahr_used (brauchen ref-Wert)
            # Wir haben hier nur prog-Werte, nehmen vereinfacht val_used (keine Rückinterpolation zu ref_jahr)
            # oder extrapolieren linear - aber sauberer wäre zwischen ref und prog zu interpolieren.
            # Für jetzt: wenn kein kleineres Jahr, nutzen wir val_used direkt.
        return val_used

    def get_ref_twh(mwh_col: str) -> float:
        """Berechnet Jahressumme im Referenzjahr für eine MWh-Spalte und gibt TWh zurück"""
        if mwh_col not in df_refJahr.columns:
            return 0.0
        return col.get_column_total(df_refJahr, mwh_col) / 1_000_000.0

    # 4) Pro Energiequelle Skalierungsfaktoren berechnen
    scaling_factors = {}
    
    # 1:1 Mappings
    for mwh_col, twh_col in source_mapping.items():
        ref_twh = get_ref_twh(mwh_col)
        prog_twh = get_prog_value(twh_col)
        if ref_twh > 0:
            scaling_factors[mwh_col] = prog_twh / ref_twh
        else:
            scaling_factors[mwh_col] = 1.0  # Keine Änderung, wenn ref=0
        print(f"{mwh_col}: Ref={ref_twh:.4f} TWh, Prog={prog_twh:.4f} TWh, Faktor={scaling_factors[mwh_col]:.6f}")

    # Sonstige Erneuerbare + Sonstige Konventionelle -> Sonstige [TWh]
    ref_soe = get_ref_twh("Sonstige Erneuerbare [MWh]")
    ref_sok = get_ref_twh("Sonstige Konventionelle [MWh]")
    ref_sonstige_total = ref_soe + ref_sok
    prog_sonstige = get_prog_value("Sonstige [TWh]")
    if ref_sonstige_total > 0:
        faktor_sonstige = prog_sonstige / ref_sonstige_total
    else:
        faktor_sonstige = 1.0
    scaling_factors["Sonstige Erneuerbare [MWh]"] = faktor_sonstige
    scaling_factors["Sonstige Konventionelle [MWh]"] = faktor_sonstige
    print(f"Sonstige Erneuerbare [MWh]: Ref={ref_soe:.4f} TWh, Faktor={faktor_sonstige:.6f}")
    print(f"Sonstige Konventionelle [MWh]: Ref={ref_sok:.4f} TWh, Faktor={faktor_sonstige:.6f}")

    # Pumpspeicher bleibt unverändert (Faktor = 1.0)
    ref_ps = get_ref_twh("Pumpspeicher [MWh]")
    scaling_factors["Pumpspeicher [MWh]"] = 1.0
    print(f"Pumpspeicher [MWh]: Ref={ref_ps:.4f} TWh, bleibt unverändert (Faktor=1.0)")

    # Wasserstoff aus progDf (existiert nicht in produDf -> wird neu hinzugefügt)
    prog_wasserstoff = get_prog_value("Wasserstoff [TWh]")
    print(f"Wasserstoff [MWh]: Ref=0.0000 TWh, Prog={prog_wasserstoff:.4f} TWh (neue Spalte wird hinzugefügt)")

    # Zusätzlicher Speicher = progDf["Speicher [TWh]"] - Pumpspeicher_Ref
    # Dieser wird als "Kurz-/Langzeitspeicher [MWh]" hinzugefügt
    prog_speicher_total = get_prog_value("Speicher [TWh]")
    zusatz_speicher_twh = max(0.0, prog_speicher_total - ref_ps)  # Nur positive Differenz
    print(f"Kurz-/Langzeitspeicher [MWh]: Zusätzlich={zusatz_speicher_twh:.4f} TWh (= Speicher {prog_speicher_total:.4f} - Pumpspeicher {ref_ps:.4f})\n")

    # 5) Skaliere jede MWh-Spalte des Referenzjahres mit ihrem Faktor und verschiebe auf simu_jahr
    jahr_offset = simu_jahr - ref_jahr
    df_simu = pd.DataFrame({
        'Datum von': pd.to_datetime(df_refJahr['Datum von']) + pd.DateOffset(years=jahr_offset),
        'Datum bis': pd.to_datetime(df_refJahr['Datum bis']) + pd.DateOffset(years=jahr_offset),
        'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=jahr_offset),
    })

    for mwh_col in df_refJahr.columns:
        if mwh_col.endswith('[MWh]'):
            faktor = scaling_factors.get(mwh_col, 1.0)
            df_simu[mwh_col] = df_refJahr[mwh_col] * faktor

    # 6) Wasserstoff hinzufügen (gleichmäßig über das Jahr verteilt)
    # Jahressumme in MWh -> auf alle Zeitschritte verteilen
    num_timesteps = len(df_simu)
    wasserstoff_pro_zeitschritt = (prog_wasserstoff * 1_000_000.0) / num_timesteps if num_timesteps > 0 else 0.0
    df_simu['Wasserstoff [MWh]'] = wasserstoff_pro_zeitschritt

    # 7) Kurz-/Langzeitspeicher hinzufügen (gleichmäßig über das Jahr verteilt)
    speicher_pro_zeitschritt = (zusatz_speicher_twh * 1_000_000.0) / num_timesteps if num_timesteps > 0 else 0.0
    df_simu['Kurz-/Langzeitspeicher [MWh]'] = speicher_pro_zeitschritt

    col.show_first_rows(df_simu)
    return df_simu


