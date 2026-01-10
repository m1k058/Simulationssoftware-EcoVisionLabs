"""Entferne deprecated Funktionen aus simulation.py"""
import re

# Lese die Datei
with open("source-code/data_processing/simulation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Entferne calc_scaled_consumption_multiyear (Zeile 12-43)
# Entferne calc_scaled_consumption (Zeile 45-203)
# Entferne calc_scaled_production_multiyear (Zeile 205-220)
# Diese Funktionen sind deprecated und werden nicht mehr verwendet

# Finde und entferne die Funktionen
lines = content.split('\n')
new_lines = []
skip_until = None
in_deprecated_function = False

i = 0
while i < len(lines):
    line = lines[i]
    
    # Prüfe ob wir in eine deprecated Funktion eintreten
    if 'def calc_scaled_consumption' in line or 'def calc_scaled_production_multiyear' in line:
        in_deprecated_function = True
        # Überspringe bis zur nächsten Funktion (def) oder Ende der Datei
        i += 1
        continue
    
    # Prüfe ob deprecated Funktion endet (neue Funktion beginnt)
    if in_deprecated_function and line.strip().startswith('def ') and 'calc_scaled' not in line:
        in_deprecated_function = False
        new_lines.append(line)
        i += 1
        continue
    
    # Wenn wir nicht in deprecated Funktion sind, Zeile behalten
    if not in_deprecated_function:
        new_lines.append(line)
    
    i += 1

# Schreibe zurück
new_content = '\n'.join(new_lines)
with open("source-code/data_processing/simulation.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("✓ Deprecated Funktionen entfernt")
print(f"  Vorher: {len(lines)} Zeilen")
print(f"  Nachher: {len(new_lines)} Zeilen")
print(f"  Entfernt: {len(lines) - len(new_lines)} Zeilen")
