

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
    "SMARD-Inst": [
        "Datum von",
        "Datum bis",
        "Biomasse [MW]",
        "Wasserkraft [MW]",
        "Wind Offshore [MW]",
        "Wind Onshore [MW]",
        "Photovoltaik [MW]",
        "Sonstige Erneuerbare [MW]",
        "Kernenergie [MW]",
        "Braunkohle [MW]",
        "Steinkohle [MW]",
        "Erdgas [MW]",
        "Pumpspeicher [MW]",
        "Sonstige Konventionelle [MW]",
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
    ],
    "BDEW-Last": [
        "timestamp",
        "month",
        "day_type",
        "value_kWh",
    ],
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
    "SMARD-Inst": {
        "sep": ";",
        "decimal": ",",
        "thousands": ".",
        "date_format": "dayfirst",
        "encoding": "utf-8",
        "na_values": ["-", "NaN", "n/a", ""]
    },    
    "BDEW-Last": {
        "sep": "\t",
        "decimal": ",",
        "thousands": ".",
        "date_format": "%Y-%m-%d %H:%M:%S",
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
    "KE": {"name": "Kernenergie", "color": "#800080", "colname": "Kernenergie [MWh]", "colname_MW": "Kernenergie [MW]"},
    "BK": {"name": "Braunkohle", "color": "#774400", "colname": "Braunkohle [MWh]", "colname_MW": "Braunkohle [MW]"},
    "SK": {"name": "Steinkohle", "color": "#1F1F1F", "colname": "Steinkohle [MWh]", "colname_MW": "Steinkohle [MW]"},
    "EG": {"name": "Erdgas", "color": "#5D5D5D", "colname": "Erdgas [MWh]", "colname_MW": "Erdgas [MW]"},
    "SOE": {"name": "Sonstige Erneuerbare", "color": "#ADFF2F", "colname": "Sonstige Erneuerbare [MWh]", "colname_MW": "Sonstige Erneuerbare [MW]"},
    "SOK": {"name": "Sonstige Konventionelle", "color": "#272727", "colname": "Sonstige Konventionelle [MWh]", "colname_MW": "Sonstige Konventionelle [MW]"},
    "BIO": {"name": "Biomasse", "color": "#00A51B", "colname": "Biomasse [MWh]", "colname_MW": "Biomasse [MW]"},
    "PS": {"name": "Pumpspeicher", "color": "#090085", "colname": "Pumpspeicher [MWh]", "colname_MW": "Pumpspeicher [MW]"},
    "WAS": {"name": "Wasserkraft", "color": "#1E90FF", "colname": "Wasserkraft [MWh]", "colname_MW": "Wasserkraft [MW]"},
    "WOF": {"name": "Wind Offshore", "color": "#00BFFF", "colname": "Wind Offshore [MWh]", "colname_MW": "Wind Offshore [MW]"},
    "WON": {"name": "Wind Onshore", "color": "#007F78", "colname": "Wind Onshore [MWh]", "colname_MW": "Wind Onshore [MW]"},
    "PV": {"name": "Photovoltaik", "color": "#FFD700", "colname": "Photovoltaik [MWh]", "colname_MW": "Photovoltaik [MW]"},
}

SOURCES_GROUPS = {
    "Renewable": ["BIO", "WAS", "WOF", "WON", "PV", "SOE"],
    "Conventional": ["KE", "BK", "SK", "EG", "SOK"],
    "Storage": ["PS"],
    "All": ["KE", "BK", "SK", "EG", "SOK", "SOE", "BIO", "PS", "WAS", "WOF", "WON", "PV"]
}

ECONOMICS_CONSTANTS = {
    "global_parameter": {
        "wacc": 0.05
    },
    "source_specific": {
        "Erdgas":{
            "capex_eur_per_mw": 600000,
            "opex_eur_per_mw_year": 9000,
            "lifetime_years":25
        },
        "Biomasse":{
            "capex_eur_per_mw": 600000,
            "opex_eur_per_mw_year": 9000,
            "lifetime_years":25
        },
        "Wasserkraft":{
            "opex_eur_per_mw_year": 9000
        },
        "Wind Onshore":{
            "capex_eur_per_mw": 1500000,
            "opex_eur_per_mw_year": 22500,
            "lifetime_years":20
        },
        "Wind Offshore":{
            "capex_eur_per_mw": 3000000,
            "opex_eur_per_mw_year": 45000,
            "lifetime_years":20
        },
        "Photovoltaik":{
            "capex_eur_per_mw": 800000,
            "opex_eur_per_mw_year": 12000,
            "lifetime_years":25
        },
        "Elektrolyseur":{
            "capex_eur_per_mw": 1000000,
            "opex_eur_per_mw_year": 15000,
            "lifetime_years":20
        },
        "H2_Elektrifizierung":{
            "capex_eur_per_mw": 500000,
            "opex_eur_per_mw_year": 7500,
            "lifetime_years":25
        },
        "Batteriespeicher":{
            "capex_eur_per_mw": 400000,
            "opex_eur_per_mw_year": 6000,
            "lifetime_years":15
        },
        "Pumpspeicher":{
            "opex_eur_per_mw_year": 30000
        },
        "Wasserstoffspeicher":{
            "capex_eur_per_mw": 200000,
            "opex_eur_per_mw_year": 3000,
            "lifetime_years":30
        }        
    }
}