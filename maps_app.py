import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from dotenv import load_dotenv
import os
import time
from streamlit_geolocation import streamlit_geolocation

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    st.error("GOOGLE_MAPS_API_KEY environment variable is not set.")
    st.stop()

st.title("Most Reviewed Places Finder")

# Initialize session state for place_query
if "previous_query" not in st.session_state:
    st.session_state.previous_query = ""

# Add a text input for the search box
place_query = st.text_input("Search for a city:", "")

# Function to fetch place details using Google Places API
def fetch_place_details(query):
    search_url = (
        f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        f"?input={query}&inputtype=textquery&fields=geometry,name&key={API_KEY}"
    )
    response = requests.get(search_url)
    if response.status_code == 200:
        candidates = response.json().get('candidates', [])
        if candidates:
            return candidates[0]  # Return the first matching place
    return None

# Initialize session state
if "marker_location" not in st.session_state:
    st.session_state.marker_location = [48.8566, 2.3522]  # Default to Paris
    st.session_state.zoom = 12

# Handle the search query only when it changes
if place_query and place_query != st.session_state.previous_query:
    print("place query", place_query)
    place_details = fetch_place_details(place_query)
    if place_details:
        location = place_details['geometry']['location']
        st.session_state.marker_location = [location['lat'], location['lng']]
        st.session_state.zoom = 15  # Zoom in closer to the selected place
        st.success(f"Found: {place_details['name']}")
    else:
        st.error("Place not found. Please try a different query.")
    # Update the previous query
    st.session_state.previous_query = place_query

# Search settings
st.subheader("Search Settings")
PLACE_TYPES = [
    'restaurant', 'bar', 'cafe', 'tourist_attraction', 
    'museum', 'art_gallery', 'church', 'park',
    'historical_landmark', 'night_club', 'tourism'
]
selected_place_type = st.selectbox("Place Type", options=PLACE_TYPES, index=0)

col1, col2 = st.columns([3, 1])
with col1:
    search_radius = st.slider("Search Radius (meters)", min_value=100, max_value=2000, value=500, step=100)
with col2:
    manual_radius = st.number_input("Custom Radius", min_value=100, value=search_radius, help="Enter a custom radius in meters")

search_radius = manual_radius if manual_radius != search_radius else search_radius

# Add geolocation button
col1, col2 = st.columns([1, 3])
with col1:
    location = streamlit_geolocation()
with col2:
    st.markdown("👈 Click to use your current location")

if location and location['latitude'] is not None and location['longitude'] is not None:
    st.session_state.marker_location = [location['latitude'], location['longitude']]
    st.session_state.zoom = 15

# Create the base map
m = folium.Map(location=st.session_state.marker_location, zoom_start=st.session_state.zoom)

# Display coordinates
st.write(f"Selected Coordinates: {st.session_state.marker_location}")

# Add a marker and circle
folium.Marker(
    location=st.session_state.marker_location,
    draggable=False,
    icon=folium.Icon(color="red", icon="info-sign"),
).add_to(m)

folium.Circle(
    location=st.session_state.marker_location,
    radius=search_radius,
    color="blue",
    fill=True,
    fillColor="blue",
    fillOpacity=0.1
).add_to(m)

# Render the map
map_data = st_folium(m, width=300, height=300)

# Simplified map click handling without debounce
if map_data.get("last_clicked"):
    print("last clicked", map_data["last_clicked"])
    lat, lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    st.session_state.marker_location = [lat, lng]
    st.session_state.zoom = map_data["zoom"]
    print('rerunning')
    st.rerun()

# Function to fetch nearby places
def fetch_nearby_places(location, radius=2500, place_type='restaurant'):
    search_url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={location}&radius={radius}&type={place_type}&key={API_KEY}"
    )
    response = requests.get(search_url)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        st.error("Error fetching data from Google Places API.")
        return []

if st.button(f"Search {selected_place_type.replace('_', ' ').title()}s"):
    location_str = f"{st.session_state.marker_location[0]},{st.session_state.marker_location[1]}"
    with st.spinner(f'Searching for {selected_place_type.replace("_", " ")}s... Please wait.'):
        results = fetch_nearby_places(location_str, radius=search_radius, place_type=selected_place_type)
        if results:
            st.subheader(f"Top {selected_place_type.replace('_', ' ').title()}s Nearby:")
            places = [
                {
                    'name': place.get('name'),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'rating': place.get('rating', 'N/A'),
                    'place_id': place.get('place_id')
                }
                for place in results
            ]
            sorted_places = sorted(places, key=lambda x: x['user_ratings_total'], reverse=True)
            for place in sorted_places:
                st.markdown(f"### {place['name']}")
                st.write(f"**Rating:** {place['rating']} stars  |  **Reviews:** {place['user_ratings_total']}")
                google_maps_link = (
                    f"https://www.google.com/maps/search/?api=1&query={place['name'].replace(' ', '+')}"
                    f"&query_place_id={place['place_id']}"
                )
                st.markdown(f"[View on Google Maps]({google_maps_link})")
                st.write("---")
        else:
            st.warning(f"No {selected_place_type.replace('_', ' ')}s found nearby.")
