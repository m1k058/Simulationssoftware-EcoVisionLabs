import streamlit as st
from pathlib import Path
import pandas as pd
from scenario_manager import ScenarioManager


LOAD_PROFILE_OPTIONS = [
    "2025-BDEW"
]

GEN_SOURCES = ["SMARD"]
TIME_RES_OPTIONS = ["15min"]


def ensure_state(sm: ScenarioManager) -> None:
    """Initialisiert den Editor-Status mit Default-Werten."""
    if "scenario_editor" not in st.session_state:
        st.session_state["scenario_editor"] = sm.default_template()


def _show_year_modal() -> list:
    """Modal zur Jahreseingabe - blockiert den Rest der Seite."""
    if "years_confirmed" not in st.session_state:
        st.session_state["years_confirmed"] = False
    
    if not st.session_state["years_confirmed"]:
        with st.container():
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("## :material/date_range: Jahre auswählen")
                st.markdown("Bitte geben Sie die Jahre ein, für die das Szenario gelten soll.")
                
                available_years = list(range(2020, 2051))
                default_years = [2030, 2045]
                
                selected_years = st.multiselect(
                    "Verfügbare Jahre (2020-2050)",
                    options=available_years,
                    default=default_years,
                    help="Wählen Sie aus der Liste oder geben Sie Jahre ein.",
                    key="modal_years_select"
                )
                
                extra_years_text = st.text_input(
                    "Weitere Jahre (kommagetrennt)",
                    value="",
                    placeholder="z.B. 2055, 2060, 2070",
                    help="Für Jahre außerhalb der Liste (2020-2050)",
                    key="modal_years_extra"
                )
                
                parsed_extra_years = []
                if extra_years_text.strip():
                    for part in extra_years_text.replace(";", ",").split(","):
                        part = part.strip()
                        if not part:
                            continue
                        try:
                            parsed_extra_years.append(int(part))
                        except ValueError:
                            pass
                
                valid_years = sorted(set(selected_years + parsed_extra_years)) or [2030, 2045]
                
                st.markdown(f"**Aktivierte Jahre:** {', '.join(map(str, valid_years))}")
                
                if st.button("✅ Jahre bestätigen", use_container_width=True, key="confirm_years"):
                    st.session_state["years_confirmed"] = True
                    st.session_state["valid_years"] = valid_years
                    st.rerun()
            
            st.markdown("---")
        st.stop()  # Seitenladevorgang stoppen, bis Jahre bestätigt sind
    
    return st.session_state.get("valid_years", [2030, 2045])


