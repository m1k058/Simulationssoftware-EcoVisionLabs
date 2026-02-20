"""Geteilte constants für EcoVision."""

GLOBAL = {
    "logo_path": "assets/logo.png",
    "icon_path": "assets/icon.png",
}

HEATPUMP_LOAD_PROFILE_NAME = "Wärmepumpen Lastprofile"

# Energie Quellen Namen, Shortcodes und Farben + Gruppierung
ENERGY_SOURCES = {
    "KE": {"name": "Kernenergie", "color": "#800080", "colname": "Kernenergie [MWh]", "colname_MW": "Kernenergie [MW]"},
    "BK": {"name": "Braunkohle", "color": "#774400", "colname": "Braunkohle [MWh]", "colname_MW": "Braunkohle [MW]"},
    "SK": {"name": "Steinkohle", "color": "#1F1F1F", "colname": "Steinkohle [MWh]", "colname_MW": "Steinkohle [MW]"},
    "EG": {"name": "Erdgas", "color": "#5D5D5D", "colname": "Erdgas [MWh]", "colname_MW": "Erdgas [MW]"},
    "SOE": {"name": "Sonstige Erneuerbare", "color": "#ADFF2F", "colname": "Sonstige Erneuerbare [MWh]", "colname_MW": "Sonstige Erneuerbare [MW]"},
    "SOK": {"name": "Sonstige Konventionelle", "color": "#272727", "colname": "Sonstige Konventionelle [MWh]", "colname_MW": "Sonstige Konventionelle [MW]"},
    "BIO": {"name": "Biomasse", "color": "#00A51B", "colname": "Biomasse [MWh]", "colname_MW": "Biomasse [MW]"},
    "PS": {"name": "Pumpspeicher", "color": "#090085", "colname": "Pumpspeicher [MWh]", "colname_MW": "Pumpspeicher [MW]"},
    "BS": {"name": "Batteriespeicher", "color": "#FF4500", "colname": "Batteriespeicher [MWh]", "colname_MW": "Batteriespeicher [MW]"},
    "WSS": {"name": "Wasserstoffspeicher", "color": "#00FCBD", "colname": "Wasserstoffspeicher [MWh]", "colname_MW": "Wasserstoffspeicher [MW]"},
    "WAS": {"name": "Wasserkraft", "color": "#1E90FF", "colname": "Wasserkraft [MWh]", "colname_MW": "Wasserkraft [MW]"},
    "WOF": {"name": "Wind Offshore", "color": "#0040FF", "colname": "Wind Offshore [MWh]", "colname_MW": "Wind Offshore [MW]"},
    "WON": {"name": "Wind Onshore", "color": "#55C6FF", "colname": "Wind Onshore [MWh]", "colname_MW": "Wind Onshore [MW]"},
    "PV": {"name": "Photovoltaik", "color": "#FFD700", "colname": "Photovoltaik [MWh]", "colname_MW": "Photovoltaik [MW]"},
}

SOURCES_GROUPS = {
    "Renewable": ["BIO", "WAS", "WOF", "WON", "PV", "SOE"],
    "Conventional": ["KE", "BK", "SK", "EG", "SOK"],
    "Storage": ["PS", "BS", "WSS"],
    "All": ["KE", "BK", "SK", "EG", "SOK", "SOE", "BIO", "PS", "WAS", "WOF", "WON", "PV"]
}

# Festgelegte Simulationseinstellungen
SIMULATION_SETTINGS = {
    "GENERATION_PARAMS": {
        "optimal_reference_years_by_technology": {
            "Wind Onshore": {
                "good": 2023,
                "average": 2015,
                "bad": 2016
            },            
            "Wind Offshore": {
                "good": 2020,
                "average": 2022,
                "bad": 2023
            },
            "Photovoltaik": {
                "good": 2022,
                "average": 2015,
                "bad": 2024
            },
            "default": 2022
        }
    },

    "EV_PARAMS": {
        "SOC0": 0.6,
        "eta_ch": 0.95,
        "eta_dis": 0.95,
        "P_ch_car_max": 11.0,
        "P_dis_car_max": 11.0,
        "dt_h": 0.25
    },

    "HEATPUMP_PARAMS": {
        "LOAD_PROFILE_NAME": "Wärmepumpen Lastprofile"
    },

    "ECONOMY_PARAMS": {

        # Investitions- und Betriebskosten der Technologien (Capex in EUR/kW, Opex in EUR/Jahr oder EUR/MWh)
        "TECHNOLOGY_COSTS": {
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
                "capex": [0, 0],
                "opex_fix": 15000,
                "opex_var": 0.0,
                "lifetime": 60,
                "efficiency": 0.90,
                "fuel_type": None
            },

            # --- SPEICHER ---
            "Elektrolyseur": {
                # IEA 2024
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
                "capex": [10000, 20000],
                "opex_fix": 5000,
                "opex_var": 0.0,
                "lifetime": 30,
                "efficiency": 1.0, 
                "fuel_type": None
            },
            "Pumpspeicher": {
                "capex": [1200000, 3000000],
                "opex_fix": 75000,
                "opex_var": 0.0,
                "lifetime": 60,
                "efficiency": 0.85,
                "fuel_type": None
            }
        },

        # Rohstoffpreise (Variable Kosten)
        "COMMODITIES": {
            "Erdgas": 35.0,        # EUR/MWh_th
            "Biomasse": 24.0,      # EUR/MWh_th
            "Wasserstoff": 142.50, # EUR/MWh_th (Import/Mix)
            "co2_price": 120.0     # EUR/t (Prognose 2030+)
        },

        # Andere wirtschaftliche Parameter
        "wacc": 0.05,           # Diskontierungszinssatz
    }

}

