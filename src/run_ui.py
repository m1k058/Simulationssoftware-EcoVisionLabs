from pathlib import Path
import streamlit as st


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
LOGO_PATH = ASSETS_DIR / "logo_icon.png"

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="EcoVision Labs Software",
    page_icon=str(LOGO_PATH),
    menu_items={
        "Get Help": "mailto:michal.kos@haw-hamburg.de?cc=julian.umlauf@haw-hamburg.de&subject=Supportanfrage%20EcovisionLabs%20Software",
        "About": "# EcoVision Labs Software\n\n" "Version 0.6.1\n\n" "© 2026 EcoVision Labs\n\n\n" "This software is developed and maintained by EcoVision Labs. For support or inquiries, please contact us at the email address provided in the 'Get Help' menu item."
    },
)

def main() -> None:
    """Main Funktion der Streamlit App."""



def load_base() -> None:
    """Lädt basis Daten"""
