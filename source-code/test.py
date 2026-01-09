import plotly.graph_objects as go

# --- 1. Daten Vorbereitung ---
categories = [
    'Bezahlbarkeit (LCOE)',
    'Investitionshürde (CAPEX)',
    'Unabhängigkeit (Autarkie)',
    'System-Effizienz (Abregelung)',
    'Klimaschutz (CO2-Freiheit)'
]

# Szenario A: "Cheap & Dirty" (Wenig Invest, aber teurer Betrieb/dreckig)
values_a = [1, 5, 2, 2, 3] 
# (1=Teurer Strom, 5=Günstiger Bau, 2=Wenig Autarkie...)

# Szenario B: "High-Tech Green" (Teurer Bau, aber billiger Strom & Sauber)
values_b = [4, 2, 5, 4, 5]
# (4=Günstiger Strom, 2=Teurer Bau, 5=Volle Autarkie...)

# Daten-Loops schließen (Ersten Wert anhängen)
r_a = values_a + [values_a[0]]
r_b = values_b + [values_b[0]]
theta = categories + [categories[0]]

# --- 2. Figure erstellen ---
fig = go.Figure()

# Trace für Szenario A (Türkis)
fig.add_trace(go.Scatterpolar(
    r=r_a,
    theta=theta,
    fill='toself',
    name='Szenario A (Studie)',
    line=dict(color='#00cc96', width=3),
    marker=dict(size=8, color='#00cc96'),
    opacity=0.6 # Etwas transparenter, damit man Überlagerungen sieht
))

# Trace für Szenario B (Orange/Lila - Kontrastfarbe)
fig.add_trace(go.Scatterpolar(
    r=r_b,
    theta=theta,
    fill='toself',
    name='Szenario B (EcoVision)',
    line=dict(color='#ab63fa', width=3), # Lila als Kontrast
    marker=dict(size=8, color='#ab63fa'),
    opacity=0.6
))

# --- 3. Styling (Große Schrift & 1er Schritte) ---
fig.update_layout(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    
    # TITEL GRÖSSER
    title=dict(
        text="Szenario-Vergleich (Je größer die Fläche, desto besser)",
        font=dict(size=34, color='white'), # Size erhöht
        y=0.95,
        x=0.5,
        xanchor='center',
        yanchor='top'
    ),
    
    polar=dict(
        bgcolor='#2a2a2a',
        radialaxis=dict(
            visible=True,
            range=[0, 5],
            dtick=1, # <--- HIER: Zwingt Schritte auf 1, 2, 3... (keine 0.5)
            showticklabels=True,
            tickfont=dict(color='gray', size=18), # Zahlen größer
            gridcolor='#444444',
            linecolor='#444444',
            linewidth=1
        ),
        angularaxis=dict(
            # KATEGORIEN TEXT VIEL GRÖSSER
            tickfont=dict(color='white', size=24), 
            gridcolor='#444444',
            linecolor='#444444',
            linewidth=2,
            layer='below traces'
        )
    ),
    
    # LEGENDE GRÖSSER
    showlegend=True,
    legend=dict(
        font=dict(size=20, color='white'),
        bgcolor='rgba(0,0,0,0)',
        orientation="h", # Horizontal unten (optional, spart Platz)
        yanchor="bottom",
        y=-0.15,
        xanchor="center",
        x=0.5
    ),
    
    margin=dict(l=100, r=100, t=120, b=100) # Ränder angepasst für großen Text
)

fig.show()