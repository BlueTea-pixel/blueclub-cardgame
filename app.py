import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

st.set_page_config(page_title="OP TCG Meta Analyzer", page_icon="🏴‍☠️", layout="wide")

st.title("🏴‍☠️ One Piece TCG — Meta Analyzer")
st.caption("Powered by optcgapi.com & Limitless TCG · Daten automatisch geladen")

# ─── Funktionen ─────────────────────────────────────────────────────────────

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
        st.error(f"Fehler beim Laden der Kartendaten: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_don_cards():
    try:
        r = requests.get("https://optcgapi.com/api/allDonCards/", timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return pd.DataFrame(data)
        for key in data:
            if isinstance(data[key], list):
                return pd.DataFrame(data[key])
        return pd.DataFrame(data)
    except:
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

@st.cache_data(ttl=1800)
def load_top_decklists(tournament_ids, top_n=8):
    all_cards = []
    for tid in tournament_ids:
        standings = load_standings(tid)
        if not standings:
            continue
        for player in standings:
            if int(player.get("placing") or 999) > top_n:
                continue
            decklist = player.get("decklist", {})
            if not decklist or not isinstance(decklist, dict):
                continue
            for section_name, section_cards in decklist.items():
                if section_name == "leader":
                    continue
                if isinstance(section_cards, list):
                    for entry in section_cards:
                        if isinstance(entry, dict):
                            card_set = entry.get("set", "")
                            card_num = entry.get("number", "")
                            card_id  = f"{card_set}-{card_num}" if card_set and card_num else ""
                            count    = entry.get("count", 1)
                            name     = entry.get("name", card_id)
                            if card_id:
                                all_cards.append({
                                    "id": card_id,
                                    "name": name,
                                    "count": count,
                                    "section": section_name,
                                    "tournament": tid,
                                    "placing": player.get("placing", 0),
                                })
    return all_cards

# ─── Daten laden ────────────────────────────────────────────────────────────

with st.spinner("Kartendaten werden geladen..."):
    df = load_all_cards()

if df.empty:
    st.error("Keine Daten geladen.")
    st.stop()

# Don Karten laden und zusammenführen
don_df = load_don_cards()
if not don_df.empty:
    don_df["is_don"] = True
    df["is_don"] = False
    df = pd.concat([df, don_df], ignore_index=True)
else:
    df["is_don"] = False

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

# Parallel erkennen
df["is_parallel"] = (
    df[NAME].astype(str).str.contains("Parallel|Alt Art|Special", case=False, na=False) |
    df["card_image_id"].astype(str).str.contains("_p", na=False)
) if "card_image_id" in df.columns else df[NAME].astype(str).str.contains("Parallel|Alt Art", case=False, na=False)

# Seltenheits-Mapping
rarity_order = {
    "L":   ("Leader", 1),
    "C":   ("Common", 2),
    "UC":  ("Uncommon", 3),
    "R":   ("Rare", 4),
    "SR":  ("Super Rare", 5),
    "SEC": ("Secret Rare", 6),
    "SP":  ("Special Card", 7),
    "TR":  ("Treasure Rare", 8),
    "MR":  ("Manga Rare", 9),
}
df["rarity_label"] = df[RARITY].map(lambda x: rarity_order.get(str(x), (str(x), 0))[0])
df["rarity_rank"]  = df[RARITY].map(lambda x: rarity_order.get(str(x), (str(x), 0))[1])

# Farbkarte für Ein- und Mehrfarben
DECK_COLORS = {
    "Red":    "#e74c3c",
    "Blue":   "#3498db",
    "Green":  "#2ecc71",
    "Purple": "#9b59b6",
    "Black":  "#4a4a4a",
    "Yellow": "#f1c40f",
    "White":  "#bdc3c7",
}

def get_color_for_value(color_str):
    """Gibt die erste Farbe eines Farbstrings zurück."""
    if not color_str or str(color_str) == "nan":
        return "#888"
    parts = str(color_str).replace("/", ";").replace(",", ";").split(";")
    first = parts[0].strip()
    return DECK_COLORS.get(first, "#888")

# ─── Metriken oben ──────────────────────────────────────────────────────────
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Karten gesamt", len(df[df["is_don"] == False]))
with col2:
    st.metric("Farben", df[COLOR].nunique() if COLOR in df.columns else "–")
with col3:
    st.metric("Sets", df[SET_ID].nunique() if SET_ID in df.columns else "–")
with col4:
    parallel_count = df["is_parallel"].sum()
    st.metric("Parallel / Alt Art", int(parallel_count))

st.divider()

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📖 Einführung & Kartentypen",
    "🎨 Farb-Analyse",
    "🃏 Don-Kurve",
    "💎 Undervalued Cards",
    "🌟 Chase Cards",
    "📈 Marktbewertung",
    "🏆 Turnierdaten",
    "🔍 Kartensuche",
])

