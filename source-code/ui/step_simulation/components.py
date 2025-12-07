SIMULATION_SCHRITTE = [
    "Daten auswählen",
    "Verbrauch Simulieren",
    "Erzeugung Simulieren",
    "Defizite anzeigen",
    "Speicher Simulieren",
    "Gesamt Ergebnisse",
    "Ergebnisse speichern"
]

def render_checklist(aktiver_schritt_index):
    """Generiert die Checkliste mit Emojis und HTML-Farben."""
    
    checklist_html = ""
    
    for i, schritt in enumerate(SIMULATION_SCHRITTE):
        
        if i < aktiver_schritt_index:
            # Zustand 1: ABGESCHLOSSEN
            line = f"✅ <span style='color: #28a745;'>{schritt}</span>"
            
        elif i == aktiver_schritt_index:
            # Zustand 2: AKTIV 
            line = f"➡️ **{schritt}**"
            
        else:
            # Zustand 3: AUSSTEHEND
            line = f"⬜ <span style='color: #6c757d;'>{schritt}</span>"
            
        # Füge einen Zeilenumbruch (<br>) hinzu, damit die Liste vertikal bleibt.
        checklist_html += f"{line} <br>\n\n"

    return checklist_html
