import streamlit as st
import requests
import pandas as pd
import plotly.express as px
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

with st.spinner("Kartendaten werden geladen..."):
    df = load_all_cards()

if df.empty:
    st.error("Keine Daten geladen.")
    st.stop()

# Feldnamen direkt aus der API
NAME   = "card_name"
COLOR  = "card_color"
TYPE   = "card_type"
COST   = "card_cost"
POWER  = "card_power"
SET    = "set_name"
SET_ID = "set_id"
RARITY = "rarity"
TEXT   = "card_text"
LIFE   = "life"
COUNTER = "counter_amount"

# Numerische Felder bereinigen
for col in [COST, POWER, LIFE, COUNTER]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# ─── Metriken oben ──────────────────────────────────────────────────────────
st.divider()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Karten gesamt", len(df))
with col2:
    st.metric("Farben", df[COLOR].nunique() if COLOR in df.columns else "–")
with col3:
    st.metric("Sets", df[SET_ID].nunique() if SET_ID in df.columns else "–")
with col4:
    if TYPE in df.columns:
        leader_count = len(df[df[TYPE].astype(str).str.upper() == "LEADER"])
        st.metric("Leader", leader_count)
    else:
        st.metric("Leader", "–")

st.divider()

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Kartentypen", "🎨 Farb-Analyse", "💰 Kosten-Kurve", "🔍 Kartensuche"
])

color_map = {
    "Red": "#e74c3c", "Blue": "#3498db", "Green": "#2ecc71",
    "Purple": "#9b59b6", "Black": "#2c3e50", "Yellow": "#f1c40f", "White": "#bdc3c7",
}

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
            fig2 = px.bar(set_counts, x="Set", y="Karten",
                          title="Karten pro Set",
                          color="Karten", color_continuous_scale="Reds")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

    if RARITY in df.columns:
        st.subheader("Verteilung nach Seltenheit")
        rarity_counts = df[RARITY].value_counts().reset_index()
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

        fig = px.bar(color_df, x="Farbe", y="Anzahl",
                     title="Karten pro Farbe",
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
                          title="Welche Typen hat jede Farbe?",
                          barmode="stack")
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

        fig = px.bar(cost_counts, x="Kosten", y="Anzahl",
                     title="Kostenverteilung",
                     color="Anzahl", color_continuous_scale="Reds")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        if POWER in df.columns:
            st.subheader("Power-Effizienz pro Kostenpunkt")
            eff = cost_df[cost_df[COST] > 0].copy()
            eff["power_per_cost"] = eff[POWER] / eff[COST]
            eff = eff[eff["power_per_cost"].notna()]
            avg = eff.groupby(COST)["power_per_cost"].mean().reset_index()
            avg.columns = ["Kosten", "Ø Power pro Kosten"]
            avg["Ø Power pro Kosten"] = avg["Ø Power pro Kosten"].round(0)

            fig2 = px.line(avg, x="Kosten", y="Ø Power pro Kosten",
                           title="Wie viel Power bekommst du pro Kostenpunkt?",
                           markers=True)
            fig2.update_traces(line_color="#e94560", marker_color="#e94560")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Hohe Werte = gutes Preis-Leistungs-Verhältnis. Nützlich für Deck-Optimierung.")

        if "market_price" in df.columns:
            st.subheader("Preis vs. Kostenpunkt")
            price_df = cost_df[cost_df["market_price"].notna()].copy()
            price_df["market_price"] = pd.to_numeric(price_df["market_price"], errors="coerce")
            avg_price = price_df.groupby(COST)["market_price"].mean().reset_index()
            avg_price.columns = ["Kosten", "Ø Marktpreis ($)"]
            avg_price["Ø Marktpreis ($)"] = avg_price["Ø Marktpreis ($)"].round(2)
            fig3 = px.bar(avg_price, x="Kosten", y="Ø Marktpreis ($)",
                          title="Durchschnittlicher Marktpreis pro Kostenpunkt",
                          color="Ø Marktpreis ($)", color_continuous_scale="Greens")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning(f"Feld '{COST}' nicht gefunden.")

# ── Tab 4: Kartensuche ───────────────────────────────────────────────────────
with tab4:
    st.subheader("Kartensuche")

    c1, c2, c3 = st.columns(3)
    with c1:
        search = st.text_input("Name enthält...", placeholder="z.B. Luffy")
    with c2:
        if COLOR in df.columns:
            col_opts = ["Alle"] + sorted(df[COLOR].dropna().unique().tolist())
            sel_color = st.selectbox("Farbe", col_opts)
        else:
            sel_color = "Alle"
    with c3:
        if TYPE in df.columns:
            type_opts = ["Alle"] + sorted(df[TYPE].dropna().unique().tolist())
            sel_type = st.selectbox("Typ", type_opts)
        else:
            sel_type = "Alle"

    result = df.copy()
    if search:
        result = result[result[NAME].astype(str).str.contains(search, case=False, na=False)]
    if sel_color != "Alle":
        result = result[result[COLOR].astype(str).str.contains(sel_color, na=False)]
    if sel_type != "Alle" and TYPE in df.columns:
        result = result[result[TYPE].astype(str) == sel_type]

    st.write(f"**{len(result)}** Karten gefunden")

    show_cols = [c for c in [NAME, COLOR, COST, POWER, TYPE, SET_ID, RARITY, "market_price", TEXT] if c in result.columns]
    st.dataframe(result[show_cols].reset_index(drop=True), use_container_width=True, height=400)

    csv = result.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Als CSV herunterladen", data=csv,
                       file_name="optcg_karten.csv", mime="text/csv")

st.divider()
st.caption("Daten: optcgapi.com · Kein offizielles Bandai-Produkt")