# Datenquellen und -pfade
DATA_SOURCES = [
    {
            "id": 0,
            "name": "SMARD_2015-2019_Erzeugung",
            "path": "raw-data/Realisierte_Erzeugung_2015-2019.csv",
            "datatype": "SMARD-gen",
            "description": "Daten für Stromerzeugung verschiedener Quellen 2015-2019"
        },
        {
            "id": 1,
            "name": "SMARD_2020-2025_Erzeugung",
            "path": "raw-data/Realisierte_Erzeugung_2020-2025.csv",
            "datatype": "SMARD-gen",
            "description": "Daten für Stromerzeugung verschiedener Quellen 2020-heute"
        },
        {
            "id": 2,
            "name": "SMARD_2015-2019_Verbrauch",
            "path": "raw-data/Realisierter_Stromverbrauch_2015-2019.csv",
            "datatype": "SMARD-con",
            "description": "Daten für realisierten Stromverbrauch verschiedener Quellen 2015-2019"
        },
        {
            "id": 3,
            "name": "SMARD_2020-2025_Verbrauch",
            "path": "raw-data/Realisierter_Stromverbrauch_2020-2025.csv",
            "datatype": "SMARD-con",
            "description": "Daten für realisierten Stromverbrauch verschiedener Quellen 2020-heute"
        },
        {
            "id": 4,
            "name": "SMARD_Installierte Leistung 2015-2019",
            "path": "raw-data/Instalierte_Leistung_2015-2019.csv",
            "datatype": "SMARD-inst",
            "description": "Daten für installierte Leistung verschiedener Quellen 2015-2019"
        },
        {
            "id": 5,
            "name": "SMARD_Installierte Leistung 2020-2025",
            "path": "raw-data/Instalierte_Leistung_2020-2025.csv",
            "datatype": "SMARD-inst",
            "description": "Daten für installierte Leistung verschiedener Quellen 2020-2025"
        },
        {
            "id": 6,
            "name": "Erzeugungs/Verbrauchs Prognose Daten",
            "path": "raw-data/Prognosedaten_Studien.csv",
            "datatype": "STUDY-prog",
            "description": "Daten für Erzeugungs- und Verbrauchsprognosen verschiedener Studien"
        },
        {
            "id": 7,
            "name": "Verbrauchsprofil Haushalte BDEW",
            "path": "raw-data/BDEW-Standardlastprofile-H25.csv",
            "datatype": "BDEW-Last",
            "description": "Verbrauchsprofil Haushalte BDEW"
        },
        {
            "id": 8,
            "name": "Verbrauchsprofil Gewerbe BDEW",
            "path": "raw-data/BDEW-Standardlastprofile-G25.csv",
            "datatype": "BDEW-Last",
            "description": "Verbrauchsprofil Gewerbe BDEW"
        },
        {
            "id": 9,
            "name": "Verbrauchsprofil Landwirtschaft BDEW",
            "path": "raw-data/BDEW-Standardlastprofile-L25.csv",
            "datatype": "BDEW-Last",
            "description": "Verbrauchsprofil Landwirtschaft BDEW"
        },
        {
            "id": 10,
            "name": "Wärmepumpen Lastprofile",
            "path": "raw-data/Waermepumpen-Standartlastprofile.csv",
            "datatype": "WP-Last",
            "description": "Standartlastprofile für Wärmepumpen"
        },
        {
            "id": 11,
            "name": "Lufttemperatur-2019",
            "path": "raw-data/Lufttemperatur-2019.csv",
            "datatype": "Temperature",
            "description": "Lufttemperaturdaten für das Jahr 2019"
        },
        {
            "id": 12,
            "name": "Lufttemperatur-2021",
            "path": "raw-data/Lufttemperatur-2021.csv",
            "datatype": "Temperature",
            "description": "Lufttemperaturdaten für das Jahr 2021"
        }
]

