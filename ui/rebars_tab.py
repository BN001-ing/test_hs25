import streamlit as st
import pandas as pd

from logic.rebar_logic import (
    build_rebar_kubaturen,
    apply_rebar_overrides,
    compute_rebar_split_totals,
)
from database.datenbank import get_all_materials


def _load_default_rebar_price() -> float:
    """
    Standard-Bewehrungspreis aus der Materialdatenbank:
    Materialname 'Bewehrung' (case-insensitive).
    Fallback: 2.0 CHF/kg
    """
    rows = get_all_materials()
    if not rows:
        return 2.0

    df = pd.DataFrame(
        rows,
        columns=["id", "material_name", "einheit", "preis_chf", "datum_aktualisiert"],
    )

    mask = df["material_name"].astype(str).str.lower() == "bewehrung"
    if mask.any():
        return float(df.loc[mask, "preis_chf"].iloc[0])

    return 2.0


def _get_rebar_overrides() -> dict:
    if "rebar_overrides" not in st.session_state:
        st.session_state["rebar_overrides"] = {}
    return st.session_state["rebar_overrides"]


def _get_rebar_split_state(default_price: float) -> dict:
    """
    Session-State für die Aufteilung (Fix, BG1, BG2, BGS) + Preise ablegen.
    Struktur siehe compute_rebar_split_totals().
    """
    if "rebar_split" not in st.session_state:
        st.session_state["rebar_split"] = {
            "Fix": {
                "grp_pct": 40.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {
                    "8-10": default_price,
                    "12-16": default_price,
                    "18-26": default_price,
                    "30-46": default_price,
                },
            },
            "BG 1": {
                "grp_pct": 30.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {
                    "8-10": default_price,
                    "12-16": default_price,
                    "18-26": default_price,
                    "30-46": default_price,
                },
            },
            "BG 2": {
                "grp_pct": 10.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {
                    "8-10": default_price,
                    "12-16": default_price,
                    "18-26": default_price,
                    "30-46": default_price,
                },
            },
            "BG S": {
                "grp_pct": 5.0,
                "bins": {"8-10": 50.0, "12-16": 35.0, "18-26": 10.0, "30-46": 5.0},
                "prices": {
                    "8-10": default_price,
                    "12-16": default_price,
                    "18-26": default_price,
                    "30-46": default_price,
                },
            },
        }
    return st.session_state["rebar_split"]


