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

st.title("Most reviewed places Finder")

# Remove sidebar references and place controls in main page
st.subheader("Search Settings")

# Add place type selector
PLACE_TYPES = [
    'restaurant', 'bar', 'cafe', 'tourist_attraction', 
    'museum', 'art_gallery', 'church', 'park',
    'historical_landmark', 'night_club', 'tourism'
]
selected_place_type = st.selectbox(
    "Place Type",
    options=PLACE_TYPES,
    index=0  # Default to restaurant
)

# Replace the existing slider with a number input that has a slider
col1, col2 = st.columns([3, 1])
with col1:
    search_radius = st.slider(
        "Search Radius (meters)",
        min_value=100,
        max_value=2000,
        value=500,
        step=100
    )
with col2:
    manual_radius = st.number_input(
        "Custom Radius",
        min_value=100,
        value=search_radius,
        help="Enter a custom radius in meters"
    )

# Use the manual input if it's different from the slider value
search_radius = manual_radius if manual_radius != search_radius else search_radius

# Add geolocation button
location = streamlit_geolocation()

# Update marker location when geolocation is received
if location and location['latitude'] is not None and location['longitude'] is not None:
    st.session_state.marker_location = [location['latitude'], location['longitude']]
    st.session_state.zoom = 15  # Zoom in closer when getting user's location

# Initialize session state to store marker location if not already set
if "marker_location" not in st.session_state:
    st.session_state.marker_location = [48.8566, 2.3522]  # Default to Paris
    st.session_state.zoom = 12

# Create the base map with smaller dimensions
m = folium.Map(location=st.session_state.marker_location, zoom_start=st.session_state.zoom)

# Display coordinates before the map
st.write(f"Selected Coordinates: {st.session_state.marker_location}")

# Add a marker at the current location in session state
marker = folium.Marker(
    location=st.session_state.marker_location,
    draggable=False,
    icon=folium.Icon(color="red", icon="info-sign"),
)
marker.add_to(m)

# Add a circle to show the search radius
folium.Circle(
    location=st.session_state.marker_location,
    radius=search_radius,
    color="blue",
    fill=True,
    fillColor="blue",
    fillOpacity=0.1
).add_to(m)

# Render the map with smaller dimensions
map_data = st_folium(m, width=300, height=300)

# Update marker position immediately after each click
if map_data.get("last_clicked"):
    lat, lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    st.session_state.marker_location = [lat, lng]
    st.session_state.zoom = map_data["zoom"]
    st.rerun()

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

# Update the search button text to be more generic
if st.button(f"Search {selected_place_type.replace('_', ' ').title()}s"):
    # Update the fetch call to use selected place type
    location_str = f"{st.session_state.marker_location[0]},{st.session_state.marker_location[1]}"
    with st.spinner(f'Searching for {selected_place_type.replace("_", " ")}s... Please wait.'):
        results = fetch_nearby_restaurants(location_str, radius=search_radius, place_type=selected_place_type)

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
                st.write(
                    f"**Rating:** {place['rating']} stars  |  **Reviews:** {place['user_ratings_total']}"
                )
                google_maps_link = (
                    f"https://www.google.com/maps/search/?api=1&query={place['name'].replace(' ', '+')}"
                    f"&query_place_id={place['place_id']}"
                )
                st.markdown(f"[View on Google Maps]({google_maps_link})")
                st.write("---")
        else:
            st.warning(f"No {selected_place_type.replace('_', ' ')}s found nearby.")
