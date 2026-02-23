# Scoring-System – Dokumentation

**Datei:** `source-code/data_processing/scoring_system.py`  
**Konfiguration (UI-Anzeige):** `source-code/plotting/scoring_plots.py` → `KPI_CONFIG`

---

## Gesamtstruktur

Der Gesamtscore eines Szenarios berechnet sich aus drei Kategorien:

$$\text{Gesamtscore} = 0{,}40 \times \text{Safety} + 0{,}30 \times \text{Ecology} + 0{,}30 \times \text{Economy}$$

Jede Kategorie hat einen Composite-Score (Durchschnitt bzw. gewichtete Summe ihrer KPIs), der auf **[0, 1]** normiert ist. Für die Darstellung in der UI werden alle Scores mit 100 multipliziert (0–100 Punkte).

---

## Annahmen / Simulationskontext

Das Scoring bewertet den Zustand **vor Netzverbund und Reservekraftwerken**. Erdgas wird in der Simulation als **historisches Erzeugungs­profil** (skaliert auf installierte Kapazität) behandelt, nicht als dispatchable Backup. Verbleibende Defizite nach EE + Speicher entsprechen dem Bedarf an Stromimporten oder Reservekraftwerken.

---

## Kategorie 1: Safety (Gewicht: 40 %)

**Composite:** Gleichgewichteter Durchschnitt der drei Sub-Scores (je 1/3).

### 1.1 Adequacy Score — Gewicht: 1/3 (= 13,3 % Gesamt)

**Frage:** In wie vielen Jahresstunden kann das System die Nachfrage ohne Import/Reserve decken?

$$\text{Adequacy} = 1 - \frac{\text{Defizit-Stunden}}{\text{Gesamtstunden der Simulation}}$$

| Eingangsgröße | Quelle | Beschreibung |
|---|---|---|
| Defizit-Stunden | `Bilanz_nach_Flex` → `Rest Bilanz [MWh]` | Anzahl 15-min-Intervalle mit negativer Restbilanz × 0,25 h |
| Gesamtstunden | `len(Verbrauch) × 0,25` | Vollständige Simulationsperiode (i.d.R. 8.760 h/Jahr) |

- Score = **1,0** → kein einziges Defizit
- Score = **0,0** → jede Stunde Defizit
- S0 Referenz 2025 ≈ **0,19** (81 % der Stunden brauchen Import/Reserve)

---

### 1.2 Robustness Score — Gewicht: 1/3 (= 13,3 % Gesamt)

**Frage:** Reicht die verfügbare Leistung zum Zeitpunkt der Jahreslastspitze?

$$\text{cap\_ratio} = \frac{P_{\text{Erzeugung@Spitze}} + P_{\text{Speicher-Entladung@Spitze}}}{P_{\text{Spitzenlast}}}$$

| cap_ratio | Score |
|---|---|
| ≥ 1,10 (≥ 110 %) | 1,0 |
| 1,00–1,10 | linear 0,75 → 1,0 |
| < 1,00 | linear 0,0 → 0,75 |

| Eingangsgröße | Quelle |
|---|---|
| Erzeugung zum Spitzenlastzeitpunkt | `Bilanz_nach_Flex` → `Produktion [MWh]` am Index-Maximum von `Gesamt [MWh]` |
| Speicher-Entladung zum Spitzenlastzeitpunkt | `Speicher` → Summe aller `*Entladene MWh`-Spalten am gleichen Index |
| Spitzenlast | `Verbrauch` → `max(Gesamt [MWh]) × 4` (MWh/15min → MW) |

---

### 1.3 Dependency Score — Gewicht: 1/3 (= 13,3 % Gesamt)

**Frage:** Wie groß ist der Anteil nicht gedeckter Energie am Gesamtverbrauch?

$$\text{Dependency} = 1 - \frac{\text{Nicht gedeckte Energie [MWh]}}{\text{Gesamtverbrauch [MWh]}}$$

| Eingangsgröße | Quelle |
|---|---|
| Nicht gedeckte Energie | `Bilanz_nach_Flex` → Summe aller negativen `Rest Bilanz [MWh]`-Werte (Absolutwert) |
| Gesamtverbrauch | `Verbrauch` → Summe `Gesamt [MWh]` |

- Score = **1,0** → vollständig autark (kein Defizit)
- Score = **0,0** → gesamter Verbrauch ungedeckt

