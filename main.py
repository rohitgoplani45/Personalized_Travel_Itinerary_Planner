import json
import os
import re
import io
import copy
import hashlib
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st

# Optional integrations
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import requests
except ImportError:
    requests = None


# ---------------------------------------------------------------------------
# App configuration and design system
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Wanderlust · Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

TEAL = "#0F766E"
TEAL_DARK = "#115E59"
AMBER = "#F97316"
SAND = "#FDFBF7"
SLATE = "#1E293B"
MUTED = "#64748B"
BORDER = "#E8E5DE"
PALE_TEAL = "#E6F4F1"
PALE_AMBER = "#FFF0E5"

CURRENCIES = {
    "USD ($)": {"code": "USD", "symbol": "$", "rate": 1.0},
    "INR (₹)": {"code": "INR", "symbol": "₹", "rate": 83.5},
    "EUR (€)": {"code": "EUR", "symbol": "€", "rate": 0.92},
    "GBP (£)": {"code": "GBP", "symbol": "£", "rate": 0.79},
}
SLOTS = [
    ("morning", "Morning Sightseeing", "☀️"),
    ("lunch", "Lunch Recommendation", "🥗"),
    ("afternoon", "Afternoon Leisure", "🌿"),
    ("evening", "Evening Dining & Entertainment", "🌙"),
]
INTERESTS = ["Food", "Adventure", "History", "Nightlife"]

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
      --teal: #0F766E; --amber: #F97316; --sand: #FDFBF7;
      --slate: #1E293B; --muted: #64748B; --line: #E8E5DE;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--slate); }
    .stApp { background: var(--sand); }
    [data-testid="stHeader"] { background: rgba(253,251,247,.88); }
    [data-testid="stSidebar"] { background: #F4F1EA; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div { padding-top: 1.1rem; }
    h1, h2, h3, h4 { font-family: 'Manrope', sans-serif !important; letter-spacing: -.035em; color: var(--slate); }
    h1 { font-weight: 800 !important; }
    h2, h3 { font-weight: 750 !important; }
    .brand { display:flex; align-items:center; gap:10px; font-family:'Manrope',sans-serif; font-weight:800; font-size:1.18rem; color:var(--slate); }
    .brand-mark { width:36px; height:36px; border-radius:12px; display:grid; place-items:center; color:white; background:var(--teal); box-shadow:0 5px 14px #0f766e35; }
    .eyebrow { color:var(--teal); font-size:.72rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; }
    .hero { background:linear-gradient(115deg,#0F766E 0%,#115E59 68%,#164E63 100%); color:white; border-radius:24px; padding:30px 32px; position:relative; overflow:hidden; box-shadow:0 14px 34px #0f766e20; margin:8px 0 24px; }
    .hero:after { content:'✈'; position:absolute; right:32px; top:0; font-size:8rem; opacity:.10; transform:rotate(-14deg); }
    .hero h1 { color:white !important; font-size:clamp(1.8rem,3vw,2.8rem) !important; margin:.35rem 0 .55rem; }
    .hero p { color:#D6F2ED; max-width:650px; margin:0; font-size:1rem; line-height:1.65; }
    .hero .eyebrow { color:#FDBA74; }
    .panel { background:white; border:1px solid var(--line); border-radius:18px; padding:20px 22px; box-shadow:0 6px 22px rgba(30,41,59,.045); }
    .destination-card { background:white; border:1px solid var(--line); border-radius:18px; padding:21px; height:100%; box-shadow:0 8px 22px rgba(30,41,59,.045); }
    .destination-card h3 { margin:.45rem 0 .35rem; font-size:1.25rem; }
    .muted { color:var(--muted); font-size:.9rem; line-height:1.55; }
    .pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:.73rem; font-weight:800; margin:2px 4px 2px 0; }
    .pill-teal { background:#DDF3EF; color:#0F766E; }
    .pill-amber { background:#FFF0E5; color:#C2410C; }
    .pill-slate { background:#F1F5F9; color:#475569; }
    .micro { background:white; border:1px solid var(--line); border-radius:16px; padding:16px 18px; box-shadow:0 5px 18px rgba(30,41,59,.035); }
    .micro-label { color:var(--muted); font-size:.78rem; font-weight:700; }
    .micro-value { color:var(--slate); font-family:'Manrope',sans-serif; font-size:1.55rem; font-weight:800; margin-top:4px; }
    .micro-note { color:var(--teal); font-size:.75rem; margin-top:2px; }
    .activity { background:white; border:1px solid var(--line); border-radius:14px; padding:15px 16px; margin:8px 0; }
    .activity-title { font-weight:800; color:var(--slate); font-size:1rem; }
    .activity-meta { color:var(--muted); font-size:.82rem; margin-top:5px; line-height:1.5; }
    .slot-number { display:inline-grid; place-items:center; width:28px; height:28px; border-radius:9px; background:var(--pa, #E6F4F1); color:var(--teal); font-weight:800; margin-right:8px; }
    .section-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:12px 0 16px; }
    .section-head p { color:var(--muted); margin:0; font-size:.88rem; }
    div.stButton > button { border-radius:11px; font-weight:750; min-height:2.65rem; border:1px solid #D5E5E1; transition:all .15s ease; }
    div.stButton > button[kind="primary"] { background:var(--teal); border-color:var(--teal); color:white; }
    div.stButton > button[kind="primary"]:hover { background:var(--teal-dark); border-color:var(--teal-dark); box-shadow:0 6px 16px #0f766e28; }
    div.stButton > button:hover { border-color:var(--teal); color:var(--teal); }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input, .stNumberInput input { border-radius:10px !important; }
    div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:15px; padding:14px 16px; box-shadow:0 4px 16px #1e293b08; }
    div[data-testid="stMetricLabel"] { color:var(--muted); }
    .stTabs [data-baseweb="tab-list"] { gap:8px; border-bottom:1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { background:transparent; border-radius:10px 10px 0 0; padding:12px 15px; font-weight:700; }
    .stTabs [aria-selected="true"] { color:var(--teal) !important; border-bottom:3px solid var(--teal) !important; }
    [data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:white; overflow:hidden; }
    .footer { text-align:center; color:#94A3B8; font-size:.78rem; padding:28px 0 8px; }
    .side-note { color:#64748B; font-size:.8rem; line-height:1.5; }
    hr { border-color:var(--line) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state and sample data
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "demo_mode": True,
        "trips": [],
        "active_trip": None,
        "selected_destination": "",
        "notice": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def seed_for(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


DESTINATIONS = [
    {
        "city": "Kyoto, Japan", "score": 98, "season": "Mar–May · Oct–Nov",
        "highlights": ["Temple trails", "Tea houses", "Seasonal cuisine"],
        "reason": "A thoughtful fit for culture, food, and walkable neighborhoods, with memorable historic districts and calm garden breaks.",
        "districts": ["Higashiyama", "Gion", "Downtown Kyoto", "Arashiyama"],
        "image": "🏯",
    },
    {
        "city": "Lisbon, Portugal", "score": 95, "season": "Apr–Jun · Sep–Oct",
        "highlights": ["Coastal views", "Local markets", "Live fado"],
        "reason": "A strong all-rounder for relaxed city wandering, local food, scenic viewpoints, and lively evenings without overpacking the schedule.",
        "districts": ["Baixa", "Alfama", "Belém", "Cais do Sodré"],
        "image": "🌅",
    },
    {
        "city": "Jaipur, India", "score": 93, "season": "Oct–Mar",
        "highlights": ["Royal forts", "Craft bazaars", "Rajasthani food"],
        "reason": "Excellent for heritage and food lovers, with landmark sights and markets that can be grouped into compact geographic days.",
        "districts": ["Pink City", "Amer", "Civil Lines", "Bani Park"],
        "image": "🕌",
    },
    {
        "city": "Bali, Indonesia", "score": 91, "season": "May–Sep",
        "highlights": ["Rice terraces", "Waterfalls", "Sunset beaches"],
        "reason": "Best suited to outdoor adventure and slower days, balancing nature excursions with beach time and casual dining.",
        "districts": ["Ubud", "Canggu", "Uluwatu", "Sanur"],
        "image": "🌴",
    },
    {
        "city": "Istanbul, Türkiye", "score": 90, "season": "Apr–May · Sep–Oct",
        "highlights": ["Grand bazaars", "Waterfront walks", "Street food"],
        "reason": "A high-variety choice for history, food, and nightlife, with iconic landmarks and lively neighborhoods.",
        "districts": ["Sultanahmet", "Karaköy", "Beyoğlu", "Kadıköy"],
        "image": "🧿",
    },
]

ACTIVITY_LIBRARY = {
    "Kyoto": {
        "morning": [
            ("Walk the Higashiyama temple lanes", "Higashiyama", 12, "Historic streets, small shrines, and traditional architecture."),
            ("Visit a quiet Zen garden", "Higashiyama", 8, "A slower start among landscaped gardens and temple grounds."),
            ("Explore Arashiyama bamboo paths", "Arashiyama", 10, "A leafy walk; arrive early for a calmer atmosphere."),
        ],
        "lunch": [
            ("Neighborhood udon lunch", "Higashiyama", 18, "A casual bowl of noodles with seasonal sides."),
            ("Market-side Kyoto set meal", "Downtown Kyoto", 22, "A balanced set lunch with local specialties."),
            ("Tofu and vegetable tasting", "Arashiyama", 24, "A regional meal inspired by Kyoto's temple cuisine."),
        ],
        "afternoon": [
            ("Browse Nishiki Market", "Downtown Kyoto", 15, "Sample local snacks and browse specialty stalls."),
            ("Tea ceremony experience", "Gion", 32, "Learn the ritual and craft of Japanese tea."),
            ("Riverside stroll and café stop", "Downtown Kyoto", 10, "Unhurried time beside the Kamo River."),
        ],
        "evening": [
            ("Izakaya dinner in Pontocho", "Gion", 35, "Small plates and a lively alley atmosphere."),
            ("Gion lantern-lit walk", "Gion", 8, "An atmospheric evening walk; keep noise low in residential lanes."),
            ("Seasonal tasting dinner", "Downtown Kyoto", 48, "A special meal focused on seasonal ingredients."),
        ],
    },
    "Lisbon": {
        "morning": [
            ("Alfama lanes and viewpoints", "Alfama", 8, "Cobblestone lanes and city panoramas; wear comfortable shoes."),
            ("Belém riverside monuments", "Belém", 16, "A waterfront route with striking architecture."),
            ("Tram-side neighborhood walk", "Baixa", 5, "Explore central streets and tiled façades on foot."),
        ],
        "lunch": [
            ("Seafood rice lunch", "Baixa", 24, "A relaxed Portuguese classic with seafood."),
            ("Pastelaria café lunch", "Belém", 14, "Light bites and a famous custard tart stop."),
            ("Market hall tasting plates", "Cais do Sodré", 22, "Mix-and-match local flavors in one place."),
        ],
        "afternoon": [
            ("Browse design and food stalls", "Cais do Sodré", 12, "Independent shops and easygoing browsing."),
            ("Riverside promenade break", "Belém", 5, "Open views and a slower pace by the water."),
            ("Tile museum visit", "Alfama", 14, "Portuguese azulejo history and intricate patterns."),
        ],
        "evening": [
            ("Fado dinner in Alfama", "Alfama", 38, "Traditional music in an intimate setting."),
            ("Sunset at a hilltop miradouro", "Baixa", 4, "Golden-hour views over rooftops."),
            ("Petiscos evening crawl", "Cais do Sodré", 32, "Share small plates across a lively neighborhood."),
        ],
    },
    "Jaipur": {
        "morning": [
            ("Amber Fort and courtyards", "Amer", 18, "Explore hilltop palace architecture and courtyards."),
            ("City Palace heritage visit", "Pink City", 15, "Royal collections and historic courtyards."),
            ("Hawa Mahal photo stop and walk", "Pink City", 5, "Admire the famous façade and surrounding streets."),
        ],
        "lunch": [
            ("Rajasthani thali lunch", "Pink City", 10, "A generous spread of regional dishes."),
            ("Traditional kachori and lassi stop", "Pink City", 5, "A quick, local-flavor lunch."),
            ("Courtyard café meal", "Civil Lines", 14, "A calmer meal away from the busiest lanes."),
        ],
        "afternoon": [
            ("Johari Bazaar craft browsing", "Pink City", 8, "Jewelry, textiles, and colorful market lanes."),
            ("Jantar Mantar observatory", "Pink City", 7, "Historic astronomical instruments and open courtyards."),
            ("Block-printing workshop", "Bani Park", 22, "Try a traditional textile craft with a local artisan."),
        ],
        "evening": [
            ("Rajasthani dinner with folk music", "Bani Park", 20, "Regional dishes and cultural performances."),
            ("Patrika Gate evening photo walk", "Civil Lines", 3, "Colorful arches and a relaxed stroll."),
            ("Rooftop dinner overlooking the city", "Pink City", 24, "An open-air dinner with old-city views."),
        ],
    },
    "Bali": {
        "morning": [
            ("Ubud rice terrace walk", "Ubud", 8, "Green landscapes and a refreshing outdoor start."),
            ("Waterfall trail and swim stop", "Ubud", 12, "A nature excursion; check local conditions before swimming."),
            ("Coastal sunrise walk", "Sanur", 3, "A flat, peaceful route beside the sea."),
        ],
        "lunch": [
            ("Balinese rice bowl", "Ubud", 10, "Local spices, vegetables, and a filling rice plate."),
            ("Beachside seafood lunch", "Sanur", 20, "Fresh seafood with ocean views."),
            ("Plant-forward café lunch", "Canggu", 15, "A relaxed option with vegetarian choices."),
        ],
        "afternoon": [
            ("Local craft and art browsing", "Ubud", 10, "Small galleries and artisan shops."),
            ("Beach and book break", "Canggu", 5, "Leave space in the schedule to unwind."),
            ("Clifftop coastal viewpoint", "Uluwatu", 8, "Wide ocean views and dramatic scenery."),
        ],
        "evening": [
            ("Sunset seafood dinner", "Jimbaran", 28, "An easygoing dinner by the water."),
            ("Beachfront live music", "Canggu", 18, "Casual evening entertainment."),
            ("Uluwatu cultural performance", "Uluwatu", 16, "A sunset performance; check show times locally."),
        ],
    },
    "Istanbul": {
        "morning": [
            ("Historic Sultanahmet walk", "Sultanahmet", 18, "Major monuments and layers of city history."),
            ("Spice Bazaar tasting walk", "Karaköy", 8, "A sensory tour of spices, sweets, and local goods."),
            ("Bosphorus waterfront stroll", "Karaköy", 5, "Sea views and a gentle start to the day."),
        ],
        "lunch": [
            ("Kebab and mezze lunch", "Sultanahmet", 18, "Classic regional dishes and shared mezze."),
            ("Street-food tasting plate", "Karaköy", 12, "A casual introduction to local flavors."),
            ("Fish sandwich by the water", "Karaköy", 9, "A quick, iconic waterfront bite."),
        ],
        "afternoon": [
            ("Grand Bazaar browsing", "Sultanahmet", 8, "Historic covered lanes full of craft and textile stalls."),
            ("Independent shops in Karaköy", "Karaköy", 12, "Design stores, cafés, and street art."),
            ("Ferry ride across the Bosphorus", "Kadıköy", 7, "A scenic way to see the city from the water."),
        ],
        "evening": [
            ("Meyhane dinner and mezze", "Beyoğlu", 32, "A lively shared-plate dining experience."),
            ("Rooftop tea with city views", "Beyoğlu", 12, "A relaxed stop above the busy streets."),
            ("Kadıköy food and music walk", "Kadıköy", 22, "A vibrant neighborhood for casual food and nightlife."),
        ],
    },
}


def get_city_key(destination: str) -> str:
    text = destination.lower()
    for key in ACTIVITY_LIBRARY:
        if key.lower() in text:
            return key
    aliases = {
        "japan": "Kyoto", "portugal": "Lisbon", "india": "Jaipur",
        "indonesia": "Bali", "turkiye": "Istanbul", "turkey": "Istanbul",
    }
    for alias, key in aliases.items():
        if alias in text:
            return key
    return "Lisbon"


def interest_note(interests: List[str], slot: str) -> str:
    if not interests:
        return "A balanced pick selected to keep the day varied."
    lookup = {
        "Food": "Food-focused option", "Adventure": "Outdoor-friendly option",
        "History": "Culture and history pick", "Nightlife": "Evening atmosphere pick",
    }
    if slot == "evening" and "Nightlife" in interests:
        return "Nightlife-friendly option"
    if slot in ("lunch", "evening") and "Food" in interests:
        return "Food-focused option"
    if slot == "morning" and "History" in interests:
        return "Culture and history pick"
    if slot == "afternoon" and "Adventure" in interests:
        return "Outdoor-friendly option"
    return lookup.get(interests[0], "A balanced pick")


def generate_itinerary(destination: str, days: int, budget: str, party: str,
                       pace: str, interests: List[str], start_date: date) -> List[Dict[str, Any]]:
    city_key = get_city_key(destination)
    library = ACTIVITY_LIBRARY[city_key]
    budget_factor = {"Budget": 0.68, "Moderate": 1.0, "Luxury": 1.85}.get(budget, 1.0)
    party_factor = 1.0
    if party == "Family":
        party_factor = 1.08
    elif party == "Friends":
        party_factor = 1.04
    pace_adjust = {"Relaxed": 0, "Moderate": 1, "Fast-Paced": 2}.get(pace, 1)
    result = []
    for day_index in range(days):
        day_num = day_index + 1
        activities = {}
        # Rotate each slot to avoid repeating the same activity on consecutive days.
        for slot_index, (slot_key, slot_name, emoji) in enumerate(SLOTS):
            options = library[slot_key]
            chosen = options[(day_index + slot_index + pace_adjust) % len(options)]
            name, district, base_cost, description = chosen
            if interests and day_index % 3 == 1:
                description += " " + interest_note(interests, slot_key) + "."
            cost = round(base_cost * budget_factor * party_factor, 2)
            activities[slot_key] = {
                "slot": slot_key,
                "slot_name": slot_name,
                "name": name,
                "district": district,
                "cost_usd": cost,
                "description": description,
                "duration": ["1–2 hours", "45–90 min", "1–2 hours", "1–3 hours"][slot_index],
                "tip": (
                    "Keep nearby stops together to reduce transit time."
                    if slot_key in ("morning", "afternoon")
                    else "Confirm opening hours and reserve ahead where useful."
                ),
            }
        result.append({
            "day": day_num,
            "date": (start_date + timedelta(days=day_index)).isoformat(),
            "title": [
                "Landmarks & local flavor", "Neighborhood discoveries",
                "A slower local rhythm", "Culture, craft & cuisine",
            ][day_index % 4],
            "activities": activities,
        })
    return result


def recommend_destinations(interests: List[str], budget: str, pace: str, party: str) -> List[Dict[str, Any]]:
    scored = copy.deepcopy(DESTINATIONS[:])
    interest_map = {
        "Food": {"Lisbon": 3, "Jaipur": 4, "Istanbul": 4, "Kyoto": 3},
        "Adventure": {"Bali": 7, "Lisbon": 2, "Kyoto": 2},
        "History": {"Kyoto": 5, "Jaipur": 5, "Istanbul": 5},
        "Nightlife": {"Lisbon": 5, "Istanbul": 5, "Bali": 3},
    }
    for item in scored:
        key = item["city"].split(",")[0]
        score = item["score"] + sum(interest_map.get(i, {}).get(key, 0) for i in interests)
        if budget == "Budget" and key in ("Jaipur", "Bali"):
            score += 3
        if budget == "Luxury" and key in ("Kyoto", "Lisbon", "Istanbul"):
            score += 2
        if pace == "Relaxed" and key in ("Bali", "Kyoto"):
            score += 2
        if party == "Family" and key in ("Kyoto", "Lisbon"):
            score += 1
        item["score"] = min(99, score)
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:3]


def parse_json_response(text: str) -> Any:
    """Parse plain JSON or JSON wrapped in a Markdown code fence."""
    if not isinstance(text, str):
        raise ValueError("Model response was not text.")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"Could not parse model JSON: {exc}") from exc
        start, end = cleaned.find("["), cleaned.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError(f"Could not parse model JSON: {exc}") from exc
        raise ValueError("No JSON object or array found in model response.")


def call_gemini(prompt: str, api_key: str) -> str:
    if requests is None:
        raise RuntimeError("Install requests to use Gemini.")
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    response = requests.post(
        url + "?key=" + api_key,
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.6}},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_groq(prompt: str, api_key: str) -> str:
    if requests is None:
        raise RuntimeError("Install requests to use Groq.")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a travel planning assistant. Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
        },
        timeout=45,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def llm_json(prompt: str, provider: str, api_key: str) -> Any:
    raw = call_gemini(prompt, api_key) if provider == "Gemini" else call_groq(prompt, api_key)
    return parse_json_response(raw)


def format_money(usd: float, currency_label: str) -> str:
    currency = CURRENCIES[currency_label]
    converted = usd * currency["rate"]
    return f'{currency["symbol"]}{converted:,.2f}'


def get_totals(trip: Dict[str, Any]) -> Dict[str, float]:
    total = sum(
        activity.get("cost_usd", 0)
        for day in trip.get("itinerary", [])
        for activity in day.get("activities", {}).values()
    )
    count_days = max(1, len(trip.get("itinerary", [])))
    return {"usd": total, "daily": total / count_days, "days": count_days}


def build_trip(destination: str, start_date: date, days: int, budget: str, party: str,
               pace: str, interests: List[str], demo: bool, provider: str,
               api_key: str) -> Dict[str, Any]:
    itinerary = generate_itinerary(destination, days, budget, party, pace, interests, start_date)
    ai_note = "Demo itinerary built from curated sample activities."
    if not demo and api_key:
        prompt = (
            "Create a concise travel-planning note as JSON with keys 'trip_note' and 'safety_notes'. "
            "Do not invent specific opening hours. Destination: " + destination +
            "; days: " + str(days) + "; budget: " + budget + "; interests: " + ", ".join(interests) +
            ". safety_notes must be an array of 4 general practical safety reminders."
        )
        try:
            response = llm_json(prompt, provider, api_key)
            if isinstance(response, dict):
                ai_note = str(response.get("trip_note", "AI-assisted planning note generated."))
        except Exception as exc:
            ai_note = "AI service unavailable; curated itinerary used instead. Details: " + str(exc)[:180]
    return {
        "id": hashlib.sha1(f"{destination}{start_date}{days}{os.urandom(4).hex()}".encode()).hexdigest()[:10],
        "name": f"{destination} · {days} day{'s' if days != 1 else ''}",
        "destination": destination,
        "start_date": start_date.isoformat(),
        "end_date": (start_date + timedelta(days=days - 1)).isoformat(),
        "days": days,
        "budget": budget,
        "party": party,
        "pace": pace,
        "interests": interests[:],
        "itinerary": itinerary,
        "note": ai_note,
        "created_at": date.today().isoformat(),
    }


def swap_activity(trip: Dict[str, Any], day_number: int, slot_key: str, request: str,
                  demo: bool, provider: str, api_key: str) -> Dict[str, Any]:
    updated = copy.deepcopy(trip)
    day = next((d for d in updated["itinerary"] if d["day"] == day_number), None)
    if day is None or slot_key not in day["activities"]:
        raise ValueError("That day or time slot is not part of this itinerary.")
    old = day["activities"][slot_key]
    if not demo and api_key:
        prompt = (
            "Return a JSON object with a single key 'activity' containing keys "
            "name, district, cost_usd, description, duration, tip. Keep it plausible and safe. "
            "Do not add other itinerary slots. Destination: " + trip["destination"] +
            ". Slot: " + old["slot_name"] + ". Existing activity: " + old["name"] +
            ". User request: " + request +
            ". Keep cost_usd numeric and in USD, matching the trip budget level " + trip["budget"] + "."
        )
        try:
            response = llm_json(prompt, provider, api_key)
            candidate = response.get("activity", response) if isinstance(response, dict) else None
            if isinstance(candidate, dict) and candidate.get("name"):
                old.update({
                    "name": str(candidate["name"]),
                    "district": str(candidate.get("district", old["district"])),
                    "cost_usd": max(0, float(candidate.get("cost_usd", old["cost_usd"]))),
                    "description": str(candidate.get("description", "Customized activity based on your request.")),
                    "duration": str(candidate.get("duration", old["duration"])),
                    "tip": str(candidate.get("tip", old["tip"])),
                })
                day["activities"][slot_key] = old
                return updated
        except Exception:
            pass
    # Deterministic demo fallback that changes only the selected slot.
    seed = seed_for(trip["destination"] + request + str(day_number) + slot_key)
    options = ACTIVITY_LIBRARY[get_city_key(trip["destination"])][slot_key]
    candidates = [x for x in options if x[0] != old["name"]]
    if not candidates:
        candidates = options
    chosen = candidates[seed % len(candidates)]
    name, district, cost, description = chosen
    lowered = request.lower()
    if "market" in lowered:
        name = "Explore a local market and artisan stalls"
        description = "Browse local produce, crafts, and neighborhood specialties at an easy pace."
    elif "outdoor" in lowered or "nature" in lowered:
        name = "Outdoor neighborhood walk and scenic stop"
        description = "Spend time outside with a flexible route and a few scenic pauses."
    elif "museum" in lowered or "history" in lowered:
        name = "Local history and heritage visit"
        description = "Explore local stories, architecture, and cultural context."
    elif "food" in lowered or "restaurant" in lowered:
        name = "Local food tasting experience"
        description = "Try regional flavors at a well-reviewed local spot or casual tasting route."
    elif request.strip():
        description = f"Customized alternative inspired by your request: {request.strip()[:120]}."
    old.update({
        "name": name,
        "district": district,
        "cost_usd": round(float(cost) * ({"Budget": .68, "Moderate": 1, "Luxury": 1.85}[trip["budget"]]), 2),
        "description": description,
        "tip": "Only this time slot was updated; all other activities remain unchanged.",
    })
    day["activities"][slot_key] = old
    return updated


def pdf_export(trip: Dict[str, Any], currency_label: str) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return json.dumps(trip, indent=2, ensure_ascii=False).encode("utf-8")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title=f"Wanderlust itinerary - {trip['destination']}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="WanderTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=23, leading=28, textColor=colors.HexColor(TEAL), alignment=TA_LEFT, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="WanderSub", parent=styles["Normal"], fontSize=9, leading=13,
        textColor=colors.HexColor(MUTED), spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="DayHead", parent=styles["Heading2"], fontSize=14, leading=18,
        textColor=colors.HexColor(TEAL), spaceBefore=12, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name="SmallCell", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor(SLATE),
    ))
    story = [
        Paragraph("Wanderlust", styles["WanderTitle"]),
        Paragraph("YOUR PERSONALIZED TRAVEL ITINERARY", styles["Heading3"]),
        Paragraph(
            f"{trip['destination']} &nbsp;·&nbsp; {trip['start_date']} – {trip['end_date']} "
            f"&nbsp;·&nbsp; {trip['days']} days &nbsp;·&nbsp; {trip['budget']} budget",
            styles["WanderSub"],
        ),
    ]
    totals = get_totals(trip)
    story.append(Paragraph(
        f"<b>Estimated activity total:</b> ${totals['usd']:,.2f} USD "
        f"({format_money(totals['usd'], currency_label)}) &nbsp; "
        f"<b>Daily average:</b> ${totals['daily']:,.2f} USD",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))
    for day in trip["itinerary"]:
        story.append(Paragraph(
            f"Day {day['day']} · {day['title']} · {day['date']}", styles["DayHead"]
        ))
        rows = [[
            Paragraph("<b>Time</b>", styles["SmallCell"]),
            Paragraph("<b>Plan &amp; area</b>", styles["SmallCell"]),
            Paragraph("<b>Est. cost</b>", styles["SmallCell"]),
        ]]
        for slot_key, slot_name, emoji in SLOTS:
            activity = day["activities"][slot_key]
            desc = (
                f"<b>{activity['name']}</b><br/>"
                f"<font color='#64748B'>{activity['district']} · {activity['duration']}</font><br/>"
                f"{activity['description']}"
            )
            rows.append([
                Paragraph(slot_name, styles["SmallCell"]),
                Paragraph(desc, styles["SmallCell"]),
                Paragraph(f"${activity['cost_usd']:.2f}<br/>{format_money(activity['cost_usd'], currency_label)}", styles["SmallCell"]),
            ])
        table = Table(rows, colWidths=[34 * mm, 102 * mm, 28 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TEAL)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), .45, colors.HexColor(BORDER)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(table)
        story.append(Spacer(1, 7))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Emergency &amp; Safety Checklist", styles["DayHead"]))
    checklist = [
        "Save local emergency numbers and your accommodation address offline.",
        "Keep a photo of your passport/ID and travel insurance details in a secure place.",
        "Share your itinerary and check-in plan with someone you trust.",
        "Use licensed transport and confirm the destination before departing.",
        "Carry essential medication and note nearby pharmacies or medical facilities.",
        "Check local weather, entry requirements, and attraction hours before leaving.",
    ]
    for item in checklist:
        story.append(Paragraph(f"☐ &nbsp; {item}", styles["Normal"]))
        story.append(Spacer(1, 4))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Costs are planning estimates, not live quotes. Confirm prices, opening hours, "
        "entry rules, and transport details before travel.",
        styles["Italic"],
    ))
    doc.build(story)
    return buffer.getvalue()


def set_active_trip(trip: Dict[str, Any]) -> None:
    st.session_state.active_trip = copy.deepcopy(trip)
    st.session_state.selected_destination = trip["destination"]


def render_activity(activity: Dict[str, Any], currency_label: str, index: int) -> None:
    cost = activity.get("cost_usd", 0)
    st.markdown(
        f"""
        <div class="activity">
          <div><span class="slot-number">{index}</span><span class="activity-title">{activity['name']}</span></div>
          <div style="margin:8px 0 5px">
            <span class="pill pill-teal">District: {activity['district']}</span>
            <span class="pill pill-slate">{activity['duration']}</span>
            <span class="pill pill-amber">{format_money(cost, currency_label)}</span>
          </div>
          <div class="activity-meta">{activity['description']}</div>
          <div class="activity-meta">✦ {activity.get('tip', '')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar: preferences and API configuration
# ---------------------------------------------------------------------------
init_state()
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">✈</div><div>Wanderlust<br><span style="font-size:.72rem;color:#64748B;font-weight:600">PERSONAL TRAVEL STUDIO</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown("### Trip preferences")
    destination_input = st.text_input(
        "Destination", placeholder="Leave blank to discover somewhere…",
        value=st.session_state.get("sidebar_destination", ""),
        help="Enter a city or leave blank to receive destination recommendations.",
    )
    date_range = st.date_input(
        "Travel dates",
        value=(date.today() + timedelta(days=30), date.today() + timedelta(days=34)),
        min_value=date.today(),
        help="Select your start and end date.",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_date = end_date = date_range[0]
    else:
        start_date = end_date = date_range
    duration = st.slider("Duration (days)", min_value=1, max_value=14, value=5)
    # Dates anchor the trip; the explicit duration slider controls itinerary length.
    budget = st.selectbox("Budget level", ["Budget", "Moderate", "Luxury"], index=1)
    party = st.selectbox("Travel party", ["Solo", "Couple", "Family", "Friends"], index=1)
    pace = st.select_slider("Travel pace", options=["Relaxed", "Moderate", "Fast-Paced"], value="Moderate")
    interests = st.multiselect("Interests", INTERESTS, default=["Food", "History"])
    currency_label = st.selectbox("Display currency", list(CURRENCIES.keys()), index=1)
    st.markdown("---")
    st.markdown("### AI configuration")
    demo_mode = st.toggle(
        "Demo Mode", value=st.session_state.demo_mode,
        help="On: no API calls. Off: use the provider and API key below for AI-assisted notes and activity swaps.",
    )
    st.session_state.demo_mode = demo_mode
    provider = st.radio("AI provider", ["Gemini", "Groq"], horizontal=True)
    gemini_key = st.text_input("Gemini API key", type="password", placeholder="Paste Gemini key")
    groq_key = st.text_input("Groq API key", type="password", placeholder="Paste Groq key")
    active_key = gemini_key.strip() if provider == "Gemini" else groq_key.strip()
    st.markdown(
        '<div class="side-note">🔒 Keys are used only for requests during this session. For deployment, prefer Streamlit Secrets instead of entering production credentials into a shared device.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    generate_clicked = st.button("✦ Build my travel plan", type="primary", use_container_width=True)
    st.caption("No database required · Session-based trip vault")


# ---------------------------------------------------------------------------
# Header and initial itinerary generation
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Your next chapter starts here</div>
      <h1>Travel thoughtfully.<br>Remember everything.</h1>
      <p>A personal travel studio for meaningful discoveries, neighborhood-smart itineraries, and trips that feel like you.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if generate_clicked:
    if not destination_input.strip():
        st.session_state.sidebar_destination = ""
        st.session_state.pending_recommendations = recommend_destinations(interests, budget, pace, party)
        first = st.session_state.pending_recommendations[0]["city"]
        destination_to_use = st.session_state.selected_destination or first
        st.session_state.sidebar_destination = destination_to_use
    else:
        destination_to_use = destination_input.strip()
        st.session_state.sidebar_destination = destination_to_use
    trip = build_trip(
        destination_to_use, start_date, duration, budget, party, pace, interests,
        demo_mode, provider, active_key,
    )
    set_active_trip(trip)
    st.session_state.trips = [t for t in st.session_state.trips if t["id"] != trip["id"]]
    st.session_state.notice = f"Your {duration}-day plan for {destination_to_use} is ready."

if st.session_state.get("notice"):
    st.success(st.session_state.notice)
    st.session_state.notice = ""

active_trip = st.session_state.active_trip
if active_trip is None:
    st.markdown(
        """
        <div class="panel">
          <div class="eyebrow">A better way to get away</div>
          <h2 style="margin:.45rem 0">Start with a feeling, not a spreadsheet.</h2>
          <p class="muted">Choose your preferences in the sidebar, then build a plan. Leave the destination blank to explore personalized recommendations. Demo Mode is ready to go.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown("#### A little inspiration")
    cols = st.columns(3)
    for col, item in zip(cols, DESTINATIONS[:3]):
        with col:
            st.markdown(
                f"""<div class="destination-card"><div style="font-size:2rem">{item['image']}</div>
                <span class="pill pill-teal">{item['score']}% match</span>
                <h3>{item['city']}</h3><div class="muted">{item['reason']}</div></div>""",
                unsafe_allow_html=True,
            )
    st.stop()

# Sidebar edits are preferences for the next generated trip; currency remains live.
trip = active_trip
totals = get_totals(trip)
st.markdown(
    f"""
    <div class="section-head">
      <div><div class="eyebrow">Your current escape</div><h2 style="margin:.25rem 0">{trip['destination']}</h2>
      <p>{trip['start_date']} — {trip['end_date']} &nbsp;·&nbsp; {trip['days']} days &nbsp;·&nbsp; {trip['party']}</p></div>
      <div><span class="pill pill-teal">{trip['budget']} budget</span><span class="pill pill-amber">{trip['pace']} pace</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)
metric_cols = st.columns(3)
with metric_cols[0]:
    st.markdown(
        f'<div class="micro"><div class="micro-label">TOTAL ACTIVITY ESTIMATE · USD</div><div class="micro-value">${totals["usd"]:,.2f}</div><div class="micro-note">Across {totals["days"]} planned days</div></div>',
        unsafe_allow_html=True,
    )
with metric_cols[1]:
    st.markdown(
        f'<div class="micro"><div class="micro-label">CONVERTED TRIP TOTAL · {CURRENCIES[currency_label]["code"]}</div><div class="micro-value">{format_money(totals["usd"], currency_label)}</div><div class="micro-note">Indicative rate · editable in sidebar</div></div>',
        unsafe_allow_html=True,
    )
with metric_cols[2]:
    st.markdown(
        f'<div class="micro"><div class="micro-label">AVERAGE DAILY SPEND</div><div class="micro-value">{format_money(totals["daily"], currency_label)}</div><div class="micro-note">${totals["daily"]:,.2f} USD per day</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")
tab_recommend, tab_itinerary, tab_vibe, tab_vault = st.tabs([
    "✦ Destination Match", "▦ Your Itinerary", "↻ Customize the Vibe", "▤ Trip Vault"
])

# ---------------------------------------------------------------------------
# Tab 1: Destination recommender
# ---------------------------------------------------------------------------
with tab_recommend:
    st.markdown("### Find a destination that fits you")
    st.markdown(
        '<p class="muted">Recommendations use your selected interests, budget, travel party, and pace. Scores are illustrative demo match scores, not live travel data.</p>',
        unsafe_allow_html=True,
    )
    recommendations = recommend_destinations(trip["interests"], trip["budget"], trip["pace"], trip["party"])
    if destination_input.strip():
        st.info("You entered a destination. Explore alternatives below, or keep your current trip.")
    cards = st.columns(3)
    for idx, (col, item) in enumerate(zip(cards, recommendations)):
        with col:
            highlight_html = "".join([f'<span class="pill pill-slate">{x}</span>' for x in item["highlights"]])
            st.markdown(
                f"""
                <div class="destination-card">
                  <div style="display:flex;align-items:center;justify-content:space-between">
                    <div style="font-size:2.25rem">{item['image']}</div>
                    <span class="pill pill-teal">{item['score']}% Match</span>
                  </div>
                  <h3>{item['city']}</h3>
                  <span class="pill pill-amber">Best: {item['season']}</span>
                  <div style="margin:12px 0 8px">{highlight_html}</div>
                  <p class="muted">{item['reason']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Choose {item['city'].split(',')[0]} →", key=f"choose_dest_{idx}", use_container_width=True):
                new_trip = build_trip(
                    item["city"], start_date, duration, budget, party, pace, interests,
                    demo_mode, provider, active_key,
                )
                set_active_trip(new_trip)
                st.session_state.sidebar_destination = item["city"]
                st.session_state.trips = [t for t in st.session_state.trips if t["id"] != new_trip["id"]]
                st.session_state.notice = f"Destination updated to {item['city']}."
                st.rerun()
    st.markdown("")
    st.markdown(
        '<div class="panel"><b>Why these recommendations?</b><p class="muted">The demo recommender ranks a curated set of destinations against your selected preferences. In a production version, enrich this with seasonality, visa requirements, live flight prices, weather, accessibility, and current local events.</p></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Tab 2: Itinerary with geographically grouped activities
# ---------------------------------------------------------------------------
with tab_itinerary:
    st.markdown("### The day, thoughtfully mapped")
    st.markdown(
        '<p class="muted">Four sequential slots per day. Activities are grouped by district where possible to reduce unnecessary backtracking and transit fatigue.</p>',
        unsafe_allow_html=True,
    )
    for day in trip["itinerary"]:
        with st.expander(f"Day {day['day']:02d}  ·  {day['date']}  ·  {day['title']}", expanded=(day["day"] == 1)):
            day_total = sum(a["cost_usd"] for a in day["activities"].values())
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f'<span class="pill pill-teal">4 planned stops</span><span class="pill pill-slate">Neighborhood-first routing</span>', unsafe_allow_html=True)
            with c2:
                st.markdown(f"**Day estimate:** {format_money(day_total, currency_label)}")
            for idx, (slot_key, slot_name, emoji) in enumerate(SLOTS, start=1):
                st.markdown(f"**{emoji} {slot_name}**")
                render_activity(day["activities"][slot_key], currency_label, idx)
            st.caption("Routing note: district tags are planning aids, not turn-by-turn directions. Check real transit times before departure.")

# ---------------------------------------------------------------------------
# Tab 3: Change exactly one activity
# ---------------------------------------------------------------------------
with tab_vibe:
    st.markdown("### Make one moment more you")
    st.markdown(
        '<p class="muted">Choose one slot and describe the vibe you want. The rest of your itinerary is copied unchanged.</p>',
        unsafe_allow_html=True,
    )
    day_options = [d["day"] for d in trip["itinerary"]]
    selected_day = st.selectbox("Which day?", day_options, format_func=lambda x: f"Day {x} · {trip['itinerary'][x-1]['date']}")
    slot_labels = {f"{emoji} {name}": key for key, name, emoji in SLOTS}
    selected_slot_label = st.selectbox("Which time slot?", list(slot_labels.keys()))
    selected_slot = slot_labels[selected_slot_label]
    current_day = next(d for d in trip["itinerary"] if d["day"] == selected_day)
    current_activity = current_day["activities"][selected_slot]
    st.markdown(
        f"""
        <div class="panel">
          <div class="eyebrow">Currently planned</div>
          <h3 style="margin:.4rem 0">{current_activity['name']}</h3>
          <span class="pill pill-teal">District: {current_activity['district']}</span>
          <span class="pill pill-amber">{format_money(current_activity['cost_usd'], currency_label)}</span>
          <p class="muted" style="margin-top:10px">{current_activity['description']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    swap_request = st.text_area(
        "What would you rather do?",
        placeholder="e.g., Swap museum for an outdoor market, keep it affordable…",
        height=100,
        key="swap_request",
    )
    if st.button("↻ Regenerate this slot only", type="primary"):
        if not swap_request.strip():
            st.warning("Add a short request so the planner knows what to change.")
        else:
            try:
                updated_trip = swap_activity(
                    trip, selected_day, selected_slot, swap_request.strip(),
                    demo_mode, provider, active_key,
                )
                st.session_state.active_trip = updated_trip
                st.session_state.notice = f"Updated Day {selected_day} · {current_activity['slot_name']}. The other slots were preserved."
                st.session_state.swap_request = ""
                st.rerun()
            except Exception as exc:
                st.error(f"Could not update this slot: {exc}")
    st.markdown("")
    st.markdown(
        '<div class="panel"><b>Single-slot integrity</b><p class="muted">The planner deep-copies the active trip and changes only the selected day/slot. It does not regenerate other activities or alter their costs.</p></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Tab 4: Session vault and offline export
# ---------------------------------------------------------------------------
with tab_vault:
    st.markdown("### Your trip vault")
    st.markdown(
        '<p class="muted">Save several versions in this browser session, switch between them, and export a printable itinerary. Session trips are cleared when the Streamlit session resets.</p>',
        unsafe_allow_html=True,
    )
    vault_left, vault_right = st.columns([1, 1])
    with vault_left:
        st.markdown('<div class="panel"><h3>Save this trip</h3><p class="muted">Keep the current plan in your temporary vault so you can return to it later in this session.</p></div>', unsafe_allow_html=True)
        if st.button("＋ Save current trip to vault", type="primary", use_container_width=True):
            existing = next((i for i, t in enumerate(st.session_state.trips) if t["id"] == trip["id"]), None)
            saved = copy.deepcopy(trip)
            if existing is None:
                st.session_state.trips.append(saved)
            else:
                st.session_state.trips[existing] = saved
            st.success("Trip saved to this session's vault.")
    with vault_right:
        st.markdown('<div class="panel"><h3>Offline export</h3><p class="muted">Download a print-friendly PDF with a safety checklist. If ReportLab is unavailable, a JSON itinerary is provided instead.</p></div>', unsafe_allow_html=True)
        export_name = re.sub(r"[^A-Za-z0-9_-]+", "-", trip["destination"]).strip("-").lower() or "travel"
        try:
            export_bytes = pdf_export(trip, currency_label)
            export_is_pdf = REPORTLAB_AVAILABLE
            mime = "application/pdf" if export_is_pdf else "application/json"
            ext = "pdf" if export_is_pdf else "json"
            label = "⬇ Download printable PDF" if export_is_pdf else "⬇ Download JSON fallback"
            st.download_button(
                label, data=export_bytes,
                file_name=f"wanderlust-{export_name}-itinerary.{ext}",
                mime=mime, use_container_width=True,
            )
            if not REPORTLAB_AVAILABLE:
                st.warning("ReportLab is not installed. Exporting JSON fallback. Add `reportlab` to requirements.txt for PDF output.")
        except Exception as exc:
            st.error(f"Export could not be generated: {exc}")
            fallback = json.dumps(trip, indent=2, ensure_ascii=False).encode("utf-8")
            st.download_button(
                "Download JSON fallback", data=fallback,
                file_name=f"wanderlust-{export_name}-itinerary.json",
                mime="application/json", use_container_width=True,
            )

    st.markdown("---")
    st.markdown("#### Saved trips")
    if not st.session_state.trips:
        st.markdown(
            '<div class="panel"><div style="font-size:1.8rem">🧳</div><b>Your vault is waiting.</b><p class="muted">Save the current itinerary to keep it here during this session.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        for saved_trip in st.session_state.trips:
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.markdown(
                        f"**{saved_trip['destination']}**  \n"
                        f"<span class='muted'>{saved_trip['start_date']} · {saved_trip['days']} days · {saved_trip['budget']}</span>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    saved_total = get_totals(saved_trip)["usd"]
                    st.markdown(f"**${saved_total:,.0f}**<br><span class='muted'>activity total</span>", unsafe_allow_html=True)
                with c3:
                    if st.button("Load trip", key=f"load_{saved_trip['id']}", use_container_width=True):
                        set_active_trip(saved_trip)
                        st.session_state.sidebar_destination = saved_trip["destination"]
                        st.session_state.notice = f"Loaded {saved_trip['destination']} from your vault."
                        st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("Clear saved trips", type="secondary"):
            st.session_state.trips = []
            st.success("Session vault cleared.")

st.markdown(
    '<div class="footer">WANDERLUST · PLAN WITH INTENTION · TRAVEL WITH CURIOSITY<br>All costs are illustrative estimates. Exchange rates are fixed demo rates and are not live financial data.</div>',
    unsafe_allow_html=True,
)