def main():
    st.title("🔩 Bewehrung")

    df_ifc: pd.DataFrame | None = st.session_state.get("df_ifc")
    if df_ifc is None or df_ifc.empty:
        st.warning("Bitte zuerst im KuBeKo-Tab eine IFC-Datei laden und auswerten.")
        return

    default_price = _load_default_rebar_price()
    rebar_overrides = _get_rebar_overrides()

    # 1) Beton-Bauteile aus IFC extrahieren
    df_rebar_base = build_rebar_kubaturen(df_ifc)

    if df_rebar_base.empty:
        st.info("Keine betonrelevanten Bauteile gefunden (Bewehrung).")
        return

    # 2) Overrides anwenden → effektive kg/m³ & kg total
    df_rebar_view = apply_rebar_overrides(
        df_rebar_base,
        overrides=rebar_overrides,
        default_kg_m3=0.0,
    )
    st.session_state["df_rebar_view"] = df_rebar_view

    project_total_kg = float(df_rebar_view["Bewehrung_kg"].sum())
    st.session_state["project_total_rebar_kg"] = project_total_kg

    st.subheader("Projekt-Gesamtsumme Bewehrung")
    st.markdown(f"**{project_total_kg:,.0f} kg**")

    # --- Eingabe pro Geschoss / Bauteil (kg/m³) ---
    st.markdown("---")
    st.subheader("Bewehrung pro Bauteil (kg/m³)")

    gebaeude_liste = sorted(df_rebar_view["Gebäude"].dropna().astype(str).unique())

    for geb in gebaeude_liste:
        df_geb = df_rebar_view[df_rebar_view["Gebäude"].astype(str) == geb]

        geb_total_kg = df_geb["Bewehrung_kg"].sum()
        with st.expander(f"🏢 Gebäude: {geb}", expanded=False):
            st.markdown(f"**Bewehrung Gebäude:** {geb_total_kg:,.0f} kg")

            storeys = sorted(df_geb["Geschoss"].dropna().astype(str).unique())

            for storey in storeys:
                df_storey = df_geb[df_geb["Geschoss"].astype(str) == storey]

                st.markdown("---")
                st.markdown(f"### Geschoss: {storey}")

                form_key = f"rebar_form_{geb}_{storey}"
                with st.form(key=form_key):
                    pending_overrides: dict = {}
                    storey_total_preview = 0.0

                    head_cols = st.columns([3.0, 3.0, 2.0, 2.0])
                    head_cols[0].markdown("**Bauteil**")
                    head_cols[1].markdown("**Material**")
                    head_cols[2].markdown("**Kubatur [m³]**")
                    head_cols[3].markdown("**kg/m³**")

                    # WICHTIG: Iteration über Index (idx) und Row
                    for idx, row in df_storey.iterrows():
                        grund = str(row.get("Grundstück", ""))
                        bau = str(row.get("Bauteil", ""))
                        mat = str(row.get("Material", ""))
                        vol = float(row.get("Volumen_m3_sum", 0.0))

                        key_tuple = (grund, geb, storey, bau, mat)
                        start_kg_m3 = float(
                            rebar_overrides.get(key_tuple, row.get("kg_m3_auto", 0.0))
                        )
                        
                        # Generiere einen stabilen, eindeutigen String-Key inkl. Index (idx)
                        stable_key = f"rebar-{idx}-{grund}-{geb}-{storey}-{bau}-{mat}".replace(" ", "_").replace(".", "-")


                        c1, c2, c3, c4 = st.columns([3.0, 3.0, 2.0, 2.0])

                        with c1:
                            st.markdown(bau or "—")
                            st.caption(mat or "")

                        with c2:
                            st.markdown(mat or "—")

                        with c3:
                            st.markdown(f"{vol:,.2f}")

                        with c4:
                            new_kg_m3 = st.number_input(
                                label=" ",
                                label_visibility="collapsed",
                                min_value=0.0,
                                step=5.0,
                                format="%.1f",
                                value=float(start_kg_m3),
                                key=stable_key, # <--- STABILER KEY VERWENDET
                            )
                            pending_overrides[key_tuple] = float(new_kg_m3)
                            storey_total_preview += vol * float(new_kg_m3)

                    st.markdown(
                        f"**Vorschau Bewehrung Geschoss {storey}:** {storey_total_preview:,.0f} kg"
                    )

                    submitted = st.form_submit_button("kg/m³ übernehmen")
                    if submitted:
                        rebar_overrides.update(pending_overrides)
                        st.session_state["rebar_overrides"] = rebar_overrides

                        # Neu berechnen
                        df_rebar_view_new = apply_rebar_overrides(
                            df_rebar_base,
                            overrides=rebar_overrides,
                            default_kg_m3=0.0,
                        )
                        st.session_state["df_rebar_view"] = df_rebar_view_new
                        st.session_state["project_total_rebar_kg"] = float(
                            df_rebar_view_new["Bewehrung_kg"].sum()
                        )

                        st.success(f"Bewehrung für Geschoss {storey} übernommen.")
                        st.rerun() # st.experimental_rerun() ersetzt durch st.rerun()

    # --- Aufteilung B500B (Fix, BG1, BG2, BG S, Matten) ---
    st.markdown("---")
    st.subheader("Aufteilung Bewehrung (B500B)")

    rebar_split = _get_rebar_split_state(default_price)

    # Matten-Prozent
    st.markdown("#### B500B Bewehrungsmatten")
    col_m1, col_m2, col_m3 = st.columns([3.0, 2.0, 3.0])
    with col_m1:
        st.write("B500B Bewehrungsmatten (inkl. 300 kg Firipa)")
    with col_m2:
        matten_pct = st.number_input(
            "Anteil Matten [%]",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=15.0,
            key="matten_pct",
        )
    with col_m3:
        st.write("")  # Platzhalter

    # Gruppen-Felder (Fix, BG1, BG2, BGS)
    for label in ["Fix", "BG 1", "BG 2", "BG S"]:
        data = rebar_split[label]
        with st.expander(f"B500B {label}", expanded=False):
            grp_pct = st.number_input(
                f"Anteil Gruppe {label} [%]",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                value=float(data.get("grp_pct", 0.0)),
                key=f"{label}_grp_pct",
            )
            data["grp_pct"] = grp_pct

            st.markdown("**Verteilung nach Durchmesser + Preis [CHF/kg]**")
            cols = st.columns(4)
            for i, bin_name in enumerate(["8-10", "12-16", "18-26", "30-46"]):
                with cols[i]:
                    bin_pct = st.number_input(
                        f"{bin_name} [%] ({label})",
                        min_value=0.0,
                        max_value=100.0,
                        step=1.0,
                        value=float(data["bins"].get(bin_name, 0.0)),
                        key=f"{label}_{bin_name}_pct",
                    )
                    data["bins"][bin_name] = bin_pct

                    price_val = st.number_input(
                        f"Preis {bin_name} [CHF/kg]",
                        min_value=0.0,
                        step=0.05,
                        format="%.2f",
                        value=float(
                            data["prices"].get(bin_name, default_price)
                        ),
                        key=f"{label}_{bin_name}_price",
                    )
                    data["prices"][bin_name] = price_val

    # Ergebnisse der Aufteilung berechnen
    split_result = compute_rebar_split_totals(
        project_total_kg=project_total_kg,
        rebar_split=rebar_split,
        matten_pct=float(matten_pct),
        default_rebar_price=float(default_price),
    )

    st.session_state["project_total_rebar_cost"] = float(split_result["total_cost"])

    st.markdown("---")
    st.markdown(
        f"**Total Devis Bewehrung:** {split_result['total_kg']:,.0f} kg "
        f"• Kosten Bewehrung: {split_result['total_cost']:,.2f} CHF"
    )


if __name__ == "__main__":
    main()