---

## Kategorie 2: Ecology (Gewicht: 30 %)

**Composite:** Gewichtete Summe der drei Sub-Scores.

$$\text{Ecology} = 0{,}60 \times \text{CO2} + 0{,}25 \times \text{Renewable} + 0{,}15 \times \text{Curtailment}$$

### 2.1 CO2 Score — Gewicht: 60 % (= 18,0 % Gesamt)

**Frage:** Wie hoch ist die CO₂-Intensität der Stromerzeugung?

$$\text{CO2-Score} = 1 - \min\!\left(1,\; \frac{\text{CO2-Intensität [g/kWh]}}{400}\right)$$

**CO2-Intensität:**

$$\text{CO2 [g/kWh]} = \frac{\text{Erdgas [MWh]} \times 490 + \text{Biomasse [MWh]} \times 50 + \text{Wasserkraft [MWh]} \times 5}{\text{Gesamterzeugung [MWh]}}$$

| Eingangsgröße | Quelle | CO₂-Faktor |
|---|---|---|
| Erdgas-Erzeugung | `Erzeugung` → `Erdgas [MWh]` | 490 gCO₂/kWh |
| Biomasse-Erzeugung | `Erzeugung` → `Biomasse [MWh]` | 50 gCO₂/kWh |
| Wasserkraft-Erzeugung | `Erzeugung` → `Wasserkraft [MWh]` | 5 gCO₂/kWh |
| Gesamterzeugung | `Bilanz_nach_Flex` → `Produktion [MWh]` | — |

- Referenzpunkt Score = 0: **400 g/kWh** (typischer fossiler Mix ohne EE)
- Score = **1,0** bei 0 g/kWh (vollständig CO₂-frei)

---

### 2.2 Renewable Share — Gewicht: 25 % (= 7,5 % Gesamt)

**Frage:** Welcher Anteil der Erzeugung ist fossil-frei?

$$\text{Renewable Share} = \frac{\text{Gesamterzeugung} - \text{Erdgas-Erzeugung}}{\text{Gesamterzeugung}}$$

> „Fossil" = nur Erdgas. Wind, PV, Biomasse, Wasserkraft gelten als fossil-frei.

| Eingangsgröße | Quelle |
|---|---|
| Gesamterzeugung | `Bilanz_nach_Flex` → `Produktion [MWh]` |
| Erdgas-Erzeugung | `Erzeugung` → `Erdgas [MWh]` |

---

### 2.3 Curtailment Score — Gewicht: 15 % (= 4,5 % Gesamt)

**Frage:** Wie viel EE-Erzeugung wird abgeregelt?

$$\text{Abregelungs-Quote} = \frac{\text{Abregelung [MWh]}}{\text{EE-Erzeugung [MWh]}} \quad \text{(begrenzt auf 40 \%)}$$

$$\text{Curtailment-Score} = 1 - \frac{\text{Abregelungs-Quote}}{0{,}40}$$

| Eingangsgröße | Quelle | Beschreibung |
|---|---|---|
| Abregelung | `Bilanz_nach_Flex` → positive `Rest Bilanz [MWh]`-Werte (Summe) | Überschuss NACH allen Speichern = nicht nutzbare Energie |
| EE-Erzeugung | `Erzeugung` → Summe Wind Onshore + Wind Offshore + Photovoltaik | Variable Erzeugung |

- Score = **0,0** ab ≥ 40 % Abregelung
- Score = **1,0** bei 0 % Abregelung

---

## Kategorie 3: Economy (Gewicht: 30 %)

**Composite:** Gewichtete Summe der drei Sub-Scores.

$$\text{Economy} = 0{,}40 \times \text{LCOE} + 0{,}35 \times \text{Curtailment-Econ} + 0{,}25 \times \text{Storage-Efficiency}$$

### 3.1 LCOE Index — Gewicht: 40 % (= 12,0 % Gesamt)

**Frage:** Wie hoch sind die Systemkosten pro erzeugter kWh?

$$\text{LCOE-Index} = 1 - \frac{\text{LCOE [ct/kWh]} - 8}{40 - 8}$$

| Grenzwert | Bedeutung |
|---|---|
| 8 ct/kWh (Best) | Score = 1,0 |
| 40 ct/kWh (Worst) | Score = 0,0 |
| Nicht berechenbar | Score = 0,5 (neutral) |

