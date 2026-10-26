import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, date, timedelta
from io import BytesIO

# Try importing ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Try importing Google GenAI SDK
try:
    import google.generativeai as genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM WANDERLUST CSS STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Wanderlust AI - Personal Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Theme Color Palette */
    :root {
        --primary-teal: #0D9488;
        --dark-teal: #0F766E;
        --sunset-orange: #F97316;
        --sand-bg: #FDFBF7;
        --slate-gray: #334155;
    }
    
    /* Global Styles */
    .stApp {
        background-color: var(--sand-bg);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Header Styling */
    .hero-container {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 50%, #F97316 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(13, 148, 136, 0.3);
    }
    .hero-container h1 {
        color: white !important;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 0.5rem;
    }
    .hero-container p {
        font-size: 1.15rem;
        opacity: 0.95;
    }
    
    /* Card Component */
    .wander-card {
        background-color: #FFFFFF;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    
    /* Tag Styles */
    .tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .tag-teal { background-color: #CCFBF1; color: #0F766E; }
    .tag-orange { background-color: #FFEDD5; color: #C2410C; }
    .tag-slate { background-color: #F1F5F9; color: #475569; }
    
    /* Budget Metric Widget */
    .metric-card {
        background-color: #FFFFFF;
        border-left: 4px solid var(--primary-teal);
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    
    /* Custom Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DEMO MOCK DATA & FALLBACK GENERATOR
# -----------------------------------------------------------------------------
DEMO_RECOMMENDATIONS = [
    {
        "city": "Kyoto",
        "country": "Japan",
        "vibe": "Cultural & Serene",
        "best_season": "Spring (Mar-May) / Autumn (Sep-Nov)",
        "match_score": "98%",
        "highlights": ["Ancient Shrines", "Matcha Tea Ceremonies", "Bamboo Groves", "Traditional Ryokans"],
        "reason": "Perfect match for your interest in History & Food with a Moderate pace. Spring cherry blossoms provide unforgettable scenic beauty."
    },
    {
        "city": "Florence",
        "country": "Italy",
        "vibe": "Artistic & Culinary",
        "best_season": "April to October",
        "match_score": "94%",
        "highlights": ["Renaissance Masterpieces", "Tuscan Wine Tours", "Historic Duomo", "Artisanal Markets"],
        "reason": "Aligns seamlessly with your love for rich heritage, walkable city centers, and world-class dining opportunities."
    },
    {
        "city": "Reykjavik",
        "country": "Iceland",
        "vibe": "Adventure & Nature",
        "best_season": "September to April (Northern Lights)",
        "match_score": "91%",
        "highlights": ["Geothermal Spas", "Glacier Hikes", "Northern Lights", "Volcanic Landscapes"],
        "reason": "An ideal destination for adventurous spirits looking for breathtaking landscapes paired with unique cultural comfort."
    }
]

def get_demo_itinerary(destination, days, budget, currency_symbol, exchange_rate):
    """Generates structured mock data when running in Demo Mode."""
    dest = destination if destination else "Tokyo, Japan"
    itinerary = []
    
    activities_pool = [
        {"slot": "Morning Sightseeing", "title": "Historic Temple & Garden Tour", "desc": "Explore iconic landmark sites and traditional gardens during peak quiet hours.", "cluster": "North District", "cost_usd": 25},
        {"slot": "Lunch Recommendation", "title": "Artisanal Local Bistro", "desc": "Sample signature local dishes at a highly-rated family-run eatery.", "cluster": "North District", "cost_usd": 20},
        {"slot": "Afternoon Leisure", "title": "Cultural District Walk & Artisan Shops", "desc": "Stroll through historic alleys, artisan crafts shops, and scenic vantage points.", "cluster": "North District", "cost_usd": 15},
        {"slot": "Evening Dining & Entertainment", "title": "Riverside Dining & Night Market", "desc": "Savor authentic evening cuisine followed by a stroll through vibrant night markets.", "cluster": "Central District", "cost_usd": 40}
    ]
    
    mult = 0.6 if budget == "Budget" else (1.0 if budget == "Moderate" else 2.2)
    
    for day in range(1, days + 1):
        day_plan = {
            "day": day,
            "theme": f"Exploring {dest} - District Highlights Day {day}",
            "district_cluster": f"Zone {((day - 1) % 3) + 1} (Minimized Transit)",
            "slots": []
        }
        for act in activities_pool:
            cost_usd = round(act["cost_usd"] * mult)
            cost_local = round(cost_usd * exchange_rate, 2)
            day_plan["slots"].append({
                "time_slot": act["slot"],
                "activity_name": f"{act['title']} (Day {day})",
                "description": act["desc"],
                "geographic_cluster": day_plan["district_cluster"],
                "estimated_cost_usd": cost_usd,
                "estimated_cost_local": cost_local,
                "currency_symbol": currency_symbol
            })
        itinerary.append(day_plan)
    return itinerary

# -----------------------------------------------------------------------------
# 3. LLM API & PROMPT ENGINE (GEMINI & GROQ INTEGRATION)
# -----------------------------------------------------------------------------
def call_gemini_api(api_key, prompt):
    """Call Google Gemini API using native SDK or direct web structure."""
    if not GEMINI_SDK_AVAILABLE:
        raise Exception("Google GenerativeAI SDK is not installed. Please install `google-generativeai`.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return response.text

def call_groq_api(api_key, prompt):
    """Call Groq API using HTTP requests."""
    import urllib.request
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are an expert travel planner API that responds ONLY in valid raw JSON format."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "response_format": {"type": "json_object"}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        return res_data['choices'][0]['message']['content']

def query_llm(prompt, provider, api_key, is_demo):
    """Central gateway for handling LLM calls with robust error fallbacks."""
    if is_demo or not api_key:
        st.info("ℹ️ Running in **Demo Mode** using smart deterministic fallback logic.")
        return None
    try:
        if provider == "Google Gemini":
            return call_gemini_api(api_key, prompt)
        elif provider == "Groq (Llama 3.3)":
            return call_groq_api(api_key, prompt)
    except Exception as e:
        st.error(f"⚠️ API Error ({provider}): {str(e)}. Falling back to Demo Mode.")
        return None

# -----------------------------------------------------------------------------
# 4. JSON PARSER UTILITIES
# -----------------------------------------------------------------------------
def clean_json_response(raw_text):
    """Extract and parse JSON from API text response safely."""
    if not raw_text:
        return None
    try:
        # Direct parse attempt
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Regex search for markdown block or raw braces
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match_brace = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', raw_text)
        if match_brace:
            try:
                return json.loads(match_brace.group(0))
            except json.JSONDecodeError:
                pass
    return None

# -----------------------------------------------------------------------------
# 5. PDF GENERATION ENGINE (REPORTLAB)
# -----------------------------------------------------------------------------
def generate_pdf_itinerary(trip_data):
    """Generates a styled offline PDF travel itinerary document using ReportLab."""
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette & Typography
    primary_color = colors.HexColor("#0F766E")
    secondary_color = colors.HexColor("#F97316")
    text_color = colors.HexColor("#334155")
    bg_light = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=text_color,
        spaceAfter=15
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=text_color,
        leading=12
    )

    story = []

    # Title & Metadata Header
    dest_name = trip_data.get('destination', 'Travel Itinerary')
    story.append(Paragraph(f"✈️ Travel Itinerary: {dest_name}", title_style))
    
    meta_text = f"<b>Dates:</b> {trip_data.get('dates', 'N/A')} | <b>Duration:</b> {trip_data.get('days')} Days | <b>Party:</b> {trip_data.get('party')} | <b>Pace:</b> {trip_data.get('pace')}"
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=15))

    # Day-by-Day Detailed Schedule
    itinerary = trip_data.get('itinerary', [])
    for day in itinerary:
        day_num = day.get('day', '')
        theme = day.get('theme', '')
        cluster = day.get('district_cluster', '')
        
        story.append(Paragraph(f"Day {day_num}: {theme}", heading_style))
        if cluster:
            story.append(Paragraph(f"<i>Geographic Focus: {cluster}</i>", body_style))
        story.append(Spacer(1, 4))

        # Table for Activities
        table_data = [["Time Slot", "Activity & Details", "Est. Cost"]]
        for slot in day.get('slots', []):
            time_slot = slot.get('time_slot', '')
            act_name = slot.get('activity_name', '')
            desc = slot.get('description', '')
            cost_usd = slot.get('estimated_cost_usd', 0)
            cost_local = slot.get('estimated_cost_local', 0)
            sym = slot.get('currency_symbol', '$')

            details_p = Paragraph(f"<b>{act_name}</b><br/>{desc}", body_style)
            cost_p = Paragraph(f"${cost_usd} USD<br/>({sym}{cost_local})", body_style)
            table_data.append([time_slot, details_p, cost_p])

        t = Table(table_data, colWidths=[120, 320, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    # Emergency & Safety Checklist
    story.append(HRFlowable(width="100%", thickness=1, color=secondary_color, spaceBefore=10, spaceAfter=10))
    story.append(Paragraph("🚨 Emergency & Safety Checklist", heading_style))
    
    emergency_contacts = [
        ["Contact / Service", "Details / Phone Number"],
        ["Local Emergency Services (Police/Ambulance)", "112 (Europe) / 911 (US) / Local Equivalent"],
        ["Embassy / Consulate Info", "Keep contact details of your local embassy on hand."],
        ["Travel Insurance Policy", "Policy # & Hotline saved on mobile device."],
        ["Hotel / Accommodation", "Primary Address & Front Desk phone number logged."]
    ]
    em_table = Table(emergency_contacts, colWidths=[220, 320])
    em_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(em_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# -----------------------------------------------------------------------------
# 6. SESSION STATE & STORAGE INITIALIZATION
# -----------------------------------------------------------------------------
if "saved_trips" not in st.session_state:
    st.session_state.saved_trips = []

if "current_itinerary" not in st.session_state:
    st.session_state.current_itinerary = None

if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = None

# -----------------------------------------------------------------------------
# 7. SIDEBAR: CONFIGURATION & USER PREFERENCES (EPIC 3)
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/illustrations/100/compass.png", width=70)
st.sidebar.title("🧭 Trip Preferences")

# 1. API Configuration
with st.sidebar.expander("🔑 API & Mode Settings", expanded=False):
    demo_mode = st.checkbox("Enable Demo Mode (No API key needed)", value=True)
    provider = st.selectbox("LLM Provider", ["Google Gemini", "Groq (Llama 3.3)"])
    api_key = st.text_input("Enter API Key", type="password", disabled=demo_mode)

st.sidebar.markdown("---")

# 2. Trip Specification Form
destination_input = st.sidebar.text_input(
    "📍 Destination City / Country",
    placeholder="e.g., Paris, Kyoto or leave blank for recommendations",
    help="Leave blank if you want Smart Destination Recommendations!"
)

vibe_input = st.sidebar.multiselect(
    "🎨 Preferred Vibe / Atmosphere",
    ["Beach & Coastal", "Mountain & Nature", "Cultural & Heritage", "Urban Exploration", "Foodie & Culinary", "Relaxation & Spa"],
    default=["Cultural & Heritage"]
)

col_d1, col_d2 = st.sidebar.columns(2)
with col_d1:
    trip_days = st.number_input("⏱️ Duration (Days)", min_value=1, max_value=14, value=3)
with col_d2:
    budget_level = st.selectbox("💰 Budget", ["Budget", "Moderate", "Luxury"], index=1)

travel_dates = st.sidebar.date_input(
    "📅 Travel Range",
    value=(date.today() + timedelta(days=30), date.today() + timedelta(days=33))
)

col_p1, col_p2 = st.sidebar.columns(2)
with col_p1:
    travel_party = st.selectbox("👥 Party", ["Solo", "Couple", "Family", "Friends"])
with col_p2:
    pace = st.selectbox("⚡ Pace", ["Relaxed", "Moderate", "Fast-Paced"])

interests = st.sidebar.multiselect(
    "🎯 Core Interests",
    ["Food & Dining", "Adventure & Sports", "History & Museums", "Nightlife & Bars", "Shopping", "Nature & Wildlife"],
    default=["Food & Dining", "History & Museums"]
)

# Currency Selector
currency_option = st.sidebar.selectbox("💱 Display Currency", ["USD ($)", "INR (₹)", "EUR (€)", "GBP (£)"])
currency_map = {"USD ($)": ("$", 1.0), "INR (₹)": ("₹", 83.0), "EUR (€)": ("€", 0.92), "GBP (£)": ("£", 0.79)}
currency_symbol, exchange_rate = currency_map[currency_option]

# -----------------------------------------------------------------------------
# 8. MAIN UI LAYOUT & HERO HEADER
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <h1>✈️ Personalized Travel Itinerary Planner</h1>
    <p>AI-powered geographic clustering, smart dynamic activity swaps, and offline itinerary exports.</p>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "💡 Destination Finder",
    "📅 Optimized Itinerary",
    "🔀 Vibe Swap",
    "💼 Trip Manager & PDF"
])

# -----------------------------------------------------------------------------
# TAB 1: SMART DESTINATION RECOMMENDER (EPIC 3)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("💡 Smart Destination Recommendations")
    st.write("Not sure where to head next? Let AI analyze your preferences, budget, and desired vibe to suggest top matches.")

    if st.button("✨ Recommend Top Destinations", type="primary", use_container_width=True):
        with st.spinner("Analyzing global weather, budget tiers, and local vibes..."):
            prompt = f"""
            Act as a world-class travel advisor. Recommend top 3 matching cities based on:
            Vibe: {', '.join(vibe_input)}
            Budget: {budget_level}
            Duration: {trip_days} days
            Interests: {', '.join(interests)}
            Party: {travel_party}

            Return RAW JSON format ONLY matching this exact structure:
            [
              {{
                "city": "City Name",
                "country": "Country",
                "vibe": "Short Vibe Summary",
                "best_season": "Optimal months",
                "match_score": "95%",
                "highlights": ["Highlight 1", "Highlight 2", "Highlight 3"],
                "reason": "Clear explanation why this fits user preferences."
              }}
            ]
            """
            raw_res = query_llm(prompt, provider, api_key, demo_mode)
            recs = clean_json_response(raw_res)
            
            if not recs or not isinstance(recs, list):
                recs = DEMO_RECOMMENDATIONS
            
            st.session_state.current_recommendations = recs

    if st.session_state.current_recommendations:
        cols = st.columns(3)
        for idx, rec in enumerate(st.session_state.current_recommendations):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="wander-card">
                    <span class="tag tag-orange">{rec.get('match_score', '90% Match')}</span>
                    <span class="tag tag-teal">{rec.get('vibe', 'Scenic')}</span>
                    <h3>{rec.get('city')}, {rec.get('country')}</h3>
                    <p><b>Best Time to Visit:</b> {rec.get('best_season')}</p>
                    <p>{rec.get('reason')}</p>
                    <hr style="margin: 0.5rem 0;"/>
                    <b>Key Highlights:</b><br/>
                    {' '.join([f'<span class="tag tag-slate">{h}</span>' for h in rec.get('highlights', [])])}
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Select {rec.get('city')}", key=f"sel_{idx}"):
                    st.success(f"Selected **{rec.get('city')}**! Head over to Tab 2 to generate your day-by-day plan.")

# -----------------------------------------------------------------------------
# TAB 2: DAY-BY-DAY OPTIMIZED ITINERARY GENERATOR (EPIC 4)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("📅 Day-by-Day Geographically Clustered Itinerary")
    
    target_dest = destination_input.strip() if destination_input.strip() else "Kyoto, Japan"
    
    col_gen1, col_gen2 = st.columns([3, 1])
    with col_gen1:
        st.info(f"📍 Current Target: **{target_dest}** | Duration: **{trip_days} Days** | Budget: **{budget_level}**")
    with col_gen2:
        generate_btn = st.button("🚀 Generate Itinerary", type="primary", use_container_width=True)

    if generate_btn:
        with st.spinner(f"Clustering neighborhood attractions & balancing schedules for {target_dest}..."):
            prompt = f"""
            Create a highly structured day-wise travel itinerary for {target_dest}.
            Duration: {trip_days} days.
            Budget Level: {budget_level}.
            Party: {travel_party}. Pace: {pace}.
            Interests: {', '.join(interests)}.

            CRITICAL REQUIREMENTS:
            1. Group geographically close attractions on the same day to minimize transit fatigue.
            2. Format output strictly in JSON.
            
            JSON Structure:
            [
              {{
                "day": 1,
                "theme": "Historic Core & Culinary Evening",
                "district_cluster": "Old Town / North District",
                "slots": [
                  {{
                    "time_slot": "Morning Sightseeing",
                    "activity_name": "Specific Famous Landmark",
                    "description": "2-sentence vivid description.",
                    "geographic_cluster": "North District",
                    "estimated_cost_usd": 20
                  }},
                  {{
                    "time_slot": "Lunch Recommendation",
                    "activity_name": "Authentic Local Eatery",
                    "description": "Must-try local dish details.",
                    "geographic_cluster": "North District",
                    "estimated_cost_usd": 15
                  }},
                  {{
                    "time_slot": "Afternoon Leisure",
                    "activity_name": "Park or Neighborhood Exploration",
                    "description": "Relaxed scenic stroll.",
                    "geographic_cluster": "North District",
                    "estimated_cost_usd": 10
                  }},
                  {{
                    "time_slot": "Evening Dining & Entertainment",
                    "activity_name": "Nightlife or River Evening",
                    "description": "Atmospheric evening experience.",
                    "geographic_cluster": "Central District",
                    "estimated_cost_usd": 35
                  }}
                ]
              }}
            ]
            """
            raw_resp = query_llm(prompt, provider, api_key, demo_mode)
            parsed_itinerary = clean_json_response(raw_resp)
            
            if not parsed_itinerary or not isinstance(parsed_itinerary, list):
                parsed_itinerary = get_demo_itinerary(target_dest, trip_days, budget_level, currency_symbol, exchange_rate)
            else:
                # Recalculate currency values for API response
                for day in parsed_itinerary:
                    for slot in day.get('slots', []):
                        cost_usd = slot.get('estimated_cost_usd', 15)
                        slot['estimated_cost_local'] = round(cost_usd * exchange_rate, 2)
                        slot['currency_symbol'] = currency_symbol

            st.session_state.current_itinerary = {
                "destination": target_dest,
                "days": trip_days,
                "budget_level": budget_level,
                "party": travel_party,
                "pace": pace,
                "dates": f"{travel_dates[0]} to {travel_dates[1]}" if isinstance(travel_dates, tuple) and len(travel_dates) == 2 else str(travel_dates),
                "itinerary": parsed_itinerary
            }

    # Render Current Itinerary
    if st.session_state.current_itinerary:
        plan_data = st.session_state.current_itinerary
        itinerary = plan_data['itinerary']
        
        # Calculate Running & Total Budget Metrics
        total_usd = 0
        for d in itinerary:
            for s in d.get('slots', []):
                total_usd += s.get('estimated_cost_usd', 0)
        total_local = round(total_usd * exchange_rate, 2)
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Days", f"{plan_data['days']} Days")
        with m2:
            st.metric("Est. Cost (USD)", f"${total_usd} USD")
        with m3:
            st.metric(f"Est. Cost ({currency_symbol})", f"{currency_symbol}{total_local}")
        with m4:
            st.metric("Avg. Daily Cost", f"${round(total_usd / max(1, plan_data['days']))} / day")
            
        st.markdown("---")

        # Display Day-wise Accordions
        for day_obj in itinerary:
            day_num = day_obj.get('day', 1)
            theme = day_obj.get('theme', 'Exploration')
            cluster = day_obj.get('district_cluster', 'City Center')
            
            with st.expander(f"📍 **Day {day_num}: {theme}**  |  🗺️ *Cluster: {cluster}*", expanded=True):
                for slot in day_obj.get('slots', []):
                    c1, c2, c3 = st.columns([1.5, 4, 1.5])
                    with c1:
                        st.markdown(f"**{slot.get('time_slot')}**")
                        st.caption(f"📍 {slot.get('geographic_cluster', 'Local Zone')}")
                    with c2:
                        st.markdown(f"**{slot.get('activity_name')}**")
                        st.write(slot.get('description'))
                    with c3:
                        c_usd = slot.get('estimated_cost_usd', 0)
                        c_loc = round(c_usd * exchange_rate, 2)
                        st.markdown(f"💰 **${c_usd}** USD")
                        st.caption(f"({currency_symbol}{c_loc})")
                    st.markdown("<hr style='margin:0.3rem 0; border-top:1px dashed #E2E8F0;'/>", unsafe_allow_html=True)
    else:
        st.info("👆 Click **Generate Itinerary** above to build your customized travel plan.")

# -----------------------------------------------------------------------------
# TAB 3: VIBE CUSTOMIZATION & DYNAMIC ACTIVITY SWAP (EPIC 4)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("🔀 Dynamic Single-Day Activity Swap")
    st.write("Modify specific time slots or change the vibe of a single day without wiping the rest of your itinerary.")

    if not st.session_state.current_itinerary:
        st.warning("⚠️ Please generate an itinerary in Tab 2 before customizing activities.")
    else:
        itinerary_data = st.session_state.current_itinerary['itinerary']
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            selected_day_num = st.selectbox(
                "Select Day to Modify",
                options=[d['day'] for d in itinerary_data],
                format_func=lambda x: f"Day {x}: {itinerary_data[x-1].get('theme', '')}"
            )
        with col_s2:
            swap_slot = st.selectbox(
                "Select Time Slot",
                ["Morning Sightseeing", "Lunch Recommendation", "Afternoon Leisure", "Evening Dining & Entertainment"]
            )

        swap_instruction = st.text_input(
            "💬 Custom Request / Modification Preference",
            placeholder="e.g. 'Swap museum for outdoor market', 'Find vegetarian lunch spot', 'Make it low energy'"
        )

        if st.button("🔄 Swap Activity for Selected Slot", type="primary"):
            if not swap_instruction:
                st.error("Please enter a custom modification request.")
            else:
                with st.spinner(f"Regenerating {swap_slot} for Day {selected_day_num}..."):
                    day_idx = selected_day_num - 1
                    target_day = itinerary_data[day_idx]
                    
                    prompt = f"""
                    Regenerate ONLY the '{swap_slot}' slot for Day {selected_day_num} in {st.session_state.current_itinerary['destination']}.
                    User Modification Request: "{swap_instruction}".
                    Current District Cluster: {target_day.get('district_cluster')}.
                    
                    Return RAW JSON ONLY matching this format:
                    {{
                        "time_slot": "{swap_slot}",
                        "activity_name": "New Swapped Activity",
                        "description": "Updated description tailored to request.",
                        "geographic_cluster": "{target_day.get('district_cluster')}",
                        "estimated_cost_usd": 25
                    }}
                    """
                    raw_swap = query_llm(prompt, provider, api_key, demo_mode)
                    parsed_swap = clean_json_response(raw_swap)
                    
                    if not parsed_swap:
                        # Demo fallback replacement
                        parsed_swap = {
                            "time_slot": swap_slot,
                            "activity_name": f"Custom Swapped: {swap_instruction.capitalize()}",
                            "description": f"Tailored activity replacement matching your preference for '{swap_instruction}' in the {target_day.get('district_cluster')} area.",
                            "geographic_cluster": target_day.get('district_cluster', 'Central'),
                            "estimated_cost_usd": 20
                        }

                    parsed_swap['estimated_cost_local'] = round(parsed_swap.get('estimated_cost_usd', 20) * exchange_rate, 2)
                    parsed_swap['currency_symbol'] = currency_symbol

                    # Update only the specific slot in place
                    slots = target_day.get('slots', [])
                    updated = False
                    for idx, s in enumerate(slots):
                        if s.get('time_slot') == swap_slot:
                            slots[idx] = parsed_swap
                            updated = True
                            break
                    if not updated:
                        slots.append(parsed_swap)

                    st.success(f"Successfully updated **{swap_slot}** on Day {selected_day_num}!")

        st.markdown("---")
        st.subheader("Preview Updated Day")
        preview_day = itinerary_data[selected_day_num - 1]
        for slot in preview_day.get('slots', []):
            st.markdown(f"**{slot.get('time_slot')}**: {slot.get('activity_name')}")
            st.caption(slot.get('description'))

# -----------------------------------------------------------------------------
# TAB 4: TRIP MANAGEMENT & OFFLINE PDF EXPORT (EPIC 5)
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("💼 Trip Management & Offline Export")

    # 1. Save Trip Functionality
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.write("Save your generated itinerary to local session history or export a print-ready offline PDF guide.")
    with col_t2:
        if st.button("💾 Save Current Trip", use_container_width=True):
            if st.session_state.current_itinerary:
                # Check for duplicates
                dest_name = st.session_state.current_itinerary['destination']
                st.session_state.saved_trips.append(dict(st.session_state.current_itinerary))
                st.success(f"Saved trip to **{dest_name}** to history!")
            else:
                st.warning("No active itinerary found to save. Generate one in Tab 2 first.")

    st.markdown("---")

    # 2. Offline PDF Export Section
    st.subheader("📄 Generate Offline PDF Guide")
    if st.session_state.current_itinerary:
        curr_trip = st.session_state.current_itinerary
        st.write(f"Ready to export: **{curr_trip['destination']}** ({curr_trip['days']} Days)")
        
        pdf_buffer = generate_pdf_itinerary(curr_trip)
        
        if pdf_buffer:
            st.download_button(
                label="📥 Download PDF Itinerary & Safety Checklist",
                data=pdf_buffer,
                file_name=f"Wanderlust_Itinerary_{curr_trip['destination'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        else:
            st.error("ReportLab library is not installed. Please install `reportlab` to enable PDF downloads.")
            # Fallback JSON Download
            json_str = json.dumps(curr_trip, indent=2)
            st.download_button(
                label="📥 Download JSON Itinerary Data",
                data=json_str,
                file_name=f"Itinerary_{curr_trip['destination']}.json",
                mime="application/json"
            )
    else:
        st.info("Generate an itinerary in Tab 2 to enable PDF export.")

    st.markdown("---")

    # 3. Saved Trip History Viewer
    st.subheader("📜 Saved Trip History")
    if len(st.session_state.saved_trips) == 0:
        st.caption("No saved trips yet. Click 'Save Current Trip' above to build your travel vault.")
    else:
        for idx, saved in enumerate(st.session_state.saved_trips):
            with st.expander(f"🧳 Trip #{idx+1}: {saved['destination']} ({saved['days']} Days - {saved['budget_level']})"):
                st.write(f"**Dates:** {saved.get('dates', 'N/A')} | **Party:** {saved.get('party')} | **Pace:** {saved.get('pace')}")
                if st.button("Load into Active View", key=f"load_{idx}"):
                    st.session_state.current_itinerary = saved
                    st.success(f"Loaded {saved['destination']} into active workspace! Check Tab 2.")
