import pandas as pd
import numpy as np
import data_processing.col as col
import data_processing.gen as gen
import data_processing.generation_profile as genPro
import locale
from typing import List, Optional
from data_processing.load_profile import apply_load_profile_to_simulation
from config_manager import ConfigManager


def calc_scaled_consumption_multiyear(conDf: pd.DataFrame, progDf: pd.DataFrame,
                            prog_dat_studie: str, simu_jahr_start: int, simu_jahr_ende: int,
                            ref_jahr: int = 2023, prog_dat_jahr: int = -1,
                            use_load_profile: bool = True) -> pd.DataFrame:
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
        use_load_profile: Wenn True, wird das Lastprofil S25 verwendet (empfohlen).
                         Wenn False, wird einfach linear skaliert (alte Methode).
        
    Returns:
        DataFrame mit skaliertem Energieverbrauch für die Simulationsjahre.
    """
    df_list = []
    for simu_jahr in range(simu_jahr_start, simu_jahr_ende + 1):
        df_scaled = calc_scaled_consumption(conDf, progDf,
                                            prog_dat_studie, simu_jahr, prog_dat_jahr,
                                            ref_jahr, use_load_profile)
        df_list.append(df_scaled)
    
    return pd.concat(df_list).reset_index(drop=True)

def calc_scaled_consumption(conDf: pd.DataFrame, progDf: pd.DataFrame,
                            prog_dat_studie: str, simu_jahr: int, prog_dat_jahr: int = -1,
                            ref_jahr: int = 2023, use_load_profile: bool = True) -> pd.DataFrame:
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
        use_load_profile: Wenn True, wird das Lastprofil S25 verwendet (empfohlen).
                         Wenn False, wird einfach linear skaliert (alte Methode).
        
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

    # Erstelle Basis-DataFrame mit aktualisierten Zeitstempeln
    jahr_offset = simu_jahr - ref_jahr
    df_simu = pd.DataFrame({
        'Datum von': pd.to_datetime(df_refJahr['Datum von']) + pd.DateOffset(years=jahr_offset),
        'Datum bis': pd.to_datetime(df_refJahr['Datum bis']) + pd.DateOffset(years=jahr_offset),
        'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=jahr_offset),
        })
    
    if use_load_profile:
        # NEUE METHODE: Verwende Lastprofil S25 für realistische Lastkurve
        print("→ Verwende Lastprofil S25 für realistische Lastschwankungen")
        df_simu = apply_load_profile_to_simulation(
            df_simu,
            total_consumption_twh=Gesamtenergie_ziel_jahr
        )
        # Umbenennen für Konsistenz
        df_simu.rename(columns={'Lastprofil Netzlast [MWh]': 'Skalierte Netzlast [MWh]'}, inplace=True)
    else:
        # ALTE METHODE: Einfache lineare Skalierung (konstanter Faktor)
        print("→ Verwende einfache lineare Skalierung (konstanter Faktor)")
        df_simu['Skalierte Netzlast [MWh]'] = df_refJahr['Netzlast [MWh]'] * faktor
    
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
    
    Neue Regeln:
    - Wasserstoff/Abfall aus progDf werden gleichmäßig über das Jahr verteilt (falls vorhanden).
    - Sonstige [TWh] aus progDf entspricht nur "Sonstige Erneuerbare [MWh]" (SOE).
    - "Sonstige Konventionelle [MWh]" (SOK) wird vernachlässigt (bleibt unverändert).
    - Pumpspeicher [MWh] wird vernachlässigt (bleibt unverändert).
    - Speicher [TWh] aus progDf wird bei der Erzeugung ignoriert.
    
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

    # Neue Regeln (Sonderfälle):
    # - "Sonstige [TWh]" aus progDf -> nur "Sonstige Erneuerbare [MWh]" (SOE)
    # - "Sonstige Konventionelle [MWh]" (SOK) wird vernachlässigt (bleibt unverändert)
    # - "Pumpspeicher [MWh]" wird vernachlässigt (bleibt unverändert)
    # - "Speicher [TWh]" aus progDf wird ignoriert
    # - "Wasserstoff [TWh]" aus progDf -> neue Spalte, gleichmäßig verteilt
    # - "Abfall [TWh]" aus progDf -> neue Spalte, gleichmäßig verteilt (falls vorhanden)

    def get_prog_value_interpolated(prog_col: str, ref_value: Optional[float] = None) -> float:
        """
        Holt Wert aus progDf für simu_jahr mit intelligenter Interpolation.
        
        Regeln:
        - Wenn Prognose = 0: Interpoliere vom letzten Nicht-Null-Wert auf 0
        - Wenn ref_value = 0 (z.B. Wasserstoff): Interpoliere von 0 zum ersten Prognosewert
        - Sonst: Normal zwischen Prognosejahren interpolieren
        """
        # Hole alle verfügbaren Jahre für diese Spalte (nicht nur test_col)
        studie_data_col = progDf.loc[progDf['Studie'] == prod_dat_studie, ['Jahr', prog_col]].copy()
        studie_data_col = studie_data_col.dropna(subset=[prog_col])
        
        if studie_data_col.empty:
            return 0.0
        
        # Sortiere nach Jahr
        studie_data_col = studie_data_col.sort_values('Jahr')
        years_list = studie_data_col['Jahr'].astype(int).tolist()
        values_list = studie_data_col[prog_col].astype(float).tolist()
        
        # Finde Position von simu_jahr
        if simu_jahr in years_list:
            # Exakt vorhanden
            idx = years_list.index(simu_jahr)
            return values_list[idx]
        
        # Finde umgebende Jahre
        smaller = [(y, v) for y, v in zip(years_list, values_list) if y < simu_jahr]
        larger = [(y, v) for y, v in zip(years_list, values_list) if y > simu_jahr]
        
        # Fall 1: simu_jahr liegt vor dem ersten Prognosejahr
        if not smaller and larger:
            # Interpoliere von ref_value (oder 0) zum ersten Prognosewert
            jahr_1 = ref_jahr
            val_1 = ref_value if ref_value is not None else 0.0
            jahr_2, val_2 = larger[0]
            return np.interp(float(simu_jahr), [float(jahr_1), float(jahr_2)], [val_1, val_2])
        
        # Fall 2: simu_jahr liegt nach dem letzten Prognosejahr
        if smaller and not larger:
            # Nutze letzten verfügbaren Wert (oder 0 falls letzter Wert = 0)
            return smaller[-1][1]
        
        # Fall 3: simu_jahr liegt zwischen zwei Prognosejahren
        if smaller and larger:
            jahr_1, val_1 = smaller[-1]
            jahr_2, val_2 = larger[0]
            
            # Spezialfall: Wenn val_2 = 0, dann linear auf 0 interpolieren
            if val_2 == 0.0:
                return np.interp(float(simu_jahr), [float(jahr_1), float(jahr_2)], [val_1, 0.0])
            
            # Normaler Fall: linear interpolieren
            return np.interp(float(simu_jahr), [float(jahr_1), float(jahr_2)], [val_1, val_2])
        
        # Fallback
        return 0.0

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
        prog_twh = get_prog_value_interpolated(twh_col, ref_twh)
        if ref_twh > 0:
            scaling_factors[mwh_col] = prog_twh / ref_twh
        else:
            # Wenn Referenz = 0, aber Prognose > 0, setze Faktor auf sehr groß (oder handle speziell)
            scaling_factors[mwh_col] = 1.0 if prog_twh == 0 else 1.0
        print(f"{mwh_col}: Ref={ref_twh:.4f} TWh, Prog={prog_twh:.4f} TWh, Faktor={scaling_factors[mwh_col]:.6f}")

    # Neue Regel: Sonstige [TWh] aus progDf -> nur Sonstige Erneuerbare [MWh] (SOE)
    ref_soe = get_ref_twh("Sonstige Erneuerbare [MWh]")
    prog_sonstige = get_prog_value_interpolated("Sonstige [TWh]", ref_soe)
    if ref_soe > 0:
        faktor_soe = prog_sonstige / ref_soe
    else:
        faktor_soe = 1.0
    scaling_factors["Sonstige Erneuerbare [MWh]"] = faktor_soe
    print(f"Sonstige Erneuerbare [MWh]: Ref={ref_soe:.4f} TWh, Prog={prog_sonstige:.4f} TWh, Faktor={faktor_soe:.6f}")

    # Sonstige Konventionelle [MWh] komplett entfernen (nicht in Ergebnis aufnehmen)
    ref_sok = get_ref_twh("Sonstige Konventionelle [MWh]")
    print(f"Sonstige Konventionelle [MWh]: Ref={ref_sok:.4f} TWh, wird aus Ausgabe entfernt")

    # Pumpspeicher [MWh] komplett entfernen (nicht in Ergebnis aufnehmen)
    ref_ps = get_ref_twh("Pumpspeicher [MWh]")
    print(f"Pumpspeicher [MWh]: Ref={ref_ps:.4f} TWh, wird aus Ausgabe entfernt")

    # Wasserstoff nicht mehr hinzufügen (keine Spalte im Ergebnis)

    # Abfall aus progDf (existiert nicht in produDf -> wird gleichmäßig verteilt, falls vorhanden)
    prog_abfall = get_prog_value_interpolated("Abfall [TWh]", 0.0)
    print(f"Abfall [MWh]: Ref=0.0000 TWh, Prog={prog_abfall:.4f} TWh (gleichmäßig über Jahr verteilt)")

    # Speicher [TWh] aus progDf wird bei der Erzeugung ignoriert
    print(f"Speicher [TWh] aus progDf wird bei der Erzeugung ignoriert\n")

    # 5) Skaliere jede MWh-Spalte des Referenzjahres mit ihrem Faktor und verschiebe auf simu_jahr
    jahr_offset = simu_jahr - ref_jahr
    df_simu = pd.DataFrame({
        'Datum von': pd.to_datetime(df_refJahr['Datum von']) + pd.DateOffset(years=jahr_offset),
        'Datum bis': pd.to_datetime(df_refJahr['Datum bis']) + pd.DateOffset(years=jahr_offset),
        'Zeitpunkt': pd.to_datetime(df_refJahr['Zeitpunkt']) + pd.DateOffset(years=jahr_offset),
    })

    for mwh_col in df_refJahr.columns:
        if mwh_col.endswith('[MWh]'):
            # Überspringe ausgewählte Spalten, sie sollen in der Ausgabe fehlen
            if mwh_col in {"Sonstige Konventionelle [MWh]", "Pumpspeicher [MWh]"}:
                continue
            faktor = scaling_factors.get(mwh_col, 1.0)
            df_simu[mwh_col] = df_refJahr[mwh_col] * faktor

    # 6) Wasserstoff nicht hinzufügen (keine Spalte mehr)
    num_timesteps = len(df_simu)

    # 7) Abfall hinzufügen (gleichmäßig über das Jahr verteilt, falls vorhanden)
    if prog_abfall > 0:
        abfall_pro_zeitschritt = (prog_abfall * 1_000_000.0) / num_timesteps if num_timesteps > 0 else 0.0
        df_simu['Abfall [MWh]'] = abfall_pro_zeitschritt

    col.show_first_rows(df_simu)
    return df_simu

def simulate_storage_generic(
    df_balance: pd.DataFrame,
    type_name: str, # "Batteriespeicher" | "Pumpspeicher" | "Wasserstoffspeicher"
    capacity_mwh: float,
    max_charge_mw: float,
    max_discharge_mw: float,
    charge_efficiency: float,
    discharge_efficiency: float,
    initial_soc_mwh: float = 0.0,
    min_soc_mwh: float = 0.0,
    max_soc_mwh: Optional[float] = None
) -> pd.DataFrame:
    """
    Simuliert einen generischen Energiespeicher mit Bucket-Modell.
    
    Flexible Speichersimulation für verschiedene Speichertypen (Batterie, Pumpspeicher, Wasserstoff).
    Iteriert durch alle Zeitschritte (Viertelstunden) und gleicht Überschüsse/Defizite
    mit dem Speicher aus. Berücksichtigt Kapazitätsgrenzen, Lade-/Entladeleistung,
    Wirkungsgrade und Min/Max SOC-Limits.
    
    Logik:
    - Überschuss (Balance > 0): Versuche zu laden (begrenzt durch max_charge_mw und verbleibende Kapazität bis max_soc_mwh)
    - Defizit (Balance < 0): Versuche zu entladen (begrenzt durch max_discharge_mw und verfügbare Energie über min_soc_mwh)
    - Wirkungsgrade werden beim Laden/Entladen angewendet
    
    Args:
        df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
        type_name: Name des Speichertyps (z.B. "Batteriespeicher", "Pumpspeicher", "Wasserstoffspeicher")
        capacity_mwh: Speicherkapazität in MWh
        max_charge_mw: Maximale Ladeleistung in MW
        max_discharge_mw: Maximale Entladeleistung in MW
        charge_efficiency: Ladewirkungsgrad (0.0-1.0)
        discharge_efficiency: Entladewirkungsgrad (0.0-1.0)
        initial_soc_mwh: Initialer Ladestand in MWh (Default: 0.0)
        min_soc_mwh: Minimaler SOC in MWh - Schutz vor Tiefentladung (Default: 0.0)
        max_soc_mwh: Maximaler SOC in MWh (Default: None = capacity_mwh)
    
    Returns:
        DataFrame mit Spalten:
        - 'Zeitpunkt': Zeitstempel
        - '{type_name}_SOC_MWh': Ladestand des Speichers pro Zeitschritt
        - '{type_name}_Charged_MWh': Geladene Energie pro Zeitschritt
        - '{type_name}_Discharged_MWh': Entladene Energie pro Zeitschritt
        - 'Rest_Balance_MWh': Restbilanz nach Speicheroperationen
    """
    
    if max_soc_mwh is None:
        max_soc_mwh = capacity_mwh
    
    #  DataFrame kopieren und initiale Balance berechnen
    df = df_balance.copy()
    balance_series = df['Gesamterzeugung [MWh]'] - df['Skalierte Netzlast [MWh]']
    
    # Initialisiere Arrays für Ergebnisse
    n = len(balance_series)
    soc = np.zeros(n)
    charged = np.zeros(n) # Geladene Energie pro Zeitschritt
    discharged = np.zeros(n) # Entladene Energie pro Zeitschritt
    
    current_soc = initial_soc_mwh
    dt = 0.25 # 15 Minuten
    
    # Konvertiere min/max SOC in absolute Werte
    max_charge_energy_per_step = max_charge_mw * dt
    max_discharge_energy_per_step = max_discharge_mw * dt
    
    print(f"\n{'='*80}")
    print(f"Simuliere {type_name}:")
    print(f"{'='*80}")
    print(f"Kapazität: {capacity_mwh:,.0f} MWh")
    print(f"Min SOC: {min_soc_mwh:,.0f} MWh ({min_soc_mwh/capacity_mwh*100:.1f}%)")
    print(f"Max SOC: {max_soc_mwh:,.0f} MWh ({max_soc_mwh/capacity_mwh*100:.1f}%)")
    print(f"Initial SOC: {initial_soc_mwh:,.0f} MWh ({initial_soc_mwh/capacity_mwh*100:.1f}%)")
    print(f"Max Ladeleistung: {max_charge_mw:,.0f} MW")
    print(f"Max Entladeleistung: {max_discharge_mw:,.0f} MW")
    print(f"Wirkungsgrade: Laden {charge_efficiency*100:.1f}%, Entladen {discharge_efficiency*100:.1f}%")
    
    # Iteriere durch alle Zeitschritte
    for i in range(n):
        bal = balance_series.iloc[i]
        
        if bal > 0:
            # Fall A: Überschuss - Versucht zu laden
            free_space = max_soc_mwh - current_soc
            max_grid_intake_by_capacity = free_space / charge_efficiency
            energy_in_from_grid = min(bal, max_charge_energy_per_step, max_grid_intake_by_capacity)

            # Berechne soc stand nach dem Laden
            current_soc += energy_in_from_grid * charge_efficiency
            charged[i] = energy_in_from_grid
            
        elif bal < 0:
            deficit = abs(bal)
            # Fall B: Defizit - Versucht zu entladen
            available_energy_above_min = current_soc - min_soc_mwh
            max_grid_output_by_power = max_discharge_energy_per_step
            max_grid_output_by_content = available_energy_above_min * discharge_efficiency
            energy_out_to_grid = min(deficit, max_grid_output_by_power, max_grid_output_by_content)

            # Berechne soc stand nach dem Entladen
            current_soc -= energy_out_to_grid / discharge_efficiency
            discharged[i] = energy_out_to_grid
            
        soc[i] = current_soc
    
    # Baue Ergebnis-DataFrame
    result = pd.DataFrame({
        'Zeitpunkt': df_balance['Zeitpunkt'],
        f'{type_name}_SOC_MWh': soc,
        f'{type_name}_Charged_MWh': charged,
        f'{type_name}_Discharged_MWh': discharged,
        # Restbilanz berechnen:
        # Ursprüngliche Balance - Geladen + Entladen
        'Rest_Balance_MWh': balance_series - charged + discharged
    })
    
    print(f"\nErgebnisse:")
    print(f"Geladene Energie: {charged.sum():,.0f} MWh")
    print(f"Entladene Energie: {discharged.sum():,.0f} MWh")
    print(f"Finaler SOC: {soc[-1]:,.0f} MWh ({soc[-1]/capacity_mwh*100:.1f}%)")
    print(f"Max SOC erreicht: {soc.max():,.0f} MWh ({soc.max()/capacity_mwh*100:.1f}%)")
    print(f"Min SOC erreicht: {soc.min():,.0f} MWh ({soc.min()/capacity_mwh*100:.1f}%)")
    print(f"{'='*80}\n")
    
    return result


def simulate_production(
    cfg: ConfigManager,
    smardGeneration: pd.DataFrame,
    smardCapacity: pd.DataFrame,
    capacity_dict: dict,
    wind_on_weather: str, wind_off_weather: str, pv_weather: str,
    simu_jahr: int
) -> pd.DataFrame:
    
    """
    Simuliert die Energieproduktion für alle Technologien basierend auf SMARD-Daten
    und Ziel-Installierte-Leistung für ein Simulationsjahr.
    
    Args:
        smardGeneration: DataFrame mit SMARD Erzeugungsdaten (Kapazitätsfaktoren 0-1)
        smardCapacity: DataFrame mit installierten Kapazitäten im Referenzjahr
        capacity_dict: Dictionary mit Format:
                      {"Photovoltaik":{"2030":150000,"2045":385000}, 
                       "Wind_Onshore":{"2030":81000,"2045":145000},
                       ...} (Werte in MW)
        wind_on_weather: Weather-Profil für Wind Onshore ("good", "average", "bad")
        wind_off_weather: Weather-Profil für Wind Offshore ("good", "average", "bad")
        pv_weather: Weather-Profil für Photovoltaik ("good", "average", "bad")
        simu_jahr: Das Zieljahr für die Simulation
    
    Returns:
        DataFrame mit skalierter Energieproduktion für alle Technologien im Simulationsjahr
    """

    # Suche Referenzjahre für das filtern der SMARD-Daten
    windOn_smard_ref_jahr = cfg.get_generation_year("Wind_Onshore", wind_on_weather)
    windOff_smard_ref_jahr = cfg.get_generation_year("Wind_Offshore", wind_off_weather)
    pv_smard_ref_jahr = cfg.get_generation_year("Photovoltaik", pv_weather)
    ref_jahr = cfg.config["GENERATION_SIMULATION"]["optimal_reference_years_by_technology"]["default"]

    # Bereite SMARD-Daten vor
    smardGeneration = smardGeneration.set_index("Zeitpunkt")
    smardGeneration.index = pd.to_datetime(smardGeneration.index)

    df_windOn_ref = smardGeneration.loc[str(windOn_smard_ref_jahr)].copy()
    df_windOff_ref = smardGeneration.loc[str(windOff_smard_ref_jahr)].copy()
    df_pv_ref = smardGeneration.loc[str(pv_smard_ref_jahr)].copy()
    df_ref = smardGeneration.loc[str(ref_jahr)].copy()

    df_windOn_refCap = smardCapacity[smardCapacity["Jahr"] == windOn_smard_ref_jahr]
    df_windOff_refCap = smardCapacity[smardCapacity["Jahr"] == windOff_smard_ref_jahr]
    df_pv_refCap = smardCapacity[smardCapacity["Jahr"] == pv_smard_ref_jahr]
    df_refCap = smardCapacity[smardCapacity["Jahr"] == ref_jahr]

    # bereite ziel Kapazitäten für simu_jahr vor
    

    # generiere GeneratioProfile für alle Technologien

    # Wind Onshore
    df_windOn_Profile = genPro.generate_generation_profile(
                            df_windOn_ref,
                            df_windOn_refCap,
                            False
                            )
    
    # Wind Offshore
    df_windOff_Profile = genPro.generate_generation_profile(
                            df_windOff_ref,
                            df_windOff_refCap,
                            False
                            )
    
    # Photovoltaik
    df_pv_Profile = genPro.generate_generation_profile(
                            df_pv_ref,
                            df_pv_refCap,
                            False
                            )
    
    # Sonstige Technologien (Braunkohle, Steinkohle, Erdgas, Kernenergie, Wasserkraft, Biomasse)
    df_other_Profile = genPro.generate_generation_profile(
                            df_ref,
                            df_refCap,
                            True
                            )
    
    # Simuliere Produktion für alle Technologien

    # Konvertiere target_year zu String für Dictionary-Zugriff
    target_year_str = str(simu_jahr)
    target_year_int = int(simu_jahr)
    
    # Initialisiere Ergebnis-DataFrame mit Zeitpunkt-Spalte
    df_result = pd.DataFrame()
    if 'Zeitpunkt' in df_windOn_Profile.columns:
        df_result['Zeitpunkt'] = df_windOn_Profile['Zeitpunkt'].copy()
    elif 'Zeitpunkt' in df_windOff_Profile.columns:
        df_result['Zeitpunkt'] = df_windOff_Profile['Zeitpunkt'].copy()
    elif 'Zeitpunkt' in df_pv_Profile.columns:
        df_result['Zeitpunkt'] = df_pv_Profile['Zeitpunkt'].copy()
    elif 'Zeitpunkt' in df_other_Profile.columns:
        df_result['Zeitpunkt'] = df_other_Profile['Zeitpunkt'].copy()
    else:
        # Wenn keine Zeitpunkt-Spalte, nutze Index von einem der Profile
        df_result['Zeitpunkt'] = df_windOn_Profile.index
    
    # Verarbeitungsfaktor: 0.25 für Viertelstunden
    quarter_hour_factor = 0.25
    
    # 1. Wind Onshore
    if 'Wind_Onshore' in capacity_dict:
        target_capacity = capacity_dict['Wind_Onshore'].get(target_year_str, 
                         capacity_dict['Wind_Onshore'].get(target_year_int, 0))
        if target_capacity > 0:
            # Suche nach passender Spalte (mit verschiedenen Namensformaten)
            possible_cols = ['Wind Onshore [MWh]', 'Wind_Onshore [MWh]', 'Wind Onshore', 'Wind_Onshore', 'Onshore [MWh]']
            wind_on_col = None
            for col in possible_cols:
                if col in df_windOn_Profile.columns:
                    wind_on_col = col
                    break
            
            if wind_on_col:
                df_result['Wind Onshore [MWh]'] = (
                    df_windOn_Profile[wind_on_col].values * target_capacity * quarter_hour_factor
                )
    
    # 2. Wind Offshore
    if 'Wind_Offshore' in capacity_dict:
        target_capacity = capacity_dict['Wind_Offshore'].get(target_year_str,
                         capacity_dict['Wind_Offshore'].get(target_year_int, 0))
        if target_capacity > 0:
            # Suche nach passender Spalte (mit verschiedenen Namensformaten)
            possible_cols = ['Wind Offshore [MWh]', 'Wind_Offshore [MWh]', 'Wind Offshore', 'Wind_Offshore', 'Offshore [MWh]']
            wind_off_col = None
            for col in possible_cols:
                if col in df_windOff_Profile.columns:
                    wind_off_col = col
                    break
            
            if wind_off_col:
                df_result['Wind Offshore [MWh]'] = (
                    df_windOff_Profile[wind_off_col].values * target_capacity * quarter_hour_factor
                )
    
    # 3. Photovoltaik
    if 'Photovoltaik' in capacity_dict:
        target_capacity = capacity_dict['Photovoltaik'].get(target_year_str,
                         capacity_dict['Photovoltaik'].get(target_year_int, 0))
        if target_capacity > 0:
            # Suche nach passender Spalte
            possible_cols = ['Photovoltaik [MWh]', 'PV [MWh]', 'Photovoltaik', 'Solar [MWh]']
            pv_col = None
            for col in possible_cols:
                if col in df_pv_Profile.columns:
                    pv_col = col
                    break
            
            if pv_col:
                df_result['Photovoltaik [MWh]'] = (
                    df_pv_Profile[pv_col].values * target_capacity * quarter_hour_factor
                )
    
    # 4. Alle anderen Technologien aus df_other_Profile
    other_technologies = [
        'Biomasse', 'Wasserkraft', 'Erdgas', 'Steinkohle', 'Braunkohle', 
        'Kernenergie', 'Sonstige Erneuerbare'
    ]
    
    for tech in other_technologies:
        tech_col_name = f'{tech} [MWh]'
        if tech in capacity_dict and tech_col_name in df_other_Profile.columns:
            target_capacity = capacity_dict[tech].get(target_year_str,
                             capacity_dict[tech].get(target_year_int, 0))
            if target_capacity > 0:
                df_result[tech_col_name] = (
                    df_other_Profile[tech_col_name].values * target_capacity * quarter_hour_factor
                )
    
    # Setze das Jahr in der Zeitpunkt-Spalte auf das Simulationsjahr
    if 'Zeitpunkt' in df_result.columns:
        df_result['Zeitpunkt'] = pd.to_datetime(df_result['Zeitpunkt'])
        # Ersetze das Jahr durch das Simulationsjahr
        df_result['Zeitpunkt'] = df_result['Zeitpunkt'].apply(
            lambda x: x.replace(year=simu_jahr)
        )
    
    return df_result

def simulate_consumption(
    lastH: pd.DataFrame, 
    lastG: pd.DataFrame, 
    lastL: pd.DataFrame, 
    lastZielH: float, 
    lastZielG: float, 
    lastZielL: float, 
    simu_jahr: int
) -> pd.DataFrame:
    """
    Simuliert den Energieverbrauch basierend auf BDEW-Lastprofilen für Haushalte (H25), 
    Gewerbe (G25) und Landwirtschaft (L25) und vorgegebenen Jahres-Zielwerten.
    
    Die Funktion:
    1. Lädt die BDEW-Standardlastprofile (H25, G25, L25) aus dem Jahr 2025
    2. Erstellt einen vollständigen Jahresverlauf basierend auf:
       - Wochentagen (WT)
       - Samstagen (SA)
       - Sonn- und Feiertagen (FT)
    3. Skaliert die Profile so, dass die Jahressummen den Zielwerten entsprechen
    4. Gibt einen DataFrame mit Viertelstunden-Auflösung zurück
    
    Args:
        lastH (pd.DataFrame): BDEW H25-Lastprofil (Haushalte)
        lastG (pd.DataFrame): BDEW G25-Lastprofil (Gewerbe)
        lastL (pd.DataFrame): BDEW L25-Lastprofil (Landwirtschaft)
        lastZielH (float): Ziel-Jahresverbrauch Haushalte [TWh]
        lastZielG (float): Ziel-Jahresverbrauch Gewerbe [TWh]
        lastZielL (float): Ziel-Jahresverbrauch Landwirtschaft [TWh]
        simu_jahr (int): Simulationsjahr (z.B. 2030 oder 2045)
        
    Returns:
        pd.DataFrame: DataFrame mit Spalten:
            - Zeitpunkt: DateTime-Index mit Viertelstunden-Auflösung
            - Haushalte [MWh]: Verbrauch Haushalte
            - Gewerbe [MWh]: Verbrauch Gewerbe
            - Landwirtschaft [MWh]: Verbrauch Landwirtschaft
            - Gesamt [MWh]: Summe aller Sektoren
    """
    
    def prepare_load_profile(df: pd.DataFrame) -> pd.DataFrame:
        """
        Bereitet ein BDEW-Lastprofil vor: Komma -> Punkt, sichert numerische Werte.
        """
        df = df.copy()
        
        # Ersetze Kommas durch Punkte in der value_kWh Spalte
        if 'value_kWh' in df.columns:
            # Falls als String eingelesen, konvertieren
            if df['value_kWh'].dtype == 'object':
                df['value_kWh'] = df['value_kWh'].astype(str).str.replace(',', '.')
            df['value_kWh'] = pd.to_numeric(df['value_kWh'], errors='coerce')
        
        # Stelle sicher, dass timestamp ein Datetime ist
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Stelle sicher, dass month ein int ist
        if 'month' in df.columns:
            df['month'] = pd.to_numeric(df['month'], errors='coerce').astype('Int64')
        
        return df
    
    # Vorbereiten der drei Lastprofile
    lastH = prepare_load_profile(lastH)
    lastG = prepare_load_profile(lastG)
    lastL = prepare_load_profile(lastL)
    
    # Erstelle Kalender für das Simulationsjahr
    
    # Erzeuge alle Viertelstunden des Jahres
    start_date = pd.Timestamp(f'{simu_jahr}-01-01 00:00:00')
    end_date = pd.Timestamp(f'{simu_jahr}-12-31 23:45:00')
    zeitpunkte = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Erstelle Basis-DataFrame
    df_result = pd.DataFrame({'Zeitpunkt': zeitpunkte})
    df_result['month'] = df_result['Zeitpunkt'].dt.month
    df_result['weekday'] = df_result['Zeitpunkt'].dt.weekday  # 0=Montag, 6=Sonntag
    df_result['day'] = df_result['Zeitpunkt'].dt.day
    
    # Deutsche Feiertage für das Simulationsjahr
    # Wir nutzen das holidays Package für bundeseinheitliche Feiertage
    try:
        import holidays
        # Standardmäßig bundeseinheitliche Feiertage. 
        # Für bundeslandspezifische Feiertage müsste hier das Bundesland (prov) übergeben werden.
        de_holidays = holidays.Germany(years=simu_jahr)
        feiertage = [pd.Timestamp(date) for date in de_holidays.keys()]
    except ImportError:
        # Fallback: Feste Feiertage (vereinfacht)
        feiertage = [
            pd.Timestamp(f'{simu_jahr}-01-01'),  # Neujahr
            pd.Timestamp(f'{simu_jahr}-05-01'),  # Tag der Arbeit
            pd.Timestamp(f'{simu_jahr}-10-03'),  # Tag der Deutschen Einheit
            pd.Timestamp(f'{simu_jahr}-12-25'),  # 1. Weihnachtstag
            pd.Timestamp(f'{simu_jahr}-12-26'),  # 2. Weihnachtstag
        ]
    
    # Bestimme day_type für jeden Zeitpunkt
    def get_day_type(row):
        date = row['Zeitpunkt'].date()
        is_holiday = pd.Timestamp(date) in feiertage
        is_sunday = row['weekday'] == 6
        
        # BDEW-Regel: 24.12. und 31.12. gelten als Samstag, sofern sie nicht auf einen Sonntag fallen
        is_heiligabend_silvester = (row['month'] == 12) and (row['day'] in [24, 31])
        
        if is_holiday or is_sunday:
            return 'FT'
        elif row['weekday'] == 5 or is_heiligabend_silvester:  # Samstag oder 24./31.12.
            return 'SA'
        else:  # Montag-Freitag
            return 'WT'
    
    df_result['day_type'] = df_result.apply(get_day_type, axis=1)
    
    # Funktion zum Zuordnen der Lastprofilwerte (optimiert mit merge)
    def map_load_profile(df_result: pd.DataFrame, df_profile: pd.DataFrame, sector_name: str) -> pd.Series:
        """
        Ordnet jedem Zeitpunkt im Ergebnis-DataFrame den passenden Wert aus dem Lastprofil zu.
        Verwendet merge für bessere Performance.
        """
        # Erstelle Hilfsspalten für das Matching
        df_work = df_result.copy()
        df_work['hour'] = df_work['Zeitpunkt'].dt.hour
        df_work['minute'] = df_work['Zeitpunkt'].dt.minute
        
        # Bereite Profil vor
        df_prof = df_profile.copy()
        df_prof['hour'] = df_prof['timestamp'].dt.hour
        df_prof['minute'] = df_prof['timestamp'].dt.minute
        
        # Merge basierend auf month, day_type, hour, minute
        df_merged = df_work.merge(
            df_prof[['month', 'day_type', 'hour', 'minute', 'value_kWh']],
            on=['month', 'day_type', 'hour', 'minute'],
            how='left'
        )
        
        # Prüfe auf fehlende Werte
        missing = df_merged['value_kWh'].isna().sum()
        if missing > 0:
            # print(f"Warnung: {missing} Zeitpunkte ohne Lastprofil-Wert für {sector_name} (werden mit 0 gefüllt)")
            df_merged['value_kWh'].fillna(0.0, inplace=True)
        
        return df_merged['value_kWh']
    
    # print("\nOrdne Lastprofil-Werte zu...")
    df_result['Haushalte_kWh'] = map_load_profile(df_result, lastH, 'Haushalte')
    
    # Dynamisierung für Haushalte (H25)
    # Formel: x = x_0 * (-3,9E-10*t^4 + 3,20E-7*t^3 - 7,02E-5*t^2 + 2,10E-3*t + 1,24)
    # t = Tag des Jahres
    t = df_result['Zeitpunkt'].dt.dayofyear
    
    # Berechnung des Dynamisierungsfaktors
    dyn_faktor = (
        -3.92e-10 * t**4 + 
        3.20e-7 * t**3 - 
        7.02e-5 * t**2 + 
        2.10e-3 * t + 
        1.24
    )
    
    # Rundung des Faktors auf 4 Nachkommastellen (empfohlen)
    dyn_faktor = dyn_faktor.round(4)
    
    # Anwenden auf das Haushaltsprofil
    df_result['Haushalte_kWh'] = df_result['Haushalte_kWh'] * dyn_faktor
    
    # Ergebnis auf 3 Nachkommastellen runden (empfohlen)
    df_result['Haushalte_kWh'] = df_result['Haushalte_kWh'].round(3)
    
    df_result['Gewerbe_kWh'] = map_load_profile(df_result, lastG, 'Gewerbe')
    df_result['Landwirtschaft_kWh'] = map_load_profile(df_result, lastL, 'Landwirtschaft')
    
    # Berechne Skalierungsfaktoren
    # Die Lastprofile geben relative Werte für 1 MWh Jahresverbrauch an
    # Wir müssen sie so skalieren, dass die Jahressumme dem Zielwert entspricht
    
    # print("\nBerechne Skalierungsfaktoren...")
    
    # Summe der Profilwerte (in kWh)
    sum_H_kWh = df_result['Haushalte_kWh'].sum()
    sum_G_kWh = df_result['Gewerbe_kWh'].sum()
    sum_L_kWh = df_result['Landwirtschaft_kWh'].sum()
    
    # Konvertiere Zielwerte von TWh in kWh
    ziel_H_kWh = lastZielH * 1e9  # TWh -> kWh
    ziel_G_kWh = lastZielG * 1e9
    ziel_L_kWh = lastZielL * 1e9
    
    # Berechne Skalierungsfaktoren
    faktor_H = ziel_H_kWh / sum_H_kWh if sum_H_kWh > 0 else 0
    faktor_G = ziel_G_kWh / sum_G_kWh if sum_G_kWh > 0 else 0
    faktor_L = ziel_L_kWh / sum_L_kWh if sum_L_kWh > 0 else 0
    
    # print(f"  Haushalte: Faktor = {faktor_H:.6f} (Ziel: {lastZielH:.2f} TWh)")
    # print(f"  Gewerbe: Faktor = {faktor_G:.6f} (Ziel: {lastZielG:.2f} TWh)")
    # print(f"  Landwirtschaft: Faktor = {faktor_L:.6f} (Ziel: {lastZielL:.2f} TWh)")
    
    # Skaliere und konvertiere zu MWh
    df_result['Haushalte [MWh]'] = df_result['Haushalte_kWh'] * faktor_H / 1000.0
    df_result['Gewerbe [MWh]'] = df_result['Gewerbe_kWh'] * faktor_G / 1000.0
    df_result['Landwirtschaft [MWh]'] = df_result['Landwirtschaft_kWh'] * faktor_L / 1000.0
    
    # Berechne Gesamtverbrauch
    df_result['Gesamt [MWh]'] = (
        df_result['Haushalte [MWh]'] + 
        df_result['Gewerbe [MWh]'] + 
        df_result['Landwirtschaft [MWh]']
    )
    
    # Bereinige DataFrame - entferne Hilfsspalten
    df_result = df_result[[
        'Zeitpunkt',
        'Haushalte [MWh]',
        'Gewerbe [MWh]',
        'Landwirtschaft [MWh]',
        'Gesamt [MWh]'
    ]]
    
    # Validierung der Ergebnisse
    # print("\n" + "="*60)
    # print("VALIDIERUNG DER SIMULATION")
    # print("="*60)
    
    sum_H_TWh = df_result['Haushalte [MWh]'].sum() / 1e6
    sum_G_TWh = df_result['Gewerbe [MWh]'].sum() / 1e6
    sum_L_TWh = df_result['Landwirtschaft [MWh]'].sum() / 1e6
    sum_total_TWh = df_result['Gesamt [MWh]'].sum() / 1e6
    
    # print(f"Haushalte:       {sum_H_TWh:.4f} TWh (Ziel: {lastZielH:.4f} TWh, Abweichung: {abs(sum_H_TWh - lastZielH):.6f} TWh)")
    # print(f"Gewerbe:         {sum_G_TWh:.4f} TWh (Ziel: {lastZielG:.4f} TWh, Abweichung: {abs(sum_G_TWh - lastZielG):.6f} TWh)")
    # print(f"Landwirtschaft:  {sum_L_TWh:.4f} TWh (Ziel: {lastZielL:.4f} TWh, Abweichung: {abs(sum_L_TWh - lastZielL):.6f} TWh)")
    # print(f"GESAMT:          {sum_total_TWh:.4f} TWh (Ziel: {lastZielH + lastZielG + lastZielL:.4f} TWh)")
    # print("="*60)
    
    # col.show_first_rows(df_result)
    
    return df_result
    