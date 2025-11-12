

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
    "SMARD-V": [
        "Datum von",
        "Datum bis",
        "Netzlast [MWh]",
        "Netzlast inkl. Pumpspeicher [MWh]",
        "Pumpspeicher [MWh]",
        "Residuallast [MWh]",
    ],
    "CUST_PROG": [
        "Studie",
        "Jahr",
        "Biomasse [TWh]",
        "Wasserkraft [TWh]",
        "Wind Offshore [TWh]",
        "Wind Onshore [TWh]",
        "Photovoltaik [TWh]",
        "Abgeregelte EE-Menge [TWh]",
        "Wasserstoff [TWh]",
        "Kernenergie [TWh]",
        "Braunkohle [TWh]",
        "Steinkohle [TWh]",
        "Erdgas [TWh]",
        "Sonstige [TWh]",
        "Speicher [TWh]",
        "Abfall [TWh]",
        "Summe [TWh]",
        "Importsaldo [TWh]",
        "Gesamterzeugung Erneuerbare [TWh]",
        "Gesamterzeugung Konventionelle [TWh]",
        "Gesamterzeugung [TWh]",
        "Bruttostromverbrauch [TWh]",
        "Anteil Erneuerbare",
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
    "SMARD-V": {
        "sep": ";",
        "decimal": ",",
        "thousands": ".",
        "date_format": "%d.%m.%Y %H:%M",
        "encoding": "utf-8",
        "na_values": ["-", "NaN", "n/a", ""]
    },
    "CUST_PROG": {
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
    "KE": {"name": "Kernenergie", "color": "#800080", "colname": "Kernenergie [MWh]"},
    "BK": {"name": "Braunkohle", "color": "#774400", "colname": "Braunkohle [MWh]"},
    "SK": {"name": "Steinkohle", "color": "#1F1F1F", "colname": "Steinkohle [MWh]"},
    "EG": {"name": "Erdgas", "color": "#5D5D5D", "colname": "Erdgas [MWh]"},
    "SOE": {"name": "Sonstige Erneuerbare", "color": "#ADFF2F", "colname": "Sonstige Erneuerbare [MWh]"},
    "SOK": {"name": "Sonstige Konventionelle", "color": "#272727", "colname": "Sonstige Konventionelle [MWh]"},
    "BIO": {"name": "Biomasse", "color": "#00A51B", "colname": "Biomasse [MWh]"},
    "PS": {"name": "Pumpspeicher", "color": "#090085", "colname": "Pumpspeicher [MWh]"},
    "WAS": {"name": "Wasserkraft", "color": "#1E90FF", "colname": "Wasserkraft [MWh]"},
    "WOF": {"name": "Wind Offshore", "color": "#00BFFF", "colname": "Wind Offshore [MWh]"},
    "WON": {"name": "Wind Onshore", "color": "#007F78", "colname": "Wind Onshore [MWh]"},
    "PV": {"name": "Photovoltaik", "color": "#FFD700", "colname": "Photovoltaik [MWh]"},
}

SOURCES_GROUPS = {
    "Renewable": ["BIO", "WAS", "WOF", "WON", "PV", "SOE"],
    "Conventional": ["KE", "BK", "SK", "EG", "SOK"],
    "Storage": ["PS"],
    "All": ["KE", "BK", "SK", "EG", "SOK", "SOE", "BIO", "PS", "WAS", "WOF", "WON", "PV"]
}