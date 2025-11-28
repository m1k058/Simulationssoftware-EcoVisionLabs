# Technische Planung – EcoVision Labs

> **Projekt:** Analyse der Klimaziele 2030/2045 (Energiewende-Simulator)  
> **Kurs:** REE3 – IPJ1  
> **Team:** EcoVision Labs  
> **Version:** 0.2.3 (Fokus Daten & Roadmap MS4)  
> **Datum:** November 2025  
> **Autoren:** Julian Umlauf, Michał Kos  

---

## 1. Datenstrategie & Modellierungsansatz

Wir wechseln von einer pauschalen Energieskalierung (Top-Down) zu einer kapazitätsbasierten Simulation (Bottom-Up).

### A. Referenzjahr-Prinzip
Um meteorologische Korrelationen (z. B. „Dunkelflaute“ = Kälte + Windstille) korrekt abzubilden, verzichten wir auf Randomisierung.
* **Referenzjahr:** 2023 (als „Wetter-Schablone“).
* **Konsequenz:** Alle Zeitreihen (Wind, Solar, Temperatur, Last) basieren auf dem Verlauf dieses Jahres.

### B. Erzeugung: Kapazitäts-Ansatz (Capacity-Based Scaling)
Die Erzeugung wird nicht über Energiemengen, sondern über die **installierte Leistung (GW)** skaliert.
1.  **Input:** Installierte Leistung 2023 (Ist-Stand) & Zeitreihe 2023.
2.  **Normierung:** Berechnung eines „Unit-Profils“ (Einspeisung pro 1 GW installierter Leistung).
3.  **Simulation:** `Erzeugung_Neu(t) = Unit_Profil(t) * Installierte_Leistung_Szenario`.

### C. Verbrauch: Sektorenkopplung
Der Verbrauch setzt sich additiv zusammen (Superposition):
1.  **Basislast:** Klassischer Stromverbrauch (skaliert anhand Effizienztrends).
2.  **Wärme:** Basierend auf **Außentemperatur** (DWD-Daten) und COP-Kennlinien.
3.  **Verkehr:** Basierend auf **Standardlastprofilen** für E-Mobilität (BDEW) und Fahrzeuganzahl.

---

## 2. Benötigte Datenquellen (To-Do)

| Datensatz | Beschreibung | Quelle | Status |
| :--- | :--- | :--- | :--- |
| **Strommarktdaten** | Erzeugung/Verbrauch 2023 (15-min Auflösung) | SMARD | ✅ Vorhanden |
| **Installierte Leistung** | GW-Zahlen für Wind/PV (Status Quo 2023) | BNetzA / BMWK | 🔄 Offen |
| **Wetterdaten** | Zeitreihe Außentemperatur DE 2023 | DWD (Open Data) | 🔄 Offen |
| **Lastprofile** | Normierte Profile für E-Mobilität & Wärmepumpen | BDEW / Netzbetreiber | 🔄 Offen |

---

## 3. Roadmap bis MS4 (Beta)

1.  **Daten-Infrastruktur:**
    * Integration der Wetterdaten (Temperatur) in das Pandas-DataFrame.
    * Erstellung der „Unit-Profile“ für Wind und PV.
2.  **Erweiterung der Simulation:**
    * Implementierung der Speicher-Logik (Füllstandsberechnung mit Constraints).
    * Kostenmodul (Berechnung CAPEX/OPEX basierend auf den GW-Slidern).
3.  **UI-Ausbau:**
    * Ersetzen der abstrakten Faktoren-Slider durch **GW-Slider** (z. B. "Wind Onshore: 115 GW").
    * Hinzufügen von Preset-Buttons (z. B. "Lade Szenario BMWK 2030").
