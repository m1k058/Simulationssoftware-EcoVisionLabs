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


def scenario_generation_page() -> None:
    st.set_page_config(layout="wide")
    st.title("Szenario Editor")
    st.caption("Szenarien erstellen und als YAML herunterladen.")

    sm = ScenarioManager()
    ensure_state(sm)

    data = st.session_state["scenario_editor"]

    with st.form("scenario_form"):
        # === METADATEN ===
        st.subheader("Metadaten")
        name = st.text_input("Name", value=data.get("metadata", {}).get("name", ""))
        description = st.text_area("Beschreibung", value=data.get("metadata", {}).get("description", ""), height=80)
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            valid_years_from = st.number_input(
                "Gültig ab Jahr",
                value=int(data.get("metadata", {}).get("valid_years_from", 2025)),
                step=1,
            )
            version = st.text_input("Version", value=str(data.get("metadata", {}).get("version", "1.0")))
        with col_meta2:
            valid_years_to = st.number_input(
                "Gültig bis Jahr",
                value=int(data.get("metadata", {}).get("valid_years_to", 2045)),
                step=1,
            )
            author = st.text_input("Autor", value=str(data.get("metadata", {}).get("author", "SW-Team EcoVisionLabs")))

        st.markdown("---")

        # === LASTPROFIL ===
        st.subheader("Last (Verbrauch)")
        load_profile = st.selectbox(
            "Lastprofil",
            options=LOAD_PROFILE_OPTIONS,
            index=LOAD_PROFILE_OPTIONS.index(data.get("load_parameters", {}).get("load_profile", LOAD_PROFILE_OPTIONS[0]))
            if data.get("load_parameters", {}).get("load_profile") in LOAD_PROFILE_OPTIONS else 0,
        )
        if load_profile == "Benutzerdefiniert":
            load_profile = st.text_input("Benutzerdef. Lastprofil", value="")

        st.markdown("**Zielwerte [TWh]** - Jahre und Werte eingeben")
        existing_demand = data.get("load_parameters", {}).get("target_demand_twh", {})
        base_years = {2030, 2045}
        demand_rows = []
        all_years = sorted(base_years.union(existing_demand.keys()))
        for y in all_years:
            demand_rows.append({"Jahr": int(y), "Zielverbrauch [TWh]": float(existing_demand.get(y, 0.0))})
        demand_df = pd.DataFrame(demand_rows).drop_duplicates(subset=["Jahr"], keep="first")
        edited_demand = st.data_editor(demand_df, use_container_width=True, num_rows="dynamic", key="demand_editor")

        st.markdown("---")

        # === ERZEUGUNGSPROFILE ===
        st.subheader("Erzeugungsprofile (SMARD-Daten)")
        col_gp1, col_gp2 = st.columns(2)
        with col_gp1:
            time_resolution = st.selectbox(
                "Zeitauflösung",
                options=TIME_RES_OPTIONS,
                index=TIME_RES_OPTIONS.index(data.get("generation_profile_parameters", {}).get("time_resolution", "15min"))
                if data.get("generation_profile_parameters", {}).get("time_resolution") in TIME_RES_OPTIONS else 0,
            )
        with col_gp2:
            source = st.selectbox(
                "Quelle",
                options=GEN_SOURCES,
                index=GEN_SOURCES.index(data.get("generation_profile_parameters", {}).get("source", "SMARD"))
                if data.get("generation_profile_parameters", {}).get("source") in GEN_SOURCES else 0,
            )

        st.markdown("**Referenz-Jahre für Profile**")
        gen_profiles = data.get("generation_profile_parameters", {})
        good_y = gen_profiles.get("good_year", {})
        bad_y = gen_profiles.get("bad_year", {})
        avg_y = gen_profiles.get("average_year", {})

        ref_df_data = {
            "Typ": ["Gutes Jahr", "Schlechtes Jahr", "Durchschnittsjahr"],
            "Wind Onshore": [
                int(good_y.get("wind_onshore", 0)),
                int(bad_y.get("wind_onshore", 0)),
                int(avg_y.get("wind_onshore", 0)),
            ],
            "Wind Offshore": [
                int(good_y.get("wind_offshore", 0)),
                int(bad_y.get("wind_offshore", 0)),
                int(avg_y.get("wind_offshore", 0)),
            ],
            "Photovoltaik": [
                int(good_y.get("photovoltaics", 0)),
                int(bad_y.get("photovoltaics", 0)),
                int(avg_y.get("photovoltaics", 0)),
            ],
        }
        ref_df = pd.DataFrame(ref_df_data)
        edited_ref = st.data_editor(ref_df, use_container_width=True, disabled=["Typ"], key="ref_editor")

        st.markdown("---")

        # === ZIEL-KAPAZITÄTEN ===
        st.subheader("Ziel-Kapazitäten [MW]")
        caps = data.get("generation_capacities_mw", {})
        techs = list(caps.keys())
        base_years = {2030, 2045}
        all_years = set(base_years)
        for tech_caps in caps.values():
            all_years.update(tech_caps.keys())
        rows = []
        for y in sorted(all_years):
            row = {"Jahr": int(y)}
            for tech in techs:
                row[tech] = float(caps.get(tech, {}).get(y, 0.0))
            rows.append(row)
        cap_df = pd.DataFrame(rows).drop_duplicates(subset=["Jahr"], keep="first")
        edited_cap = st.data_editor(cap_df, use_container_width=True, num_rows="dynamic", key="cap_editor")

        st.markdown("---")

        # === SPEICHER ===
        st.subheader("Speicher")
        storage_defaults = data.get("storage_capacities", {})

        # Persistierte Speicherzeilen für Reloads/Toggles
        def build_row(key: str, label: str, source: dict) -> dict:
            return {
                "key": key,
                "Speichertyp": label,
                "Kapazität [MWh]": float(source.get("installed_capacity_mwh", 0)),
                "Ladeleistung [MW]": float(source.get("max_charge_power_mw", 0)),
                "Entladeleistung [MW]": float(source.get("max_discharge_power_mw", 0)),
                "η Laden": float(source.get("charge_efficiency", 0.0)),
                "η Entladen": float(source.get("discharge_efficiency", 0.0)),
                "SOC initial": float(source.get("soc", {}).get("initial", 0.0)),
                "SOC min": float(source.get("soc", {}).get("min", 0.0)),
                "SOC max": float(source.get("soc", {}).get("max", 1.0)),
            }

        if "storage_rows" not in st.session_state:
            st.session_state["storage_rows"] = [
                build_row("battery_storage", "Batterie", storage_defaults.get("battery_storage", {})),
                build_row("pumped_hydro_storage", "Pumpspeicher", storage_defaults.get("pumped_hydro_storage", {})),
                build_row("h2_storage", "H2", storage_defaults.get("h2_storage", {})),
            ]

        storage_rows_state = st.session_state["storage_rows"]
        rows_by_key = {r["key"]: r for r in storage_rows_state}

        st.markdown("Hinweis: Zur Aktualisierung der Tabelle nach dem Ankreuzen bitte unten auf 'Bestätigen & YAML generieren' klicken.")

        # Aktivierungs-Checkboxen je Speichertyp
        a, b, c = st.columns(3)
        battery_on = a.checkbox(
            "Batterie aktiv",
            value=storage_defaults.get("battery_storage", {}).get("installed_capacity_mwh", 0) > 0
            or storage_defaults.get("battery_storage", {}).get("max_charge_power_mw", 0) > 0,
        )
        pumped_on = b.checkbox(
            "Pumpspeicher aktiv",
            value=storage_defaults.get("pumped_hydro_storage", {}).get("installed_capacity_mwh", 0) > 0
            or storage_defaults.get("pumped_hydro_storage", {}).get("max_charge_power_mw", 0) > 0,
        )
        h2_on = c.checkbox(
            "H2-Speicher aktiv",
            value=storage_defaults.get("h2_storage", {}).get("installed_capacity_mwh", 0) > 0
            or storage_defaults.get("h2_storage", {}).get("max_charge_power_mw", 0) > 0,
        )

        active_flags = {
            "battery_storage": battery_on,
            "pumped_hydro_storage": pumped_on,
            "h2_storage": h2_on,
        }

        enabled_pairs = []
        if battery_on:
            enabled_pairs.append(("battery_storage", "Batterie"))
        if pumped_on:
            enabled_pairs.append(("pumped_hydro_storage", "Pumpspeicher"))
        if h2_on:
            enabled_pairs.append(("h2_storage", "H2"))

        storage_rows = []
        for key, label in enabled_pairs:
            existing = rows_by_key.get(key)
            if existing is None:
                existing = build_row(key, label, storage_defaults.get(key, {}))
            storage_rows.append({k: v for k, v in existing.items() if k != "key"})

        stor_df = pd.DataFrame(storage_rows)
        edited_stor = st.data_editor(
            stor_df,
            use_container_width=True,
            disabled=["Speichertyp"],
            key="storage_editor",
            num_rows="dynamic",
        )

        submitted = st.form_submit_button("✅ Bestätigen & YAML generieren")

    # Nach Submit: Update Session-State aus DataFrames
    if submitted:
        # Demand aus DataFrame
        target_demand_twh = {}
        if not edited_demand.empty:
            for _, row in edited_demand.iterrows():
                try:
                    year = int(row.get("Jahr"))
                    val = float(row.get("Zielverbrauch [TWh]", 0))
                    target_demand_twh[year] = val
                except (ValueError, TypeError):
                    pass

        # Referenz-Jahre aus DataFrame
        good_year_dict = {
            "wind_onshore": int(edited_ref.iloc[0]["Wind Onshore"]),
            "wind_offshore": int(edited_ref.iloc[0]["Wind Offshore"]),
            "photovoltaics": int(edited_ref.iloc[0]["Photovoltaik"]),
        }
        bad_year_dict = {
            "wind_onshore": int(edited_ref.iloc[1]["Wind Onshore"]),
            "wind_offshore": int(edited_ref.iloc[1]["Wind Offshore"]),
            "photovoltaics": int(edited_ref.iloc[1]["Photovoltaik"]),
        }
        avg_year_dict = {
            "wind_onshore": int(edited_ref.iloc[2]["Wind Onshore"]),
            "wind_offshore": int(edited_ref.iloc[2]["Wind Offshore"]),
            "photovoltaics": int(edited_ref.iloc[2]["Photovoltaik"]),
        }

        # Kapazitäten aus transponiertem DataFrame (Jahr als Zeile)
        tech_list = list(caps.keys())
        if not tech_list and not edited_cap.empty:
            tech_list = [c for c in edited_cap.columns if c != "Jahr"]
        gen_capacities_mw = {tech: {} for tech in tech_list}
        if not edited_cap.empty:
            for _, row in edited_cap.iterrows():
                try:
                    year = int(row.get("Jahr"))
                except (ValueError, TypeError):
                    continue
                for tech in tech_list:
                    try:
                        gen_capacities_mw.setdefault(tech, {})[year] = float(row.get(tech, 0.0))
                    except (ValueError, TypeError):
                        pass

        # Speicher aus DataFrame + Checkbox-Status
        storage_capacities = {}

        def zero_storage():
            return {
                "installed_capacity_mwh": 0.0,
                "max_charge_power_mw": 0.0,
                "max_discharge_power_mw": 0.0,
                "charge_efficiency": 0.0,
                "discharge_efficiency": 0.0,
                "soc": {"initial": 0.0, "min": 0.0, "max": 1.0},
            }

        # Update rows_by_key with edited values for enabled storages
        if not edited_stor.empty:
            for i, (stor_type, label) in enumerate(enabled_pairs):
                row = edited_stor.iloc[i]
                rows_by_key[stor_type] = {
                    "key": stor_type,
                    "Speichertyp": label,
                    "Kapazität [MWh]": float(row.get("Kapazität [MWh]", 0)),
                    "Ladeleistung [MW]": float(row.get("Ladeleistung [MW]", 0)),
                    "Entladeleistung [MW]": float(row.get("Entladeleistung [MW]", 0)),
                    "η Laden": float(row.get("η Laden", 0)),
                    "η Entladen": float(row.get("η Entladen", 0)),
                    "SOC initial": float(row.get("SOC initial", 0)),
                    "SOC min": float(row.get("SOC min", 0)),
                    "SOC max": float(row.get("SOC max", 1)),
                }

        # Disabled Speicher auf 0 setzen und rows_by_key updaten
        for stor_type, label in [
            ("battery_storage", "Batterie"),
            ("pumped_hydro_storage", "Pumpspeicher"),
            ("h2_storage", "H2"),
        ]:
            if stor_type not in rows_by_key:
                rows_by_key[stor_type] = build_row(stor_type, label, zero_storage())

        # Build storage_capacities; disabled => zero
        for stor_type, label in [
            ("battery_storage", "Batterie"),
            ("pumped_hydro_storage", "Pumpspeicher"),
            ("h2_storage", "H2"),
        ]:
            is_active = active_flags.get(stor_type, False)
            if not is_active:
                zero_row = build_row(stor_type, label, zero_storage())
                rows_by_key[stor_type] = zero_row
                storage_capacities[stor_type] = {
                    "installed_capacity_mwh": 0.0,
                    "max_charge_power_mw": 0.0,
                    "max_discharge_power_mw": 0.0,
                    "charge_efficiency": 0.0,
                    "discharge_efficiency": 0.0,
                    "soc": {"initial": 0.0, "min": 0.0, "max": 1.0},
                }
                continue

            row = rows_by_key.get(stor_type, build_row(stor_type, label, zero_storage()))
            storage_capacities[stor_type] = {
                "installed_capacity_mwh": float(row.get("Kapazität [MWh]", 0)),
                "max_charge_power_mw": float(row.get("Ladeleistung [MW]", 0)),
                "max_discharge_power_mw": float(row.get("Entladeleistung [MW]", 0)),
                "charge_efficiency": float(row.get("η Laden", 0)),
                "discharge_efficiency": float(row.get("η Entladen", 0)),
                "soc": {
                    "initial": float(row.get("SOC initial", 0)),
                    "min": float(row.get("SOC min", 0)),
                    "max": float(row.get("SOC max", 1)),
                },
            }

        # Speichern der UI-Zeilen für spätere Reruns
        st.session_state["storage_rows"] = list(rows_by_key.values())

        # Update Session State
        st.session_state["scenario_editor"] = {
            "metadata": {
                "name": name,
                "description": description,
                "valid_years_from": int(valid_years_from),
                "valid_years_to": int(valid_years_to),
                "version": version,
                "author": author,
            },
            "load_parameters": {
                "target_demand_twh": target_demand_twh,
                "load_profile": load_profile,
            },
            "generation_profile_parameters": {
                "time_resolution": time_resolution,
                "source": source,
                "good_year": good_year_dict,
                "bad_year": bad_year_dict,
                "average_year": avg_year_dict,
            },
            "generation_capacities_mw": gen_capacities_mw,
            "storage_capacities": storage_capacities,
        }
        st.success("✅ Daten verarbeitet - YAML bereit zum Download!")
        st.rerun()

    # === DOWNLOAD BEREICH ===
    st.markdown("---")
    st.subheader("📥 YAML Download")
    
    # Generiere YAML aus aktuellen Session-State Daten
    yaml_output = sm.create_scenario_yaml(st.session_state["scenario_editor"])
    
    st.download_button(
        "Download YAML",
        data=yaml_output,
        file_name=f"{st.session_state['scenario_editor'].get('metadata', {}).get('name', 'szenario')}.yaml",
        mime="text/yaml",
        use_container_width=True,
    )

    st.markdown("---")
    with st.expander("📄 Vorschau YAML"):
        st.code(yaml_output, language="yaml")

