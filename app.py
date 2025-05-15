import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import urlencode

# --- Page setup ---
st.set_page_config(page_title="Concert Tracker", layout="wide")
st.title("🎶 Your Personal Concert Tracker")

# --- Spotify Authentication ---
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=st.secrets["SPOTIFY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
    scope="user-top-read"
))

# --- Fetch top 100 artists ---
results = sp.current_user_top_artists(limit=50, time_range='medium_term')
artist_names = [artist['name'] for artist in results['items']]

# --- Exclude kids/music ---
excluded_artists = {"blippi", "ms. rachel", "raffi", "beyonce", "robyn", "chappell roan", "elmo", "doobie brothers"}
artist_names = [name for name in artist_names if name.lower() not in excluded_artists]

# --- Ticketmaster API key from Streamlit secrets ---
TICKETMASTER_API_KEY = st.secrets["TICKETMASTER_API_KEY"]

def get_ticketmaster_events(artist_name, city, radius=30):
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "keyword": artist_name,
        "city": city,
        "radius": radius,
        "unit": "miles",
        "sort": "date,asc",
        "countryCode": "US"
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    events = []
    if "_embedded" in data and "events" in data["_embedded"]:
        for event in data["_embedded"]["events"]:
            events.append({
                "Artist": artist_name,
                "Date": event["dates"]["start"]["localDate"],
                "Time": event["dates"]["start"].get("localTime", ""),
                "Venue": event["_embedded"]["venues"][0]["name"],
                "City": event["_embedded"]["venues"][0]["city"]["name"],
                "Event": event["name"],
                "Link": event["url"],
                "Opening Act": ""  # Ticketmaster API does not explicitly provide this
            })
    return events

# --- Display Data ---
if concert_data:
    df = pd.DataFrame(concert_data)
    df.sort_values(by="Date", inplace=True)
    df['Date'] = df['Date'].dt.strftime('%b %d %Y')
    st.markdown("### 🎤 Upcoming Concerts Near NYC")
    st.dataframe(df[['Artist', 'Date', 'Venue', 'City', 'Time', 'Event', 'Opening Act', 'Link']], use_container_width=True)
else:
    st.info("No upcoming concerts found for your top artists near New York, NY.")