# ── Tab 1: Einführung & Kartentypen ─────────────────────────────────────────
with tab1:
    st.subheader("Willkommen beim One Piece TCG Meta Analyzer")

    with st.expander("📖 Was ist das One Piece Kartenspiel? — Einführung für Einsteiger", expanded=True):
        st.markdown("""
**Das One Piece Trading Card Game (OP TCG)** ist ein strategisches Sammelkartenspiel von Bandai,
das seit 2022 erscheint. Jeder Spieler baut ein Deck aus 50 Karten rund um einen **Leader** —
einer besonderen Karte die deinen Spielstil bestimmt.

---

### 🎯 Das Spielziel
Bringe die **Life Cards** deines Gegners auf null und greife dann seinen Leader direkt an — dann gewinnst du.
Jeder Spieler startet mit 4–5 Life Cards (je nach Leader).

---

### 🃏 Kartentypen
| Typ | Beschreibung |
|-----|-------------|
| **Leader** | Deine Anführer-Karte. Bestimmt Farbe, Spielstil und Startpunkte. Jedes Deck hat genau einen. |
| **Character** | Charaktere die du auf deinem Feld platzierst — sie greifen an und verteidigen. |
| **Event** | Einmalige Effekte die sofort wirken, dann auf den Ablagestapel. |
| **Stage** | Dauerhafte Karten die auf dem Feld bleiben und passive Effekte geben. |

---

### 🔴 Don!! — Die Spielwährung
**Don!!** sind rote Zahlungsmarken — die Währung des Spiels. Jede Runde bekommst du mehr Don!!
und kannst sie ausgeben um Karten zu spielen. Karten kosten zwischen 1 und 10 Don!!.
Du kannst Don!! auch an Karten **anlegen** um sie zu verstärken.

---

### 🎨 Die Farben und ihre Spielstile
| Farbe | Strategie |
|-------|-----------|
| 🔴 **Rot** | Aggressiv · Viel Angriff · Schnelle Siege |
| 🔵 **Blau** | Kontrolle · Karten zurückschicken · Tempo stören |
| 🟢 **Grün** | Don!! Manipulation · Ruhende Don!! aktivieren · Überraschungsangriffe |
| 🟣 **Lila** | Kostenreduktion · Mächtige teure Karten früh spielen |
| ⚫ **Schwarz** | KO-Effekte · Gegnerische Karten eliminieren · Kontrolle |
| 🟡 **Gelb** | Life-Manipulation · Aus dem Life ziehen · Defensive Stärke |

---

### 📦 Die Sets (OP01–OP14)
Jedes Set bringt neue Karten, neue Leader und neue Strategien. **OP** steht für "One Piece",
die Zahl danach ist die Set-Nummer. **ST** steht für Starter Deck — fertige Einstiegsdecks.
        """)

    st.divider()
    st.subheader("Kartentypen im Überblick")

    c1, c2 = st.columns(2)
    with c1:
        if TYPE in df.columns:
            type_counts = df[df["is_don"] == False][TYPE].value_counts().reset_index()
            type_counts.columns = ["Typ", "Anzahl"]
            fig = px.pie(type_counts, values="Anzahl", names="Typ",
                         title="Verteilung nach Kartentyp", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Zeigt wie viele Karten jedes Typs im gesamten Kartenpool existieren. Character-Karten machen den Großteil aus — sie sind das Herzstück jedes Decks.")

    with c2:
        if SET_ID in df.columns:
            set_counts = df[df["is_don"] == False][SET_ID].value_counts().reset_index()
            set_counts.columns = ["Set", "Karten"]
            set_counts = set_counts.sort_values("Set")
            fig2 = px.bar(set_counts, x="Set", y="Karten",
                          title="Karten pro Set",
                          color="Karten", color_continuous_scale="Reds")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Zeigt wie viele Karten jedes Set enthält. Neuere Sets haben oft mehr Karten da das Spiel gewachsen ist.")

    st.divider()
    st.subheader("Seltenheitsstufen — was bedeuten sie?")
    st.markdown("""
Jede Karte hat eine **Seltenheitsstufe** die bestimmt wie schwer sie zu ziehen ist.
Je seltener, desto wertvoller — und desto beeindruckender das Artwork.
    """)

    if RARITY in df.columns and IMAGE in df.columns:
        rarity_info = {
            "C":   ("Common", "Die häufigste Karte. Jedes Pack enthält mehrere davon."),
            "UC":  ("Uncommon", "Etwas seltener als Common. Immer noch regelmäßig zu ziehen."),
            "R":   ("Rare", "Ca. 1 pro Pack. Oft spielstarke Karten."),
            "SR":  ("Super Rare", "Ca. 6–7 pro Box. Sehr begehrt für starke Decks."),
            "SEC": ("Secret Rare", "Ca. 4–6 pro Case (12 Boxen). Extrem wertvoll."),
            "SP":  ("Special Card", "Seltene Spezialversionen mit besonderem Artwork."),
            "TR":  ("Treasure Rare", "Extrem selten. Oft die wertvollsten Karten überhaupt."),
            "MR":  ("Manga Rare", "Seltenste Kategorie. Fast nie in einer einzelnen Box."),
            "L":   ("Leader", "Anführer-Karten. Garantiert in jeder Box enthalten."),
        }

        # Beispielkarte: Zoro — suche nach verschiedenen Versionen
        example_cards = df[
            df[NAME].astype(str).str.contains("Roronoa Zoro|Zoro", case=False, na=False) &
            df[IMAGE].notna()
        ].copy()

        # Eine Karte pro Seltenheit finden
        shown_rarities = []
        for rarity_code, (rarity_name, rarity_desc) in rarity_info.items():
            rarity_cards = example_cards[example_cards[RARITY] == rarity_code]
            if rarity_cards.empty:
                # Falls kein Zoro — nimm irgendeine Karte dieser Seltenheit
                rarity_cards = df[
                    (df[RARITY] == rarity_code) & df[IMAGE].notna()
                ]
            if not rarity_cards.empty:
                shown_rarities.append({
                    "code": rarity_code,
                    "name": rarity_name,
                    "desc": rarity_desc,
                    "image": rarity_cards.iloc[0][IMAGE],
                    "card_name": rarity_cards.iloc[0][NAME],
                })

        cols_per_row = 4
        for i in range(0, len(shown_rarities), cols_per_row):
            chunk = shown_rarities[i:i+cols_per_row]
            cols = st.columns(cols_per_row)
            for j, r in enumerate(chunk):
                with cols[j]:
                    try:
                        st.image(r["image"], use_container_width=True)
                    except:
                        st.write("🃏")
                    st.markdown(f"**{r['code']} — {r['name']}**")
                    st.caption(r["desc"])

    rarity_counts = df[df["is_don"] == False]["rarity_label"].value_counts().reset_index()
    rarity_counts.columns = ["Seltenheit", "Anzahl"]
    fig3 = px.bar(rarity_counts, x="Seltenheit", y="Anzahl",
                  title="Anzahl Karten pro Seltenheitsstufe",
                  color="Anzahl", color_continuous_scale="Blues")
    fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Common-Karten dominieren mengenmäßig — das spiegelt die Ziehwahrscheinlichkeiten wider. Seltene Karten sind bewusst rar gehalten.")

# ── Tab 2: Farb-Analyse ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Farbverteilung")

    base_df = df[df["is_don"] == False].copy()

    if COLOR in base_df.columns:
        # Einzelfarben extrahieren
        all_colors = []
        for c in base_df[COLOR].dropna():
            for part in str(c).replace("/", ";").replace(",", ";").split(";"):
                cleaned = part.strip()
                if cleaned:
                    all_colors.append(cleaned)

        color_counts = Counter(all_colors)
        color_df = pd.DataFrame(color_counts.items(), columns=["Farbe", "Anzahl"]).sort_values("Anzahl", ascending=False)
        color_df["Farbe_hex"] = color_df["Farbe"].map(lambda x: DECK_COLORS.get(x, "#888"))

        fig = px.bar(color_df, x="Farbe", y="Anzahl",
                     title="Karten pro Farbe",
                     color="Farbe",
                     color_discrete_map=DECK_COLORS)
        fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Zeigt wie viele Karten jede Farbe im gesamten Kartenpool hat. Mehrfarbige Karten werden bei jeder ihrer Farben gezählt. Eine ausgeglichene Verteilung bedeutet dass jede Farbe gut unterstützt wird.")

        st.divider()

        # Farbkombinationen der Leader
        st.subheader("Farbkombinationen der Leader")
        st.markdown("Manche Leader spielen zwei Farben gleichzeitig — das ermöglicht hybride Strategien.")

        if TYPE in base_df.columns:
            leaders = base_df[base_df[TYPE].astype(str).str.upper() == "LEADER"].copy()
            leaders = leaders[~leaders["is_parallel"]]

            multi_leaders = leaders[leaders[COLOR].astype(str).str.contains("/", na=False)]
            single_leaders = leaders[~leaders[COLOR].astype(str).str.contains("/", na=False)]

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Einfarb-Leader", len(single_leaders))
            with c2:
                st.metric("Mehrfarb-Leader", len(multi_leaders))

            if not multi_leaders.empty:
                combo_counts = multi_leaders[COLOR].value_counts().reset_index()
                combo_counts.columns = ["Kombination", "Anzahl"]
                combo_counts["Farbe1"] = combo_counts["Kombination"].apply(
                    lambda x: DECK_COLORS.get(str(x).split("/")[0].strip(), "#888")
                )

                fig2 = px.bar(combo_counts.head(15), x="Anzahl", y="Kombination",
                              orientation="h",
                              title="Häufigste Farbkombinationen bei Leadern",
                              color="Kombination",
                              color_discrete_map={row["Kombination"]: row["Farbe1"] for _, row in combo_counts.iterrows()})
                fig2.update_layout(showlegend=False,
                                   yaxis={"categoryorder": "total ascending"},
                                   paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("Mehrfarb-Leader können Karten beider Farben nutzen — das macht sie flexibler aber auch komplexer zu spielen.")

        st.divider()

        # Set-Heatmap
        st.subheader("Farbverteilung pro Set")
        st.markdown("Zeigt welche Farben in welchem Set besonders stark vertreten sind — nützlich um zu sehen welche Sets für deinen Favoriten-Leader relevant sind.")

        single_color = base_df[~base_df[COLOR].astype(str).str.contains("/", na=False)].copy()
        single_color = single_color[single_color[SET_ID].notna() & single_color[COLOR].notna()]

        heatmap_data = single_color.groupby([SET_ID, COLOR]).size().reset_index(name="Anzahl")
        heatmap_pivot = heatmap_data.pivot(index=COLOR, columns=SET_ID, values="Anzahl").fillna(0)

        fig3 = px.imshow(
            heatmap_pivot,
            title="Karten pro Farbe und Set (Heatmap)",
            color_continuous_scale="Reds",
            aspect="auto",
        )
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Helle Felder = viele Karten dieser Farbe in diesem Set. Dunkle Felder = wenige. So siehst du auf einen Blick welche Sets für welche Farbe am ergiebigsten sind.")

# ── Tab 3: Don-Kurve ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("Don-Kurve")
    st.markdown("""
**Don!!** ist die Spielwährung im One Piece TCG. Jede Runde erhältst du mehr Don!!-Karten
und kannst sie ausgeben um Charaktere, Events und Stages zu spielen.
Die Don-Kurve zeigt wie die Kosten deiner Karten verteilt sind — ein ausgewogenes Deck
hat eine gute Mischung aus günstigen und teuren Karten.
    """)

    base_df2 = df[df["is_don"] == False].copy()

    if COST in base_df2.columns:
        cost_df = base_df2[base_df2[COST].notna() & (base_df2[COST] >= 0)].copy()

        c_left, c_right = st.columns([1, 2])
        with c_left:
            farben_liste = ["Alle"] + sorted(base_df2[COLOR].dropna().unique().tolist())
            selected = st.selectbox("Filtern nach Farbe", farben_liste, key="don_color")
        with c_right:
            if TYPE in base_df2.columns:
                typen_liste = ["Alle"] + sorted(base_df2[TYPE].dropna().unique().tolist())
                selected_type = st.selectbox("Filtern nach Typ", typen_liste, key="don_type")
            else:
                selected_type = "Alle"

        if selected != "Alle":
            cost_df = cost_df[cost_df[COLOR].astype(str).str.contains(selected, na=False)]
        if selected_type != "Alle":
            cost_df = cost_df[cost_df[TYPE].astype(str) == selected_type]

        cost_counts = cost_df[COST].value_counts().reset_index().sort_values(COST)
        cost_counts.columns = ["Don", "Anzahl"]

        bar_color = DECK_COLORS.get(selected, "#e74c3c") if selected != "Alle" else "#e74c3c"

        fig = go.Figure(go.Bar(
            x=cost_counts["Don"],
            y=cost_counts["Anzahl"],
            marker_color=bar_color,
        ))
        fig.update_layout(
            title="Don-Kurve — Wie viele Karten kosten wie viel Don?",
            xaxis_title="Don-Kosten",
            yaxis_title="Anzahl Karten",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Ein ausgewogenes Deck hat viele günstige Karten (1–3 Don) für den frühen Spielverlauf und einige starke teure Karten (7–10 Don) als Finisher. Zu viele teure Karten = langsames Deck.")

        if POWER in base_df2.columns:
            st.subheader("Power-Effizienz pro Don-Kostenpunkt")
            eff = cost_df[cost_df[COST] > 0].copy()
            eff["power_per_don"] = eff[POWER] / eff[COST]
            eff = eff[eff["power_per_don"].notna()]
            avg = eff.groupby(COST)["power_per_don"].mean().reset_index()
            avg.columns = ["Don", "Ø Power pro Don"]
            avg["Ø Power pro Don"] = avg["Ø Power pro Don"].round(0)

            fig2 = px.line(avg, x="Don", y="Ø Power pro Don",
                           title="Wie viel Power bekommst du pro Don?",
                           markers=True)
            fig2.update_traces(line_color=bar_color, marker_color=bar_color)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Zeigt das Power-Preis-Verhältnis: Hohe Werte bedeuten viel Power für wenig Don. Günstige Karten sind oft effizienter — teure Karten rechtfertigen ihren Preis durch starke Effekte, nicht nur durch rohe Power.")

        if PRICE in base_df2.columns:
            st.subheader("Durchschnittlicher Marktpreis pro Don-Kostenpunkt")
            price_df = cost_df[cost_df[PRICE].notna()].copy()
            avg_price = price_df.groupby(COST)[PRICE].mean().reset_index()
            avg_price.columns = ["Don", "Ø Marktpreis ($)"]
            avg_price["Ø Marktpreis ($)"] = avg_price["Ø Marktpreis ($)"].round(2)

            fig3 = px.bar(avg_price, x="Don", y="Ø Marktpreis ($)",
                          title="Marktpreis nach Don-Kostenpunkt",
                          color="Ø Marktpreis ($)", color_continuous_scale="Greens")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Teure Don-Karten sind im Schnitt auch teurer im Markt — aber nicht immer. Günstige Karten mit starken Effekten können trotzdem sehr wertvoll sein.")

# ── Tab 4: Undervalued Cards ─────────────────────────────────────────────────
with tab4:
    st.subheader("💎 Undervalued Cards — stark aber günstig")

    col_info, _ = st.columns([1, 3])
    with col_info:
        with st.popover("ℹ️ Was ist der UV Score?"):
            st.markdown("""
**UV Score (Undervalued Score)** misst wie stark eine Karte ist
im Verhältnis zu ihrem Marktpreis.

**Berechnung:**
- 60% Power-Effizienz (Power ÷ Don-Kosten)
- 40% Preisvorteil (niedrigerer Preis = höherer Score)

**Score-Bedeutung:**
- **80–100** = Sehr stark und günstig — klarer Geheimtipp
- **60–80** = Gutes Preis-Leistungs-Verhältnis
- **40–60** = Durchschnittlich
- **unter 40** = Eher überteuert für die Spielstärke

Der Score ist **absolut** — nicht relativ zur Filterauswahl.
            """)

    st.caption("Karten mit hoher Spielstärke aber niedrigem Marktpreis — potenzielle Meta-Geheimtipps die Guides noch nicht entdeckt haben.")

    if COST in df.columns and POWER in df.columns and PRICE in df.columns:
        base_uv = df[df["is_don"] == False].copy()

        c1, c2, c3 = st.columns(3)
        with c1:
            max_price = st.slider("Max. Marktpreis ($)", 0.0,
                                  float(base_uv[PRICE].quantile(0.95) or 20), 5.0, 0.5)
        with c2:
            uv_colors = ["Alle"] + sorted(base_uv[COLOR].dropna().unique().tolist())
            uv_color = st.selectbox("Farbe", uv_colors, key="uv_color")
        with c3:
            uv_types = ["Alle"] + sorted(base_uv[TYPE].dropna().unique().tolist())
            uv_type = st.selectbox("Typ", uv_types, key="uv_type")

        # Score absolut berechnen (auf gesamtem Datensatz)
        scored_all = base_uv[
            base_uv[COST].notna() & base_uv[POWER].notna() &
            base_uv[PRICE].notna() & (base_uv[COST] > 0) & (base_uv[PRICE] > 0)
        ].copy()

        scored_all["power_efficiency"] = scored_all[POWER] / scored_all[COST]

        p_min, p_max   = scored_all["power_efficiency"].min(), scored_all["power_efficiency"].max()
        pr_min, pr_max = scored_all[PRICE].min(), scored_all[PRICE].max()

        scored_all["eff_score"]   = (scored_all["power_efficiency"] - p_min) / (p_max - p_min + 0.001)
        scored_all["price_score"] = 1 - (scored_all[PRICE] - pr_min) / (pr_max - pr_min + 0.001)
        scored_all["uv_score"]    = (scored_all["eff_score"] * 0.6 + scored_all["price_score"] * 0.4) * 100
        scored_all["uv_score"]    = scored_all["uv_score"].round(1)

        # Filter anwenden
        filtered = scored_all[scored_all[PRICE] <= max_price].copy()
        if uv_color != "Alle":
            filtered = filtered[filtered[COLOR].astype(str).str.contains(uv_color, na=False)]
        if uv_type != "Alle":
            filtered = filtered[filtered[TYPE].astype(str) == uv_type]
        filtered = filtered.sort_values("uv_score", ascending=False)

        if filtered.empty:
            st.warning("Keine Karten gefunden. Preis-Limit erhöhen?")
        else:
            top20 = filtered.head(20)

            # Farben für Balken
            bar_colors = [get_color_for_value(c) for c in top20[COLOR]]

            fig = go.Figure(go.Bar(
                x=top20["uv_score"],
                y=top20[NAME],
                orientation="h",
                marker_color=bar_colors,
                text=top20["uv_score"].astype(str),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>UV Score: %{x}<extra></extra>",
            ))
            fig.update_layout(
                title=f"Top {min(20, len(filtered))} Undervalued Cards",
                yaxis={"categoryorder": "total ascending"},
                paper_bgcolor="rgba(0,0,0,0)",
                height=600,
                xaxis_range=[0, 110],
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Balkenfarbe entspricht der Deck-Farbe der Karte. Längere Balken = besseres Preis-Leistungs-Verhältnis.")

            # Scatter
            st.subheader("Power-Effizienz vs. Marktpreis")
            st.caption("Karten **oben links** sind am interessantesten — hohe Stärke, niedriger Preis. Punkte rechts unten sind überteuert für ihre Spielstärke.")

            top50 = filtered.head(50)
            scatter_colors = [get_color_for_value(c) for c in top50[COLOR]]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=top50[PRICE],
                y=top50["power_efficiency"],
                mode="markers",
                marker=dict(
                    color=scatter_colors,
                    size=top50["uv_score"] / 5 + 5,
                    line=dict(width=1, color="white"),
                ),
                text=top50[NAME],
                hovertemplate="<b>%{text}</b><br>Preis: $%{x:.2f}<br>Power/Don: %{y:.0f}<extra></extra>",
            ))
            fig2.update_layout(
                xaxis_title="Marktpreis ($)",
                yaxis_title="Power pro Don",
                paper_bgcolor="rgba(0,0,0,0)",
            )
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

    chase_tab1, chase_tab2 = st.tabs(["🏆 Sammler-Chase Cards", "⚔️ Spieler-Chase Cards"])

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

                top15 = chase_df.head(15)
                bar_colors_chase = [get_color_for_value(c) for c in top15[COLOR]]

                fig = go.Figure(go.Bar(
                    x=top15[PRICE],
                    y=top15[NAME],
                    orientation="h",
                    marker_color=bar_colors_chase,
                ))
                fig.update_layout(
                    title="Top 15 wertvollste Karten",
                    yaxis={"categoryorder": "total ascending"},
                    xaxis_title="Marktpreis ($)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=500,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Balkenfarbe = Deck-Farbe der Karte. Die teuersten Karten sind fast immer Parallel- oder Alt-Art-Versionen beliebter Charaktere.")

                st.subheader("Durchschnittspreis nach Seltenheit")
                rarity_price = chase_df.groupby("rarity_label")[PRICE].agg(["mean", "max", "count"]).reset_index()
                rarity_price.columns = ["Seltenheit", "Ø Preis", "Max Preis", "Anzahl"]
                rarity_price["Ø Preis"] = rarity_price["Ø Preis"].round(2)
                rarity_price = rarity_price.sort_values("Ø Preis", ascending=False)

                fig2 = px.bar(rarity_price, x="Seltenheit", y="Ø Preis",
                              title="Durchschnittspreis pro Seltenheitsstufe",
                              color="Ø Preis", color_continuous_scale="YlOrRd",
                              hover_data=["Max Preis", "Anzahl"])
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("Zeigt wie viel eine Karte im Schnitt kostet je nach Seltenheit. Secret Rares und Manga Rares sind fast immer am wertvollsten.")

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
                            st.caption(f"**{card.get(NAME, '')}**")
                            st.caption(f"💰 ${float(card.get(PRICE, 0)):.2f} · {card.get('rarity_label', '')}")

                show_cols = [c for c in [NAME, SET_ID, "rarity_label", COLOR, PRICE, INV, "is_parallel"] if c in chase_df.columns]
                st.dataframe(chase_df[show_cols].reset_index(drop=True),
                             use_container_width=True, height=350)
                csv = chase_df[show_cols].to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Chase Cards als CSV", data=csv,
                                   file_name="optcg_chase_cards.csv", mime="text/csv")

    with chase_tab2:
        st.subheader("⚔️ Spieler-Chase Cards")
        st.caption("Karten die in den stärksten Turnier-Decks am häufigsten vorkommen.")

        c1, c2, c3 = st.columns(3)
        with c1:
            top_n = st.selectbox("Top Platzierungen analysieren", [4, 8, 16, 32], index=1)
        with c2:
            num_tournaments = st.slider("Anzahl Turniere", 5, 50, 20)
        with c3:
            min_appearances = st.slider("Mindest-Vorkommen", 1, 20, 3)

        with st.spinner("Analysiere Top-Decklisten..."):
            all_tournaments = load_tournaments(limit=200)
            if all_tournaments:
                tourn_df_chase = pd.DataFrame(all_tournaments)
                tourn_df_chase = tourn_df_chase[tourn_df_chase["players"] >= 64]
                recent_ids = tourn_df_chase.sort_values("date", ascending=False).head(num_tournaments)["id"].tolist()
                raw_cards = load_top_decklists(recent_ids, top_n=top_n)
            else:
                raw_cards = []

        if not raw_cards:
            st.warning("Keine Decklisten-Daten verfügbar.")
        else:
            cards_df = pd.DataFrame(raw_cards)
            freq = cards_df.groupby(["id", "name"]).agg(
                Vorkommen=("tournament", "nunique"),
                Gesamt_Kopien=("count", "sum"),
                Ø_Kopien=("count", "mean"),
            ).reset_index()
            freq["Ø_Kopien"] = freq["Ø_Kopien"].round(1)
            freq = freq[freq["Vorkommen"] >= min_appearances]
            freq = freq.sort_values("Vorkommen", ascending=False)

            if PRICE in df.columns and "card_set_id" in df.columns:
                price_lookup = df[["card_set_id", PRICE, COLOR, RARITY]].dropna(subset=["card_set_id"])
                price_lookup = price_lookup.rename(columns={"card_set_id": "id"})
                freq = freq.merge(price_lookup, on="id", how="left")

            if freq.empty:
                st.warning("Nicht genug Daten.")
            else:
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Analysierte Turniere", len(recent_ids))
                with m2:
                    st.metric("Analysierte Decklisten", cards_df["tournament"].nunique() * top_n)
                with m3:
                    st.metric("Unverzichtbare Karten", len(freq))
                with m4:
                    if PRICE in freq.columns:
                        avg_p = freq[PRICE].mean()
                        st.metric("Ø Preis", f"${avg_p:.2f}" if pd.notna(avg_p) else "–")

                st.divider()

                top_freq = freq.head(20)
                bar_colors_freq = [get_color_for_value(c) for c in top_freq.get(COLOR, [""] * len(top_freq))]

                fig = go.Figure(go.Bar(
                    x=top_freq["Vorkommen"],
                    y=top_freq["name"],
                    orientation="h",
                    marker_color=bar_colors_freq,
                ))
                fig.update_layout(
                    title=f"Top 20 Spieler-Chase Cards (Top {top_n} aus {len(recent_ids)} Turnieren)",
                    yaxis={"categoryorder": "total ascending"},
                    xaxis_title="Vorkommen in Turnieren",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=600,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Zeigt wie oft eine Karte in den Top-Decks verschiedener Turniere vorkommt. Hohe Werte = unverzichtbar für kompetitives Spiel.")

                if PRICE in freq.columns:
                    st.subheader("Vorkommen vs. Marktpreis")
                    st.caption("**Oben links** = häufig gespielt aber günstig = bestes Preis-Leistungs-Verhältnis für kompetitive Spieler.")
                    scatter_df = freq[freq[PRICE].notna()].copy()
                    scatter_colors2 = [get_color_for_value(c) for c in scatter_df.get(COLOR, [""] * len(scatter_df))]

                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=scatter_df[PRICE],
                        y=scatter_df["Vorkommen"],
                        mode="markers",
                        marker=dict(color=scatter_colors2, size=10, line=dict(width=1, color="white")),
                        text=scatter_df["name"],
                        hovertemplate="<b>%{text}</b><br>Preis: $%{x:.2f}<br>Vorkommen: %{y}<extra></extra>",
                    ))
                    fig2.update_layout(
                        xaxis_title="Marktpreis ($)",
                        yaxis_title="Vorkommen in Top-Decks",
                        paper_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                st.subheader("Top Chase Cards — Galerie")
                top_gallery = freq.head(15).to_dict("records")
                cols_g = st.columns(5)
                for i, card in enumerate(top_gallery):
                    with cols_g[i % 5]:
                        card_id = card["id"]
                        img_url = f"https://optcgapi.com/media/static/Card_Images/{card_id}.jpg"
                        try:
                            st.image(img_url, use_container_width=True)
                        except:
                            st.write("🃏")
                        st.caption(f"**{card['name']}**")
                        st.caption(f"In {card['Vorkommen']} Turnieren")
                        if PRICE in card and pd.notna(card.get(PRICE)):
                            st.caption(f"💰 ${float(card[PRICE]):.2f}")

                show_cols = [c for c in ["name", "id", "Vorkommen", "Ø_Kopien", PRICE, COLOR, RARITY] if c in freq.columns]
                st.dataframe(freq[show_cols].reset_index(drop=True),
                             use_container_width=True, height=400)
                csv = freq[show_cols].to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Spieler-Chase Cards als CSV", data=csv,
                                   file_name="optcg_player_chase.csv", mime="text/csv")

