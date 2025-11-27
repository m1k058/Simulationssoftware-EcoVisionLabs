# Roadmap MS4: Bottom-Up Simulation & Flexibilisierung

Diese Planung beschreibt den Übergang von der pauschalen Skalierung (Top-Down) hin zur detaillierten Modellierung einzelner Sektoren (Bottom-Up) für eine präzise Lastprognose.

## 1. Geplante Features (Module)

Das Ziel ist der Aufbau einer **Superpositions-Logik**:
`Last_Gesamt(t) = Last_Basis(t) + Last_Wärme(t) + Last_EV(t) + Last_H2(t)`

### A. Sektor Wärme (Wärmepumpen)
- [ ] Implementierung eines temperaturabhängigen Lastmodells.
- [ ] Berechnung der Heizleistung basierend auf Außentemperatur und Heizgrenztemperatur.
- [ ] Umrechnung in elektrische Last unter Berücksichtigung des COP (Coefficient of Performance).

### B. Sektor Verkehr (E-Mobilität)
- [ ] Implementierung eines verhaltensbasierten Lademodells.
- [ ] Hochrechnung basierend auf Fahrzeuganzahl und typischen Ladeprofilen (Standardlastprofil).
- [ ] Berücksichtigung von Saisonalität (Mehrverbrauch im Winter).

### C. Sektor Industrie & Wasserstoff (P2X)
- [ ] Implementierung einer Elektrolyseur-Simulation.
- [ ] Option 1: Bandlast (Konstante Abnahme für Industrieprozesse).
- [ ] Option 2: Flexible Last (Betrieb nur bei niedrigen Strompreisen/hoher EE-Einspeisung).

### D. Core Engine
- [ ] **Superposition:** Aggregation aller Teil-Lastkurven zur neuen Gesamtlast.
- [ ] **Residuallast-Berechnung:** `Erzeugung_Neu - Last_Gesamt_Neu`.

---

## 2. Zusätzlich benötigte Daten

Um diese Modelle zu füttern, reichen die reinen SMARD-Stromdaten nicht mehr aus. Folgende Datensätze müssen beschafft/integriert werden:

### Wetterdaten (Dringend notwendig!)
- **Was:** Zeitreihen der Außentemperatur ($T_{amb}$) für Deutschland (oder repräsentative Regionen).
- **Format:** 15-Minuten-Auflösung (passend zu SMARD).
- **Quelle:** Deutscher Wetterdienst (DWD) CDC Open Data oder ERA5 Reanalysis Daten.

### Standardlastprofile (SLP) & Referenzkurven
- **E-Mobilität:** Typisches Ladeprofil für private Haushalte (Verteilung der Ladevorgänge über 24h).
    - *Quelle:* BDEW Studien oder Netzbetreiber-Daten.
- **Wärmepumpen:** Normierte Lastprofile (h-Profile) oder COP-Kennlinien (Effizienz vs. Temperatur).

### Technische Parameter
- **COP-Werte:** Durchschnittliche Effizienz von Luft-Wasser-Wärmepumpen bei verschiedenen Temperaturen (z.B. COP bei -5°C vs. +10°C).
- **EV-Verbrauch:** Durchschnittsverbrauch in kWh/100km (inkl. Ladeverluste).

---

## 3. Entscheidungen & Annahmen (Zu definieren)

Bevor programmiert wird, müssen im Team (oder über die GUI konfigurierbar) folgende Parameter festgelegt werden:

### Szenario-Parameter (Die "Slider" in der GUI)
- **Anzahl Wärmepumpen:** Wie viele Millionen Geräte sollen im Zieljahr installiert sein? (z.B. 6 Mio. bis 2030).
- **Anzahl E-Autos:** Zielwert für die Flotte (z.B. 15 Mio.).
- **Installierte Elektrolyseur-Leistung:** Wie viel GW H2-Kapazität nehmen wir an?

### Modellierungs-Strategie
- **Heizgrenztemperatur:** Ab welcher Außentemperatur springen die Wärmepumpen an? (Standard: 15°C).
- **Elektrolyseur-Fahrweise:**
    - *Entscheidung:* Simulieren wir "Stupid Baseload" (läuft immer durch) oder "Smart Grid" (läuft nur bei Windüberschuss)?
    - *Empfehlung für Start:* Baseload, da einfacher zu implementieren.
- **Verteilnetz-Logik:** Nehmen wir an, dass E-Autos netzdienlich laden (Glättung der Spitzen) oder ungesteuert (alle stecken um 18:00 Uhr ein)?
    - *Empfehlung:* Ungesteuertes Standardprofil (Worst-Case) simulieren.

---

## 4. Nächste Schritte (Action Items)

1. [ ] **Research:** Wetterdaten (Temperatur 2023) als CSV herunterladen und bereinigen (auf 15-min interpolieren/resamplen).
2. [ ] **Architektur:** `SimulationEngine`-Klasse erweitern, um Sub-Module (`HeatModule`, `TransportModule`) aufzunehmen.
3. [ ] **Prototyping:** Erste Funktion schreiben, die *Temperatur* -> *Heizbedarf* umrechnet.
