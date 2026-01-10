import pandas as pd
import numpy as np
import data_processing.generation_profile as genPro
import locale
from typing import List, Optional, Dict, Any
from data_processing.load_profile import apply_load_profile_to_simulation
from config_manager import ConfigManager
from data_processing.economic_calculator import EconomicCalculator
from data_processing.simulation_logger import SimulationLogger


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
    DEPRECATED: Diese Funktion implementiert die alte "Top-Down" Logik.
    Bitte stattdessen `simulate_consumption_BDEW` (Bottom-Up mit BDEW-Profilen) verwenden.

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
    Gesamtenergie_RefJahr = df_refJahr["Netzlast [MWh]"].sum() / 1000000  # in TWh

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
    
    # Debug: df_simu.head()  # Deaktiviert
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
        return df_refJahr[mwh_col].sum() / 1_000_000.0

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
    print(f"Sonstige Erneuerung [MWh]: Ref={ref_soe:.4f} TWh, Prog={prog_sonstige:.4f} TWh, Faktor={faktor_soe:.6f}")

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

    # Debug: df_simu.head()  # Deaktiviert
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
    if 'Rest Bilanz [MWh]' not in df.columns:
        balance_series = df['Bilanz [MWh]']
    else:
        balance_series = df['Rest Bilanz [MWh]']

    
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
    
    # print(f"\n{'='*80}")
    # print(f"Simuliere {type_name}:")
    # print(f"{'='*80}")
    # print(f"Kapazität: {capacity_mwh:,.0f} MWh")
    # print(f"Min SOC: {min_soc_mwh:,.0f} MWh ({min_soc_mwh/capacity_mwh*100:.1f}%)")
    # print(f"Max SOC: {max_soc_mwh:,.0f} MWh ({max_soc_mwh/capacity_mwh*100:.1f}%)")
    # print(f"Initial SOC: {initial_soc_mwh:,.0f} MWh ({initial_soc_mwh/capacity_mwh*100:.1f}%)")
    # print(f"Max Ladeleistung: {max_charge_mw:,.0f} MW")
    # print(f"Max Entladeleistung: {max_discharge_mw:,.0f} MW")
    # print(f"Wirkungsgrade: Laden {charge_efficiency*100:.1f}%, Entladen {discharge_efficiency*100:.1f}%")
    
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
    
    if 'Rest Bilanz [MWh]' not in df.columns:
        # Baue Ergebnis-DataFrame für das erste Mal
        result = pd.DataFrame({
            'Zeitpunkt': df_balance['Zeitpunkt'],
            f'{type_name} SOC MWh': soc,
            f'{type_name} Geladene MWh': charged,
            f'{type_name} Entladene MWh': discharged,
            # Restbilanz berechnen:
            # Ursprüngliche Balance - Geladen + Entladen
            f'Rest Bilanz [MWh]': balance_series - charged + discharged
        })
    else:
        # Nimm alle bestehenden Spalten aus df und füge die neuen Speicherwerte hinzu
        result = df.copy()
        # Füge die drei neuen Batterie-Spalten hinzu
        result[f'{type_name} SOC MWh'] = soc
        result[f'{type_name} Geladene MWh'] = charged
        result[f'{type_name} Entladene MWh'] = discharged
        # Überschreibe Rest Bilanz mit neu berechneter Bilanz
        result['Rest Bilanz [MWh]'] = balance_series - charged + discharged
    
    # print(f"\nErgebnisse:")
    # print(f"Geladene Energie: {charged.sum():,.0f} MWh")
    # print(f"Entladene Energie: {discharged.sum():,.0f} MWh")
    # print(f"Finaler SOC: {soc[-1]:,.0f} MWh ({soc[-1]/capacity_mwh*100:.1f}%)")
    # print(f"Max SOC erreicht: {soc.max():,.0f} MWh ({soc.max()/capacity_mwh*100:.1f}%)")
    # print(f"Min SOC erreicht: {soc.min():,.0f} MWh ({soc.min()/capacity_mwh*100:.1f}%)")
    # print(f"{'='*80}\n")
    
    return result


