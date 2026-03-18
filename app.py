import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

st.set_page_config(page_title="OP TCG Meta Analyzer", page_icon="🏴‍☠️", layout="wide")

st.title("🏴‍☠️ One Piece TCG — Meta Analyzer")
st.caption("Powered by optcgapi.com · Daten automatisch geladen")

@st.cache_data(ttl=3600)
def load_all_cards():
    try:
        r = requests.get("https://optcgapi.com/api/allSetCards/", timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return pd.DataFrame(data)
        for key in data:
            if isinstance(data[key], list):
                return pd.DataFrame(data[key])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_tournaments(limit=100):
    try:
        r = requests.get(
            f"https://play.limitlesstcg.com/api/tournaments?game=OP&limit={limit}",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return []

@st.cache_data(ttl=1800)
def load_standings(tournament_id):
    try:
        r = requests.get(
            f"https://play.limitlesstcg.com/api/tournaments/{tournament_id}/standings",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except:
        return []

with st.spinner("Kartendaten werden geladen..."):
    df = load_all_cards()

if df.empty:
    st.error("Keine Daten geladen.")
    st.stop()

# Feldnamen
NAME    = "card_name"
COLOR   = "card_color"
TYPE    = "card_type"
COST    = "card_cost"
POWER   = "card_power"
SET_ID  = "set_id"
SET     = "set_name"
RARITY  = "rarity"
TEXT    = "card_text"
LIFE    = "life"
COUNTER = "counter_amount"
PRICE   = "market_price"
INV     = "inventory_price"
IMAGE   = "card_image"
CARD_ID = "card_set_id"

# Numerische Felder
for col in [COST, POWER, LIFE, COUNTER, PRICE, INV]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Parallel-Karten erkennen (card_name enthält "Parallel" oder card_image_id endet auf _p)
df["is_parallel"] = (
    df[NAME].astype(str).str.contains("Parallel|Alt Art|Special", case=False, na=False) |
    df["card_image_id"].astype(str).str.contains("_p", na=False)
) if "card_image_id" in df.columns else df[NAME].astype(str).str.contains("Parallel|Alt Art", case=False, na=False)

# Seltenheits-Mapping (One Piece TCG Codes)
rarity_order = {
    "L":   ("Leader", 1),
    "C":   ("Common", 2),
    "UC":  ("Uncommon", 3),
    "R":   ("Rare", 4),
    "SR":  ("Super Rare", 5),
    "SEC": ("Secret Rare", 6),
    "SP":  ("Special Card", 7),
    "TR":  ("Treasure Rare", 8),
}
df["rarity_label"] = df[RARITY].map(lambda x: rarity_order.get(str(x), (str(x), 0))[0])
df["rarity_rank"]  = df[RARITY].map(lambda x: rarity_order.get(str(x), (str(x), 0))[1])

color_map = {
    "Red": "#e74c3c", "Blue": "#3498db", "Green": "#2ecc71",
    "Purple": "#9b59b6", "Black": "#2c3e50", "Yellow": "#f1c40f", "White": "#bdc3c7",
}

# ─── Metriken ───────────────────────────────────────────────────────────────
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Karten gesamt", len(df))
with col2:
    st.metric("Farben", df[COLOR].nunique() if COLOR in df.columns else "–")
with col3:
    st.metric("Sets", df[SET_ID].nunique() if SET_ID in df.columns else "–")
with col4:
    parallel_count = df["is_parallel"].sum()
    st.metric("Parallel/Alt Art", int(parallel_count))

st.divider()

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Kartentypen",
    "🎨 Farb-Analyse",
    "💰 Kosten-Kurve",
    "💎 Undervalued Cards",
    "🌟 Chase Cards",
    "📈 Marktbewertung",
    "🔍 Kartensuche",
    "🏆 Turnierdaten",
])

# ── Tab 1: Kartentypen ───────────────────────────────────────────────────────
with tab1:
    st.subheader("Kartentypen im Überblick")
    c1, c2 = st.columns(2)
    with c1:
        if TYPE in df.columns:
            type_counts = df[TYPE].value_counts().reset_index()
            type_counts.columns = ["Typ", "Anzahl"]
            fig = px.pie(type_counts, values="Anzahl", names="Typ",
                         title="Verteilung nach Kartentyp", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if SET_ID in df.columns:
            set_counts = df[SET_ID].value_counts().reset_index()
            set_counts.columns = ["Set", "Karten"]
            set_counts = set_counts.sort_values("Set")
            fig2 = px.bar(set_counts, x="Set", y="Karten", title="Karten pro Set",
                          color="Karten", color_continuous_scale="Reds")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
    if RARITY in df.columns:
        st.subheader("Verteilung nach Seltenheit")
        rarity_counts = df["rarity_label"].value_counts().reset_index()
        rarity_counts.columns = ["Seltenheit", "Anzahl"]
        fig3 = px.bar(rarity_counts, x="Seltenheit", y="Anzahl",
                      title="Karten pro Seltenheitsstufe",
                      color="Anzahl", color_continuous_scale="Blues")
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

# ── Tab 2: Farb-Analyse ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Farbverteilung")
    if COLOR in df.columns:
        all_colors = []
        for c in df[COLOR].dropna():
            for part in str(c).replace("/", ";").replace(",", ";").split(";"):
                cleaned = part.strip()
                if cleaned:
                    all_colors.append(cleaned)
        color_counts = Counter(all_colors)
        color_df = pd.DataFrame(color_counts.items(), columns=["Farbe", "Anzahl"]).sort_values("Anzahl", ascending=False)
        fig = px.bar(color_df, x="Farbe", y="Anzahl", title="Karten pro Farbe",
                     color="Farbe", color_discrete_map=color_map)
        fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        if POWER in df.columns:
            st.subheader("Durchschnittliche Power nach Farbe")
            single = df[~df[COLOR].astype(str).str.contains("/", na=False)].copy()
            power_by_color = single.groupby(COLOR)[POWER].mean().reset_index()
            power_by_color.columns = ["Farbe", "Ø Power"]
            power_by_color["Ø Power"] = power_by_color["Ø Power"].round(0)
            power_by_color = power_by_color.sort_values("Ø Power", ascending=False)
            fig2 = px.bar(power_by_color, x="Farbe", y="Ø Power",
                          title="Durchschnittliche Stärke pro Farbe",
                          color="Farbe", color_discrete_map=color_map)
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        if TYPE in df.columns:
            st.subheader("Kartentypen pro Farbe")
            single2 = df[~df[COLOR].astype(str).str.contains("/", na=False)].copy()
            cross = single2.groupby([COLOR, TYPE]).size().reset_index(name="Anzahl")
            fig3 = px.bar(cross, x=COLOR, y="Anzahl", color=TYPE,
                          title="Welche Typen hat jede Farbe?", barmode="stack")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

# ── Tab 3: Kosten-Kurve ──────────────────────────────────────────────────────
with tab3:
    st.subheader("Kosten-Kurve")
    if COST in df.columns:
        cost_df = df[df[COST].notna() & (df[COST] >= 0)].copy()
        c_left, c_right = st.columns([1, 2])
        with c_left:
            farben_liste = ["Alle"] + sorted(df[COLOR].dropna().unique().tolist())
            selected = st.selectbox("Filtern nach Farbe", farben_liste)
        with c_right:
            if TYPE in df.columns:
                typen_liste = ["Alle"] + sorted(df[TYPE].dropna().unique().tolist())
                selected_type = st.selectbox("Filtern nach Typ", typen_liste)
            else:
                selected_type = "Alle"
        if selected != "Alle":
            cost_df = cost_df[cost_df[COLOR].astype(str).str.contains(selected, na=False)]
        if selected_type != "Alle" and TYPE in df.columns:
            cost_df = cost_df[cost_df[TYPE].astype(str) == selected_type]
        cost_counts = cost_df[COST].value_counts().reset_index().sort_values(COST)
        cost_counts.columns = ["Kosten", "Anzahl"]
        fig = px.bar(cost_counts, x="Kosten", y="Anzahl", title="Kostenverteilung",
                     color="Anzahl", color_continuous_scale="Reds")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        if POWER in df.columns:
            eff = cost_df[cost_df[COST] > 0].copy()
            eff["power_per_cost"] = eff[POWER] / eff[COST]
            eff = eff[eff["power_per_cost"].notna()]
            avg = eff.groupby(COST)["power_per_cost"].mean().reset_index()
            avg.columns = ["Kosten", "Ø Power pro Kosten"]
            avg["Ø Power pro Kosten"] = avg["Ø Power pro Kosten"].round(0)
            fig2 = px.line(avg, x="Kosten", y="Ø Power pro Kosten",
                           title="Power-Effizienz pro Kostenpunkt", markers=True)
            fig2.update_traces(line_color="#e94560", marker_color="#e94560")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        if PRICE in df.columns:
            price_df = cost_df[cost_df[PRICE].notna()].copy()
            avg_price = price_df.groupby(COST)[PRICE].mean().reset_index()
            avg_price.columns = ["Kosten", "Ø Marktpreis ($)"]
            avg_price["Ø Marktpreis ($)"] = avg_price["Ø Marktpreis ($)"].round(2)
            fig3 = px.bar(avg_price, x="Kosten", y="Ø Marktpreis ($)",
                          title="Marktpreis pro Kostenpunkt",
                          color="Ø Marktpreis ($)", color_continuous_scale="Greens")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

# ── Tab 4: Undervalued Cards ─────────────────────────────────────────────────
with tab4:
    st.subheader("💎 Undervalued Cards — stark aber günstig")
    st.caption("Karten mit hoher Spielstärke aber niedrigem Marktpreis.")
    if COST in df.columns and POWER in df.columns and PRICE in df.columns:
        c1, c2, c3 = st.columns(3)
        with c1:
            max_price = st.slider("Max. Marktpreis ($)", 0.0,
                                  float(df[PRICE].quantile(0.95) or 20), 5.0, 0.5)
        with c2:
            uv_colors = ["Alle"] + sorted(df[COLOR].dropna().unique().tolist())
            uv_color = st.selectbox("Farbe", uv_colors, key="uv_color")
        with c3:
            uv_types = ["Alle"] + sorted(df[TYPE].dropna().unique().tolist())
            uv_type = st.selectbox("Typ", uv_types, key="uv_type")
        scored = df[
            df[COST].notna() & df[POWER].notna() &
            df[PRICE].notna() & (df[COST] > 0) & (df[PRICE] > 0)
        ].copy()
        scored["power_efficiency"] = scored[POWER] / scored[COST]
        p_min, p_max = scored["power_efficiency"].min(), scored["power_efficiency"].max()
        pr_min, pr_max = scored[PRICE].min(), scored[PRICE].max()
        scored["eff_score"]   = (scored["power_efficiency"] - p_min) / (p_max - p_min + 0.001)
        scored["price_score"] = 1 - (scored[PRICE] - pr_min) / (pr_max - pr_min + 0.001)
        scored["uv_score"] = (scored["eff_score"] * 0.6 + scored["price_score"] * 0.4) * 100
        scored["uv_score"] = scored["uv_score"].round(1)
        filtered = scored[scored[PRICE] <= max_price].copy()
        if uv_color != "Alle":
            filtered = filtered[filtered[COLOR].astype(str).str.contains(uv_color, na=False)]
        if uv_type != "Alle":
            filtered = filtered[filtered[TYPE].astype(str) == uv_type]
        filtered = filtered.sort_values("uv_score", ascending=False)
        if filtered.empty:
            st.warning("Keine Karten gefunden. Preis-Limit erhöhen?")
        else:
            top20 = filtered.head(20)
            fig = px.bar(top20, x="uv_score", y=NAME, orientation="h",
                         title=f"Top {min(20, len(filtered))} Undervalued Cards",
                         color="uv_score", color_continuous_scale="RdYlGn",
                         hover_data=[COLOR, COST, POWER, PRICE])
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              paper_bgcolor="rgba(0,0,0,0)", height=550)
            st.plotly_chart(fig, use_container_width=True)
            top50 = filtered.head(50)
            fig2 = px.scatter(top50, x=PRICE, y="power_efficiency",
                              color=COLOR, color_discrete_map=color_map,
                              hover_name=NAME, hover_data=[COST, POWER, RARITY],
                              title="Power-Effizienz vs. Marktpreis",
                              labels={PRICE: "Marktpreis ($)", "power_efficiency": "Power / Spielkosten"},
                              size="uv_score", size_max=20)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            show = [NAME, COLOR, COST, POWER, PRICE, RARITY, "uv_score"]
            show = [c for c in show if c in filtered.columns]
            st.dataframe(filtered[show].head(50).reset_index(drop=True),
                         use_container_width=True, height=350)
            csv = filtered[show].to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Undervalued Cards als CSV", data=csv,
                               file_name="optcg_undervalued.csv", mime="text/csv")