**LCOE-Berechnung** (`economic_calculator.py`):
- Annualisierte CAPEX (nach Annuitätenfaktor, WACC = 5 %) + fixe OPEX + variable OPEX (inkl. Brennstoffkosten)
- Bezogen auf alle installierten Technologien im Vergleich zur Baseline 2025
- System-LCOE = Gesamtjahreskosten / Gesamtverbrauch (kWh)

Quelle LCOE: `Wirtschaftlichkeit` → `system_lco_e`

---

### 3.2 Curtailment Econ Score — Gewicht: 35 % (= 10,5 % Gesamt)

**Frage:** Wie viel investiertes EE-Kapital wird durch Abregelung wirtschaftlich verschwendet?

$$\text{Abregelungs-Anteil} = \frac{\text{Abregelung [MWh]}}{\text{Gesamterzeugung [MWh]}} \quad \text{(begrenzt auf 35 \%)}$$

$$\text{Curtailment-Econ-Score} = 1 - \frac{\text{Abregelungs-Anteil}}{0{,}35}$$

| Eingangsgröße | Quelle |
|---|---|
| Abregelung | `Bilanz_nach_Flex` → positive `Rest Bilanz [MWh]` (Summe) |
| Gesamterzeugung | `Bilanz_nach_Flex` → `Produktion [MWh]` |

> **Unterschied zu 2.3:** Ecology-Curtailment normiert auf EE-Erzeugung (ökologische Perspektive). Economy-Curtailment normiert auf Gesamterzeugung mit härterem Schwellenwert (35 % statt 40 %) — wirtschaftliche Perspektive.

---

### 3.3 Storage Efficiency — Gewicht: 25 % (= 7,5 % Gesamt)

**Frage:** Wie effizient wird der verfügbare Speicher genutzt?

$$\text{Storage-Efficiency} = \min\!\left(1,\; \frac{\text{Nützlicher Speicherdurchsatz [MWh]}}{\text{Speicherbedarf [MWh]}}\right)$$

| Eingangsgröße | Berechnung |
|---|---|
| Nützlicher Speicherdurchsatz | `min(Σ Geladene MWh, Σ Entladene MWh)` über Batterie + Pumpspeicher + H2 |
| Speicherbedarf | `min(Überschuss-Energie, Defizit-Energie)` aus `Bilanz_vor_Flex` |

Das `min()` beim Speicherbedarf verhindert Überbewertung bei stark asymmetrischen Bilanzen.

---

## Datenquellen im Überblick

| DataFrame-Key | Inhalt | Primäre Verwendung |
|---|---|---|
| `Verbrauch` | Gesamt-Verbrauch pro 15-min-Slot | Safety: Spitzenlast, Gesamtverbrauch |
| `Erzeugung` | Erzeugung pro Technologie | Ecology: CO₂, EE-Anteil |
| `Speicher` | SOC, Geladene/Entladene MWh je Speichertyp | Safety: Robustness; Economy: Storage-Efficiency |
| `Bilanz_vor_Flex` | Bilanz vor E-Mobility V2G + Speicher | Economy: Speicherbedarf |
| `Bilanz_nach_Flex` | Restbilanz nach allen Flexibilitäten | Safety: Defizit; Ecology + Economy: Curtailment |
| `Wirtschaftlichkeit` | CAPEX/OPEX/LCOE-Ergebnisse | Economy: LCOE-Index |

---

## Gewichtungsübersicht (vollständig)

| Kategorie | Kat.-Gewicht | KPI | Intra-Gewicht | Anteil Gesamt |
|---|---|---|---|---|
| Safety | 40 % | Adequacy Score | 1/3 | **13,3 %** |
| Safety | 40 % | Robustness Score | 1/3 | **13,3 %** |
| Safety | 40 % | Dependency Score | 1/3 | **13,3 %** |
| Ecology | 30 % | CO2 Score | 60 % | **18,0 %** |
| Ecology | 30 % | Renewable Share | 25 % | **7,5 %** |
| Ecology | 30 % | Curtailment Score | 15 % | **4,5 %** |
| Economy | 30 % | LCOE Index | 40 % | **12,0 %** |
| Economy | 30 % | Curtailment Econ Score | 35 % | **10,5 %** |
| Economy | 30 % | Storage Efficiency | 25 % | **7,5 %** |
| | | | **Σ** | **100 %** |
