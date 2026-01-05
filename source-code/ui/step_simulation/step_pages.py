"""
Separate Page-Module für jeden Simulationsschritt.
Diese Datei definiert individuelle Pages für die Step-Simulation.
"""
import streamlit as st
from .steps import (
    ensure_step_state,
    daten_auswaehlen,
    verbrauch_simulieren,
    erzeugung_simulieren,
    defizite_anzeigen,
    speicher_simulieren,
    gesamt_validieren,
    ergebnisse_speichern,
)
from .components import SIMULATION_SCHRITTE


def render_navigation_buttons(current_step: int, can_proceed: bool = True):
    """Zeigt Weiter/Zurück Buttons."""
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if current_step > 0:
            if st.button("⬅️ Zurück", width='stretch', key=f"back_{current_step}"):
                st.session_state.step_index = current_step - 1
                # Nutze query_params um die Page zu kontrollieren
                st.query_params.update({"step": current_step - 1})
        else:
            st.button("⬅️ Zurück", disabled=True, width='stretch', key=f"back_{current_step}")
    
    with col2:
        if current_step < len(SIMULATION_SCHRITTE) - 1:
            if st.button("Weiter ➡️", width='stretch', type="primary", disabled=not can_proceed, key=f"next_{current_step}"):
                if can_proceed:
                    st.session_state.step_index = current_step + 1
                    # Nutze query_params um die Page zu kontrollieren
                    st.query_params.update({"step": current_step + 1})
        else:
            if st.button("✅ Fertig", width='stretch', type="primary", key=f"finish_{current_step}"):
                # Simulation zurücksetzen und zur Home-Page
                st.session_state.step_index = 0
                st.query_params.clear()


# ===== STEP 1: Daten auswählen =====
def step_1_daten_auswaehlen():
    """Step 1: Daten auswählen"""
    ensure_step_state()
    st.session_state.step_index = 0  # Setze aktuellen Step
    
    st.title("Step 1️⃣: Daten auswählen")
    st.caption("Wähle die Datensätze für die Simulation aus.")
    st.markdown("---")
    
    daten_auswaehlen()
    
    render_navigation_buttons(0, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 2: Verbrauch Simulieren =====
def step_2_verbrauch_simulieren():
    """Step 2: Verbrauch Simulieren"""
    ensure_step_state()
    st.session_state.step_index = 1  # Setze aktuellen Step
    
    # Validierung: Daten müssen ausgewählt sein
    if not st.session_state.get("sim_datei_verbrauch"):
        st.warning("⚠️ Bitte wähle zuerst die Daten im ersten Schritt aus!")
        st.stop()
    
    st.title("Step 2️⃣: Verbrauch Simulieren")
    st.caption("Simuliere die Verbrauchsdaten basierend auf deinen Einstellungen.")
    st.markdown("---")
    
    verbrauch_simulieren()
    
    render_navigation_buttons(1, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 3: Erzeugung Simulieren =====
def step_3_erzeugung_simulieren():
    """Step 3: Erzeugung Simulieren"""
    ensure_step_state()
    st.session_state.step_index = 2  # Setze aktuellen Step
    
    # Validierung: Vorherige Steps müssen abgeschlossen sein
    if not st.session_state.get("df_simulation_con") is not None:
        st.warning("⚠️ Bitte fülle zuerst Schritt 1 und 2 aus!")
        st.stop()
    
    st.title("Step 3️⃣: Erzeugung Simulieren")
    st.caption("Simuliere die Erzeugungsdaten basierend auf deinen Einstellungen.")
    st.markdown("---")
    
    erzeugung_simulieren()
    
    render_navigation_buttons(2, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 4: Defizite anzeigen =====
def step_4_defizite_anzeigen():
    """Step 4: Defizite anzeigen"""
    ensure_step_state()
    st.session_state.step_index = 3  # Setze aktuellen Step
    
    # Validierung: Verbrauch und Erzeugung müssen simuliert sein
    if not (st.session_state.get("df_simulation_con") is not None and 
            st.session_state.get("df_simulation_prod") is not None):
        st.warning("⚠️ Bitte fülle zuerst die Schritte 1-3 aus!")
        st.stop()
    
    st.title("Step 4️⃣: Defizite analysieren")
    st.caption("Analysiere die Defizite zwischen Verbrauch und Erzeugung.")
    st.markdown("---")
    
    defizite_anzeigen()
    
    render_navigation_buttons(3, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 5: Speicher Simulieren =====
def step_5_speicher_simulieren():
    """Step 5: Speicher Simulieren"""
    ensure_step_state()
    st.session_state.step_index = 4  # Setze aktuellen Step
    
    # Validierung: Defizite müssen analysiert sein
    energie_bilanz = st.session_state.get("energie_bilanz")
    if energie_bilanz is None or (hasattr(energie_bilanz, 'empty') and energie_bilanz.empty):
        st.warning("⚠️ Bitte fülle zuerst die Schritte 1-4 aus!")
        st.stop()
    
    st.title("Step 5️⃣: Speicher Simulieren")
    st.caption("Simuliere verschiedene Speicherszenarien.")
    st.markdown("---")
    
    speicher_simulieren()
    
    render_navigation_buttons(4, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 6: Gesamt Validieren =====
def step_6_gesamt_validieren():
    """Step 6: Gesamt Validieren"""
    ensure_step_state()
    st.session_state.step_index = 5  # Setze aktuellen Step
    
    st.title("Step 6️⃣: Gesamt Ergebnisse")
    st.caption("Validiere die Gesamtergebnisse deiner Simulation.")
    st.markdown("---")
    
    gesamt_validieren()
    
    render_navigation_buttons(5, can_proceed=st.session_state.get("step_valid", True))


# ===== STEP 7: Ergebnisse speichern =====
def step_7_ergebnisse_speichern():
    """Step 7: Ergebnisse speichern"""
    ensure_step_state()
    st.session_state.step_index = 6  # Setze aktuellen Step
    
    st.title("Step 7️⃣: Ergebnisse speichern")
    st.caption("Speichere deine Simulationsergebnisse ab.")
    st.markdown("---")
    
    ergebnisse_speichern()
    
    render_navigation_buttons(6, can_proceed=True)

