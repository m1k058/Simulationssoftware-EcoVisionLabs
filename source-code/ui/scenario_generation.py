import streamlit as st
from pathlib import Path
import pandas as pd
from scenario_manager import ScenarioManager
from config_manager import ConfigManager


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
                
                if st.button("✅ Jahre bestätigen", width='stretch', key="confirm_years"):
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
    if st.button(":material/lab_profile: Beispielwerte laden", width='stretch'):
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
    
    # Sektoren definieren (BDEW nur)
    sectors = {
        "Haushalt_Basis": "Haushalte (Standardlastprofil)",
        "Gewerbe_Basis": "Gewerbe",
        "Landwirtschaft_Basis": "Landwirtschaft",
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


    # === WÄRMEPUMPEN-PARAMETER (NEU) ===
    st.subheader("Wärmepumpen - Parameter")
    hp_params = data.get("target_heat_pump_parameters", {})
    edited_hp = {}
    
    # Verfügbare Temperature-Datasets laden
    if "cfg" not in st.session_state:
        st.session_state.cfg = ConfigManager()
    available_temps = ScenarioManager.get_available_temperature_datasets(st.session_state.cfg)
    
    for year in valid_years if valid_years else [2030, 2045]:
        st.markdown(f"**Jahr {year}**")
        year_hp = hp_params.get(year, {})
        
        hp_cols1 = st.columns(2)
        with hp_cols1[0]:
            edited_hp[year] = {
                "installed_units": st.number_input(
                    "Installierte WP (Stück)",
                    value=int(year_hp.get("installed_units", 3000000)),
                    step=100000,
                    key=f"hp_units_{year}",
                )
            }
        with hp_cols1[1]:
            edited_hp[year]["annual_heat_demand_kwh"] = st.number_input(
                "Wärmebedarf/WP [kWh/Jahr]",
                value=float(year_hp.get("annual_heat_demand_kwh", 51000)),
                step=1000.0,
                key=f"hp_heat_{year}",
            )
        hp_cols2 = st.columns(2)
        with hp_cols2[0]:
            edited_hp[year]["cop_avg"] = st.number_input(
                "COP (durchschn.)",
                value=float(year_hp.get("cop_avg", 3.4)),
                min_value=2.5,
                max_value=4.5,
                step=0.1,
                key=f"hp_cop_{year}",
            )
        with hp_cols2[1]:
            # Weather_data als Dropdown mit verfügbaren Temperature-Datasets
            current_weather = year_hp.get("weather_data", "Lufttemperatur-2019")
            default_idx = available_temps.index(current_weather) if current_weather in available_temps else 0
            edited_hp[year]["weather_data"] = st.selectbox(
                "Wetterdaten",
                options=available_temps,
                index=default_idx,
                key=f"hp_weather_{year}",
                help="Temperature-Dataset aus config.json"
            )
        
        # load_profile wird nicht mehr in YAML gespeichert (fix in constants.py)
    
    st.markdown("---")

    # === E-MOBILITÄT-PARAMETER (NEU) ===
    st.subheader(":material/directions_car: E-Mobilität - Parameter")
    em_params = data.get("target_emobility_parameters", {})
    edited_em = {}
    
    # Initialisiere E-Mobility Werte in session_state falls nicht vorhanden
    if "emobility_values" not in st.session_state:
        st.session_state["emobility_values"] = {}
        for y in valid_years if valid_years else [2030, 2045]:
            default_vals = em_params.get(y, {})
            st.session_state["emobility_values"][y] = {
                "s_EV": default_vals.get("s_EV", 0.7 if y == 2030 else 0.95),
                "N_cars": default_vals.get("N_cars", 48000000),
                "E_drive_car_year": default_vals.get("E_drive_car_year", 2250.0),
                "E_batt_car": default_vals.get("E_batt_car", 50.0),
                "plug_share_max": default_vals.get("plug_share_max", 0.6),
                "v2g_share": default_vals.get("v2g_share", 0.3),
                "SOC_min_day": default_vals.get("SOC_min_day", 0.4),
                "SOC_min_night": default_vals.get("SOC_min_night", 0.2),
                "SOC_target_depart": default_vals.get("SOC_target_depart", 0.6),
                "t_depart": default_vals.get("t_depart", "07:30"),
                "t_arrive": default_vals.get("t_arrive", "18:00"),
                "thr_surplus": default_vals.get("thr_surplus", 200000.0),
                "thr_deficit": default_vals.get("thr_deficit", 200000.0),
            }
    
    # Stelle sicher, dass neue Jahre auch Einträge haben
    for y in valid_years if valid_years else [2030, 2045]:
        if y not in st.session_state["emobility_values"]:
            st.session_state["emobility_values"][y] = {
                "s_EV": 0.7 if y <= 2030 else 0.95,
                "N_cars": 48000000,
                "E_drive_car_year": 2250.0,
                "E_batt_car": 50.0,
                "plug_share_max": 0.6,
                "v2g_share": 0.3,
                "SOC_min_day": 0.4,
                "SOC_min_night": 0.2,
                "SOC_target_depart": 0.6,
                "t_depart": "07:30",
                "t_arrive": "18:00",
                "thr_surplus": 200000.0,
                "thr_deficit": 200000.0,
            }
    
    # Tabs für jedes Jahr
    em_tabs = st.tabs([f"Jahr {year}" for year in (valid_years if valid_years else [2030, 2045])])
    
    for tab_idx, (tab, year) in enumerate(zip(em_tabs, valid_years if valid_years else [2030, 2045])):
        with tab:
            year_em = st.session_state["emobility_values"].get(year, {})
            
            # Hauptparameter
            st.markdown("**Flotten-Parameter**")
            em_col1, em_col2 = st.columns(2)
            with em_col1:
                s_ev_val = st.slider(
                    "Anteil E-Fahrzeuge",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(year_em.get("s_EV", 0.7)),
                    step=0.05,
                    key=f"em_s_ev_{year}",
                    help="Anteil der Fahrzeugflotte, die elektrisch ist (0.0 - 1.0)"
                )
                n_cars_val = st.number_input(
                    "Gesamtanzahl PKW",
                    min_value=0,
                    max_value=100000000,
                    value=int(year_em.get("N_cars", 48000000)),
                    step=1000000,
                    key=f"em_n_cars_{year}",
                    help="Gesamtzahl aller PKW in Deutschland"
                )
            with em_col2:
                e_drive_val = st.number_input(
                    "Jahresfahrverbrauch [kWh/Fzg]",
                    min_value=0.0,
                    max_value=10000.0,
                    value=float(year_em.get("E_drive_car_year", 2250.0)),
                    step=50.0,
                    key=f"em_e_drive_{year}",
                    help="Stromverbrauch pro E-Auto pro Jahr"
                )
                e_batt_val = st.number_input(
                    "Batteriekapazität [kWh/Fzg]",
                    min_value=10.0,
                    max_value=200.0,
                    value=float(year_em.get("E_batt_car", 50.0)),
                    step=5.0,
                    key=f"em_e_batt_{year}",
                    help="Durchschnittliche Batteriekapazität pro Fahrzeug"
                )
            
            # SOC Parameter
            st.markdown("**SOC-Grenzen**")
            soc_col1, soc_col2, soc_col3 = st.columns(3)
            with soc_col1:
                soc_min_day_val = st.slider(
                    "Min. SOC Tag",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(year_em.get("SOC_min_day", 0.4)),
                    step=0.05,
                    key=f"em_soc_min_day_{year}",
                    help="Minimaler SOC während Tageszeit"
                )
            with soc_col2:
                soc_min_night_val = st.slider(
                    "Min. SOC Nacht",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(year_em.get("SOC_min_night", 0.2)),
                    step=0.05,
                    key=f"em_soc_min_night_{year}",
                    help="Minimaler SOC während Nachtzeit"
                )
            with soc_col3:
                soc_target_val = st.slider(
                    "Ziel-SOC Abfahrt",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(year_em.get("SOC_target_depart", 0.6)),
                    step=0.05,
                    key=f"em_soc_target_{year}",
                    help="Ziel-SOC bei Abfahrt morgens"
                )
            
            # Erweiterte Einstellungen - Defaults initialisieren
            plug_share_val = float(year_em.get("plug_share_max", 0.6))
            v2g_share_val = float(year_em.get("v2g_share", 0.3))
            t_depart_val = str(year_em.get("t_depart", "07:30"))
            t_arrive_val = str(year_em.get("t_arrive", "18:00"))
            thr_surplus_mw = float(year_em.get("thr_surplus", 200000.0)) / 1000.0
            thr_deficit_mw = float(year_em.get("thr_deficit", 200000.0)) / 1000.0
            
            with st.expander("Erweiterte Einstellungen"):
                adv_col1, adv_col2 = st.columns(2)
                with adv_col1:
                    plug_share_val = st.slider(
                        "Max. Anschlussquote ",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(year_em.get("plug_share_max", 0.6)),
                        step=0.05,
                        key=f"em_plug_share_{year}",
                        help="Anteil der Fahrzeuge, die nachts am Netz angeschlossen sind"
                    )
                    v2g_share_val = st.slider(
                        "V2G-Teilnahmequote",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(year_em.get("v2g_share", 0.3)),
                        step=0.05,
                        key=f"em_v2g_share_{year}",
                        help="Anteil der angeschlossenen Fahrzeuge, deren Besitzer bereit sind, ins Netz zurückzuspeisen (V2G). Studien zeigen ca. 20-40% Bereitschaft."
                    )
                    t_depart_val = st.text_input(
                        "Abfahrtszeit",
                        value=str(year_em.get("t_depart", "07:30")),
                        key=f"em_t_depart_{year}",
                        help="Format: HH:MM"
                    )
                with adv_col2:
                    t_arrive_val = st.text_input(
                        "Ankunftszeit",
                        value=str(year_em.get("t_arrive", "18:00")),
                        key=f"em_t_arrive_{year}",
                        help="Format: HH:MM"
                    )
                
                # Netz-Schwellwerte
                st.markdown("**Netz-Dispatch Schwellwerte**")
                thr_col1, thr_col2 = st.columns(2)
                with thr_col1:
                    thr_surplus_mw = st.number_input(
                        "Schwellwert Überschuss [MW]",
                        min_value=0.0,
                        max_value=1000.0,
                        value=float(year_em.get("thr_surplus", 200000.0)) / 1000.0,
                        step=10.0,
                        key=f"em_thr_surplus_{year}",
                        help="Ab diesem Überschuss wird geladen"
                    )
                with thr_col2:
                    thr_deficit_mw = st.number_input(
                        "Schwellwert Defizit [MW]",
                        min_value=0.0,
                        max_value=1000.0,
                        value=float(year_em.get("thr_deficit", 200000.0)) / 1000.0,
                        step=10.0,
                        key=f"em_thr_deficit_{year}",
                        help="Ab diesem Defizit wird entladen"
                    )
            
            # Werte in Session State speichern
            st.session_state["emobility_values"][year] = {
                "s_EV": s_ev_val,
                "N_cars": n_cars_val,
                "E_drive_car_year": e_drive_val,
                "E_batt_car": e_batt_val,
                "plug_share_max": plug_share_val,
                "v2g_share": v2g_share_val,
                "SOC_min_day": soc_min_day_val,
                "SOC_min_night": soc_min_night_val,
                "SOC_target_depart": soc_target_val,
                "t_depart": t_depart_val,
                "t_arrive": t_arrive_val,
                "thr_surplus": thr_surplus_mw * 1000.0,  # Konvertiere MW zu kW
                "thr_deficit": thr_deficit_mw * 1000.0,  # Konvertiere MW zu kW
            }
    
    # E-Mobility Werte für Export zusammenstellen
    for year in valid_years if valid_years else [2030, 2045]:
        edited_em[year] = st.session_state["emobility_values"].get(year, {})

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

    
    
    st.markdown("---")
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
        "target_heat_pump_parameters": edited_hp,
        "target_emobility_parameters": edited_em,
        "target_generation_capacities_mw": target_generation_capacities_mw,
        "weather_generation_profiles": weather_generation_profiles_dict,
        "target_storage_capacities": target_storage_capacities,
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
            width='stretch',
            key="final_download"
        )
    
    col_empty1, col_preview, col_empty2 = st.columns([1, 2, 1])
    with col_preview:
        if st.button(":material/preview: YAML-Vorschau anzeigen", width='stretch'):
            st.session_state["show_yaml_preview"] = not st.session_state.get("show_yaml_preview", False)
    
    if st.session_state.get("show_yaml_preview", False):
        st.markdown("---")
        st.markdown("### 📋 YAML-Vorschau")
        st.code(yaml_output, language="yaml")
    

    # Neustart-Button: Jahre erneut abfragen und State leeren
    col_empty1, col_preview, col_empty2 = st.columns([1, 2, 1])
    if col_preview.button("RESET", width='stretch'):
        reset_keys = [
            "years_confirmed",
            "valid_years",
            "modal_years_select",
            "modal_years_extra",
            "cap_values",
            "cap_df_session",
            "storage_values",
            "emobility_values",
            "scenario_editor",
            "show_yaml_preview",
        ]
        for key in reset_keys:
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("")

