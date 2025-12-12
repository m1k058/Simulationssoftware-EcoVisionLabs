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
        "Industrie_Basis": "Industrie",
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

