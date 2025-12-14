import streamlit as st
from .components import render_checklist, SIMULATION_SCHRITTE
from .steps import ensure_step_state, reset_step_simulation


def step_simulation_page() -> None:
    """Übersichtsseite der Step Simulation mit Fortschritt und Links."""
    ensure_step_state()
    
    st.title("Step by Step Simulation")
    st.caption("Werde schrittweise durch die Simulation geführt. Wähle einen Schritt aus oder starte mit Schritt 1.")
    st.markdown("---")
    
    # Simulationsfortschritt in der Hauptseite anzeigen
    st.subheader("📊 Dein Simulationsfortschritt")
    step_index = st.session_state.get("step_index", 0)
    st.markdown(render_checklist(step_index), unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🚀 Simulation starten")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("▶️ Weiter zum aktuellen Schritt", use_container_width=True, type="primary"):
            st.switch_page(f"pages/step_{step_index + 1}:_*.py")
    
    with col2:
        if st.button("🔄 Von vorne beginnen", use_container_width=True):
            reset_step_simulation()
            st.rerun()
    
    with col3:
        if st.button("🏠 Zurück zur Startseite", use_container_width=True):
            st.switch_page("pages/home.py")
    
    st.markdown("---")
    st.subheader("📋 Alle Schritte")
    
    # Zeige alle Steps mit Status
    for i, schritt in enumerate(SIMULATION_SCHRITTE):
        col1, col2 = st.columns([0.3, 0.7])
        
        with col1:
            if i < step_index:
                st.success("✅")
            elif i == step_index:
                st.info("➡️")
            else:
                st.warning("⬜")
        
        with col2:
            if st.button(f"{schritt}", use_container_width=True, key=f"step_btn_{i}"):
                if i <= step_index:  # Nur zu abgeschlossenen oder aktuellem Step
                    st.session_state.step_index = i
                    # Navigiere zum entsprechenden Step
                    page_map = {
                        0: "step_1:_daten_ausw%C3%A4hlen",
                        1: "step_2:_verbrauch_simulieren",
                        2: "step_3:_erzeugung_simulieren",
                        3: "step_4:_defizite_anzeigen",
                        4: "step_5:_speicher_simulieren",
                        5: "step_6:_gesamt_validieren",
                        6: "step_7:_ergebnisse_speichern",
                    }
                    st.switch_page(f"pages/{page_map.get(i, 'home.py')}")
                else:
                    st.warning("⚠️ Bitte absolviere die vorherigen Schritte zuerst!")