# ── Tab 5: Chase Cards ───────────────────────────────────────────────────────
with tab5:
    st.subheader("🌟 Chase Cards")

    chase_tab1, chase_tab2 = st.tabs(["🏆 Sammler-Chase Cards", "⚔️ Spieler-Chase Cards (bald)"])

    with chase_tab1:
        st.caption("Die wertvollsten Karten zum Sammeln — sortiert nach Marktpreis.")

        if PRICE in df.columns:
            c1, c2, c3 = st.columns(3)
            with c1:
                sets_liste = ["Alle Sets"] + sorted(df[SET_ID].dropna().unique().tolist())
                chase_set = st.selectbox("Set", sets_liste, key="chase_set")
            with c2:
                parallel_filter = st.selectbox(
                    "Kartenversion",
                    ["Alle", "Nur Parallel / Alt Art", "Nur normale Versionen"],
                    key="chase_parallel"
                )
            with c3:
                chase_rarity = st.multiselect(
                    "Seltenheit",
                    options=sorted(df["rarity_label"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Alle Seltenheiten",
                    key="chase_rarity"
                )

            chase_df = df[df[PRICE].notna() & (df[PRICE] > 0)].copy()

            if chase_set != "Alle Sets":
                chase_df = chase_df[chase_df[SET_ID] == chase_set]
            if parallel_filter == "Nur Parallel / Alt Art":
                chase_df = chase_df[chase_df["is_parallel"] == True]
            elif parallel_filter == "Nur normale Versionen":
                chase_df = chase_df[chase_df["is_parallel"] == False]
            if chase_rarity:
                chase_df = chase_df[chase_df["rarity_label"].isin(chase_rarity)]

            chase_df = chase_df.sort_values(PRICE, ascending=False)

            if chase_df.empty:
                st.warning("Keine Karten mit diesen Filtern gefunden.")
            else:
                # Top Metriken
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Teuerste Karte", f"${chase_df[PRICE].max():.2f}")
                with m2:
                    st.metric("Ø Preis Top 10", f"${chase_df.head(10)[PRICE].mean():.2f}")
                with m3:
                    st.metric("Karten über $50", len(chase_df[chase_df[PRICE] >= 50]))
                with m4:
                    st.metric("Karten über $100", len(chase_df[chase_df[PRICE] >= 100]))

                st.divider()

                # Top 15 Balkendiagramm
                top15 = chase_df.head(15)
                fig = px.bar(
                    top15, x=PRICE, y=NAME, orientation="h",
                    title="Top 15 wertvollste Karten",
                    color=PRICE, color_continuous_scale="YlOrRd",
                    hover_data=[SET_ID, "rarity_label", COLOR, "is_parallel"],
                    labels={PRICE: "Marktpreis ($)"},
                )
                fig.update_layout(
                    yaxis={"categoryorder": "total ascending"},
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Preis nach Seltenheit
                st.subheader("Durchschnittspreis nach Seltenheit")
                rarity_price = chase_df.groupby("rarity_label")[PRICE].agg(["mean", "max", "count"]).reset_index()
                rarity_price.columns = ["Seltenheit", "Ø Preis", "Max Preis", "Anzahl"]
                rarity_price["Ø Preis"] = rarity_price["Ø Preis"].round(2)
                rarity_price["Max Preis"] = rarity_price["Max Preis"].round(2)
                rarity_price = rarity_price.sort_values("Ø Preis", ascending=False)
                fig2 = px.bar(rarity_price, x="Seltenheit", y="Ø Preis",
                              title="Durchschnittspreis pro Seltenheitsstufe",
                              color="Ø Preis", color_continuous_scale="YlOrRd",
                              hover_data=["Max Preis", "Anzahl"])
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

                # Kartenbilder der Top Chase Cards
                st.subheader("Top Chase Cards — Galerie")
                show_images = st.toggle("Bilder anzeigen", value=True, key="chase_images")
                if show_images and IMAGE in chase_df.columns:
                    top_gallery = chase_df.head(10).to_dict("records")
                    cols = st.columns(5)
                    for i, card in enumerate(top_gallery):
                        with cols[i % 5]:
                            img_url = card.get(IMAGE, "")
                            if img_url and str(img_url) != "nan":
                                try:
                                    st.image(str(img_url), use_container_width=True)
                                except:
                                    st.write("🃏")
                            price = card.get(PRICE, 0)
                            name  = card.get(NAME, "")
                            rarity_l = card.get("rarity_label", "")
                            st.caption(f"**{name}**")
                            st.caption(f"💰 ${float(price):.2f} · {rarity_l}")

                # Vollständige Tabelle
                st.subheader("Alle Chase Cards")
                show_cols = [c for c in [NAME, SET_ID, "rarity_label", COLOR, PRICE, INV, "is_parallel"] if c in chase_df.columns]
                st.dataframe(chase_df[show_cols].reset_index(drop=True),
                             use_container_width=True, height=350)
                csv = chase_df[show_cols].to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Chase Cards als CSV", data=csv,
                                   file_name="optcg_chase_cards.csv", mime="text/csv")

    with chase_tab2:
        st.info("⚔️ Spieler-Chase Cards werden nach dem Einbinden der Turnierdaten verfügbar. Dann sehen wir welche Karten in den stärksten Decks unverzichtbar sind.")

# ── Tab 6: Marktbewertung ────────────────────────────────────────────────────
with tab6:
    st.subheader("📈 Marktbewertung")
    st.caption("Aktueller Snapshot — historische Trends werden nach mehreren Wochen Datensammlung verfügbar.")

    if PRICE in df.columns:

        market_tab1, market_tab2, market_tab3 = st.tabs([
            "🌍 Gesamtmarkt", "📦 Set-Vergleich", "🎁 Box vs. Einzelkarten"
        ])

        with market_tab1:
            st.subheader("Gesamtmarkt Überblick")

            valid = df[df[PRICE].notna() & (df[PRICE] > 0)]

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                total_value = valid[PRICE].sum()
                st.metric("Gesamtwert aller Karten", f"${total_value:,.0f}")
            with m2:
                avg_price = valid[PRICE].mean()
                st.metric("Ø Kartenpreis", f"${avg_price:.2f}")
            with m3:
                median_price = valid[PRICE].median()
                st.metric("Median Kartenpreis", f"${median_price:.2f}")
            with m4:
                expensive = len(valid[valid[PRICE] >= 10])
                st.metric("Karten über $10", expensive)

            st.divider()

            # Preisverteilung
            st.subheader("Preisverteilung aller Karten")
            price_bins = valid.copy()
            price_bins["Preisklasse"] = pd.cut(
                price_bins[PRICE],
                bins=[0, 1, 5, 10, 25, 50, 100, float("inf")],
                labels=["$0–1", "$1–5", "$5–10", "$10–25", "$25–50", "$50–100", "$100+"]
            )
            bin_counts = price_bins["Preisklasse"].value_counts().reset_index()
            bin_counts.columns = ["Preisklasse", "Anzahl"]
            bin_order = ["$0–1", "$1–5", "$5–10", "$10–25", "$25–50", "$50–100", "$100+"]
            bin_counts["Preisklasse"] = pd.Categorical(bin_counts["Preisklasse"], categories=bin_order, ordered=True)
            bin_counts = bin_counts.sort_values("Preisklasse")
            fig = px.bar(bin_counts, x="Preisklasse", y="Anzahl",
                         title="Wie viele Karten kosten wie viel?",
                         color="Anzahl", color_continuous_scale="Blues")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            # Preis nach Farbe
            st.subheader("Durchschnittspreis nach Farbe")
            single_color = valid[~valid[COLOR].astype(str).str.contains("/", na=False)]
            color_price = single_color.groupby(COLOR)[PRICE].agg(["mean", "sum", "count"]).reset_index()
            color_price.columns = ["Farbe", "Ø Preis", "Gesamtwert", "Karten"]
            color_price["Ø Preis"] = color_price["Ø Preis"].round(2)
            color_price["Gesamtwert"] = color_price["Gesamtwert"].round(0)
            color_price = color_price.sort_values("Ø Preis", ascending=False)
            fig2 = px.bar(color_price, x="Farbe", y="Ø Preis",
                          title="Welche Farbe hat die teuersten Karten?",
                          color="Farbe", color_discrete_map=color_map,
                          hover_data=["Gesamtwert", "Karten"])
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        with market_tab2:
            st.subheader("Set-Vergleich")

            set_stats = df[df[PRICE].notna() & (df[PRICE] > 0)].groupby(SET_ID).agg(
                Karten=(PRICE, "count"),
                Gesamtwert=(PRICE, "sum"),
                Durchschnitt=(PRICE, "mean"),
                Median=(PRICE, "median"),
                Teuerste=(PRICE, "max"),
            ).reset_index()
            set_stats.columns = ["Set", "Karten", "Gesamtwert ($)", "Ø Preis ($)", "Median ($)", "Teuerste ($)"]
            for col in ["Gesamtwert ($)", "Ø Preis ($)", "Median ($)", "Teuerste ($)"]:
                set_stats[col] = set_stats[col].round(2)
            set_stats = set_stats.sort_values("Set")

            # Gesamtwert pro Set
            fig = px.bar(set_stats, x="Set", y="Gesamtwert ($)",
                         title="Gesamtwert aller Karten pro Set",
                         color="Gesamtwert ($)", color_continuous_scale="Greens")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            # Durchschnittspreis pro Set
            fig2 = px.line(set_stats, x="Set", y="Ø Preis ($)",
                           title="Durchschnittlicher Kartenpreis pro Set",
                           markers=True)
            fig2.update_traces(line_color="#3498db", marker_color="#3498db")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Steigende Linie = neuere Sets haben im Schnitt teurere Karten.")

            # Tabelle
            st.dataframe(set_stats.reset_index(drop=True), use_container_width=True)

        with market_tab3:
            st.subheader("🎁 Box vs. Einzelkarten")
            st.caption("Lohnt es sich eine Booster Box zu kaufen, oder besser Einzelkarten?")

            # Booster Box Preise (manuelle Richtwerte — werden nicht von API geliefert)
            box_prices = {
                "OP-01": 90, "OP-02": 85, "OP-03": 80, "OP-04": 80,
                "OP-05": 80, "OP-06": 80, "OP-07": 80, "OP-08": 80,
                "OP-09": 80, "OP-10": 80, "OP-11": 80, "OP-12": 80,
                "OP-13": 80, "OP-14": 80,
            }

            # Erwarteter Wert pro Box berechnen
            # Eine Box hat 24 Packs à 12 Karten = 288 Karten
            # Aber nur Karten die im Set sind, gewichtet nach Seltenheit
            results = []
            for set_id, box_price in box_prices.items():
                set_cards = df[(df[SET_ID] == set_id) & df[PRICE].notna() & (df[PRICE] > 0)]
                if len(set_cards) == 0:
                    continue
                total_card_value = set_cards[PRICE].sum()
                avg_card_value   = set_cards[PRICE].mean()
                max_card_value   = set_cards[PRICE].max()
                card_count       = len(set_cards)
                results.append({
                    "Set": set_id,
                    "Box Preis ($)": box_price,
                    "Gesamtwert Karten ($)": round(total_card_value, 2),
                    "Ø Kartenpreis ($)": round(avg_card_value, 2),
                    "Teuerste Karte ($)": round(max_card_value, 2),
                    "Karten im Set": card_count,
                    "Wert/Preis Ratio": round(total_card_value / box_price, 2),
                })

            if results:
                box_df = pd.DataFrame(results).sort_values("Set")

                # Ratio Chart
                fig = px.bar(box_df, x="Set", y="Wert/Preis Ratio",
                             title="Gesamtwert aller Karten ÷ Box-Preis",
                             color="Wert/Preis Ratio",
                             color_continuous_scale="RdYlGn")
                fig.add_hline(y=1.0, line_dash="dash", line_color="white",
                              annotation_text="Break-Even (Ratio = 1)")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Ratio > 1 = Gesamtwert aller Karten im Set ist höher als der Box-Preis. Beachte: Du bekommst nicht alle Karten aus einer Box!")

                st.dataframe(box_df.reset_index(drop=True), use_container_width=True)

                st.info("💡 Die Box-Preise sind Richtwerte (~$80). Für aktuelle Preise empfehle ich TCGPlayer oder CardMarket zu prüfen.")
    else:
        st.warning("Keine Preisdaten verfügbar.")

# ── Kartensuche (Sidebar) ────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🔍 Schnellsuche")
    search = st.text_input("Kartenname", placeholder="z.B. Luffy")
    if search:
        results = df[df[NAME].astype(str).str.contains(search, case=False, na=False)]
        st.write(f"{len(results)} Karten gefunden")
        for _, row in results.head(5).iterrows():
            img = row.get(IMAGE, "")
            price = row.get(PRICE, None)
            if img and str(img) != "nan":
                try:
                    st.image(str(img), width=120)
                except:
                    pass
            price_str = f"💰 ${float(price):.2f}" if price and str(price) != "nan" else ""
            st.caption(f"**{row[NAME]}** {price_str}")
            st.divider()

# ── Tab 8: Turnierdaten ──────────────────────────────────────────────────────
with tab8:
    st.subheader("🏆 Turnierdaten — Limitless TCG")
    st.caption("Echte Turnierergebnisse · Welche Leader und Decks gewinnen wirklich?")

    with st.spinner("Turnierdaten werden geladen..."):
        tournaments = load_tournaments(limit=200)

    if not tournaments:
        st.error("Turnierdaten konnten nicht geladen werden.")
    else:
        tourn_df = pd.DataFrame(tournaments)
        tourn_df["date"] = pd.to_datetime(tourn_df["date"]).dt.date

        # ── Übersicht Metriken
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Turniere geladen", len(tourn_df))
        with m2:
            st.metric("Gesamt Spieler", f"{tourn_df['players'].sum():,}")
        with m3:
            st.metric("Größtes Turnier", f"{tourn_df['players'].max():,} Spieler")
        with m4:
            latest = tourn_df["date"].max()
            st.metric("Letztes Turnier", str(latest))

        st.divider()

        tourn_tab1, tourn_tab2, tourn_tab3 = st.tabs([
            "📋 Turnierübersicht", "🎯 Leader Meta-Analyse", "🃏 Deck Details"
        ])

        with tourn_tab1:
            st.subheader("Alle Turniere")

            # Filter
            c1, c2 = st.columns(2)
            with c1:
                formats = ["Alle"] + sorted(tourn_df["format"].dropna().unique().tolist())
                sel_format = st.selectbox("Format/Set", formats, key="t_format")
            with c2:
                min_players = st.slider("Mindest-Spielerzahl", 0, 500, 64, 32)

            filtered_t = tourn_df.copy()
            if sel_format != "Alle":
                filtered_t = filtered_t[filtered_t["format"] == sel_format]
            filtered_t = filtered_t[filtered_t["players"] >= min_players]
            filtered_t = filtered_t.sort_values("date", ascending=False)

            # Spieler pro Turnier Chart
            fig = px.bar(
                filtered_t.head(30), x="name", y="players",
                title="Spielerzahl pro Turnier (neueste 30)",
                color="players", color_continuous_scale="Blues",
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                paper_bgcolor="rgba(0,0,0,0)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Turniere über Zeit
            monthly = filtered_t.copy()
            monthly["monat"] = pd.to_datetime(monthly["date"]).dt.to_period("M").astype(str)
            monthly_counts = monthly.groupby("monat").agg(
                Turniere=("id", "count"),
                Spieler=("players", "sum")
            ).reset_index()
            fig2 = px.line(monthly_counts, x="monat", y="Spieler",
                           title="Gesamte Spieler pro Monat (Aktivität der Community)",
                           markers=True)
            fig2.update_traces(line_color="#3498db")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Steigende Linie = wachsendes Interesse am Spiel.")

            # Tabelle
            show_t = [c for c in ["date", "name", "format", "players"] if c in filtered_t.columns]
            st.dataframe(filtered_t[show_t].reset_index(drop=True),
                         use_container_width=True, height=350)

        with tourn_tab2:
            st.subheader("Leader Meta-Analyse")
            st.caption("Welche Leader dominieren die Turniere?")

            # Turnier auswählen für Detailanalyse
            st.info("Wähle ein Turnier um die Leader-Verteilung zu analysieren.")

            recent = tourn_df.sort_values("date", ascending=False).head(50)
            tourn_options = {
                f"{row['name']} ({row['players']} Spieler, {row['date']})": row["id"]
                for _, row in recent.iterrows()
            }

            selected_tourn = st.selectbox(
                "Turnier auswählen",
                options=list(tourn_options.keys()),
                key="meta_tourn"
            )

            if selected_tourn:
                tourn_id = tourn_options[selected_tourn]

                with st.spinner("Platzierungen werden geladen..."):
                    standings = load_standings(tourn_id)

                if not standings:
                    st.warning("Keine Daten für dieses Turnier verfügbar.")
                else:
                    stand_df = pd.DataFrame(standings)

                    # Wins/Losses extrahieren
                    if "record" in stand_df.columns:
                        stand_df["wins"]   = stand_df["record"].apply(lambda x: x.get("wins", 0) if isinstance(x, dict) else 0)
                        stand_df["losses"] = stand_df["record"].apply(lambda x: x.get("losses", 0) if isinstance(x, dict) else 0)
                        stand_df["winrate"] = (stand_df["wins"] / (stand_df["wins"] + stand_df["losses"]).replace(0, 1) * 100).round(1)

                    # Leader extrahieren
                    if "deck" in stand_df.columns:
                        stand_df["leader"] = stand_df["deck"].apply(
                            lambda x: x.get("name", "Unbekannt") if isinstance(x, dict) else "Unbekannt"
                        )

                        # Metriken
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Teilnehmer", len(stand_df))
                        with m2:
                            top_leader = stand_df["leader"].value_counts().index[0]
                            st.metric("Meistgespielter Leader", top_leader)
                        with m3:
                            unique_leaders = stand_df["leader"].nunique()
                            st.metric("Verschiedene Leader", unique_leaders)

                        # Leader Verteilung
                        leader_counts = stand_df["leader"].value_counts().reset_index()
                        leader_counts.columns = ["Leader", "Anzahl Spieler"]
                        leader_counts["Anteil %"] = (leader_counts["Anzahl Spieler"] / len(stand_df) * 100).round(1)

                        fig = px.bar(
                            leader_counts.head(15), x="Anzahl Spieler", y="Leader",
                            orientation="h",
                            title="Leader Verteilung (Top 15)",
                            color="Anzahl Spieler",
                            color_continuous_scale="Reds",
                            hover_data=["Anteil %"],
                        )
                        fig.update_layout(
                            yaxis={"categoryorder": "total ascending"},
                            paper_bgcolor="rgba(0,0,0,0)",
                            height=500,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Winrate pro Leader
                        if "winrate" in stand_df.columns:
                            leader_wr = stand_df.groupby("leader").agg(
                                Spieler=("leader", "count"),
                                Ø_Winrate=("winrate", "mean"),
                                Ø_Wins=("wins", "mean"),
                            ).reset_index()
                            leader_wr = leader_wr[leader_wr["Spieler"] >= 3]
                            leader_wr["Ø_Winrate"] = leader_wr["Ø_Winrate"].round(1)
                            leader_wr["Ø_Wins"] = leader_wr["Ø_Wins"].round(1)
                            leader_wr = leader_wr.sort_values("Ø_Winrate", ascending=False)

                            fig2 = px.bar(
                                leader_wr.head(15), x="Ø_Winrate", y="leader",
                                orientation="h",
                                title="Durchschnittliche Winrate pro Leader (min. 3 Spieler)",
                                color="Ø_Winrate",
                                color_continuous_scale="RdYlGn",
                                hover_data=["Spieler", "Ø_Wins"],
                            )
                            fig2.update_layout(
                                yaxis={"categoryorder": "total ascending"},
                                paper_bgcolor="rgba(0,0,0,0)",
                                height=500,
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                            st.caption("Grün = hohe Winrate · Rot = niedrige Winrate")

                        # Top 8 Platzierungen
                        st.subheader("Top 8")
                        top8 = stand_df[stand_df["placing"] <= 8].sort_values("placing")
                        show_cols = [c for c in ["placing", "name", "leader", "wins", "losses", "winrate"] if c in top8.columns]
                        st.dataframe(top8[show_cols].reset_index(drop=True), use_container_width=True)
                    else:
                        st.info("Keine Deck-Daten für dieses Turnier verfügbar.")
                        show_cols = [c for c in ["placing", "name", "wins", "losses"] if c in stand_df.columns]
                        st.dataframe(stand_df[show_cols].head(20).reset_index(drop=True), use_container_width=True)

with tourn_tab3:
            st.subheader("🃏 Deck Details")
            st.info("Wähle zuerst ein Turnier im Tab 'Leader Meta-Analyse' — dann erscheinen hier die Decklisten.")
            if "stand_df" in dir() and "leader" in stand_df.columns:
                top16 = stand_df[stand_df["placing"] <= 16].sort_values("placing")
                for _, row in top16.iterrows():
                    label = f"#{int(row['placing'])} — {row.get('name', '?')} · {row.get('leader', '?')}"
                    with st.expander(label):
                        decklist = row.get("decklist", None)
                        if not decklist or not isinstance(decklist, dict):
                            st.write("Keine Deckliste verfügbar.")
                            continue

                        # Karten aus Decklist extrahieren
                        # Limitless Format: {"leader": [...], "main": [...]}
                        all_cards = []
                        for section_name, section_cards in decklist.items():
                            if isinstance(section_cards, list):
                                for entry in section_cards:
                                    if isinstance(entry, dict):
                                        card_id  = entry.get("id", entry.get("card", ""))
                                        count    = entry.get("count", 1)
                                        all_cards.append({
                                            "id": str(card_id),
                                            "count": count,
                                            "section": section_name,
                                        })

                            if not all_cards:
                            st.write("Deckliste konnte nicht gelesen werden.")
                            st.json(decklist)
                            continue
                        
                        # Zeige rohe Deckliste zur Diagnose
                        with st.expander("🔧 Rohdaten"):
                             st.json(decklist)
                        # Karten nach Sektion gruppieren
                        sections = {}
                        for c in all_cards:
                            s = c["section"]
                            if s not in sections:
                                sections[s] = []
                            sections[s].append(c)

                        for section_name, cards in sections.items():
                            total = sum(c["count"] for c in cards)
                            st.markdown(f"**{section_name.capitalize()} ({total} Karten)**")

                            # Karten in Grid anzeigen
                            cards_per_row = 5
                            for i in range(0, len(cards), cards_per_row):
                                chunk = cards[i:i+cards_per_row]
                                cols = st.columns(cards_per_row)
                                for j, card in enumerate(chunk):
                                    with cols[j]:
                                        card_id = card["id"]
                                        count   = card["count"]
                                        # Bild-URL aus OPTCG API Format aufbauen
                                        img_url = f"https://optcgapi.com/media/static/Card_Images/{card_id}.jpg"
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.write("🃏")
                                        st.caption(f"**x{count}** {card_id}")
                            st.write(f"DEBUG: {card}")

# ── Tab 7: Kartensuche ───────────────────────────────────────────────────────
with tab7:
    st.subheader("Kartensuche")

    c1, c2, c3 = st.columns(3)
    with c1:
        search7 = st.text_input("Name enthält...", placeholder="z.B. Luffy", key="search7")
    with c2:
        col_opts = ["Alle"] + sorted(df[COLOR].dropna().unique().tolist())
        sel_color = st.selectbox("Farbe", col_opts, key="search_color")
    with c3:
        if TYPE in df.columns:
            type_opts = ["Alle"] + sorted(df[TYPE].dropna().unique().tolist())
            sel_type = st.selectbox("Typ", type_opts, key="search_type")
        else:
            sel_type = "Alle"

    show_images = st.toggle("Kartenbilder anzeigen", value=False, key="search_images")

    result = df.copy()
    if search7:
        result = result[result[NAME].astype(str).str.contains(search7, case=False, na=False)]
    if sel_color != "Alle":
        result = result[result[COLOR].astype(str).str.contains(sel_color, na=False)]
    if sel_type != "Alle" and TYPE in df.columns:
        result = result[result[TYPE].astype(str) == sel_type]

    st.write(f"**{len(result)}** Karten gefunden")

    if show_images and IMAGE in result.columns:
        cards_per_row = 5
        items = result.head(30).to_dict("records")
        for i in range(0, len(items), cards_per_row):
            cols = st.columns(cards_per_row)
            for j, card in enumerate(items[i:i+cards_per_row]):
                with cols[j]:
                    img_url = card.get(IMAGE, "")
                    if img_url and str(img_url) != "nan":
                        try:
                            st.image(str(img_url), use_container_width=True)
                        except:
                            st.write("🃏")
                    st.caption(f"**{card.get(NAME, '')}**")
                    price = card.get(PRICE, "")
                    if price and str(price) != "nan":
                        st.caption(f"💰 ${float(price):.2f}")
        if len(result) > 30:
            st.info("Zeige erste 30 Karten. Suche verfeinern für mehr.")
    else:
        show_cols = [c for c in [NAME, COLOR, COST, POWER, TYPE, SET_ID, RARITY, PRICE, TEXT] if c in result.columns]
        st.dataframe(result[show_cols].reset_index(drop=True),
                     use_container_width=True, height=400)

    csv = result.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Als CSV herunterladen", data=csv,
                       file_name="optcg_karten.csv", mime="text/csv")

st.divider()
st.caption("Daten: optcgapi.com · Kein offizielles Bandai-Produkt")
