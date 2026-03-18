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

@st.cache_data(ttl=1800)
def load_top_decklists(tournament_ids, top_n=8):
    """Lädt Decklisten der Top N Platzierten aus mehreren Turnieren."""
    all_cards = []
    for tid in tournament_ids:
        standings = load_standings(tid)
        if not standings:
            continue
        for player in standings:
            if player.get("placing", 999) > top_n:
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

with st.spinner("Kartendaten werden geladen..."):
    df = load_all_cards()

if df.empty:
    st.error("Keine Daten geladen.")
    st.stop()
