import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import re
import json
from typing import List, Dict, Optional

# ==================== CONFIGURATION ====================
SERP_API_KEY = "808e9eb85adc2da256f83bb263b7184b2199f64cf214b53f2e4272f5b7aafd08"

EVENT_CATEGORIES = {
    "all": "All Events",
    "music": "Concerts & Music",
    "conference": "Conferences & Business",
    "festival": "Festivals & Cultural",
    "sports": "Sports & Fitness",
    "arts": "Arts & Theater",
    "food": "Food & Drink",
    "family": "Family & Kids",
    "comedy": "Comedy Shows",
    "exhibition": "Exhibitions & Expos"
}

# ==================== CORE FUNCTIONS ====================

def validate_location(location: str) -> bool:
    return bool(re.match(r'^[a-zA-Z\s,.-]{2,50}$', location.strip()))

def build_search_queries(location: str, start_date: str, end_date: str, category: str) -> List[str]:
    base_queries = []
    date_range = f"{start_date} to {end_date}"
    if category in ["all", "music"]:
        base_queries += [f"concerts {location} {date_range}", f"music events {location}", f"live music {location}"]
    if category in ["all", "conference"]:
        base_queries += [f"conferences {location} {date_range}", f"business events {location}", f"tech events {location}"]
    if category in ["all", "festival"]:
        base_queries += [f"festivals {location} {date_range}", f"cultural events {location}", f"{location} festivals"]
    if category in ["all", "sports"]:
        base_queries += [f"sports events {location} {date_range}", f"{location} sports games", f"fitness events {location}"]
    base_queries += [f"events {location} {date_range}", f"things to do {location}", f"upcoming events {location}"]
    return base_queries

def is_event_like(title: str, snippet: str) -> bool:
    keywords = ['event', 'concert', 'festival', 'conference', 'show', 'exhibition', 'tickets', 'register']
    return any(k in (title + snippet).lower() for k in keywords)

def classify_event_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ['concert', 'music', 'dj']): return 'music'
    if any(w in t for w in ['conference', 'summit', 'workshop']): return 'conference'
    if any(w in t for w in ['festival', 'cultural']): return 'festival'
    if any(w in t for w in ['sports', 'game', 'match']): return 'sports'
    if any(w in t for w in ['art', 'theater', 'exhibition']): return 'arts'
    if any(w in t for w in ['food', 'drink']): return 'food'
    if any(w in t for w in ['family', 'kids']): return 'family'
    return 'other'

def deduplicate_events(events: List[Dict]) -> List[Dict]:
    seen, unique = set(), []
    for e in events:
        ident = (e['name'].lower().strip(), e['date'].lower().strip())
        if ident not in seen:
            seen.add(ident)
            unique.append(e)
    return unique

def extract_events_from_results(results: Dict, location: str) -> List[Dict]:
    events = []
    if 'events_results' in results:
        for e in results['events_results']:
            events.append({
                'name': e.get('title', 'Unknown'),
                'date': e.get('date', 'Not specified'),
                'venue': e.get('address', location),
                'description': e.get('description', ''),
                'link': e.get('link', ''),
                'category': classify_event_type(e.get('title', ''))
            })
    return events

def search_events_google(location: str, start_date: str, end_date: str, category: str = "all") -> List[Dict]:
    events = []
    queries = build_search_queries(location, start_date, end_date, category)
    for query in queries:
        params = {"q": query, "location": location, "hl": "en", "api_key": SERP_API_KEY}
        try:
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()
            events += extract_events_from_results(data, location)
        except Exception as e:
            print("Error:", e)
    return deduplicate_events(events)

# ==================== STREAMLIT APP ====================

st.title(" Event Discovery Web App")
st.write("Find real events using **SerpApi + Google Search**")

location = st.text_input("📍 Location", "Dubai")
today = datetime.now().date()
start_date = st.date_input("Start Date", today)
end_date = st.date_input("End Date", today + timedelta(days=30))
category = st.selectbox("🎯 Category", list(EVENT_CATEGORIES.keys()), index=0)

if st.button("Search Events"):
    if not validate_location(location):
        st.error("Invalid location. Please enter a proper city/country.")
    else:
        with st.spinner("Searching events..."):
            events = search_events_google(location, str(start_date), str(end_date), category)
        if not events:
            st.warning("No events found.")
        else:
            df = pd.DataFrame(events)
            st.success(f"Found {len(events)} events!")
            st.dataframe(df)
            st.download_button("⬇ Download as CSV", df.to_csv(index=False), "events.csv", "text/csv")
