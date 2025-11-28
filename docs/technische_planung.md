# Technische Planung – EcoVision Labs

> **Projekt:** Analyse der Klimaziele 2030/2045 (Energiewende-Simulator)  
> **Kurs:** REE3 – IPJ1  
> **Team:** EcoVision Labs  
> **Version:** 3.0 (Planung MS4 - Beta)  
> **Datum:** November 2025  
> **Autoren:** Julian Umlauf, Michał Kos  

---

## 1. Modellierungsstrategie (Core Concepts)

Für den Meilenstein 4 wechseln wir von einer pauschalen Skalierung (Top-Down) zu einer detaillierten Sektoren-Simulation (Bottom-Up).

### A. Referenzjahr-Prinzip (Datenkonsistenz)
Um meteorologische Korrelationen (z. B. „Dunkelflaute“ = Kälte + Windstille) korrekt abzubilden, verzichten wir auf Randomisierung.
* **Referenzjahr:** 2023 (als „Wetter-Schablone“).
* **Konsequenz:** Alle Zeitreihen (Wind, Solar, Temperatur, Last) basieren starr auf dem Verlauf dieses Jahres.

### B. Erzeugungs-Logik (Capacity-Based Scaling)
Die Erzeugung wird über die **installierte Leistung (GW)** skaliert, nicht über Energiemengen.
1.  **Input:** Installierte Leistung 2023 (Ist-Stand) & Zeitreihe 2023.
2.  **Normierung:** Berechnung eines „Unit-Profils“ (Einspeisung pro 1 GW installierter Leistung).
3.  **Simulation:** `Erzeugung_Neu(t) = Unit_Profil(t) * Installierte_Leistung_Szenario`.

### C. Verbrauchs-Logik (Superposition)
Der Gesamtverbrauch setzt sich additiv aus den Einzel-Sektoren zusammen:
`Last_Gesamt(t) = Last_Basis(t) + Last_Wärme(t) + Last_EV(t) + Last_H2(t)`

---

## 2. Geplante Features (Module)

### A. Sektor Wärme (Wärmepumpen)
* [ ] **Temperaturabhängiges Lastmodell:** Implementierung einer Funktion, die Heizbedarf aus der Außentemperatur ableitet.
* [ ] **Heizgrenztemperatur:** Logik, ab wann geheizt wird (Standard: 15°C).
* [ ] **COP-Berechnung:** Dynamische Umrechnung von thermischer in elektrische Energie unter Berücksichtigung des COP (Coefficient of Performance) bei aktueller Temperatur.

### B. Sektor Verkehr (E-Mobilität)
* [ ] **Verhaltensbasiertes Lademodell:** Nutzung von Standardlastprofilen (SLP) für Haushalte.
* [ ] **Hochrechnung:** `Last_EV(t) = Anzahl_Autos * Verbrauch_pro_Auto * Profil(t)`.
* [ ] **Saisonalität:** Berücksichtigung des Mehrverbrauchs im Winter (Heizung/Batteriechemie).

### C. Sektor Industrie & Wasserstoff (P2X)
* [ ] **Elektrolyseur-Simulation:** Berechnung der Stromnachfrage für H2-Produktion.
* [ ] **Option 1 (Start):** Bandlast (Konstante Abnahme für Industrieprozesse).
* [ ] **Option 2 (Erweiterung):** Flexible Last (Betrieb nur bei niedrigen Strompreisen/hoher EE-Einspeisung).

### D. Core Engine
* [ ] **Superposition:** Aggregation aller Teil-Lastkurven zur neuen Gesamtlast.
* [ ] **Residuallast-Berechnung:** `Erzeugung_Neu - Last_Gesamt_Neu`.
* [ ] **Speicher-Logik:** Füllstandsberechnung basierend auf Residuallast und Kapazitäts-Constraints.

---

## 3. Datenanforderungen & Quellen

Um die Modelle zu füttern, müssen folgende Datensätze beschafft und auf das Referenzjahr (2023) normiert werden:

| Datensatz | Beschreibung & Anforderungen | Quelle | Status |
| :--- | :--- | :--- | :--- |
| **Strommarktdaten** | Erzeugung/Verbrauch 2023 (15-min Auflösung). | SMARD | ✅ Da |
| **Wetterdaten** | Zeitreihen der Außentemperatur ($T_{amb}$) für DE 2023. Format: 15-Minuten-Auflösung. | DWD (Open Data) / ERA5 | 🔄 Offen |
| **Installierte Leistung** | GW-Zahlen für Wind/PV (Status Quo 2023) zur Normierung. | BNetzA / BMWK | 🔄 Offen |
| **SLP E-Mobilität** | Typisches Ladeprofil für private Haushalte (Verteilung über 24h). | BDEW / Netzbetreiber | 🔄 Offen |
| **WP-Kennlinien** | Normierte Lastprofile (h-Profile) oder COP-Tabellen (Effizienz vs. Temperatur). | BDEW / Hersteller | 🔄 Offen |

---

## 4. Parameter & Annahmen (Definitionen)

Diese Parameter müssen im Team definiert oder über die GUI konfigurierbar gemacht werden.

### Szenario-Parameter (GUI Slider)
* **Erzeugung:** Installierte Leistung Wind Onshore / Offshore / PV in [GW].
* **Wärme:** Anzahl Wärmepumpen im Zieljahr (z. B. 6 Mio.).
* **Verkehr:** Anzahl E-Autos im Zieljahr (z. B. 15 Mio.).
* **P2X:** Installierte Elektrolyseur-Leistung in [GW].

### Technische Parameter (Konstanten/Config)
* **COP-Werte:** Durchschnittliche Effizienz bei verschiedenen Temperaturen (z.B. -5°C vs. +10°C).
* **EV-Verbrauch:** Durchschnittsverbrauch in kWh/100km (inkl. Ladeverluste).
* **Heizgrenztemperatur:** 15°C (Standard).

### Modellierungs-Entscheidungen
* **Elektrolyseur-Fahrweise:** Vorerst "Baseload" (läuft durch), da einfacher zu implementieren als marktgetriebene Flexibilität.
* **Lade-Strategie:** "Ungesteuertes Laden" (Worst-Case Szenario, Abend-Spitze), um Netzstress zu simulieren.

---

## 5. Roadmap / Action Items

1.  **Daten-Infrastruktur:**
    * [ ] Wetterdaten (Temperatur 2023) laden und auf 15-min interpolieren.
    * [ ] "Unit-Profile" für Wind und PV erstellen (Profil / Installierte Leistung 2023).
2.  **Architektur:**
    * [ ] `SimulationEngine`-Klasse erweitern, um Sub-Module (`HeatModule`, `TransportModule`) aufzunehmen.
3.  **Prototyping (Logik):**
    * [ ] Funktion schreiben: *Temperatur* -> *Heizbedarf*.
    * [ ] Funktion schreiben: *Residuallast* -> *Speicher Füllstand*.
4.  **UI-Ausbau:**
    * [ ] Ersetzen der Skalierungs-Faktoren durch **GW-Slider**.
    * [ ] Implementierung des **Kostenmoduls** (CAPEX/OPEX Anzeige).
