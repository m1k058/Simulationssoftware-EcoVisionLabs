# Simulationssoftware-EcoVisionLabs

Ein Projekt von **EcoVision Labs** :) 

### Shortcuts:
- [zu den Features](docu/code_features_aktuell.md)  
- [zur technischen Planung](docu/technische_planung.md)  
- [Beispiel Plot Interaktiv](https://m1k058.github.io/Simulationssoftware-EcoVisionLabs/interactive_plot_example.html)  
- [zum Konzept](docu/konzept.md)

- [Online Software (in entwicklung)](https://simu-ecovisionlabs.streamlit.app/)
   
## 1. Funktionen

Die Software dient zur **Simulation und Analyse der Energieerzeugung in Deutschland**,  
mit Fokus auf erneuerbare Energien und das Erreichen der Klimaziele 2030/2045.  

### Hauptfunktionen
- **Simulation verschiedener Energiequellen**
  - Windenergie  
  - Solarenergie
  - und mehr
- **Visualisierung**
  - Diagramme und Statistiken zur Stromerzeugung, -nachfrage und zum Anteil erneuerbarer Energien  



## 2. Schnellstart

### Voraussetzungen
- Python 3.9 oder höher
- Abhängigkeiten: `pandas`, `matplotlib`, `numpy`

### Software starten (einfach)

Die Software kann **direkt** gestartet werden, ohne Installation:

**Linux/macOS (bash/fish):**
```bash
python source-code/main.py
```

**Windows (PowerShell/cmd):**
```powershell
python source-code\main.py
```

### Abhängigkeiten installieren

Falls Bibliotheken fehlen:

**Mit pip (alle Plattformen):**
```bash
pip install pandas matplotlib numpy
```

**Mit Virtual Environment (empfohlen für Entwicklung):**

Linux/macOS:
```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib numpy
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install pandas matplotlib numpy
```

---

## 3. Installation für Entwickler (optional)

Für die **Entwicklung** (z.B. zum Ausführen von Unit-Tests oder für bessere IDE-Integration) 
kann das Projekt im "editable mode" installiert werden:

```bash
# Projekt im editable mode installieren
pip install -e .
```

### Tests ausführen (nach editable install)

```bash
# Alle Tests
python -m unittest discover tests -v

# Einzelne Test-Datei
python -m unittest tests.test_config_manager -v
```

## 3. Das EcoVision-Team

![Teamfoto](assets/team1.png)  
*Team EcoVision Labs – Gründung Oktober 2025*
