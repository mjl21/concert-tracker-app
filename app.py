import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import pandas as pd
from datetime import datetime

# --- Streamlit page config ---
st.set_page_config(page_title="Concert Tracker", layout="wide")
st.title("🎶 Your Personal Concert Tracker")

# --- Secrets and Config ---
SPOTIPY_CLIENT_ID = st.secrets["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]
SPOTIPY_REDIRECT_URI = st.secrets["SPOTIPY_REDIRECT_URI"]
TICKETMASTER_API_KEY = st.secrets["TICKETMASTER_API_KEY"]

# --- Spotify Authentication ---
scope = "user-top-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=scope
))

# --- Excluded artists ---
excluded_artists = {'blippi', 'ms. rachel', 'raffi', 'beyoncé', 'robyn', 'chappell roan', 'the doobie brothers'}

# --- Helper: Format 24h to 12h time ---
def format_time_12h(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M:%S").strftime("%-I:%M%p").lower()
    except:
        return ''

# --- Fetch user's top artists from Spotify ---
@st.cache_data(show_spinner=False)
def fetch_top_artists():
    top_artists = []
    for offset in [0, 49]:  # fetch 100 total, 50 per batch
        results = sp.current_user_top_artists(limit=50, offset=offset, time_range='medium_term')
        top_artists.extend(results['items'])
    filtered = [artist['name'] for artist in top_artists if artist['name'].strip().lower() not in excluded_artists]
    return filtered

artist_names = fetch_top_artists()

st.write(f"🎧 Found {len(artist_names)} top artists after exclusions.")

# --- Fetch Ticketmaster concerts ---
def find_concerts(artist_name):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        'apikey': TICKETMASTER_API_KEY,
        'keyword': artist_name,
        'latlong': '40.7128,-74.0060',  # NYC coords
        'radius': 30,
        'unit': 'miles',
        'countryCode': 'US',
        'classificationName': 'Music',
        'size': 3
    }
    res = requests.get(url, params=params)
    data = res.json()

    concerts = []
    if '_embedded' in data:
        events = data['_embedded'].get('events', [])
        for event in events:
            start_info = event['dates']['start']
            local_date = start_info.get('localDate', '')
            local_time = format_time_12h(start_info.get('localTime', ''))
            formatted_date = datetime.strptime(local_date, '%Y-%m-%d').strftime('%b %d %Y') if local_date else ''

            venue_info = event['_embedded']['venues'][0]
            venue = venue_info.get('name', '')
            city_name = venue_info.get('city', {}).get('name', '')
            state_code = venue_info.get('state', {}).get('stateCode', '')
            full_city = f"{city_name}, {state_code}".strip(', ')

            # Opening acts (attractions other than main artist)
            openers = []
            for attraction in event['_embedded'].get('attractions', []):
                if attraction.get('name', '').lower() != artist_name.lower():
                    openers.append(attraction.get('name'))
            opening_acts = ', '.join(openers) if openers else ''

            concerts.append({
                'Artist': artist_name,
                'Date': formatted_date,
                'Venue': venue,
                'City': full_city,
                'Time': local_time,
                'Event': event.get('name', ''),
                'Opening Act': opening_acts,
                'Link': f"[Buy Tickets]({event['url']})"
            })
    return concerts

# --- Aggregate concerts for all artists ---
concert_data = []
with st.spinner("Fetching concerts for your top artists..."):
    for artist in artist_names:
        concert_data.extend(find_concerts(artist))

# --- Display concert data ---
if concert_data:
    df = pd.DataFrame(concert_data)
    df['Date'] = pd.to_datetime(df['Date'], format='%b %d %Y', errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date')
    df['Date'] = df['Date'].dt.strftime('%b %d %Y')

    st.markdown("### 🎤 Upcoming Concerts Near New York, NY")
    st.dataframe(df[['Artist', 'Date', 'Venue', 'City', 'Time', 'Event', 'Opening Act', 'Link']], use_container_width=True)
else:
    st.info("No upcoming concerts found for your top artists within 30 miles of New York, NY.")
