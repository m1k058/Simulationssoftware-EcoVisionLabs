from enum import Enum

class EnergySources(Enum):
    BIO = {
        "name": "Biomasse",
        "col": "Biomasse [MWh] Berechnete Auflösungen",
        "color": "#00A51B"
    }
    WAS = {
        "name": "Wasserkraft",
        "col": "Wasserkraft [MWh] Berechnete Auflösungen",
        "color": "#1E90FF"
    }
    WOF = {
        "name": "Wind (Offshore)",
        "col": "Wind Offshore [MWh] Berechnete Auflösungen",
        "color": "#00BFFF"
    }
    WON = {
        "name": "Wind (Onshore)",
        "col": "Wind Onshore [MWh] Berechnete Auflösungen",
        "color": "#00C4A3"
    }
    PV = {
        "name": "Photovoltaik",
        "col": "Photovoltaik [MWh] Berechnete Auflösungen",
        "color": "#FFD700"
    }
    SOE = {
        "name": "Sonstige Erneuerbare",
        "col": "Sonstige Erneuerbare [MWh] Berechnete Auflösungen",
        "color": "#ADFF2F"
    }
    KE = {
        "name": "Kernenergie",
        "col": "Kernenergie [MWh] Berechnete Auflösungen",
        "color": "#800080"
    }
    BK = {
        "name": "Braunkohle",
        "col": "Braunkohle [MWh] Berechnete Auflösungen",
        "color": "#774400"
    }
    SK = {
        "name": "Steinkohle",
        "col": "Steinkohle [MWh] Berechnete Auflösungen",
        "color": "#1F1F1F"
    }
    EG = {
        "name": "Erdgas",
        "col": "Erdgas [MWh] Berechnete Auflösungen",
        "color": "#5D5D5D"
    }
    PS = {
        "name": "Pumpspeicher",
        "col": "PS [MWh] Berechnete Auflösungen",  
        "color": "#090085"
    }
    SOK = {
        "name": "Sonstige Konventionelle",
        "col": "Sonstige Konventionelle [MWh] Berechnete Auflösungen",
        "color": "#A9A9A9"
    }

