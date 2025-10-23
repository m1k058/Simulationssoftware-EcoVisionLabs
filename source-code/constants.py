from enum import Enum

# Words that should be cleaed from columns
HEADER_CLEAN_PATTERNS = [
    "Berechnete Auflösungen",
    "Originalauflösungen"
]

# Expected headers for different datatypes
EXPECTED_HEADERS = {
    "SMARD": [
        "Datum von",
        "Datum bis",
        "Biomasse [MWh]",
        "Wasserkraft [MWh]",
        "Wind Offshore [MWh]",
        "Wind Onshore [MWh]",
        "Photovoltaik [MWh]",
        "Sonstige Erneuerbare [MWh]",
        "Kernenergie [MWh]",
        "Braunkohle [MWh]",
        "Steinkohle [MWh]",
        "Erdgas [MWh]",
        "Pumpspeicher [MWh]",
        "Sonstige Konventionelle [MWh]",
    ],
    "OTHER": [
        "Column1",
        "Column2",
    ]
}

# Format for data in file
FILE_FORMAT_OPTIONS = {
    "SMARD": {
        "sep": ";",
        "decimal": ",",
        "thousands": ".",
        "date_format": "%d.%m.%Y %H:%M",
        "encoding": "utf-8",
        "na_values": ["-", "NaN", "n/a", ""]
    },
    "OTHER": {
        "sep": ",",
        "decimal": ".",
        "thousands": ",",
        "date_format": "%Y-%m-%d",
        "encoding": "utf-8",
        "na_values": ["", "null", "NaN"]
    }
}


# Energy Sources Names, Shortcodes and Colors
ENERGY_SOURCES = {
    "BIO": {"name": "Biomasse", "color": "#00A51B"},
    "WAS": {"name": "Wasserkraft", "color": "#1E90FF"},
    "WOF": {"name": "Wind Offshore", "color": "#00BFFF"},
    "WON": {"name": "Wind Onshore", "color": "#007F78"},
    "PV": {"name": "Photovoltaik", "color": "#FFD700"},
    "SOE": {"name": "Sonstige Erneuerbare", "color": "#ADFF2F"},
    "KE": {"name": "Kernenergie", "color": "#800080"},
    "BK": {"name": "Braunkohle", "color": "#774400"},
    "SK": {"name": "Steinkohle", "color": "#1F1F1F"},
    "EG": {"name": "Erdgas", "color": "#5D5D5D"},
    "PS": {"name": "Pumpspeicher", "color": "#090085"},
    "SOK": {"name": "Sonstige Konventionelle", "color": "#A9A9A9"},
}