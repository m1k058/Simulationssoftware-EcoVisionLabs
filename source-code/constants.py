
# Konstanten für Verbrauchssimulation
HEATPUMP_LOAD_PROFILE_NAME = "Wärmepumpen Lastprofile"

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
    "WP-Last": [
        "Zeitpunkt", "LOW", "-13", "-12", "-11", "-10",
        "-9", "-8", "-7", "-6", "-5", "-4", "-3", "-2",
        "-1", "0", "1", "2", "3", "4", "5", "6", "7",
        "8", "9", "10", "11", "12", "13", "14", "15",
        "16", "17", "HIGH"
    ],
    "Temperature": [
        "Zeitpunkt", "AVERAGE", "Berlin", "Chemnitz", "Diepholz", "Frankfurt/Main",
        "Hamburg", "München", "Villingen-Schwenningen", "Itzehoe"
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
    "WP-Last": {
        "sep": "\t",
        "decimal": ",",
        "thousands": ".",
        "date_format": "%d.%m.%Y %H:%M",
        "encoding": "utf-8",
        "na_values": ["-", "NaN", "n/a", ""]
    },
    "Temperature": {
        "sep": ";",
        "decimal": ",",
        "thousands": ".",
        "date_format": "%d.%m.%Y %H:%M",
        "encoding": "cp1252",
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

# ECONOMICS_CONSTANTS basierend auf Fraunhofer ISE 2024 & EWI Analyse

TECHNOLOGY_COSTS = {
    # --- THERMISCHE KRAFTWERKE ---
    "Erdgas": {
        # Fraunhofer ISE: GT (450-700 EUR/kW) -> MW
        "capex": [450000, 700000],
        "opex_fix": 23000,
        "opex_var": 4.0,       # EUR/MWh (zzgl. Brennstoff!)
        "lifetime": 30,
        "efficiency": 0.40,
        "fuel_type": "Erdgas"
    },
    "Biomasse": {
        # Fraunhofer ISE: Feste Biomasse (3473-5788 EUR/kW)
        "capex": [3470000, 5790000], 
        "opex_fix": 185000,    # Hohe Betriebskosten
        "opex_var": 4.0,
        "lifetime": 25,
        "efficiency": 0.45,
        "fuel_type": "Biomasse"
    },
    "H2_Elektrifizierung": {
        # Annahme: H2-Ready Gasturbine
        "capex": [550000, 1200000],
        "opex_fix": 23000,
        "opex_var": 5.0,
        "lifetime": 30,
        "efficiency": 0.40,
        "fuel_type": "Wasserstoff"
    },

    # --- ERNEUERBARE ---
    "Wind Onshore": {
        # Fraunhofer ISE (1300-1900 EUR/kW)
        "capex": [1300000, 1900000],
        "opex_fix": 32000,
        "opex_var": 7.0,
        "lifetime": 25,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Wind Offshore": {
        # Fraunhofer ISE (2200-3400 EUR/kW)
        "capex": [2200000, 3400000],
        "opex_fix": 39000,
        "opex_var": 8.0,
        "lifetime": 25,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Photovoltaik": {
        # Fraunhofer ISE (700-900 EUR/kW)
        "capex": [700000, 900000],
        "opex_fix": 13300,
        "opex_var": 0.0,
        "lifetime": 30,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Wasserkraft": {
        # Bestandsschutz (Invest abgeschrieben = 0)
        "capex": [0, 0],
        "opex_fix": 15000,
        "opex_var": 0.0,
        "lifetime": 60,
        "efficiency": 0.90,
        "fuel_type": None
    },

    # --- SPEICHER & P2G ---
    "Elektrolyseur": {
        # IEA 2024 Anpassung
        "capex": [1800000, 2400000],
        "opex_fix": 36000,
        "opex_var": 0.0,
        "lifetime": 20,
        "efficiency": 0.68,
        "fuel_type": None
    },
    "Batteriespeicher": {
        # Fraunhofer ISE (400-600 EUR/kWh Kapazität)
        "capex": [400000, 600000],
        "opex_fix": 10000,
        "opex_var": 0.0,
        "lifetime": 15,
        "efficiency": 0.92,
        "fuel_type": None
    },
    "Wasserstoffspeicher": {
        # EWI Rückrechnung (siehe Doku)
        "capex": [400000, 600000],
        "opex_fix": 5000,
        "opex_var": 0.0,
        "lifetime": 30,
        "efficiency": 1.0, 
        "fuel_type": None
    },
    "Pumpspeicher": {
        # Wuppertal Inst. (Teuer bei Neubau)
        "capex": [1200000, 3000000],
        "opex_fix": 75000,
        "opex_var": 0.0,
        "lifetime": 60,
        "efficiency": 0.85,
        "fuel_type": None
    }
}

# --- ROHSTOFFPREISE (Variable Kosten) ---
COMMODITIES = {
    "Erdgas": 35.0,        # EUR/MWh_th
    "Biomasse": 24.0,      # EUR/MWh_th
    "Wasserstoff": 142.50, # EUR/MWh_th (Import/Mix)
    "co2_price": 120.0     # EUR/t (Prognose 2030+)
}

ECONOMICS_CONSTANTS = {
    "global_parameter": {
        "wacc": 0.05
    },
    "source_specific": TECHNOLOGY_COSTS,
    "commodities": COMMODITIES
}