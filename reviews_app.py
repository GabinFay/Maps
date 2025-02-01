import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from dotenv import load_dotenv
import os
from streamlit_geolocation import streamlit_geolocation

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    st.error("GOOGLE_MAPS_API_KEY environment variable is not set.")
    st.stop()

st.title("Restaurant Finder")

# Add geolocation button in sidebar
st.sidebar.header("Location Options")
location = streamlit_geolocation()

# Update marker location when geolocation is received
if location and location['latitude'] is not None and location['longitude'] is not None:
    st.session_state.marker_location = [location['latitude'], location['longitude']]
    st.session_state.zoom = 15  # Zoom in closer when getting user's location

# Initialize session state to store marker location if not already set
if "marker_location" not in st.session_state:
    st.session_state.marker_location = [48.8566, 2.3522]  # Default to Paris
    st.session_state.zoom = 12

# Create the base map
m = folium.Map(location=st.session_state.marker_location, zoom_start=st.session_state.zoom)

# Add a marker at the current location in session state
marker = folium.Marker(
    location=st.session_state.marker_location,
    draggable=False,
    icon=folium.Icon(color="red", icon="info-sign"),
)
marker.add_to(m)

# Render the map and capture clicks
map_data = st_folium(m, width=700, height=500)

# Update marker position immediately after each click
if map_data.get("last_clicked"):
    lat, lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    st.session_state.marker_location = [lat, lng]
    st.session_state.zoom = map_data["zoom"]

# Display coordinates
st.write(f"Selected Coordinates: {st.session_state.marker_location}")

# Function to fetch nearby restaurants
def fetch_nearby_restaurants(location, radius=2500, place_type='restaurant'):
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

# Add search button (renamed from "Confirm Location")
if st.button("Search Restaurants"):
    # Fetch and display restaurants
    location_str = f"{st.session_state.marker_location[0]},{st.session_state.marker_location[1]}"
    with st.spinner('Searching for restaurants... Please wait.'):
        results = fetch_nearby_restaurants(location_str)

        if results:
            st.subheader("Top Restaurants Nearby:")
            restaurants = [
                {
                    'name': place.get('name'),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'rating': place.get('rating', 'N/A'),
                    'place_id': place.get('place_id')
                }
                for place in results
            ]
            sorted_restaurants = sorted(restaurants, key=lambda x: x['user_ratings_total'], reverse=True)

            for restaurant in sorted_restaurants:
                st.markdown(f"### {restaurant['name']}")
                st.write(
                    f"**Rating:** {restaurant['rating']} stars  |  **Reviews:** {restaurant['user_ratings_total']}"
                )
                google_maps_link = (
                    f"https://www.google.com/maps/search/?api=1&query={restaurant['name'].replace(' ', '+')}"
                    f"&query_place_id={restaurant['place_id']}"
                )
                st.markdown(f"[View on Google Maps]({google_maps_link})")
                st.write("---")
        else:
            st.warning("No restaurants found nearby.")
