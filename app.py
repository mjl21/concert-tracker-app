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

# --- Query Songkick API ---
concert_data = []
for artist in artist_names:
    params = {
        "apikey": st.secrets["SONGKICK_API_KEY"],
        "query": artist
    }
    response = requests.get("https://api.songkick.com/api/3.0/search/artists.json", params=params)
    results = response.json()

    if results['resultsPage']['totalEntries'] > 0:
        artist_id = results['resultsPage']['results']['artist'][0]['id']
        gig_url = f"https://api.songkick.com/api/3.0/artists/{artist_id}/calendar.json"
        gigs = requests.get(gig_url, params={"apikey": st.secrets["SONGKICK_API_KEY"]}).json()

        for event in gigs['resultsPage']['results'].get('event', []):
            location = event['location']['city']
            if "New York" in location or "NY" in location or "Brooklyn" in location:  # crude filter for 30-mile radius
                date = datetime.strptime(event['start']['date'], "%Y-%m-%d")
                time_str = event['start'].get('time', '')
                if time_str:
                    time_fmt = datetime.strptime(time_str, "%H:%M:%S").strftime("%-I:%M%p").lower()
                else:
                    time_fmt = "TBD"
                concert_data.append({
                    "Artist": artist,
                    "Date": date,
                    "Venue": event['venue']['displayName'],
                    "City": location,
                    "Time": time_fmt,
                    "Event": event['displayName'],
                    "Opening Act": ', '.join(p['artist']['displayName'] for p in event['performance'][1:]) if len(event['performance']) > 1 else '',
                    "Link": f"[Link]({event['uri']})"
                })

# --- Display Data ---
if concert_data:
    df = pd.DataFrame(concert_data)
    df.sort_values(by="Date", inplace=True)
    df['Date'] = df['Date'].dt.strftime('%b %d %Y')
    st.markdown("### 🎤 Upcoming Concerts Near NYC")
    st.dataframe(df[['Artist', 'Date', 'Venue', 'City', 'Time', 'Event', 'Opening Act', 'Link']], use_container_width=True)
else:
    st.info("No upcoming concerts found for your top artists near New York, NY.")
