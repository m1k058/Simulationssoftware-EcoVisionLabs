import streamlit as st

def set_mode(new_mode: str) -> None:
    st.session_state.mode = new_mode