def scenario_generation_page() -> None:
    st.title("Szenario Editor :material/edit_note:")
    st.caption("Szenarien erstellen und als YAML herunterladen.")

    sm = ScenarioManager()
    ensure_state(sm)

    # === MODAL: JAHRE ZUERST ABFRAGEN ===
    valid_years = _show_year_modal()

    # Schneller Reset auf die Beispielwerte aus der Vorlage
    if st.button(":material/lab_profile: Beispielwerte laden", use_container_width=True):
        st.session_state["scenario_editor"] = sm.default_template()
        st.session_state.pop("storage_values", None)
        st.rerun()

    data = st.session_state["scenario_editor"]

    # === METADATEN ===
    st.subheader("Metadaten")
    name = st.text_input("Name", value=data.get("metadata", {}).get("name", ""))
    description = st.text_area("Beschreibung", value=data.get("metadata", {}).get("description", ""), height=80)
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        version = st.text_input("Version", value=str(data.get("metadata", {}).get("version", "1.0")))
    with col_meta2:
        author = st.text_input("Autor", value=str(data.get("metadata", {}).get("author", "SW-Team EcoVisionLabs")))

    st.markdown("---")

    # === LASTPROFIL ===
    st.subheader("Last (Verbrauch) - pro Sektor")
    load_params = data.get("target_load_demand_twh", {})
    
    # Sektoren definieren
    sectors = {
        "Haushalt_Basis": "Haushalte (Standardlastprofil)",
        "Gewerbe_Basis": "Gewerbe",
        "Landwirtschaft_Basis": "Landwirtschaft",
        "EMobility": "Elektromobilität",
        "Heat_Pumps": "Wärmepumpen (Gebäudewärme)",
    }
    
    target_load_demand_twh = {}
    for sector_key, sector_label in sectors.items():
        st.markdown(f"**{sector_label}**")
        sector_data = load_params.get(sector_key, {})
        load_profile = st.text_input(
            f"Lastprofil für {sector_key}",
            value=sector_data.get("load_profile", ""),
            key=f"lp_{sector_key}",
        )

        demand_cols = st.columns(len(valid_years) if valid_years else 2)
        sector_demands = {}
        for idx, year in enumerate(valid_years if valid_years else [2030, 2045]):
            with demand_cols[idx]:
                demand_val = sector_data.get(year, 0.0)
                sector_demands[year] = st.number_input(
                    f"TWh ({year})",
                    value=float(demand_val),
                    step=10.0,
                    key=f"demand_{sector_key}_{year}",
                )

        target_load_demand_twh[sector_key] = {"load_profile": load_profile, **sector_demands}

    st.markdown("---")

    # === ZIEL-KAPAZITÄTEN ===
    st.subheader("Ziel-Kapazitäten [MW]")
    
    years_to_show = valid_years if valid_years else [2030, 2045]
    
    # Standard-Technologien definieren
    default_techs = [
        "Photovoltaik", "Wind_Onshore", "Wind_Offshore", "Biomasse",
        "Wasserkraft", "Erdgas", "Steinkohle", "Braunkohle", "Kernenergie"
    ]
    
    # Initialisiere cap_values in session_state
    if "cap_values" not in st.session_state:
        st.session_state["cap_values"] = {}
        for y in years_to_show:
            st.session_state["cap_values"][y] = {tech: 0.0 for tech in default_techs}
    
    # Stelle sicher, dass neue Jahre auch Einträge haben
    for y in years_to_show:
        if y not in st.session_state["cap_values"]:
            st.session_state["cap_values"][y] = {tech: 0.0 for tech in default_techs}
    
    
    
    # Header-Zeile (Jahre)
    header_cols = st.columns([2] + [1.5] * len(years_to_show))
    header_cols[0].write("**Technologie**")
    for idx, year in enumerate(years_to_show):
        header_cols[idx + 1].write(f"**{year}**")
    
    # Daten-Zeilen (Technologien)
    for tech in default_techs:
        row_cols = st.columns([2] + [1.5] * len(years_to_show))
        row_cols[0].write(f"**{tech} [MW]**")
        for idx, year in enumerate(years_to_show):
            st.session_state["cap_values"][year][tech] = row_cols[idx + 1].number_input(
                f"{tech}_{year}",
                value=st.session_state["cap_values"][year].get(tech, 0.0),
                step=1000.0,
                label_visibility="collapsed",
                key=f"cap_{year}_{tech}"
            )
    
    # Konvertiere für später (altes Format)
    rows = []
    for y in years_to_show:
        row = {"Jahr": int(y)}
        for tech in default_techs:
            row[tech] = st.session_state["cap_values"][y].get(tech, 0.0)
        rows.append(row)
    edited_cap = pd.DataFrame(rows)
    
    st.markdown("---")

    # === WETTERPROFILE ===
    st.subheader("Wetterprofile für erneuerbare Energien")
    weather_gen_profiles = data.get("weather_generation_profiles", {})
    weather_options = ["good", "average", "bad"]
    edited_weather = {}
    for year in valid_years if valid_years else [2030, 2045]:
        st.markdown(f"**Jahr {year}**")
        year_weather = weather_gen_profiles.get(year, {})
        col1, col2, col3 = st.columns(3)
        with col1:
            edited_weather[year] = {
                "Wind_Onshore": st.selectbox(
                    "Wind Onshore",
                    options=weather_options,
                    index=weather_options.index(year_weather.get("Wind_Onshore", "average")) if year_weather else 1,
                    key=f"weather_onshore_{year}",
                ),
            }
        with col2:
            edited_weather[year]["Wind_Offshore"] = st.selectbox(
                "Wind Offshore",
                options=weather_options,
                index=weather_options.index(year_weather.get("Wind_Offshore", "average")) if year_weather else 1,
                key=f"weather_offshore_{year}",
            )
        with col3:
            edited_weather[year]["Photovoltaik"] = st.selectbox(
                "Photovoltaik",
                options=weather_options,
                index=weather_options.index(year_weather.get("Photovoltaik", "average")) if year_weather else 1,
                key=f"weather_pv_{year}",
            )

    st.markdown("---")

    # === SPEICHER ===
    st.subheader(":material/battery_profile: Speicher")
    storage_caps = data.get("target_storage_capacities", {})
    storage_types = {
        "battery_storage": ":material/battery_charging_90: Batteriespeicher (Kurzzeitspeicher)",
        "pumped_hydro_storage": ":material/water_pump: Pumpspeicherkraftwerke",
        "h2_storage": ":material/format_h2: Wasserstoff-Speicher",
    }

    if "storage_values" not in st.session_state:
        st.session_state["storage_values"] = {}
        for stor_key in storage_types.keys():
            st.session_state["storage_values"][stor_key] = storage_caps.get(stor_key, {}).copy()

    # Stelle sicher, dass neue Jahre auch Default-Werte bekommen
    for stor_key in storage_types.keys():
        st.session_state["storage_values"].setdefault(stor_key, {})
        for y in valid_years:
            st.session_state["storage_values"][stor_key].setdefault(y, {
                "installed_capacity_mwh": 0.0,
                "max_charge_power_mw": 0.0,
                "max_discharge_power_mw": 0.0,
                "initial_soc": 0.5,
            })

    target_storage_capacities = {}
    for stor_key, stor_label in storage_types.items():
        st.markdown(f"**{stor_label}**")
        years_list = valid_years if valid_years else [2030, 2045]
        
        # Tabs für jedes Jahr
        tabs = st.tabs([str(year) for year in years_list])
        
        for tab_idx, (tab, year) in enumerate(zip(tabs, years_list)):
            with tab:
                year_config = st.session_state["storage_values"][stor_key].get(year, {})

                c1, c2, c3 = st.columns(3)
                with c1:
                    cap_val = st.number_input(
                        f"Kapazität [MWh]",
                        value=float(year_config.get("installed_capacity_mwh", 0)),
                        step=1000.0,
                        key=f"stor_{stor_key}_{year}_cap",
                    )
                with c2:
                    charge_val = st.number_input(
                        f"Ladeleistung [MW]",
                        value=float(year_config.get("max_charge_power_mw", 0)),
                        step=1000.0,
                        key=f"stor_{stor_key}_{year}_charge",
                    )
                with c3:
                    discharge_val = st.number_input(
                        f"Entladeleistung [MW]",
                        value=float(year_config.get("max_discharge_power_mw", 0)),
                        step=1000.0,
                        key=f"stor_{stor_key}_{year}_discharge",
                    )

                soc_val = st.slider(
                    f"Initial SOC",
                    0.0, 1.0,
                    value=float(year_config.get("initial_soc", 0.5)),
                    step=0.05,
                    key=f"stor_{stor_key}_{year}_soc",
                )

                st.session_state["storage_values"][stor_key][year] = {
                    "installed_capacity_mwh": cap_val,
                    "max_charge_power_mw": charge_val,
                    "max_discharge_power_mw": discharge_val,
                    "initial_soc": soc_val,
                }

        target_storage_capacities[stor_key] = {
            year: vals
            for year, vals in st.session_state["storage_values"][stor_key].items()
            if year in valid_years
        }

    # === NEU: KONSUM-STRATEGIEN (E-MOBILITÄT V2G) ===
    st.subheader("Konsum-Strategien / E-Mobilität (V2G)")
    emob = data.get("consumption_strategies", {}).get("emobility_v2g", {})
    
    col_v2g_main, col_v2g_params = st.columns([1, 2])
    with col_v2g_main:
        emob_active = st.checkbox("V2G Aktivieren", value=emob.get("active", True), key="emob_active")
        n_cars_base = int(emob.get(2030, {}).get("n_cars", 5000000)) # Fallback
    
    with col_v2g_params:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            bat_kwh = st.number_input("Batterie [kWh]", value=float(emob.get("battery_capacity_kwh", 50.0)), step=1.0)
            chg_kw = st.number_input("Ladeleistung [kW]", value=float(emob.get("charging_power_kw", 11.0)), step=1.0)
        with col_p2:
            eff = st.number_input("Effizienz (0-1)", value=float(emob.get("efficiency", 0.95)), step=0.01, max_value=1.0)
            
        st.markdown("**Flottengröße (Anzahl E-Autos)**")
        fleet_dict_ui = {}
        fl_cols = st.columns(len(years_to_show))
        for idx, year in enumerate(years_to_show):
            with fl_cols[idx]:
                # Hole Wert aus YAML (direkter Key oder nested in Year dict)
                val_y = emob.get(year, {}).get("n_cars", 0)
                if val_y == 0 and year == 2030: val_y = 5000000
                if val_y == 0 and year == 2045: val_y = 10000000 # Default Logik
                
                fleet_val = st.number_input(f"Anzahl {year}", value=int(val_y), step=100000, key=f"emob_cars_{year}")
                fleet_dict_ui[year] = {"n_cars": fleet_val}
    
    # Erweiterte Einstellungen (SOC Limits & Grid Thresholds)
    with st.expander("Erweiterte V2G-Parameter (SOC & Netzgrenzen)"):
        c_soc, c_grid = st.columns(2)
        
        # 1. SOC Limits
        limits = emob.get("soc_limits", {})
        with c_soc:
            st.markdown("**SOC Grenzen (Anteil 0-1)**")
            
            soc_min_day = st.number_input("Min SOC Tag (06-22h)", 
                                        value=float(limits.get("min_day", 0.4)), 
                                        step=0.05, min_value=0.0, max_value=1.0)
                                        
            soc_min_night = st.number_input("Min SOC Nacht (22-06h)", 
                                          value=float(limits.get("min_night", 0.2)), 
                                          step=0.05, min_value=0.0, max_value=1.0)
                                          
            soc_target_morn = st.number_input("Ziel SOC Morgen (07:30)", 
                                            value=float(limits.get("target_morning", 0.6)), 
                                            step=0.05, min_value=0.0, max_value=1.0)

        # 2. Grid Thresholds
        thresholds = emob.get("grid_thresholds_mw", {})
        with c_grid:
            st.markdown("**Netzschwellwerte [MW]**")
            st.caption("Ab wann soll reagiert werden?")
            
            # Surplus ist negativ in der Bilanz (z.B. -200 MW heißt 200 MW zu viel im Netz die wir rausholen)
            # Oder ist Surplus positiv? In simulation.py: 
            # GRID_UPPER_THRESHOLD = 200.0 (Überschuss -> Laden) 
            # GRID_LOWER_THRESHOLD = -200.0 (Defizit -> Entladen)
            # Moment. Üblicherweise ist positive Load ein Verbrauch.
            # In simulation.py steht: 
            # "df_balance['Rest Bilanz [MWh]'] (positiv = Überschuss, negativ = Defizit)" in simulate_emobility_fleet docstring.
            # Aber weiter unten: 
            #     if grid_val > GRID_UPPER_THRESHOLD: # Überschuss -> Laden
            # Heißt: Positiv = Überschuss.
            
            # In der Excel extract logic: surplus = -200.0. 
            # Das war evtl. verwirrend.
            # Wenn Positiv = Überschuss, dann sollte Threshold Positiv sein.
            
            # User Input: Ab welchem Überschuss [MW] laden?
            thr_surplus_val = thresholds.get("surplus", 200.0) 
            # Falls im Config negativ gespeichert war (wegen alter Logik), nehmen wir abs() für UI
            
            thr_load = st.number_input("Lade-Start bei Überschuss > [MW]", 
                                     value=float(abs(thr_surplus_val)), 
                                     step=50.0)
            
            # User Input: Ab welchem Defizit [MW] entladen?
            thr_deficit_val = thresholds.get("deficit", -200.0)
            
            thr_unload = st.number_input("Entlade-Start bei Defizit > [MW]", 
                                       value=float(abs(thr_deficit_val)), 
                                       step=50.0)
            st.caption("Wert wird als negative Schwelle für Defizit genutzt.")

    
    emob_v2g_config = {
        "active": emob_active,
        "battery_capacity_kwh": bat_kwh,
        "charging_power_kw": chg_kw,
        "efficiency": eff,
        "soc_limits": {
            "min_day": soc_min_day,
            "min_night": soc_min_night,
            "target_morning": soc_target_morn
        },
        "grid_thresholds_mw": {
            "surplus": thr_load,      # Positiv für Überschuss-Trigger (> 200)
            "deficit": -thr_unload    # Negativ für Defizit-Trigger (< -200)
        },
        **fleet_dict_ui 
    }

    # === LIVE ZUSAMMENFASSUNG IN SESSION STATE ===
    tech_list = [c for c in edited_cap.columns if c != "Jahr"]
    target_generation_capacities_mw = {tech: {} for tech in tech_list}
    for _, row in edited_cap.iterrows():
        try:
            year_val = int(row.get("Jahr"))
        except (ValueError, TypeError):
            continue
        for tech in tech_list:
            try:
                target_generation_capacities_mw.setdefault(tech, {})[year_val] = float(row.get(tech, 0.0))
            except (ValueError, TypeError):
                pass

    weather_generation_profiles_dict = {
        year: {
            "Wind_Onshore": edited_weather[year].get("Wind_Onshore", "average"),
            "Wind_Offshore": edited_weather[year].get("Wind_Offshore", "average"),
            "Photovoltaik": edited_weather[year].get("Photovoltaik", "average"),
        }
        for year in edited_weather
    }

    st.session_state["scenario_editor"] = {
        "metadata": {
            "name": name,
            "description": description,
            "valid_for_years": valid_years,
            "version": version,
            "author": author,
        },
        "target_load_demand_twh": target_load_demand_twh,
        "target_generation_capacities_mw": target_generation_capacities_mw,
        "weather_generation_profiles": weather_generation_profiles_dict,
        "target_storage_capacities": target_storage_capacities,
        "consumption_strategies": {
            "emobility_v2g": emob_v2g_config
        }
    }

    st.success("Daten aktualisiert - YAML immer aktuell.")

    # === GROSSER DOWNLOAD BUTTON AM ENDE ===
    st.markdown("---")
    st.markdown("")
    
    yaml_output = sm.create_scenario_yaml(st.session_state["scenario_editor"])
    scenario_name = st.session_state['scenario_editor'].get('metadata', {}).get('name', 'szenario')
    scenario_version = st.session_state['scenario_editor'].get('metadata', {}).get('version', '1.0')
    
    col_empty1, col_button, col_empty2 = st.columns([1, 2, 1])
    with col_button:
        st.download_button(
            ":material/refresh: YAML GENERIEREN & :material/download: HERUNTERLADEN",
            data=yaml_output,
            file_name=f"{scenario_name}_{scenario_version}.yaml",
            mime="text/yaml",
            use_container_width=True,
            key="final_download"
        )
    
    col_empty1, col_preview, col_empty2 = st.columns([1, 2, 1])
    with col_preview:
        if st.button(":material/preview: YAML-Vorschau anzeigen", use_container_width=True):
            st.session_state["show_yaml_preview"] = not st.session_state.get("show_yaml_preview", False)
    
    if st.session_state.get("show_yaml_preview", False):
        st.markdown("---")
        st.markdown("### 📋 YAML-Vorschau")
        st.code(yaml_output, language="yaml")
    

    # Neustart-Button: Jahre erneut abfragen und State leeren
    col_empty1, col_preview, col_empty2 = st.columns([1, 2, 1])
    if col_preview.button("RESET", use_container_width=True):
        reset_keys = [
            "years_confirmed",
            "valid_years",
            "modal_years_select",
            "modal_years_extra",
            "cap_values",
            "cap_df_session",
            "storage_values",
            "scenario_editor",
            "show_yaml_preview",
        ]
        for key in reset_keys:
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("")

