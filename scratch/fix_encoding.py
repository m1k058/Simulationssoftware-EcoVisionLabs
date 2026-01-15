"""Ersetze Sonderzeichen in simulation.py für Python-Kompatibilität"""

with open("source-code/data_processing/simulation.py", "r", encoding="utf-8") as f:
    content = f.read()

# Ersetze Sonderzeichen
replacements = {
    "°C": "Grad C",
    "€": "EUR",
    "€/kWh": "EUR/kWh",
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open("source-code/data_processing/simulation.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Sonderzeichen ersetzt")
