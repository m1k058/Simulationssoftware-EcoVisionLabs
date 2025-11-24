"""
Modul zur Integration von standardisierten Lastprofilen in die Verbrauchssimulation.

Das Lastprofil S25 (Speicher- und PV-Kombination) wird verwendet, um realistische
Lastschwankungen über das Jahr zu modellieren, anstatt einen konstanten Skalierungsfaktor
zu verwenden.

Das Profil ist normiert auf 1 Mio kWh Jahresverbrauch und enthält für jeden Monat
und jeden Tagestyp (Werktag, Samstag, Feiertag) die 96 Viertelstundenwerte.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple


def load_standard_load_profile(csv_path: str | Path = "raw-data/Lastprofile 2024 BMWK(S25).csv") -> pd.DataFrame:
    """
    Lädt das standardisierte Lastprofil S25 aus der CSV-Datei.
    
    Format der CSV:
    - Zeile 1-2: Info-Header
    - Zeile 3: Monate (Januar-Dezember, jeweils 3x für SA/FT/WT)
    - Zeile 4: Tagestypen (SA=Samstag, FT=Feiertag, WT=Werktag)
    - Ab Zeile 5: 96 Viertelstunden (00:00-00:15 bis 23:45-24:00)
    
    Args:
        csv_path: Pfad zur Lastprofil-CSV-Datei
        
    Returns:
        DataFrame mit 96 Zeilen (Viertelstunden) und Spalten für jeden Monat/Tagestyp
        
    Raises:
        FileNotFoundError: Wenn die CSV-Datei nicht gefunden wird
        ValueError: Wenn die CSV-Datei nicht das erwartete Format hat
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Lastprofil-Datei nicht gefunden: {csv_path}")
    
    try:
        # Einlesen mit deutschen Dezimaltrennzeichen, überspringe Info-Header
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8', skiprows=3, decimal=',')
        
        # Entferne leere erste Spalte und verwende Zeitfenster als Index
        df = df.iloc[:, 1:]  # Entferne "Unnamed: 0"
        df = df.rename(columns={df.columns[0]: 'Zeitfenster'})
        
        # Entferne Zeilen mit NaN in Zeitfenster
        df = df[df['Zeitfenster'].notna()].copy()
        
        # Extrahiere Start-Zeit aus Zeitfenster (z.B. "00:00-00:15" -> 0)
        df['Viertelstunde_Nr'] = df['Zeitfenster'].apply(
            lambda x: int(x.split('-')[0].split(':')[0]) * 4 + int(x.split('-')[0].split(':')[1]) // 15
        )
        
        # Prüfe ob wir 96 Viertelstunden haben
        if len(df) != 96:
            raise ValueError(f"Erwartet 96 Viertelstunden, gefunden: {len(df)}")
        
        print(f"✓ Lastprofil geladen: {len(df)} Viertelstunden × {len(df.columns)-2} Monat/Tagestyp-Kombinationen")
        
        return df
        
    except Exception as e:
        raise ValueError(f"Fehler beim Laden der Lastprofil-Datei: {e}")


def parse_profile_header(df_profile: pd.DataFrame) -> pd.DataFrame:
    """
    Parsed die Spaltenstruktur des Lastprofils und erstellt Multi-Index.
    
    Die Spalten haben Namen wie: SA, FT, WT, SA.1, FT.1, WT.1, ...
    - SA/FT/WT für Januar
    - SA.1/FT.1/WT.1 für Februar
    - usw.
    
    Args:
        df_profile: Geladenes Lastprofil
        
    Returns:
        DataFrame mit Multi-Index-Spalten (Monat, Tagestyp)
    """
    # Mapping für Tagestypen
    day_type_map = {
        'SA': 'Samstag',
        'FT': 'Feiertag', 
        'WT': 'Werktag'
    }
    
    # Erstelle neue Spaltennamen
    new_columns = []
    col_mapping = {}
    
    for col in df_profile.columns:
        if col in ['Zeitfenster', 'Viertelstunde_Nr']:
            new_columns.append(col)
            col_mapping[col] = col
            continue
            
        # Parse Spaltenname: z.B. "SA" -> (1, Samstag), "FT.1" -> (2, Feiertag)
        parts = col.split('.')
        day_type_code = parts[0]
        
        if day_type_code not in day_type_map:
            print(f"⚠ Warnung: Unbekannter Tagestyp '{day_type_code}' in Spalte '{col}'")
            continue
            
        # Monat ableiten aus Index
        month_idx = 0 if len(parts) == 1 else int(parts[1])
        month = month_idx + 1  # 0->Januar(1), 1->Februar(2), ...
        
        day_type = day_type_map[day_type_code]
        new_col_name = f"{month}_{day_type}"
        new_columns.append(new_col_name)
        col_mapping[col] = new_col_name
    
    # Umbenennen
    df_renamed = df_profile.rename(columns=col_mapping)
    
    return df_renamed