def simulate_battery_storage(
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
    """
    Simuliert einen Batteriespeicher mit typischen Parametern.
    Args:
        df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
        capacity_mwh: Speicherkapazität in MWh
        max_charge_mw: Maximale Ladeleistung in MW
        max_discharge_mw: Maximale Entladeleistung in MW
        initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
    Returns:
        DataFrame mit Simulationsergebnissen
    """
    # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
    initial_soc_absolute = initial_soc_mwh * capacity_mwh
    
    return simulate_storage_generic(
        df_balance,
        type_name="Batteriespeicher",
        capacity_mwh=capacity_mwh,
        max_charge_mw=max_charge_mw,
        max_discharge_mw=max_discharge_mw,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        initial_soc_mwh=initial_soc_absolute,
        min_soc_mwh=0.05*capacity_mwh,
        max_soc_mwh=0.95*capacity_mwh
    )


def simulate_pump_storage(
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
    """
    Simuliert einen Pumpspeicher mit typischen Parametern.
    Args:
        df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
        capacity_mwh: Speicherkapazität in MWh
        max_charge_mw: Maximale Ladeleistung in MW
        max_discharge_mw: Maximale Entladeleistung in MW
        initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
    Returns:
        DataFrame mit Simulationsergebnissen
    """
    # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
    initial_soc_absolute = initial_soc_mwh * capacity_mwh
    
    return simulate_storage_generic(
        df_balance,
        type_name="Pumpspeicher",
        capacity_mwh=capacity_mwh,
        max_charge_mw=max_charge_mw,
        max_discharge_mw=max_discharge_mw,
        charge_efficiency=0.88,
        discharge_efficiency=0.88,
        initial_soc_mwh=initial_soc_absolute,
        min_soc_mwh=0.0,
        max_soc_mwh=capacity_mwh
    )


def simulate_hydrogen_storage(
        df_balance: pd.DataFrame,
        capacity_mwh: float,
        max_charge_mw: float,
        max_discharge_mw: float,
        initial_soc_mwh: float = 0.0,
    ) -> pd.DataFrame:
    """
    Simuliert einen Wasserstoffspeicher mit typischen Parametern.
    Args:
        df_balance: DataFrame mit Spalten 'Zeitpunkt', 'Gesamterzeugung [MWh]', 'Skalierte Netzlast [MWh]'
        capacity_mwh: Speicherkapazität in MWh
        max_charge_mw: Maximale Ladeleistung in MW
        max_discharge_mw: Maximale Entladeleistung in MW
        initial_soc_mwh: Initialer Ladestand als Anteil der Kapazität (0.0-1.0, z.B. 0.5 = 50%)
    Returns:
        DataFrame mit Simulationsergebnissen
    """ 
    # Konvertiere initial_soc von Anteil (0-1) zu absoluten MWh
    initial_soc_absolute = initial_soc_mwh * capacity_mwh

    return simulate_storage_generic(
        df_balance,
        type_name="Wasserstoffspeicher",
        capacity_mwh=capacity_mwh,
        max_charge_mw=max_charge_mw,
        max_discharge_mw=max_discharge_mw,
        charge_efficiency=0.67,
        discharge_efficiency=0.58,
        initial_soc_mwh=initial_soc_absolute,
        min_soc_mwh=0.0,
        max_soc_mwh=capacity_mwh
    )


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
    
    # Erstelle Ziel-Zeitindex für das Simulationsjahr
    start_date = pd.Timestamp(year=simu_jahr, month=1, day=1)
    end_date = pd.Timestamp(year=simu_jahr, month=12, day=31, hour=23, minute=45)
    target_time_index = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Funktion zum Anpassen der Profile auf Zieljahr-Länge
    def align_profile_to_target_year(df_profile, target_index):
        """Passt ein Profil an die Länge des Zieljahres an (kürzt oder wiederholt)."""
        profile_len = len(df_profile)
        target_len = len(target_index)
        
        if profile_len == target_len:
            return df_profile
        elif profile_len > target_len:
            # Schaltjahr-Profil auf Normaljahr kürzen
            return df_profile.iloc[:target_len].copy()
        else:
            # Normaljahr-Profil auf Schaltjahr erweitern (letzten Tag wiederholen)
            # Wiederhole die letzten 96 Viertelstunden (24h)
            repeat_data = df_profile.iloc[-96:].copy()
            df_extended = pd.concat([df_profile, repeat_data], ignore_index=True)
            return df_extended.iloc[:target_len].copy()
    
    # Profile auf Zieljahr-Länge anpassen
    df_windOn_Profile = align_profile_to_target_year(df_windOn_Profile, target_time_index)
    df_windOff_Profile = align_profile_to_target_year(df_windOff_Profile, target_time_index)
    df_pv_Profile = align_profile_to_target_year(df_pv_Profile, target_time_index)
    df_other_Profile = align_profile_to_target_year(df_other_Profile, target_time_index)
    
    # Simuliere Produktion für alle Technologien

    # Konvertiere target_year zu String für Dictionary-Zugriff
    target_year_str = str(simu_jahr)
    target_year_int = int(simu_jahr)
    
    # Initialisiere Ergebnis-DataFrame mit Zeitpunkt-Spalte aus Ziel-Index
    df_result = pd.DataFrame()
    df_result['Zeitpunkt'] = target_time_index
    
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


def simulate_consumption_BDEW(
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
        # BDEW-Definition: Es gelten die bundeseinheitlichen Feiertage.
        # holidays.Germany() ohne Provinz liefert genau diese 9 Feiertage:
        # Neujahr, Karfreitag, Ostermontag, Tag der Arbeit, Christi Himmelfahrt,
        # Pfingstmontag, Tag der Deutschen Einheit, 1. & 2. Weihnachtstag.
        de_holidays = holidays.Germany(years=simu_jahr, language='de')
        feiertage = [pd.Timestamp(date) for date in de_holidays.keys()]
    except ImportError:
        # Fallback: Feste Feiertage (vereinfacht)
        # Warnung: Bewegliche Feiertage fehlen hier!
        print("Warnung: Package 'holidays' nicht verfügbar. Bewegliche Feiertage fehlen!")
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
    
    # Dynamisierung für Haushalte (H25) - AKTIVIERT
    # Formel: x = x_0 * (-3,92E-10*t^4 + 3,20E-7*t^3 - 7,02E-5*t^2 + 2,10E-3*t + 1,24)
    # t = Tag des Jahres
    # WICHTIG: t muss als float behandelt werden, da t^4 bei int32 überlaufen kann (ab Tag 216)
    t = df_result['Zeitpunkt'].dt.dayofyear.astype(float)
    
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


def simulate_consumption_heatpump(
    weather_df: pd.DataFrame,
    hp_profile_matrix: pd.DataFrame,
    n_heatpumps: int,
    Q_th_a: float,
    COP_avg: float,
    dt: float,
    simu_jahr: int,
    debug: bool = False
) -> pd.DataFrame:
    """
    Simuliert den Energieverbrauch für Wärmepumpen basierend auf vorgegebenen Lastprofil und Parametern.
    
    Args:
        weather_df (pd.DataFrame): Lastprofil für Wärmepumpen
        hp_profile_matrix (pd.DataFrame): Matrix mit Lastprofilen für verschiedene Wetterlagen
        n_heatpumps (int): Anzahl der Wärmepumpen
        Q_th_a (float): Jahreswärmebedarf pro Wärmepumpe [kWh]
        COP_avg (float): Durchschnittlicher COP der Wärmepumpen
        dt (float): Zeitintervall in Stunden (z.B. 0.25 für 15 Minuten)
        simu_jahr (int): Simulationsjahr (z.B. 2030 oder 2045)
        
    Returns:
        pd.DataFrame: DataFrame mit Spalten:
            - Zeitpunkt: DateTime-Index mit Viertelstunden-Auflösung
            - Wärmepumpen [MWh]: Verbrauch Wärmepumpen
    """
    # Stelle sicher, dass alle Spaltennamen Strings sind (für konsistenten Matrix-Zugriff)
    hp_profile_matrix.columns = hp_profile_matrix.columns.astype(str)

    # Vorbereiten der HP-Lastprofilmatrix: Zeitspalten parsen, Kommas als Dezimalpunkte wandeln
    hp_profile_matrix = hp_profile_matrix.copy()
    if 'Zeitpunkt' in hp_profile_matrix.columns:
        time_str = hp_profile_matrix['Zeitpunkt'].astype(str).str.split('-', n=1).str[0]
        parsed_time = pd.to_datetime(time_str, format='%H:%M', errors='coerce')
        hp_profile_matrix['hour'] = parsed_time.dt.hour
        hp_profile_matrix['minute'] = parsed_time.dt.minute
    else:
        hp_profile_matrix['hour'] = hp_profile_matrix.index
        hp_profile_matrix['minute'] = 0

    value_cols = [c for c in hp_profile_matrix.columns if c not in {'Zeitpunkt', 'hour', 'minute'}]
    for c in value_cols:
        hp_profile_matrix[c] = pd.to_numeric(
            hp_profile_matrix[c].astype(str).str.replace(',', '.'),
            errors='coerce'
        )
    
    # HILFSFUNKTIONEN
    def prep_temp_df(df: pd.DataFrame, location: str = "AVERAGE") -> pd.DataFrame:
        """
        Bereitet das Wetter-DataFrame vor:
        - Konvertiert Zeitpunkt von 'DD.MM.YY HH:MM' zu DateTime
        - Wählt die angegebene Spalte aus (location)
        - Interopliert zu Viertelstunden (aktuell nur stündliche Werte)
        """
        df_local = df.copy()
        
        # Konvertiere Zeitpunkt-Format "01.01.19 01:00" zu DateTime
        df_local['Zeitpunkt'] = pd.to_datetime(df_local['Zeitpunkt'], format='%d.%m.%y %H:%M')
        
        # Wähle nur AVERAGE Spalte
        if location not in df_local.columns:
            raise ValueError(f"Spalte '{location}' nicht gefunden im Weather-DataFrame")
        
        df_local = df_local[['Zeitpunkt', location]].copy()
        df_local.columns = ['Zeitpunkt', 'Temperatur [°C]']
        
        # Sortiere nach Zeitpunkt
        df_local = df_local.sort_values('Zeitpunkt').reset_index(drop=True)
        
        return df_local

    def get_hp_faktor(time_index: pd.Timestamp, temp: float) -> float:
        """
        Gibt den Lastprofilfaktor für eine bestimmte Temperatur und Uhrzeit zurück.
        
        Args:
            time_index: DateTime Objekt mit Uhrzeit (0-23)
            temp: Außentemperatur in °C
            
        Returns:
            Lastprofilfaktor (dimensionslos, 0-1 oder höher) aus der Matrix
            
        Raises:
            KeyError: Wenn Spalte nicht in Matrix gefunden
        """
        # Temperatur Clamping: -14 bis 17 oder String 'LOW'/'HIGH'
        t_lookup = int(round(temp))
        if t_lookup < -14:
            t_lookup = 'LOW'
        elif t_lookup >= 18:
            t_lookup = 'HIGH'
        
        
        t_col = str(t_lookup) if isinstance(t_lookup, int) else t_lookup
        
        # Zeile anhand Stunde und Minute finden (Matrix hat 96 Zeilen/Tag)
        row = hp_profile_matrix[(hp_profile_matrix['hour'] == time_index.hour) & (hp_profile_matrix['minute'] == time_index.minute)]
        if row.empty:
            raise KeyError(
                f"Matrix-Zeile nicht gefunden für Stunde={time_index.hour}, Minute={time_index.minute}"
            )
        if t_col not in row.columns:
            raise KeyError(
                f"Temperaturspalte '{t_col}' nicht in Matrix gefunden. Verfügbare: {value_cols[:5]}"
            )
        factor = row.iloc[0][t_col]
        return float(factor)

    # Bereite Wetterdaten vor: Konvertiere, bereinige und interpoliere auf Viertelstunden-Auflösung
    df_weather = prep_temp_df(weather_df, location="AVERAGE")
    df_weather = df_weather.drop_duplicates(subset='Zeitpunkt', keep='first')
    df_weather = df_weather.sort_values('Zeitpunkt').reset_index(drop=True)
    
    # Erstelle vollständigen 15-Minuten-Zeitindex für das Wetterjahr
    # (Alternative zu resample, vermeidet Probleme mit Zeitumstellung/Duplikaten)
    weather_year = int(df_weather['Zeitpunkt'].dt.year.iloc[0])
    start = pd.Timestamp(f'{weather_year}-01-01 00:00')
    end = pd.Timestamp(f'{weather_year}-12-31 23:45')
    full_index = pd.date_range(start=start, end=end, freq='15min')
    df_full = pd.DataFrame({'Zeitpunkt': full_index})
    
    # Merge und interpoliere Temperaturdaten (forward-fill + backward-fill für Lücken am Anfang/Ende)
    df_weather = df_full.merge(df_weather, on='Zeitpunkt', how='left')
    df_weather['Temperatur [°C]'] = df_weather['Temperatur [°C]'].ffill().bfill()
    
    # Verschiebe Jahr auf Simulationsjahr für Merge mit BDEW-Daten
    df_weather['Zeitpunkt'] = df_weather['Zeitpunkt'].apply(lambda x: x.replace(year=simu_jahr))
    
    # Berechne Normierungsfaktor für Lastprofile
    summe_lp_dt = 0.0
    for index, row in df_weather.iterrows():
        time = row['Zeitpunkt']
        temp = row['Temperatur [°C]']
        lp_faktor = get_hp_faktor(time, temp)
        summe_lp_dt += lp_faktor * dt

    # VALIDIERUNG
    if summe_lp_dt <= 0:
        raise ValueError(f"Fehler: Normierungssumme summe_lp_dt={summe_lp_dt} ist nicht positiv!")
    
    # Skalierungsfaktor: Jahreslast / Summe aller Profile
    f = Q_th_a / summe_lp_dt
    if debug:
        print(f"Normierungsfaktor f: {f:.2f} kW (Q_th_a={Q_th_a} kWh, summe={summe_lp_dt:.1f} h-äquiv)")
    
    # Berechne Leistungen und Energieverbrauch für jede Viertelstunde
    ergebnisse = []
    
    for index, row in df_weather.iterrows():
        time = row['Zeitpunkt']
        temp = row['Temperatur [°C]']
        
        # A. Profilwert holen (dimensionslos, 0-1 oder höher)
        lp_wert = get_hp_faktor(time, temp)
        
        # B. Thermische Leistung EINER WP (kW)
        p_th = lp_wert * f
        
        # C. Elektrische Leistung EINER WP (kW)
        p_el = p_th / COP_avg
        
        # D. Gesamtleistung ALLER n WP (kW)
        p_el_ges = p_el * n_heatpumps
        
        # Speichern (für Debug/Validierung)
        ergebnisse.append({
            "Zeitpunkt": time,
            "Temperatur [°C]": temp,
            "P_th [kW]": p_th,
            "P_el [kW]": p_el,
            "P_el_ges [kW]": p_el_ges,
            "P_el_ges [MW]": p_el_ges / 1000  # Umrechnung zu MW
        })
    
    # Konvertiere zu DataFrame
    df_result = pd.DataFrame(ergebnisse)
    
    # --- SCHRITT 5: KONVERTIERUNG ZU ENERGIEERZEUGUNG (MWh) ---
    df_result['Wärmepumpen [MWh]'] = df_result['P_el_ges [MW]'] * dt
    
    # Rückgabe nur mit Zeitpunkt und Verbrauch
    df_result = df_result[['Zeitpunkt', 'Wärmepumpen [MWh]']]
    
    # VALIDIERUNG
    if debug:
        jahres_verbrauch_mwh = df_result['Wärmepumpen [MWh]'].sum()
        jahres_verbrauch_twh = jahres_verbrauch_mwh / 1e6
        target_twh = (Q_th_a * n_heatpumps) / (COP_avg * 1e6)
        print(f"Jahres-Stromverbrauch: {jahres_verbrauch_twh:.4f} TWh")
    
    return df_result


def simulate_consumption_emobility(
    lastEMobility: pd.DataFrame,
    zielEMobility: float,
    simu_jahr: int
) -> pd.DataFrame:
    """
    Simuliert den Energieverbrauch für Elektromobilität basierend auf vorgegebenen Lastprofilen.
    
    Args:
        lastEMobility (pd.DataFrame): Lastprofil für E-Autos
        zielEMobility (float): Ziel-Jahresverbrauch E-Mobilität [TWh]
        simu_jahr (int): Simulationsjahr (z.B. 2030 oder 2045)
        
    Returns:
        pd.DataFrame: DataFrame mit Spalten:
            - Zeitpunkt: DateTime-Index mit Viertelstunden-Auflösung
            - E-Mobilität [MWh]: Verbrauch E-Autos
    """
    pass


def simulate_consumption_all(
    lastH: pd.DataFrame,
    lastG: pd.DataFrame,
    lastL: pd.DataFrame,
    wetter_df: pd.DataFrame,
    hp_profile_matrix: pd.DataFrame,
    lastZielH: float,
    lastZielG: float,
    lastZielL: float,
    anzahl_heatpumps: int,
    Q_th_a: float,
    COP_avg: float,
    dt: float,
    simu_jahr: int,
    debug: bool = False
) -> pd.DataFrame:
    """
    Simuliert den gesamten Energieverbrauch (BDEW + Wärmepumpen + E-Mobilität) für ein Jahr.
    
    Diese Funktion führt alle drei Verbrauchssimulationen aus und kombiniert sie in einem
    einzelnen DataFrame. Die Gesammtwerte werden erst am Ende berechnet.
    
    Args:
        lastH (pd.DataFrame): BDEW H25-Lastprofil (Haushalte)
        lastG (pd.DataFrame): BDEW G25-Lastprofil (Gewerbe)
        lastL (pd.DataFrame): BDEW L25-Lastprofil (Landwirtschaft)
        wetter_df (pd.DataFrame): Wetterdaten für Wärmepumpen
        hp_profile_matrix (pd.DataFrame): Matrix mit Lastprofilen für Wärmepump
        lastZielH (float): Ziel-Jahresverbrauch Haushalte [TWh]
        lastZielG (float): Ziel-Jahresverbrauch Gewerbe [TWh]
        lastZielL (float): Ziel-Jahresverbrauch Landwirtschaft [TWh]
        anzahl_heatpumps (int): Anzahl der Wärmepumpen
        Q_th_a (float): Jahreswärmebedarf pro Wärmepumpe [kWh]
        COP_avg (float): Durchschnittlicher COP der Wärmepumpen
        dt (float): Zeitintervall in Stunden (z.B. 0.25 für 15 Minuten)
        simu_jahr (int): Simulationsjahr (z.B. 2030 oder 2045)
        debug (bool): Debug-Informationen ausgeben
        
    Returns:
        pd.DataFrame: DataFrame mit Spalten:
            - Zeitpunkt: DateTime-Index mit Viertelstunden-Auflösung
            - Haushalte [MWh]: Verbrauch Haushalte (BDEW)
            - Gewerbe [MWh]: Verbrauch Gewerbe (BDEW)
            - Landwirtschaft [MWh]: Verbrauch Landwirtschaft (BDEW)
            - Wärmepumpen [MWh]: Verbrauch Wärmepumpen
            - E-Mobilität [MWh]: Verbrauch E-Autos
            - Gesamt [MWh]: Summe aller Sektoren (berechnet am Ende)
    """
    # 1. Simuliere BDEW-Verbrauch (Haushalte, Gewerbe, Landwirtschaft)
    df_bdew = simulate_consumption_BDEW(
        lastH, lastG, lastL,
        lastZielH, lastZielG, lastZielL,
        simu_jahr
    )
    
    # 2. Simuliere Wärmepumpen-Verbrauch (optional, nur wenn Daten vorhanden)
    df_result = df_bdew.copy()
    
    if wetter_df is not None and hp_profile_matrix is not None and anzahl_heatpumps > 0:
        try:
            df_heatpump = simulate_consumption_heatpump(
                wetter_df,
                hp_profile_matrix,
                anzahl_heatpumps,
                Q_th_a,
                COP_avg,
                dt,
                simu_jahr,
                debug=debug
            )
            # Merge mit BDEW-Daten (outer-merge, damit keine Zeitpunkte verloren gehen)
            df_result = df_result.merge(df_heatpump, on='Zeitpunkt', how='outer')
            df_result['Wärmepumpen [MWh]'] = df_result['Wärmepumpen [MWh]'].fillna(0.0)
        except Exception as e:
            if debug:
                print(f"Warnung: Wärmepumpen-Simulation fehlgeschlagen: {e}")
            df_result['Wärmepumpen [MWh]'] = 0.0
    else:
        # Falls keine Wärmepumpen konfiguriert, Spalte mit Nullen anlegen
        df_result['Wärmepumpen [MWh]'] = 0.0
    
    # 3. Simuliere E-Mobilität-Verbrauch (TODO: Noch nicht implementiert)
    # Wenn E-Mobilität implementiert wird, analog zu Wärmepumpen hinzufügen:
    # df_result = df_result.merge(df_emobility, on='Zeitpunkt', how='outer')
    # df_result['E-Mobilität [MWh]'] = df_result['E-Mobilität [MWh]'].fillna(0.0)
    
    # 4. Berechne Gesamtverbrauch: Summe aller Sektoren
    mwh_cols = [col for col in df_result.columns if '[MWh]' in col and col != 'Gesamt [MWh]']
    if mwh_cols:
        df_result['Gesamt [MWh]'] = df_result[mwh_cols].sum(axis=1)
    
    return df_result




def _align_to_quarter_hour(df: pd.DataFrame, simu_jahr: int, label: str) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Bringt ein DataFrame auf das vollstaendige 15-Minuten-Raster des Simulationsjahres."""

    if "Zeitpunkt" not in df.columns:
        raise KeyError(f"{label}: Spalte 'Zeitpunkt' fehlt.")

    df_local = df.copy()
    df_local["Zeitpunkt"] = pd.to_datetime(df_local["Zeitpunkt"])
    df_local = df_local.sort_values("Zeitpunkt").drop_duplicates(subset="Zeitpunkt", keep="last")

    start = pd.Timestamp(f"{simu_jahr}-01-01 00:00:00")
    end = pd.Timestamp(f"{simu_jahr}-12-31 23:45:00")
    target_index = pd.date_range(start=start, end=end, freq="15min")

    aligned = df_local.set_index("Zeitpunkt").reindex(target_index)
    if aligned.isnull().any().any():
        missing = aligned.isnull().all(axis=1).sum()
        raise ValueError(f"{label}: {missing} Viertelstunden fehlen im Jahr {simu_jahr}; Eingabedaten sind lueckenhaft.")

    return aligned, target_index


def calc_balance(simProd: pd.DataFrame, simCons: pd.DataFrame, simu_jahr: int) -> pd.DataFrame:
    """Berechnet die Bilanz (Erzeugung - Verbrauch) je 15-Minuten-Zeitschritt des Simulationsjahres."""

    prod_aligned, target_index = _align_to_quarter_hour(simProd, simu_jahr, "Produktion")
    cons_aligned, _ = _align_to_quarter_hour(simCons, simu_jahr, "Verbrauch")

    # Summiere nur relevante Spalten, nicht die Gesamt-Spalte (sonst Doppelzählung!)
    # Wenn "Gesamt [MWh]" vorhanden ist, verwende nur diese, ansonsten summiere alle MWh-Spalten
    if "Gesamt [MWh]" in cons_aligned.columns:
        cons_sum = cons_aligned["Gesamt [MWh]"]
    else:
        cons_sum = cons_aligned.select_dtypes(include=[np.number]).sum(axis=1)
    
    # Für Produktion: Summiere alle MWh-Spalten (es gibt dort keine Gesamt-Spalte)
    prod_sum = prod_aligned.select_dtypes(include=[np.number]).sum(axis=1)
    
    bilance = prod_sum - cons_sum

    df_bilance = pd.DataFrame({
        "Zeitpunkt": target_index,
        "Produktion [MWh]": prod_sum.values,
        "Verbrauch [MWh]": cons_sum.values,
        "Bilanz [MWh]": bilance.values
    })

    return df_bilance


def economical_calculation(
    sm,
    dm,
    sim_results: Dict[str, pd.DataFrame],
    year: int,
    smard_installed: pd.DataFrame
) -> Dict[str, Any]:
    """
    Berechnet die wirtschaftlichen Kennzahlen (CAPEX, OPEX, LCOE) basierend auf echten Simulationsergebnissen.

    Args:
        sm: ScenarioManager mit geladenen Szenario-Daten
        dm: DataManager
        sim_results: Dictionary mit Simulationsergebnissen {"consumption", "production", "balance", "storage"}
        year: Das Simulationsjahr (z.B. 2030 oder 2045)
        smard_installed: DataFrame mit historischen installierten Leistungen (für Baseline 2025)

    Returns:
        dict: Ein Dictionary mit den wirtschaftlichen KPIs:
            - "year": Das Simulationsjahr
            - "total_investment_bn": Gesamter Investitionsbedarf für den Zubau (Mrd. €)
            - "total_annual_cost_bn": Jährliche Gesamtkosten des Systems (Mrd. €/Jahr)
            - "system_lco_e": Durchschnittliche Stromgestehungskosten (ct/kWh)
    """
    try:
        # Mapping: Szenario Tech-IDs zu DataFrame Spalten
        tech_mapping = {
            'Photovoltaik': 'Photovoltaik [MWh]',
            'Wind_Onshore': 'Wind Onshore [MWh]',
            'Wind_Offshore': 'Wind Offshore [MWh]',
            'Biomasse': 'Biomasse [MWh]',
            'Wasserkraft': 'Wasserkraft [MWh]',
            'Erdgas': 'Erdgas [MWh]',
            'Steinkohle': 'Steinkohle [MWh]',
            'Braunkohle': 'Braunkohle [MWh]',
            'Kernenergie': 'Kernenergie [MWh]'
        }
        
        # Mapping: SMARD Spalten zu Szenario Tech-IDs
        smard_tech_mapping = {
            'Photovoltaik [MW]': 'Photovoltaik',
            'Wind Onshore [MW]': 'Wind_Onshore',
            'Wind Offshore [MW]': 'Wind_Offshore',
            'Biomasse [MW]': 'Biomasse',
            'Wasserkraft [MW]': 'Wasserkraft',
            'Erdgas [MW]': 'Erdgas',
            'Steinkohle [MW]': 'Steinkohle',
            'Braunkohle [MW]': 'Braunkohle',
            'Kernenergie [MW]': 'Kernenergie'
        }
        
        # Hole die Erzeugungskapazitäten aus dem Szenario für das Zieljahr
        capacities_target_raw = sm.get_generation_capacities(year=year)
        storage_targets = {
            "battery_storage": sm.get_storage_capacities("battery_storage", year) or {},
            "pumped_hydro_storage": sm.get_storage_capacities("pumped_hydro_storage", year) or {},
            "h2_storage": sm.get_storage_capacities("h2_storage", year) or {},
        }
        
        # Entferne nested dict Layer (falls vorhanden)
        capacities_target = {}
        for tech_id, val in capacities_target_raw.items():
            if isinstance(val, dict):
                # Nested dict: nimm den Wert für das target year
                capacities_target[tech_id] = val.get(year, 0)
            else:
                # Direkter Wert
                capacities_target[tech_id] = val

        # Storage Targets: nutze Leistungsangaben (max_charge_power_mw) als Invest-Basis
        storage_flat = {}
        for s_id, s_val in storage_targets.items():
            if isinstance(s_val, dict):
                cap_mw = s_val.get("max_charge_power_mw") or s_val.get("max_discharge_power_mw") or 0.0
                storage_flat[s_id] = cap_mw
        
        # Hole die Baseline-Kapazitäten aus SMARD 2025
        capacities_base = {}
        if not smard_installed.empty:
            smard_2025 = smard_installed[smard_installed['Zeitpunkt'].dt.year == 2025]
            if not smard_2025.empty:
                # Konvertiere SMARD Spalten zu Tech-IDs
                for smard_col, tech_id in smard_tech_mapping.items():
                    if smard_col in smard_2025.columns:
                        val = pd.to_numeric(smard_2025[smard_col], errors='coerce').max()
                        if pd.notna(val) and val > 0:
                            capacities_base[tech_id] = float(val)
        
        # Fallback: Verwende 70% der Zielkapazität
        for tech_id, capacity_mw in capacities_target.items():
            if isinstance(capacity_mw, (int, float)) and capacity_mw > 0:
                if tech_id not in capacities_base:
                    capacities_base[tech_id] = capacity_mw * 0.7
        
        # Strukturiere die Eingangsdaten für EconomicCalculator (Erzeuger + Speicher)
        inputs = {}
        for tech_id in capacities_target.keys():
            if isinstance(capacities_target[tech_id], (int, float)) and capacities_target[tech_id] > 0:
                inputs[tech_id] = {
                    2025: capacities_base.get(tech_id, capacities_target[tech_id] * 0.7),
                    year: capacities_target[tech_id]
                }

        # Speicher (Basis 0, Ziel aus storage_flat)
        storage_inputs = {}
        for s_id, cap_mw in storage_flat.items():
            if isinstance(cap_mw, (int, float)) and cap_mw > 0:
                storage_inputs[s_id] = {
                    2025: 0.0,
                    year: cap_mw
                }

        if storage_inputs:
            inputs["storage"] = storage_inputs
        
        # Strukturiere Simulationsergebnisse aus echten Simulationen
        df_prod = sim_results.get("production", pd.DataFrame())
        df_cons = sim_results.get("consumption", pd.DataFrame())
        
        # Extrahiere Generierungsdaten pro Technologie (MWh pro Jahr)
        # Muss mit den DataFrame Spalten gemappt werden
        generation_by_tech = {}
        for tech_id, df_col in tech_mapping.items():
            if df_col in df_prod.columns:
                try:
                    gen_mwh = pd.to_numeric(df_prod[df_col], errors='coerce').sum()
                    if pd.notna(gen_mwh) and gen_mwh > 0:
                        generation_by_tech[tech_id] = float(gen_mwh)
                except Exception:
                    pass
        
        # Extrahiere Gesamtverbrauch (MWh pro Jahr)
        total_consumption_mwh = 0.0
        if "Gesamt [MWh]" in df_cons.columns:
            total_consumption_mwh = float(pd.to_numeric(df_cons["Gesamt [MWh]"], errors='coerce').sum())
        
        # Strukturiere für EconomicCalculator
        simulation_results = {
            "generation": {
                year: generation_by_tech
            },
            "total_consumption": {
                year: total_consumption_mwh
            }
        }
        
        # Führe die Berechnung durch
        # Speicher werden bereits in inputs["storage"] übergeben
        calc = EconomicCalculator(inputs, simulation_results, target_storage_capacities=storage_inputs)
        result = calc.perform_calculation(year)
        
        return result
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "year": float(year),
            "total_investment_bn": 0.0,
            "total_annual_cost_bn": 0.0,
            "system_lco_e": 0.0,
            "error": str(e)
        }





# =============================================================================
# Kombi-Funktion: führt alle Standard-Simulationen in einem Schritt aus
# =============================================================================
def kobi(
    cfg: ConfigManager,
    dm,
    sm,
    years: List[int] | None = None,
    verbose: bool = False
) -> dict:
    """
    Führt die vollständige Standard-Simulation mit einem Klick aus und liefert
    alle Zwischenergebnisse für jedes Jahr zurück.

    Pipeline pro Jahr:
    1) Verbrauchssimulation (BDEW H/G/L basierend auf Ziel-TWh aus Szenario)
    2) Erzeugungssimulation (SMARD-Profile skaliert mit Ziel-MW-Kapazitäten)
    3) Bilanz (Produktion minus Verbrauch)
    4) Speichersimulation (Batterie -> Pumpspeicher -> H2)
    5) Wirtschaftlichkeitsanalyse

    Args:
        cfg: `ConfigManager` Instanz
        dm:  `DataManager` Instanz (liefert benötigte Roh-Datenframes über Namen)
        sm:  `ScenarioManager` Instanz (liefert Szenario-Parameter)
        years: Liste der zu simulierenden Jahre. Wenn None, dann aus Szenario entnommen.
        verbose: Wenn True, zeige detaillierte Informationen

    Returns:
        dict: {jahr: {"consumption": df, "production": df, "balance": df, "storage": df, "economics": dict}}
    """
    
    # Initialisiere Logger
    logger = SimulationLogger(verbose=verbose)
    logger.start_step("Simulation wird vorbereitet", "Laden von Konfiguration und Daten")

    # Jahre bestimmen
    if years is None:
        years = sm.scenario_data.get("metadata", {}).get("valid_for_years", [])
        if not years:
            logger.finish_step(False, "Keine gültigen Jahre im Szenario gefunden")
            raise ValueError("Keine gültigen Jahre im Szenario gefunden und keine years übergeben.")

    logger.finish_step(True, f"{len(years)} Jahre identifiziert: {years}")

    # Verbrauchsprofile laden (Haushalt/Gewerbe/Landwirtschaft)
    logger.start_step("Verbrauchsprofile werden geladen")
    try:
        load_cfg = sm.scenario_data.get("target_load_demand_twh", {})
        last_H_name = load_cfg["Haushalt_Basis"]["load_profile"]
        last_G_name = load_cfg["Gewerbe_Basis"]["load_profile"]
        last_L_name = load_cfg["Landwirtschaft_Basis"]["load_profile"]
        
        last_H = dm.get(last_H_name)
        last_G = dm.get(last_G_name)
        last_L = dm.get(last_L_name)
        logger.finish_step(True, "H/G/L-Profile erfolgreich geladen")
    except Exception as e:
        logger.finish_step(False, str(e))
        raise KeyError(f"Fehlende Load-Profile in Szenario: {e}")

    # SMARD-Daten (Erzeugung/Kapazitäten) laden und zusammenführen
    logger.start_step("SMARD-Erzeugungsdaten werden geladen")
    try:
        smard_generation = pd.concat([
            dm.get("SMARD_2015-2019_Erzeugung"),
            dm.get("SMARD_2020-2025_Erzeugung"),
        ])
        smard_installed = pd.concat([
            dm.get("SMARD_Installierte Leistung 2015-2019"),
            dm.get("SMARD_Installierte Leistung 2020-2025"),
        ])
        logger.finish_step(True)
    except Exception as e:
        logger.finish_step(False, str(e))
        raise

    # Ziel-Kapazitäten (MW) und Wetterprofile aus Szenario
    capacity_dict = sm.get_generation_capacities()
    weather_profiles = sm.scenario_data.get("weather_generation_profiles", {})

    results: dict = {}

    for year in years:
        year_num = len(results) + 1
        total_years = len(years)
        
        # 1) Verbrauch
        logger.start_step(f"[{year_num}/{total_years}] Verbrauchssimulation {year}")
        try:
            targets = load_cfg

            # Bereite Wärmepumpen-Parameter vor (falls verfügbar)
            hp_params = {}
            # Hole Jahres-HP-Konfiguration aus ScenarioManager, falls verfügbar
            if hasattr(sm, "get_heat_pump_parameters"):
                hp_config = sm.get_heat_pump_parameters(year) or {}
            else:
                hp_config = sm.scenario_data.get("target_heat_pump_parameters", {}).get(year, {})

            if hp_config:
                # Versuche per-Jahres Datensätze zu laden
                wetter_df_year = None
                hp_profile_matrix_year = None
                # Wetterdaten
                try:
                    wd_name = hp_config.get("weather_data")
                    if wd_name:
                        wetter_df_year = dm.get(wd_name)
                except Exception:
                    wetter_df_year = None
                # Lastprofil-Matrix: Nutze feste Konstante aus constants.py
                try:
                    from constants import HEATPUMP_LOAD_PROFILE_NAME
                    hp_profile_matrix_year = dm.get(HEATPUMP_LOAD_PROFILE_NAME)
                except Exception:
                    hp_profile_matrix_year = None

                # Nur setzen, wenn Daten vorhanden sind; sonst None, dann wird HP übersprungen
                hp_params["wetter_df"] = wetter_df_year
                hp_params["hp_profile_matrix"] = hp_profile_matrix_year
                hp_params["n_heatpumps"] = hp_config.get("installed_units", 0)
                hp_params["Q_th_a"] = hp_config.get("annual_heat_demand_kwh", 51000)  # [kWh/WP/Jahr]
                hp_params["COP_avg"] = hp_config.get("cop_avg", 3.4)
                hp_params["dt"] = 0.25  # Viertelstunden
            
            # Rufe simulieren_consumption_all() auf
            df_cons = simulate_consumption_all(
                lastH=last_H,
                lastG=last_G,
                lastL=last_L,
                wetter_df=hp_params.get("wetter_df"),
                hp_profile_matrix=hp_params.get("hp_profile_matrix"),
                lastZielH=targets["Haushalt_Basis"][year],
                lastZielG=targets["Gewerbe_Basis"][year],
                lastZielL=targets["Landwirtschaft_Basis"][year],
                anzahl_heatpumps=hp_params.get("n_heatpumps", 0),
                Q_th_a=hp_params.get("Q_th_a", 0.0),
                COP_avg=hp_params.get("COP_avg", 3.4),
                dt=hp_params.get("dt", 0.25),
                simu_jahr=year,
                debug=verbose,
            )
            cons_mwh = df_cons['Gesamt [MWh]'].sum() if 'Gesamt [MWh]' in df_cons.columns else 0
            logger.finish_step(True, f"{cons_mwh/1e6:.1f} TWh")
        except Exception as e:
            logger.finish_step(False, str(e))
            raise RuntimeError(f"Verbrauchssimulation {year} fehlgeschlagen: {e}")

        # 2) Erzeugung
        logger.start_step(f"[{year_num}/{total_years}] Erzeugungssimulation {year}")
        try:
            wprof = weather_profiles.get(year, {})
            df_prod = simulate_production(
                cfg,
                smard_generation,
                smard_installed,
                capacity_dict,
                wprof.get("Wind_Onshore", "average"),
                wprof.get("Wind_Offshore", "average"),
                wprof.get("Photovoltaik", "average"),
                year,
            )
            prod_mwh = df_prod[df_prod.columns[1:]].sum().sum() if len(df_prod.columns) > 1 else 0
            logger.finish_step(True, f"{prod_mwh/1e6:.1f} TWh")
        except Exception as e:
            logger.finish_step(False, str(e))
            raise RuntimeError(f"Erzeugungssimulation {year} fehlgeschlagen: {e}")

        # 3) Bilanz
        logger.start_step(f"[{year_num}/{total_years}] Bilanzberechnung {year}")
        try:
            df_bal = calc_balance(df_prod, df_cons, year)
            logger.finish_step(True)
        except Exception as e:
            logger.finish_step(False, str(e))
            raise RuntimeError(f"Bilanzberechnung {year} fehlgeschlagen: {e}")

        # 4) Speicher
        logger.start_step(f"[{year_num}/{total_years}] Speichersimulation {year}")
        try:
            stor_bat = sm.get_storage_capacities("battery_storage", year) or {}
            stor_pump = sm.get_storage_capacities("pumped_hydro_storage", year) or {}
            stor_h2 = sm.get_storage_capacities("h2_storage", year) or {}

            res_bat = simulate_battery_storage(
                df_bal,
                stor_bat.get("installed_capacity_mwh", 0.0),
                stor_bat.get("max_charge_power_mw", 0.0),
                stor_bat.get("max_discharge_power_mw", 0.0),
                stor_bat.get("initial_soc", 0.0),
            )

            res_pump = simulate_pump_storage(
                res_bat,
                stor_pump.get("installed_capacity_mwh", 0.0),
                stor_pump.get("max_charge_power_mw", 0.0),
                stor_pump.get("max_discharge_power_mw", 0.0),
                stor_pump.get("initial_soc", 0.0),
            )

            res_h2 = simulate_hydrogen_storage(
                res_pump,
                stor_h2.get("installed_capacity_mwh", 0.0),
                stor_h2.get("max_charge_power_mw", 0.0),
                stor_h2.get("max_discharge_power_mw", 0.0),
                stor_h2.get("initial_soc", 0.0),
            )
            logger.finish_step(True)
        except Exception as e:
            logger.finish_step(False, str(e))
            raise RuntimeError(f"Speichersimulation {year} fehlgeschlagen: {e}")

        # 5) Wirtschaftlichkeit
        logger.start_step(f"[{year_num}/{total_years}] Wirtschaftlichkeitsanalyse {year}")
        try:
            econ_result = economical_calculation(sm, dm, {
                "production": df_prod,
                "consumption": df_cons,
                "balance": df_bal,
                "storage": res_h2
            }, year, smard_installed)
            logger.finish_step(True, f"LCOE: {econ_result.get('system_lco_e', 0):.2f} ct/kWh")
        except Exception as e:
            logger.finish_step(False, str(e))
            raise RuntimeError(f"Wirtschaftlichkeitsanalyse {year} fehlgeschlagen: {e}")

        results[year] = {
            "consumption": df_cons,
            "production": df_prod,
            "balance": df_bal,
            "storage": res_h2,
            "economics": econ_result,
        }

    # Abschließende Zusammenfassung
    logger.print_summary()
    return results