TECHNOLOGY_COSTS = {
    "Erdgas": {
        "capex": [450000, 700000],
        "opex_fix": 23000,
        "opex_var": 4.0,
        "lifetime": 30,
        "efficiency": 0.40,
        "fuel_type": "Erdgas"
    },
    "Biomasse": {
        "capex": [3470000, 5790000],
        "opex_fix": 185000,
        "opex_var": 4.0,
        "lifetime": 25,
        "efficiency": 0.45,
        "fuel_type": "Biomasse"
    },
    "H2_Elektrifizierung": {
        "capex": [550000, 1200000],
        "opex_fix": 23000,
        "opex_var": 5.0,
        "lifetime": 30,
        "efficiency": 0.40,
        "fuel_type": "Wasserstoff"
    },
    "Wind Onshore": {
        "capex": [1300000, 1900000],
        "opex_fix": 32000,
        "opex_var": 7.0,
        "lifetime": 25,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Wind Offshore": {
        "capex": [2200000, 3400000],
        "opex_fix": 39000,
        "opex_var": 8.0,
        "lifetime": 25,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Photovoltaik": {
        "capex": [700000, 900000],
        "opex_fix": 13300,
        "opex_var": 0.0,
        "lifetime": 30,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Wasserkraft": {
        "capex": [0, 0],
        "opex_fix": 15000,
        "opex_var": 0.0,
        "lifetime": 60,
        "efficiency": 0.90,
        "fuel_type": None
    },
    "Elektrolyseur": {
        "capex": [1800000, 2400000],
        "opex_fix": 36000,
        "opex_var": 0.0,
        "lifetime": 20,
        "efficiency": 0.68,
        "fuel_type": None
    },
    "Batteriespeicher": {
        "capex": [400000, 600000],
        "opex_fix": 10000,
        "opex_var": 0.0,
        "lifetime": 15,
        "efficiency": 0.92,
        "fuel_type": None
    },
    "Wasserstoffspeicher": {
        "capex": [10000, 20000],
        "opex_fix": 5000,
        "opex_var": 0.0,
        "lifetime": 30,
        "efficiency": 1.0,
        "fuel_type": None
    },
    "Pumpspeicher": {
        "capex": [1200000, 3000000],
        "opex_fix": 75000,
        "opex_var": 0.0,
        "lifetime": 60,
        "efficiency": 0.85,
        "fuel_type": None
    },
}

COMMODITIES = {
    "Erdgas": 35.0,
    "Biomasse": 24.0,
    "Wasserstoff": 142.50,
    "co2_price": 120.0,
}

ECONOMICS_CONSTANTS = {
    "global_parameter": {
        "wacc": 0.05
    },
    "source_specific": TECHNOLOGY_COSTS,
    "commodities": COMMODITIES,
}

COLUMN_NAMES = {
    "ZEITPUNKT": "Zeitpunkt",
    "BILANZ": "Bilanz [MWh]",
    "REST_BILANZ": "Rest Bilanz [MWh]",
    "PRODUKTION": "Produktion [MWh]",
    "VERBRAUCH": "Verbrauch [MWh]",
    "GESAMT_VERBRAUCH": "Gesamt [MWh]",
    "HAUSHALTE": "Haushalte [MWh]",
    "GEWERBE": "Gewerbe [MWh]",
    "LANDWIRTSCHAFT": "Landwirtschaft [MWh]",
    "WAERMEPUMPEN": "Wärmepumpen [MWh]",
    "EMOBILITY": "E-Mobility [MWh]",
    "BATTERIE_SOC": "Batteriespeicher SOC MWh",
    "BATTERIE_GELADEN": "Batteriespeicher Geladene MWh",
    "BATTERIE_ENTLADEN": "Batteriespeicher Entladene MWh",
    "PUMP_SOC": "Pumpspeicher SOC MWh",
    "PUMP_GELADEN": "Pumpspeicher Geladene MWh",
    "PUMP_ENTLADEN": "Pumpspeicher Entladene MWh",
    "H2_SOC": "Wasserstoffspeicher SOC MWh",
    "H2_GELADEN": "Wasserstoffspeicher Geladene MWh",
    "H2_ENTLADEN": "Wasserstoffspeicher Entladene MWh",
    "EV_SOC": "Fleet SOC [MWh]",
    "EV_DISPATCH": "Dispatch [MW]",
    "EV_FAHRVERBRAUCH": "Fahrverbrauch [MWh]",
    "EV_LADEVERLUSTE": "Ladeverluste [MWh]",
    "EV_GESAMT": "Gesamt Verbrauch [MWh]",
}
