import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import pandas as pd
from datetime import datetime

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

# --- User input for city ---
city = st.text_input("Enter your city to find nearby concerts", "New York")

# --- Fetch top 50 artists from Spotify ---
results = sp.current_user_top_artists(limit=50, time_range='medium_term')
artist_names = [artist['name'] for artist in results['items']]

# --- Exclude certain artists ---
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
            venue = event["_embedded"]["venues"][0]
            events.append({
                "Artist": artist_name,
                "Date": event["dates"]["start"]["localDate"],
                "Time": event["dates"]["start"].get("localTime", ""),
                "Venue": venue["name"],
                "City": venue["city"]["name"],
                "Event": event["name"],
                "Link": event["url"],
                "Opening Act": ""  # Ticketmaster doesn't provide this info
            })
    return events

# --- Fetch events for all artists and show results ---
if city:
    concert_data = []
    with st.spinner("Fetching concerts for your top artists..."):
        for artist in artist_names:
            events = get_ticketmaster_events(artist, city)
            concert_data.extend(events)
    
    if concert_data:
        df = pd.DataFrame(concert_data)
        df['Date'] = pd.to_datetime(df['Date'])
        df.sort_values(by="Date", inplace=True)
        df['Date'] = df['Date'].dt.strftime('%b %d %Y')
        st.markdown(f"### 🎤 Upcoming Concerts Near {city.title()}")
        st.dataframe(df[['Artist', 'Date', 'Venue', 'City', 'Time', 'Event', 'Opening Act', 'Link']], use_container_width=True)
    else:
        st.info(f"No upcoming concerts found for your top artists near {city.title()}.")
else:
    st.info("Please enter a city to search for concerts.")
