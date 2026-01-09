

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

TECHNOLOGY_COSTS = {
    "Erdgas": {
        "capex_eur_per_mw": [450000, 700000],
        "opex_fix_eur_per_mw": 23000,
        "opex_var_eur_per_mwh": 4.0,
        "lifetime_years": 30,
        "efficiency": 0.40,
        "fuel_type": "Erdgas"
    },
    "Biomasse": {
        "capex_eur_per_mw": [3470000, 5790000],
        "opex_fix_eur_per_mw": 185000,
        "opex_var_eur_per_mwh": 4.0,
        "lifetime_years": 25,
        "efficiency": 0.45,
        "fuel_type": "Biomasse"
    },
    "Wasserkraft": {
        "capex_eur_per_mw": [0, 0],
        "opex_fix_eur_per_mw": 15000,
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 60,
        "efficiency": 0.90
    },
    "Wind Offshore": {
        "capex_eur_per_mw": [2200000, 3400000],
        "opex_fix_eur_per_mw": 39000,
        "opex_var_eur_per_mwh": 8.0,
        "lifetime_years": 25,
        "efficiency": 1.00
    },
    "Wind Onshore": {
        "capex_eur_per_mw": [1300000, 1900000],
        "opex_fix_eur_per_mw": 32000,
        "opex_var_eur_per_mwh": 7.0,
        "lifetime_years": 25,
        "efficiency": 1.00
    },
    "Photovoltaik": {
        "capex_eur_per_mw": [700000, 900000],
        "opex_fix_eur_per_mw": 13300,
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 30,
        "efficiency": 1.00
    },
    "Elektrolyseur": {
        "capex_eur_per_mw": [1800000, 2400000], # Update: IEA 2024 DE
        "opex_fix_eur_per_mw": 20000,
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 20,
        "efficiency": 0.68
    },
    "H2_Elektrifizierung": {
        "capex_eur_per_mw": [550000, 1200000],
        "opex_fix_eur_per_mw": 23000,
        "opex_var_eur_per_mwh": 5.0,
        "lifetime_years": 30,
        "efficiency": 0.40,
        "fuel_type": "Wasserstoff"
    },
    "Batteriespeicher": {
        "capex_eur_per_mw": [400000, 600000],
        "opex_fix_eur_per_mw": 10000,
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 15,
        "efficiency": 0.92
    },
    "Pumpspeicher": {
        "capex_eur_per_mw": [1200000, 3000000], # Update: Wuppertal Paper
        "opex_fix_eur_per_mw": 75000,           # Update: Mittelwert (50k-100k)
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 60,
        "efficiency": 0.85
    },
    "Wasserstoffspeicher": {
        "capex_eur_per_mw": [400000, 600000],
        "opex_fix_eur_per_mw": 5000,
        "opex_var_eur_per_mwh": 0.0,
        "lifetime_years": 30,
        "efficiency": 1.00
    }
}

COMMODITIES = {
    "fuel_prices": {
        "Erdgas": 35.0,
        "Wasserstoff": 142.5, # Update: Mittelwert aus WD-5-029-20
        "Biomasse": 24.0      # Update: Fraunhofer ISE 2024
    },
    "co2_price": 55.0,        # Update: Preis 2025
    "co2_emission_factors": {
        "Erdgas": 0.198,
        "Biomasse": 0.0,
        "Wasserstoff": 0.0
    }
}