# ── Tab 6: Marktbewertung ────────────────────────────────────────────────────
with tab6:
    st.subheader("📈 Marktbewertung")
    st.caption("Aktueller Markt-Snapshot basierend auf TCGPlayer-Preisen.")

    if PRICE in df.columns:
        market_tab1, market_tab2, market_tab3 = st.tabs([
            "🌍 Gesamtmarkt", "📦 Set-Vergleich", "🎁 Pull-Wahrscheinlichkeiten"
        ])

        with market_tab1:
            st.subheader("Gesamtmarkt Überblick")
            valid = df[df[PRICE].notna() & (df[PRICE] > 0) & (df["is_don"] == False)]

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Gesamtwert aller Karten", f"${valid[PRICE].sum():,.0f}")
            with m2:
                st.metric("Ø Kartenpreis", f"${valid[PRICE].mean():.2f}")
            with m3:
                st.metric("Median Kartenpreis", f"${valid[PRICE].median():.2f}")
            with m4:
                st.metric("Karten über $10", len(valid[valid[PRICE] >= 10]))

            st.divider()

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
                         title="Preisverteilung aller Karten",
                         color="Anzahl", color_continuous_scale="Blues")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Die meisten Karten kosten zwischen $0–5. Nur wenige teure Chase Cards treiben den Gesamtwert nach oben.")

            st.subheader("Durchschnittspreis nach Farbe")
            single_color = valid[~valid[COLOR].astype(str).str.contains("/", na=False)]
            color_price = single_color.groupby(COLOR)[PRICE].agg(["mean", "sum", "count"]).reset_index()
            color_price.columns = ["Farbe", "Ø Preis", "Gesamtwert", "Karten"]
            color_price["Ø Preis"] = color_price["Ø Preis"].round(2)
            color_price = color_price.sort_values("Ø Preis", ascending=False)

            bar_colors_market = [DECK_COLORS.get(f, "#888") for f in color_price["Farbe"]]
            fig2 = go.Figure(go.Bar(
                x=color_price["Farbe"],
                y=color_price["Ø Preis"],
                marker_color=bar_colors_market,
            ))
            fig2.update_layout(
                title="Welche Farbe hat die teuersten Karten im Schnitt?",
                xaxis_title="Farbe",
                yaxis_title="Ø Preis ($)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Farben mit teuren Chase Cards oder starken Meta-Karten haben einen höheren Durchschnittspreis.")

        with market_tab2:
            st.subheader("Set-Vergleich")
            set_stats = df[df[PRICE].notna() & (df[PRICE] > 0) & (df["is_don"] == False)].groupby(SET_ID).agg(
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

            fig = px.bar(set_stats, x="Set", y="Gesamtwert ($)",
                         title="Gesamtwert aller Karten pro Set",
                         color="Gesamtwert ($)", color_continuous_scale="Greens")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Sets mit seltenen Chase Cards oder starken Meta-Karten haben einen höheren Gesamtwert.")

            fig2 = px.line(set_stats, x="Set", y="Ø Preis ($)",
                           title="Durchschnittlicher Kartenpreis pro Set",
                           markers=True)
            fig2.update_traces(line_color="#3498db", marker_color="#3498db")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Steigende Werte können auf ein wertvolleres Set hindeuten — oder auf weniger Karten mit höherer Einzelqualität.")

            st.dataframe(set_stats.reset_index(drop=True), use_container_width=True)

        with market_tab3:
            st.subheader("🎁 Pull-Wahrscheinlichkeiten & Erwarteter Box-Wert")
            st.markdown("""
Lohnt es sich eine Booster Box zu kaufen? Diese Analyse berechnet den **statistischen Erwartungswert**
basierend auf den offiziellen Pull-Raten und aktuellen Marktpreisen.
            """)

            # Pull-Raten pro Box (24 Packs)
            pull_rates = {
                "L":   {"pro_box": 8,    "label": "Leader"},
                "SR":  {"pro_box": 6.5,  "label": "Super Rare"},
                "SEC": {"pro_box": 0.42, "label": "Secret Rare"},      # 5/12 Boxen pro Case
                "SP":  {"pro_box": 0.25, "label": "Special Card"},
                "TR":  {"pro_box": 0.17, "label": "Treasure Rare"},
                "MR":  {"pro_box": 0.08, "label": "Manga Rare"},        # ca. 1 pro Case
                "R":   {"pro_box": 24,   "label": "Rare"},              # ca. 1 pro Pack
                "UC":  {"pro_box": 72,   "label": "Uncommon"},          # ca. 3 pro Pack
                "C":   {"pro_box": 168,  "label": "Common"},            # ca. 7 pro Pack
            }

            sets_for_box = ["Alle Sets"] + sorted(df[SET_ID].dropna().unique().tolist())
            selected_box_set = st.selectbox("Set auswählen", sets_for_box, key="box_set")

            box_price = st.number_input("Box-Preis ($)", min_value=50, max_value=300, value=90, step=5)

            if selected_box_set != "Alle Sets":
                set_df = df[(df[SET_ID] == selected_box_set) & df[PRICE].notna() & (df[PRICE] > 0) & (df["is_don"] == False)]
            else:
                set_df = df[df[PRICE].notna() & (df[PRICE] > 0) & (df["is_don"] == False)]

            if set_df.empty:
                st.warning("Keine Preisdaten für dieses Set.")
            else:
                results = []
                total_expected = 0

                for rarity_code, info in pull_rates.items():
                    rarity_cards = set_df[set_df[RARITY] == rarity_code]
                    if rarity_cards.empty:
                        continue
                    avg_price = rarity_cards[PRICE].mean()
                    expected_value = info["pro_box"] * avg_price
                    total_expected += expected_value
                    results.append({
                        "Seltenheit": info["label"],
                        "Ø pro Box": round(info["pro_box"], 2),
                        "Ø Kartenpreis ($)": round(avg_price, 2),
                        "Erwarteter Wert ($)": round(expected_value, 2),
                        "Karten im Set": len(rarity_cards),
                    })

                results_df = pd.DataFrame(results).sort_values("Erwarteter Wert ($)", ascending=False)

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Box-Preis", f"${box_price}")
                with m2:
                    st.metric("Erwarteter Wert", f"${total_expected:.2f}")
                with m3:
                    roi = ((total_expected - box_price) / box_price * 100)
                    st.metric("Erwarteter Gewinn/Verlust", f"{roi:+.1f}%",
                              delta_color="normal" if roi >= 0 else "inverse")

                st.info("""
💡 **Wichtiger Hinweis:** Der erwartete Wert ist ein statistischer Durchschnitt über viele Boxen.
Eine einzelne Box kann deutlich besser oder schlechter sein — das ist die Natur von Zufallspacks.
Wer gezielt eine bestimmte Karte will, kauft sie besser direkt als Einzelkarte.
                """)

                fig = px.bar(results_df, x="Seltenheit", y="Erwarteter Wert ($)",
                             title="Erwarteter Wert pro Seltenheitsstufe",
                             color="Erwarteter Wert ($)", color_continuous_scale="Greens",
                             hover_data=["Ø pro Box", "Ø Kartenpreis ($)"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Zeigt wie viel Wert du statistisch von jeder Seltenheitsstufe pro Box bekommst. Common und Uncommon tragen durch ihre Menge oft mehr zum Gesamtwert bei als erwartet.")

                st.dataframe(results_df.reset_index(drop=True), use_container_width=True)

# ── Tab 7: Turnierdaten ──────────────────────────────────────────────────────
with tab7:
    st.subheader("🏆 Turnierdaten — Limitless TCG")
    st.caption("Echte Turnierergebnisse · Welche Leader und Decks gewinnen wirklich?")

    with st.spinner("Turnierdaten werden geladen..."):
        tournaments = load_tournaments(limit=200)

    if not tournaments:
        st.error("Turnierdaten konnten nicht geladen werden.")
    else:
        tourn_df = pd.DataFrame(tournaments)
        tourn_df["date"] = pd.to_datetime(tourn_df["date"]).dt.date

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Turniere geladen", len(tourn_df))
        with m2:
            st.metric("Gesamt Spieler", f"{tourn_df['players'].sum():,}")
        with m3:
            st.metric("Größtes Turnier", f"{tourn_df['players'].max():,} Spieler")
        with m4:
            st.metric("Letztes Turnier", str(tourn_df["date"].max()))

        st.divider()

        tourn_tab1, tourn_tab2, tourn_tab3 = st.tabs([
            "📋 Turnierübersicht", "🎯 Leader Meta-Analyse", "🃏 Deck Details"
        ])

        with tourn_tab1:
            st.subheader("Alle Turniere")
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

            fig = px.bar(filtered_t.head(30), x="name", y="players",
                         title="Spielerzahl pro Turnier (neueste 30)",
                         color="players", color_continuous_scale="Blues")
            fig.update_layout(xaxis_tickangle=-45, paper_bgcolor="rgba(0,0,0,0)", height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Größere Turniere sind repräsentativer für die Meta — kleine Events können stark vom Zufall abhängen.")

            monthly = filtered_t.copy()
            monthly["monat"] = pd.to_datetime(monthly["date"]).dt.to_period("M").astype(str)
            monthly_counts = monthly.groupby("monat").agg(
                Turniere=("id", "count"),
                Spieler=("players", "sum")
            ).reset_index()
            fig2 = px.line(monthly_counts, x="monat", y="Spieler",
                           title="Gesamte Spieler pro Monat — Community-Aktivität",
                           markers=True)
            fig2.update_traces(line_color="#3498db")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Steigende Werte zeigen wachsendes Interesse am Spiel. Peaks oft rund um neue Set-Releases.")

            show_t = [c for c in ["date", "name", "format", "players"] if c in filtered_t.columns]
            st.dataframe(filtered_t[show_t].reset_index(drop=True),
                         use_container_width=True, height=350)

        with tourn_tab2:
            st.subheader("Leader Meta-Analyse")
            st.caption("Welche Leader dominieren die Turniere?")

            recent = tourn_df.sort_values("date", ascending=False).head(50)
            tourn_options = {
                f"{row['name']} ({row['players']} Spieler, {row['date']})": row["id"]
                for _, row in recent.iterrows()
            }

            selected_tourn = st.selectbox("Turnier auswählen", options=list(tourn_options.keys()), key="meta_tourn")

            if selected_tourn:
                tourn_id = tourn_options[selected_tourn]
                with st.spinner("Platzierungen werden geladen..."):
                    standings = load_standings(tourn_id)

                if not standings:
                    st.warning("Keine Daten für dieses Turnier verfügbar.")
                else:
                    stand_df = pd.DataFrame(standings)

                    if "record" in stand_df.columns:
                        stand_df["wins"]    = stand_df["record"].apply(lambda x: x.get("wins", 0) if isinstance(x, dict) else 0)
                        stand_df["losses"]  = stand_df["record"].apply(lambda x: x.get("losses", 0) if isinstance(x, dict) else 0)
                        stand_df["winrate"] = (stand_df["wins"] / (stand_df["wins"] + stand_df["losses"]).replace(0, 1) * 100).round(1)

                    if "deck" in stand_df.columns:
                        stand_df["leader"] = stand_df["deck"].apply(
                            lambda x: x.get("name", "Unbekannt") if isinstance(x, dict) else "Unbekannt"
                        )

                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("Teilnehmer", len(stand_df))
                        with m2:
                            st.metric("Meistgespielter Leader", stand_df["leader"].value_counts().index[0])
                        with m3:
                            st.metric("Verschiedene Leader", stand_df["leader"].nunique())

                        leader_counts = stand_df["leader"].value_counts().reset_index()
                        leader_counts.columns = ["Leader", "Anzahl Spieler"]
                        leader_counts["Anteil %"] = (leader_counts["Anzahl Spieler"] / len(stand_df) * 100).round(1)

                        fig = px.bar(leader_counts.head(15), x="Anzahl Spieler", y="Leader",
                                     orientation="h",
                                     title="Leader Verteilung (Top 15)",
                                     color="Anzahl Spieler", color_continuous_scale="Reds",
                                     hover_data=["Anteil %"])
                        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                                          paper_bgcolor="rgba(0,0,0,0)", height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("Zeigt welche Leader am häufigsten gespielt wurden. Hohe Spielerzahl = beliebter Leader, aber nicht unbedingt der stärkste.")

                        if "winrate" in stand_df.columns:
                            leader_wr = stand_df.groupby("leader").agg(
                                Spieler=("leader", "count"),
                                Ø_Winrate=("winrate", "mean"),
                                Ø_Wins=("wins", "mean"),
                            ).reset_index()
                            leader_wr = leader_wr[leader_wr["Spieler"] >= 3]
                            leader_wr["Ø_Winrate"] = leader_wr["Ø_Winrate"].round(1)
                            leader_wr = leader_wr.sort_values("Ø_Winrate", ascending=False)

                            fig2 = px.bar(leader_wr.head(15), x="Ø_Winrate", y="leader",
                                          orientation="h",
                                          title="Winrate pro Leader (min. 3 Spieler)",
                                          color="Ø_Winrate", color_continuous_scale="RdYlGn",
                                          hover_data=["Spieler", "Ø_Wins"])
                            fig2.update_layout(yaxis={"categoryorder": "total ascending"},
                                              paper_bgcolor="rgba(0,0,0,0)", height=500)
                            st.plotly_chart(fig2, use_container_width=True)
                            st.caption("Grün = hohe Winrate, Rot = niedrige Winrate. Wichtig: Mindestens 3 Spieler nötig für aussagekräftige Werte. Ein Leader mit 100% Winrate aber nur 1 Spieler sagt wenig.")

                        st.subheader("Top 8")
                        top8 = stand_df[stand_df["placing"] <= 8].sort_values("placing")
                        show_cols = [c for c in ["placing", "name", "leader", "wins", "losses", "winrate"] if c in top8.columns]
                        st.dataframe(top8[show_cols].reset_index(drop=True), use_container_width=True)
                    else:
                        st.info("Keine Deck-Daten für dieses Turnier.")
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

                        all_cards = []
                        if "leader" in decklist and isinstance(decklist["leader"], dict):
                            leader_data = decklist["leader"]
                            leader_set  = leader_data.get("set", "")
                            leader_num  = leader_data.get("number", "")
                            leader_name = leader_data.get("name", "Leader")
                            if leader_set and leader_num:
                                all_cards.append({
                                    "id": f"{leader_set}-{leader_num}",
                                    "name": leader_name,
                                    "count": 1,
                                    "section": "leader",
                                })

                        for section_name, section_cards in decklist.items():
                            if section_name == "leader":
                                continue
                            if isinstance(section_cards, list):
                                for entry in section_cards:
                                    if isinstance(entry, dict):
                                        card_set = entry.get("set", "")
                                        card_num = entry.get("number", "")
                                        card_id  = f"{card_set}-{card_num}" if card_set and card_num else ""
                                        count    = entry.get("count", 1)
                                        name     = entry.get("name", card_id)
                                        if card_id:
                                            all_cards.append({
                                                "id": card_id,
                                                "name": name,
                                                "count": count,
                                                "section": section_name,
                                            })

                        if not all_cards:
                            st.write("Deckliste konnte nicht gelesen werden.")
                            continue

                        sections = {}
                        for c in all_cards:
                            s = c["section"]
                            if s not in sections:
                                sections[s] = []
                            sections[s].append(c)

                        for section_name, cards in sections.items():
                            total = sum(c["count"] for c in cards)
                            st.markdown(f"**{section_name.capitalize()} ({total} Karten)**")
                            cards_per_row = 5
                            for i in range(0, len(cards), cards_per_row):
                                chunk = cards[i:i+cards_per_row]
                                cols = st.columns(cards_per_row)
                                for j, card in enumerate(chunk):
                                    with cols[j]:
                                        card_id = card["id"]
                                        count   = card["count"]
                                        name    = card.get("name", card_id)
                                        img_url = f"https://optcgapi.com/media/static/Card_Images/{card_id}.jpg"
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.write("🃏")
                                        st.caption(f"**x{count} {name}**")

# ── Tab 8: Kartensuche ───────────────────────────────────────────────────────
with tab8:
    st.subheader("Kartensuche")

    c1, c2, c3 = st.columns(3)
    with c1:
        search8 = st.text_input("Name enthält...", placeholder="z.B. Luffy", key="search8")
    with c2:
        col_opts = ["Alle"] + sorted(df[COLOR].dropna().unique().tolist())
        sel_color = st.selectbox("Farbe", col_opts, key="search_color")
    with c3:
        if TYPE in df.columns:
            type_opts = ["Alle"] + sorted(df[TYPE].dropna().unique().tolist())
            sel_type = st.selectbox("Typ", type_opts, key="search_type")
        else:
            sel_type = "Alle"

    include_don = st.toggle("Don!! Karten einschließen", value=False, key="include_don")
    show_images = st.toggle("Kartenbilder anzeigen", value=False, key="search_images")

    result = df.copy()
    if not include_don:
        result = result[result["is_don"] == False]
    if search8:
        result = result[result[NAME].astype(str).str.contains(search8, case=False, na=False)]
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

# ── Sidebar Schnellsuche ─────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🔍 Schnellsuche")
    search_side = st.text_input("Kartenname", placeholder="z.B. Luffy", key="sidebar_search")
    if search_side:
        results_side = df[df[NAME].astype(str).str.contains(search_side, case=False, na=False)]
        st.write(f"{len(results_side)} Karten gefunden")
        for _, row in results_side.head(5).iterrows():
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

st.divider()
st.caption("Daten: optcgapi.com & Limitless TCG · Kein offizielles Bandai-Produkt")
