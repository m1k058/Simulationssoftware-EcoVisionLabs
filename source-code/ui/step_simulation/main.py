import streamlit as st
from .components import render_checklist, SIMULATION_SCHRITTE
from .steps import (
    ensure_step_state,
    set_step,
    reset_step_simulation,
    daten_auswaehlen,
    verbrauch_simulieren,
    erzeugung_simulieren,
    defizite_anzeigen,
    speicher_simulieren,
    gesamt_validieren,
    ergebnisse_speichern,
)
from .. import set_mode


def show_step_simulation() -> None:
    st.title("Step by Step Simulation")
    st.caption("Werde schrittweise durch die Simulation geführt.")
    st.markdown("---")

    ensure_step_state()
    aktiver_schritt_index = st.session_state.step_index

    sidebar = st.sidebar
    sidebar.title("Simulationsfortschritt")
    sidebar.markdown(render_checklist(aktiver_schritt_index), unsafe_allow_html=True)

    step_functions = [
        daten_auswaehlen,
        verbrauch_simulieren,
        erzeugung_simulieren,
        defizite_anzeigen,
        speicher_simulieren,
        gesamt_validieren,
        ergebnisse_speichern,
    ]

    if 0 <= aktiver_schritt_index < len(step_functions):
        step_functions[aktiver_schritt_index]()
    else:
        st.error("Unbekannter Simulationsschritt. Versuche die App neu zu starten.")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if aktiver_schritt_index > 0:
            st.button(
                "⬅️ Zurück",
                on_click=set_step,
                args=(aktiver_schritt_index - 1,),
                use_container_width=True,
            )
        else:
            st.button("⬅️ Zurück", disabled=True, use_container_width=True)

    with col2:
        st.button("Hauptmenü", on_click=set_mode, args=("main",), use_container_width=True)

    with col3:
        if aktiver_schritt_index < len(SIMULATION_SCHRITTE) - 1:
            if st.session_state.step_valid:
                st.button(
                    "Weiter ➡️",
                    on_click=set_step,
                    args=(aktiver_schritt_index + 1,),
                    use_container_width=True,
                    type="primary",
                )
            else:
                st.button("Weiter ➡️", disabled=True, use_container_width=True)
        else:
            st.button("✅ Fertig", on_click=set_mode, args=("main",), use_container_width=True, type="primary")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button(
            "Simulation zurücksetzen",
            on_click=reset_step_simulation,
            use_container_width=True,
            type="secondary",
        )
