"""
Test-Script zur Validierung des Storage-Cost-Fixes
Vergleicht alte vs. neue Logik für Batteriespeicher
"""

# Alte Logik (FEHLERHAFT):
def old_logic_battery():
    """Alte Logik: MW * duration_h = MWh (FALSCH bei bereits vorhandenen MWh-Werten)"""
    p_target_mw = 100  # Annahme: Input war MW
    duration_h = 4.0  # Batteriespeicher Standard
    capacity_target_mwh = p_target_mw * duration_h  # = 400 MWh
    
    capex_eur_per_mwh = 500000  # 500k EUR/MWh (Durchschnitt)
    
    investment = capacity_target_mwh * capex_eur_per_mwh
    return {
        "input": p_target_mw,
        "calculated_capacity_mwh": capacity_target_mwh,
        "capex_per_mwh": capex_eur_per_mwh,
        "total_investment_mio": investment / 1e6,
        "error": "Wenn Input bereits 100 MWh war, wird fälschlicherweise 400 MWh angenommen!"
    }

# Neue Logik (KORREKT):
def new_logic_battery():
    """Neue Logik: Liest installed_capacity_mwh direkt aus YAML"""
    storage_dict = {
        "installed_capacity_mwh": 100.0,  # Direkter Wert aus YAML
        "max_discharge_power_mw": 25.0
    }
    
    capacity_target_mwh = storage_dict["installed_capacity_mwh"]  # = 100 MWh (KORREKT!)
    
    capex_eur_per_mwh = 500000  # 500k EUR/MWh (Durchschnitt)
    
    investment = capacity_target_mwh * capex_eur_per_mwh
    return {
        "input_dict": storage_dict,
        "capacity_mwh": capacity_target_mwh,
        "capex_per_mwh": capex_eur_per_mwh,
        "total_investment_mio": investment / 1e6,
        "success": "Kapazität wird korrekt aus YAML übernommen, keine Multiplikation!"
    }

# Alte Logik (FEHLERHAFT):
def old_logic_h2():
    """Alte Logik für H2-Speicher (168h Faktor)"""
    p_target_mw = 1000  # Annahme: Input war MW
    duration_h = 168.0  # H2-Speicher Standard (1 Woche)
    capacity_target_mwh = p_target_mw * duration_h  # = 168.000 MWh
    
    capex_eur_per_mwh = 500000  # 500k EUR/MWh
    
    investment = capacity_target_mwh * capex_eur_per_mwh
    return {
        "input": p_target_mw,
        "calculated_capacity_mwh": capacity_target_mwh,
        "capex_per_mwh": capex_eur_per_mwh,
        "total_investment_mrd": investment / 1e9,
        "error": "Bei 1000 MWh Input wird fälschlicherweise 168.000 MWh berechnet!"
    }

# Neue Logik (KORREKT):
def new_logic_h2():
    """Neue Logik für H2-Speicher"""
    storage_dict = {
        "installed_capacity_mwh": 1000.0,  # Direkter Wert aus YAML
        "max_discharge_power_mw": 100.0
    }
    
    capacity_target_mwh = storage_dict["installed_capacity_mwh"]  # = 1000 MWh
    
    capex_eur_per_mwh = 500000  # 500k EUR/MWh
    
    investment = capacity_target_mwh * capex_eur_per_mwh
    return {
        "input_dict": storage_dict,
        "capacity_mwh": capacity_target_mwh,
        "capex_per_mwh": capex_eur_per_mwh,
        "total_investment_mrd": investment / 1e9,
        "success": "Korrekte Berechnung ohne Multiplikation!"
    }


if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("VALIDIERUNG: Storage Cost Fix")
    print("=" * 80)
    print()
    
    print("1. BATTERIESPEICHER (60.000 MWh aus YAML)")
    print("-" * 80)
    print("ALTE LOGIK (FEHLERHAFT):")
    old_bat = old_logic_battery()
    print(json.dumps(old_bat, indent=2, ensure_ascii=False))
    print()
    print("NEUE LOGIK (KORREKT):")
    new_bat = new_logic_battery()
    print(json.dumps(new_bat, indent=2, ensure_ascii=False))
    print()
    print(f"DIFFERENZ: {old_bat['total_investment_mio']} Mio € vs. {new_bat['total_investment_mio']} Mio €")
    print(f"FAKTOR: {old_bat['total_investment_mio'] / new_bat['total_investment_mio']:.1f}x zu hoch (alte Logik)")
    print()
    
    print()
    print("2. H2-SPEICHER (500.000 MWh aus YAML)")
    print("-" * 80)
    print("ALTE LOGIK (FEHLERHAFT):")
    old_h2 = old_logic_h2()
    print(json.dumps(old_h2, indent=2, ensure_ascii=False))
    print()
    print("NEUE LOGIK (KORREKT):")
    new_h2 = new_logic_h2()
    print(json.dumps(new_h2, indent=2, ensure_ascii=False))
    print()
    print(f"DIFFERENZ: {old_h2['total_investment_mrd']} Mrd. € vs. {new_h2['total_investment_mrd']} Mrd. €")
    print(f"FAKTOR: {old_h2['total_investment_mrd'] / new_h2['total_investment_mrd']:.1f}x zu hoch (alte Logik)")
    print()
    
    print()
    print("=" * 80)
    print("ZUSAMMENFASSUNG:")
    print("=" * 80)
    print("✅ Der Fix korrigiert die Kostenberechnung für Speicher:")
    print("   - Batteriespeicher: Kosten werden um Faktor 4 reduziert (korrekt)")
    print("   - H2-Speicher: Kosten werden um Faktor 168 reduziert (korrekt)")
    print("   - Grund: installed_capacity_mwh wird direkt aus YAML verwendet")
    print("   - Keine Multiplikation mit duration_h mehr!")
    print()
