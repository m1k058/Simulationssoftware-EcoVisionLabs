# Technische Planung – EcoVision Labs

> **Projekt:** Erreichbarkeit der Klimaziele 2030/2045  
> **Kurs:** REE3 – IPJ1  
> **Team:** EcoVision Labs  
> **Version:** 1.0 (MS1)  
> **Datum:** Oktober 2025  
> **Autoren:** Julian Umlauf, Michal Kos

---

 Dieses Dokument beschreibt die **technische Struktur und die genutzten Werkzeuge** für die Umsetzung der Aufgaben im **IPJ1**.  
 Es dient als Leitfaden für das Entwicklerteam und zur Transparenz innerhalb des Projekts.

---

## 1. Eingesetzte Werkzeuge und Bibliotheken

| Kategorie | Tool / Bibliothek | Beschreibung |
|------------|------------------|---------------|
| Programmiersprache | **Python 3.13.x** | Hauptsprache für Analyse, Simulation und Benutzeroberfläche |
| Datenanalyse | **Pandas** | Verarbeitung und Analyse von CSV-/Excel-Daten |
| Visualisierung | **Matplotlib** | Erstellung von Diagrammen und Plots |
| Versionskontrolle | **GitHub** | Verwaltung von Code und Dokumentation im Team |
| Entwicklungsumgebung | **VS Code** | Lokale Entwicklungsumgebung für Python-Projekte |

---

## 2. Projektstruktur (GitHub-Repository)

| **Ordner** | **Beschreibung** |
|------------|------------------|
| `/assets` | Zusätzliche Inhalte (z. B. Bilder für die Dokumentation) |
| `/documentation` | Projekt- und Entwicklungsdokumentation |
| `/output` | Ausgaben der Simulationssoftware (z. B. Diagramme, Ergebnisse) |
| `/raw-data` | Rohdaten zur weiteren Verarbeitung (z. B. SMARD-Daten) |
| `/source-code` | Quellcode der Anwendung (Python-Module und Skripte) |

---

## 3. Datenbeschaffung (SMARD)

Zugriff über: 
| Methode | Ursprung |
|-----|-----|
| SMARD API | Bundesnetzagentur Strommarktdaten |
| CSV-Download | SMARD Downloadcenter |
| Smardcast-Tool | Kolja Egers Github |

(Kombination der Methoden möglich)