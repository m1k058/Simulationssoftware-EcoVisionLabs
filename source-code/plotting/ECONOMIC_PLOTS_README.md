# Wirtschaftlichkeits-Dashboard Integrations-Guide

## Überblick

Das Consulting-Dashboard besteht aus drei integrierten Visualisierungen zur Darstellung der wirtschaftlichen Entwicklung:

### 1. **Trend-Graph** (`plot_economic_trends`)
- **Typ**: Kombi-Plot mit zwei Y-Achsen
- **Primärachse (Balken)**: Investitionsbedarf in Mrd. €
- **Sekundärachse (Linie)**: LCOE (Stromgestehungskosten in ct/kWh)
- **Datenbasis**: Liste aller Jahresergebnisse
- **Zweck**: Zeigt Investitionen und deren Effekt auf die LCOE über die Zeit

### 2. **Kostenaufschlüsselung** (`plot_cost_structure`)
- **Typ**: Gestapeltes Balkendiagramm (Stacked Bar)
- **Kategorien**: 
  - Kapitalkosten (CAPEX) - Dunkelblau
  - Fixe Betriebskosten - Hellblau
  - Variable Kosten (Brennstoff/CO2) - Orange/Rot
- **Datenbasis**: Liste aller Jahresergebnisse
- **Zweck**: Erklärt, woraus sich die Gesamtkosten zusammensetzen und zeigt, wie Variable Kosten mit höherem EE-Anteil sinken

### 3. **Investitionsmix** (`plot_investment_donut`)
- **Typ**: Donut-Chart
- **Daten**: Investitionsverteilung nach Technologie für ein Jahr
- **Farben**: Konsistent mit anderen Energy-Source-Charts
- **Zweck**: Zeigt visuell, welche Technologien den Zubau dominieren

## Integration in Streamlit

Die Diagramme werden unterhalb des SOC-Graphen angeordnet:

```python
# Hauptgraph: Trend (volle Breite)
fig_econ = ply.plot_economic_trends(econ_series)
st.plotly_chart(fig_econ, use_container_width=True)

# Nebendiagramme: Kosten und Investitionsmix (Nebeneinander)
col_cost, col_inv = st.columns(2)

with col_cost:
    fig_cost = econ_ply.plot_cost_structure(econ_series)
    st.plotly_chart(fig_cost, use_container_width=True)

with col_inv:
    fig_donut = econ_ply.plot_investment_donut(
        investment_dict={'Photovoltaik': 50.0, 'Wind_Onshore': 120.0, ...},
        year=2030
    )
    st.plotly_chart(fig_donut, use_container_width=True)
```

## Datenbedarf für `plot_investment_donut`

Derzeit wird die Investitionsverteilung noch nicht automatisch aus dem EconomicCalculator generiert. 

**Sobald verfügbar**, sollte der `economical_calculation()` in `simulation.py` erweitert werden um:
```python
"investment_by_tech": {
    'Photovoltaik': 50.0,     # Mrd. €
    'Wind_Onshore': 120.0,
    'Wind_Offshore': 30.0,
    ...
}
```

Bis dahin zeigt Streamlit eine Info-Nachricht "Investitionsverteilung nach Technologie nicht verfügbar."

## Styling-Details

- **Template**: `plotly_white` (sauberer, moderner Look)
- **Legenden**: Horizontal über/unter den Charts für bessere Lesbarkeit
- **Hover**: Einheitlich über alle Charts (`hovermode="x unified"`)
- **Grid**: Nur auf primären Achsen, um "Chart Junk" zu minimieren
- **Farben**: 
  - CAPEX: Navy `#1f4b99`
  - OpEx Fix: Light Blue `#7fa6d1`
  - OpEx Var: Orange/Red `#e4572e`
  - Technologien: Konsistent mit ENERGY_SOURCES aus constants.py

## Beispielaufruf

```python
# Test-Daten erstellen
econ_series = [
    {'year': 2030, 'total_annual_cost_bn': 22.4, 'system_lco_e': 7.5},
    {'year': 2045, 'total_annual_cost_bn': 18.2, 'system_lco_e': 6.8},
]

# Funktionen aufrufen
fig_trend = plot_economic_trends(econ_series)
fig_cost = plot_cost_structure(econ_series)
fig_donut = plot_investment_donut({'Photovoltaik': 50, 'Wind_Onshore': 100}, 2030)

# In Streamlit anzeigen
st.plotly_chart(fig_trend)
st.plotly_chart(fig_cost)
st.plotly_chart(fig_donut)
```