def normalize_load_profile(df_profile: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """
    Normalisiert das Lastprofil, sodass die Summe aller Jahreswerte
    genau 1.0 ergibt (= 100% des Jahresverbrauchs).
    
    Das Original ist normiert auf 1 Mio kWh Jahresverbrauch. Wir müssen
    für jeden Tag im Jahr den entsprechenden Viertelstundenwert aufsummieren
    und dann auf 1.0 normieren.
    
    Args:
        df_profile: DataFrame mit Lastprofil nach parse_profile_header()
        year: Referenzjahr für die Berechnung der tatsächlichen Tage pro Monat/Typ
        
    Returns:
        DataFrame mit normalisierten Werten
    """
    df_norm = df_profile.copy()
    
    # Berechne tatsächliche Anzahl Tage pro Monat und Tagestyp für das gegebene Jahr
    import calendar
    
    days_per_month = {}
    for month in range(1, 13):
        # Anzahl Tage im Monat
        _, num_days = calendar.monthrange(year, month)
        
        # Zähle Tagestypen
        werktage = 0
        samstage = 0
        feiertage = 0  # Sonntage + gesetzliche Feiertage
        
        for day in range(1, num_days + 1):
            weekday = calendar.weekday(year, month, day)  # 0=Mo, ..., 6=So
            if weekday == 5:  # Samstag
                samstage += 1
            elif weekday == 6:  # Sonntag
                feiertage += 1
            else:  # Montag-Freitag
                werktage += 1
        
        # Profil-Definition:
        # SA = Samstag (nur Samstage)
        # FT = Feiertag (Sonntage + gesetzliche Feiertage, hier nur Sonntage)
        # WT = Werktag (Montag-Freitag)
        # Hinweis: Gesetzliche Feiertage (außer Sonntag) werden hier nicht extra gezählt
        days_per_month[month] = {
            'Werktag': werktage,
            'Samstag': samstage,
            'Feiertag': feiertage
        }
    
    # Berechne Jahressumme (gewichtet nach Anzahl Tage)
    jahressumme = 0.0
    
    for month in range(1, 13):
        for day_type in ['Werktag', 'Samstag', 'Feiertag']:
            col_name = f"{month}_{day_type}"
            if col_name in df_norm.columns:
                monatssumme = df_norm[col_name].sum()  # Summe der 96 Viertelstunden
                tage = days_per_month[month][day_type]
                if tage > 0:  # Nur wenn Tage vorhanden
                    jahressumme += monatssumme * tage
    
    print(f"  Jahressumme (Original, für Jahr {year}): {jahressumme:,.2f} kWh")
    
    # Normiere alle Werte, sodass Jahressumme = 1.0
    for col in df_norm.columns:
        if col not in ['Zeitfenster', 'Viertelstunde_Nr']:
            df_norm[col] = df_norm[col] / jahressumme
    
    # Verifiziere Normierung
    jahressumme_norm = 0.0
    for month in range(1, 13):
        for day_type in ['Werktag', 'Samstag', 'Feiertag']:
            col_name = f"{month}_{day_type}"
            if col_name in df_norm.columns:
                monatssumme = df_norm[col_name].sum()
                tage = days_per_month[month][day_type]
                if tage > 0:
                    jahressumme_norm += monatssumme * tage
    
    print(f"  Jahressumme (normiert): {jahressumme_norm:.10f} (sollte ~1.0 sein)")
    
    return df_norm


def map_profile_to_timestamps(df_timestamps: pd.DataFrame, 
                              df_profile_norm: pd.DataFrame,
                              total_consumption_twh: float) -> pd.DataFrame:
    """
    Ordnet jedem Zeitstempel den entsprechenden Lastfaktor aus dem Profil zu
    und berechnet den resultierenden Verbrauchswert.
    
    Args:
        df_timestamps: DataFrame mit Spalte 'Zeitpunkt' (datetime)
        df_profile_norm: Normalisiertes Lastprofil mit Monat_Tagestyp-Spalten
        total_consumption_twh: Ziel-Jahresverbrauch in TWh
        
    Returns:
        DataFrame mit zusätzlicher Spalte 'Lastprofil Netzlast [MWh]'
    """
    df_result = df_timestamps.copy()
    
    # Extrahiere Zeitkomponenten
    df_result['Monat'] = df_result['Zeitpunkt'].dt.month
    df_result['Wochentag'] = df_result['Zeitpunkt'].dt.dayofweek  # 0=Montag, ..., 6=Sonntag
    df_result['Stunde'] = df_result['Zeitpunkt'].dt.hour
    df_result['Minute'] = df_result['Zeitpunkt'].dt.minute
    df_result['Viertelstunde_Nr'] = df_result['Stunde'] * 4 + df_result['Minute'] // 15
    
    # Bestimme Tagestyp basierend auf Wochentag
    # SA = Samstag (nur Samstag)
    # FT = Feiertag (Sonntag + gesetzliche Feiertage)
    # WT = Werktag (Montag-Freitag, außer Feiertage)
    def get_day_type(wochentag):
        if wochentag == 5:  # Samstag
            return 'Samstag'
        elif wochentag == 6:  # Sonntag
            return 'Feiertag'
        else:  # Montag-Freitag
            return 'Werktag'
    
    df_result['Tagestyp'] = df_result['Wochentag'].apply(get_day_type)
    
    # Erstelle Lookup-Spaltenname
    df_result['Profile_Column'] = (
        df_result['Monat'].astype(str) + '_' + df_result['Tagestyp']
    )
    
    # Initialisiere Lastfaktor-Spalte
    df_result['Lastfaktor_normiert'] = np.nan
    
    # Für jeden Zeitstempel: Finde den passenden Wert aus dem Profil
    for idx, row in df_result.iterrows():
        viertelstunde = row['Viertelstunde_Nr']
        profile_col = row['Profile_Column']
        
        if profile_col in df_profile_norm.columns:
            # Finde den Wert für diese Viertelstunde
            lastfaktor = df_profile_norm.loc[
                df_profile_norm['Viertelstunde_Nr'] == viertelstunde,
                profile_col
            ].values[0]
            
            df_result.at[idx, 'Lastfaktor_normiert'] = lastfaktor
        else:
            print(f"⚠ Warnung: Spalte '{profile_col}' nicht im Profil gefunden")
    
    # Prüfe auf fehlende Zuordnungen
    missing_count = df_result['Lastfaktor_normiert'].isna().sum()
    if missing_count > 0:
        print(f"⚠ Warnung: {missing_count} Zeitstempel konnten keinem Lastprofil-Wert zugeordnet werden")
        # Fülle fehlende Werte mit Durchschnitt
        mean_factor = df_result['Lastfaktor_normiert'].mean()
        df_result['Lastfaktor_normiert'].fillna(mean_factor, inplace=True)
    
    # Berechne tatsächlichen Verbrauch in MWh
    # total_consumption_twh * 1.000.000 = MWh für das ganze Jahr
    # Lastfaktor_normiert gibt an, welcher Anteil davon in dieser Viertelstunde verbraucht wird
    total_consumption_mwh = total_consumption_twh * 1_000_000
    df_result['Lastprofil Netzlast [MWh]'] = (
        df_result['Lastfaktor_normiert'] * total_consumption_mwh
    )
    
    # Entferne Hilfsspalten
    df_result.drop(columns=['Monat', 'Wochentag', 'Stunde', 'Minute', 
                            'Viertelstunde_Nr', 'Tagestyp', 'Profile_Column',
                            'Lastfaktor_normiert'], 
                   inplace=True)
    
    print(f"✓ Lastprofil auf {len(df_result)} Zeitstempel angewendet")
    actual_total = df_result['Lastprofil Netzlast [MWh]'].sum() / 1_000_000
    print(f"  Ziel-Verbrauch: {total_consumption_twh:.2f} TWh")
    print(f"  Tatsächlicher Verbrauch: {actual_total:.2f} TWh")
    print(f"  Abweichung: {abs(actual_total - total_consumption_twh) / total_consumption_twh * 100:.2f}%")
    
    return df_result


def apply_load_profile_to_simulation(df_timestamps: pd.DataFrame,
                                    total_consumption_twh: float,
                                    profile_path: str | Path = "raw-data/Lastprofile 2024 BMWK(S25).csv") -> pd.DataFrame:
    """
    Komplette Pipeline: Lädt Lastprofil, normalisiert es und wendet es auf
    die Zeitstempel-Daten an.
    
    Dies ist die Hauptfunktion, die in simulation.py verwendet werden soll.
    
    Args:
        df_timestamps: DataFrame mit Spalte 'Zeitpunkt'
        total_consumption_twh: Ziel-Jahresverbrauch in TWh
        profile_path: Pfad zur Lastprofil-CSV
        
    Returns:
        DataFrame mit zusätzlicher Spalte 'Lastprofil Netzlast [MWh]'
        
    Example:
        >>> df_simu = pd.DataFrame({
        ...     'Zeitpunkt': pd.date_range('2030-01-01', '2030-12-31 23:45', freq='15min')
        ... })
        >>> df_result = apply_load_profile_to_simulation(df_simu, total_consumption_twh=600.0)
        >>> print(df_result[['Zeitpunkt', 'Lastprofil Netzlast [MWh]']].head())
    """
    print(f"\n{'='*60}")
    print(f"Anwendung Lastprofil S25")
    print(f"{'='*60}")
    print(f"Ziel-Jahresverbrauch: {total_consumption_twh:.2f} TWh")
    print(f"Zeitraum: {df_timestamps['Zeitpunkt'].min()} bis {df_timestamps['Zeitpunkt'].max()}")
    print(f"Anzahl Zeitstempel: {len(df_timestamps)}")
    
    # Ermittle das Jahr aus den Zeitstempeln für die Normalisierung
    year = df_timestamps['Zeitpunkt'].dt.year.iloc[0]
    
    # 1. Lade Lastprofil
    print(f"\n1. Lade Lastprofil...")
    df_profile = load_standard_load_profile(profile_path)
    
    # 2. Parse Header
    print(f"\n2. Parse Spaltenstruktur...")
    df_profile_parsed = parse_profile_header(df_profile)
    
    # 3. Normalisiere
    print(f"\n3. Normalisiere auf Jahresverbrauch = 1.0...")
    df_profile_norm = normalize_load_profile(df_profile_parsed, year=year)
    
    # 4. Wende auf Zeitstempel an
    print(f"\n4. Ordne Lastfaktoren zu und berechne Verbrauch...")
    df_result = map_profile_to_timestamps(df_timestamps, df_profile_norm, total_consumption_twh)
    
    print(f"\n{'='*60}")
    print(f"✓ Lastprofil erfolgreich angewendet")
    print(f"{'='*60}\n")
    
    return df_result


if __name__ == "__main__":
    # Test-Code
    print("Test: Lade und normalisiere Lastprofil\n")
    
    df_profile = load_standard_load_profile()
    df_profile_parsed = parse_profile_header(df_profile)
    df_profile_norm = normalize_load_profile(df_profile_parsed)
    
    print(f"\nNormalisiertes Profil:")
    print(f"  Shape: {df_profile_norm.shape}")
    print(f"  Spalten: {list(df_profile_norm.columns[:5])}...")
    print(f"\n  Erste 5 Zeilen (Januar Werktag):")
    if '1_Werktag' in df_profile_norm.columns:
        print(df_profile_norm[['Zeitfenster', '1_Werktag']].head())
    
    # Test mit Beispiel-Zeitstempeln
    print("\n\nTest mit Beispiel-Zeitstempeln (Januar 2030):")
    df_test = pd.DataFrame({
        'Zeitpunkt': pd.date_range('2030-01-01', '2030-01-07 23:45', freq='15min')
    })
    df_test_result = apply_load_profile_to_simulation(df_test, total_consumption_twh=650.0)
    print(f"\nErgebnis:")
    print(f"  Gesamt (7 Tage): {df_test_result['Lastprofil Netzlast [MWh]'].sum() / 1_000:.2f} GWh")
    print(f"  Durchschnitt pro Viertelstunde: {df_test_result['Lastprofil Netzlast [MWh]'].mean():.2f} MWh")
